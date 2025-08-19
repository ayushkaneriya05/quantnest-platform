import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from trading.models import Instrument

class Command(BaseCommand):
    help = 'Populates the Instrument table from nifty100_symbols.json'

    def handle(self, *args, **options):
        self.stdout.write('Deleting existing instruments...')
        Instrument.objects.all().delete()

        file_path = Path(settings.BASE_DIR) / 'data' / 'nifty100_symbols.json'
        with open(file_path, 'r') as f:
            instruments_data = json.load(f)

        instruments_to_create = []
        for item in instruments_data:
            instruments_to_create.append(
                Instrument(symbol=item['symbol'], company_name=item['company_name'])
            )

        Instrument.objects.bulk_create(instruments_to_create)
        self.stdout.write(self.style.SUCCESS(f'Successfully populated {len(instruments_to_create)} instruments.'))