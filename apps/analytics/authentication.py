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
        self.pk = user_data.get("user_id")  # Add pk for django compatibility
        self.user_id = user_data.get("user_id")
        self.email = user_data.get("email", "")
        self.username = user_data.get("username", "")
        self.first_name = user_data.get("first_name", "")
        self.last_name = user_data.get("last_name", "")
        self.role = user_data.get("role", "developer")
        self.company_id = user_data.get("company_id")
        self.is_authenticated = True
        self.is_anonymous = False
        self.is_staff = user_data.get("is_staff", False)
        self.is_superuser = user_data.get("is_superuser", False)
        self._user_data = user_data

    def __str__(self):
        if self.first_name and self.last_name and self.email:
            return f"{self.first_name} {self.last_name} ({self.email})"
        return f"AnalyticsUser({self.user_id})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def is_admin(self):
        return self.role == "admin"

    def is_supervisor(self):
        return self.role in ["admin", "supervisor"]

    def has_perm(self, perm, obj=None):
        """Check if user has permission."""
        return self.is_staff or self.is_superuser

    def has_perms(self, perm_list, obj=None):
        """Check if user has multiple permissions."""
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, package_name):
        """Check if user has permissions for a module."""
        return self.is_staff or self.is_superuser

    def get_user_data(self):
        """Get original user data from token."""
        return self._user_data


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
            # Decode JWT token - use same SECRET_KEY as auth service
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

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
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

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

        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


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


def get_auth_headers(service_name=None):
    """
    Get authentication headers for outgoing requests to other services
    Different services use different authentication methods:
    - Monitoring service: Uses X-Service-Token header
    - Management service: Uses Authorization Bearer token with auth service validation
    - Auth service: Uses Authorization Bearer token
    """
    service_token = ServiceAuthentication.create_service_token()

    # Monitoring service uses X-Service-Token header
    if service_name == "monitoring":
        return {
            "X-Service-Token": service_token,
            "Content-Type": "application/json",
        }

    # Other services (management, auth) use standard Authorization header
    return {
        "Authorization": f"Bearer {service_token}",
        "Content-Type": "application/json",
    }
