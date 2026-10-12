"""Market-provider adapters. Calculations and matching consume normalized data."""
import logging
from datetime import datetime, timezone as py_timezone
from functools import lru_cache
from django.conf import settings
from django.utils.module_loading import import_string
from django.utils import timezone
from trading_domain.contracts import DataCapabilities
from marketdata.utils import get_active_fyers_access_token

logger = logging.getLogger(__name__)


class FyersProvider:
    name = "fyers"
    capabilities = DataCapabilities(trades=False, quotes=True, depth=False, historical=True, sequence=False)

    def live_client(self):
        from marketdata.live_feed import FyersLiveFeedClient
        return FyersLiveFeedClient()

    def quote(self, symbol):
        from marketdata.services import MarketDataService
        access_token = get_active_fyers_access_token()
        if not access_token:
            return None
        
        try:
            from fyers_apiv3 import fyersModel
            fyers = fyersModel.FyersModel(client_id=settings.FYERS_CLIENT_ID, is_async=False, token=access_token)
            
            normalized = MarketDataService.normalize_symbol(symbol)
            data = {"symbols": normalized}
            response = fyers.quotes(data=data)
            
            if response.get("s") == "ok" and "d" in response and response["d"]:
                quote_data = response["d"][0].get("v", {})
                if quote_data:
                    # Fyers timestamp is typically in epoch seconds
                    tt_val = quote_data.get("tt", 0)
                    if not tt_val:
                        tt_val = int(timezone.now().timestamp())
                    dt = datetime.fromtimestamp(int(tt_val), tz=py_timezone.utc)
                    return {
                        "symbol": normalized,
                        "price": float(quote_data.get("lp", 0)),
                        
                        # Normalized OHLC values
                        "open": float(quote_data.get("open_price", 0)),
                        "high": float(quote_data.get("high_price", 0)),
                        "low": float(quote_data.get("low_price", 0)),
                        "close": float(quote_data.get("prev_close_price", 0)),
                        
                        # Session summary
                        "day_open": float(quote_data.get("open_price", 0)),
                        "day_high": float(quote_data.get("high_price", 0)),
                        "day_low": float(quote_data.get("low_price", 0)),
                        "prev_close": float(quote_data.get("prev_close_price", 0)),
                        "volume": int(quote_data.get("volume", 0)),
                        "timestamp": dt.isoformat(),
                        "resolution": "1m",
                        "change": float(quote_data.get("ch", 0)),
                        "change_percent": float(quote_data.get("chp", 0)),
                        "updated_at": dt.isoformat(),
                    }
        except Exception as e:
            logger.error(f"Error fetching live quote from Fyers for {symbol}: {e}")
        return None


    def history(self, symbol, timeframe, date_from, date_to):
        from marketdata.services import MarketDataService
        access_token = get_active_fyers_access_token()
        if not access_token:
            logger.error("No active Fyers access token found")
            return None

        client_id = settings.FYERS_CLIENT_ID
        resolution = MarketDataService.normalize_timeframe(timeframe)
        api_resolution = MarketDataService.RESOLUTION_TO_FYERS.get(resolution, resolution)

        def _to_fyers_epoch(val, *, end_of_day=False):
            if isinstance(val, (int, float)):
                return int(val)
            val_str = str(val)
            if "T" in val_str or ":" in val_str:
                dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
                return int(dt.timestamp())
            if "-" in val_str:
                dt = datetime.fromisoformat(val_str[:10]).replace(tzinfo=py_timezone.utc)
                if len(val_str) <= 10 and end_of_day:
                    dt = dt.replace(hour=23, minute=59, second=59)
                return int(dt.timestamp())
            return int(val_str)
        params = {
            "symbol": MarketDataService.normalize_symbol(symbol),
            "resolution": api_resolution,
            "date_format": "0",
            "range_from": str(_to_fyers_epoch(date_from)),
            "range_to": str(_to_fyers_epoch(date_to, end_of_day=True)),
            "cont_flag": "1",
        }

        try:
            from fyers_apiv3 import fyersModel
            fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token)
            data = fyers.history(data=params)
        except Exception as exc:
            logger.exception("Exception while fetching candles for %s: %s", symbol, exc)
            return None

        if data.get("s") == "no_data":
            return []

        if data.get("s") != "ok":
            logger.error("Fyers API Error for %s: %s", symbol, data)
            return None

        candles = []
        for item in data.get("candles", []):
            candles.append(
                {
                    "time": datetime.fromtimestamp(int(item[0]), tz=py_timezone.utc),
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": int(item[5]),
                }
            )
        return candles

@lru_cache(maxsize=1)
def provider():
    name = settings.MARKET_DATA_PROVIDER
    adapters = {"fyers": FyersProvider}
    implementation = adapters.get(name)
    if implementation is None:
        implementation = import_string(name)
    return implementation()


def live_client():
    return provider().live_client()
