from django.urls import path
from .views import (
    get_feedback_list,
    create_feedback,
    get_feedback_detail,
    update_feedback_status,
    get_feedback_overview_stats,
    feedbacks_by_month,
    feedback_types,
    priority_distribution,
)

urlpatterns = [
    path("feedbacks/", get_feedback_list, name="feedback_list"),
    path("feedbacks/create/", create_feedback, name="create_feedback"),
    path(
        "feedbacks/<uuid:feedback_id>/",
        get_feedback_detail,
        name="feedback_detail",
    ),
    path(
        "feedbacks/<uuid:feedback_id>/status/",
        update_feedback_status,
        name="update_feedback_status",
    ),
    path("feedbacks/dashboard/overview/", get_feedback_overview_stats, name="feedback_overview_stats"),
    path("feedbacks/dashboard/feedbacks-by-month/", feedbacks_by_month, name="feedbacks_by_month"),
    path("feedbacks/dashboard/feedback-types/", feedback_types, name="feedback_types"),
    path("feedbacks/dashboard/feedback-priority/", priority_distribution, name="priority_distribution"),
]
