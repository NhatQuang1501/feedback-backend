from django.db import models

VIETNAMESE_DISPLAY_NAMES = {
    "FeedbackTypeChoices": {
        "suggestion": "Góp ý",
        "bug": "Lỗi",
        "other": "Khác",
    },
    "PriorityChoices": {
        "low": "Thấp",
        "medium": "Trung bình",
        "high": "Cao",
    },
    "StatusChoices": {
        "pending": "Chờ xử lý",
        "processing": "Đang xử lý",
        "resolved": "Đã xử lý",
    },
}

VALID_STATUS_TRANSITIONS = {
    "pending": ["processing"],
    "processing": ["resolved"],
    "resolved": [],
}


class BaseChoices(models.TextChoices):
    @classmethod
    def get_values(cls):
        return [choice[0] for choice in cls.choices]

    @classmethod
    def get_display_name(cls, value):
        class_name = cls.__name__
        if (
            class_name in VIETNAMESE_DISPLAY_NAMES
            and value in VIETNAMESE_DISPLAY_NAMES[class_name]
        ):
            return VIETNAMESE_DISPLAY_NAMES[class_name][value]

        for choice_value, choice_label in cls.choices:
            if choice_value == value:
                return choice_label

        return value.capitalize() if value else ""


class FeedbackTypeChoices(BaseChoices):
    SUGGESTION = "suggestion", "Suggestion"
    BUG = "bug", "Bug"
    OTHER = "other", "Other"


class PriorityChoices(BaseChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class StatusChoices(BaseChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    RESOLVED = "resolved", "Resolved"
