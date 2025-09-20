"""
JWT Authentication for Analytics Service
Validates JWT tokens issued by the Auth Service
"""

import logging

from django.conf import settings
from django.contrib.auth.models import AnonymousUser

import jwt
import requests
from rest_framework import authentication, exceptions

logger = logging.getLogger(__name__)


class AnalyticsUser:
    """
    Simple user class for analytics service
    Contains user information extracted from JWT token
    """

    def __init__(self, user_data):
        self.id = user_data.get("user_id")
        self.email = user_data.get("email", "")
        self.first_name = user_data.get("first_name", "")
        self.last_name = user_data.get("last_name", "")
        self.role = user_data.get("role", "developer")
        self.company_id = user_data.get("company_id")
        self.is_authenticated = True
        self.is_anonymous = False

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def is_admin(self):
        return self.role == "admin"

    def is_supervisor(self):
        return self.role in ["admin", "supervisor"]


class JWTAuthentication(authentication.BaseAuthentication):
    """
    JWT Authentication class for Analytics Service
    """

    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token).
        """
        auth_header = request.META.get("HTTP_AUTHORIZATION")

        if not auth_header:
            return None

        try:
            # Extract token from "Bearer <token>" format
            token_type, token = auth_header.split(" ", 1)
            if token_type.lower() != "bearer":
                return None

        except ValueError:
            return None

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token):
        """
        Authenticate the JWT token and return user information.
        """
        try:
            # Decode JWT token
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])

            # Verify token type
            if payload.get("token_type") != "access":
                raise exceptions.AuthenticationFailed("Invalid token type")

            # Check if token is expired
            import time

            if payload.get("exp", 0) < time.time():
                raise exceptions.AuthenticationFailed("Token has expired")

            # Verify issuer
            if payload.get("iss") != "syncscope-auth":
                raise exceptions.AuthenticationFailed("Invalid token issuer")

            # Create user object from token payload
            user = AnalyticsUser(payload)

            return (user, token)

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise exceptions.AuthenticationFailed("Invalid token")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise exceptions.AuthenticationFailed("Authentication failed")

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return "Bearer"


class ServiceAuthentication:
    """
    Authentication helper for inter-service communication
    """

    @staticmethod
    def verify_service_token(token):
        """
        Verify a service-to-service authentication token
        """
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])

            # Check if it's a service token
            if payload.get("token_type") != "service":
                return False

            # Verify service name
            service_name = payload.get("service_name")
            if service_name not in ["monitoring", "management", "alerts"]:
                return False

            return True

        except jwt.InvalidTokenError:
            return False

    @staticmethod
    def create_service_token(service_name="analytics"):
        """
        Create a service authentication token for outgoing requests
        """
        import time

        payload = {
            "token_type": "service",
            "service_name": service_name,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,  # 1 hour expiration
            "iss": "syncscope-analytics",
        }

        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


class UserPermissions:
    """
    Helper class to check user permissions for analytics operations
    """

    @staticmethod
    def can_view_team_analytics(user, team_id):
        """
        Check if user can view analytics for a specific team
        """
        if user.is_admin():
            return True

        # TODO: Implement team membership check via Management Service
        # For now, allow all authenticated users
        return user.is_authenticated

    @staticmethod
    def can_view_company_analytics(user, company_id):
        """
        Check if user can view company-wide analytics
        """
        if user.is_admin():
            return True

        # User can view their own company's analytics
        return user.company_id == company_id

    @staticmethod
    def can_generate_reports(user):
        """
        Check if user can generate reports
        """
        # All authenticated users can generate reports
        return user.is_authenticated

    @staticmethod
    def can_view_individual_analytics(user, target_user_id):
        """
        Check if user can view analytics for a specific individual
        """
        if user.is_admin():
            return True

        if user.is_supervisor():
            # TODO: Check if user supervises the target user
            return True

        # Users can view their own analytics
        return str(user.id) == str(target_user_id)

    @staticmethod
    def can_export_data(user):
        """
        Check if user can export analytics data
        """
        # Only supervisors and admins can export data
        return user.is_supervisor()

    @staticmethod
    def can_manage_metrics(user):
        """
        Check if user can manage metric definitions
        """
        # Only admins can manage metric definitions
        return user.is_admin()


def get_auth_headers():
    """
    Get authentication headers for outgoing requests to other services
    """
    service_token = ServiceAuthentication.create_service_token()
    return {
        "Authorization": f"Bearer {service_token}",
        "Content-Type": "application/json",
    }
