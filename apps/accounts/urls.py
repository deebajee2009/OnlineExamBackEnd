from django.urls import path

from apps.accounts.views import (
    OtpRequestLoginOrSignupView,
    OtpLoginOrSignupView,
    UserProfileView,
    LogoutView,
    RefreshTokenView

)


urlpatterns  = [
    path(
        "otp/request/login/",
        OtpRequestLoginOrSignupView.as_view(),
        name="otp_request_login",
    ),
    path(
        "otp/verify/login/",
        OtpLoginOrSignupView.as_view(),
        name="otp_verify_login",
    ),
    # path(
    #     "signup/user",
    #     SignUpUserView.as_view(),
    #     name="signup_user",
    # ),
    path(
        "user/profile/",
        UserProfileView.as_view(),
        name="dashboard_profile"
    ),
    path(
        "auth/logout/",
        LogoutView.as_view(),
        name="user_logout",
    ),
    path(
        "auth/token/new/",
        RefreshTokenView.as_view(),
        name="get_new_access_token",
    ),

]
