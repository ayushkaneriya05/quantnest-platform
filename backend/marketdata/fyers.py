"""FYERS market-data API and SDK adapters; consumers receive QuantNest data."""
import logging
import socket
import ssl
import threading
import time
from datetime import datetime, timedelta, timezone

import requests
from django.conf import settings
from fyers_apiv3.FyersWebsocket import data_ws
from websocket import WebSocketException

from .live_feed import MarketObservationClient
from .contracts import HistoryRequest, normalize_symbol, ProviderError
from .models import MarketDataToken

logger = logging.getLogger(__name__)


class FyersProvider:
    name = "fyers"
    DATA_URL = "https://api-t1.fyers.in/data"
    RESOLUTIONS = {"1m": "1", "1D": "D"}
    history_window_days = {"1m": 30, "1D": 360}
    quota_timezone = "Asia/Kolkata"
    # Enhanced source-account entitlement. Keep vendor limits in this adapter.
    subscription_limit = 5000
    quote_batch_size = 50  # FYERS' GET quotes endpoint limit.
    request_interval_ms = 120  # Within 10/second and 500/minute.
    daily_request_limit = 500000

    @property
    def account_key(self):
        return settings.FYERS_CLIENT_ID

    def _get(self, endpoint: str, parameters: dict) -> dict:
        """Bound read-only HTTP waits and retain errors the SDK masks as -99.

        History preparation already schedules retries. Do not multiply calls
        here when the network is down, and never log credentials or headers.
        """
        from .providers import acquire_data_request
        access_token = MarketDataToken.active_access_token()
        if not access_token:
            raise ProviderError("Authorize the market-data connection before fetching FYERS data.")
        acquire_data_request(self)
        try:
            response = requests.get(f"{self.DATA_URL}/{endpoint}", params=parameters,
                headers={"Authorization": f"{settings.FYERS_CLIENT_ID}:{access_token}", "version": "3"},
                timeout=(5, 15))
        except requests.RequestException as exc:
            kind = type(exc).__name__
            logger.warning("FYERS data transport failed endpoint=%s category=%s", endpoint, kind)
            raise ProviderError(f"FYERS data connection failed ({kind}). Check network/DNS/TLS connectivity and retry.") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError(f"FYERS data returned an unreadable response (HTTP {response.status_code}); retry shortly.") from exc
        if not isinstance(payload, dict):
            raise ProviderError("FYERS data returned an invalid response; retry shortly.")
        if response.status_code in (401, 403) or payload.get("code") in (-8, -15, -16, -17):
            raise ProviderError("FYERS data authorization failed. Check the source account's access and reauthorize market data.")
        if not response.ok:
            raise ProviderError(f"FYERS data request failed (HTTP {response.status_code}): {payload.get('message') or 'Provider unavailable.'}")
        return payload

    def live_client(self):
        return FyersLiveFeedClient()

    def quotes(self, symbols: list[str]) -> dict[str, dict]:
        """Acquire watchlist snapshots together; one bad symbol does not hide others."""
        symbols = list(dict.fromkeys(normalize_symbol(symbol) for symbol in symbols))
        quotes = {}
        for start in range(0, len(symbols), self.quote_batch_size):
            batch = symbols[start:start + self.quote_batch_size]
            try:
                requested_at = datetime.now(timezone.utc).isoformat()
                response = self._get("quotes", {"symbols": ",".join(batch)})
                if response["s"] != "ok":
                    raise ValueError(response["message"])
                for row in response["d"]:
                    if row["s"] != "ok" or row["n"] not in batch:
                        continue
                    values = row["v"]
                    quotes[row["n"]] = {
                        "symbol": row["n"], "price": values["lp"],
                        "timestamp": datetime.fromtimestamp(int(values["tt"]), timezone.utc).isoformat(),
                        # A live tick received during this request must stay newer.
                        "change_percent": values["chp"], "updated_at": requested_at,
                        "source": "provider",
                    }
            except ProviderError:
                break
            except Exception:
                logger.exception("FYERS quotes failed symbols=%s", batch)
        return quotes

    def history(self, window: HistoryRequest):
        symbol, timeframe = window.instrument.sym_ticker, window.timeframe
        start_dt, end_dt = window.start, window.end - timedelta(seconds=1)
        request = {
            "symbol": normalize_symbol(symbol),
            "resolution": self.RESOLUTIONS[timeframe], "date_format": "0",
            "range_from": str(int(start_dt.timestamp())), "range_to": str(int(end_dt.timestamp())),
            # Every stored series belongs to this exact contract, not a roll.
            "cont_flag": "0",
        }
        try:
            response = self._get("history", request)
            if response["s"] == "no_data":
                logger.debug("FYERS history empty symbol=%s timeframe=%s from=%s to=%s",
                             request["symbol"], timeframe, start_dt.isoformat(), end_dt.isoformat())
                return []
            if response["s"] != "ok":
                logger.error("FYERS history rejected symbol=%s timeframe=%s from=%s to=%s status=%s code=%s message=%s",
                             request["symbol"], timeframe, start_dt.isoformat(), end_dt.isoformat(),
                             response["s"], response.get("code"), response.get("message"))
                raise ProviderError(f"FYERS rejected historical data (code {response.get('code')}): {response.get('message') or 'No reason supplied.'}")
            return [{"time": datetime.fromtimestamp(row[0], timezone.utc),
                     "open": row[1], "high": row[2], "low": row[3], "close": row[4], "volume": row[5]}
                    for row in response["candles"]]
        except ProviderError:
            raise
        except Exception as exc:
            logger.exception("FYERS history failed symbol=%s timeframe=%s from=%s to=%s",
                             request["symbol"], timeframe, start_dt.isoformat(), end_dt.isoformat())
            raise ProviderError("FYERS history is unavailable. Check the market-data connection and retry.") from exc

    @staticmethod
    def instrument_master():
        from instruments.fyers import FyersInstrumentMaster
        return FyersInstrumentMaster


