import os
import sys
import time
import django
import psycopg2
import redis
from django.core.management import execute_from_command_line


def wait_for_db():
    print("Database connection checking...")
    max_tries = 30
    tries = 0

    while tries < max_tries:
        try:
            conn = psycopg2.connect(
                dbname=os.environ.get("DB_NAME"),
                user=os.environ.get("DB_USER"),
                password=os.environ.get("DB_PASSWORD"),
                host=os.environ.get("DB_HOST"),
                port=os.environ.get("DB_PORT"),
            )
            conn.close()
            print("Database connection successful!")
            return True
        except psycopg2.OperationalError:
            tries += 1
            print(f"Database connection failed, retrying... ({tries}/{max_tries})")
            time.sleep(1)
    return False


def check_redis_connection():
    print("Checking Redis connection...")

    redis_host = os.environ.get("REDIS_HOST", "redis")
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    print(f"Connecting to Redis at {redis_host}:{redis_port}")

    try:
        connection = redis.Redis(
            host=redis_host, port=redis_port, socket_connect_timeout=5
        )
        if connection.ping():
            print("Redis connection successful!")
            return True
        else:
            print("Redis ping failed!")
            return False
    except Exception as e:
        print(f"Redis connection error: {e}")
        return False


def main():
    print("Starting Django Backend...")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "feedback.settings")

    wait_for_db()
    check_redis_connection()

    try:
        # Basic Django setup
        django.setup()
        print("Setup Django succesfully!")

        # Các bước tiếp theo...

        # Run migrations
        print("Running migrations...")
        execute_from_command_line(["manage.py", "migrate", "--noinput"])

        # Collect static files
        print("Collecting static files...")
        execute_from_command_line(
            ["manage.py", "collectstatic", "--noinput", "--clear", "--verbosity", "0"]
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
