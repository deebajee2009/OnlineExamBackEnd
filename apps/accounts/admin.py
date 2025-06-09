from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Profile

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('phone_number', 'role', 'is_active', 'profile_completed')
    ordering = ('phone_number',)
    search_fields = ('phone_number', 'email', 'role')

    # Configure the fields for viewing and editing the User model.
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        (_('Personal info'), {'fields': ('username', 'email', 'role')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login',)}),
    )

    # Fields to be used when creating a new user.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2', 'role', 'is_active'),
        }),
    )

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'gender', 'birth_day', 'education', 'province', 'city')
    search_fields = ('first_name', 'last_name', 'national_code', 'school_name', 'acquisition')
