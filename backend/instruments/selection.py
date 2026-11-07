"""Deterministic contract selection over a prepared catalog.

Preparation owns database access. PreparedSelector.select performs only indexed
in-memory lookups; it never fetches quotes, discovers contracts or warms history.
"""
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from common.enums import ExpirySelection, StrikeSelection, InstrumentType, OptionType
from strategies.specification.configuration import POLICY_FIELDS


@dataclass(frozen=True, slots=True)
class SelectionPolicy:
    instrument_type: str
    option_type: str
    expiry: str
    expiry_date: date | None
    allow_expiry_day: bool
    strike: str
    distance: int
    strike_price: Decimal | None

    @classmethod
    def parse(cls, value: dict):
        fields = set(POLICY_FIELDS)
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError('Provide the complete contract selection policy.')
        kind = value['instrument_type']
        if kind not in (InstrumentType.FUTURE, InstrumentType.OPTION):
            raise ValueError('Automatic selection supports futures or options.')
        if value['expiry'] not in ExpirySelection.values or value['strike'] not in StrikeSelection.values:
            raise ValueError('Choose a supported expiry and strike selection method.')
        if type(value['allow_expiry_day']) is not bool:
            raise ValueError('allow_expiry_day must be true or false.')
        if type(value['distance']) is not int or not POLICY_FIELDS['distance']['min'] <= value['distance'] <= POLICY_FIELDS['distance']['max']:
            raise ValueError(f'Strike distance must be an integer from {POLICY_FIELDS["distance"]["min"]} to {POLICY_FIELDS["distance"]["max"]}.')
        expiry = None
        if value['expiry'] == ExpirySelection.FIXED:
            if not isinstance(value['expiry_date'], str):
                raise ValueError('Choose a listed expiry date.')
            expiry = date.fromisoformat(value['expiry_date'])
        elif value['expiry_date'] is not None:
            raise ValueError('Only a specific expiry uses expiry_date.')
        price = None
        if value['strike'] == StrikeSelection.FIXED:
            try:
                price = Decimal(value['strike_price']) if isinstance(value['strike_price'], str) else None
            except InvalidOperation:
                price = None
            if price is None or not price.is_finite() or price <= 0:
                raise ValueError('Specific strike must be a positive decimal string.')
        elif value['strike_price'] is not None:
            raise ValueError('Only a specific strike uses strike_price.')
        relative = value['strike'] in (StrikeSelection.ITM, StrikeSelection.OTM)
        if relative != (value['distance'] > 0):
            raise ValueError('ITM/OTM requires a positive distance; other choices use zero.')
        if kind == InstrumentType.OPTION:
            if value['option_type'] not in OptionType.values:
                raise ValueError('Choose Call or Put for an option route.')
        elif value['option_type'] != '' or value['strike'] != StrikeSelection.ATM:
            raise ValueError('Futures do not use an option right or strike selection.')
        return cls(kind, value['option_type'], value['expiry'], expiry,
                   value['allow_expiry_day'], value['strike'], value['distance'], price)


@dataclass(frozen=True, slots=True)
class Candidate:
    instrument_id: int
    expiry: date
    strike: Decimal | None


