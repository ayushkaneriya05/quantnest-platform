"""Admission and requested configuration. The owner confirms application later."""
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from common.enums import ExecutionCommandType, ExecutionMode, ExecutionSessionStatus
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


def request_catalog_refresh():
    """A completed master sync refreshes running deployments off the tick path."""
    from paper_trading.models import PaperTradingSession
    from live_trading.models import TradingSession
    from .models import Command
    for scope, model, owner in ((ExecutionMode.PAPER, PaperTradingSession, 'account_id'),
                                (ExecutionMode.LIVE, TradingSession, 'broker_credential_id')):
        if scope not in settings.EXECUTION_ENABLED_SCOPES:
            continue
        accounts = set(model.objects.exclude(status=ExecutionSessionStatus.STOPPED).values_list(owner, flat=True))
        pending = set(Command.objects.filter(mode=scope, kind=ExecutionCommandType.REFRESH,
            applied_at__isnull=True).values_list('account_id', flat=True))
        for account in accounts - pending:
            enqueue(scope, account, ExecutionCommandType.REFRESH, {})
