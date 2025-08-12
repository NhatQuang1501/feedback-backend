from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_email_task(email, subject, body):
    try:
        message = EmailMultiAlternatives(
            subject=subject, body=body, from_email=settings.EMAIL_HOST_USER, to=[email]
        )
        message.send()
        logger.info(f"Email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}")
        return False


@shared_task
def send_otp_email_task(email, full_name, otp, expiry_minutes):
    email_support = "feedbackhub2025@gmail.com"
    hotline = "0123 456 789"
    subject = "Xác thực tài khoản -  FeedbackHub"
    body = (
        f"Kính gửi {full_name},\n\n"
        f"Cảm ơn bạn đã đăng ký tài khoản tại FeedbackHub. Để hoàn tất quá trình đăng ký, vui lòng nhập mã OTP dưới đây:\n\n"
        f"{otp}\n\n"
        f"Mã OTP này có hiệu lực trong {expiry_minutes} phút. Nếu mã hết hạn, vui lòng yêu cầu mã mới từ hệ thống.\n\n"
        "Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email này.\n\n"
        "Cảm ơn bạn đã tin tưởng và sử dụng dịch vụ FeedbackHub. Chúng tôi luôn sẵn sàng hỗ trợ bạn.\n\n"
        "Nếu bạn cần hỗ trợ, vui lòng liên hệ:\n"
        f"  - Email hỗ trợ: {email_support}\n"
        f"  - Hotline: {hotline}\n\n"
        "Trân trọng,\n"
        "Đội ngũ quản lý FeedbackHub"
    )

    try:
        message = EmailMultiAlternatives(
            subject=subject, body=body, from_email=settings.EMAIL_HOST_USER, to=[email]
        )
        message.send()
        logger.info(f"OTP email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False


# @shared_task
# def send_reset_password_email_task(email, full_name, reset_link, expiry_minutes):
#     """Task Celery để gửi email đặt lại mật khẩu"""
#     email_support = "feedbackhub2025@gmail.com"
#     hotline = "0123 456 789"

#     subject = "Đặt lại mật khẩu - FeedbackHub"
#     body = (
#         f"Kính gửi {full_name},\n\n"
#         f"Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn. Để đặt lại mật khẩu, vui lòng nhấp vào liên kết dưới đây:\n\n"
#         f"{reset_link}\n\n"
#         f"Liên kết này có hiệu lực trong {expiry_minutes} phút. Nếu liên kết hết hạn, vui lòng yêu cầu đặt lại mật khẩu mới từ hệ thống.\n\n"
#         "Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email này và đảm bảo rằng bạn vẫn có thể đăng nhập vào tài khoản của mình.\n\n"
#         "Cảm ơn bạn đã tin tưởng và sử dụng dịch vụ FeedbackHub. Chúng tôi luôn sẵn sàng hỗ trợ bạn.\n\n"
#         "Nếu bạn cần hỗ trợ, vui lòng liên hệ:\n"
#         f"  - Email hỗ trợ: {email_support}\n"
#         f"  - Hotline: {hotline}\n\n"
#         "Trân trọng,\n"
#         "Đội ngũ quản lý FeedbackHub"
#     )

#     return send_email_task.delay(email, subject, body)