class PreparedSelector:
    """One family/right/underlying, grouped and sorted once at preparation.

    ATM ties choose the lower listed strike. ITM/OTM distances are listed-grid
    steps from that anchor. A missing requested strike never picks a substitute.
    """
    def __init__(self, policy: SelectionPolicy, candidates: tuple[Candidate, ...]):
        self.policy = policy
        groups = {}
        for candidate in candidates:
            strike = candidate.strike if policy.instrument_type == InstrumentType.OPTION else Decimal(0)
            if strike is None or not strike.is_finite() or strike < 0 or (
                    policy.instrument_type == InstrumentType.OPTION and strike == 0):
                raise ValueError('Option candidates need a positive qualified strike.')
            group = groups.setdefault(candidate.expiry, {})
            if strike in group:
                raise ValueError('Ambiguous contract identity for the same expiry and strike.')
            group[strike] = candidate
        self.expiries = tuple(sorted(groups))
        self.grids = {expiry: tuple(sorted(group)) for expiry, group in groups.items()}
        self.contracts = groups

    def select(self, spot: Decimal, session_day: date) -> Candidate:
        policy = self.policy
        first = (bisect_left if policy.allow_expiry_day else bisect_right)(self.expiries, session_day)
        if policy.expiry == ExpirySelection.FIXED:
            expiry = policy.expiry_date
            if expiry not in self.contracts or expiry < session_day or (expiry == session_day and not policy.allow_expiry_day):
                raise ValueError('The requested expiry is not eligible in this catalog.')
        else:
            index = first + (policy.expiry == ExpirySelection.NEXT)
            if index >= len(self.expiries):
                raise ValueError('The requested eligible expiry is unavailable.')
            expiry = self.expiries[index]
        grid = self.grids[expiry]
        if policy.instrument_type == InstrumentType.FUTURE:
            return self.contracts[expiry][grid[0]]
        if policy.strike == StrikeSelection.FIXED:
            if policy.strike_price not in self.contracts[expiry]:
                raise ValueError('The requested strike is not listed for this expiry and right.')
            return self.contracts[expiry][policy.strike_price]
        if not spot.is_finite() or spot <= 0:
            raise ValueError('ATM/ITM/OTM needs a positive underlying price.')
        index = bisect_left(grid, spot)
        if index == len(grid) or index > 0 and spot-grid[index-1] <= grid[index]-spot:
            index -= 1
        if policy.distance:
            direction = 1 if policy.option_type == OptionType.CE else -1
            index += direction * policy.distance * (1 if policy.strike == StrikeSelection.OTM else -1)
        if not 0 <= index < len(grid):
            raise ValueError('The requested strike distance is outside the eligible listed grid.')
        return self.contracts[expiry][grid[index]]

    def warmup_candidates(self, spot: Decimal, session_day: date) -> set[int]:
        """Cold history demand: exact selection plus one listed neighbour each side.

        The complete catalog still owns selection. Nearby history reduces a
        normal strike transition's warmup; a larger jump waits for its own data.
        Owned contracts are added separately, independently of the current ATM.
        """
        selected = self.select(spot, session_day)
        if self.policy.instrument_type == InstrumentType.FUTURE or self.policy.strike == StrikeSelection.FIXED:
            return {selected.instrument_id}
        grid = self.grids[selected.expiry]
        index = bisect_left(grid, selected.strike)
        return {self.contracts[selected.expiry][strike].instrument_id
                for strike in grid[max(0, index-1):index+2]}


def prepare_current_selector(underlying, policy, *, allow_empty=False):
    """Prepare current Paper/Live candidates; historical discovery is separate.

    Exact underlying tokens avoid matching a similarly named contract on another
    exchange. Never parse derivative symbols or truncate a grid before selection.
    """
    from common.enums import Exchange, FyersSegment
    from .models import Instrument
    from django.utils import timezone
    if underlying.exchange not in (Exchange.NSE, Exchange.BSE) or underlying.instrument_type not in (InstrumentType.STOCK, InstrumentType.INDEX):
        raise ValueError('Select an NSE/BSE stock or index underlying.')
    if not underlying.fy_token or underlying.fy_token == '0':
        raise ValueError('The underlying needs a qualified provider identity before selecting contracts.')
    rows = Instrument.objects.filter(exchange=underlying.exchange, segment=FyersSegment.EQUITY_DERIVATIVES,
        underlying_fy_token=underlying.fy_token, instrument_type=policy.instrument_type)
    rows = rows.filter(is_active=True, is_tradeable=True, expiry_date__gte=timezone.localdate())
    if policy.instrument_type == InstrumentType.OPTION:
        rows = rows.filter(option_type=policy.option_type)
    if policy.expiry == ExpirySelection.FIXED:
        rows = rows.filter(expiry_date=policy.expiry_date)
    instruments = {row.pk: row for row in rows}
    if not instruments and not allow_empty:
        raise ValueError('No qualified contracts are linked to this underlying. Sync the instrument catalog first.')
    candidates = tuple(Candidate(row.pk, row.expiry_date, row.strike_price) for row in instruments.values())
    if policy.expiry == ExpirySelection.FIXED:
        candidates = tuple(row for row in candidates if row.expiry == policy.expiry_date)
    else:
        day = timezone.localdate()
        dates = sorted({row.expiry for row in candidates if row.expiry > day or policy.allow_expiry_day and row.expiry == day})
        dates = dates[:2 if policy.expiry == ExpirySelection.NEXT else 1]
        candidates = tuple(row for row in candidates if row.expiry in dates)
    if (policy.instrument_type == InstrumentType.OPTION and policy.strike == StrikeSelection.FIXED
            and policy.expiry in (ExpirySelection.FIXED, ExpirySelection.NEAREST)):
        # Exact-strike selection never needs history for unrelated strikes.
        # Only prune after selecting one expiry: removing an expiry whose strike
        # is absent must not turn NEXT into a different date.
        candidates = tuple(row for row in candidates if row.strike == policy.strike_price)
    # Expiry filtering does not change the strike grid. Candidate preparation is
    # refreshed at the next session; expired owned contracts remain pinned.
    instruments = {row.instrument_id: instruments[row.instrument_id] for row in candidates}
    if not candidates and not allow_empty:
        raise ValueError('No eligible contracts for the requested expiry policy.')
    return PreparedSelector(policy, candidates), instruments
