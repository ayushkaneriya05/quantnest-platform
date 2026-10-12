"""Observed-event fanout to execution nodes; UI quote coalescing is a separate path."""
import hashlib
import json
import logging
import queue
import threading
import time
import uuid

from core.redis import runtime_redis

logger = logging.getLogger(__name__)
STREAM = "quantnest:market:observations"


class ObservationRelay:
    def __init__(self):
        self.generation = int.from_bytes(hashlib.blake2b(uuid.uuid4().bytes, digest_size=8).digest(), "big") & ((1 << 63) - 1)
        self.queue = queue.Queue(maxsize=32768)
        self.stop = threading.Event()
        self.failed = threading.Event()
        self.thread = threading.Thread(target=self.run, name="market-relay", daemon=True)
        self.thread.start()

    def rotate(self):
        self.generation = int.from_bytes(hashlib.blake2b(uuid.uuid4().bytes, digest_size=8).digest(), "big") & ((1 << 63) - 1)

    def emit(self, symbol, quote, volume, event_time, received, sequence):
        try:
            self.queue.put_nowait({"symbol": symbol, "quote": quote, "volume": volume,
                                   "event_time": event_time, "received": received,
                                   "sequence": sequence, "generation": self.generation})
        except queue.Full:
            self.failed.set()
            raise RuntimeError("Market observation relay capacity exhausted")

    def run(self):
        while not self.stop.is_set():
            try:
                event = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                events = [event]
                for _ in range(255):
                    try:
                        events.append(self.queue.get_nowait())
                    except queue.Empty:
                        break
                pipeline = runtime_redis().pipeline(transaction=False)
                for value in events:
                    pipeline.xadd(STREAM, {"event": json.dumps(value, separators=(",", ":"))})
                pipeline.xtrim(STREAM, minid=f"{int((time.time() - 120) * 1000)}-0", approximate=True)
                pipeline.execute()
            except Exception:
                self.failed.set()
                logger.exception("Market observation replication failed")
                return

    def close(self):
        self.stop.set()
        self.thread.join(timeout=6)


class SubscriptionSink:
    def subscribe(self, **kwargs):
        pass

    def unsubscribe(self, **kwargs):
        pass

    def close_connection(self):
        pass


def run_replica(stop):
    from marketdata.live_feed import MarketObservationClient
    # Reuse canonical preparation/publication plumbing without opening a broker socket.
    client = MarketObservationClient()
    client.broadcast_quotes = False
    client.socket = SubscriptionSink()
    tail = runtime_redis().xrevrange(STREAM, count=1)
    cursor = tail[0][0] if tail else "0-0"
    client.start_subscription_sync()
    try:
        while not stop.is_set():
            for _, messages in runtime_redis().xread({STREAM: cursor}, count=1000, block=1000):
                for identity, fields in messages:
                    event = json.loads(fields["event"])
                    client.ingest_observation(
                        event["symbol"], event["quote"], event["volume"], event["event_time"],
                        event["received"], source_sequence=event["sequence"], source_generation=event["generation"])
                    cursor = identity
    finally:
        client.shutdown()
