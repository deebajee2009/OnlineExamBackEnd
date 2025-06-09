from typing import Optional

from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.views import exception_handler


class CustomAPIException(APIException):
    default_detail = "خطا در سرور رخ داده است"
    default_code = 'server_error'

    def __init__(self, detail: Optional[str] = None, code: Optional[int] = None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        self.detail = detail
        self.code = code

    def get_detail(self):
        return str(self.detail)

    def get_code(self):
        return self.code

class CustomNoContentError(APIException):
    status_code = status.HTTP_204_NO_CONTENT
    default_code = "no_content"
    default_detail = "عملیات با موفقیت انجام شد ولی داده‌ای برای بازگشت وجود ندارد"

class CustomValidationError(CustomAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "validation_error"
    default_detail = "اطلاعات وارد شده معتبر نیست"


class CustomPermissionError(CustomAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "permission_denied"
    default_detail = "کاربر اجازه این کار را ندارد"


class CustomNotFoundError(CustomAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "not_found"
    default_detail = "پیدا نشد"


class CustomAuthenticationError(CustomAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "not_authenticated"
    default_detail = "کاربر احراز هویت نشده است"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if isinstance(exc, CustomAPIException):
            response.data = {
                "error": {
                    "code": exc.get_code(),
                    "message": exc.get_detail()
                }
            }
        elif isinstance(exc, PermissionDenied):
            response.data = {
                "error": {
                    "code": status.HTTP_403_FORBIDDEN,
                    "message": "شما اجازه انجام این کار را ندارید."
                }
            }
        else:
            if isinstance(response.data, list) and response.data:
                detail = response.data[0]
            elif isinstance(response.data, dict):
                detail = response.data.get('detail', f': {exc}خطایی رخ داده است')
            else:
                detail = 'خطایی رخ داده است'

            response.data = {
                "error": {
                    "code": "unknown_error",
                    "message": detail
                }
            }
    return response
