from django.core.management.base import BaseCommand

from sms.backfill import backfill


class Command(BaseCommand):
    help = (
        "Attribute SMS sent before category and location were recorded, "
        "by matching them to tokens, reminders and case logs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be attributed without saving anything.",
        )

    def handle(self, *args, **options):
        counts = backfill(dry_run=options["dry_run"])
        for label, count in counts.items():
            self.stdout.write(f"{label}: {count}")
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run, nothing was saved."))
