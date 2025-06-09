from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from utils.exceptions import CustomValidationError


class UserAnswer(models.TextChoices):
    CORRECT = 'C', 'Correct'
    FALSE = 'F', 'False'
    NOT_SELECTED = 'N', 'Not Selected'

CHOICE_FIELD_NAMES = [
    ('choice_1', 'Choice 1'),
    ('choice_2', 'Choice 2'),
    ('choice_3', 'Choice 3'),
    ('choice_4', 'Choice 4'),
]

class Tag(MPTTModel):
    name = models.CharField(max_length=255)
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        unique_together = ('parent', 'name')

    def __str__(self):
        return self.name


class Question(models.Model):
    text_body        = models.TextField()
    choice_1         = models.CharField(max_length=255)
    choice_2         = models.CharField(max_length=255)
    choice_3         = models.CharField(max_length=255)
    choice_4         = models.CharField(max_length=255)
    is_active        = models.BooleanField(default=True)
    true_choice      = models.CharField(max_length=20, choices=CHOICE_FIELD_NAMES)
    answer           = models.TextField(blank=True, null=True)
    hardness         = models.FloatField(default=0.0)
    tags             = models.ManyToManyField(Tag, related_name="questions", blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    direction        = models.TextField(
        default=None,
        blank=True,
        null=True
    )
    min_required_age = models.PositiveIntegerField(
        default=None,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-id']   # newest (highest id) first

    def calculate_hardness(self):
        """
        Calculates the hardness of a question based on user answers:
        - Correct answer: 1 point
        - Not selected: 5 points
        - Incorrect answer: 10 points
        Hardness = (sum of points given by users) / (total number of users who answered)
        """
        answers = self.journey_steps.all()
        total_users = answers.count()

        if total_users == 0:
            new_hardness = 0.0
        else:
            total_points = sum(
                1 if ans.answer_result == UserAnswer.CORRECT else
                5 if ans.answer_result == UserAnswer.NOT_SELECTED else
                10 for ans in answers
            )
            new_hardness = total_points / total_users


        self.hardness = new_hardness
        self.save(update_fields=['hardness'])

    def clean(self):
        """
        Validates that the true_choice is one of the allowed field names and that the corresponding
        field has a non-empty value.
        """
        valid_field_names = [choice[0] for choice in CHOICE_FIELD_NAMES]
        if self.true_choice not in valid_field_names:
            raise CustomValidationError(
                "The true_choice must be one of 'choice_1', 'choice_2', 'choice_3', or 'choice_4'."
            )
        # Ensure that the designated field is not empty.
        if not getattr(self, self.true_choice):
            raise CustomValidationError(f"The field {self.true_choice} cannot be empty.")
        super().clean()

    def get_true_choice_value(self):
        """
        Returns the actual value of the true choice field.
        """
        return getattr(self, self.true_choice)

    def __str__(self):
        return f"Question: {self.text_body[:50]}..."
