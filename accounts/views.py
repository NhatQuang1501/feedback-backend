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

        user.is_active = True
        user.save()

        delete_otp_from_cache(email)
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
    token = request.data.get("token")

    if not token:
        return Response(
            {"error": "Google token không được cung cấp"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user, created = GoogleAuthService.authenticate_google_user(token)
        tokens = get_tokens_for_user(user)
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


@api_view(["POST"])
@permission_classes([AllowAny])
def register_admin(request):
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_profile(request):
    """
    API để lấy thông tin profile của user hiện tại
    
    Mục đích:
    - Xác thực và lấy thông tin user sau khi đăng nhập
    - Khôi phục session khi user refresh trang/mở lại app
    - Kiểm tra quyền hạn (role: admin/user)
    - Hiển thị thông tin cá nhân trong UI
    """
    try:
        user = request.user
        serializer = UserSerializer(user)
        
        return Response({
            "success": True,
            "message": "Lấy thông tin profile thành công",
            "data": {
                "user": serializer.data,
                "permissions": {
                    "is_admin": user.role.name == "admin" if user.role else False,
                    "is_staff": user.is_staff,
                    "is_active": user.is_active,
                }
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "success": False,
            "error": "Không thể lấy thông tin profile",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
