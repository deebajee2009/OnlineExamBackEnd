import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.questions.models import Tag

class Command(BaseCommand):
    help = (
        "Import hierarchical tags from a CSV file. "
        "Each row represents a path; cells are levels.\n"
        "Example CSV row:\n"
        "  Electronics, Computers, Laptops"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file to import'
        )
        parser.add_argument(
            '--delimiter', '-d',
            default=',',
            help='CSV delimiter (default: ,)'
        )
        parser.add_argument(
            '--encoding', '-e',
            default='utf-8-sig',
            help='File encoding (default: utf-8)'
        )

    def create_tag_path(self, path):
        parent = None
        for name in path:
            name = name.strip().lstrip('\ufeff')
            if not name:
                continue
            tag, created = Tag.objects.get_or_create(
                name=name,
                parent=parent
            )
            parent = tag
        return parent

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = options['csv_file']
        delim = options['delimiter']
        enc = 'utf-8-sig'

        try:
            with open(file_path, encoding=enc, newline='') as f:
                reader = csv.reader(f, delimiter=delim)
                for row_num, row in enumerate(reader, start=1):
                    # filter out empty cells
                    tag_path = [cell for cell in (c.strip() for c in row) if cell]
                    if not tag_path:
                        # self.stdout.write(self.style.WARNING(f"Row {row_num}: empty, skipping"))
                        continue

                    # self.stdout.write(f"Row {row_num}: Creating path → {' > '.join(tag_path)}")
                    self.create_tag_path(tag_path)

        except FileNotFoundError:
            raise CommandError(f"File not found: {file_path}")
        except Exception as e:
            raise CommandError(f"Error importing CSV: {e}")

        self.stdout.write(self.style.SUCCESS("Import complete!"))
