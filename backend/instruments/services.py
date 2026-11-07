from common.enums import ExchangeInstrumentType, InstrumentType
from strategies.specification.configuration import LIMITS


class InstrumentResolver:
    """Validate bound instruments and read their optional sizing configuration."""

    @staticmethod
    def validate_execution_instrument(instrument, *, historical=False):
        if instrument.instrument_type in (InstrumentType.INDEX, InstrumentType.MF) or instrument.ex_inst_type == ExchangeInstrumentType.UNDCUR:
            raise ValueError('Select a tradable instrument. Indices and underlying references are for analysis only.')
        if not historical and (not instrument.is_active or not instrument.is_tradeable):
            raise ValueError('This instrument is not active for trading.')

    @staticmethod
    def validate_execution_snapshot(snapshot, *, historical=False):
        from .models import Instrument
        watchlist = snapshot.get("watchlist_instruments", [])
        if any(not isinstance(item, dict) or type(item.get('instrument_id')) is not int or
               item['instrument_id'] <= 0 or not isinstance(item.get('execution_routes', []), list) or
               any(not isinstance(route, dict) for route in item.get('execution_routes', [])) for item in watchlist):
            raise ValueError('Each watchlist item needs a positive integer instrument ID and a list of sizing configuration objects.')
        ids = {item['instrument_id'] for item in watchlist}
        identities = [(item['route_id'], item['leg_id']) for item in watchlist]
        if len(set(identities)) != len(identities):
            raise ValueError('An execution version must have distinct route/leg identities.')
        instruments = Instrument.objects.in_bulk(ids)
        if not ids or set(instruments) != ids:
            raise ValueError("The execution version must contain available instruments.")
        for item in watchlist:
            instrument = instruments[item['instrument_id']]
            if 'contract_selection' in item:
                from .selection import SelectionPolicy
                from common.enums import Exchange
                SelectionPolicy.parse(item['contract_selection'])
                if instrument.instrument_type not in (InstrumentType.STOCK, InstrumentType.INDEX) or instrument.exchange not in (Exchange.NSE, Exchange.BSE):
                    raise ValueError('Select an NSE/BSE stock or index underlying.')
            else:
                InstrumentResolver.validate_execution_instrument(instrument, historical=historical)
        if any(len(item.get('execution_routes', [])) > LIMITS['sizing_overrides_per_contract'] for item in watchlist):
            raise ValueError('Use one sizing configuration per instrument.')
        return instruments

    @staticmethod
    def input_bindings(watch: dict) -> dict[str, int]:
        """Concrete inputs for a route; ownership is independent of these IDs."""
        trade = watch['instrument_id']
        return {'signal': watch.get('signal_instrument_id', trade), 'trade': trade}

    @staticmethod
    def sizing_for(watch: dict, default_sizing: dict) -> dict:
        """Read the validated route override or the strategy's shared sizing."""
        overrides = watch.get('execution_routes', [])
        if overrides and overrides[0]['override_sizing']:
            return {key: overrides[0][key] for key in ('sizing_method', 'fixed_quantity', 'capital_percentage', 'quantity_unit')}
        return default_sizing
