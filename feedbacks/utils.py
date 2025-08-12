from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status
from functools import wraps
from accounts.models import User
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
