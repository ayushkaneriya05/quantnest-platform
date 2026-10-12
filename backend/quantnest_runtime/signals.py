"""Best-effort local wakeups; sequence watermarks provide recovery when packets drop."""
import socket
from django.conf import settings


def notify_market_change():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as channel:
        channel.setblocking(False)
        for index in range(settings.EXECUTION_WORKERS):
            try:
                channel.sendto(b"market", ("127.0.0.1", settings.EXECUTION_NOTIFY_PORT + index))
            except OSError:
                pass


def notification_socket(index):
    channel = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    channel.bind(("127.0.0.1", settings.EXECUTION_NOTIFY_PORT + index))
    channel.settimeout(settings.EXECUTION_SCAN_INTERVAL)
    return channel
