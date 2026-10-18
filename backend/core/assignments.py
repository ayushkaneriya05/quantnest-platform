"""Publish execution ownership within the session lifecycle transaction."""
from django.conf import settings
from django.db import connection, transaction
from django.db.models import Count
from common.models import RuntimeAssignment
from quantnest_runtime.ownership import partition


@transaction.atomic
def synchronize(scope, session_id):
    from live_trading.models import TradingSession
    from paper_trading.models import PaperTradingSession
    from instruments.services import InstrumentResolver
    model = TradingSession if scope == "live" else PaperTradingSession
    session = model.objects.select_related("allocation__deployed_version").filter(pk=session_id).first()
    queryset = RuntimeAssignment.objects.filter(scope=scope, session_id=str(session_id))
    if session is None or session.status == "STOPPED":
        queryset.delete()
        return
    ids = InstrumentResolver.execution_instrument_ids(session)
    if connection.vendor == "postgresql":
        # Serialize cold admission only; evaluations and fills never acquire this lock.
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [716326091])
    current = set(queryset.values_list("instrument_id", flat=True))
    additions = set(ids) - current
    user_id = session.user_id if scope == "live" else session.account.user_id
    if session.status == "RUNNING" and scope not in settings.EXECUTION_ENABLED_SCOPES:
        raise ValueError(f"{scope.title()} execution is not enabled in this deployment")
    if additions:
        if settings.QUANTNEST_DEPLOYMENT_MODE != "private" and RuntimeAssignment.objects.filter(user_id=user_id).count() + len(additions) > settings.EXECUTION_MAX_USER_ACTORS:
            raise ValueError("Execution capacity for this account is full. Stop a session before adding instruments.")
        total = settings.EXECUTION_WORKERS * settings.EXECUTION_NODE_COUNT
        counts = [0] * total
        for row in RuntimeAssignment.objects.values("shard").annotate(total=Count("id")):
            counts[row["shard"] % total] += row["total"]
        for instrument_id in additions:
            owner = partition(f"{scope}:{session_id}:{instrument_id}", settings.EXECUTION_SHARDS) % total
            counts[owner] += 1
            if counts[owner] > settings.EXECUTION_MAX_ACTORS:
                raise ValueError("Execution worker capacity is full. Increase runtime capacity before starting this session.")
    queryset.exclude(instrument_id__in=ids).delete()
    for instrument_id in ids:
        RuntimeAssignment.objects.update_or_create(
            scope=scope, session_id=str(session_id), instrument_id=instrument_id,
            defaults={"user_id": user_id, "shard": partition(f"{scope}:{session_id}:{instrument_id}", settings.EXECUTION_SHARDS)},
        )
