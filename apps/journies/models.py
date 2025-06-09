from django.db import models
from datetime import timedelta
from django.utils import timezone

from apps.accounts.models import User
from utils.exceptions import CustomValidationError
from apps.questions.models import Question


class StaticJourneyType(models.TextChoices):
    TRAINING = 'training', 'آموزشی'
    EXAM = 'exam', 'آزمون استاتیک'
    GROUP_EXAM = 'group_exam', 'آزمون استاتیک گروهی'


class JourneyTemplate(models.Model):
    name = models.CharField(max_length=300)  # konkoor_92
    time_minutes_limit = models.PositiveIntegerField(
        default=0, blank=True, null=True)
    start_datetime = models.DateTimeField(null=True, blank=True)
    journey_type = models.CharField(
        max_length=30,
        choices=StaticJourneyType.choices,
        default=StaticJourneyType.TRAINING
    )

    def __str__(self):
        return self.name


class JourneyStepTemplate(models.Model):
    journey_template = models.ForeignKey(JourneyTemplate, on_delete=models.CASCADE, related_name="quiz_steps")
    question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        related_name="quiz"
    )

    class Meta:
        ordering = ["id"]
        unique_together = [("journey_template", "question")]

    def __str__(self):
        return self.question.text_body[:50]


class SubjectChoices(models.TextChoices):
    ANALYTICAL_INTELLIGENCE = 'analytical', 'هوش و استعداد تحلیلی'
    SPEED_ACCURACY_FOCUS = 'speed_focus', 'سرعت، دقت و تمرکز'

class Journey(models.Model):
    journey_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="journeys",
    )
    subject = models.CharField(
        max_length=20,
        choices=SubjectChoices.choices,
        blank=True,
        null=True
    )
    time_minutes_limit   = models.PositiveIntegerField(
        default=0,
        blank=True,
        null=True
    )
    question_count_limit = models.PositiveIntegerField(
        default=0,
        blank=True,
        null=True
    )
    created_at           = models.DateTimeField(auto_now_add=True)
    finished_at          = models.DateTimeField(
        blank=True,
        null=True,
        default=None
    )
    journey_type         = models.CharField(
        max_length=30,
        choices=StaticJourneyType.choices,
        default=StaticJourneyType.TRAINING,
        blank=True,
        null=True
    )
    journey_static       = models.ForeignKey(
        JourneyTemplate,
        on_delete=models.CASCADE,
        related_name='template',
        blank=True,
        null=True
    )
    last_seen_journey_step = models.ForeignKey(
        'JourneyStep',                # string name, because JourneyStep is below
        on_delete=models.SET_NULL,    # keep the Journey if the step is deleted
        null=True,
        blank=True,
        default=None,
        related_name='+',             # no reverse accessor needed
        help_text="The most recent JourneyStep this Journey has seen"

    )
    answered_count = models.PositiveIntegerField(
        default=None,
        blank=True,
        null=True
    )
    unanswered_count = models.PositiveIntegerField(
        default=None,
        blank=True,
        null=True
    )
    correct_count = models.PositiveIntegerField(
        default=None,
        blank=True,
        null=True
    )
    wrong_count = models.PositiveIntegerField(
        default=None,
        blank=True,
        null=True
    )
    score = models.FloatField(
        default=None,
        blank=True,
        null=True
    )
    rank = models.PositiveIntegerField(
        default=None,
        blank=True,
        null=True
    )
    total_participants = models.PositiveIntegerField(
        default=None,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-created_at']  # descending (most recent first)

    def is_active(self):
        """
        Returns True if the journey is still active, i.e., the number of questions shown
        is less than question_count_limit and the elapsed time (since the first question was shown)
        is less than time_minutes_limit. Otherwise, returns False.
        """
        if self.journey_static:
            if self.journey_static.journey_type == StaticJourneyType.GROUP_EXAM:
                deadline = self.journey_static.start_datetime + timedelta(
                    minutes=self.journey_static.time_minutes_limit or 0
                )
                if timezone.now() > deadline or self.finished_at < timezone.now():
                    return False
                return True
        if self.finished_at:
            if self.finished_at < timezone.now():
                return False

        # Check if the question count limit is reached.
        if self.question_count_limit:
            steps = self.steps.all()
            if steps.count() > self.question_count_limit:
                return False


        if self.time_minutes_limit > 0:
            elapsed_minutes = (timezone.now() - self.created_at).total_seconds() / 60
            if elapsed_minutes >= self.time_minutes_limit:
                return False

        return True

    def __str__(self):
        return f"{self.user.phone_number}'s journey on {self.get_subject_display()} created at {self.created_at}"


class UserAnswer(models.TextChoices):
    CORRECT = 'C', 'Correct'
    FALSE = 'F', 'False'
    NOT_SELECTED = 'N', 'Not Selected'

class JourneyStep(models.Model):
    step_id       = models.AutoField(primary_key=True)
    journey       = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name="steps")
    question      = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        related_name="journey_steps"
    )
    user_answer   = models.CharField(max_length=255, blank=True, null=True)
    answer_result = models.CharField(
        max_length=20,
        choices=UserAnswer.choices,
        default=UserAnswer.NOT_SELECTED,
    )

    class Meta:
        ordering = ["step_id"]

    def calculate_answer_result(self):
        """
        Determine and set answer_result based on the current user_answer.
        """
        if self.user_answer:
            if self.user_answer == self.question.true_choice:
                self.answer_result = UserAnswer.CORRECT
            else:
                self.answer_result = UserAnswer.FALSE
        else:
            self.answer_result = UserAnswer.NOT_SELECTED
    def calculate_time_taken(self):
        """
        Calculate and update answered_at and time_taken based on user_answer and shown_at.
        This method assumes that 'shown_at' is already set.
        """
        if self.user_answer:
            # Only set answered_at if it hasn't been set yet
            if not self.answered_at:
                self.answered_at = timezone.now()
            # Calculate time_taken as the difference between answered_at and shown_at
            self.time_taken = self.answered_at - self.shown_at
    def update_computed_fields(self):
        """
        Convenience method to update all computed fields.
        This can be manually called before calling save().
        """
        self.calculate_answer_result()

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)
    def __str__(self):
        return f"JourneyStep for Journey {self.journey.id} on Question {self.question.id}"


# class JourneyResult(models.Model):
#     journey = models.ForeignKey(
#         Journey,
#         on_delete=models.CASCADE,
#         related_name="result"
#     )
#     user = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         related_name="result",
#     )
