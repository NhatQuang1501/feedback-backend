from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    register,
    login,
    logout,
    user_profile,
    send_verification_otp,
    verify_otp,
)

urlpatterns = [
    # Authentication endpoints
    path("register/", register, name="register"),
    path("login/", login, name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", logout, name="logout"),
    # OAuth endpoints
    # path("login/google/", google_login, name="google_login"),
    # User profile endpoints
    path("profile/", user_profile, name="user_profile"),
    # OTP verification endpoints
    path(
        "send-verification-otp/",
        send_verification_otp,
        name="send_verification_otp",
    ),
    path("verify-otp/", verify_otp, name="verify_otp"),
]
