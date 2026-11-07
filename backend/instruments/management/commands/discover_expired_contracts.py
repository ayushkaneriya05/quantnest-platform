"""Read-only discovery of provider symbols and their local catalog coverage."""
from datetime import date
import json

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Min

from instruments.models import Instrument
from marketdata.contracts import ProviderError, normalize_symbol
from marketdata.providers import provider


class Command(BaseCommand):
    help = 'List provider expiry dates, then optionally inspect exact contracts for one expiry. Writes no database records.'

    def add_arguments(self, parser):
        parser.add_argument('symbol', help='Exact underlying sym_ticker, such as NSE:NIFTY50-INDEX.')
        parser.add_argument('--from-date', type=date.fromisoformat, required=True)
        parser.add_argument('--to-date', type=date.fromisoformat, required=True)
        parser.add_argument('--expiry', type=date.fromisoformat, help='One expiry returned by discovery; enables the second request.')

    def handle(self, *args, **options):
        adapter = provider()
        try:
            symbol = normalize_symbol(options['symbol'])
            start, end, expiry = options['from_date'], options['to_date'], options['expiry']
            if not 0 <= (end - start).days < 366 or expiry is not None and not start <= expiry <= end:
                raise ValueError('Use a range of at most 366 days and an expiry inside that range.')
            listing = adapter.expiry_dates(symbol, start, end)
            result = {'provider': adapter.name, 'from_date': start, 'to_date': end, **listing}
            if expiry is not None:
                if not any(expiry in dates for dates in listing['expiries'].values()):
                    raise ValueError('The provider did not return this expiry. Choose an expiry from the listing.')
                contracts = adapter.expired_contracts(symbol, expiry)
                if contracts['provider_underlying'] != listing['provider_underlying']:
                    raise ValueError('The two provider responses identify different underlyings.')
                symbols = [value for values in contracts['contracts'].values() for value in values]
                # A discovery symbol is not a specification: report gaps rather
                # than manufacturing exchange tokens, strikes or historical lots.
                catalog = {item['sym_ticker']: item for item in Instrument.objects.filter(sym_ticker__in=symbols)
                    .annotate(terms_from=Min('specifications__effective_at'))
                    .values('id', 'sym_ticker', 'name', 'instrument_type', 'expiry_date', 'terms_from')}
                result.update(expiry=expiry, contracts={kind: [
                    {'sym_ticker': value, 'catalog': catalog.get(value)} for value in values]
                    for kind, values in contracts['contracts'].items()})
                result['note'] = ('Catalog presence alone does not qualify historical execution. '
                    'Import sourced contract terms for the requested period; missing catalog identities require a sourced master record.')
        except (ValueError, ProviderError) as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(json.dumps(result, cls=DjangoJSONEncoder, indent=2))
