from datetime import date
from .models import Instrument
from common.enums import InstrumentType
class InstrumentResolver:
    """Resolves the actual execution instrument from a signal instrument + route config."""

    @staticmethod
    def validate_strategy_for_first_release(strategy):
        """Validate that every watchlist instrument uses direct routing."""
        for watch in strategy.watchlist_instruments.all():
            for route in watch.execution_routes.all():
                if route.route_type != "DIRECT":
                    raise ValueError(
                        f"Routing type '{route.route_type}' is disabled. Only DIRECT routing is supported."
                    )
        return True


    @staticmethod
    def execution_instrument_ids(session):
        """Return the deployed watchlist instrument IDs for the active session.
        Execution must always use the strategy version pinned to the active session.
        The config snapshot contains the instruments selected for this deployment.
        """
        candidate = session
        if hasattr(candidate, 'allocation') and candidate.allocation is not None:
            candidate = candidate.allocation
        if not hasattr(candidate, 'deployed_version') or candidate.deployed_version is None:
            raise ValueError("Session has no deployed strategy version configured for execution.")

        config = candidate.deployed_version.config_snapshot or {}
        direct_ids = [item['instrument_id'] for item in config['watchlist_instruments']]
        if not direct_ids:
            raise ValueError("Deployed strategy snapshot is has no watchlist instruments for execution.")
        return sorted({int(item) for item in direct_ids if item is not None})

    
    @staticmethod
    def resolve(watchlist_instrument, signal_side, spot_price=None, routes_data=None):
        """
        Returns a list of (execution_instrument, execution_side, route_sizing_dict).
        If no routes → returns the original instrument and side unchanged.
        
        Args:
            watchlist_instrument: WatchlistInstrument object or dict
            signal_side: Trading side (BUY/SELL)
            spot_price: Current spot price for options resolution
            routes_data: Pre-loaded execution routes (to avoid DB query)
        """
        # Use routes_data if provided, otherwise query DB
        if routes_data is not None:
            routes = routes_data  # Use pre-loaded data
        else:
            # Fallback to DB query (backward compatibility)
            if hasattr(watchlist_instrument, 'execution_routes'):
                routes = watchlist_instrument.execution_routes.all()
            else:
                routes = []
        
        if not routes or (hasattr(routes, 'exists') and not routes.exists()):
            # DIRECT route - return base instrument
            if isinstance(watchlist_instrument, dict):
                # Handle dict format from config
                inst_id = watchlist_instrument.get('instrument_id')
                # Return instrument ID for deferred resolution
                return [(inst_id, signal_side, None)]
            else:
                return [(watchlist_instrument.instrument, signal_side, None)]
            
        results = []
        for route in routes:
            # Handle both model objects and dict format
            if isinstance(route, dict):
                route_type = route.get('route_type')
                sizing = dict(route) if route.get('override_sizing', False) else None
                # target_instrument_id = route.get('target_instrument_id')
            else:
                route_type = route.route_type
                sizing = route.get_sizing_dict()
                # target_instrument_id = route.target_instrument_id

            if route_type != "DIRECT":
                raise ValueError(
                    f"Unsupported routing type '{route_type}'. Only DIRECT routing is enabled."
                )
            
            def _enforce(sz, inst):
                if sz and sz.get("sizing_method") == "FIXED" and sz.get("fixed_quantity"):
                    lot = getattr(inst, 'lot_size', 1) or 1
                    sz["fixed_quantity"] = max(lot, round(sz["fixed_quantity"] / lot) * lot)
                return sz

            if route_type == 'DIRECT':
                if isinstance(watchlist_instrument, dict):
                    inst_id = watchlist_instrument.get('instrument_id')
                    results.append((inst_id, signal_side, _enforce(sizing, watchlist_instrument)))
                else:
                    results.append((watchlist_instrument.instrument, signal_side, _enforce(sizing, watchlist_instrument.instrument)))
                continue
                
            # Non-direct routing is intentionally disabled for the current
            # execution release. The implementation remains below in history
            # for the future routing rollout.
            # if route_type == 'MANUAL':
            #     if isinstance(watchlist_instrument, dict):
            #         results.append((target_instrument_id, signal_side, _enforce(sizing, watchlist_instrument)))
            #     else:
            #         results.append((route.target_instrument, signal_side, _enforce(sizing, route.target_instrument)))
            #     continue

            # if route_type == 'FUTURES':
            #     if isinstance(watchlist_instrument, dict):
            #         raise ValueError("Dynamic FUTURES routing is disabled for first release.")
            #     resolved = InstrumentResolver._resolve_futures(route, watchlist_instrument)
            #     target = resolved or watchlist_instrument.instrument
            #     results.append((target, signal_side, _enforce(sizing, target)))
            #     continue

            # if route_type == 'OPTIONS':
            #     if isinstance(watchlist_instrument, dict):
            #         raise ValueError("Dynamic OPTIONS routing is disabled for first release.")
            #     instrument, side = InstrumentResolver._resolve_options(
            #         route, watchlist_instrument, signal_side, spot_price
            #     )
            #     target = instrument or watchlist_instrument.instrument
            #     results.append((target, side, _enforce(sizing, target)))
            #     continue
                
        return results
    
    # Future MANUAL/FUTURES/OPTIONS helper implementations are intentionally
    # retained but disabled while direct routing is the only supported mode.
    #
    # @staticmethod
    # def _get_underlying_symbol(route, watchlist_instrument):
    #     if route.target_underlying_instrument:
    #         return route.target_underlying_instrument.symbol
    #     return watchlist_instrument.instrument.symbol
    #
    # @staticmethod
    # def _filter_by_expiry_preference(qs, preference):
    #     if not qs.exists():
    #         return qs
                
    #     if preference in ['NEAREST', 'WEEKLY']:
    #         nearest_expiry = qs.values_list('expiry_date', flat=True).first()
    #         if nearest_expiry:
    #             return qs.filter(expiry_date=nearest_expiry)
                
    #     elif preference == 'MONTHLY':
    #         expiries = list(qs.values_list('expiry_date', flat=True).distinct().order_by('expiry_date'))
    #         if expiries:
    #             from collections import defaultdict
    #             month_map = defaultdict(list)
    #             for d in expiries:
    #                 if d: month_map[(d.year, d.month)].append(d)
                
    #             monthly_expiries = sorted([max(dates) for dates in month_map.values()])
    #             if monthly_expiries:
    #                 return qs.filter(expiry_date=monthly_expiries[0])

    #     return qs
    #
    # @staticmethod
    # def _resolve_futures(route, watchlist_instrument):
    #     underlying = InstrumentResolver._get_underlying_symbol(route, watchlist_instrument)
    #     today = date.today()
    #     expiry_filter = {'expiry_date__gt': today} if getattr(route, 'avoid_same_day_expiry', False) else {'expiry_date__gte': today}
    #     qs = Instrument.objects.filter(
    #         instrument_type=InstrumentType.FUTURE,
    #         underlying_symbol=underlying,
    #         is_active=True,
    #         **expiry_filter
    #     ).order_by('expiry_date')
    #     qs = InstrumentResolver._filter_by_expiry_preference(qs, route.expiry_preference)
    #     return qs.first()
    #
    # @staticmethod
    # def _resolve_options(route, watchlist_instrument, signal_side, spot_price):
    #     underlying = InstrumentResolver._get_underlying_symbol(route, watchlist_instrument)
    #     option_type = route.buy_signal_option_type if signal_side == 'BUY' else route.sell_signal_option_type
    #     today = date.today()
    #     expiry_filter = {'expiry_date__gt': today} if getattr(route, 'avoid_same_day_expiry', False) else {'expiry_date__gte': today}
    #     qs = Instrument.objects.filter(
    #         instrument_type=InstrumentType.OPTION,
    #         underlying_symbol=underlying,
    #         option_type=option_type,
    #         is_active=True,
    #         **expiry_filter
    #     ).order_by('expiry_date')
    #     qs = InstrumentResolver._filter_by_expiry_preference(qs, route.expiry_preference)
    #     if spot_price is not None and qs.exists():
    #         spot = float(spot_price)
    #         contracts = list(qs)
    #         atm_contract = min(contracts, key=lambda c: abs(float(c.strike_price or 0) - spot))
    #         strike_selection = route.strike_selection
    #         if strike_selection == 'ATM':
    #             return atm_contract, signal_side
    #         contracts_sorted = sorted(contracts, key=lambda c: float(c.strike_price or 0))
    #         atm_index = contracts_sorted.index(atm_contract)
    #         offset = 0
    #         if 'ITM_1' in strike_selection: offset = -1 if option_type == 'CE' else 1
    #         elif 'ITM_2' in strike_selection: offset = -2 if option_type == 'CE' else 2
    #         elif 'ITM_3' in strike_selection: offset = -3 if option_type == 'CE' else 3
    #         elif 'OTM_1' in strike_selection: offset = 1 if option_type == 'CE' else -1
    #         elif 'OTM_2' in strike_selection: offset = 2 if option_type == 'CE' else -2
    #         elif 'OTM_3' in strike_selection: offset = 3 if option_type == 'CE' else -3
    #         target_index = atm_index + offset
    #         if 0 <= target_index < len(contracts_sorted):
    #             return contracts_sorted[target_index], signal_side
    #         return atm_contract, signal_side
    #     return qs.first(), signal_side
