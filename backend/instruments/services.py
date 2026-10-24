class InstrumentResolver:
    """Resolves the actual execution instrument from a signal instrument + route config."""

    @staticmethod
    def validate_execution_instrument(instrument):
        if instrument.instrument_type in {'INDEX', 'MF'} or instrument.ex_inst_type == 20:
            raise ValueError('Select a tradable instrument. Indices and underlying references are for analysis only.')
        if not instrument.is_active or not instrument.is_tradeable:
            raise ValueError('This instrument is not active for trading.')

    @staticmethod
    def validate_execution_snapshot(snapshot):
        from .models import Instrument
        watchlist = snapshot.get("watchlist_instruments", [])
        if any(not isinstance(item, dict) or type(item.get('instrument_id')) is not int or
               item['instrument_id'] <= 0 or not isinstance(item.get('execution_routes', []), list) or
               any(not isinstance(route, dict) for route in item.get('execution_routes', [])) for item in watchlist):
            raise ValueError('Each watchlist item needs a positive integer instrument ID and a list of execution route objects.')
        ids = {item['instrument_id'] for item in watchlist}
        if len(ids) != len(watchlist):
            raise ValueError('An execution version can contain each instrument only once.')
        instruments = Instrument.objects.in_bulk(ids)
        if not ids or set(instruments) != ids:
            raise ValueError("The execution version must contain available instruments.")
        for instrument in instruments.values():
            InstrumentResolver.validate_execution_instrument(instrument)
        if any(route.get("route_type") != "DIRECT" for item in watchlist for route in item.get("execution_routes", [])):
            raise ValueError("Execution currently supports Direct instrument routing only.")
        if any(len(item.get('execution_routes', [])) > 1 for item in watchlist):
            raise ValueError('Use one Direct execution configuration per instrument.')
        return instruments

    @staticmethod
    def execution_instrument_ids(config: dict) -> list[int]:
        """Read instrument IDs from a deployed strategy snapshot."""
        ids = {item['instrument_id'] for item in config['watchlist_instruments']}
        if not ids:
            raise ValueError("Deployed strategy snapshot has no watchlist instruments for execution.")
        return sorted(ids)

    
    @staticmethod
    def resolve(watch: dict, signal_side: str, default_sizing: dict) -> tuple[int, str, dict]:
        """Resolve a snapshot's Direct route to an ID, side and flat sizing block."""
        routes = watch.get('execution_routes', [])
        if len(routes) > 1:
            raise ValueError('Use one Direct execution configuration per instrument.')
        sizing = default_sizing
        if routes:
            route = routes[0]
            route_type = route['route_type']
            if route_type != 'DIRECT':
                raise ValueError(f"Unsupported routing type '{route_type}'. Only DIRECT routing is enabled.")
            if route.get('override_sizing', False):
                sizing = {key: route[key] for key in ('sizing_method', 'fixed_quantity', 'capital_percentage')}
        return watch['instrument_id'], signal_side, sizing
