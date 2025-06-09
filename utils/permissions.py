from django.http import HttpRequest
from rest_framework import status
from rest_framework.permissions import BasePermission

from apps.accounts.models import RoleTextChoices
from utils.exceptions import CustomPermissionError
from utils.auth import CustomRefreshToken


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin


class IsSupervisor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_supervisor


class IsOperator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_operator


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_student

class RoleBasedPermission(BasePermission):
    allowed_roles = []

    def has_permission(self, request: HttpRequest, view) -> bool:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise CustomPermissionError("احراز هویت انجام نشده است.", code=status.HTTP_401_UNAUTHORIZED)

        token = auth_header.split(" ")[1]
        try:
            payload = CustomRefreshToken.decode_token(token)
            role = payload.get("role")
            print("role", "role")

            if role in self.allowed_roles and request.user.role in self.allowed_roles:
                return True
        except Exception:
            raise CustomPermissionError("شما مجوز انجام این کار را ندارید", code=status.HTTP_403_FORBIDDEN)

        return False


class IsOperatorUserPermission(RoleBasedPermission):
    allowed_roles = [RoleTextChoices.OPERATOR.value]

class IsStudentPermission(RoleBasedPermission):
    allowed_roles = [RoleTextChoices.STUDENT.value]

class IsAdminUserPermission(RoleBasedPermission):
    allowed_roles = [RoleTextChoices.ADMIN.value]
