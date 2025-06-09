from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.journies.views import (
    StartJourneyAPIView,
    CreateNextQuestionAPIView,
    SubmitAnswerAPIView,
    FinishJourneyAPIView,
    JourneyDetailAPIView,
    GetQuestionAPIView,
    UserJourniesListAPIView,
    OverallReportAPIView,
    OpenStaticGroupJourniesListAPIView,
    # UserStaticJourniesListAPIView,
    CreateJourneyTemplateAPIView,
    StartJourneyGeneralAPIView,
    JourneyViewSet,
    JourneyTemplateExamListAPIView,
    JourneyTemplateGroupExamAPIView,
    UserJourneySummaryListAPIView,
    CurrentTimeAPIView
)


router = DefaultRouter()
router.register(r'journeys', JourneyViewSet, basename='journey')

urlpatterns = [
    # path('journey/static/group/open/', OpenStaticGroupJourniesListAPIView.as_view(), name='open-static-group-journies'),
    path('journey/<int:journey_id>/create-next-question/<int:current_journey_step_id>', CreateNextQuestionAPIView.as_view(), name='next-question'),
    # path('journey/step/<int:step_id>/submit-answer/', SubmitAnswerAPIView.as_view(), name='submit-answer'),
    path('user/journey/step/submit-answer/', SubmitAnswerAPIView.as_view(), name='submit-answer'),
    # path('journey/<int:journey_id>/finish', FinishJourneyAPIView.as_view(), name='finish-journey'),
    path('journey/finish/', FinishJourneyAPIView.as_view(), name='finish-journey'),
    # path('user/journeies/', UserJourniesListAPIView.as_view(), name='user-journey-list'),
    # path('user/static/journeis', UserStaticJourniesListAPIView.as_view(), name='user-static-journies-list'),
    path('journey/<int:journey_id>/', JourneyDetailAPIView.as_view(), name='journey-detail'),
    path('journey/get_question/<int:journey_step_id>/', GetQuestionAPIView.as_view(), name='get-question'),
    path('journey/overall_report/', OverallReportAPIView.as_view(), name='overall-report'),
    path('journey/create-journey/template/', CreateJourneyTemplateAPIView.as_view(), name='create-journey-template'),
    path('journey/start/general/', StartJourneyGeneralAPIView.as_view(), name='start-journey-general'),
    path('', include(router.urls)),
    path('journey/template/exam/list/', JourneyTemplateExamListAPIView.as_view(), name='exam-list'),
    path('journey/template/group-exam/list',JourneyTemplateGroupExamAPIView.as_view(), name='group-exam-list'),
    path('journey/current-time/', CurrentTimeAPIView.as_view(), name='current-time')
    # path(
    #     'journeys/summary/',
    #     UserJourneySummaryListAPIView.as_view(),
    #     name='user-journeys-summary'
    # ),
]
