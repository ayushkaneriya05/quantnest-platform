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
def request_session_refresh(scope, session, *, close_positions=False):
    account_id = session.account_id if scope == ExecutionMode.PAPER else session.broker_credential_id
    return enqueue(scope, account_id, ExecutionCommandType.REFRESH,
        {'session_id': session.pk, 'close_positions': close_positions})
