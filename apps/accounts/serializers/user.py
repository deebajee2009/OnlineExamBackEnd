from typing import Dict
from rest_framework import serializers, status
from django.db import transaction
from django.core.cache import cache

from apps.accounts.models import (
    User,
    Profile,
    RoleTextChoices
)

from apps.accounts.otp import (
    confirm_otp,
    delete_otp_from_cache
)
from apps.accounts.general_validators import validate_phone_number_format


class InputRequestOtpLoginOrSignupSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        max_length=50,
        required=True,
        write_only=True,
        validators=[validate_phone_number_format],
    )
    role = serializers.ChoiceField(
        choices=[
            RoleTextChoices.STUDENT.value,
            RoleTextChoices.OPERATOR.value
        ],
        default=RoleTextChoices.STUDENT,
    )

    # def validate(self, data: Dict[str, str]) -> Dict[str, str]:
    #     user = get_user_by_phone_number(data.get("phone_number"))
    #     if user and user.status == StatusTextChoices.BLOCKED:
    #         raise CustomAuthenticationError("دسترسی کاربر به سامانه قطع شده است")
    #     return data


class InputOtpLoginOrSignupSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=50, required=True)
    otp = serializers.CharField(max_length=5, required=True)

    def validate(self, data):
        phone_number = data["phone_number"]
        otp = data["otp"]

        confirm_otp(key=phone_number, otp=otp, _cache=cache)
        delete_otp_from_cache(phone_number, _cache=cache)

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            raise CustomNotFoundError("کاربر پیدا نشد", code=status.HTTP_404_NOT_FOUND)

        if not user.is_active:
            user.is_active = True
            user.save()

        data["user"] = user
        return data


class OutputTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(max_length=500)
    access = serializers.CharField(max_length=500)
    # completed_profile = serializers.BooleanField(default=False)
    role = serializers.ChoiceField(choices=[key for key, _ in RoleTextChoices.choices])


