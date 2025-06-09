from typing import Dict, Optional, Any
import httpx
from django.conf import settings
from utils.logger import CustomLogger


logger = CustomLogger(__name__).get_logger()

class SMS:
    def __init__(self, api_key: str, template: str):
        self.api_key = api_key
        self.url = f"https://api.kavenegar.com/v1/{self.api_key}/verify/lookup.json"
        self.template = template

    def send(self, phone_number: str, token: int) -> Optional[
        Dict[str, Any]]:

        """Send SMS to phone number."""
        params = {
            "receptor": phone_number,
            "template": self.template,
            "token": str(token)
        }

        logger.info(f"Sending SMS with params: {params}")

        try:
            # Send GET request with query parameters
            response = httpx.get(self.url, params=params)
            response.raise_for_status()  # Raise an error for 4xx/5xx responses
            return response.json()
        except httpx.RequestError as error:
            logger.error(f"Request error occurred for phone {phone_number}: {error}")
        except httpx.HTTPStatusError as error:
            logger.error(f"HTTP error occurred for phone {phone_number}: {error}")
        except Exception as error:
            logger.error(f"Unexpected error: {error}")

        return None


def send_sms(receiver: str, token: str):
    template_id = settings.OTP_TEMPLATE
    api_key = settings.SMS_API_KEY
    sms = SMS(api_key, template_id)
    response = sms.send(receiver, token)
    if response:
        logger.info(f"SMS sent to {receiver} with template {template_id}: {response}")
    else:
        logger.error(f"Failed to send SMS to {receiver} with template {template_id}")
