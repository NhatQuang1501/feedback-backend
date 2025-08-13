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
from .utils import CustomPagination, send_feedback_emails, notify_status_change
from accounts.permissions import IsUser, IsAdmin, IsOwnerOrAdmin


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_feedback_list(request):
    paginator = CustomPagination()

    status_filter = request.query_params.get("status")
    type_filter = request.query_params.get("type")
    priority_filter = request.query_params.get("priority")

    if request.user.role.name == "admin":
        queryset = Feedback.objects.all()
    else:
        queryset = Feedback.objects.filter(user=request.user)

    if status_filter:
        queryset = queryset.filter(status__name=status_filter)
    if type_filter:
        queryset = queryset.filter(type__name=type_filter)
    if priority_filter:
        queryset = queryset.filter(priority__name=priority_filter)

    queryset = queryset.order_by("-created_at")

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
