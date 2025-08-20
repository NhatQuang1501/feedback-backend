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
from .filters import (
    get_multi_values,
    apply_feedback_filters,
    apply_keyword_search,
    apply_sorting,
)
from .utils import (
    CustomPagination,
    send_feedback_emails,
    notify_status_change,
    get_monthly_feedback_counts,
    get_feedback_type_counts,
    get_priority_distribution_counts,
    get_handling_speed_by_month,
)
from accounts.permissions import IsUser, IsAdmin, IsOwnerOrAdmin
from django.db.models import Q
from django.db.models import Count
from .choices import StatusChoices, PriorityChoices

import json
from django.http import StreamingHttpResponse
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .tasks import export_feedbacks_to_csv
from accounts.permissions import IsAdmin

import uuid as uuid_module


def clean_feedback_id(feedback_id):
    if feedback_id.startswith("\ufeff"):
        feedback_id = feedback_id[1:]
    try:
        uuid_module.UUID(feedback_id)
        return feedback_id
    except ValueError:
        raise ValueError("Invalid UUID format")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_feedback_list(request):
    paginator = CustomPagination()

    status_values = get_multi_values(request, "status")
    type_values = get_multi_values(request, "type")
    priority_values = get_multi_values(request, "priority")
    keyword = request.query_params.get("q")
    sort = request.query_params.get("sort", "newest")

    is_admin = IsAdmin().is_admin(request.user)
    queryset = (
        Feedback.objects.all()
        if is_admin
        else Feedback.objects.filter(user=request.user)
    )

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
    try:
        feedback_id = clean_feedback_id(feedback_id)
    except ValueError:
        return Response(
            {"error": "Invalid feedback ID format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)

    if not IsOwnerOrAdmin().is_owner_or_admin(request.user, feedback):
        return Response(
            {"error": "You don't have permission to view this feedback"},
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
    try:
        feedback = get_object_or_404(Feedback, feedback_id=feedback_id)
    except ValueError:
        return Response(
            {"error": "Invalid feedback ID format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

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


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def get_feedback_overview_stats(request):
    """
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
    try:
        data = get_priority_distribution_counts(
            request.query_params.get("from"),
            request.query_params.get("to"),
        )
        return Response(data, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def handling_speed(request):
    try:
        data = get_handling_speed_by_month(
            request.query_params.get("from"),
            request.query_params.get("to"),
            request.query_params.get("order") or "desc",
        )
        return Response(data, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def export_feedbacks(request):
    try:
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
                "message": "Processing export request...",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def check_export_status(request, task_id):
    try:
        task = export_feedbacks_to_csv.AsyncResult(task_id)

        if task.ready():
            result = task.get()
            if result["status"] == "success":
                download_path = f"/api/feedbacks/export/download/{result['csv_id']}/"
                return Response(
                    {
                        "status": "completed",
                        "csv_id": result["csv_id"],
                        "filename": result["filename"],
                        "message": result["message"],
                        "download_url": request.build_absolute_uri(download_path),
                    }
                )
            else:
                return Response(
                    {"status": "error", "message": result["message"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response({"status": "processing", "message": "Processing..."})

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def download_csv(request, csv_id):
    try:
        cache_key = f"csv_export:{csv_id}"
        cached_data = cache.get(cache_key)

        if not cached_data:
            return Response(
                {"error": "CSV data not found or expired"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = json.loads(cached_data)
        csv_data = data.get("csv_data")
        filename = data.get("filename")

        if not csv_data or not filename:
            return Response(
                {"error": "Invalid CSV data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        def csv_generator():
            yield "\ufeff"
            for line in csv_data.splitlines():
                yield line + "\n"

        response = StreamingHttpResponse(
            csv_generator(), content_type="text/csv; charset=utf-8"
        )

        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        return Response(
            {"error": f"Error when downloading CSV file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