class FyersLiveFeedClient(MarketObservationClient):
    """Fyers transport and normalization; shared consumers receive canonical observations."""

    # FYERS channel 15 updates full quote fields together. The SDK's default
    # channel can emit price-only updates with cached time/volume fields.
    subscription_channel = 15

    def __init__(self):
        super().__init__()
        self._volume_lock = threading.Lock()
        self._last_cumulative_volume = {}

    def connect(self):
        access_token = MarketDataToken.active_access_token()
        if not settings.FYERS_CLIENT_ID or not access_token:
            raise RuntimeError("Authorize the FYERS market-data connection before starting the feed.")

        epoch = self._transport_epoch = object()
        self.socket = data_ws.FyersDataSocket(
            access_token=f"{settings.FYERS_CLIENT_ID}:{access_token}",
            log_path=str(settings.BASE_DIR / "logs"),
            litemode=False,
            write_to_file=False,
            reconnect=True,
            on_close=lambda message: self._on_close(message) if self._transport_epoch is epoch else None,
            on_error=lambda message: self._on_error(message) if self._transport_epoch is epoch else None,
            on_message=lambda message: self._on_message(message) if self._transport_epoch is epoch else None,
        )
        self.socket.connect()
        return self.socket

    def subscribe_symbols(self, symbols: list[str]) -> None:
        from .providers import acquire_data_request
        acquire_data_request(FyersProvider())
        self.socket.subscribe(symbols=symbols, data_type="SymbolUpdate", channel=self.subscription_channel)

    def unsubscribe_symbols(self, symbols: list[str]) -> None:
        from .providers import acquire_data_request
        acquire_data_request(FyersProvider())
        self.socket.unsubscribe(symbols=symbols, data_type="SymbolUpdate", channel=self.subscription_channel)

    def disconnect(self) -> None:
        if self.socket is not None:
            self.socket.close_connection()

    def _on_close(self, message: dict):
        logger.warning("FYERS market socket closed code=%s", message["code"])
        self.mark_disconnected()

    def _on_error(self, message: dict):
        # The SDK's transport failures are exceptions; protocol errors are dicts.
        if isinstance(message, (WebSocketException, ConnectionError, ssl.SSLError, socket.gaierror)):
            logger.warning("FYERS market connection interrupted; SDK reconnecting: %s", message)
            self.mark_disconnected()
        else:
            logger.error("FYERS market socket error: %s", message)
        if isinstance(message, dict) and message.get("type") == "cn":
            self.mark_disconnected()
        if isinstance(message, dict):
            operation = {"sub": "subscribe", "unsub": "unsubscribe"}.get(message.get("type"))
            if message.get("code") == -300 and message.get("invalid_symbols"):
                with self._state_lock:
                    self._invalid_symbols.update(message.get("invalid_symbols", []))
                    for symbol in message.get("invalid_symbols", []):
                        self._rejected[symbol] = "The provider rejected this instrument symbol."
                    if self._pending is not None:
                        pending_operation, symbols, deadline = self._pending
                        remaining = [symbol for symbol in symbols if symbol not in self._invalid_symbols]
                        self._pending = (pending_operation, remaining, deadline) if remaining else None
                self._sync_wakeup.set()
                return
            if operation is None and self._pending is not None:
                operation = self._pending[0]
            if operation:
                self.subscription_result(operation, False, message.get("message", "Subscription failed."))

    def _on_message(self, tick: dict):
        kind = tick.get("type")
        if kind == "cn":
            if tick["s"] == "ok":
                # The SDK's on_connect can run before its transport opens.
                # Subscribe only after the server acknowledges authentication.
                self.mark_connected()
                with self._volume_lock:
                    self._last_cumulative_volume.clear()
                logger.info("FYERS market-data authentication confirmed")
            return
        if kind == "msg" and tick.get("code") == 51001:
            self.subscription_result("subscribe", False, tick["message"])
            return
        if kind in {"sub", "unsub"}:
            self.subscription_result("subscribe" if kind == "sub" else "unsubscribe", tick["s"] == "ok")
            return
        if kind not in {"sf", "if"}:
            return
        if tick["ltp"] <= 0:
            return
        received_at = time.time()
        # This is a quote stream, not a trade tape. A price update can carry an
        # older last_traded_time; use the exchange feed clock for both stocks
        # and indices so current quotes cannot reopen an earlier candle.
        event_at = tick["exch_feed_time"]
        timestamp = datetime.fromtimestamp(event_at, timezone.utc).isoformat()
        quote = {
            "price": tick["ltp"], "change_percent": tick["chp"], "timestamp": timestamp,
            "updated_at": datetime.fromtimestamp(received_at, timezone.utc).isoformat(),
        }
        volume_delta = 0
        if kind == "sf":
            cumulative_volume = tick["vol_traded_today"]
            with self._volume_lock:
                previous = self._last_cumulative_volume.get(tick["symbol"])
                if previous is not None:
                    previous_time, previous_volume = previous
                    if event_at < previous_time:
                        return  # Do not rewind the cumulative-volume baseline either.
                    if cumulative_volume >= previous_volume:
                        volume_delta = cumulative_volume - previous_volume
                self._last_cumulative_volume[tick["symbol"]] = event_at, cumulative_volume
        self.ingest_observation(tick["symbol"], quote, volume_delta, event_at, received_at)
