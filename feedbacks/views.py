from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Feedback, Attachment
from .serializers import (
    FeedbackListSerializer,
    FeedbackDetailSerializer,
    FeedbackCreateSerializer,
    FeedbackUpdateStatusSerializer,
    AttachmentSerializer,
)
from .utils import CustomPagination, handle_feedback_response, notify_status_change
from accounts.permissions import IsUser, IsAdmin, IsOwnerOrAdmin


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_feedback_list(request):
    paginator = CustomPagination()

    # Basic filter
    status_filter = request.query_params.get("status")
    type_filter = request.query_params.get("type")
    priority_filter = request.query_params.get("priority")

    if request.user.role.name == "admin":
        queryset = Feedback.objects.all()
    else:
        queryset = Feedback.objects.filter(user=request.user)

    # Apply filters
    if status_filter:
        queryset = queryset.filter(status__name=status_filter)
    if type_filter:
        queryset = queryset.filter(type__name=type_filter)
    if priority_filter:
        queryset = queryset.filter(priority__name=priority_filter)

    queryset = queryset.order_by("-created_at")

    page = paginator.paginate_queryset(queryset, request)
    serializer = FeedbackListSerializer(page, many=True)

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

    serializer = FeedbackDetailSerializer(feedback)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUser])
@handle_feedback_response(FeedbackCreateSerializer)
def create_feedback(request):
    pass


@api_view(["PUT"])
@permission_classes([IsAuthenticated, IsAdmin])
def update_feedback_status(request, feedback_id):
    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)
    old_status = feedback.status.name

    serializer = FeedbackUpdateStatusSerializer(feedback, data=request.data)
    if serializer.is_valid():
        updated_feedback = serializer.save()

        notify_status_change(updated_feedback, old_status)

        return Response(FeedbackDetailSerializer(updated_feedback).data)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsOwnerOrAdmin])
def upload_attachment(request, feedback_id):
    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)

    if request.user.role.name != "admin" and feedback.user != request.user:
        return Response(
            {"error": "Bạn không có quyền upload file cho feedback này"},
            status=status.HTTP_403_FORBIDDEN,
        )

    if "file" not in request.FILES:
        return Response(
            {"error": "Không có file nào được upload"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    file = request.FILES["file"]

    attachment_data = {
        "feedback": feedback,
        "file_name": file.name,
        "file_url": file,
        "file_type": file.content_type,
    }

    serializer = AttachmentSerializer(data=attachment_data)
    if serializer.is_valid():
        attachment = serializer.create(attachment_data)
        return Response(
            AttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
