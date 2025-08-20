from django.urls import path, re_path
from .views import (
    get_feedback_list,
    create_feedback,
    get_feedback_detail,
    update_feedback_status,
    get_feedback_overview_stats,
    feedbacks_by_month,
    feedback_types,
    priority_distribution,
    handling_speed,
    export_feedbacks,
    check_export_status,
    download_csv,
)

urlpatterns = [
    path("feedbacks/", get_feedback_list, name="feedback_list"),
    path("feedbacks/create/", create_feedback, name="create_feedback"),
    # Dashboard
    path(
        "feedbacks/dashboard/overview/",
        get_feedback_overview_stats,
        name="feedback_overview_stats",
    ),
    path(
        "feedbacks/dashboard/feedbacks-by-month/",
        feedbacks_by_month,
        name="feedbacks_by_month",
    ),
    path("feedbacks/dashboard/feedback-types/", feedback_types, name="feedback_types"),
    path(
        "feedbacks/dashboard/feedback-priority/",
        priority_distribution,
        name="priority_distribution",
    ),
    path("feedbacks/dashboard/handling-speed/", handling_speed, name="handling_speed"),
    # Export csv
    path("feedbacks/export/", export_feedbacks, name="export_feedbacks"),
    path(
        "feedbacks/export/<str:task_id>/status/",
        check_export_status,
        name="check_export_status",
    ),
    path(
        "feedbacks/export/download/<str:csv_id>/",
        download_csv,
        name="download_csv",
    ),
    path("feedbacks/<str:feedback_id>/", get_feedback_detail, name="feedback_detail"),
    path(
        "feedbacks/<uuid:feedback_id>/status/",
        update_feedback_status,
        name="update_feedback_status",
    ),
]
