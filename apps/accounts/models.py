from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

from apps.accounts.managers import CustomUserManager
from apps.commons.model_fields import (
    CharFieldNoEmptyString,
    EmailFieldNoEmptyString
)


class RoleTextChoices(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    OPERATOR = "OPERATOR", "Operator"
    STUDENT = "STUDENT", "Student"

# test

class User(AbstractUser):
    phone_number = CharFieldNoEmptyString(max_length=11, unique=True)
    username = CharFieldNoEmptyString(unique=True, blank=True, null=True)
    password = CharFieldNoEmptyString(unique=True, blank=True, null=True)
    email = EmailFieldNoEmptyString(blank=True, null=True)

    role = models.CharField(
        max_length=8,
        choices=RoleTextChoices.choices,
        default=RoleTextChoices.STUDENT,
    )
    is_active =  models.BooleanField(default=False)

    group = models.ManyToManyField(
        Group,
        related_name="accounts",
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="accounts",
        blank=True,
    )

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    @property
    def profile_completed(self):
        try:
            profile = self.student_profile
        except Profile.DoesNotExist:
            return False

        required_fields = [
            profile.first_name,
            profile.last_name,
            profile.gender,
            profile.education,
            profile.province,
            profile.city,
        ]

        return all(bool(field and str(field).strip()) for field in required_fields)

    @property
    def is_admin(self):
        return self.role == RoleTextChoices.ADMIN

    @property
    def is_operator(self):
        return self.role == RoleTextChoices.OPERATOR

    @property
    def is_student(self):
        return self.role == RoleTextChoices.STUDENT


    def __str__(self):
        return self.phone_number


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name="student_profile")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=100)
    birth_day = models.DateField(null=True, blank=True)
    education = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    national_code = models.CharField(max_length=100, unique=True, blank=True, null=True)
    school_name = models.CharField(max_length=100, blank=True, null=True)
    acquisition = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.first_name + self.last_name
