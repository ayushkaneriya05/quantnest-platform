"""
BacktestExecutionService - Backtest execution service mirroring PaperExecutionService.
Uses same logic but operates on BacktestContext instead of DB.
"""

import logging

logger = logging.getLogger(__name__)


class BacktestExecutionService:
    """
    Backtest execution service mirroring PaperExecutionService.
    Uses same logic but operates on BacktestContext instead of DB.
    """
    
    @staticmethod
    def execute_market_order(context, instrument, side, quantity, price, timestamp, strategy_config, exit_reason="strategy_entry", slippage_pct=0.0, execute_immediately=False):
        """
        Execute market order in backtest context.
        If execute_immediately=False, queues order for next candle open.
        Mirrors PaperExecutionService._execute_market_order()
        """
        from common.enums import Side

        if not execute_immediately:
            # Queue order for next candle open
            context.add_pending_order({
                'instrument': instrument,
                'side': side,
                'quantity': quantity,
                'strategy_config': strategy_config,
                'exit_reason': exit_reason,
                'slippage_pct': slippage_pct,
            })
            return

        # 1. Check for opposite position (close existing)
        opposite_side = Side.SELL if side == Side.BUY else Side.BUY
        opposite_position = context.get_position(instrument.id)
        
        if opposite_position and opposite_position['side'] == opposite_side:
            # Close existing position
            closing_qty = min(opposite_position['quantity'], quantity)
            position_closed = BacktestExecutionService._apply_fill_to_position(
                context,
                opposite_position,
                closing_qty,
                price,
                timestamp,
                exit_reason=exit_reason,
                slippage_pct=slippage_pct,
            )
            quantity -= closing_qty

            if position_closed:
                context.remove_position(instrument.id)

        # 2. Open new position if remaining quantity
        if quantity > 0:
            BacktestExecutionService._open_position(context, instrument, side, quantity, price, timestamp, strategy_config, slippage_pct=slippage_pct)
    
    @staticmethod
    def _apply_fill_to_position(context, position, fill_quantity, fill_price, timestamp, exit_reason="strategy_exit", slippage_pct=0.0):
        """
        Apply fill to position in backtest context.
        Mirrors PaperExecutionService._apply_fill_to_position()
        """
        from common.costs import TradingCostCalculator
        from common.enums import Side

        entry_price = position['avg_price']
        side = position['side']

        # Apply slippage and track actual slippage amount
        original_fill_price = fill_price
        if slippage_pct > 0:
            exit_side = Side.SELL if side == Side.BUY else Side.BUY
            fill_price = float(TradingCostCalculator.apply_slippage(fill_price, exit_side, slippage_pct))

        # Calculate actual slippage amount
        slippage_amount = abs(fill_price - original_fill_price) * fill_quantity
        position['capital_used'] = max(
            float(position.get('capital_used', 0.0)) - float(entry_price) * fill_quantity,
            0.0,
        )

        # Calculate PnL
        if side == Side.BUY:
            gross_pnl = (fill_price - entry_price) * fill_quantity
        else:
            gross_pnl = (entry_price - fill_price) * fill_quantity

        # Calculate charges
        profile = context.get_charge_profile()
        include_charges = context.should_include_charges()
        net_pnl, charges = TradingCostCalculator.calculate_net_pnl(
            gross_pnl=gross_pnl,
            entry_price=entry_price,
            exit_price=fill_price,
            quantity=fill_quantity,
            side=side,
            instrument_type=position.get('instrument_type', 'EQUITY'),
            entry_time=position['entry_time'],
            exit_time=timestamp,
            profile=profile,
            include_charges=include_charges,
        )

        # Update context capital
        context.current_capital += float(net_pnl)
        context.record_risk_close(net_pnl, timestamp)

        position['realized_quantity'] = position.get('realized_quantity', 0) + fill_quantity
        position['realized_gross_pnl'] = position.get('realized_gross_pnl', 0.0) + float(gross_pnl)
        position['realized_net_pnl'] = position.get('realized_net_pnl', 0.0) + float(net_pnl)
        position['realized_slippage'] = position.get('realized_slippage', 0.0) + slippage_amount
        position['realized_exit_notional'] = position.get('realized_exit_notional', 0.0) + fill_price * fill_quantity
        position['realized_charges'] = _merge_charges(position.get('realized_charges', {}), charges)
        position['exit_reasons'] = position.get('exit_reasons', []) + [exit_reason]
        position['last_exit_time'] = timestamp

        # Update position quantity
        position['quantity'] -= fill_quantity
        if position['quantity'] <= 0:
            position['quantity'] = 0
            context.closed_trades.append(_position_trade(position, timestamp))
            return True
        return False
    
    @staticmethod
    def _open_position(context, instrument, side, quantity, price, timestamp, strategy_config, slippage_pct=0.0):
        """
        Open new position in backtest context.
        Mirrors paper trading position creation.
        """
        from rules_engine.utils import derive_protection_levels
        from common.costs import TradingCostCalculator

        # Apply slippage and track entry slippage
        original_price = price
        if slippage_pct > 0:
            price = float(TradingCostCalculator.apply_slippage(price, side, slippage_pct))

        # Calculate entry slippage amount
        entry_slippage = abs(price - original_price) * quantity

        protection = derive_protection_levels(strategy_config, side, price)

        position = {
            'instrument': instrument,
            'instrument_type': getattr(instrument, 'instrument_type', 'EQUITY'),
            'side': side,
            'quantity': quantity,
            'avg_price': price,
            'entry_time': timestamp,
            'protected_stop_price': protection.get('protected_stop_price'),
            'protected_target_price': protection.get('protected_target_price'),
            'peak_price': price,
            'max_profit': 0.0,
            'max_loss': 0.0,
            'entry_slippage': entry_slippage,
            'initial_quantity': quantity,
            'capital_used': price * quantity,
            'realized_quantity': 0,
            'realized_gross_pnl': 0.0,
            'realized_net_pnl': 0.0,
            'realized_slippage': 0.0,
            'realized_exit_notional': 0.0,
            'realized_charges': {},
            'exit_reasons': [],
        }

        context.update_position(instrument.id, position)
    
    @staticmethod
    def execute_pending_orders(context, candles_by_instrument, timestamp):
        """
        Execute all pending orders at the current candle open.
        Orders are executed at the OPEN price of the current candle.
        """
        pending_orders = context.get_pending_orders()
        if not pending_orders:
            return

        remaining_orders = []
        committed_capital = sum(float(position.get('capital_used', 0.0)) for position in context.positions.values())
        for order in pending_orders:
            instrument = order['instrument']
            side = order['side']
            quantity = order['quantity']
            slippage_pct = order['slippage_pct']
            strategy_config = order['strategy_config']
            exit_reason = order['exit_reason']

            if exit_reason == "strategy_entry" and not context.can_enter(timestamp):
                context.diagnostics["auto_disable_restrictions"] += 1
                continue

            execution_candle = candles_by_instrument.get(instrument.id)
            if execution_candle is None:
                remaining_orders.append(order)
                continue

            # Execute at OPEN price
            execution_price = float(execution_candle["open"])
            if exit_reason == "strategy_entry" and execution_price * quantity > context.current_capital - committed_capital:
                logger.info(
                    "Backtest entry rejected at fill: instrument=%s required=%.2f available=%.2f",
                    instrument.id, execution_price * quantity, context.current_capital - committed_capital,
                )
                context.diagnostics["capital_rejections"] += 1
                continue
            BacktestExecutionService.execute_market_order(
                context,
                instrument,
                side,
                quantity,
                execution_price,
                timestamp,
                strategy_config,
                exit_reason=exit_reason,
                slippage_pct=slippage_pct,
                execute_immediately=True,
            )
            if exit_reason == "strategy_entry":
                committed_capital += execution_price * quantity
                context.diagnostics["entry_fills"] += 1

        context.pending_orders = remaining_orders

    @staticmethod
    def finalize_open_positions(context):
        """Keep realized partial exits as one record per entry; discard residual exposure."""
        for instrument_id, position in list(context.positions.items()):
            if position.get('realized_quantity', 0) > 0:
                context.closed_trades.append(_position_trade(position, position['last_exit_time']))
            context.remove_position(instrument_id)


