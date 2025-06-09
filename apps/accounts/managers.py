from django.contrib.auth.models import UserManager

from . import models


class CustomUserManager(UserManager):
    def _create_user(self, phone_number: str, **extra_fields) -> "accounts.models.User":
        """
        Create and save a User with the given email and password.
        """
        user = self.model(phone_number=phone_number, **extra_fields)
        user.role = models.RoleTextChoices.STUDENT
        user.save(using=self._db)
        return user

    def create_user(self, phone_number: str, **extra_fields) -> "accounts.models.User":
        """
        Create and save a regular User with the given email and password.
        """
        extra_fields.setdefault("is_active", False)
        extra_fields.setdefault("profile_completed", False)
        return self._create_user(phone_number,  **extra_fields)

    def create_superuser(self, phone_number: str, **extra_fields) -> "accounts.models.User":
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("role", models.RoleTextChoices.ADMIN)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("profile_completed", True)

        if extra_fields.get("is_active") is not True:
            raise ValueError("Superuser must have is_active=True.")
        if extra_fields.get("profile_completed") is not True:
            raise ValueError("Superuser must have profile_completed=True.")

        return self._create_user(phone_number, **extra_fields)
