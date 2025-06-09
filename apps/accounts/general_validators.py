import re
from rest_framework import status

from utils.exceptions import CustomValidationError

def validate_phone_number_format(phone_number: str) -> None:
    rule = re.compile(r"^((\+98|0|0098)9\d{9})$")
    if not rule.search(phone_number):
        raise CustomValidationError(
            "فرمت شماره موبایل نامعتبر است.", code=status.HTTP_400_BAD_REQUEST
        )
