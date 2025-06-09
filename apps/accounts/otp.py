import random
import re
from typing import Optional

from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from datetime import datetime
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.request import Request
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from apps.accounts.sms import send_sms
from utils.exceptions import (
    CustomAuthenticationError,
    CustomNotFoundError,
    CustomPermissionError,
    CustomValidationError,
)
from apps.accounts.models import (
    Profile,
    User,
    RoleTextChoices,
)

from utils.time_utility import (
    convert_datetime_into_str,
    convert_str_into_datetime
)

from apps.accounts.data_class_objects import (
    OtpStructureDTO,
    RequestOtpStructureDTO
)
from utils.auth import CustomRefreshToken
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)


def validate_phone_number_format(phone_number: str) -> None:
    rule = re.compile(r"^((\+98|0|0098)9\d{9})$")
    if not rule.search(phone_number):
        raise CustomValidationError(
            "فرمت شماره موبایل نامعتبر است.", code=status.HTTP_400_BAD_REQUEST
        )


def generate_otp(start=10000, stop=99999) -> str:
    return str(random.randrange(start, stop))


def unify_phone_number(phone_number: str) -> str:
    if phone_number[0] == "+":
        phone_number = "0" + phone_number[3:]
    elif phone_number[0:2] == "00":
        phone_number = "0" + phone_number[4:]
    return phone_number


def make_otp_output_structure(
    otp_structure_dto: OtpStructureDTO, is_send_before: bool, expiry_time: int
) -> RequestOtpStructureDTO:
    remaining_time = (
        expiry_time
        - (
            datetime.now() - convert_str_into_datetime(otp_structure_dto.created_time)
        ).seconds
    )
    return RequestOtpStructureDTO(
        remaining_time=remaining_time, is_send_before=is_send_before
    )


def set_otp_in_cache(key, otp, expiry_time, _cache) -> RequestOtpStructureDTO:
    if _cache.get(key):
        return make_otp_output_structure(
            otp_structure_dto=_cache.get(key),
            is_send_before=True,
            expiry_time=expiry_time,
        )
    else:
        otp_structure_dto = OtpStructureDTO(
            otp=otp, created_time=convert_datetime_into_str(datetime.now())
        )
        _cache.set(key, otp_structure_dto, expiry_time)
        return make_otp_output_structure(
            otp_structure_dto=otp_structure_dto,
            is_send_before=False,
            expiry_time=expiry_time,
        )


def send_otp_by_sms(receiver_number, otp_code) -> None:
    # TODO: Implement this later!
    pass


def confirm_otp(key: str, otp: str, _cache) -> None:
    otp_structure_dto: OtpStructureDTO = _cache.get(key)

    if not otp_structure_dto:
        raise CustomNotFoundError(
            "کد فعال‌سازی منقضی شده است.", code=status.HTTP_404_NOT_FOUND
        )

    if otp != str(otp_structure_dto.otp):
        raise CustomValidationError(
            "کد وارد شده نامعتبر است.", code=status.HTTP_400_BAD_REQUEST
        )


def generate_otp_to_login_or_signup_and_send_to_user(
    phone_number: str,
) -> RequestOtpStructureDTO:
    EXPIRE_TIME: Final[int] = 60 * 5

    otp = 11111 if settings.DEBUG else generate_otp()
    # otp = generate_otp()


    # TODO: This cache is not cross-process, so you will need to reconfigure it later.
    request_otp_structure_dto = set_otp_in_cache(
        key=unify_phone_number(phone_number),
        otp=otp,
        expiry_time=EXPIRE_TIME,
        _cache=cache,
    )
    if not request_otp_structure_dto.is_send_before:
        # send_sms(phone_number, otp)
        if not settings.DEBUG:
            send_sms(phone_number, otp)
        # send_otp_by_sms(
        #     receiver_number=phone_number,
        #     otp_code=otp,
        # )

        # Send sms to celery
        # if not settings.DEBUG:
        #     send_sms_task.delay(
        #         phone_number, settings.SMS_TEMPLATE_CODES["OTP"], {"otp": otp}
        #     )
    return request_otp_structure_dto


def delete_otp_from_cache(key: str, _cache) -> bool:
    """
    Delete the OTP from the cache.
    :param key: The key to delete from the cache.
    :param _cache: The cache to delete the key from.
    :return: True if the key was deleted, False otherwise.
    """
    return _cache.delete(key)


def create_token_for_user(user: User) -> dict:
    refresh = CustomRefreshToken.for_user(user)
    token = {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "role": user.role,
        "phone_number": user.phone_number,
    }
    return token


