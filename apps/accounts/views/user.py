from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
    OpenApiTypes,
)
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.accounts.otp import (
    create_or_get_user,
    generate_otp_to_login_or_signup_and_send_to_user,
    create_token_for_user,
    get_new_access_token,
    user_logout
)
from apps.accounts.serializers.user import *
from apps.accounts.models import User
from apps.accounts.data_class_objects import (
    OutputRequestOtpSerializer,
    MessageOutputSerializer
)
from utils.exceptions import (
    CustomValidationError,
    CustomNotFoundError,
    CustomPermissionError
)
from utils.permissions import *


class OtpRequestLoginOrSignupView(APIView):
    @extend_schema(
        summary="Request OTP code to login/signup",
        tags=["Otp"],
        request=InputRequestOtpLoginOrSignupSerializer,
        responses={
            201: OpenApiResponse(OutputRequestOtpSerializer, description="OTP sent successfully."),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def post(self, request):
        serializer = InputRequestOtpLoginOrSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            create_or_get_user(
                phone_number=serializer.validated_data["phone_number"],
                role=serializer.validated_data["role"]
            )
        except PermissionDenied as e:
            raise e
        except Exception as e:
            raise ValidationError(str(e))

        request_otp_structure_dto = generate_otp_to_login_or_signup_and_send_to_user(
            phone_number=serializer.validated_data["phone_number"]
        )

        return Response(
            OutputRequestOtpSerializer(request_otp_structure_dto).data,
            status=status.HTTP_200_OK,
        )

class OtpLoginOrSignupView(APIView):
    @extend_schema(
        summary="Verify and Signup with OTP code",
        description="""Note: For registration, Frontend must specify the role field. For login,
            this field is not considered by Backend.""",
        tags=["Otp"],
        request=InputOtpLoginOrSignupSerializer,
        responses={
            201: OpenApiResponse(
                OutputTokenSerializer,
                description="""User create/retrieve successfully.""",
            ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def post(self, request):
        serializer = InputOtpLoginOrSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        data = create_token_for_user(user=user)

        return Response(data=data, status=status.HTTP_200_OK)

# class SignUpUserView(APIView):
#     permission = [
#         IsStudentPermission
#     ]
#
#     @extend_schema(
#         summary="register information of Profile",
#         tags=["Profile"],
#         request={"multipart/form-data": ProfileSaveSerializer},
#         responses={
#             201: OpenApiResponse(
#                 ProfileSaveSerializer,
#                 description="extra info saved for user",
#             ),
#         },
#     )
#     def post(self, request, *args, **kwargs):
#         serializer = ProfileSaveSerializer(data=request.data)
#         if serializer.is_valid():
#
#             serializer.save()
#
#             return Response(
#                 data=serializer.data,
#                 status=status.HTTP_201_CREATED
#             )
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    permission_classes = [
        IsStudentPermission
    ]
    @extend_schema(
        summary="fetching data of Profile for dashboard",
        tags=["Profile"],
        responses={
            200: OpenApiResponse(
                UserProfileSerializer,
                description="profile data for dashboard",
                ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def get(self, request, *args, **kwargs):
        try:
            user = User.objects.get(phone_number=request.user.phone_number)
        except User.DoesNotExist:
            return Response(
                {'message': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Creating objectof  Profile ",
        tags=["Profile"],
        request=UserProfileSerializer,
        responses={
            201: OpenApiResponse(
                UserProfileSerializer,
                description="profile data for dashboard",
                ),
            400: OpenApiResponse(description="Invalid or Bad Request"),
        },
    )
    def post(self, request, *args, **kwargs):
        # The serializer will perform phone number validation and profile creation/updating.
        serializer = UserProfileSerializer(data=request.data)
        if serializer.is_valid():
            # serializer.save() calls the create() method defined in the serializer.
            user = serializer.save()
            # For consistency, we return the output using the same serializer.
            output_serializer = UserProfileSerializer(user)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [
        IsStudentPermission
    ]

    @extend_schema(
        summary="Logout from system",
        tags=["auth"],
        request=RefreshTokenSerializer,
        responses={
            200: OpenApiResponse(
                MessageOutputSerializer,
                description="Delete refresh token JTI",
            ),
        },
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_logout(request, serializer.validated_data)
        return Response({"message": "Successfully logout"}, status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
    # Anyone can call this (we’ll do our own checks below)
    permission_classes = [AllowAny]
    # Turn off DRF’s normal JWT header auth here:
    authentication_classes = []

    @extend_schema(
        summary="Get new access token",
        tags=["auth"],
        request=RefreshTokenSerializer,
        responses={
            200: OpenApiResponse(
                description="New access token generated",
                response=OutputTokenSerializer,
            ),
            400: OpenApiResponse(description="Invalid refresh token or user"),
        },
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = get_new_access_token(request.user, serializer.validated_data)
            return Response(result, status=status.HTTP_200_OK)
        except PermissionDenied as e:
            raise CustomPermissionError(f"{str(e)}", code=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            raise CustomValidationError(f"{str(e)}", code=status.HTTP_403_FORBIDDEN)
