"""Load sourced derivative terms for historical replay without changing the master."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from instruments.specifications import import_specifications


class Command(BaseCommand):
    help = 'Import immutable dated contract terms from a reviewed JSON file.'

    def add_arguments(self, parser):
        parser.add_argument('file', type=Path, help='JSON document described in docs/backtesting.md.')
        parser.add_argument('--dry-run', action='store_true', help='Validate the entire batch without saving.')

    def handle(self, *args, **options):
        try:
            with options['file'].open('rb') as source:
                content = source.read(8 * 1024 * 1024 + 1)
            if len(content) > 8 * 1024 * 1024:
                raise ValueError('Specification file must be at most 8 MiB.')
            document = json.loads(content.decode('utf-8-sig'))
            result = import_specifications(document, dry_run=options['dry_run'])
        except (OSError, ValueError) as exc:
            raise CommandError(str(exc)) from None
        verb = 'Would create' if options['dry_run'] else 'Created'
        self.stdout.write(self.style.SUCCESS(f'{verb} {result["created"]} specifications; {result["unchanged"]} unchanged.'))
