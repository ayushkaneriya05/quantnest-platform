import logging
import threading

from django.core.management.base import BaseCommand

from live_trading.services import LiveExecutionService
from paper_trading.services import PaperExecutionService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs the LIVE and PAPER ZeroMQ order subscribers."

    def handle(self, *args, **options):
        subscribers = (
            ("live", LiveExecutionService.run_zmq_subscriber),
            ("paper", PaperExecutionService.run_zmq_subscriber),
        )
        threads = []

        for name, subscriber in subscribers:
            thread = threading.Thread(
                target=self._run_subscriber,
                args=(name, subscriber),
                name=f"zmq-{name}-subscriber",
                daemon=True,
            )
            thread.start()
            threads.append(thread)
            self.stdout.write(f"Started {name} ZeroMQ order subscriber")

        self.stdout.write(self.style.SUCCESS("LIVE and PAPER order subscribers are running."))
        self.stdout.write("Press Ctrl+C to stop both subscribers.")

        try:
            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            self.stdout.write("\nStopping order subscribers...")

    @staticmethod
    def _run_subscriber(name, subscriber):
        try:
            subscriber()
        except Exception:
            logger.exception("%s ZeroMQ order subscriber stopped unexpectedly", name)
            raise