class UserProfileSerializer(serializers.Serializer):
    # These fields are required for POST input.
    phone_number = serializers.CharField()  # both input and output via our logic
    # Profile fields - not required in GET if profile is incomplete,
    # but expected as input for POST.
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    gender = serializers.CharField(required=False)
    birth_day = serializers.DateField(required=False)
    education = serializers.CharField(required=False)
    province = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    national_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    school_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    acquisition = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # This field is output only.
    profile_completed = serializers.BooleanField(read_only=True)

    def validate_phone_number(self, value):
        # Ensure that a User with the provided phone number exists.
        try:
            user = User.objects.get(phone_number=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this phone number does not exist.")
        return value

    def create(self, validated_data):
        """
        For a POST request, find the User by phone_number, then create (or update)
        its related Profile object with the provided data. Finally, return the User
        so that subsequent serialization (to_representation) uses the same logic as GET.
        """
        phone_number = validated_data.pop("phone_number")
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            # Although validate_phone_number should catch this, be safe.
            raise serializers.ValidationError({"phone_number": "User not found."})

        # Create or update the related Profile using the remaining fields.
        profile, created = Profile.objects.get_or_create(user=user)
        for field, value in validated_data.items():
            setattr(profile, field, value)
        profile.save()

        # Optionally, you might update some field on the User or trigger profile completion logic.
        return user

    def to_representation(self, instance):
        """
        For GET requests, instance is a User object. Based on the User property
        profile_completed, return:
         - If not complete: only the phone number and profile_completed.
         - If complete: the detailed profile fields.
        """
        # This output is independent of fields used for POST input.
        fields = [
            field.name
            for field in Profile._meta.get_fields()
            if not (field.primary_key or field.auto_created)
        ]
        profile_result_dict = {
            "phone_number": instance.phone_number,
            "profile_completed": instance.profile_completed,
        }



        if not instance.profile_completed:
            for model_field in fields:
                profile_result_dict[model_field] = None
            return profile_result_dict
        try:
            # Assume the one-to-one relation's related name is "student_profile".
            profile = instance.student_profile
        except Exception:
            for model_field in fields:
                profile_result_dict[model_field] = None
            return profile_result_dict

        # When the profile is complete, return the profile detail fields.
        return {
            "phone_number": instance.phone_number,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "gender": profile.gender,
            "birth_day": profile.birth_day,
            "education": profile.education,
            "province": profile.province,
            "city": profile.city,
            "national_code": profile.national_code,
            "school_name": profile.school_name,
            "acquisition": profile.acquisition,
            "profile_completed": True
        }

# class UserProfileSerializer(serializers.Serializer):
#     phone_number = serializers.CharField(write_only=True)
#     first_name = serializers.CharField(required=True)
#     last_name = serializers.CharField(required=True)
#     gender = serializers.CharField(required=True)
#     birth_day = serializers.DateField(required=True)  # Added birth_day field
#     education = serializers.CharField(required=True)
#     province = serializers.CharField(required=True)
#     city = serializers.CharField(required=True)
#     national_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
#     school_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
#     acquisition = serializers.CharField(required=False, allow_blank=True, allow_null=True)
#     completed_profile = serializers.BooleanField(default=False)
#
#     def validate_phone_number(self, value):
#         """
#         Validates that a user exists with the given phone number.
#         """
#         try:
#             user = User.objects.get(phone_number=value)
#         except User.DoesNotExist:
#             raise serializers.ValidationError("No user found with this phone number.")
#         # Store the user instance in the serializer context for later use.
#         self.context['user'] = user
#         return value
#
#     def get_profile(self, obj):
#         """
#         Retrieves profile data for the validated user.
#         """
#         user = self.context.get('user')
#         if not user:
#             return {}
#         profile = getattr(user, 'profile', None)
#         if not profile:
#             return {}
#
#         # Customize the profile data as needed.
#         return {
#             "id": profile.id,
#             "bio": profile.bio,
#             # Add additional profile fields here.
#         }
#
#     def to_representation(self, validated_data):
#         """
#         Customize the final output to include the user's phone number and profile data.
#         """
#         user = self.context.get('user')
#         ret = {
#             "phone_number": user.phone_number,
#             "profile": self.get_profile(validated_data)
#
#         }
#         return ret


class ProfileSaveSerializer(serializers.Serializer):
    phone_number = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    gender = serializers.CharField(required=True)
    birth_day = serializers.DateField(required=True)  # Added birth_day field
    education = serializers.CharField(required=True)
    province = serializers.CharField(required=True)
    city = serializers.CharField(required=True)
    national_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    school_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    acquisition = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_phone_number(self, value):
        """
        Validate that a User exists with the provided phone number.
        """
        try:
            user = User.objects.get(phone_number=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this phone number does not exist.")
        # Store the user instance in the context for later use
        self.context['user'] = user
        return value

    @transaction.atomic
    def create(self, validated_data):
        """
        Create or update the Profile associated with the User.
        """
        user = self.context['user']
        # Remove phone_number from validated_data because Profile doesn't have this field.
        validated_data.pop('phone_number', None)
        # Update or create the profile associated with this user.
        profile, created = Profile.objects.update_or_create(user=user, defaults=validated_data)
        user.profile_completed = True
        user.save()
        return profile

    def update(self, instance, validated_data):
        """
        Update an existing Profile instance.
        """
        # Loop through the remaining fields and update using setattr.
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    def to_representation(self, instance):
        """
        Return a representation of the Profile data.
        """
        return {
            "phone_number": instance.user.phone_number,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
            "gender": instance.gender,
            "birth_day": instance.birth_day,
            "education": instance.education,
            "province": instance.province,
            "city": instance.city,
            "national_code": instance.national_code,
            "school_name": instance.school_name,
            "acquisition": instance.acquisition
        }

class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True, write_only=True, min_length=1)
