import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from marketdata.models import MarketDataToken
from marketdata.utils import get_active_fyers_access_token
from fyers_apiv3 import fyersModel
from decouple import config

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch and refresh the active Fyers Market Data token"

    def handle(self, *args, **options):
        try:
            # Get current active token from DB
            token = get_active_fyers_access_token()

            if not token:
                self.stdout.write(self.style.WARNING("⚠️ No active Fyers token found in DB."))
                return

            self.stdout.write(self.style.SUCCESS(f"✅ Using Fyers token: {token[:15]}..."))

            # Initialize Fyers model with token
            fyers = fyersModel.FyersModel(
                client_id=config("FYERS_CLIENT_ID"),
                token=token,
                log_path="."
            )

            # Test call - profile or market status (lightweight endpoint)
            response = fyers.get_profile()

            if response.get("s") == "ok":
                self.stdout.write(self.style.SUCCESS("🎯 Token is valid."))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Token validation failed: {response}"))

        except Exception as e:
            logger.exception("Error while refreshing Fyers token")
            self.stdout.write(self.style.ERROR(f"❌ Exception: {str(e)}"))