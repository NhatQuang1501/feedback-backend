from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging
from .models import EmailLog
from .choices import StatusChoices

logger = logging.getLogger(__name__)


@shared_task
def send_feedback_confirmation_email(
    feedback_id, user_email, user_name, feedback_title
):
    subject = "Xác nhận đã nhận phản hồi - FeedbackHub"
    body = (
        f"Kính gửi {user_name},\n\n"
        f"Cảm ơn bạn đã gửi phản hồi tới FeedbackHub. Chúng tôi đã nhận được phản hồi của bạn với tiêu đề:\n\n"
        f"'{feedback_title}'\n\n"
        f"Phản hồi của bạn đã được ghi nhận và sẽ được xử lý trong thời gian sớm nhất.\n\n"
        f"Bạn có thể xem chi tiết phản hồi tại: {settings.FRONTEND_URL}/feedbacks/{feedback_id}\n\n"
        "Trân trọng,\n"
        "Đội ngũ FeedbackHub"
    )

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.EMAIL_HOST_USER,
            to=[user_email],
        )
        message.send()

        EmailLog.objects.create(
            feedback_id=feedback_id,
            email_to=user_email,
            subject=subject,
            content=body,
            status="Success",
        )

        logger.info(f"Confirmation email sent successfully to {user_email}")
        return True
    except Exception as e:
        EmailLog.objects.create(
            feedback_id=feedback_id,
            email_to=user_email,
            subject=subject,
            content=body,
            status="Failed",
            error_message=str(e),
        )

        logger.error(f"Failed to send confirmation email to {user_email}: {str(e)}")
        return False


@shared_task
def send_new_feedback_notification_to_admin(
    feedback_id, admin_email, user_name, feedback_title
):
    subject = "Thông báo phản hồi mới - FeedbackHub"
    body = (
        f"Kính gửi Quản trị viên,\n\n"
        f"Hệ thống vừa nhận được một phản hồi mới từ người dùng {user_name} với tiêu đề:\n\n"
        f"'{feedback_title}'\n\n"
        f"Vui lòng truy cập hệ thống để xem chi tiết và xử lý phản hồi này.\n\n"
        f"Link truy cập: {settings.ADMIN_URL}/feedbacks/{feedback_id}\n\n"
        "Trân trọng,\n"
        "Hệ thống FeedbackHub"
    )

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.EMAIL_HOST_USER,
            to=[admin_email],
        )
        message.send()

        EmailLog.objects.create(
            feedback_id=feedback_id,
            email_to=admin_email,
            subject=subject,
            content=body,
            status="Success",
        )

        logger.info(f"Admin notification email sent successfully to {admin_email}")
        return True
    except Exception as e:
        EmailLog.objects.create(
            feedback_id=feedback_id,
            email_to=admin_email,
            subject=subject,
            content=body,
            status="Failed",
            error_message=str(e),
        )

        logger.error(
            f"Failed to send admin notification email to {admin_email}: {str(e)}"
        )
        return False


@shared_task
def send_feedback_status_update_email(
    feedback_id, user_email, user_name, feedback_title, new_status
):
    status_display = StatusChoices.get_display_name(new_status)

    subject = "Cập nhật trạng thái phản hồi - FeedbackHub"
    body = (
        f"Kính gửi {user_name},\n\n"
        f"Phản hồi của bạn với tiêu đề '{feedback_title}' đã được cập nhật trạng thái thành: {status_display}\n\n"
        f"Bạn có thể xem chi tiết phản hồi tại: {settings.FRONTEND_URL}/feedbacks/{feedback_id}\n\n"
        "Trân trọng,\n"
        "Đội ngũ FeedbackHub"
    )

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.EMAIL_HOST_USER,
            to=[user_email],
        )
        message.send()

        EmailLog.objects.create(
            feedback_id=feedback_id,
            email_to=user_email,
            subject=subject,
            content=body,
            status="Success",
        )

        logger.info(f"Status update email sent successfully to {user_email}")
        return True
    except Exception as e:
        EmailLog.objects.create(
            feedback_id=feedback_id,
            email_to=user_email,
            subject=subject,
            content=body,
            status="Failed",
            error_message=str(e),
        )

        logger.error(f"Failed to send status update email to {user_email}: {str(e)}")
        return False
