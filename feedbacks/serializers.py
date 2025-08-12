from rest_framework import serializers
from .models import (
    Feedback,
    FeedbackType,
    Priority,
    FeedbackStatus,
    Attachment,
    EmailLog,
)
from .choices import (
    FeedbackTypeChoices,
    PriorityChoices,
    StatusChoices,
    VIETNAMESE_DISPLAY_NAMES,
)
from accounts.serializers import UserSerializer


class FeedbackTypeSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = FeedbackType
        fields = ["type_id", "name", "display_name"]

    def get_display_name(self, obj):
        return FeedbackTypeChoices.get_display_name(obj.name)


class PrioritySerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Priority
        fields = ["priority_id", "name", "display_name"]

    def get_display_name(self, obj):
        return PriorityChoices.get_display_name(obj.name)


class FeedbackStatusSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = FeedbackStatus
        fields = ["status_id", "name", "display_name"]

    def get_display_name(self, obj):
        return StatusChoices.get_display_name(obj.name)


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ["attachment_id", "file_name", "file_url", "file_type", "uploaded_at"]
        read_only_fields = ["attachment_id", "uploaded_at"]

    def create(self, validated_data):
        feedback = validated_data.pop("feedback")
        return Attachment.objects.create(feedback=feedback, **validated_data)


class EmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailLog
        fields = [
            "email_log_id",
            "email_to",
            "subject",
            "content",
            "created_at",
            "status",
            "error_message",
        ]
        read_only_fields = ["email_log_id", "created_at"]


class FeedbackListSerializer(serializers.ModelSerializer):
    type = FeedbackTypeSerializer(read_only=True)
    priority = PrioritySerializer(read_only=True)
    status = FeedbackStatusSerializer(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Feedback
        fields = [
            "feedback_id",
            "title",
            "type",
            "priority",
            "status",
            "created_at",
            "updated_at",
            "user",
        ]


class FeedbackDetailSerializer(serializers.ModelSerializer):
    type = FeedbackTypeSerializer(read_only=True)
    priority = PrioritySerializer(read_only=True)
    status = FeedbackStatusSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Feedback
        fields = [
            "feedback_id",
            "title",
            "content",
            "type",
            "priority",
            "status",
            "created_at",
            "updated_at",
            "user",
            "attachments",
        ]


class FeedbackCreateSerializer(serializers.ModelSerializer):
    type_id = serializers.PrimaryKeyRelatedField(
        queryset=FeedbackType.objects.all(), source="type"
    )
    priority_id = serializers.PrimaryKeyRelatedField(
        queryset=Priority.objects.all(), source="priority"
    )

    class Meta:
        model = Feedback
        fields = ["title", "content", "type_id", "priority_id"]

    def create(self, validated_data):
        user = self.context["request"].user
        # Lấy trạng thái mặc định (Pending)
        default_status = FeedbackStatus.objects.get(name="pending")

        feedback = Feedback.objects.create(
            user=user, status=default_status, **validated_data
        )
        return feedback


class FeedbackUpdateStatusSerializer(serializers.ModelSerializer):
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=FeedbackStatus.objects.all(), source="status"
    )

    class Meta:
        model = Feedback
        fields = ["status_id"]
