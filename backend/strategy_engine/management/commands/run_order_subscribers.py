import logging
import signal
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
        stop_event = threading.Event()

        def _shutdown(signum, frame):
            logger.info("Received shutdown signal %s; stopping ZeroMQ subscribers.", signum)
            stop_event.set()

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        for name, subscriber in subscribers:
            thread = threading.Thread(
                target=self._run_subscriber,
                args=(name, subscriber, stop_event),
                name=f"zmq-{name}-subscriber",
            )
            thread.start()
            threads.append(thread)
            self.stdout.write(f"Started {name} ZeroMQ order subscriber")

        self.stdout.write(self.style.SUCCESS("LIVE and PAPER order subscribers are running."))
        self.stdout.write("Press Ctrl+C to stop both subscribers.")

        try:
            while any(thread.is_alive() for thread in threads):
                for thread in threads:
                    thread.join(timeout=0.5)
                if stop_event.is_set():
                    break
        except KeyboardInterrupt:
            self.stdout.write("\nStopping order subscribers...")
            stop_event.set()

        self.stdout.write("Stopping order subscribers...")
        stop_event.set()
        for thread in threads:
            thread.join(timeout=2)

    @staticmethod
    def _run_subscriber(name, subscriber, stop_event):
        try:
            subscriber(stop_event=stop_event)
        except Exception:
            logger.exception("%s ZeroMQ order subscriber stopped unexpectedly", name)
            raise
