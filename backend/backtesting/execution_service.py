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
    def execute_market_order(
        context,  # BacktestContext
        instrument,
        side,
        quantity,
        price,
        timestamp,
        strategy_config,
        exit_reason="strategy_entry",
        slippage_pct=0.0,
    ):
        """
        Execute market order in backtest context.
        Mirrors PaperExecutionService._execute_market_order()
        """
        from common.costs import TradingCostCalculator
        from common.enums import Side, OrderType

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
                strategy_config,
                exit_reason=exit_reason,
                slippage_pct=slippage_pct,
            )
            quantity -= closing_qty

            if position_closed:
                context.remove_position(instrument.id)

        # 2. Open new position if remaining quantity
        if quantity > 0:
            BacktestExecutionService._open_position(
                context,
                instrument,
                side,
                quantity,
                price,
                timestamp,
                strategy_config,
                slippage_pct=slippage_pct,
            )
    
    @staticmethod
    def _apply_fill_to_position(
        context,
        position,
        fill_quantity,
        fill_price,
        timestamp,
        strategy_config,
        exit_reason="strategy_exit",
        slippage_pct=0.0,
    ):
        """
        Apply fill to position in backtest context.
        Mirrors PaperExecutionService._apply_fill_to_position()
        """
        from common.costs import TradingCostCalculator
        from common.enums import Side

        entry_price = position['avg_price']
        side = position['side']

        # Apply slippage
        if slippage_pct > 0:
            exit_side = Side.SELL if side == Side.BUY else Side.BUY
            fill_price = float(TradingCostCalculator.apply_slippage(fill_price, exit_side, slippage_pct))

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

        # Update risk metrics
        risk_metrics = context.get_risk_metrics()
        pnl = float(net_pnl)
        risk_metrics['daily_trades'] += 1
        risk_metrics['daily_pnl'] += pnl
        risk_metrics['weekly_pnl'] += pnl
        risk_metrics['monthly_pnl'] += pnl
        risk_metrics['total_closed_trades'] += 1

        if pnl < 0:
            risk_metrics['consecutive_losses'] += 1
            risk_metrics['consecutive_wins'] = 0
            risk_metrics['losing_trades'] += 1
        elif pnl > 0:
            risk_metrics['consecutive_wins'] += 1
            risk_metrics['consecutive_losses'] = 0
            risk_metrics['winning_trades'] += 1

        total_closed = risk_metrics['total_closed_trades']
        wins = risk_metrics['winning_trades']
        risk_metrics['win_rate'] = (wins / total_closed) * 100 if total_closed else 0.0

        context.update_risk_metrics(risk_metrics)

        # Create trade record (saved to DB after backtest)
        trade_data = {
            'instrument': position.get('instrument'),
            'side': side,
            'entry_time': position['entry_time'],
            'exit_time': timestamp,
            'entry_price': entry_price,
            'exit_price': fill_price,
            'quantity': fill_quantity,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'charges_json': charges,
            'exit_reason': exit_reason,
            'mae': position.get('max_loss', 0),
            'mfe': position.get('max_profit', 0),
        }
        context.closed_trades.append(trade_data)

        # Update position quantity
        position['quantity'] -= fill_quantity
        if position['quantity'] <= 0:
            position['quantity'] = 0
            # If position is fully closed, return True to signal removal
            return True
        return False
    
    @staticmethod
    def _open_position(
        context,
        instrument,
        side,
        quantity,
        price,
        timestamp,
        strategy_config,
        slippage_pct=0.0,
    ):
        """
        Open new position in backtest context.
        Mirrors paper trading position creation.
        """
        from rules_engine.utils import derive_protection_levels
        from common.costs import TradingCostCalculator

        # Apply slippage
        if slippage_pct > 0:
            price = float(TradingCostCalculator.apply_slippage(price, side, slippage_pct))

        protection = derive_protection_levels(strategy_config, side, price)

        position = {
            'instrument': instrument,
            'instrument_id': instrument.id,
            'instrument_type': getattr(instrument, 'instrument_type', 'EQUITY'),
            'side': side,
            'quantity': quantity,
            'avg_price': price,
            'current_price': price,
            'entry_time': timestamp,
            'protected_stop_price': protection.get('protected_stop_price'),
            'protected_target_price': protection.get('protected_target_price'),
            'peak_price': price,
            'trailing_stop': None,
            'trailing_target': None,
            'max_profit': 0.0,
            'max_loss': 0.0,
        }

        context.update_position(instrument.id, position)
