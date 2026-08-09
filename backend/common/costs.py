"""Unified Trading Cost Calculator for the QuantNest platform.

Provides accurate simulation of Indian market trading costs including
brokerage, STT, exchange charges, SEBI fees, stamp duty, and GST.
Used by both backtesting and paper trading engines.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Tuple
import datetime

from common.enums import ProductType, Side, InstrumentType

logger = logging.getLogger(__name__)


class TradingCostCalculator:
    """Calculates realistic trading costs for Indian markets.
    
    Uses a BrokerChargeProfile to compute all components:
    - Brokerage (flat + percentage, capped)
    - STT (Securities Transaction Tax)
    - Exchange Transaction Charges
    - SEBI Turnover Fees
    - Stamp Duty
    - GST on brokerage + exchange charges
    """
    
    @staticmethod
    def apply_slippage(price: Decimal, side: str, slippage_pct: Decimal) -> Decimal:
        """Apply slippage to a fill price.
        
        For BUY orders: price increases (worse fill).
        For SELL orders: price decreases (worse fill).
        
        Args:
            price: The theoretical fill price.
            side: 'BUY' or 'SELL'.
            slippage_pct: Slippage as a percentage (e.g., 0.05 for 0.05%).
        
        Returns:
            Adjusted fill price with slippage applied.
        """
        price = Decimal(str(price))
        slippage_pct = Decimal(str(slippage_pct))
        
        slippage_amount = price * slippage_pct / Decimal('100')
        
        if side == Side.BUY:
            return (price + slippage_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:  # SELL
            return (price - slippage_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_brokerage(
        turnover: Decimal,
        per_order: Decimal,
        pct: Decimal,
        cap: Decimal,
    ) -> Decimal:
        """Calculate brokerage for a single order leg.

        Indian discount brokers usually charge the lower of a flat per-order
        fee and percentage brokerage, with an optional cap as the hard ceiling.
        """
        pct_brokerage = turnover * Decimal(str(pct)) / Decimal('100')
        flat_brokerage = Decimal(str(per_order))
        cap = Decimal(str(cap))

        candidates = [value for value in (flat_brokerage, pct_brokerage) if value > 0]
        if not candidates:
            brokerage = Decimal('0')
        else:
            brokerage = min(candidates)

        if cap > 0:
            brokerage = min(brokerage, cap)

        return brokerage.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_stt(
        turnover: Decimal,
        instrument_type: str,
        tax_classification: str,
        side: str,
        profile,
    ) -> Decimal:
        """Calculate Securities Transaction Tax."""
        if instrument_type in (InstrumentType.STOCK, InstrumentType.INDEX):
            if tax_classification == ProductType.CNC:
                pct = Decimal(str(profile.stt_eq_delivery_pct))
            else:  # ProductType.INTRADAY
                if side == Side.SELL:
                    pct = Decimal(str(profile.stt_eq_intraday_pct))
                else:
                    return Decimal('0')
        elif instrument_type == InstrumentType.FUTURE:
            if side == Side.SELL:
                pct = Decimal(str(profile.stt_futures_pct))
            else:
                return Decimal('0')
        elif instrument_type == InstrumentType.OPTION:
            if side == Side.SELL:
                pct = Decimal(str(profile.stt_options_sell_pct))
            else:
                return Decimal('0')
        else:
            return Decimal('0')
        
        return (turnover * pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_exchange_charges(
        turnover: Decimal,
        instrument_type: str,
        profile,
    ) -> Decimal:
        """Calculate exchange transaction charges."""
        if instrument_type in (InstrumentType.FUTURE, InstrumentType.OPTION):
            pct = Decimal(str(profile.exchange_txn_fo_pct))
        else:
            pct = Decimal(str(profile.exchange_txn_pct))
        
        return (turnover * pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_sebi_fee(turnover: Decimal, profile) -> Decimal:
        """Calculate SEBI turnover fee."""
        pct = Decimal(str(profile.sebi_turnover_pct))
        return (turnover * pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_stamp_duty(
        turnover: Decimal,
        side: str,
        profile,
    ) -> Decimal:
        """Calculate stamp duty (charged only on buy side)."""
        if side != Side.BUY:
            return Decimal('0')
        pct = Decimal(str(profile.stamp_duty_pct))
        return (turnover * pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_gst(
        brokerage: Decimal,
        exchange_charges: Decimal,
        sebi_fee: Decimal,
        profile,
    ) -> Decimal:
        """Calculate GST on brokerage + exchange charges + SEBI fee."""
        taxable = brokerage + exchange_charges + sebi_fee
        gst_pct = Decimal(str(profile.gst_pct))
        return (taxable * gst_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @classmethod
    def calculate_charges(
        cls,
        turnover: Decimal,
        instrument_type: str,
        tax_classification: str,
        side: str,
        profile,
        include_charges: bool = True,
    ) -> Dict:
        """Calculate all charges for a single order leg.
        
        Args:
            turnover: Total turnover (price * quantity).
            instrument_type: InstrumentType
            tax_classification: INTRADAY or CNC.
            side: BUY or SELL.
            profile: BrokerChargeProfile instance.
            include_charges: If False, returns zero charges.
        
        Returns:
            Dict with itemized charges and total.
        """
        if not include_charges or profile is None:
            return {
                'brokerage': 0,
                'stt': 0,
                'exchange_charges': 0,
                'sebi_fee': 0,
                'stamp_duty': 0,
                'gst': 0,
                'total': 0,
            }
        
        turnover = Decimal(str(turnover))
        
        brokerage = cls.calculate_brokerage(
            turnover, profile.brokerage_per_order,
            profile.brokerage_pct, profile.brokerage_cap,
        )
        stt = cls.calculate_stt(turnover, instrument_type, tax_classification, side, profile)
        exchange_charges = cls.calculate_exchange_charges(turnover, instrument_type, profile)
        sebi_fee = cls.calculate_sebi_fee(turnover, profile)
        stamp_duty = cls.calculate_stamp_duty(turnover, side, profile)
        gst = cls.calculate_gst(brokerage, exchange_charges, sebi_fee, profile)
        
        total = brokerage + stt + exchange_charges + sebi_fee + stamp_duty + gst
        
        return {
            'brokerage': float(brokerage),
            'stt': float(stt),
            'exchange_charges': float(exchange_charges),
            'sebi_fee': float(sebi_fee),
            'stamp_duty': float(stamp_duty),
            'gst': float(gst),
            'total': float(total),
        }
    
    @classmethod
    def calculate_trade_charges(
        cls,
        entry_price: Decimal,
        exit_price: Decimal,
        quantity: int,
        side: str,
        instrument_type: str,
        entry_time,
        exit_time,
        profile,
        include_charges: bool = True,
    ) -> Dict:
        """Calculate complete charges for a round-trip trade (entry + exit).
        
        Args:
            entry_price: Entry fill price.
            exit_price: Exit fill price.
            quantity: Number of shares/lots.
            side: Entry side ('BUY' or 'SELL').
            instrument_type: InstrumentType
            entry_time: Datetime of entry.
            exit_time: Datetime of exit.
            profile: BrokerChargeProfile instance.
            include_charges: If False, returns zero charges.
        
        Returns:
            Dict with entry_charges, exit_charges, and total_charges.
        """
        entry_turnover = Decimal(str(entry_price)) * Decimal(str(quantity))
        exit_turnover = Decimal(str(exit_price)) * Decimal(str(quantity))
        
        exit_side = Side.BUY if side == Side.SELL else Side.SELL
        
        tax_classification = ProductType.INTRADAY if entry_time.date() == exit_time.date() else ProductType.CNC
        
        entry_charges = cls.calculate_charges(
            entry_turnover, instrument_type, tax_classification, side, profile, include_charges
        )
        exit_charges = cls.calculate_charges(
            exit_turnover, instrument_type, tax_classification, exit_side, profile, include_charges
        )
        
        total_charges = entry_charges['total'] + exit_charges['total']
        
        return {
            'entry_charges': entry_charges,
            'exit_charges': exit_charges,
            'total_charges': round(total_charges, 2),
        }
    
    @classmethod
    def calculate_net_pnl(
        cls,
        gross_pnl: Decimal,
        entry_price: Decimal,
        exit_price: Decimal,
        quantity: int,
        side: str,
        instrument_type: InstrumentType = InstrumentType.STOCK,
        entry_time=None,
        exit_time=None,
        profile=None,
        include_charges: bool = True,
    ) -> Tuple[Decimal, Dict]:
        """Calculate net PnL after deducting all trading charges.
        
        Args:
            gross_pnl: Gross profit/loss before charges.
            entry_price: Entry fill price.
            exit_price: Exit fill price.
            quantity: Number of shares/lots.
            side: Entry side ('BUY' or 'SELL').
            instrument_type: InstrumentType
            entry_time: Datetime of entry.
            exit_time: Datetime of exit.
            profile: BrokerChargeProfile instance (None = no charges).
            include_charges: If False, returns gross_pnl unchanged.
        
        Returns:
            Tuple of (net_pnl, charges_breakdown_dict).
        """
        charges = cls.calculate_trade_charges(
            entry_price, exit_price, quantity, side,
            instrument_type, entry_time, exit_time, profile, include_charges,
        )
        
        gross_pnl = Decimal(str(gross_pnl))
        total_charges = Decimal(str(charges['total_charges']))
        net_pnl = (gross_pnl - total_charges).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return net_pnl, charges
