#!/usr/bin/env python
import os
import sys
import time
import django
from django.core.management import execute_from_command_line


def main():
    print("Starting Django Backend...")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "feedback.settings")

    # Simple database wait
    print("Waiting for database...")
    time.sleep(5)  # Simple wait instead of complex check

    try:
        # Basic Django setup
        django.setup()
        print("Django setup successful!")

        # Run migrations
        print("Running migrations...")
        execute_from_command_line(["manage.py", "migrate", "--noinput"])

        # Collect static files
        print("Collecting static files...")
        execute_from_command_line(
            ["manage.py", "collectstatic", "--noinput", "--clear"]
        )

        print("Backend setup complete!")
        print("Starting server at http://127.0.0.1:8000")

        # Start server
        execute_from_command_line(["manage.py", "runserver", "0.0.0.0:8000"])

    except Exception as e:
        print(f"Error: {e}")
        print("Starting basic server anyway...")
        os.system("python manage.py runserver 0.0.0.0:8000")


if __name__ == "__main__":
    main()
