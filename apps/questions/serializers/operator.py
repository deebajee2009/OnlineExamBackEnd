from rest_framework import serializers
from apps.questions.models import (
    Question,
    Tag
)
from utils.exceptions import (
    CustomNotFoundError,
    CustomValidationError
)


class QuestionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)


    class Meta:
        model = Question
        fields = [
            'id',
            'text_body',
            'choice_1',
            'choice_2',
            'choice_3',
            'choice_4',
            'true_choice',
            'answer',
            'direction',
        ]

    # def get_tags(self, obj):
    #     """
    #     Returns a list of names of the Tag objects associated with the Question.
    #     """
    #     return [tag.name for tag in obj.tags.all()]

class OperatorQuestionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            'id',
            'text_body',
            'choice_1',
            'choice_2',
            'choice_3',
            'choice_4',
            'true_choice',
            'is_active',
            'true_choice',
            'answer',
            'hardness',
            'tags',
            'created_at',
            'direction'            
        ]

    def get_tags(self, obj):
        """
        Returns a list of names of the Tag objects associated with the Question.
        """
        return [tag.name for tag in obj.tags.all()]

class QuestionTagSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    tags        = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )

    def validate_tags(self, tag_id_list):
         # 1 query to fetch all matching Tags
        tags = list(Tag.objects.filter(pk__in=tag_id_list))
        if len(tags) != len(tag_id_list):
            missing = set(tag_id_list) - {t.id for t in tags}
            raise CustomValidationError(
                f"Tags not found: {missing}"
            )
        return tags
    def save(self):
        # self.instance is the Question from the view
        question = self.instance
        tags     = self.validated_data['tags']  # already a list of Tag objs
        # This issues just *one* set of SQL statements:
        question.tags.set(tags)
        return question

class QuestionActiveSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    is_active = serializers.BooleanField()

    def validate_question_id(self, value):
        try:
            question = Question.objects.get(pk=value)
            # Store the retrieved Question object in the serializer instance
            self.question_object = question
            return value
        except Question.DoesNotExist:
            raise CustomNotFoundError("Question with this ID does not exist.")

    def update(self, instance: Question, validated_data):
        # instance will often be None, so pull from self.question_object
        question = getattr(self, 'question_object', instance)
        question.is_active = validated_data['is_active']
        question.save(update_fields=['is_active'])
        return question
