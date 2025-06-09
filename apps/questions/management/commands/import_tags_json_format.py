import json
import sys
from django.core.management.base import BaseCommand, CommandError
from apps.questions.models import Tag

class Command(BaseCommand):
    help = 'Import tags from a nested JSON file into the Tag model.'

    def add_arguments(self, parser):
        parser.add_argument(
            'filepath',
            type=str,
            help='The file path of the JSON file containing the tags data'
        )

    def handle(self, *args, **options):
        filepath = options['filepath']
        try:
            with open(filepath, encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File {filepath} does not exist.")
        except json.JSONDecodeError as e:
            raise CommandError(f"Error decoding JSON: {str(e)}")

        def process_node(name, node_data, parent=None):
            tag, created = Tag.objects.get_or_create(name=name, parent=parent)
            # if created:
            #     # self.stdout.write(self.style.SUCCESS(f"Created tag: {tag.name}"))
            #     print(tag.name, file=sys.stdout, flush=True)
            # else:
            #     # self.stdout.write(self.style.NOTICE(f"Tag already exists"))
            #     print("exists", file=sys.stdout, flush=True)
            # If this node has children then iterate and process them
            children = node_data.get("children", {})
            for child_name, child_data in children.items():
                process_node(child_name, child_data, parent=tag)

        # The top-level JSON has the main tag as its single key.
        for root_name, root_data in data.items():
            process_node(root_name, root_data, parent=None)

        self.stdout.write(self.style.SUCCESS("Finished importing tags."))
