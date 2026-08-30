from datetime import date
from .models import Instrument
from common.enums import InstrumentType
class InstrumentResolver:
    """Resolves the actual execution instrument from a signal instrument + route config."""

    @staticmethod
    def execution_instrument_ids(strategy):
        """Return watchlist and routed execution instrument IDs for a strategy."""
        instrument_ids = set()
        for watch in strategy.watchlist_instruments.all():
            if watch.instrument_id:
                instrument_ids.add(watch.instrument_id)
            for route in watch.execution_routes.all():
                if route.target_instrument_id:
                    instrument_ids.add(route.target_instrument_id)
                if route.route_type in {"FUTURES", "OPTIONS"}:
                    underlying = (
                        route.target_underlying_instrument.symbol
                        if route.target_underlying_instrument_id
                        else watch.instrument.symbol
                    )
                    instrument_ids.update(
                        Instrument.objects.filter(
                            instrument_type=InstrumentType.FUTURE if route.route_type == "FUTURES" else InstrumentType.OPTION,
                            underlying_symbol=underlying,
                            is_active=True,
                            is_tradeable=True,
                        ).values_list("id", flat=True)
                    )
        return sorted(instrument_ids)
    
    @staticmethod
    def resolve(watchlist_instrument, signal_side, spot_price=None):
        """
        Returns a list of (execution_instrument, execution_side, route_sizing_dict).
        If no routes → returns the original instrument and side unchanged.
        """
        routes = watchlist_instrument.execution_routes.all()
        if not routes.exists():
            return [(watchlist_instrument.instrument, signal_side, None)]
            
        results = []
        for route in routes:
            sizing = route.get_sizing_dict()
            
            def _enforce(sz, inst):
                if sz and sz.get("sizing_method") == "FIXED" and sz.get("fixed_quantity"):
                    lot = inst.lot_size or 1
                    sz["fixed_quantity"] = max(lot, round(sz["fixed_quantity"] / lot) * lot)
                return sz

            if route.route_type == 'DIRECT':
                results.append((watchlist_instrument.instrument, signal_side, _enforce(sizing, watchlist_instrument.instrument)))
                continue
                
            if route.route_type == 'MANUAL':
                results.append((route.target_instrument, signal_side, _enforce(sizing, route.target_instrument)))
                continue
                
            if route.route_type == 'FUTURES':
                resolved = InstrumentResolver._resolve_futures(route, watchlist_instrument)
                target = resolved or watchlist_instrument.instrument
                results.append((target, signal_side, _enforce(sizing, target)))
                continue
                
            if route.route_type == 'OPTIONS':
                instrument, side = InstrumentResolver._resolve_options(
                    route, watchlist_instrument, signal_side, spot_price
                )
                target = instrument or watchlist_instrument.instrument
                results.append((target, side, _enforce(sizing, target)))
                continue
                
        return results
    
    @staticmethod
    def _get_underlying_symbol(route, watchlist_instrument):
        """Get the underlying symbol for derivative resolution.
        Uses the FK target_underlying_instrument if set, otherwise falls back
        to the watchlist instrument's own symbol."""
        if route.target_underlying_instrument:
            return route.target_underlying_instrument.symbol
        return watchlist_instrument.instrument.symbol

    @staticmethod
    def _filter_by_expiry_preference(qs, preference):
        if not qs.exists():
            return qs
            
        if preference in ['NEAREST', 'WEEKLY']:
            nearest_expiry = qs.values_list('expiry_date', flat=True).first()
            if nearest_expiry:
                return qs.filter(expiry_date=nearest_expiry)
                
        elif preference == 'MONTHLY':
            expiries = list(qs.values_list('expiry_date', flat=True).distinct().order_by('expiry_date'))
            if expiries:
                from collections import defaultdict
                month_map = defaultdict(list)
                for d in expiries:
                    if d: month_map[(d.year, d.month)].append(d)
                
                monthly_expiries = sorted([max(dates) for dates in month_map.values()])
                if monthly_expiries:
                    return qs.filter(expiry_date=monthly_expiries[0])
                    
        return qs
    
    @staticmethod
    def _resolve_futures(route, watchlist_instrument):
        underlying = InstrumentResolver._get_underlying_symbol(route, watchlist_instrument)
        today = date.today()
        expiry_filter = {'expiry_date__gt': today} if getattr(route, 'avoid_same_day_expiry', False) else {'expiry_date__gte': today}
        
        qs = Instrument.objects.filter(
            instrument_type=InstrumentType.FUTURE,
            underlying_symbol=underlying,
            is_active=True,
            **expiry_filter
        ).order_by('expiry_date')
        
        qs = InstrumentResolver._filter_by_expiry_preference(qs, route.expiry_preference)
        return qs.first()
    
    @staticmethod
    def _resolve_options(route, watchlist_instrument, signal_side, spot_price):
        underlying = InstrumentResolver._get_underlying_symbol(route, watchlist_instrument)
        option_type = route.buy_signal_option_type if signal_side == 'BUY' else route.sell_signal_option_type
        today = date.today()
        expiry_filter = {'expiry_date__gt': today} if getattr(route, 'avoid_same_day_expiry', False) else {'expiry_date__gte': today}
        
        qs = Instrument.objects.filter(
            instrument_type=InstrumentType.OPTION,
            underlying_symbol=underlying,
            option_type=option_type,
            is_active=True,
            **expiry_filter
        ).order_by('expiry_date')
        
        qs = InstrumentResolver._filter_by_expiry_preference(qs, route.expiry_preference)
        
        # Resolve strike based on spot price
        if spot_price is not None and qs.exists():
            spot = float(spot_price)
            contracts = list(qs)
            
            # Find closest to spot
            atm_contract = min(contracts, key=lambda c: abs(float(c.strike_price or 0) - spot))
            
            strike_selection = route.strike_selection
            if strike_selection == 'ATM':
                return atm_contract, signal_side
                
            # If ITM or OTM requested
            contracts_sorted = sorted(contracts, key=lambda c: float(c.strike_price or 0))
            atm_index = contracts_sorted.index(atm_contract)
            
            offset = 0
            if 'ITM_1' in strike_selection: offset = -1 if option_type == 'CE' else 1
            elif 'ITM_2' in strike_selection: offset = -2 if option_type == 'CE' else 2
            elif 'ITM_3' in strike_selection: offset = -3 if option_type == 'CE' else 3
            elif 'OTM_1' in strike_selection: offset = 1 if option_type == 'CE' else -1
            elif 'OTM_2' in strike_selection: offset = 2 if option_type == 'CE' else -2
            elif 'OTM_3' in strike_selection: offset = 3 if option_type == 'CE' else -3
            
            target_index = atm_index + offset
            if 0 <= target_index < len(contracts_sorted):
                return contracts_sorted[target_index], signal_side
                
            return atm_contract, signal_side
            
        return qs.first(), signal_side
