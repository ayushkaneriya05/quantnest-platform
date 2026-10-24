"""One supervised scan owns broker sockets, authentication changes and retry backoff."""
import logging
import time
from functools import partial

from django.core.cache import cache
from django.db import close_old_connections
from django.utils import timezone

from brokers.services import BrokerService
from .order_processor import apply_order_observation

logger = logging.getLogger(__name__)


def _handle_order_update(credential, data: dict):
    close_old_connections()
    try:
        apply_order_observation(credential, data)
    except Exception:
        logger.exception("Broker order update failed credential=%s", credential.pk)
    finally:
        close_old_connections()


class WebSocketConnectionManager:
    def __init__(self):
        self.connections = {}
        self.connection_health = {}

    def sync_connections(self):
        from brokers.models import BrokerCredential, BrokerSession

        close_old_connections()
        credentials = {row.pk: row for row in BrokerCredential.objects.filter(is_active=True, is_verified=True)}
        sessions = dict(BrokerSession.objects.filter(
            credential_id__in=credentials, is_valid=True, token_expiry__gt=timezone.now()
        ).order_by("credential_id", "-created_at").distinct("credential_id").values_list("credential_id", "pk"))
        for credential_id in set(self.connection_health) | set(self.connections):
            if credential_id not in credentials:
                self.stop_connection(credential_id)

        for credential_id, credential in credentials.items():
            connection = self.connections.get(credential_id)
            health = self.connection_health.setdefault(credential_id, {})
            session_id = sessions.get(credential_id)
            now = time.time()
            renewed = health.get("broker_session_id") != session_id
            if session_id is None:
                if connection:
                    self.stop_connection(credential_id)
                health = {"status": "authentication_required", "broker_session_id": None,
                          "reconnect_attempts": 0, "last_error": "No valid broker session"}
            elif connection and connection.is_connected and connection.is_subscribed and not renewed:
                health.update(status="connected", last_heartbeat=timezone.now().isoformat())
                if now - health.get("connected_since", now) >= 120:
                    health["reconnect_attempts"] = 0
            else:
                attempts = 0 if renewed else int(health.get("reconnect_attempts", 0))
                due = renewed or now - health.get("last_reconnect_attempt", 0) >= min(300, 5 * 2 ** min(attempts, 6))
                health["status"] = "reconciliation"
                if due:
                    if connection:
                        self.stop_connection(credential_id)
                    connection = None
                    health.update(broker_session_id=session_id, last_reconnect_attempt=now,
                                  reconnect_attempts=attempts + 1)
                    try:
                        connection = BrokerService.create_order_stream(credential)
                        connection.on_order_update(partial(_handle_order_update, credential))
                        connection.connect()
                        self.connections[credential_id] = connection
                        health.update(status="connected", connected_since=time.time(),
                                      last_heartbeat=timezone.now().isoformat(), last_error=None)
                    except Exception as exc:
                        if connection:
                            connection.disconnect()
                        health["last_error"] = str(exc)
                        logger.exception("Broker socket start failed credential=%s", credential_id)
            self.connection_health[credential_id] = health
            try:
                cache.set(f"live_ws_health:{credential_id}",
                          {**health, "updated_at": timezone.now().isoformat()}, timeout=90)
            except Exception:
                logger.exception("Could not publish broker health credential=%s", credential_id)

    def stop_connection(self, credential_id):
        connection = self.connections.pop(credential_id, None)
        if connection:
            connection.disconnect()
        self.connection_health.pop(credential_id, None)
        try:
            cache.delete(f"live_ws_health:{credential_id}")
        except Exception:
            logger.exception("Could not clear broker health credential=%s", credential_id)

    def stop_all(self):
        for credential_id in set(self.connections) | set(self.connection_health):
            self.stop_connection(credential_id)
