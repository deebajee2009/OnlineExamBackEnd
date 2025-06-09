from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
from django.db.models import Count, Q, F

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    OpenApiParameter,
    extend_schema_view
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, generics, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView


from apps.journies.next_journey_step import  get_next_journey_step
from apps.journies.serializers  import (
    JourneyStepAnswerSerializer,
    QuestionSerializer,
    JourneyCreateSerializer,
    JourneyFinishSerializer,
    NexstQuestionSerializer,
    JourneyListSerializer,
    JourneyDetailSerializer,
    QuestionDetailSerializer,
    OpenGroupExamJourneySerializer,
    StaticJourneyListSerializer,
    CreateJourneyTemplateSerializer,
    StartJourneyGeneralSerializer,
    JourneyStepSerializer,
    JourneySerializer,
    JourneyTemplateSerializer,
    UserJourneySummarySerializer,
    CurrentTimeSerializer
)
from utils.permissions import IsStudentPermission
from apps.journies.models import (
    JourneyStep,
    Journey,
    StaticJourneyType,
    JourneyTemplate,
    JourneyStepTemplate,
)
from apps.journies.paginations import CustomPagination
from apps.journies.serializers.user import JourneyStepSerializer


class StartJourneyAPIView(APIView):
    """
    POST endpoint to start a new journey (quiz).
    Creates a Journey record with the provided subject and limits.
    Immediately returns the first question in a JourneyStep.
    """
    permission_classes = [
        IsStudentPermission
    ]

    @extend_schema(
        summary="Start journey for user",
        tags=["Journey"],
        request=JourneyCreateSerializer,
        responses={
            201: OpenApiResponse(
                JourneyCreateSerializer,
                description="start the journey"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = JourneyCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            journey = serializer.save()
            # Retrieve the first question using journey.get_next_question()
            next_question = get_next_question(journey)
            if not next_question:
                return Response({"detail": "No available question."}, status=status.HTTP_400_BAD_REQUEST)
            # Create a JourneyStep for the first question.
            journey_step = JourneyStep.objects.create(journey=journey, question=next_question)
            # journey_step_data = JourneyStepSerializer(journey_step).data
            first_question = QuestionSerializer(next_question).data
            return Response({
                "journey_id": journey.journey_id,
                "step_id": journey_step.step_id,
                "first_question": first_question,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FinishJourneyAPIView(APIView):
    permission_classes = [
        IsStudentPermission
    ]

    @extend_schema(
        summary="Finish the journey of user",
        tags=["Journey"],
        request=JourneyFinishSerializer,
        responses={
            201: OpenApiResponse(
                JourneyFinishSerializer,
                description="Finishing the journey"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def post(self, request):
        serializer = JourneyFinishSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            journey = serializer.save()
            now     = timezone.now()

            if journey.journey_static and journey.journey_type == StaticJourneyType.GROUP_EXAM:
                return Response({"message":"Group exam finished successful"}, status=status.HTTP_204_NO_CONTENT)


            if journey.finished_at and journey.finished_at <= now and journey.answered_count is None:
                last = journey.last_seen_journey_step
                if last:
                    # a) count up through last_seen_journey_step
                    agg = (
                        JourneyStep.objects
                        .filter(journey=journey, step_id__lte=last.step_id)
                        .aggregate(
                            total_questions = Count('pk'),
                            true_answers    = Count('pk', filter=Q(user_answer=F('question__true_choice'))),
                            unanswered      = Count('pk', filter=Q(user_answer__isnull=True)),
                            false_answers   = Count('pk', filter=~Q(user_answer__isnull=True) &
                                                        ~Q(user_answer=F('question__true_choice'))),
                        )
                    )
                    total_q    = agg['total_questions']
                    unanswered = agg['unanswered']
                    true_ans   = agg['true_answers']
                    false_ans  = agg['false_answers']

                    # b) if it’s an exam, adjust unanswered against all available steps
                    if journey.journey_type == StaticJourneyType.EXAM:
                        total_available = JourneyStep.objects.filter(journey=journey).count()
                        unanswered = total_available - total_q + unanswered
                        total_q = total_available


                    # c) populate the Journey fields
                    journey.answered_count   = true_ans + false_ans
                    journey.unanswered_count = unanswered
                    journey.correct_count    = true_ans
                    journey.wrong_count      = false_ans
                    journey.save(update_fields=[
                        'answered_count', 'unanswered_count',
                        'correct_count',  'wrong_count'
                    ])

                response_data = {
                    'journey_id': journey.journey_id,
                    'result': {
                        'total_questions' : total_q,
                        'true_answers'    : true_ans,
                        'false_answers'   : false_ans,
                        'unanswered'      : unanswered,
                        'finished_at'     : journey.finished_at,
                        'created_at'      : journey.created_at,
                        'subject'         : journey.subject,
                        'journey_type'    : journey.journey_type
                    }
                }

                return Response(response_data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateNextQuestionAPIView(APIView):
    """
    GET endpoint to retrieve the next question for an active journey.
    The journey ID is passed in the URL.
    """
    permission_classes = [
        IsStudentPermission
    ]

    @extend_schema(
        summary="Getting the next question",
        tags=["Question"],
        parameters=[
            OpenApiParameter(
                name="journey_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the journey",
            ),
            OpenApiParameter(
                name="current_journey_step_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the current journey step",
            ),
        ],
        request=NexstQuestionSerializer,
        responses={
            200: OpenApiResponse(
                JourneyStepSerializer,
                description="Getting the next question"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def post(self, request, journey_id, current_journey_step_id, *args, **kwargs):

        serializer = NexstQuestionSerializer(
            data=request.data,
            context={
                'request': request,
                "journey_id": journey_id,
                "current_journey_step_id": current_journey_step_id,
            }
        )
        if serializer.is_valid():
            next_journey_step = get_next_journey_step(journey_id, current_journey_step_id)
            if not next_journey_step:
                return Response(
                    {"message": "Journey is not Active or no Questions"},
                    status=status.HTTP_204_NO_CONTENT
                )

            journey = next_journey_step.journey

            journey.last_seen_journey_step = next_journey_step
            journey.save(update_fields=['last_seen_journey_step'])

            serializer = JourneyStepSerializer(next_journey_step)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubmitAnswerAPIView(APIView):
    """
    POST endpoint for submitting an answer for a JourneyStep.
    The journey step is updated with the user's answer; during save(),
    the answered_at and time_taken are automatically set.
    """
    permission_classes = [
        IsStudentPermission
    ]

    @extend_schema(
        summary="Submiting answer of question",
        tags=["Answer"],
        request=JourneyStepAnswerSerializer,
        responses={
            201: OpenApiResponse(
                JourneyStepAnswerSerializer,
                description="submiting the answer of question"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = JourneyStepAnswerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # This calls the custom save() on JourneySteps
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserJourniesListAPIView(APIView):
    permission_classes = [
        IsStudentPermission
    ]

    @extend_schema(
        summary="Getting the list of User journies",
        tags=["Journey"],
        request=JourneyListSerializer,
        responses={
            200: OpenApiResponse(
                JourneyListSerializer,
                description="Getting the list of user journies"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def get(self, request, *args, **kwargs):
        journies = Journey.objects.filter(user=request.user).order_by('-created_at')

        # 2) paginate
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(journies, request, view=self)

        # 3) serialize
        serializer = JourneyListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class JourneyDetailAPIView(generics.RetrieveAPIView):
    permission_classes = [IsStudentPermission]

    @extend_schema(
        summary="Fetch detail of a journey",
        tags=["Journey"],

        responses={
            201: OpenApiResponse(
                JourneyDetailSerializer,
                description="submiting the answer of question"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def get(self, request, journey_id):
        journey = get_object_or_404(Journey, journey_id=journey_id, user=request.user)
        journey_steps = JourneyStep.objects.filter(journey=journey)

        questions_data = []
        for step in journey_steps:
            questions_data.append({
                'id': step.step_id,
            })

        last_question = None

        last_step = journey.last_seen_journey_step
        if last_step:
            last_seen_journey_step = {
                'step_id'    : last_step.step_id,
                'question_id': last_step.question.id,
                'text_body'  : last_step.question.text_body,
                'choice_1'   : last_step.question.choice_1,
                'choice_2'   : last_step.question.choice_2,
                'choice_3'   : last_step.question.choice_3,
                'choice_4'   : last_step.question.choice_4,
                'direction'  : last_step.question.direction,
                'answer'     : last_step.question.answer,
            }
        else:
            last_seen_journey_step = None

        # Prepare journey data
        journey_data = {
            'journey_id': journey.journey_id,
            'subject': journey.subject,
            'time_minutes_limit': journey.time_minutes_limit,
            'question_count_limit': journey.question_count_limit,
            'created_at': journey.created_at,
            'is_active': journey.is_active(),
            'journey_steps': questions_data,
            'questions_count': len(questions_data),
            'last_seen_journey_step': last_seen_journey_step,
            'finished_at': journey.finished_at
        }

        return Response(journey_data)


class GetQuestionAPIView(generics.RetrieveAPIView):
    queryset = JourneyStep.objects.select_related('journey', 'question')
    lookup_field = 'step_id'
    lookup_url_kwarg = 'journey_step_id'
    permission_classes = [IsStudentPermission]

    @extend_schema(
        summary="Fetch detail of a journey_step question",
        tags=["Journey"],

        responses={
            201: OpenApiResponse(
                QuestionDetailSerializer,
                description="Fetch detail of question from journey_step"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def get(self, request, *args, **kwargs):

        journey_step = self.get_object()
        journey = journey_step.journey  # no extra query here!

        if not journey.is_active():
            return Response({"message":"Journey is not active"}, status=status.HTTP_204_NO_CONTENT)
        question = journey_step.question  # also no extra query

        # 3) Update last_seen_journey_step on the parent Journey
        journey.last_seen_journey_step = journey_step
        journey.save(update_fields=['last_seen_journey_step'])

        # journey_step = get_object_or_404(JourneyStep, step_id=journey_step_id)
        #
        # journey.last_seen_journey_step =
        # journey.save()
        # # # Check if the requesting user is the same as the journey's user
        # # if request.user != journey_step.journey.user:
        # #     return Response(
        # #         {"detail": "You do not have permission to access this question."},
        # #         status=status.HTTP_403_FORBIDDEN
        # #     )
        #
        # question = journey_step.question
        response = {
            'step_id': journey_step.step_id,
            'journey_id': journey_step.journey.journey_id,
            'question': {
                'text_body'  : question.text_body,
                'choice_1'   : question.choice_1,
                'choice_2'   : question.choice_2,
                'choice_3'   : question.choice_3,
                'choice_4'   : question.choice_4,
                'true_choice': question.true_choice,
                'answer'     : question.answer,
                'hardness'   : question.hardness,
                'direction'  :question.direction
            },
            'user_answer': journey_step.user_answer,
            'answer_result': journey_step.answer_result,
        }
        return Response(response)

class OverallReportAPIView(APIView):
    permission_classes = [
        IsStudentPermission
    ]

    @extend_schema(
        summary="Get overall statistics of user's journeys",
        tags=["Journey"],
        responses={
            200: OpenApiResponse(
                description="Overall statistics of user's journeys"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def get(self, request):
        # Get all journeys for the user
        user_journeys = Journey.objects.filter(user=request.user)

        # Initialize counters
        total_questions = 0
        true_answers = 0
        false_answers = 0
        unanswered = 0
        total_hours = timedelta()

        # Process each journey
        for journey in user_journeys:
            # Get all steps for this journey
            journey_steps = JourneyStep.objects.filter(journey=journey)

            # Count answers for this journey
            total_questions += journey_steps.count()
            for step in journey_steps:
                if step.user_answer is None:
                    unanswered += 1
                elif step.user_answer == step.question.true_choice:
                    true_answers += 1
                else:
                    false_answers += 1

            # Calculate time spent on this journey
            if journey.finished_at:
                journey_duration = journey.finished_at - journey.created_at
                total_hours += journey_duration

        # Convert total hours to hours (float)
        total_hours_float = total_hours.total_seconds() / 3600

        response_data = {
            'result': {
                'total_questions': total_questions,
                'true_answers': true_answers,
                'false_answers': false_answers,
                'unanswered': unanswered,
                'total_hours': round(total_hours_float, 2)
            }
        }

        return Response(response_data)


class OpenStaticGroupJourniesListAPIView(APIView):
    permission_classes = [
        IsStudentPermission
    ]
    pagination_class = CustomPagination

    @extend_schema(
        summary="List open group exam journies",
        tags=["Journey"],

        responses={
            200: OpenApiResponse(
                OpenGroupExamJourneySerializer,
                description="list open group exam journies"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def get(self, request, *args, **kwargs):
        group_exams_journies = Journey.objects.filter(journey_type=StaticJourneyType.GROUP_EXAM).order_by('-created_at')
        open_group_exams_journies = [journey for journey in group_exams_journies if group_exams_journies.is_active()]

        # 2) paginate
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(open_group_exams_journies, request, view=self)

        # 3) serialize
        serializer = OpenGroupExamJourneySerializer(
            page,
            many=True
        )
        return paginator.get_paginated_response(serializer.data)


class UserStaticJourniesListAPIView(APIView):
    permission_classes = [
        IsStudentPermission
    ]
    pagination_class = CustomPagination

    @extend_schema(
        summary="List static journies of User",
        tags=["Journey"],

        responses={
            200: OpenApiResponse(
                StaticJourneyListSerializer,
                description="list static journies of User"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def get(self, request, *args, **kwargs):
        user_static_journies = Journey.objects.filter(
            user=request.user,
            journey_type__in=[StaticJourneyType.EXAM, StaticJourneyType.GROUP_EXAM]
        ).order_by('-created_at')
        # 2) paginate
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(user_static_journies, request, view=self)

        serializer = StaticJourneyListSerializer(
            page,
            many=True
        )
        return paginator.get_paginated_response(serializer.data)

class CreateJourneyTemplateAPIView(APIView):
    permission_classes = [
        IsStudentPermission
    ]

    @extend_schema(
        summary="Create journey from template",
        tags=["Journey"],
        request=CreateJourneyTemplateSerializer,
        responses={
            200: OpenApiResponse(
                JourneyStepSerializer,
                description="create journey from template"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = CreateJourneyTemplateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            journey = serializer.save()
            journey_step = get_next_journey_step(journey.journey_id)
            if not journey_step:
                return Response({"detail": "No available step."}, status=status.HTTP_400_BAD_REQUEST)

            journey.last_seen_journey_step = journey_step
            journey.save(update_fields=['last_seen_journey_step'])

            step_serialier = JourneyStepSerializer(journey_step)
            return Response(
                step_serialier.data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StartJourneyGeneralAPIView(APIView):
    permission_classes = [
        IsStudentPermission
    ]

    @extend_schema(
        summary="Create general journey",
        tags=["Journey"],
        request=StartJourneyGeneralSerializer,
        responses={
            200: OpenApiResponse(
                JourneyStepSerializer,
                description="create journey from template"
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )

    def post(self, request, *args, **kwargs):
        serializer = StartJourneyGeneralSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            journey = serializer.save()
            journey_step = get_next_journey_step(journey.journey_id)

            if not journey_step:
                return Response({"detail": "No available step."}, status=status.HTTP_400_BAD_REQUEST)

            journey.last_seen_journey_step = journey_step
            journey.save(update_fields=['last_seen_journey_step'])

            step_serialier = JourneyStepSerializer(journey_step)
            return Response(
                step_serialier.data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class JourneyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset that returns all of the authenticated user's journeys,
    optionally filtered by journey_type.
    """
    serializer_class   = JourneySerializer
    pagination_class   = CustomPagination
    permission_classes = [IsStudentPermission]
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['journey_type']

    def get_queryset(self):
        user = self.request.user
        now  = timezone.now()

        qs = Journey.objects.filter(user=user).order_by('-created_at')
        to_update = []

        for journey in qs:
            if not (journey.journey_static and journey.journey_type == StaticJourneyType.GROUP_EXAM):
                # Only act on truly finished journeys that haven't been computed yet
                if journey.finished_at and journey.finished_at <= now and journey.answered_count is None:
                    last = journey.last_seen_journey_step
                    if not last:
                        continue

                    # 1) Count only up through last_seen_journey_step
                    steps = JourneyStep.objects.filter(
                        journey=journey,
                        step_id__lte=last.step_id
                    )
                    agg = steps.aggregate(
                        total_questions = Count('pk'),
                        true_answers    = Count('pk', filter=Q(user_answer=F('question__true_choice'))),
                        unanswered      = Count('pk', filter=Q(user_answer__isnull=True)),
                        false_answers   = Count('pk', filter=~Q(user_answer__isnull=True) &
                                                    ~Q(user_answer=F('question__true_choice'))),
                    )

                    total_q    = agg['total_questions']
                    unanswered = agg['unanswered']
                    true_ans   = agg['true_answers']
                    false_ans  = agg['false_answers']

                    # 2) If this is an exam, adjust unanswered based on all available steps
                    if journey.journey_type == StaticJourneyType.EXAM:
                        total_available = JourneyStep.objects.filter(journey=journey).count()
                        # new_unanswered = total_available - total_q + unanswered
                        unanswered = total_available - total_q + unanswered

                    # 3) Populate model fields
                    journey.answered_count   = true_ans + false_ans
                    journey.unanswered_count = unanswered
                    journey.correct_count    = true_ans
                    journey.wrong_count      = false_ans

                    to_update.append(journey)

                    if to_update:
                        Journey.objects.bulk_update(
                            to_update,
                            [
                                'answered_count',
                                'unanswered_count',
                                'correct_count',
                                'wrong_count',
                            ]
                        )

        return qs

    @extend_schema(
        summary="List journeys by type",
        tags=["Journey"],
        # declare the required query-param explicitly:
        parameters=[
            OpenApiParameter(
                name="journey_type",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter journeys by this StaticJourneyType (e.g. 'exam')",
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination",
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of items per page (max 100)",
            ),
        ],
        # document the possible responses:
        responses={
            200: OpenApiResponse(
                response=JourneySerializer(many=True),
                description="A paginated list of the user's journeys of the given type"
            ),
            400: OpenApiResponse(
                description="Missing or invalid query parameter"
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or invalid"
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        """
        GET /journeys/?journey_type=<optional>&page=<n>&page_size=<m>

        If `journey_type` is present, only those journeys are returned.
        Results are paginated according to your CustomPagination settings.
        """
        return super().list(request, *args, **kwargs)


@extend_schema(
        summary="List all exam‐type journey templates",
        tags=["Journey"],
        responses={
            200: OpenApiResponse(
                JourneyTemplateSerializer(many=True),
                description="A list of all JourneyTemplate objects with journey_type=EXAM, ordered by descending id"
            ),
            401: OpenApiResponse(description="Authentication credentials were not provided or invalid"),
            403: OpenApiResponse(description="You do not have permission to perform this action"),
        }
)
class JourneyTemplateExamListAPIView(generics.ListAPIView):
    """
    API endpoint that lists all JourneyTemplate instances
    where journey_type == EXAM, ordered by descending id.
    """
    permission_classes = [IsStudentPermission]
    serializer_class = JourneyTemplateSerializer

    def get_queryset(self):
        return (
            JourneyTemplate.objects
            .filter(journey_type=StaticJourneyType.EXAM)
            .order_by('-id')
        )


    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@extend_schema(
    summary="List non expired group‐exam journey templates",
    tags=["Journey"],
    responses={
        200: OpenApiResponse(
            JourneyTemplateSerializer,
            description=(
                "A list of all JourneyTemplate objects with journey_type=GROUP_EXAM "
                "whose (start_datetime + time_minutes_limit) is before now, ordered by descending id"
            )
        ),
        401: OpenApiResponse(description="Authentication credentials were not provided or invalid"),
        403: OpenApiResponse(description="You do not have permission to perform this action"),
    }
)
class JourneyTemplateGroupExamAPIView(generics.ListAPIView):
    """
    API endpoint that lists all JourneyTemplate instances
    where journey_type == GROUP_EXAM and
    (start_datetime + time_minutes_limit minutes) < now,
    ordered by descending id.
    """
    permission_classes = [IsStudentPermission]
    serializer_class = JourneyTemplateSerializer

    def get_queryset(self):
        now = timezone.now()
        # Base queryset filtered by type and ordered
        qs = JourneyTemplate.objects.filter(
            journey_type=StaticJourneyType.GROUP_EXAM
        ).order_by('-id')
        # Python-level filter for expiration
        valid_templates = []
        for jt in qs:
            if jt.start_datetime and jt.time_minutes_limit is not None:
                expiry = jt.start_datetime + timedelta(minutes=jt.time_minutes_limit)
                if expiry > now:
                    valid_templates.append(jt)
        return valid_templates


    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@extend_schema(
    summary="List all the history for the current student",
    tags=["Journey"],
    responses={
        200: OpenApiResponse(
            UserJourneySummarySerializer(many=True),
            description="A list of journey summaries for the authenticated user"
        ),
        401: OpenApiResponse(description="Authentication credentials were not provided or invalid"),
        403: OpenApiResponse(description="You do not have permission to view these journeys"),
    }
)
class UserJourneySummaryListAPIView(generics.ListAPIView):
    """
    Lists all journeys for request.user, combining Journey, JourneyTemplate (name), and JourneyResult.
    """
    permission_classes = [IsStudentPermission]
    serializer_class = UserJourneySummarySerializer

    def get_queryset(self):
        # Prefetch results for efficiency
        results_prefetch = Prefetch(
            'result',  # related_name on JourneyResult
            queryset=JourneyResult.objects.filter(user=self.request.user),
            to_attr='prefetched_results'
        )
        # Filter journeys by user and prefetch
        return (
            Journey.objects
                .filter(user=self.request.user)
                .select_related('journey_static')
                .prefetch_related(results_prefetch)
                .order_by('-id')
        )

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class CurrentTimeAPIView(APIView):
    permission_classes = [
        IsStudentPermission
    ]

    @extend_schema(
        summary="Get current time of server",
        tags=["Journey"],
        responses={
            200: OpenApiResponse(
                response=CurrentTimeSerializer,
                description="get current server time"
            ),
        },
    )
    def get(self, request):
        now = timezone.now()
        time_data = {
            'server_time': now
        }

        return Response(CurrentTimeSerializer(time_data).data, status=status.HTTP_200_OK)
