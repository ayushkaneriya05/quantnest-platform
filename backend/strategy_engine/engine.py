
"""Owner-thread decision application. Calculations run separately and cannot place orders."""
from datetime import datetime, timezone
from common.enums import Side, TradePhase
from strategy_engine.dispatcher import OrderDispatcher

PENDING = {TradePhase.ENTRY_PENDING, TradePhase.EXIT_PENDING, TradePhase.PARTIAL_EXIT_PENDING}


def _ownership(actor):
    actor.context.deployed_version_id = actor.version_id
    actor.context.ownership = getattr(actor.context, "ownership", {})
    actor.context.ownership[actor.instrument] = (actor.lease.key, actor.lease.token)


def evaluate_protection(actor, price):
    context = actor.context
    position = context.get_position(actor.instrument)
    if not position or position.get("phase") in PENDING:
        return
    _ownership(actor)
    side = position["side"]
    peak = float(position.get("peak_price") or price)
    context.update_runtime_state(actor.instrument, {
        "current_price": price, "peak_price": max(price, peak) if side == Side.BUY else min(price, peak),
    })
    stop = position.get("protected_stop_price")
    target = position.get("protected_target_price")
    reason = None
    if stop is not None and (price <= float(stop) if side == Side.BUY else price >= float(stop)):
        reason = "Stop Loss Hit"
    elif target is not None and (price >= float(target) if side == Side.BUY else price <= float(target)):
        reason = "Target Hit"
    if reason:
        OrderDispatcher.dispatch_exit(context, actor.session, actor.strategy, actor.scope.upper(),
                                      actor.instrument, position, "EXIT_ALL", {}, reason)
        actor.generation += 1


def apply_calculation(actor, result):
    from risk_management.metrics import metrics_complete
    from risk_management.policy import evaluate_configuration
    context = actor.context
    if result.get("empty"):
        return
    state = context.get_runtime_state(actor.instrument)
    if state.get("phase") in PENDING:
        return
    _ownership(actor)
    position = context.get_position(actor.instrument, config=actor.config)
    should_exit, reason, action, params = result["exit"]
    if position:
        if should_exit:
            OrderDispatcher.dispatch_exit(context, actor.session, actor.strategy, actor.scope.upper(),
                                          actor.instrument, position, action, params, reason)
            actor.generation += 1
        return
    if actor.status != "RUNNING" or actor.gap or not actor.market_ready or not actor.runtime_ready or not actor.account_active or not actor.market.is_tick_fresh():
        return
    risk = context.get_risk_stats()
    capital = context.get_available_capital()
    if capital <= 0 or not metrics_complete(risk):
        return
    evaluator = context.get_risk_evaluator()
    if evaluate_configuration(actor.config, risk, risk.get("risk_capital", capital), datetime.now(timezone.utc))["should_disable"]:
        return
    should_enter, side, reason = result["entry"]
    if should_enter and result["timestamp"] != actor.last_entry_candle:
        executor = actor.program
        now = datetime.now(timezone.utc)
        if executor.is_in_no_trade_zone(now) or not executor.can_enter(state, now)[0]:
            return
        if not actor.calendar.is_trading_day(now.astimezone(actor.calendar.zone).date()):
            return
        local = now.astimezone(actor.calendar.zone)
        if not actor.calendar.session_open(local.date()) <= local < actor.calendar.session_close(local.date()):
            return
        OrderDispatcher.dispatch_entry(
            context, evaluator, executor, actor.session, actor.strategy, actor.scope.upper(),
            actor.instrument, side, reason, actor.watch,
            lambda instrument: actor.market.get_latest_price() if instrument == actor.instrument else None,
        )
        actor.generation += 1
        actor.last_entry_candle = result["timestamp"]
