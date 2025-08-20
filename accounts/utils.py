from datetime import timedelta
from functools import wraps
import logging
import random
import string
import uuid
from django.core.cache import cache
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken, Token
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserSerializer
from .tasks import send_otp_email_task

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
EMAIL_SUPPORT = "feedbackhub2025@gmail.com"
HOTLINE = "0123 456 789"


def generate_otp():
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


def generate_token():
    return str(uuid.uuid4())


def _get_cache_key(email, prefix="otp"):
    return f"{prefix}_{email.lower()}"


def store_otp_in_cache(email, otp):
    cache_key = _get_cache_key(email)
    cache.set(cache_key, otp, timeout=settings.OTP_EXPIRY_TIME)


def get_otp_from_cache(email):
    cache_key = _get_cache_key(email)
    return cache.get(cache_key)


def delete_otp_from_cache(email):
    cache_key = _get_cache_key(email)
    cache.delete(cache_key)


def store_token_in_cache(email, token, timeout=None):
    if timeout is None:
        timeout = settings.OTP_EXPIRY_TIME
    cache_key = _get_cache_key(email, prefix="token")
    cache.set(cache_key, token, timeout=timeout)


def get_token_from_cache(email):
    cache_key = _get_cache_key(email, prefix="token")
    return cache.get(cache_key)


def delete_token_from_cache(email):
    cache_key = _get_cache_key(email, prefix="token")
    cache.delete(cache_key)


def get_tokens_for_user(user):

    class VerificationToken(Token):
        token_type = "verification"
        lifetime = timedelta(minutes=5)

    if not user.is_active:
        token = VerificationToken()
        token.payload["user_id"] = str(user.user_id)
        token.payload["email"] = user.email
        token.payload["type"] = "verification"
        return {"verification_token": str(token)}

    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role.name
    refresh.access_token["role"] = user.role.name
    refresh.access_token["full_name"] = user.full_name

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def create_and_send_otp(user):
    otp = generate_otp()
    store_otp_in_cache(user.email, otp)
    send_otp_email_task.delay(
        user.email, user.full_name, otp, settings.OTP_EXPIRY_TIME // 60
    )

    return otp


def token_blacklisted(token):
    try:
        refresh_token = RefreshToken(token)
        if BlacklistedToken.objects.filter(
            token__jti=refresh_token.payload["jti"]
        ).exists():
            return True

        refresh_token.blacklist()
        return True
    except Exception as e:
        logger.error(f"Token blacklist error: {str(e)}")
        return False


def handle_auth_response(serializer_class):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            serializer = serializer_class(data=request.data)
            if serializer.is_valid():
                if hasattr(serializer, "create") and "register" in view_func.__name__:
                    user = serializer.save()
                else:
                    user = serializer.validated_data["user"]

                tokens = get_tokens_for_user(user)
                response_data = {"user": UserSerializer(user).data}
                response_data.update(tokens)

                if "register" in view_func.__name__:
                    create_and_send_otp(user)
                    response_data["message"] = (
                        "Vui lòng kiểm tra email để xác thực tài khoản"
                    )
                    return Response(response_data, status=status.HTTP_201_CREATED)

                if not user.is_active and "login" in view_func.__name__:
                    return Response(
                        {
                            "error": "Tài khoản chưa được kích hoạt. Vui lòng xác thực email.",
                            "verification_token": tokens.get("verification_token"),
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

                return Response(response_data, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return wrapper

    return decorator
