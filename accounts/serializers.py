from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Role


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["role_id", "name"]
        read_only_fields = ["role_id"]


class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["user_id", "email", "full_name", "role", "role_id", "created_at"]
        read_only_fields = ["user_id", "created_at"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    role_id = serializers.IntegerField(required=False)

    class Meta:
        model = User
        fields = ["email", "password", "password2", "full_name", "role_id"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Mật khẩu không khớp"})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        role_id = validated_data.pop("role_id", None)

        # Default role is 'user' if no role_id
        if role_id:
            try:
                role = Role.objects.get(role_id=role_id)
            except Role.DoesNotExist:
                role = Role.objects.get_or_create(
                    name="user", defaults={"description": "Regular user"}
                )[0]
        else:
            role = Role.objects.get_or_create(
                name="user", defaults={"description": "Regular user"}
            )[0]

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            role=role,
            is_active=False,
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                raise serializers.ValidationError(
                    "Tài khoản chưa được kích hoạt. Vui lòng xác thực email."
                )
            if not user.check_password(password):
                raise serializers.ValidationError("Mật khẩu không chính xác")
            attrs["user"] = user
            return attrs
        except User.DoesNotExist:
            raise serializers.ValidationError("Email không tồn tại")


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["full_name"]


# class ChangePasswordSerializer(serializers.Serializer):
#     old_password = serializers.CharField(required=True)
#     new_password = serializers.CharField(required=True, validators=[validate_password])
#     confirm_password = serializers.CharField(required=True)

#     def validate(self, attrs):
#         if attrs["new_password"] != attrs["confirm_password"]:
#             raise serializers.ValidationError(
#                 {"new_password": "Mật khẩu mới không khớp"}
#             )
#         return attrs
