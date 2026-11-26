"""FYERS Standard simulation rates, checked against primary sources on 2026-11-25.

All rates below are percentages, not fractions. NSE rates exclude the separately
listed IPFT contribution. Keep this table at the configuration boundary: fills
resolve a saved dictionary without a database or provider call.

Sources:
https://fyers.in/pricing
https://fyers.in/charges-list (Equity, Currency and Commodity tabs)
https://nsearchives.nseindia.com/content/circulars/FA73061.pdf (2026-03-01)
https://nsearchives.nseindia.com/content/circulars/FATAX73524.pdf (2026-04-01)
https://www.nseindia.com/static/invest/first-time-investor-sebi-turnover-fees-stt-other-levies
https://www.mcxccl.com/clearing-settlement/commodities-transaction-tax

These are ordinary exchange-traded round-trip estimates, not a contract note.
DP debits, physical delivery/exercise, penalties and funding interest need their
own account events. BSE cash uses the published standard rate; special scrip
groups and exempt agricultural contracts require a tailored profile.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from common.enums import Exchange, FyersSegment, InstrumentType, ProductType


RATE_LABELS = {
    'brokerage_per_order': 'Brokerage per order (₹)',
    'brokerage_pct': 'Brokerage (%)',
    'brokerage_cap': 'Brokerage cap per order (₹)',
    'stt_eq_delivery_pct': 'Stock delivery STT, both sides (%)',
    'stt_eq_intraday_pct': 'Stock intraday STT, sell only (%)',
    'stt_futures_pct': 'Equity futures STT, sell only (%)',
    'stt_options_sell_pct': 'Equity options STT on sold premium (%)',
    'ctt_futures_sell_pct': 'Non-agricultural futures CTT, sell only (%)',
    'ctt_options_sell_pct': 'Commodity options CTT on sold premium (%)',
    'exchange_txn_pct': 'Exchange transaction fee (%)',
    'exchange_txn_fo_pct': 'Fallback derivatives exchange fee (%)',
    'sebi_turnover_pct': 'SEBI turnover fee (%)',
    'stamp_duty_pct': 'Buy-side stamp duty (%)',
    'gst_pct': 'GST on taxable fees (%)',
    'brokerage_delivery_pct': 'Delivery brokerage (%)',
    'stamp_delivery_pct': 'Buy-side delivery stamp duty (%)',
    'clearing_pct': 'Clearing fee (%)',
    'ipft_pct': 'IPFT contribution (%)',
}

# An override changes only these fields; shared taxes, caps and flat brokerage
# remain editable once on the profile. Zero percentage means flat brokerage.
MARKET_RATE_DEFAULTS = {
    'nse_cash': {'exchange_txn_pct': '0.0030699', 'ipft_pct': '0.0000001',
                 'brokerage_delivery_pct': '0.3', 'stamp_delivery_pct': '0.015'},
    'bse_cash': {'exchange_txn_pct': '0.00375',
                 'brokerage_delivery_pct': '0.3', 'stamp_delivery_pct': '0.015'},
    'nse_futures': {'exchange_txn_pct': '0.0018299', 'ipft_pct': '0.0000001',
                    'clearing_pct': '0.0005', 'stamp_duty_pct': '0.002'},
    'nse_options': {'exchange_txn_pct': '0.0355299', 'ipft_pct': '0.0000001',
                    'clearing_pct': '0.009', 'brokerage_pct': '0', 'stamp_duty_pct': '0.003'},
    'bse_futures': {'exchange_txn_pct': '0', 'clearing_pct': '0.0005', 'stamp_duty_pct': '0.002'},
    'bse_options': {'exchange_txn_pct': '0.005', 'clearing_pct': '0.009',
                    'brokerage_pct': '0', 'stamp_duty_pct': '0.003'},
    'bse_sensex_options': {'exchange_txn_pct': '0.0325', 'clearing_pct': '0.009',
                           'brokerage_pct': '0', 'stamp_duty_pct': '0.003'},
    'bse_bankex_options': {'exchange_txn_pct': '0.0325', 'clearing_pct': '0.009',
                           'brokerage_pct': '0', 'stamp_duty_pct': '0.003'},
    'nse_currency_futures': {'exchange_txn_pct': '0.00035', 'ipft_pct': '0.00005',
                             'clearing_pct': '0.0005', 'stamp_duty_pct': '0.0001'},
    'nse_currency_options': {'exchange_txn_pct': '0.0311', 'ipft_pct': '0.002',
                             'clearing_pct': '0.009', 'brokerage_pct': '0', 'stamp_duty_pct': '0.0001'},
    'bse_currency_futures': {'exchange_txn_pct': '0.00045',
                             'clearing_pct': '0.0005', 'stamp_duty_pct': '0.0001'},
    'bse_currency_options': {'exchange_txn_pct': '0.001',
                             'clearing_pct': '0.0005', 'brokerage_pct': '0', 'stamp_duty_pct': '0.0001'},
    'nse_commodity_futures': {'exchange_txn_pct': '0.0001',
                              'clearing_pct': '0.0018', 'stamp_duty_pct': '0.002'},
    'nse_commodity_options': {'exchange_txn_pct': '0.001',
                              'clearing_pct': '0.05', 'brokerage_pct': '0', 'stamp_duty_pct': '0.003'},
    'mcx_commodity_futures': {'exchange_txn_pct': '0.0021',
                              'clearing_pct': '0.0018', 'stamp_duty_pct': '0.002'},
    'mcx_commodity_options': {'exchange_txn_pct': '0.0418',
                              'clearing_pct': '0.05', 'brokerage_pct': '0', 'stamp_duty_pct': '0.003'},
}

MARKET_LABELS = {
    'nse_cash': 'NSE stocks', 'bse_cash': 'BSE stocks · standard scrip groups',
    'nse_futures': 'NSE equity futures', 'nse_options': 'NSE equity options',
    'bse_futures': 'BSE equity futures', 'bse_options': 'BSE stock / Sensex 50 options',
    'bse_sensex_options': 'BSE Sensex options', 'bse_bankex_options': 'BSE Bankex options',
    'nse_currency_futures': 'NSE currency futures', 'nse_currency_options': 'NSE currency options',
    'bse_currency_futures': 'BSE currency futures', 'bse_currency_options': 'BSE currency options',
    'nse_commodity_futures': 'NSE non-agricultural futures',
    'nse_commodity_options': 'NSE commodity options',
    'mcx_commodity_futures': 'MCX non-agricultural futures',
    'mcx_commodity_options': 'MCX commodity options',
}


def default_market_rates():
    """Each newly created profile owns an independent, editable rate table."""
    return deepcopy(MARKET_RATE_DEFAULTS)


def validate_market_rates(value):
    if not isinstance(value, dict) or value.keys() - MARKET_LABELS.keys():
        raise ValidationError('Use the supported market keys for market rates.')
    for market, rates in value.items():
        if not isinstance(rates, dict) or rates.keys() - RATE_LABELS.keys():
            raise ValidationError(f'{market}: unknown charge field.')
        for field, raw in rates.items():
            try:
                amount = Decimal(str(raw))
            except (InvalidOperation, ValueError):
                raise ValidationError(f'{market}: {field} must be a decimal number.') from None
            maximum = Decimal('1000000') if field in ('brokerage_per_order', 'brokerage_cap') else Decimal('100')
            if isinstance(raw, bool) or not amount.is_finite() or not 0 <= amount <= maximum:
                raise ValidationError(f'{market}: {field} must be between 0 and {maximum}.')


def resolve_charge_rates(profile, instrument_type, classification, segment, exchange, symbol):
    """Select one market row before calculating fees, including cash holding period.

    Older immutable fill snapshots have no market table and retain their saved
    calculation rates. Never replace those snapshots with today's defaults.
    """
    rates = dict(profile)
    derivative = instrument_type in (InstrumentType.FUTURE, InstrumentType.OPTION)
    if derivative:
        rates['exchange_txn_pct'] = profile.get('exchange_txn_fo_pct', '0')
    suffix = 'options' if instrument_type == InstrumentType.OPTION else 'futures'
    if segment == FyersSegment.CURRENCY_DERIVATIVES:
        market = f'{exchange.lower()}_currency_{suffix}'
    elif segment == FyersSegment.COMMODITY_DERIVATIVES:
        market = f'{exchange.lower()}_commodity_{suffix}'
    elif derivative:
        market = f'{exchange.lower()}_{suffix}'
        if exchange == Exchange.BSE and instrument_type == InstrumentType.OPTION:
            # Exact contract roots: SENSEX50 must not match the SENSEX rate.
            root = symbol.split(':')[-1]
            for name in ('SENSEX', 'BANKEX'):
                if root.startswith(name) and not root.startswith('SENSEX50'):
                    market = f'bse_{name.lower()}_options'
                    break
    else:
        market = f'{exchange.lower()}_cash'
    rates.update({key: str(value) for key, value in profile.get('market_rates', {}).get(market, {}).items()})
    if not derivative and classification == ProductType.CNC:
        rates['brokerage_pct'] = rates.get('brokerage_delivery_pct', rates.get('brokerage_pct', '0'))
        rates['stamp_duty_pct'] = rates.get('stamp_delivery_pct', rates.get('stamp_duty_pct', '0'))
    return rates
