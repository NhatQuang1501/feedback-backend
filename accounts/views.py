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
from .permissions import IsAdmin, IsUser, IsSelf, IsAdminOrSelf, IsAdminOrReadOnly
from .utils import (
    handle_auth_response,
    # handle_oauth_response,
    token_blacklisted,
    create_and_send_otp,
    get_otp_from_cache,
    delete_otp_from_cache,
    get_tokens_for_user,
)
from .google_auth import GoogleAuthService, GoogleAuthError


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
def google_login(request):
    """
    Google OAuth login
    
    Expected payload:
    {
        "token": "google_id_token_from_frontend"
    }
    """
    token = request.data.get("token")
    
    if not token:
        return Response(
            {"error": "Google token không được cung cấp"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        # Authenticate user with Google
        user, created = GoogleAuthService.authenticate_google_user(token)
        
        # Generate JWT tokens
        tokens = get_tokens_for_user(user)
        
        # Prepare response
        response_data = {
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "user": UserSerializer(user).data,
        }
        
        if created:
            response_data["message"] = "Tài khoản Google đã được tạo thành công"
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            response_data["message"] = "Đăng nhập Google thành công"
            return Response(response_data, status=status.HTTP_200_OK)
            
    except GoogleAuthError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"error": "Đã xảy ra lỗi trong quá trình xác thực Google"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
