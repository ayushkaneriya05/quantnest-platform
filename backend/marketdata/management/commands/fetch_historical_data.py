# backend/marketdata/management/commands/fetch_historical_data.py
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from fyers_apiv3 import fyersModel
from ohlc.models import OHLC
from marketdata.storage import FyersTokenStorage

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Fetches and stores maximum available historical OHLC data from Fyers."

    def handle(self, *args, **options):
        self.stdout.write("Starting historical data fetch...")

        token_storage = FyersTokenStorage()
        access_token = token_storage.get_token()

        if not access_token:
            self.stderr.write("Fyers access token not found. Please generate it first.")
            return

        fyers = fyersModel.FyersModel(
            client_id=settings.FYERS_CLIENT_ID,
            token=access_token,
            log_path="",
        )

        # Example: Fetch for a single symbol. You can loop through your symbol list.
        symbol = "NSE:SBIN-EQ"
        
        # Fyers allows fetching data up to a certain range. We fetch year by year.
        for year in range(datetime.now().year - 5, datetime.now().year + 1):
            range_from = f"{year}-01-01"
            range_to = f"{year}-12-31"

            data = {
                "symbol": symbol,
                "resolution": "D", # Daily data
                "date_format": "1",
                "range_from": range_from,
                "range_to": range_to,
                "cont_flag": "1",
            }

            self.stdout.write(f"Fetching data for {symbol} from {range_from} to {range_to}...")
            response = fyers.history(data=data)

            if response.get("code") == 200 and response.get("candles"):
                candles = response["candles"]
                ohlc_objects = []
                for c in candles:
                    ohlc_objects.append(
                        OHLC(
                            symbol=symbol,
                            tf="1D", # Daily timeframe
                            ts=datetime.fromtimestamp(c[0]),
                            open=c[1],
                            high=c[2],
                            low=c[3],
                            close=c[4],
                            volume=c[5],
                        )
                    )
                
                OHLC.objects.bulk_create(ohlc_objects, ignore_conflicts=True)
                self.stdout.write(f"Stored {len(ohlc_objects)} data points for {year}.")
            else:
                self.stderr.write(f"Failed to fetch data for {year}: {response.get('message')}")

        self.stdout.write("Historical data fetch complete.")