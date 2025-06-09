from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.permissions import (
    IsStudentPermission,
    IsOperatorUserPermission,
)
from apps.questions.models import Tag
from apps.questions.serializers import (
    TagSerializer,
    TagTreeSerializer,
    TagPathSerializer
)


# TAG_CACHE_TIME = 1 if settings.DEBUG else 60 * 60 * 120
TAG_CACHE_TIME = 60 * 60 * 120


class TagListAPIView(APIView):
    permission_classes = [
        IsStudentPermission | IsOperatorUserPermission
    ]

    @extend_schema(
        summary="List all Tags",
        tags=["Tag"],
        responses={
            200: OpenApiResponse(
                response=TagSerializer,
                description="Successfully retrieved list of Tags."
            ),
            400: OpenApiResponse(
                description="Invalid or Bad Request"
            ),
        },
    )
    @method_decorator(cache_page(TAG_CACHE_TIME))
    def get(self, request, *args, **kwargs):
        tags = Tag.objects.all()
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TagTreeAPIView(APIView):
    """
    Returns nested tree of tags starting from roots
    """

    permission_classes = [
        IsStudentPermission | IsOperatorUserPermission
    ]

    @extend_schema(
        summary="List all Tags Tree",
        tags=["Tag"],
        responses={
            200: OpenApiResponse(
                response=TagTreeSerializer,
                description="Successfully retrieved list of Tags trees."
            ),
            400: OpenApiResponse(
                description="Invalid or Bad Request"
            ),
        },
    )
    @method_decorator(cache_page(TAG_CACHE_TIME))
    def get(self, request):

        roots = (
            Tag.objects
               .filter(parent=None)
               .order_by('name')        # required by Postgres when using distinct('name')
               .distinct('name')
        )
        print('len of roots', len(list(roots)))
        serializer = TagTreeSerializer(roots, many=True)
        return Response(serializer.data)


class TagPathsAPIView(APIView):
    """
    Returns all root-to-leaf paths
    """

    permission_classes = [
        IsStudentPermission | IsOperatorUserPermission
    ]

    @extend_schema(
        summary="List all Tags paths",
        tags=["Tag"],
        responses={
            200: OpenApiResponse(
                response=TagPathSerializer,
                description="Successfully retrieved list of Tags paths."
            ),
            400: OpenApiResponse(
                description="Invalid or Bad Request"
            ),
        },
    )
    @method_decorator(cache_page(TAG_CACHE_TIME))
    def get(self, request):
        def build_path(tag):
            return [{'id': ancestor.id, 'name': ancestor.name} for ancestor in tag.get_ancestors(include_self=True)]

        leaf_tags = Tag.objects.filter(children=None)
        paths = [build_path(tag) for tag in leaf_tags]
        return Response(paths)
