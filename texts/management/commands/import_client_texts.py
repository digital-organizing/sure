import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from texts.models import Text


class Command(BaseCommand):
    help = "Import client text slugs from a CSV file into the Text model."

    default_csv = Path("texts") / "tests" / "data" / "client_text_slugs.csv"
    required_columns = {"slug", "page", "note", "English Text"}

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default=None,
            help=(
                "Path to the CSV file containing client text slugs. "
                "Defaults to texts/tests/data/client_text_slugs.csv relative to BASE_DIR."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without touching the database.",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        dry_run = options["dry_run"]

        path = (
            Path(csv_path) if csv_path else Path(settings.BASE_DIR) / self.default_csv
        ).resolve()

        if not path.exists():
            raise CommandError(f"CSV file not found: {path}")

        created, updated, skipped = 0, 0, 0
        with path.open(newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames:
                raise CommandError("CSV file is missing headers.")

            missing_columns = self.required_columns.difference(reader.fieldnames)
            if missing_columns:
                raise CommandError(
                    f"CSV file is missing required columns: {', '.join(sorted(missing_columns))}"
                )

            for line_number, row in enumerate(reader, start=2):
                slug = (row.get("slug") or "").strip()
                if not slug:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Line {line_number}: missing slug, skipping."
                        )
                    )
                    continue

                page = (row.get("page") or "").strip()
                note = (row.get("note") or "").strip()
                english_text = (row.get("English Text") or "").strip()

                context_parts = [part for part in (page, note) if part]
                context = " - ".join(context_parts)[
                    : Text._meta.get_field("context").max_length
                ]

                defaults = {
                    "context": context,
                    "content": english_text or slug,
                    "internal": False,
                }

                if dry_run:
                    exists = Text.objects.filter(pk=slug).exists()
                    created += int(not exists)
                    updated += int(exists)
                    continue

                text, created_flag = Text.objects.update_or_create(
                    slug=slug,
                    defaults=defaults,
                )

                if created_flag:
                    created += 1
                else:
                    updated += 1

        summary = f"Processed {created + updated + skipped} rows: {created} created, {updated} updated, {skipped} skipped."
        if dry_run:
            summary = "DRY RUN - " + summary
        self.stdout.write(self.style.SUCCESS(summary))
