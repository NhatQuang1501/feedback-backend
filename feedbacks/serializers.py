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
    VALID_STATUS_TRANSITIONS,
)
from accounts.serializers import UserSerializer
from .utils import validate_file


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
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["attachment_id", "file_name", "file_url", "file_type", "uploaded_at"]
        read_only_fields = ["attachment_id", "uploaded_at"]

    def get_file_url(self, obj):
        if obj.file_url:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file_url.url)
            return obj.file_url.url
        return None

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
    type_id = serializers.IntegerField(source="type.type_id")
    type_display = serializers.SerializerMethodField()
    priority_id = serializers.IntegerField(source="priority.priority_id")
    priority_display = serializers.SerializerMethodField()
    status_id = serializers.IntegerField(source="status.status_id")
    status_display = serializers.SerializerMethodField()
    user_id = serializers.UUIDField(source="user.user_id")
    user_full_name = serializers.CharField(source="user.full_name")
    user_role = serializers.CharField(source="user.role.name")

    def get_type_display(self, obj):
        return str(obj.type)

    def get_priority_display(self, obj):
        return str(obj.priority)

    def get_status_display(self, obj):
        return str(obj.status)

    class Meta:
        model = Feedback
        fields = [
            "feedback_id",
            "title",
            "type_id",
            "type_display",
            "priority_id",
            "priority_display",
            "status_id",
            "status_display",
            "created_at",
            "updated_at",
            "user_id",
            "user_full_name",
            "user_role",
        ]


class FeedbackDetailSerializer(serializers.ModelSerializer):
    type_id = serializers.IntegerField(source="type.type_id")
    type_display = serializers.SerializerMethodField()
    priority_id = serializers.IntegerField(source="priority.priority_id")
    priority_display = serializers.SerializerMethodField()
    status_id = serializers.IntegerField(source="status.status_id")
    status_display = serializers.SerializerMethodField()
    user_id = serializers.UUIDField(source="user.user_id")
    user_full_name = serializers.CharField(source="user.full_name")
    user_role = serializers.CharField(source="user.role.name")
    attachments = AttachmentSerializer(many=True, read_only=True)

    def get_type_display(self, obj):
        return str(obj.type)

    def get_priority_display(self, obj):
        return str(obj.priority)

    def get_status_display(self, obj):
        return str(obj.status)

    class Meta:
        model = Feedback
        fields = [
            "feedback_id",
            "title",
            "content",
            "type_id",
            "type_display",
            "priority_id",
            "priority_display",
            "status_id",
            "status_display",
            "created_at",
            "updated_at",
            "user_id",
            "user_full_name",
            "user_role",
            "attachments",
        ]


class FeedbackCreateSerializer(serializers.ModelSerializer):
    type_id = serializers.PrimaryKeyRelatedField(
        queryset=FeedbackType.objects.all(), source="type"
    )
    priority_id = serializers.PrimaryKeyRelatedField(
        queryset=Priority.objects.all(), source="priority"
    )
    files = serializers.ListField(
        child=serializers.FileField(
            max_length=100000, allow_empty_file=False, use_url=False
        ),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Feedback
        fields = ["title", "content", "type_id", "priority_id", "files"]

    def validate_files(self, files):
        for file in files:
            is_valid, error_message = validate_file(file)
            if not is_valid:
                raise serializers.ValidationError(error_message)
        return files

    def create(self, validated_data):
        user = self.context["request"].user
        default_status = FeedbackStatus.objects.get(status_id=1)

        files = validated_data.pop("files", [])

        feedback = Feedback.objects.create(
            user=user, status=default_status, **validated_data
        )

        for file in files:
            Attachment.objects.create(
                feedback=feedback,
                file_name=file.name,
                file_url=file,
                file_type=file.content_type,
            )

        return feedback


class FeedbackUpdateStatusSerializer(serializers.ModelSerializer):
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=FeedbackStatus.objects.all(), source="status"
    )

    class Meta:
        model = Feedback
        fields = ["status_id"]

    def validate(self, attrs):
        current_status = self.instance.status.name
        new_status = attrs["status"].name

        if new_status not in VALID_STATUS_TRANSITIONS.get(current_status, []):
            valid_transitions = VALID_STATUS_TRANSITIONS.get(current_status, [])
            valid_names = [
                StatusChoices.get_display_name(status) for status in valid_transitions
            ]

            if not valid_transitions:
                error_msg = f"Không thể thay đổi trạng thái từ '{StatusChoices.get_display_name(current_status)}'."
            else:
                error_msg = f"Từ '{StatusChoices.get_display_name(current_status)}' chỉ có thể chuyển sang: {', '.join(valid_names)}."

            raise serializers.ValidationError({"status_id": error_msg})

        return attrs
