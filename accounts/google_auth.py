import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Role
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class GoogleAuthError(Exception):
    """Custom exception for Google Auth errors"""

    pass


class GoogleAuthService:
    """Service class to handle Google OAuth authentication"""

    @staticmethod
    def verify_google_token(token):
        """
        Verify Google ID token and return user info

        Args:
            token (str): Google ID token from frontend

        Returns:
            dict: User information from Google

        Raises:
            GoogleAuthError: If token verification fails
        """
        try:
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )

            # Check if token is from correct issuer
            if idinfo["iss"] not in [
                "accounts.google.com",
                "https://accounts.google.com",
            ]:
                raise GoogleAuthError("Invalid token issuer")

            return {
                "google_id": idinfo["sub"],
                "email": idinfo["email"],
                "full_name": idinfo.get("name", ""),
                "first_name": idinfo.get("given_name", ""),
                "last_name": idinfo.get("family_name", ""),
                "picture": idinfo.get("picture", ""),
                "email_verified": idinfo.get("email_verified", False),
            }

        except ValueError as e:
            logger.error(f"Google token verification failed: {str(e)}")
            raise GoogleAuthError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during Google auth: {str(e)}")
            raise GoogleAuthError(f"Authentication failed: {str(e)}")

    @staticmethod
    def get_or_create_user(google_user_info):
        """
        Get existing user or create new user from Google info

        Args:
            google_user_info (dict): User info from Google

        Returns:
            tuple: (User instance, created boolean)
        """
        email = google_user_info["email"]
        google_id = google_user_info["google_id"]

        try:
            # Try to find existing user by email
            user = User.objects.get(email=email)

            # If user exists but doesn't have Google OAuth info, update it
            if not user.oauth_provider:
                user.oauth_provider = "google"
                user.oauth_uid = google_id
                user.is_active = True  # Google users are pre-verified
                user.save()
                logger.info(f"Updated existing user {email} with Google OAuth info")

            return user, False

        except User.DoesNotExist:
            # Create new user
            try:
                # Get or create default user role
                user_role, _ = Role.objects.get_or_create(
                    name="user", defaults={"description": "Regular user"}
                )

                user = User.objects.create(
                    email=email,
                    full_name=google_user_info["full_name"],
                    oauth_provider="google",
                    oauth_uid=google_id,
                    is_active=True,  # Google users are pre-verified
                    role=user_role,
                )

                logger.info(f"Created new Google user: {email}")
                return user, True

            except Exception as e:
                logger.error(f"Failed to create Google user {email}: {str(e)}")
                raise GoogleAuthError(f"Failed to create user: {str(e)}")

    @staticmethod
    def authenticate_google_user(token):
        """
        Complete Google authentication flow

        Args:
            token (str): Google ID token

        Returns:
            tuple: (User instance, created boolean)

        Raises:
            GoogleAuthError: If authentication fails
        """
        # Step 1: Verify token and get user info
        google_user_info = GoogleAuthService.verify_google_token(token)

        # Step 2: Check if email is verified
        if not google_user_info.get("email_verified", False):
            raise GoogleAuthError("Email not verified with Google")

        # Step 3: Get or create user
        user, created = GoogleAuthService.get_or_create_user(google_user_info)

        return user, created


def get_google_user_info_from_access_token(access_token):
    """
    Alternative method: Get user info using Google access token
    (In case frontend sends access token instead of ID token)

    Args:
        access_token (str): Google access token

    Returns:
        dict: User information

    Raises:
        GoogleAuthError: If request fails
    """
    try:
        response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )

        if response.status_code != 200:
            raise GoogleAuthError(f"Failed to get user info: {response.status_code}")

        user_data = response.json()

        return {
            "google_id": user_data["id"],
            "email": user_data["email"],
            "full_name": user_data.get("name", ""),
            "first_name": user_data.get("given_name", ""),
            "last_name": user_data.get("family_name", ""),
            "picture": user_data.get("picture", ""),
            "email_verified": user_data.get("verified_email", False),
        }

    except requests.RequestException as e:
        logger.error(f"Failed to fetch Google user info: {str(e)}")
        raise GoogleAuthError(f"Failed to fetch user info: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching Google user info: {str(e)}")
        raise GoogleAuthError(f"Authentication failed: {str(e)}")
