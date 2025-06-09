from celery import shared_task
from apps.questions.models import Question


@shared_task
def calculate_hardness(cls):
    """
    Periodic task function: Updates hardness for all questions in the database.
    """
    for question in Question.objects.all():
        question.calculate_hardness()
