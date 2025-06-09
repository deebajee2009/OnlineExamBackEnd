from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.questions.paginations import CustomPagination

from utils.permissions import IsOperatorUserPermission
from apps.questions.models import Question
from apps.questions.serializers import (
    QuestionSerializer,
    QuestionTagSerializer,
    QuestionActiveSerializer,
    OperatorQuestionSerializer
)



class QuestionListAPIView(APIView):
    permission_classes = [IsOperatorUserPermission]
    pagination_class = CustomPagination

    @extend_schema(
        summary="Getting list of all questions",
        tags=["Question"],
        request=OperatorQuestionSerializer,
        responses={
            200: OpenApiResponse(
                OperatorQuestionSerializer,
                description="Getting list of all questions"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def get(self, request, *args, **kwargs):
        questions = Question.objects.all()

        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(questions, request)
        serializer = OperatorQuestionSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)



class QuestionTagAPIView(APIView):
    permission_classes = [IsOperatorUserPermission]

    @extend_schema(
        summary="Add one or more tags to a question",
        tags=["Question"],
        request=QuestionTagSerializer,
        responses={
            200: OpenApiResponse(
                response=QuestionSerializer,
                description="Question updated with new tags"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def patch(self, request, *args, **kwargs):
        q_id       = request.data.get('question_id')
        # 1 query: grab question *and* existing tags
        question   = (Question.objects
                        .prefetch_related('tags')
                        .get(pk=q_id))
        serializer = QuestionTagSerializer(
            instance=question,
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        return Response(QuestionSerializer(question).data, status=status.HTTP_200_OK)


class QuestionActiveAPIView(APIView):
        permission_classes = [IsOperatorUserPermission]

        @extend_schema(
            summary="Add one or more tags to a question",
            tags=["Question"],
            request=QuestionActiveSerializer,
            responses={
                200: OpenApiResponse(
                    response=QuestionSerializer,
                    description="Question updated with new tags"
                ),
                400: OpenApiResponse(description="Invalid or Bad Request"),
            },
        )
        def patch(self, request, *args, **kwargs):
            # 1) validate payload
            serializer = QuestionActiveSerializer(data=request.data)
            if serializer.is_valid():
                question = serializer.question_object

                # 3) perform the M2M add
                new_instance = serializer.update(question, serializer.validated_data)

                # 4) return full serialized question
                out_serializer = QuestionSerializer(new_instance)
                return Response(out_serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
