import json
import re
from django.core.management.base import BaseCommand
from apps.questions.models import Question

class Command(BaseCommand):
    help = "Import questions from a JSON file."

    def add_arguments(self, parser):
        # The command expects one argument: the path to the JSON file.
        parser.add_argument('json_file', type=str, help='Path to the JSON file containing questions')

    def handle(self, *args, **options):
        json_file_path = options['json_file']
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Could not read JSON file: {e}"))
            return

        questions_data = data.get('questions', [])
        if not questions_data:
            self.stderr.write(self.style.ERROR("No questions found in the JSON file."))
            return

        for item in questions_data:
            question_text = item.get('question_text')
            options_list = item.get('options', [])
            correct_option_num = item.get('correct_option')

            if not question_text or len(options_list) != 4:
                self.stderr.write(self.style.ERROR("Skipping a question due to invalid data format."))
                continue

            # Process options: Remove leading numbering (e.g. "1)", "2)", etc.)
            cleaned_options = []
            for opt in options_list:
                # This regex removes any leading numeric digits followed by a parenthesis and optional whitespace.
                cleaned = re.sub(r'^\s*\d+\)\s*', '', opt)
                cleaned_options.append(cleaned)

            # Map the correct option number (1, 2, 3, or 4) to the field name expected (e.g. "choice_1")
            if correct_option_num not in [1, 2, 3, 4]:
                # self.stderr.write(self.style.ERROR(
                #     f"Invalid correct option value '{correct_option_num}' for question: {question_text}"
                # ))
                continue
            true_choice_field = f"choice_{correct_option_num}"

            # Create a new Question instance. Note:
            # - The JSON 'question_text' is saved into the model's text_body.
            # - Each of the options is saved into the corresponding choice field.
            # - The true_choice field is set to the key of the correct option.
            question_instance = Question(
                text_body=question_text,
                choice_1=cleaned_options[0],
                choice_2=cleaned_options[1],
                choice_3=cleaned_options[2],
                choice_4=cleaned_options[3],
                true_choice=true_choice_field
            )
            question_instance.save()
            # self.stdout.write(self.style.SUCCESS(f"Imported question: {question_text}"))

        self.stdout.write(self.style.SUCCESS("Finished importing questions."))
