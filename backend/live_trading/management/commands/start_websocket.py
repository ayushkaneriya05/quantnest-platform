"""
Startup script for QuantNest WebSocket integration.
Initializes WebSocket processors for active broker credentials.
"""

import logging
import signal
import threading
import time

from django.core.management.base import BaseCommand

from live_trading.websocket_manager import _websocket_manager
from brokers.models import BrokerCredential

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start WebSocket processors for active broker credentials'

    def handle(self, *args, **options):
        """Handle the command."""
        self._shutdown_event = threading.Event()
        self.stdout.write("Starting WebSocket processors...")

        _websocket_manager.start_health_monitor()

        active_credentials = BrokerCredential.objects.filter(is_active=True, is_verified=True)
        self.stdout.write(f"Found {active_credentials.count()} active broker credentials")

        for credential in active_credentials:
            try:
                success = _websocket_manager.start_processor(credential.id)
                if success:
                    self.stdout.write(self.style.SUCCESS(f"✓ Started WebSocket for {credential.broker_name} - {credential.label}"))
                else:
                    self.stdout.write(self.style.WARNING(f"✗ Failed to start WebSocket for {credential.broker_name} - {credential.label}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error starting WebSocket for {credential.broker_name} - {credential.label}: {e}"))

        self.stdout.write(self.style.SUCCESS("WebSocket startup complete"))
        self.stdout.write("Press Ctrl+C to stop all WebSocket processors")

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        while not self._shutdown_event.is_set():
            time.sleep(0.5)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.stdout.write("\nReceived shutdown signal, stopping WebSocket processors...")
        self._shutdown_event.set()
        _websocket_manager.stop_all()
        self.stdout.write(self.style.SUCCESS("All WebSocket processors stopped"))
