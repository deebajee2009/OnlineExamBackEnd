import json
import re

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError

from apps.questions.models import Question

LETTER_TO_INDEX = {'A': 1, 'B': 2, 'C': 3, 'D': 4}


class Command(BaseCommand):
    help = "Import questions from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to the JSON file containing an array of question objects'
        )
    def _append_failed_object(self, file_path, obj):
        try:
            with open(file_path, 'r+', encoding='utf-8') as f:
                data = json.load(f)
                data.append(obj)
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.truncate()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to write to {file_path}: {e}"))

    def handle(self, *args, **options):
        json_file_path = options['json_file']
        failed_file_path = "failed_objects_v2.json"

        # Initialize failed objects file
        with open(failed_file_path, 'w+', encoding='utf-8') as ff:
            json.dump([], ff)

        # 1️⃣ Load JSON
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f" Failed to read JSON file: {e}"))
            return

        if not isinstance(data, list):
            self.stderr.write(self.style.ERROR(" JSON root must be an array of question objects."))
            return

        # 2️⃣ Iterate & import
        for idx, item in enumerate(data, start=1):
            question_text = item.get('question')
            options = item.get('options', [])
            correct = item.get('correct_option')
            explanation = item.get('explanation')
            direction = item.get('direction')
            min_required_age = item.get('min_required_age')


            if not question_text:
                # self.stderr.write(self.style.ERROR(f"[{idx}] Missing ‘question’ field; skipping."))
                # continue
                self._append_failed_object(failed_file_path, item)
                continue
            if not isinstance(options, list) or len(options) != 4:
                # self.stderr.write(self.style.ERROR(f"[{idx}] ‘options’ must be an array of four strings; skipping."))
                # continue
                self._append_failed_object(failed_file_path, item)
                continue
            if correct not in LETTER_TO_INDEX:
                # self.stderr.write(self.style.ERROR(f"[{idx}] ‘correct_option’ must be one of A, B, C, D; skipping."))
                # continue
                self._append_failed_object(failed_file_path, item)
                continue

            # Clean option text (strip leading “1) ”, “2) ” …)
            cleaned = [
                re.sub(r'^\s*\d+\)\s*', '', opt)
                for opt in options
            ]

            # Build the Question instance

            true_choice_field = f"choice_{LETTER_TO_INDEX[correct]}"


            q = Question(
                text_body=question_text,
                choice_1=cleaned[0],
                choice_2=cleaned[1],
                choice_3=cleaned[2],
                choice_4=cleaned[3],
                true_choice=true_choice_field,
                answer=explanation,
                direction=direction,
                min_required_age=min_required_age
            )

            # 3️⃣ Validate & save
            try:
                q.full_clean()
                q.save()
                print('okayed question', q.id)
                # self.stdout.write(self.style.SUCCESS(f"[{idx}] Imported"))
            except ValidationError as ve:
                # self.stderr.write(self.style.ERROR(f"[{idx}] ValidationError: {ve.message_dict}"))
                self._append_failed_object(failed_file_path, item)
            except Exception as e:
                # self.stderr.write(self.style.ERROR(f"[{idx}] Unexpected error: {e}"))
                self._append_failed_object(failed_file_path, item)


        self.stdout.write(self.style.SUCCESS(" Finished importing questions."))