def create_or_get_user(
    phone_number: str, role: str, avoid_creations: Optional[bool] = False
) -> User:
    phone_number = unify_phone_number(phone_number)
    user = User.objects.filter(phone_number=phone_number).first()

    if user:
        if avoid_creations:
            raise CustomValidationError(
                "کاربری با این شماره موبایل وجود دارد", code=status.HTTP_400_BAD_REQUEST
            )
        if user.role != role:
            raise CustomPermissionError(
                "عدم تطابق شماره موبایل با نوع کاربر", code=status.HTTP_403_FORBIDDEN
            )
        return user

    if role in RoleTextChoices.STUDENT:
        user = User.objects.create(
            phone_number=phone_number,
            role=role,
            last_login=timezone.now(),
            is_active=False,
        )
        return user
    elif role == RoleTextChoices.OPERATOR:
        if settings.DEBUG:
            user = User.objects.create(
                phone_number=phone_number,
                role=role,
                last_login=timezone.now(),
                is_active=False,
            )

            return user
        else:
            raise CustomNotFoundError(
                "کاربر اپراتور وجود ندارد", code=status.HTTP_404_NOT_FOUND
            )
    else:
        raise CustomNotFoundError(
            "کاربر اپراتور وجود ندارد", code=status.HTTP_404_NOT_FOUND
        )

def get_new_access_token(user: User, data: dict) -> dict:
    try:
        refresh_token = RefreshToken(data.get("refresh"))
    except TokenError as e:
        raise InvalidToken("Refresh token is invalid or expired.")
    try:
        phone_number = refresh_token.payload.get("phone_number")
    except:
        raise InvalidToken("Refresh token has no phone number.")

    try:
        get_user_phone_number = User.objects.get(id=refresh_token.payload.get("id"))

    except User.DoesNotExist:
        raise CustomNotFoundError("کاربر پیدا نشد.", code=status.HTTP_404_NOT_FOUND)

    # if not user.is_active or not get_user.is_active:
    #     raise CustomPermissionError(
    #         "کاربر نامعتبر است.", code=status.HTTP_403_FORBIDDEN
    #     )

    # if user.id != get_user_phone_number.id:
    #     raise CustomPermissionError(
    #         "کاربر نامعتبر است.", code=status.HTTP_403_FORBIDDEN
    #     )
    if get_user_phone_number.phone_number != phone_number:
        raise CustomPermissionError("phone numbers are not equal.")

    new_access_token = refresh_token.access_token
    return {
        "access": str(new_access_token),
        "refresh": str(data.get("refresh")),
    }
def user_logout(request: Request, data: dict) -> OutstandingToken:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise CustomAuthenticationError(
            "هدر احراز هویت نامعتبر است.",
            code=status.HTTP_401_UNAUTHORIZED
        )

    token_str = auth_header.split(" ")[1]

    # Obtain the refresh token from the data provided in the logout payload.
    refresh_token = RefreshToken(data.get("refresh"))
    jti = refresh_token.payload.get("jti")
    exp = refresh_token.payload.get("exp")

    if not jti or not exp:
        raise CustomAuthenticationError(
            "توکن احراز هویت نامعتبر است.",
            code=status.HTTP_401_UNAUTHORIZED
        )

    if refresh_token.payload.get("token_type") != "refresh":
        raise CustomAuthenticationError(
            "نوع توکن نامعتبر است.",
            code=status.HTTP_401_UNAUTHORIZED
        )

    # Retrieve or create an OutstandingToken for the refresh token.
    token, created = OutstandingToken.objects.get_or_create(
        jti=jti,
        defaults={
            "user": request.user,
            "token": token_str,
            "expires_at": timezone.datetime.fromtimestamp(exp),
        },
    )

    if not created and token.user != request.user:
        raise CustomValidationError(
            "نوع مربوط به این کاربر نیست.",
            code=status.HTTP_400_BAD_REQUEST
        )

    # Instead of blacklisting, update the token's expiration time to now,
    # which will effectively make it expired.
    token.expires_at = timezone.now()
    token.save()

    return token
# def user_logout(request: Request, data: dict) -> BlacklistedToken:
#     auth_header = request.headers.get("Authorization")
#     if not auth_header or not auth_header.startswith("Bearer "):
#         raise CustomAuthenticationError(
#             "هدر احراز هویت نامعتبر است.", code=status.HTTP_401_UNAUTHORIZED
#         )
#
#     token_str = auth_header.split(" ")[1]
#
#     refresh_token = RefreshToken(data.get("refresh"))
#     jti = refresh_token.payload.get("jti")
#     exp = refresh_token.payload.get("exp")
#
#     if not jti or not exp:
#         raise CustomAuthenticationError(
#             "توکن احراز هویت نامعتبر است.", code=status.HTTP_401_UNAUTHORIZED
#         )
#
#     if refresh_token.payload.get("token_type") != "refresh":
#         raise CustomAuthenticationError(
#             "نوع توکن نامعتبر است.", code=status.HTTP_401_UNAUTHORIZED
#         )
#
#     token, created = OutstandingToken.objects.get_or_create(
#         jti=jti,
#         defaults={
#             "user": request.user,
#             "token": token_str,
#             "expires_at": timezone.datetime.fromtimestamp(exp),
#         },
#     )
#
#     if not created and token.user != request.user:
#         raise CustomValidationError(
#             "نوع مربوط به این کاربر نیست.", code=status.HTTP_400_BAD_REQUEST
#         )
#
#     blocklist, _ = BlacklistedToken.objects.get_or_create(token=token)
#
#     return blocklist
