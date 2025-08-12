import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "feedback.settings")

# Create Celery app
app = Celery("feedback")

# Load config from Django settings, namespace='CELERY' means all celery-related settings
# should have a `CELERY_` prefix in settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
