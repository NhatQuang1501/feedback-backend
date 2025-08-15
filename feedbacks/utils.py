import os
from datetime import date
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_date
from functools import wraps

from django.db.models import (
    F,
    Count,
    Avg,
    ExpressionWrapper,
    DurationField,
)
from django.db.models.functions import TruncMonth
from accounts.models import User
from .models import Feedback
from .tasks import (
    send_feedback_confirmation_email,
    send_new_feedback_notification_to_admin,
    send_feedback_status_update_email,
)
from .choices import StatusChoices, FeedbackTypeChoices, PriorityChoices


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "current_page": self.page.number,
                "total_pages": self.page.paginator.num_pages,
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


def send_feedback_emails(feedback):
    """Gửi email xác nhận và thông báo cho admin khi có feedback mới."""
    send_feedback_confirmation_email.delay(
        str(feedback.feedback_id),
        feedback.user.email,
        feedback.user.full_name,
        feedback.title,
    )

    admin_users = User.objects.filter(role__name="admin")
    for admin in admin_users:
        send_new_feedback_notification_to_admin.delay(
            str(feedback.feedback_id),
            admin.email,
            feedback.user.full_name,
            feedback.title,
        )


def notify_status_change(feedback, old_status):
    """Thông báo khi trạng thái feedback thay đổi và trả về tên trạng thái hiển thị."""
    if feedback.status.name != old_status:
        send_feedback_status_update_email.delay(
            str(feedback.feedback_id),
            feedback.user.email,
            feedback.user.full_name,
            feedback.title,
            feedback.status.name,
        )
        return StatusChoices.get_display_name(feedback.status.name)
    return None


def validate_file(file):
    max_size = 5 * 1024 * 1024
    if file.size > max_size:
        return (False,)

    valid_extensions = [
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".csv",
    ]
    ext = os.path.splitext(file.name)[1].lower()

    if ext not in valid_extensions:
        return (
            False,
            f"Định dạng file không được hỗ trợ. Các định dạng được hỗ trợ: {', '.join(valid_extensions)}",
        )

    return True, ""


