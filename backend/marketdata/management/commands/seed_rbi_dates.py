from django.core.management.base import BaseCommand

from marketdata.calendar_service import EventCalendarService


class Command(BaseCommand):
    help = "Seed known RBI policy dates into the market event calendar."

    def add_arguments(self, parser):
        parser.add_argument("years", nargs="+", type=int)

    def handle(self, *args, **options):
        created = EventCalendarService.seed_rbi_policy_dates(*options["years"])
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} RBI policy events"))
