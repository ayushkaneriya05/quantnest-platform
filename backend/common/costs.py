"""Unified Trading Cost Calculator for the QuantNest platform.

Provides accurate simulation of Indian market trading costs including
brokerage, STT, exchange charges, SEBI fees, stamp duty, and GST.
Used by backtesting, paper trading and the simulated Terminal.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Tuple
from datetime import datetime
from django.utils import timezone

from common.enums import FyersSegment, ProductType, Side, InstrumentType

CHARGE_PROFILE_FIELDS = (
    "brokerage_per_order",
    "brokerage_pct",
    "brokerage_cap",
    "stt_eq_delivery_pct",
    "stt_eq_intraday_pct",
    "stt_futures_pct",
    "stt_options_sell_pct",
    "ctt_futures_sell_pct",
    "ctt_options_sell_pct",
    "exchange_txn_pct",
    "exchange_txn_fo_pct",
    "sebi_turnover_pct",
    "stamp_duty_pct",
    "gst_pct",
)


def snapshot_charge_profile(profile):
    if not profile:
        return {"resolved": True}
    return {
        "name": profile.name,
        **{field: str(getattr(profile, field)) for field in CHARGE_PROFILE_FIELDS},
    }


def get_charges_breakdown(charge_records):
    """Combine stored entry/exit charges for one trade or a report."""
    totals = dict.fromkeys(('brokerage', 'stt', 'exchange_txn', 'sebi', 'stamp_duty', 'gst', 'total'), 0.0)
    for charges in charge_records:
        charges = charges or {}
        totals['total'] += float(charges.get('total_charges', 0) or 0)
        for leg_name in ('entry_charges', 'exit_charges'):
            leg = charges.get(leg_name) or {}
            totals['brokerage'] += float(leg.get('brokerage', 0) or 0)
            totals['stt'] += float(leg.get('stt', 0) or 0)
            totals['exchange_txn'] += float(leg.get('exchange_charges', 0) or 0)
            totals['sebi'] += float(leg.get('sebi_fee', 0) or 0)
            totals['stamp_duty'] += float(leg.get('stamp_duty', 0) or 0)
            totals['gst'] += float(leg.get('gst', 0) or 0)
    return {key: round(value, 2) for key, value in totals.items()}


class TradingCostCalculator:
    """Calculates realistic trading costs for Indian markets.
    
    Uses an immutable charge-profile snapshot dictionary to compute all components:
    - Brokerage (flat + percentage, capped)
    - STT / configured commodity CTT, selected by segment
    - Exchange Transaction Charges
    - SEBI Turnover Fees
    - Stamp Duty
    - GST on brokerage + exchange charges
    """
    
    @staticmethod
    def get_tax_classification(entry_time: datetime, exit_time: datetime) -> str:
        """Use actual trade dates in the application's timezone, never the order product."""
        return (ProductType.INTRADAY if timezone.localdate(entry_time) == timezone.localdate(exit_time)
                else ProductType.CNC)

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
        profile: dict,
        *, segment: int = FyersSegment.CAPITAL_MARKET,
    ) -> Decimal:
        """Calculate the configured segment tax: STT, commodity CTT, or zero for currency."""
        if segment == FyersSegment.CURRENCY_DERIVATIVES:
            return Decimal('0')
        if segment == FyersSegment.COMMODITY_DERIVATIVES:
            if side != Side.SELL:
                return Decimal('0')
            field = 'ctt_options_sell_pct' if instrument_type == InstrumentType.OPTION else 'ctt_futures_sell_pct'
            pct = Decimal(profile.get(field, '0'))
        elif instrument_type == InstrumentType.STOCK:
            if tax_classification == ProductType.CNC:
                pct = Decimal(profile['stt_eq_delivery_pct'])
            else:  # ProductType.INTRADAY
                if side == Side.SELL:
                    pct = Decimal(profile['stt_eq_intraday_pct'])
                else:
                    return Decimal('0')
        elif instrument_type == InstrumentType.FUTURE:
            if side == Side.SELL:
                pct = Decimal(profile['stt_futures_pct'])
            else:
                return Decimal('0')
        elif instrument_type == InstrumentType.OPTION:
            if side == Side.SELL:
                pct = Decimal(profile['stt_options_sell_pct'])
            else:
                return Decimal('0')
        else:
            return Decimal('0')
        
        return (turnover * pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_exchange_charges(
        turnover: Decimal,
        instrument_type: str,
        profile: dict,
    ) -> Decimal:
        """Calculate exchange transaction charges."""
        if instrument_type in (InstrumentType.FUTURE, InstrumentType.OPTION):
            pct = Decimal(profile['exchange_txn_fo_pct'])
        else:
            pct = Decimal(profile['exchange_txn_pct'])
        
        return (turnover * pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_sebi_fee(turnover: Decimal, profile: dict) -> Decimal:
        """Calculate SEBI turnover fee."""
        pct = Decimal(profile['sebi_turnover_pct'])
        return (turnover * pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_stamp_duty(
        turnover: Decimal,
        side: str,
        profile: dict,
    ) -> Decimal:
        """Calculate stamp duty (charged only on buy side)."""
        if side != Side.BUY:
            return Decimal('0')
        pct = Decimal(profile['stamp_duty_pct'])
        return (turnover * pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_gst(
        brokerage: Decimal,
        exchange_charges: Decimal,
        sebi_fee: Decimal,
        profile: dict,
    ) -> Decimal:
        """Calculate GST on brokerage + exchange charges + SEBI fee."""
        taxable = brokerage + exchange_charges + sebi_fee
        gst_pct = Decimal(profile['gst_pct'])
        return (taxable * gst_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @classmethod
    def calculate_charges(
        cls,
        turnover: Decimal,
        instrument_type: str,
        tax_classification: str,
        side: str,
        profile: dict,
        include_charges: bool = True,
        *, segment: int = FyersSegment.CAPITAL_MARKET,
    ) -> Dict:
        """Calculate all charges for a single order leg.
        
        Args:
            turnover: Total turnover (price * quantity).
            instrument_type: InstrumentType
            tax_classification: INTRADAY or CNC.
            side: BUY or SELL.
            profile: Saved charge-profile dictionary; decimal rates are strings.
            include_charges: If False, returns zero charges.
        
        Returns:
            Dict with itemized charges and total.
        """
        if not include_charges or 'brokerage_per_order' not in profile:
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
            turnover, Decimal(profile['brokerage_per_order']),
            Decimal(profile['brokerage_pct']), Decimal(profile['brokerage_cap']),
        )
        stt = cls.calculate_stt(turnover, instrument_type, tax_classification, side, profile, segment=segment)
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
        entry_time: datetime,
        exit_time: datetime,
        profile: dict,
        include_charges: bool = True,
        *, segment: int = FyersSegment.CAPITAL_MARKET,
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
            profile: Saved charge-profile dictionary.
            include_charges: If False, returns zero charges.
        
        Returns:
            Dict with entry_charges, exit_charges, and total_charges.
        """
        entry_turnover = Decimal(str(entry_price)) * Decimal(str(quantity))
        exit_turnover = Decimal(str(exit_price)) * Decimal(str(quantity))
        
        exit_side = Side.BUY if side == Side.SELL else Side.SELL
        
        tax_classification = cls.get_tax_classification(entry_time, exit_time)
        
        entry_charges = cls.calculate_charges(
            entry_turnover, instrument_type, tax_classification, side, profile, include_charges, segment=segment
        )
        exit_charges = cls.calculate_charges(
            exit_turnover, instrument_type, tax_classification, exit_side, profile, include_charges, segment=segment
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
        instrument_type: str,
        entry_time: datetime,
        exit_time: datetime,
        profile: dict,
        include_charges: bool = True,
        *, segment: int = FyersSegment.CAPITAL_MARKET,
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
            profile: Saved charge-profile dictionary; an empty/resolved-only snapshot has no charges.
            include_charges: If False, returns gross_pnl unchanged.
        
        Returns:
            Tuple of (net_pnl, charges_breakdown_dict).
        """
        charges = cls.calculate_trade_charges(
            entry_price, exit_price, quantity, side,
            instrument_type, entry_time, exit_time, profile, include_charges, segment=segment,
        )
        
        gross_pnl = Decimal(str(gross_pnl))
        total_charges = Decimal(str(charges['total_charges']))
        net_pnl = (gross_pnl - total_charges).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return net_pnl, charges
