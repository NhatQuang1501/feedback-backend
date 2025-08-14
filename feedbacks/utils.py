from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status
from functools import wraps
from accounts.models import User
from django.db.models import Q, F, Func, TextField, Count
from django.db.models.functions import Lower, TruncMonth
from .tasks import (
    send_feedback_confirmation_email,
    send_new_feedback_notification_to_admin,
    send_feedback_status_update_email,
)
from .choices import StatusChoices, FeedbackTypeChoices, PriorityChoices
from .models import Feedback
from django.utils.dateparse import parse_date
from datetime import date
import os



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
        return False, "File không được vượt quá 5MB"

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
    Decorator để xử lý response cho các view feedback, validate dữ liệu, lưu feedback và gửi email thông báo.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            serializer = serializer_class(
                data=request.data, context={"request": request}
            )
            if serializer.is_valid():
                feedback = serializer.save()

                if (
                    hasattr(view_func, "__name__")
                    and view_func.__name__ == "create_feedback"
                ):
                    send_feedback_emails(feedback)

                return Response(
                    serializer_class(feedback, context={"request": request}).data,
                    status=(
                        status.HTTP_201_CREATED
                        if view_func.__name__ == "create_feedback"
                        else status.HTTP_200_OK
                    ),
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


# -------- Query helpers for feedback list --------
def get_multi_values(request, key):
    """Collect multi-value query params in multiple forms and normalize CSV.

    Supports: key=a&key=b, key[]=a&key[]=b, and key=a,b (mixed allowed)
    Returns a flat list of non-empty, stripped strings.
    """
    raw_values = []
    raw_values.extend(request.query_params.getlist(key))
    raw_values.extend(request.query_params.getlist(f"{key}[]"))
    single = request.query_params.get(key)
    if single:
        raw_values.append(single)

    values = []
    for item in raw_values:
        if not isinstance(item, str):
            continue
        for part in item.split(","):
            part_clean = part.strip()
            if part_clean:
                values.append(part_clean)
    return values


def apply_feedback_filters(queryset, status_values, type_values, priority_values):
    """Apply status/type/priority filters when values are provided."""
    if status_values:
        queryset = queryset.filter(status__name__in=[v for v in status_values if v])
    if type_values:
        queryset = queryset.filter(type__name__in=[v for v in type_values if v])
    if priority_values:
        queryset = queryset.filter(priority__name__in=[v for v in priority_values if v])
    return queryset


def apply_keyword_search(queryset, keyword):
    """Search behavior:
    - ASCII (không dấu): unaccent + lower contains
    - Có dấu: icontains (case-insensitive exact substring)
    """
    if not keyword:
        return queryset

    keyword_lower = (keyword or "").strip().lower()
    ascii_only = all(ord(ch) < 128 for ch in keyword_lower)

    if ascii_only:
        queryset = queryset.annotate(
            title_unaccent=Lower(
                Func(F("title"), function="unaccent", output_field=TextField())
            ),
            content_unaccent=Lower(
                Func(F("content"), function="unaccent", output_field=TextField())
            ),
            user_full_name_unaccent=Lower(
                Func(
                    F("user__full_name"),
                    function="unaccent",
                    output_field=TextField(),
                )
            ),
            user_email_unaccent=Lower(
                Func(
                    F("user__email"),
                    function="unaccent",
                    output_field=TextField(),
                )
            ),
        )

        return queryset.filter(
            Q(title_unaccent__contains=keyword_lower)
            | Q(content_unaccent__contains=keyword_lower)
            | Q(user_full_name_unaccent__contains=keyword_lower)
            | Q(user_email_unaccent__contains=keyword_lower)
        )

    return queryset.filter(
        Q(title__icontains=keyword)
        | Q(content__icontains=keyword)
        | Q(user__full_name__icontains=keyword)
        | Q(user__email__icontains=keyword)
    )


def apply_sorting(queryset, sort):
    sort_mapping = {
        "newest": "-created_at",
        "oldest": "created_at",
    }
    return queryset.order_by(sort_mapping.get(sort, "-created_at"))


def _iter_months(start_d: date, end_d: date):
    y, m = start_d.year, start_d.month
    end_y, end_m = end_d.year, end_d.month
    while (y < end_y) or (y == end_y and m <= end_m):
        yield y, m
        m += 1
        if m == 13:
            m = 1
            y += 1


def get_monthly_feedback_counts(from_param: str | None, to_param: str | None, order: str = "desc"):
    to_date = parse_date(to_param) if to_param else date.today()
    if to_date is None:
        raise ValueError("Invalid 'to' date. Expected YYYY-MM-DD")

    from_date = parse_date(from_param) if from_param else None
    if from_date is None:
        months_back = 5
        year = to_date.year
        month = to_date.month - months_back
        while month <= 0:
            month += 12
            year -= 1
        from_date = date(year, month, 1)

    from_date = date(from_date.year, from_date.month, 1)

    if (to_date.year, to_date.month) < (from_date.year, from_date.month):
        raise ValueError("'to' month must be >= 'from' month")

    month_keys = [f"{y:04d}-{m:02d}" for (y, m) in _iter_months(from_date, to_date)]

    queryset = Feedback.objects.filter(
        created_at__date__gte=from_date,
        created_at__date__lte=to_date,
    )

    monthly_counts = (
        queryset.annotate(month=TruncMonth("created_at")).values("month").annotate(
            count=Count("feedback_id")
        )
    )

    counts_map = {item["month"].strftime("%Y-%m"): item["count"] for item in monthly_counts}
    data = [{"month": key, "count": counts_map.get(key, 0)} for key in month_keys]

    if (order or "").lower() == "asc":
        return data
    return list(reversed(data))
