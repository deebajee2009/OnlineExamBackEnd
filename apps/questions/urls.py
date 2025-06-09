from django.urls import path

from apps.questions.views import (
    QuestionListAPIView,
    TagListAPIView,
    QuestionTagAPIView,
    QuestionActiveAPIView,
    TagTreeAPIView,
    TagPathsAPIView
)


urlpatterns  = [
    # Operator
    path("operator/questions/", QuestionListAPIView.as_view(), name='list-questions'),
    path("user/tags/", TagListAPIView.as_view(), name='tag-list'),
    path("user/tags/tree/", TagTreeAPIView.as_view(), name='tag-tree'),
    path("user/tags/paths/", TagPathsAPIView.as_view(), name='tag-paths'),
    path("operator/question/tag/", QuestionTagAPIView.as_view(), name='question-tag'),
    path("operator/question/active", QuestionActiveAPIView.as_view(), name='question-active'),
]
