"""FYERS market-data API and SDK adapters; consumers receive QuantNest data."""
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from django.conf import settings
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws
from websocket import WebSocketException

from .live_feed import MarketObservationClient
from .contracts import HistoryRequest, normalize_symbol, ProviderError
from .models import MarketDataToken

logger = logging.getLogger(__name__)


class FyersProvider:
    name = "fyers"
    RESOLUTIONS = {"1m": "1", "1D": "D"}
    history_window_days = {"1m": 30, "1D": 360}
    quota_timezone = "Asia/Kolkata"
    # Enhanced source-account entitlement. Keep vendor limits in this adapter.
    subscription_limit = 5000
    request_interval_ms = 120  # Within 10/second and 500/minute.
    daily_request_limit = 500000

    @property
    def account_key(self):
        return settings.FYERS_CLIENT_ID

    @staticmethod
    def _client():
        access_token = MarketDataToken.active_access_token()
        if not access_token:
            raise ValueError("Authorize the market-data connection before fetching FYERS data.")
        return fyersModel.FyersModel(client_id=settings.FYERS_CLIENT_ID, token=access_token, is_async=False, log_path=str(settings.BASE_DIR / "logs"))

    def live_client(self):
        return FyersLiveFeedClient()

    def quote(self, symbol: str):
        symbol = normalize_symbol(symbol)
        try:
            from .providers import acquire_data_request
            acquire_data_request(self, wait_seconds=0)
            response = self._client().quotes(data={"symbols": symbol})
            if response["s"] != "ok":
                raise ValueError(response["message"])
            row = response["d"][0]
            if row["s"] != "ok" or row["n"] != symbol:
                raise ValueError(f"FYERS did not return a quote for {symbol}.")
            values = row["v"]
            timestamp = datetime.fromtimestamp(int(values["tt"]), timezone.utc).isoformat()
            return {
                "symbol": row["n"], "price": values["lp"],
                "timestamp": timestamp,
                "change_percent": values["chp"], "updated_at": datetime.now(timezone.utc).isoformat(),
                "source": "provider",
            }
        except ProviderError:
            return None
        except Exception:
            logger.exception("FYERS quote failed symbol=%s", symbol)
            return None

    def history(self, window: HistoryRequest):
        from .providers import acquire_data_request
        symbol, timeframe = window.instrument.sym_ticker, window.timeframe
        start_dt, end_dt = window.start, window.end - timedelta(seconds=1)
        acquire_data_request(self)
        request = {
            "symbol": normalize_symbol(symbol),
            "resolution": self.RESOLUTIONS[timeframe], "date_format": "0",
            "range_from": str(int(start_dt.timestamp())), "range_to": str(int(end_dt.timestamp())),
            # Every stored series belongs to this exact contract, not a roll.
            "cont_flag": "0",
        }
        try:
            response = self._client().history(data=request)
            if response["s"] == "no_data":
                logger.debug("FYERS history empty symbol=%s timeframe=%s from=%s to=%s",
                             request["symbol"], timeframe, start_dt.isoformat(), end_dt.isoformat())
                return []
            if response["s"] != "ok":
                logger.error("FYERS history rejected symbol=%s timeframe=%s from=%s to=%s status=%s code=%s message=%s",
                             request["symbol"], timeframe, start_dt.isoformat(), end_dt.isoformat(),
                             response["s"], response.get("code"), response.get("message"))
                raise ProviderError(f"FYERS rejected historical data (code {response.get('code')}). Reauthorize market data or retry.")
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
        self.socket.subscribe(symbols=symbols, data_type="SymbolUpdate")

    def unsubscribe_symbols(self, symbols: list[str]) -> None:
        from .providers import acquire_data_request
        acquire_data_request(FyersProvider())
        self.socket.unsubscribe(symbols=symbols, data_type="SymbolUpdate")

    def disconnect(self) -> None:
        if self.socket is not None:
            self.socket.close_connection()

    def _on_close(self, message: dict):
        logger.warning("FYERS market socket closed code=%s", message["code"])
        self.mark_disconnected()

    def _on_error(self, message: dict):
        # The SDK's transport failures are exceptions; protocol errors are dicts.
        if isinstance(message, (WebSocketException, ConnectionError)):
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
        # Index messages omit trade time/volume; receive time is explicit here.
        event_at = tick["last_traded_time"] if kind == "sf" else received_at
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