def _merge_charges(total, update):
    result = dict(total or {})
    for key, value in (update or {}).items():
        if isinstance(value, dict):
            result[key] = _merge_charges(result.get(key), value)
        elif isinstance(value, (int, float)):
            result[key] = float(result.get(key, 0) or 0) + float(value)
        else:
            result[key] = value
    return result


def _position_trade(position, exit_time):
    quantity = position.get('realized_quantity', 0)
    exit_price = position.get('realized_exit_notional', 0.0) / quantity if quantity else position['avg_price']
    charges = position.get('realized_charges', {})
    entry_slippage = position.get('entry_slippage', 0.0)
    entry_quantity = position.get('initial_quantity', quantity) or quantity
    return {
        'instrument': position.get('instrument'),
        'side': position['side'],
        'entry_time': position['entry_time'],
        'exit_time': exit_time,
        'entry_price': position['avg_price'],
        'exit_price': exit_price,
        'quantity': quantity,
        'gross_pnl': position.get('realized_gross_pnl', 0.0),
        'net_pnl': position.get('realized_net_pnl', 0.0),
        'charges_json': charges,
        'exit_reason': ", ".join(dict.fromkeys(position.get('exit_reasons', []))),
        'mae': position.get('max_loss', 0.0),
        'mfe': position.get('max_profit', 0.0),
        'slippage': entry_slippage * quantity / entry_quantity + position.get('realized_slippage', 0.0),
    }
