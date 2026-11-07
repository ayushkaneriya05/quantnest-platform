"""Import reviewed clearing prices without creating synthetic market orders."""
import json
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from execution.settlement_records import import_prices


class Command(BaseCommand):
    help = 'Import sourced settlement prices; use --dry-run to validate before writing.'

    def add_arguments(self, parser):
        parser.add_argument('path', type=Path)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        try:
            document = json.loads(options['path'].read_text(encoding='utf-8-sig'))
            result = import_prices(document, dry_run=options['dry_run'])
        except (OSError, ValueError, ValidationError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result))
