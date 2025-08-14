from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
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
    get_multi_values,
    apply_feedback_filters,
    apply_keyword_search,
    apply_sorting,
    get_monthly_feedback_counts,
    get_feedback_type_counts,
    get_priority_distribution_counts,
)
from accounts.permissions import IsUser, IsAdmin, IsOwnerOrAdmin
from django.db.models import Q
from django.db.models import Count
from django.db.models.functions import Lower, TruncMonth
from django.db.models import F, Func, Value, TextField
from .choices import StatusChoices, PriorityChoices
from django.utils.dateparse import parse_date
from datetime import date


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_feedback_list(request):
    paginator = CustomPagination()

    status_values = get_multi_values(request, "status")
    type_values = get_multi_values(request, "type")
    priority_values = get_multi_values(request, "priority")
    keyword = request.query_params.get("q")
    sort = request.query_params.get("sort", "newest")


    queryset = (
        Feedback.objects.all()
        if request.user.role.name == "admin"
        else Feedback.objects.filter(user=request.user)
    )

    queryset = apply_feedback_filters(queryset, status_values, type_values, priority_values)

    queryset = apply_keyword_search(queryset, keyword)


    queryset = apply_sorting(queryset, sort)

    page = paginator.paginate_queryset(queryset, request)
    serializer = FeedbackListSerializer(page, many=True, context={"request": request})
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def get_feedback_detail(request, feedback_id):
    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)

    if request.user.role.name != "admin" and feedback.user != request.user:
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
    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)
    old_status = feedback.status.name

    serializer = FeedbackUpdateStatusSerializer(feedback, data=request.data)
    if serializer.is_valid():
        updated_feedback = serializer.save()

        notify_status_change(updated_feedback, old_status)

        return Response(
            FeedbackDetailSerializer(
                updated_feedback, context={"request": request}
            ).data
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def get_feedback_overview_stats(request):
    """Thống kê tổng quan dành cho admin.

    Trả về:
    - total_feedbacks
    - pending_feedbacks
    - processing_feedbacks
    - resolved_feedbacks
    """
    stats = Feedback.objects.aggregate(
        total_feedbacks=Count("feedback_id"),
        pending_feedbacks=Count(
            "feedback_id", filter=Q(status__name=StatusChoices.PENDING)
        ),
        processing_feedbacks=Count(
            "feedback_id", filter=Q(status__name=StatusChoices.PROCESSING)
        ),
        resolved_feedbacks=Count(
            "feedback_id", filter=Q(status__name=StatusChoices.RESOLVED)
        ),
        high_priority_pending_feedbacks=Count(
            "feedback_id",
            filter=Q(
                priority__name=PriorityChoices.HIGH,
                status__name=StatusChoices.PENDING,
            ),
        ),
    )

    return Response(stats, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def feedbacks_by_month(request):
    """Thống kê số lượng feedback theo tháng trong khoảng thời gian (Admin-only)."""
    try:
        data = get_monthly_feedback_counts(
            request.query_params.get("from"),
            request.query_params.get("to"),
            request.query_params.get("order") or "desc",
        )
        return Response(data, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def feedback_types(request):
    """Thống kê số lượng theo loại phản hồi trong khoảng thời gian (Admin-only)."""
    try:
        data = get_feedback_type_counts(
            request.query_params.get("from"),
            request.query_params.get("to"),
        )
        return Response(data, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def priority_distribution(request):
    """Phân bố số lượng theo mức độ ưu tiên trong khoảng thời gian (Admin-only)."""
    try:
        data = get_priority_distribution_counts(
            request.query_params.get("from"),
            request.query_params.get("to"),
        )
        return Response(data, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
