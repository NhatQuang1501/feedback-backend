from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
import os

from .models import Feedback
from .serializers import (
    FeedbackListSerializer,
    FeedbackDetailSerializer,
    FeedbackCreateSerializer,
    FeedbackUpdateStatusSerializer,
)
from .utils import (
    CustomPagination,
    send_feedback_emails,
    notify_status_change,
)
from .filters import (
    get_multi_values,
    apply_feedback_filters,
    apply_keyword_search,
    apply_sorting,
)
from .tasks import export_feedbacks_to_csv
from accounts.permissions import IsUser, IsAdmin, IsOwnerOrAdmin


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_feedback_list(request):
    """Lấy danh sách phản hồi với phân trang và lọc."""
    paginator = CustomPagination()

    status_values = get_multi_values(request, "status")
    type_values = get_multi_values(request, "type")
    priority_values = get_multi_values(request, "priority")
    keyword = request.query_params.get("q")
    sort = request.query_params.get("sort", "newest")

    # Role based access control
    is_admin = IsAdmin().is_admin(request.user)
    queryset = (
        Feedback.objects.all()
        if is_admin
        else Feedback.objects.filter(user=request.user)
    )

    # Filter
    queryset = apply_feedback_filters(
        queryset, status_values, type_values, priority_values
    )
    queryset = apply_keyword_search(queryset, keyword)
    queryset = apply_sorting(queryset, sort)

    page = paginator.paginate_queryset(queryset, request)
    serializer = FeedbackListSerializer(page, many=True, context={"request": request})
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_feedback_detail(request, feedback_id):
    """Lấy chi tiết một phản hồi dựa trên ID."""
    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)

    # Kiểm tra quyền truy cập
    if not IsOwnerOrAdmin().is_owner_or_admin(request.user, feedback):
        return Response(
            {"error": "Bạn không có quyền xem feedback này"},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = FeedbackDetailSerializer(feedback, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUser])
@parser_classes([MultiPartParser, FormParser])
def create_feedback(request):
    """Tạo phản hồi mới với tệp đính kèm tùy chọn."""
    try:
        data = {
            "title": request.data.get("title"),
            "content": request.data.get("content"),
            "type_id": request.data.get("type_id"),
            "priority_id": request.data.get("priority_id"),
        }

        files = request.FILES.getlist("files")
        if files:
            data["files"] = files

        serializer = FeedbackCreateSerializer(data=data, context={"request": request})
        if serializer.is_valid():
            feedback = serializer.save()
            send_feedback_emails(feedback)
            return Response(
                FeedbackDetailSerializer(feedback, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["PUT"])
@permission_classes([IsAuthenticated, IsAdmin])
def update_feedback_status(request, feedback_id):
    """Cập nhật trạng thái của phản hồi (chỉ dành cho admin)."""
    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)
    old_status = feedback.status.name

    serializer = FeedbackUpdateStatusSerializer(feedback, data=request.data)
    if serializer.is_valid():
        updated_feedback = serializer.save()

        notify_status_change(updated_feedback, old_status)

        return Response(
            FeedbackDetailSerializer(
                updated_feedback, context={"request": request}
            ).data,
            status=status.HTTP_200_OK,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def export_feedbacks(request):
    """Khởi tạo tác vụ xuất danh sách phản hồi ra file CSV."""
    try:
        # filter parameters
        status_values = request.data.get("status", [])
        type_values = request.data.get("type", [])
        priority_values = request.data.get("priority", [])
        keyword = request.data.get("q")
        sort = request.data.get("sort", "newest")

        task = export_feedbacks_to_csv.delay(
            status_values=status_values,
            type_values=type_values,
            priority_values=priority_values,
            keyword=keyword,
            sort=sort,
            user_email=request.user.email,
        )

        return Response(
            {
                "task_id": task.id,
                "message": "Đang xử lý yêu cầu export. Vui lòng đợi trong giây lát.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def check_export_status(request, task_id):
    """Kiểm tra trạng thái của tác vụ xuất CSV."""
    try:
        task = export_feedbacks_to_csv.AsyncResult(task_id)

        if task.ready():
            result = task.get()
            if result["status"] == "success":
                file_url = request.build_absolute_uri(
                    settings.MEDIA_URL + result["file_path"]
                )

                # Kiểm tra file có tồn tại không
                full_path = os.path.join(settings.MEDIA_ROOT, result["file_path"])
                if not os.path.exists(full_path):
                    return Response(
                        {"status": "error", "message": "File không tồn tại"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                return Response(
                    {
                        "status": "completed",
                        "file_url": file_url,
                        "message": result["message"],
                    }
                )
            else:
                return Response(
                    {"status": "error", "message": result["message"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response({"status": "processing", "message": "Đang xử lý..."})

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