def handle_feedback_response(serializer_class):
    """
    Decorator để xử lý response cho các view feedback, validate dữ liệu,
    lưu feedback và gửi email thông báo.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            serializer = serializer_class(
                data=request.data, context={"request": request}
            )
            if serializer.is_valid():
                feedback = serializer.save()

                is_create = view_func.__name__ == "create_feedback"
                if is_create:
                    send_feedback_emails(feedback)

                return Response(
                    serializer_class(feedback, context={"request": request}).data,
                    status=status.HTTP_201_CREATED if is_create else status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return wrapper

    return decorator


def translate_feedback_type(type_name):
    return FeedbackTypeChoices.get_display_name(type_name)


def translate_priority(priority_name):
    return PriorityChoices.get_display_name(priority_name)


def translate_status(status_name):
    return StatusChoices.get_display_name(status_name)


def resolve_date_range(
    from_param: str | None,
    to_param: str | None,
    *,
    default_months_back: int = 5,
    floor_from_to_month: bool = False,
) -> tuple[date, date]:
    to_date = parse_date(to_param) if to_param else date.today()
    if to_date is None:
        raise ValueError("Invalid 'to' date. Expected YYYY-MM-DD")

    from_date = parse_date(from_param) if from_param else None
    if from_date is None:
        year = to_date.year
        month = to_date.month - default_months_back
        while month <= 0:
            month += 12
            year -= 1
        from_date = date(year, month, 1)

    if floor_from_to_month:
        from_date = date(from_date.year, from_date.month, 1)

    if (to_date.year, to_date.month, to_date.day) < (
        from_date.year,
        from_date.month,
        from_date.day,
    ):
        raise ValueError("'to' date must be >= 'from' date")

    return from_date, to_date


def _iter_months(start_d: date, end_d: date):
    y, m = start_d.year, start_d.month
    end_y, end_m = end_d.year, end_d.month
    while (y < end_y) or (y == end_y and m <= end_m):
        yield y, m
        m += 1
        if m == 13:
            m = 1
            y += 1


def get_monthly_feedback_counts(
    from_param: str | None, to_param: str | None, order: str = "desc"
):
    from_date, to_date = resolve_date_range(
        from_param,
        to_param,
        default_months_back=5,
        floor_from_to_month=True,
    )

    month_keys = [f"{y:04d}-{m:02d}" for (y, m) in _iter_months(from_date, to_date)]

    queryset = Feedback.objects.filter(
        created_at__date__gte=from_date,
        created_at__date__lte=to_date,
    )

    monthly_counts = (
        queryset.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("feedback_id"))
    )

    counts_map = {
        item["month"].strftime("%Y-%m"): item["count"] for item in monthly_counts
    }
    data = [{"month": key, "count": counts_map.get(key, 0)} for key in month_keys]

    if (order or "").lower() == "asc":
        return data
    return list(reversed(data))


def get_feedback_type_counts(from_param: str | None, to_param: str | None):
    """Return counts for each feedback type in the given date range.

    Always returns all defined types with zero fill when absent.
    """
    from_date, to_date = resolve_date_range(from_param, to_param, default_months_back=5)

    # Aggregate
    qs = (
        Feedback.objects.filter(
            created_at__date__gte=from_date,
            created_at__date__lte=to_date,
        )
        .values("type__name")
        .annotate(count=Count("feedback_id"))
    )

    raw_map = {row["type__name"]: row["count"] for row in qs}

    # Ensure stable order and zero fill for all defined types
    ordered_types = FeedbackTypeChoices.get_values()
    result = [
        {
            "type": type_code,
            "display": FeedbackTypeChoices.get_display_name(type_code),
            "count": int(raw_map.get(type_code, 0)),
        }
        for type_code in ordered_types
    ]

    return result


def get_priority_distribution_counts(from_param: str | None, to_param: str | None):
    """Return counts for each priority in the given date range.

    Always returns all defined priorities with zero fill when absent.
    """
    from_date, to_date = resolve_date_range(from_param, to_param, default_months_back=5)

    qs = (
        Feedback.objects.filter(
            created_at__date__gte=from_date,
            created_at__date__lte=to_date,
        )
        .values("priority__name")
        .annotate(count=Count("feedback_id"))
    )

    raw_map = {row["priority__name"]: row["count"] for row in qs}

    ordered_priorities = PriorityChoices.get_values()
    result = [
        {
            "priority": pr_code,
            "display": PriorityChoices.get_display_name(pr_code),
            "count": int(raw_map.get(pr_code, 0)),
        }
        for pr_code in ordered_priorities
    ]

    return result


def get_handling_speed_by_month(
    from_param: str | None, to_param: str | None, order: str = "desc"
):
    """Average handling speed (days) per month, computed for resolved feedbacks.

    Uses resolution month (updated_at) and duration = updated_at - created_at.
    Returns zero for months without resolved feedbacks.
    """
    from_date, to_date = resolve_date_range(
        from_param,
        to_param,
        default_months_back=5,
        floor_from_to_month=True,
    )

    month_keys = [f"{y:04d}-{m:02d}" for (y, m) in _iter_months(from_date, to_date)]

    qs = (
        Feedback.objects.filter(
            status__name=StatusChoices.RESOLVED,
            updated_at__date__gte=from_date,
            updated_at__date__lte=to_date,
        )
        .annotate(
            month=TruncMonth("updated_at"),
            duration=ExpressionWrapper(
                F("updated_at") - F("created_at"), output_field=DurationField()
            ),
        )
        .values("month")
        .annotate(avg_duration=Avg("duration"))
    )

    avg_map: dict[str, float] = {}
    for row in qs:
        td = row.get("avg_duration")
        if td is None:
            continue
        # Convert timedelta to days with one decimal
        days = round(td.total_seconds() / 86400.0, 1)
        avg_map[row["month"].strftime("%Y-%m")] = days

    data = [
        {"month": f"{key[5:7]}/{key[0:4]}", "avg_days": avg_map.get(key, 0)}
        for key in month_keys
    ]

    if (order or "").lower() == "asc":
        return data
    return list(reversed(data))
