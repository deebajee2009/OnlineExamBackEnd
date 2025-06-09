import jwt
from django.http import HttpRequest
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken, AuthUser, Token


class CustomRefreshToken(RefreshToken):
    """
    Custom refresh token class
    """

    @property
    def access_token(self) -> AccessToken:
        """Return access token with role"""
        token = super().access_token
        token['role'] = self.payload.get('role', None)

        return token

    @classmethod
    def for_user(cls, user: AuthUser) -> Token:
        """Generate token for user with role"""
        token = super().for_user(user)
        token['role'] = user.role
        token['phone_number'] = user.phone_number
        return token

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode token and return payload"""
        try:
            payload = jwt.decode(
                token,
                api_settings.SIGNING_KEY,
                algorithms=[api_settings.ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise Exception("Token has expired")
        except jwt.InvalidTokenError:
            raise Exception("Invalid token")

    @staticmethod
    def get_role(request: HttpRequest) -> str:
        """Get role from request headers"""
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            payload = CustomRefreshToken.decode_token(token)
            role = payload.get('role')
            return role
