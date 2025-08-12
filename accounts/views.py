from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import User
from .models import User, Role
from .serializers import (
    LoginSerializer,
    UserSerializer,
    RegisterSerializer,
    ProfileUpdateSerializer,
)
from .permissions import IsAdmin, IsUser
from .utils import (
    handle_auth_response,
    # handle_oauth_response,
    token_blacklisted,
    create_and_send_otp,
    get_otp_from_cache,
    delete_otp_from_cache,
    get_tokens_for_user,
)


@api_view(["POST"])
@permission_classes([AllowAny])
@handle_auth_response(RegisterSerializer)
def register(request):
    pass


@api_view(["POST"])
@permission_classes([AllowAny])
@handle_auth_response(LoginSerializer)
def login(request):
    pass


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Xem và cập nhật profile"""
    user = request.user

    if request.method == "GET":
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "PATCH":
        serializer = ProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def change_password(request):
#     """Thay đổi mật khẩu"""
#     serializer = ChangePasswordSerializer(data=request.data)
#     if serializer.is_valid():
#         user = request.user
#         if not user.check_password(serializer.validated_data["old_password"]):
#             return Response(
#                 {"old_password": ["Mật khẩu hiện tại không đúng"]},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         user.set_password(serializer.validated_data["new_password"])
#         user.save()
#         return Response({"message": "Mật khẩu đã được thay đổi thành công"})

#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get("refresh")
        if refresh_token:
            token_blacklisted(refresh_token)
        return Response({"message": "Đăng xuất thành công"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def send_verification_otp(request):
    """Gửi OTP xác thực qua email"""
    email = request.data.get("email")
    if not email:
        return Response(
            {"error": "Email không được cung cấp"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(email=email)
        create_and_send_otp(user)
        return Response({"message": "Mã OTP đã được gửi đến email của bạn"})
    except User.DoesNotExist:
        return Response(
            {"error": "Không tìm thấy tài khoản với email này"},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    """Xác thực OTP"""
    email = request.data.get("email")
    otp = request.data.get("otp")

    if not email or not otp:
        return Response(
            {"error": "Email và OTP không được để trống"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(email=email)
        stored_otp = get_otp_from_cache(email)

        if not stored_otp:
            return Response(
                {"error": "Mã OTP đã hết hạn"}, status=status.HTTP_400_BAD_REQUEST
            )

        if otp != stored_otp:
            return Response(
                {"error": "Mã OTP không chính xác"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Kích hoạt tài khoản
        user.is_active = True
        user.save()

        # Xóa OTP khỏi cache
        delete_otp_from_cache(email)

        # Tạo token cho user
        tokens = get_tokens_for_user(user)

        return Response(
            {
                "message": "Xác thực thành công",
                "refresh": tokens["refresh"],
                "access": tokens["access"],
                "user": UserSerializer(user).data,
            }
        )

    except User.DoesNotExist:
        return Response(
            {"error": "Không tìm thấy tài khoản với email này"},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def register_admin(request):
    """Đăng ký tài khoản admin"""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        validated_data = serializer.validated_data.copy()
        validated_data.pop("password2")
        admin_role = Role.objects.get(name="admin")
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            role=admin_role,
            is_staff=True,
            is_active=False,
        )

        create_and_send_otp(user)
        tokens = get_tokens_for_user(user)

        return Response(
            {
                "message": "Đăng ký admin thành công. Vui lòng kiểm tra email để xác thực tài khoản",
                "user": UserSerializer(user).data,
                "verification_token": tokens.get("verification_token"),
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
