import csv
import os
import logging
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone

from .models import EmailLog, Feedback, Attachment
from .choices import StatusChoices
from .filters import apply_feedback_filters, apply_keyword_search, apply_sorting

logger = logging.getLogger(__name__)


def log_email(feedback_id, email_to, subject, content, status, error_message=None):
    EmailLog.objects.create(
        feedback_id=feedback_id,
        email_to=email_to,
        subject=subject,
        content=content,
        status=status,
        error_message=error_message,
    )


def send_email(subject, body, to_email, feedback_id):
    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.EMAIL_HOST_USER,
            to=[to_email],
        )
        message.send()

        log_email(feedback_id, to_email, subject, body, "Success")
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        log_email(feedback_id, to_email, subject, body, "Failed", str(e))
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


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
    return send_email(subject, body, user_email, feedback_id)


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
    return send_email(subject, body, admin_email, feedback_id)


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
    return send_email(subject, body, user_email, feedback_id)


@shared_task
def export_feedbacks_to_csv(
    status_values=None,
    type_values=None,
    priority_values=None,
    keyword=None,
    sort="newest",
    user_email=None,
):
    """Export danh sách feedback sang file CSV."""
    try:
        # Tạo thư mục lưu file nếu chưa tồn tại
        export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
        os.makedirs(export_dir, exist_ok=True)

        # Tạo tên file với timestamp
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"feedbacks_export_{timestamp}.csv"
        filepath = os.path.join(export_dir, filename)

        # Log đường dẫn đầy đủ của file để debug
        logger.info(f"Exporting CSV to: {filepath}")

        # Áp dụng các filter - Sử dụng select_related và prefetch_related để tối ưu query
        queryset = Feedback.objects.select_related(
            "user", "type", "priority", "status"
        ).prefetch_related("attachments")
        queryset = apply_feedback_filters(
            queryset, status_values, type_values, priority_values
        )
        queryset = apply_keyword_search(queryset, keyword)
        queryset = apply_sorting(queryset, sort)

        # Đếm số lượng records để log và phản hồi người dùng
        count = queryset.count()
        logger.info(f"Exporting {count} feedback records")

        # Ghi dữ liệu trực tiếp vào file thay vì buffer để tiết kiệm bộ nhớ
        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as csv_file:
            fieldnames = [
                "Feedback ID",
                "Tiêu đề",
                "Nội dung",
                "Loại phản hồi",
                "Mức độ ưu tiên",
                "Trạng thái",
                "Người gửi",
                "Email",
                "Ngày tạo",
                "Ngày cập nhật",
                "File đính kèm",
            ]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            # Xử lý từng feedback với chunk_size để tránh giữ tất cả dữ liệu trong bộ nhớ
            chunk_size = 100  # Xử lý 100 records mỗi lần
            for feedback in queryset.iterator(chunk_size=chunk_size):
                # Lấy attachments - do đã prefetch_related nên không tạo thêm query
                attachments = ", ".join(
                    [attachment.file_name for attachment in feedback.attachments.all()]
                )

                writer.writerow(
                    {
                        "Feedback ID": str(feedback.feedback_id),
                        "Tiêu đề": feedback.title,
                        "Nội dung": feedback.content,
                        "Loại phản hồi": str(feedback.type),
                        "Mức độ ưu tiên": str(feedback.priority),
                        "Trạng thái": str(feedback.status),
                        "Người gửi": feedback.user.full_name,
                        "Email": feedback.user.email,
                        "Ngày tạo": feedback.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "Ngày cập nhật": feedback.updated_at.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "File đính kèm": attachments,
                    }
                )

        # Trả về đường dẫn tương đối để truy cập qua URL
        # relative_path = os.path.join("exports", filename)
        relative_path = f"exports/{filename}"

        # Thêm thông tin số lượng records vào kết quả
        return {
            "status": "success",
            "file_path": relative_path,
            "message": f"Export thành công {count} bản ghi",
            "count": count,
            "filename": filename,
        }

    except Exception as e:
        error_msg = f"Export error: {str(e)}"
        logger.error(error_msg, exc_info=True)  # Log full traceback
        return {"status": "error", "message": f"Lỗi khi export: {str(e)}"}
