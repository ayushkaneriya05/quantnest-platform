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
        from strategy_engine.exit_actions import process_exit_action
        
        decision = process_exit_action(
            action=action,
            params=params,
            position=position,
            reason=reason,
        )
        
        if decision.state_updates:
            context.update_runtime_state(instrument_id, decision.state_updates)
            
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
                reason=decision.reason
            )
            router.publish_order(req)
            
            # Decide if it's a partial exit or full exit phase update
            if decision.quantity < position.get("quantity", 0):
                context.update_runtime_state(instrument_id, {"phase": TradePhase.PARTIAL_EXIT_PENDING})
            else:
                context.update_runtime_state(instrument_id, {"phase": TradePhase.EXIT_PENDING})

    @staticmethod
    def dispatch_entry(context, risk_evaluator, executor, session_id, strategy_id, scope, instrument_id, side, reason, watch_map, spot_price, execution_price_reader):
        """
        Dispatches an entry action, checking sizes and resolving instruments using shared sizing logic.
        """
        watch = watch_map.get(instrument_id)
        if not watch:
            logger.error(f"WatchlistInstrument not found for base instrument {instrument_id}")
            return

        # Pass routes_data from config to avoid DB query in hot path
        routes_data = watch.get('execution_routes', []) if isinstance(watch, dict) else []
        resolutions = InstrumentResolver.resolve(watch, side, spot_price=spot_price, routes_data=routes_data)

        router = StrategyOrderRouter()
        from strategy_engine.sizing import compute_position_size

        # Get strategy config from executor for fallback sizing
        strategy_config = getattr(executor, 'config', {})

        for exec_inst, exec_side, sizing in resolutions:
            # Handle both instrument objects and instrument IDs
            if isinstance(exec_inst, int):
                exec_inst_id = exec_inst
                lot_size = 1  # Default lot size for ID-based resolution
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
                    sl_distance=None,
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
                reason=reason
            )
            router.publish_order(req)
        
        context.update_runtime_state(instrument_id, {"phase": TradePhase.ENTRY_PENDING, "side": side})
