import logging
from common.enums import Side, OrderType, TradePhase
from strategy_engine.router import StrategyOrderRouter, OrderRequest
from instruments.services import InstrumentResolver

logger = logging.getLogger(__name__)

class OrderDispatcher:
    """
    Handles calculating position sizing, resolving related instruments, 
    and generating and publishing OrderRequests.
    """
    
    @staticmethod
    def dispatch_exit(context, session_id, strategy_id, scope, instrument_id, position, action, params, reason):
        """
        Dispatches an exit action based on the evaluated logic using shared exit actions.
        """
        from trading_domain.exit_actions import process_exit_action
        
        decision = process_exit_action(
            action=action,
            params=params,
            position=position,
            reason=reason,
        )
        
        if decision.state_updates:
            context.update_runtime_state(instrument_id, decision.state_updates)
            if not decision.should_send_order:
                publisher = getattr(StrategyOrderRouter(), "_publisher", None)
                if publisher:
                    key, token = context.ownership[instrument_id]
                    publisher(("checkpoint", scope.lower(), session_id, instrument_id,
                               context.get_runtime_state(instrument_id), key, token))
            
        if decision.should_send_order:
            router = StrategyOrderRouter()
            req = OrderRequest(
                session_id=session_id,
                strategy_id=strategy_id,
                instrument_id=position.get("execution_instrument_id") or instrument_id,
                side=Side.SELL if position.get("side") == Side.BUY else Side.BUY,
                qty=decision.quantity,
                order_type=OrderType.MARKET,
                scope=scope,
                target_price=None,
                reason=decision.reason,
                intent="EXIT",
                account_key=getattr(context, "account_key", str(session_id)),
                owner_key=getattr(context, "ownership", {}).get(instrument_id, ("", ""))[0],
                owner_token=getattr(context, "ownership", {}).get(instrument_id, ("", ""))[1],
                entry_time=position.get("entry_time"),
                strategy_version_id=context.deployed_version_id,
                state_updates=decision.state_updates,
            )
            # Decide if it's a partial exit or full exit phase update
            if decision.quantity < position.get("quantity", 0):
                context.update_runtime_state(instrument_id, {"phase": TradePhase.PARTIAL_EXIT_PENDING,
                                                           "pending_request_id": str(req.request_id)})
            else:
                context.update_runtime_state(instrument_id, {"phase": TradePhase.EXIT_PENDING,
                                                           "pending_request_id": str(req.request_id)})
            try:
                router.publish_order(req)
            except Exception:
                logger.exception("Failed to publish exit order for runtime instrument %s", instrument_id)
                raise

    @staticmethod
    def dispatch_entry(context, risk_evaluator, executor, session_id, strategy_id, scope, instrument_id, side, reason, watch_map, execution_price_reader):
        """
        Dispatches an entry action, checking sizes and resolving instruments using shared sizing logic.
        """
        watch = watch_map.get(instrument_id)
        if not watch:
            logger.error(f"WatchlistInstrument not found for base instrument {instrument_id}")
            return

        # Pass routes_data from config to avoid DB query in hot path
        routes_data = watch.get('execution_routes', []) if isinstance(watch, dict) else []
        resolutions = InstrumentResolver.resolve(watch, side, routes_data=routes_data)

        router = StrategyOrderRouter()
        from strategy_engine.sizing import compute_position_size

        # Get strategy config from executor for fallback sizing
        strategy_config = getattr(executor, 'config', {})

        for exec_inst, exec_side, sizing in resolutions:
            # Handle both instrument objects and instrument IDs
            if isinstance(exec_inst, int):
                exec_inst_id = exec_inst
                lot_size = getattr(context, "contracts", {}).get(exec_inst_id, {}).get("lot_size", 1)
            else:
                exec_inst_id = exec_inst.id
                lot_size = getattr(exec_inst, 'lot_size', 1) or 1
            
            exec_price = execution_price_reader(exec_inst_id)
            if exec_price is None:
                logger.error(
                    "No shared-memory price available for execution instrument %s; skipping order",
                    exec_inst_id,
                )
                continue
            try:
                qty = compute_position_size(
                    risk_evaluator=risk_evaluator,
                    sizing_config=sizing,
                    price=exec_price,
                    lot_size=lot_size,
                    strategy_config=strategy_config
                )
            except Exception as e:
                logger.error(f"Sizing error for {exec_inst_id}: {e}")
                qty = 0
            
            # Validate order quantity
            if qty <= 0:
                logger.warning(f"Invalid quantity {qty} for instrument {exec_inst_id}, skipping order")
                continue

            otype, target = executor.resolve_entry_order(exec_price)

            req = OrderRequest(
                session_id=session_id,
                strategy_id=strategy_id,
                instrument_id=exec_inst_id,
                side=exec_side,
                qty=qty,
                order_type=str(otype),
                scope=scope,
                target_price=target,
                reason=reason,
                intent="ENTRY",
                account_key=getattr(context, "account_key", str(session_id)),
                owner_key=getattr(context, "ownership", {}).get(instrument_id, ("", ""))[0],
                owner_token=getattr(context, "ownership", {}).get(instrument_id, ("", ""))[1],
                expires_at=__import__("time").time() + 5,
                strategy_version_id=context.deployed_version_id,
            )
            # Set the phase immediately before publishing
            context.update_runtime_state(instrument_id, {"phase": TradePhase.ENTRY_PENDING, "side": side,
                                                       "pending_request_id": str(req.request_id)})
            try:
                router.publish_order(req)
            except Exception:
                logger.exception("Failed to publish entry order for runtime instrument %s", instrument_id)
                raise
