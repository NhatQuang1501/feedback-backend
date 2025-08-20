from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role


class UserAdmin(BaseUserAdmin):
    list_display = ("email", "full_name", "role", "is_active", "created_at")
    list_editable = ["is_active"]
    list_filter = ("role", "is_active")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Information", {"fields": ("full_name",)}),
        (
            "Permission",
            {
                "fields": (
                    "role",
                    "is_active",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Other", {"fields": ("created_at",)}),
    )
    readonly_fields = ("created_at",)
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password1", "password2", "role"),
            },
        ),
    )
    search_fields = ("email", "full_name")
    ordering = ("email",)
    filter_horizontal = (
        "groups",
        "user_permissions",
    )


class RoleAdmin(admin.ModelAdmin):
    list_display = ("role_id", "name", "description")
    search_fields = ("name",)


admin.site.register(User, UserAdmin)
admin.site.register(Role, RoleAdmin)
