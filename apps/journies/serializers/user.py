from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from apps.journies.models import (
    Journey,
    JourneyStep,
    JourneyTemplate,
    JourneyStepTemplate,
    StaticJourneyType,
    SubjectChoices
)
from apps.questions.models import Question
from apps.questions.serializers import QuestionSerializer
from utils.exceptions import (
    CustomNotFoundError,
    CustomValidationError,
    CustomNoContentError
)


class OpenGroupExamJourneySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='journey_static.name', read_only=True)
    group_exam_id = serializers.IntegerField(source='journey_static.id', read_only=True)
    class Meta:
        model = Journey
        fields = [
            'journey_id',
            'name',
            'group_exam_id'
        ]


class JourneyCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a Journey.
    The user, subject, time limit, and question count limit are provided.
    """
    class Meta:
        model = Journey
        fields = ("journey_id", "subject", "time_minutes_limit", "question_count_limit")
        extra_kwargs = {
            "journey_id": {"read_only": True},
            "time_minutes_limit": {"required": False, "default": 0},
            "question_count_limit": {"required": False, "default": 0},
        }
    def validate(self, data):
        try:
            time_limit = data.get("time_minutes_limit", 0)
            count_limit = data.get("question_count_limit", 0)

            # Check if at least one of the limits is greater than zero.
            if not (time_limit > 0 or count_limit > 0):
                raise CustomValidationError(
                    "At least one of time_minutes_limit or question_count_limit must be greater than zero."
                )
        except:
            raise CustomValidationError(
                "At least one of time_minutes_limit or question_count_limit must be greater than zero."
            )
        return data


    def create(self, validated_data):
        # Assuming the current user is passed via context
        user = self.context["request"].user
        journey = Journey.objects.create(user=user, **validated_data)

        return journey


class JourneyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journey
        fields = ("journey_id", "user", "subject", "time_minutes_limit", "question_count_limit", "created_at", "finished_at")

class StaticJourneySerializer(serializers.ModelSerializer):
    class Meta:
        model = JourneyTemplate
        fields = (
            'id',
            'name',
            'time_minutes_limit'
        )

class StaticJourneyListSerializer(serializers.ModelSerializer):
    journey_static = StaticJourneySerializer()
    is_active = serializers.SerializerMethodField()
    class Meta:
        model = Journey
        fields = (
            "journey_id",
            "time_minutes_limit",
            "created_at",
            "finished_at",
            "journey_type",
            "journey_static",
            "is_active"
        )
    def get_is_active(self, obj):
        return obj.is_active()


class JourneyFinishSerializer(serializers.Serializer):
    journey_id           = serializers.IntegerField()
    finished_at          = serializers.DateTimeField()
    subject              = serializers.CharField(read_only=True)
    time_minutes_limit   = serializers.IntegerField(min_value=0, read_only=True)
    journey_type         = serializers.CharField(read_only=True)
    journey_static       = serializers.IntegerField(read_only=True)
    question_count_limit = serializers.IntegerField(min_value=0, read_only=True)
    created_at           = serializers.DateTimeField(read_only=True)

    def validate(self, data):
        """
        Validate the entire set of data.
        """
        user = self.context["request"].user
        journey_id = data["journey_id"]
        try:
            journey = Journey.objects.get(journey_id=journey_id, user=user)
        except Journey.DoesNotExist:
            raise CustomNotFoundError("Journey not found for this user.")
        return data

    def create(self, validated_data):
        user = self.context["request"].user
        journey_id = validated_data["journey_id"]
        # finished_at = validated_data["finished_at"]
        finished_at = timezone.now()

        journey = Journey.objects.get(journey_id=journey_id, user=user)
        journey.finished_at = finished_at

        journey.save(update_fields=[
            'finished_at',
        ])

        return journey

class NexstQuestionSerializer(serializers.Serializer):
    # journey_id = serializers.IntegerField()
    # current_journey_step_id = serializers.IntegerField()

    def validate(self, data):
        journey_id             = self.context["journey_id"]
        current_journey_step_id = self.context["current_journey_step_id"]
        user = self.context["request"].user
        # journey_id = data["journey_id"]
        try:
            journey = Journey.objects.get(journey_id=journey_id, user=user)

        except Journey.DoesNotExist:
            raise CustomNotFoundError( "Journey not found for user.")
        if not journey.is_active():
            raise CustomValidationError("Journey is no longer active & finished")
        if journey.question_count_limit == JourneyStep.objects.filter(journey=journey).count():
            raise CustomNoContentError("Journey has reached question limit")
        data["journey"] = journey
        return data


# class QuestionSerializer(serializers.Serializer):
#     text_body = serializers.CharField()
#     choice_1 = serializers.CharField(max_length=255)
#     choice_2 = serializers.CharField(max_length=255)
#     choice_3 = serializers.CharField(max_length=255)
#     choice_4 = serializers.CharField(max_length=255)


class JourneyStepAnswerSerializer(serializers.Serializer):
    journey_id    = serializers.IntegerField()
    step_id       = serializers.IntegerField()
    user_answer   = serializers.CharField(
        max_length=200,
        allow_blank=True,   # lets empty-string pass
        allow_null=True,    # lets None pass
        required=False,
    )
    # answered_at   = serializers.DateTimeField()
    true_choice   = serializers.CharField(source='question.true_choice', read_only=True)
    answer        = serializers.CharField(source='question.answer', read_only=True)
    # shown_at      = serializers.DateTimeField(read_only=True)
    # time_taken    = serializers.DurationField(read_only=True)
    answer_result = serializers.CharField(read_only=True)

    def validate(self, data):
        step_id = data['step_id']
        journey_id = data['journey_id']
        try:
            journey_step = (
                JourneyStep.objects
                .select_related(
                    'question',
                    'journey',                    # brings in the Journey
                    'journey__journey_static'     # brings in the JourneyTemplate
                )
                .get(step_id=step_id, journey__journey_id=journey_id)
            )
            # journey_step = JourneyStep.objects.get(step_id=step_id, journey__journey_id=journey_id)
        except JourneyStep.DoesNotExist:
            raise CustomNotFoundError("journey does not exist...")
        if not journey_step.journey.is_active():
            raise CustomNotFoundError("journey does not exist...")
        # --- New time‐check logic here ---
        template = journey_step.journey.journey_static
        if template and template.start_datetime:
            deadline = template.start_datetime + timedelta(
                minutes=template.time_minutes_limit or 0
            )
            if timezone.now() > deadline:
                raise CustomValidationError(
                    "the group_exam has finished"
                )
        data['journey_step'] = journey_step
        return data
    def update(self, instance, validated_data):
        # Update the user_answer and answered_at fields from the incoming data.
        instance.user_answer = validated_data.get('user_answer', instance.user_answer)
        # instance.answered_at = validated_data.get('answered_at', instance.answered_at)

        instance.save(force_update=True)  # Save the updated instance.
        return instance
    def create(self, validated_data):
        journey_step = validated_data.pop('journey_step', None)

        user_answer = validated_data['user_answer']
        # answered_at = validated_data['answered_at']
        journey_step.user_answer = user_answer
        # journey_step.answered_at = answered_at
        journey_step.update_computed_fields()
        journey_step.save(update_fields=[
            'user_answer',
            # 'answered_at',
            'answer_result',
            # 'time_taken',
        ])

        return journey_step

# class JourneyStepAnswerSerializer(serializers.ModelSerializer):
#     """
#     Serializer for updating a JourneyStep with the user's answer.
#     """
#     class Meta:
#         model = JourneySteps
#         fields = ("id", "user_answer")


class JourneyDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    subject = serializers.CharField()
    time_minutes_limit = serializers.IntegerField()
    question_count_limit = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    is_active = serializers.BooleanField()
    questions = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField(),
            help_text="Each dict has a single 'id' key pointing to a Question"
        )
    )
    last_question = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
        help_text="The last question asked, or null if none yet"
    )


class QuestionDetailSerializer(serializers.Serializer):
    text_body   = serializers.CharField(help_text="The question text")
    choice_1    = serializers.CharField(help_text="First choice")
    choice_2    = serializers.CharField(help_text="Second choice")
    choice_3    = serializers.CharField(help_text="Third choice")
    choice_4    = serializers.CharField(help_text="Fourth choice")
    true_choice = serializers.CharField(help_text="The correct choice key (e.g. 'choice_2')")
    hardness    = serializers.IntegerField(help_text="The question's hardness level")
    answer      = serializers.CharField(help_text="Text answer of questions")


class CreateJourneyTemplateSerializer(serializers.Serializer):
    journey_template_id = serializers.IntegerField()

    def validate(self, data):
        user = self.context["request"].user
        journey_template_id = data['journey_template_id']
        journey_template = get_object_or_404(JourneyTemplate, pk=journey_template_id)

        if journey_template.journey_type == StaticJourneyType.GROUP_EXAM:
            if Journey.objects.filter(user=user, journey_static=journey_template).exists():
                raise CustomValidationError({
                    'journey_template_id': 'A journey from this template already exists for your account.'
                })
            now = timezone.now()
            deadline = journey_template.start_datetime + timedelta(minutes=journey_template.time_minutes_limit)
            if (now >= deadline) or (now < journey_template.start_datetime):
                raise CustomValidationError({
                    'message': 'no proper time to start journey'
                })

        data['journey_template'] = journey_template
        return data

    def create(self, validated_data):
        journey_template = validated_data['journey_template']
        user = self.context["request"].user
        with transaction.atomic():
            finished_at = None
            if journey_template.journey_type == StaticJourneyType.GROUP_EXAM:
                finished_at = journey_template.start_datetime + timedelta(minutes=journey_template.time_minutes_limit)

            journey = Journey.objects.create(
                user=user,
                journey_type=journey_template.journey_type,
                journey_static=journey_template,
                finished_at=finished_at
            )

            # here’s the eager-loading:
            step_templates = (
                JourneyStepTemplate.objects
                .filter(journey_template=journey_template)
                .select_related("question")
            )


            for step_template in step_templates:
                journey_step = JourneyStep.objects.create(
                    journey=journey,
                    question=step_template.question
                )
            return journey

        return None


