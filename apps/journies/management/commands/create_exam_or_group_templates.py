from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.journies.models import JourneyTemplate, JourneyStepTemplate, StaticJourneyType
from apps.questions.models import Question


def create_exam_journey_template(name: str, time_minutes_limit: int, question_count: int) -> JourneyTemplate:
    journey_template = JourneyTemplate.objects.create(
        name=name,
        time_minutes_limit=time_minutes_limit,
        journey_type=StaticJourneyType.EXAM
    )

    random_questions = Question.objects.filter(
        is_active=True
    ).order_by('?')[:question_count]

    for question in random_questions:
        JourneyStepTemplate.objects.create(
            journey_template=journey_template,
            question=question
        )

    return journey_template


def create_multiple_exam_templates():
    exam_sizes = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
    exam_names = [
        "آزمون جامع ریاضی",
        "آزمون هوش و استعداد تحلیلی",
        "آزمون سرعت و دقت",
        "آزمون تمرکز و هوشیاری",
        "آزمون استدلال منطقی",
        "آزمون تفکر تحلیلی",
        "آزمون هوش کلامی",
        "آزمون هوش غیرکلامی",
        "آزمون هوش فضایی",
        "آزمون هوش ریاضی"
    ]

    created_templates = []
    for size, name in zip(exam_sizes, exam_names):
        template = create_exam_journey_template(
            name=name,
            time_minutes_limit=size * 2,
            question_count=size
        )
        created_templates.append(template)
        print(f"Created exam template: {name} with {size} questions")

    return created_templates


def create_group_exam_journey_template(
    name: str,
    time_minutes_limit: int,
    question_count: int,
    start_datetime: timezone.datetime
) -> JourneyTemplate:
    journey_template = JourneyTemplate.objects.create(
        name=name,
        time_minutes_limit=time_minutes_limit,
        journey_type=StaticJourneyType.GROUP_EXAM,
        start_datetime=start_datetime
    )

    random_questions = Question.objects.filter(
        is_active=True
    ).order_by('?')[:question_count]

    for question in random_questions:
        JourneyStepTemplate.objects.create(
            journey_template=journey_template,
            question=question
        )

    return journey_template


def create_multiple_group_exam_templates(count=100, question_count=20, interval_minutes=5):
    import random
    current_time = timezone.now()
    durations = [5, 10, 15, 30, 60]

    created_templates = []
    for i in range(count):
        duration = random.choice(durations)
        exam_name = (
            f"آزمون گروهی (شروع: {current_time.strftime('%Y/%m/%d %H:%M')}, "
            f"مدت: {duration} دقیقه)"
        )
        template = create_group_exam_journey_template(
            name=exam_name,
            time_minutes_limit=duration,
            question_count=question_count,
            start_datetime=current_time
        )
        created_templates.append(template)
        print(f"Created group exam template: {exam_name}")
        current_time += timezone.timedelta(minutes=interval_minutes)

    return created_templates


class Command(BaseCommand):
    help = 'Generate exam and group exam journey templates.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['exam', 'group', 'all'],
            default='all',
            help='Type of templates to create: exam, group, or all'
        )
        parser.add_argument(
            '--group-count',
            type=int,
            default=100,
            help='Number of group exam templates to create'
        )
        parser.add_argument(
            '--group-questions',
            type=int,
            default=20,
            help='Number of questions in each group exam'
        )
        parser.add_argument(
            '--group-interval',
            type=int,
            default=5,
            help='Interval in minutes between group exam start times'
        )

    def handle(self, *args, **options):
        template_type = options['type']

        if template_type in ('exam', 'all'):
            self.stdout.write('Creating standard exam templates...')
            create_multiple_exam_templates()

        if template_type in ('group', 'all'):
            count = options['group_count']
            qcount = options['group_questions']
            interval = options['group_interval']
            self.stdout.write(
                f'Creating {count} group exam templates '
                f'with {qcount} questions and {interval}m intervals...'
            )
            create_multiple_group_exam_templates(
                count=count,
                question_count=qcount,
                interval_minutes=interval
            )

        self.stdout.write(self.style.SUCCESS('Template creation complete.'))
