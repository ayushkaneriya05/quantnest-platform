# ohlc/backfill.py
import datetime
from fyers_apiv3 import fyersModel
from marketdata.utils import get_active_fyers_access_token
from django.conf import settings

def backfill_ohlc(symbol, resolution="1", days=5):
    """
    Fetch OHLC data from Fyers API using stored DB token.
    """
    access_token = get_active_fyers_access_token()
    fyers = fyersModel.FyersModel(
        client_id=settings.FYERS_CLIENT_ID,
        token=f"{settings.FYERS_CLIENT_ID}:{access_token}"
    )

    from_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    to_date = datetime.datetime.now().strftime("%Y-%m-%d")

    data = {
        "symbol": symbol,
        "resolution": resolution,
        "date_format": "1",
        "range_from": from_date,
        "range_to": to_date,
        "cont_flag": "1"
    }

    return fyers.history(data)
