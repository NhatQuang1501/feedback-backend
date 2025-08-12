from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.name == "admin"


class IsUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.name == "user"


class IsSelf(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.user_id


class IsAdminOrSelf(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.role.name == "admin" or obj.user_id == request.user.user_id


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or (
            request.user.is_authenticated and request.user.role.name == "admin"
        )


class IsOwnerOrAdmin(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.role.name == "admin":
            return True
        return obj.user.user_id == request.user.user_id