class StartJourneyGeneralSerializer(serializers.Serializer):
    subject              = serializers.ChoiceField(
        choices=SubjectChoices.choices,
        allow_blank=True,   # lets empty-string pass
        allow_null=True,    # lets None pass
        required=False,
    )
    time_minutes_limit   = serializers.IntegerField()
    question_count_limit = serializers.IntegerField()
    journey_type         = serializers.ChoiceField(
        choices=StaticJourneyType.choices,
        allow_blank=True,   # lets empty-string pass
        allow_null=True,    # lets None pass
        required=False,
    )
    # journey_static       = serializers.IntegerField(
    #     allow_null=True,    # lets None pass
    #     required=False,
    # )

    # def validate(self, data):
    #     journey_template_id = data['journey_static']
    #     if journey_static:
    #         journey_template = get_object_or_404(JourneyTemplate, pk=journey_temple_id)
    #     return data

    def create(self, validated_data):
        # Assuming the current user is passed via context
        user = self.context["request"].user
        # journey_static = validated_data.get("journey_static", None)
        journey = Journey.objects.create(user=user, **validated_data)
        # if journey_static:
        #     # here’s the eager-loading:
        #     step_templates = (
        #         JourneyStepTemplate.objects
        #         .filter(journey_template_id=journey_static)
        #         .select_related("question")
        #     )
        #
        #     for step_template in step_templates:
        #         journey_step = JourneyStep.objects.Create(
        #             journey=journey,
        #             question=step_template.question
        #         )
        return journey

class JourneyStepSerializer(serializers.ModelSerializer):
    question = QuestionSerializer()

    class Meta:
        model = JourneyStep
        fields = [
            'step_id',
            'journey',
            'question',
        ]
        read_only_fields = ['step_id',]

class JourneySerializer(serializers.ModelSerializer):
    """
    Serializes all fields of a Journey instance.
    """
    title          = serializers.SerializerMethodField()
    group_exam_id  = serializers.SerializerMethodField()
    is_active      = serializers.SerializerMethodField()

    class Meta:
        model = Journey
        fields = '__all__'

    def get_is_active(self, obj):

        return obj.is_active()

    def get_title(self, obj):
        """
        Return the related JourneyTemplate.name,
        or None if no journey_static is set.
        """
        if obj.journey_static:
            return obj.journey_static.name
        return None

    def get_group_exam_id(self, obj):
        """
        Return the related JourneyTemplate.pk,
        or None if no journey_static is set.
        """
        if obj.journey_static:
            return obj.journey_static.pk
        return None

class JourneyTemplateSerializer(serializers.ModelSerializer):
    # Include human-readable label if desired
    journey_type_display = serializers.CharField(source='get_journey_type_display', read_only=True)

    class Meta:
        model = JourneyTemplate
        fields = ['id', 'name', 'time_minutes_limit', 'start_datetime', 'journey_type', 'journey_type_display']

# Serializer for the combined Journey + JourneyResult data
class UserJourneySummarySerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    unanswered_count = serializers.SerializerMethodField()
    correct_count = serializers.SerializerMethodField()
    wrong_count = serializers.SerializerMethodField()
    result_id = serializers.SerializerMethodField()

    class Meta:
        model = Journey
        fields = [
            'journey_id',
            'title',
            'created_at',
            'journey_type',
            'unanswered_count',
            'correct_count',
            'wrong_count',
            'result_id',
        ]

    def get_title(self, obj):
        # Use template name if set, otherwise subject
        if obj.journey_static:
            return obj.journey_static.name
        return obj.subject

    def _get_result(self, obj):
        # Prefetched 'results' or fallback to first
        results = getattr(obj, 'prefetched_results', None)
        if results is not None:
            return results[0] if results else None
        # fallback: lookup
        try:
            return JourneyResult.objects.get(journey=obj, user=obj.user)
        except JourneyResult.DoesNotExist:
            return None

    def get_unanswered_count(self, obj):
        result = self._get_result(obj)
        return result.unanswered_count if result else None

    def get_correct_count(self, obj):
        result = self._get_result(obj)
        return result.correct_count if result else None

    def get_wrong_count(self, obj):
        result = self._get_result(obj)
        return result.wrong_count if result else None

    def get_result_id(self, obj):
        result = self._get_result(obj)
        return result.id if result else None

class CurrentTimeSerializer(serializers.Serializer):
    server_time = serializers.DateTimeField()
