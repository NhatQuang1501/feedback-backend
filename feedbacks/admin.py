from django.contrib import admin
from .models import (
    Feedback,
    FeedbackType,
    Priority,
    FeedbackStatus,
    Attachment,
    EmailLog,
)


class FeedbackTypeAdmin(admin.ModelAdmin):
    list_display = ("type_id", "name", "description")
    search_fields = ("name", "description")


class PriorityAdmin(admin.ModelAdmin):
    list_display = ("priority_id", "name")
    search_fields = ("name",)


class FeedbackStatusAdmin(admin.ModelAdmin):
    list_display = ("status_id", "name")
    search_fields = ("name",)


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = (
        "attachment_id",
        "file_name",
        "file_url",
        "file_type",
        "uploaded_at",
    )


class EmailLogInline(admin.TabularInline):
    model = EmailLog
    extra = 0
    readonly_fields = (
        "email_log_id",
        "email_to",
        "subject",
        "content",
        "created_at",
        "status",
        "error_message",
    )


class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "feedback_id",
        "title",
        "user",
        "type",
        "priority",
        "status",
        "created_at",
    )
    list_editable = ("status",)
    list_filter = ("status", "type", "priority", "created_at")
    search_fields = ("title", "content", "user__full_name", "user__email")
    readonly_fields = ("feedback_id", "created_at")
    inlines = [AttachmentInline, EmailLogInline]
    date_hierarchy = "created_at"
    list_per_page = 20


class AttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "attachment_id",
        "feedback",
        "file_name",
        "file_url",
        "file_type",
        "uploaded_at",
    )
    list_filter = ("file_type", "uploaded_at")
    search_fields = ("file_name", "feedback__title")
    readonly_fields = ("attachment_id", "uploaded_at")


class EmailLogAdmin(admin.ModelAdmin):
    list_display = (
        "email_log_id",
        "feedback",
        "email_to",
        "subject",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("email_to", "subject", "content")
    readonly_fields = ("email_log_id", "created_at")


admin.site.register(FeedbackType, FeedbackTypeAdmin)
admin.site.register(Priority, PriorityAdmin)
admin.site.register(FeedbackStatus, FeedbackStatusAdmin)
admin.site.register(Feedback, FeedbackAdmin)
admin.site.register(Attachment, AttachmentAdmin)
admin.site.register(EmailLog, EmailLogAdmin)
