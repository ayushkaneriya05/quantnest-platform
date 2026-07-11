# backend/backend/run_fyers_client.py
import logging
import os
import django
import webbrowser
import requests

logger = logging.getLogger(__name__)


# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()


def main():
    """
    This script handles the one-time Fyers login process by generating the
    login URL. It then guides the user to complete the login in their browser,
    which triggers our backend callback to securely generate and store the access token.
    """
    webbrowser.open("http://127.0.0.1:8000/api/v1/market/fyers/login/")

if __name__ == "__main__":
    # Ensure the Django server is running before starting the auth process
    try:
        requests.get("http://localhost:8000/health/", timeout=2)
    except requests.ConnectionError:
        logger.error("Django server is not running. Please start the server before running this script.")
    else:
        main()
