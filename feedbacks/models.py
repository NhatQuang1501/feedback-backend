import uuid
from django.db import models
from .choices import FeedbackTypeChoices, PriorityChoices, StatusChoices

User = "accounts.User"


class FeedbackType(models.Model):
    type_id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(
        max_length=50,
        choices=FeedbackTypeChoices.choices,
        default=FeedbackTypeChoices.SUGGESTION,
    )
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return FeedbackTypeChoices.get_display_name(self.name)


class Priority(models.Model):
    priority_id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(
        max_length=50, choices=PriorityChoices.choices, default=PriorityChoices.MEDIUM
    )

    def __str__(self):
        return PriorityChoices.get_display_name(self.name)


class FeedbackStatus(models.Model):
    status_id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(
        max_length=50, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )

    def __str__(self):
        return StatusChoices.get_display_name(self.name)


class Feedback(models.Model):
    feedback_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="feedbacks")
    type = models.ForeignKey(
        FeedbackType, on_delete=models.PROTECT, related_name="feedbacks"
    )
    priority = models.ForeignKey(
        Priority, on_delete=models.PROTECT, related_name="feedbacks"
    )
    status = models.ForeignKey(
        FeedbackStatus, on_delete=models.PROTECT, related_name="feedbacks"
    )
    title = models.CharField(max_length=100)
    content = models.TextField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Attachment(models.Model):
    attachment_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    feedback = models.ForeignKey(
        Feedback, on_delete=models.CASCADE, related_name="attachments"
    )
    file_name = models.CharField(max_length=255)
    file_url = models.FileField(upload_to="media/")
    file_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name


class EmailLog(models.Model):
    email_log_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    feedback = models.ForeignKey(
        Feedback, on_delete=models.CASCADE, related_name="email_logs"
    )
    email_to = models.EmailField()
    subject = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.subject} - {self.email_to}"
