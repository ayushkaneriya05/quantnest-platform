# backend/run_fyers_client.py
import os
import django
import threading

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from marketdata.fyers_ws_client import run_forever_from_env
from marketdata.redis_forwarder import run_forwarder

def main():
    """
    This script runs the Fyers WebSocket client and the Redis forwarder in separate threads.
    It should be run as a standalone, persistent background service for the application to receive live data.
    """
    print("Starting Fyers WebSocket client and Redis forwarder...")

    # Run the Fyers WebSocket client in a separate thread
    fyers_thread = threading.Thread(target=run_forever_from_env, daemon=True)
    fyers_thread.start()

    # Run the Redis forwarder in the main thread (or another thread)
    run_forwarder()

if __name__ == "__main__":
    main()