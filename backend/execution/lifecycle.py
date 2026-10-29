"""Admission and requested configuration. The owner confirms application later."""
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from common.enums import ExecutionCommandType, ExecutionMode
from .repository import enqueue


def require_execution_scope(scope):
    if scope not in settings.EXECUTION_ENABLED_SCOPES:
        raise PermissionDenied({'code': 'execution_scope_disabled',
            'message': 'This execution scope is disabled in this installation.', 'scope': scope})


@transaction.atomic
def request_session_refresh(scope, session, *, close_positions=None):
    account_id = session.account_id if scope == ExecutionMode.PAPER else session.broker_credential_id
    payload = {'session_id': session.pk}
    # A version/capital refresh must not revoke an outstanding stop-and-close.
    if close_positions is not None:
        payload['close_positions'] = close_positions
    return enqueue(scope, account_id, ExecutionCommandType.REFRESH, payload)
