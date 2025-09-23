"""
Tests for analytics authentication module
"""

import time
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import RequestFactory

import jwt
import pytest
from rest_framework import exceptions

from apps.analytics.authentication import (
    AnalyticsUser,
    JWTAuthentication,
    ServiceAuthentication,
    UserPermissions,
    get_auth_headers,
)


class TestAnalyticsUser:
    """Test AnalyticsUser class"""

    def test_init_with_all_fields(self):
        """Test AnalyticsUser initialization with all fields"""
        user_data = {
            "user_id": 123,
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "admin",
            "company_id": 456,
        }
        user = AnalyticsUser(user_data)

        assert user.id == 123
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.role == "admin"
        assert user.company_id == 456
        assert user.is_authenticated is True
        assert user.is_anonymous is False

    def test_init_with_minimal_fields(self):
        """Test AnalyticsUser initialization with minimal fields"""
        user_data = {"user_id": 123}
        user = AnalyticsUser(user_data)

        assert user.id == 123
        assert user.email == ""
        assert user.first_name == ""
        assert user.last_name == ""
        assert user.role == "developer"
        assert user.company_id is None

    def test_str_representation(self):
        """Test string representation of user"""
        user_data = {
            "user_id": 123,
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
        }
        user = AnalyticsUser(user_data)
        assert str(user) == "John Doe (test@example.com)"

    def test_full_name_property(self):
        """Test full_name property"""
        user_data = {"first_name": "John", "last_name": "Doe"}
        user = AnalyticsUser(user_data)
        assert user.full_name == "John Doe"

        # Test with only first name
        user_data = {"first_name": "John", "last_name": ""}
        user = AnalyticsUser(user_data)
        assert user.full_name == "John"

        # Test with empty names
        user_data = {"first_name": "", "last_name": ""}
        user = AnalyticsUser(user_data)
        assert user.full_name == ""

    def test_is_admin(self):
        """Test is_admin method"""
        admin_user = AnalyticsUser({"role": "admin"})
        assert admin_user.is_admin() is True

        dev_user = AnalyticsUser({"role": "developer"})
        assert dev_user.is_admin() is False

    def test_is_supervisor(self):
        """Test is_supervisor method"""
        admin_user = AnalyticsUser({"role": "admin"})
        assert admin_user.is_supervisor() is True

        supervisor_user = AnalyticsUser({"role": "supervisor"})
        assert supervisor_user.is_supervisor() is True

        dev_user = AnalyticsUser({"role": "developer"})
        assert dev_user.is_supervisor() is False


class TestJWTAuthentication:
    """Test JWTAuthentication class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.auth = JWTAuthentication()
        self.factory = RequestFactory()

    def test_authenticate_no_header(self):
        """Test authentication with no authorization header"""
        request = self.factory.get("/")
        result = self.auth.authenticate(request)
        assert result is None

    def test_authenticate_invalid_header_format(self):
        """Test authentication with invalid header format"""
        request = self.factory.get("/", HTTP_AUTHORIZATION="InvalidFormat")
        result = self.auth.authenticate(request)
        assert result is None

    def test_authenticate_non_bearer_token(self):
        """Test authentication with non-Bearer token"""
        request = self.factory.get("/", HTTP_AUTHORIZATION="Basic token123")
        result = self.auth.authenticate(request)
        assert result is None

    @patch("apps.analytics.authentication.jwt.decode")
    def test_authenticate_valid_token(self, mock_decode):
        """Test authentication with valid token"""
        # Mock JWT decode
        mock_payload = {
            "user_id": 123,
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "developer",
            "company_id": 456,
            "token_type": "access",
            "exp": int(time.time()) + 3600,
            "iss": "syncscope-auth",
        }
        mock_decode.return_value = mock_payload

        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer valid_token")
        user, token = self.auth.authenticate(request)

        assert isinstance(user, AnalyticsUser)
        assert user.id == 123
        assert user.email == "test@example.com"
        assert token == "valid_token"

    @patch("apps.analytics.authentication.jwt.decode")
    def test_authenticate_invalid_token_type(self, mock_decode):
        """Test authentication with refresh token (should still work with simplified auth)"""
        mock_payload = {
            "user_id": 123,
            "token_type": "refresh",  # No longer validates token type
            "exp": int(time.time()) + 3600,
            "iss": "syncscope-auth",
        }
        mock_decode.return_value = mock_payload

        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer refresh_token")

        # With simplified auth, this should work
        user, token = self.auth.authenticate(request)
        assert isinstance(user, AnalyticsUser)
        assert user.id == 123

    @patch("apps.analytics.authentication.jwt.decode")
    def test_authenticate_expired_token(self, mock_decode):
        """Test authentication with expired token - JWT library handles expiration"""
        # Mock JWT library to raise ExpiredSignatureError for expired token
        mock_decode.side_effect = jwt.ExpiredSignatureError("Token has expired")

        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer expired_token")

        with pytest.raises(exceptions.AuthenticationFailed, match="Invalid token"):
            self.auth.authenticate(request)

    @patch("apps.analytics.authentication.jwt.decode")
    def test_authenticate_invalid_issuer(self, mock_decode):
        """Test authentication with invalid issuer (should work with simplified auth)"""
        mock_payload = {
            "user_id": 123,
            "token_type": "access",
            "exp": int(time.time()) + 3600,
            "iss": "invalid-issuer",  # No longer validates issuer
        }
        mock_decode.return_value = mock_payload

        request = self.factory.get(
            "/", HTTP_AUTHORIZATION="Bearer different_issuer_token"
        )

        # With simplified auth, this should work
        user, token = self.auth.authenticate(request)
        assert isinstance(user, AnalyticsUser)
        assert user.id == 123

    @patch("apps.analytics.authentication.jwt.decode")
    def test_authenticate_jwt_decode_error(self, mock_decode):
        """Test authentication with JWT decode error"""
        mock_decode.side_effect = jwt.InvalidTokenError("Invalid token")

        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer invalid_token")

        with pytest.raises(exceptions.AuthenticationFailed, match="Invalid token"):
            self.auth.authenticate(request)

    @patch("apps.analytics.authentication.jwt.decode")
    def test_authenticate_general_exception(self, mock_decode):
        """Test authentication with general exception"""
        mock_decode.side_effect = Exception("Something went wrong")

        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer error_token")

        with pytest.raises(
            exceptions.AuthenticationFailed, match="Authentication failed"
        ):
            self.auth.authenticate(request)

    def test_authenticate_header(self):
        """Test authenticate_header method"""
        request = self.factory.get("/")
        header = self.auth.authenticate_header(request)
        assert header == "Bearer"


class TestServiceAuthentication:
    """Test ServiceAuthentication class"""

    @patch("apps.analytics.authentication.jwt.decode")
    def test_verify_service_token_valid(self, mock_decode):
        """Test verifying valid service token"""
        mock_payload = {
            "token_type": "service",
            "service_name": "monitoring",
        }
        mock_decode.return_value = mock_payload

        result = ServiceAuthentication.verify_service_token("valid_service_token")
        assert result is True

    @patch("apps.analytics.authentication.jwt.decode")
    def test_verify_service_token_invalid_type(self, mock_decode):
        """Test verifying service token with invalid type"""
        mock_payload = {
            "token_type": "access",  # Not service type
            "service_name": "monitoring",
        }
        mock_decode.return_value = mock_payload

        result = ServiceAuthentication.verify_service_token("invalid_type_token")
        assert result is False

    @patch("apps.analytics.authentication.jwt.decode")
    def test_verify_service_token_invalid_service_name(self, mock_decode):
        """Test verifying service token with invalid service name"""
        mock_payload = {
            "token_type": "service",
            "service_name": "invalid_service",  # Not in allowed list
        }
        mock_decode.return_value = mock_payload

        result = ServiceAuthentication.verify_service_token("invalid_service_token")
        assert result is False

    @patch("apps.analytics.authentication.jwt.decode")
    def test_verify_service_token_jwt_error(self, mock_decode):
        """Test verifying service token with JWT error"""
        mock_decode.side_effect = jwt.InvalidTokenError("Invalid token")

        result = ServiceAuthentication.verify_service_token("malformed_token")
        assert result is False

    @patch("apps.analytics.authentication.jwt.encode")
    @patch("time.time")
    def test_create_service_token(self, mock_time, mock_encode):
        """Test creating service token"""
        mock_time.return_value = 1000
        mock_encode.return_value = "service_token_123"

        token = ServiceAuthentication.create_service_token("analytics")

        expected_payload = {
            "token_type": "service",
            "service_name": "analytics",
            "iat": 1000,
            "exp": 4600,
            "iss": "syncscope-analytics",
        }

        mock_encode.assert_called_once_with(
            expected_payload, settings.JWT_SECRET_KEY, algorithm="HS256"
        )
        assert token == "service_token_123"

    @patch("apps.analytics.authentication.jwt.encode")
    @patch("time.time")
    def test_create_service_token_default_service(self, mock_time, mock_encode):
        """Test creating service token with default service name"""
        mock_time.return_value = 1000
        mock_encode.return_value = "default_token_123"

        token = ServiceAuthentication.create_service_token()

        expected_payload = {
            "token_type": "service",
            "service_name": "analytics",
            "iat": 1000,
            "exp": 4600,
            "iss": "syncscope-analytics",
        }

        mock_encode.assert_called_once_with(
            expected_payload, settings.JWT_SECRET_KEY, algorithm="HS256"
        )
        assert token == "default_token_123"


class TestUserPermissions:
    """Test UserPermissions class"""

    def test_can_view_team_analytics_admin(self):
        """Test admin can view team analytics"""
        admin_user = AnalyticsUser({"role": "admin"})
        result = UserPermissions.can_view_team_analytics(admin_user, "team_123")
        assert result is True

    def test_can_view_team_analytics_authenticated(self):
        """Test authenticated user can view team analytics"""
        user = AnalyticsUser({"role": "developer"})
        result = UserPermissions.can_view_team_analytics(user, "team_123")
        assert result is True

    def test_can_view_company_analytics_admin(self):
        """Test admin can view company analytics"""
        admin_user = AnalyticsUser({"role": "admin"})
        result = UserPermissions.can_view_company_analytics(admin_user, "company_123")
        assert result is True

    def test_can_view_company_analytics_same_company(self):
        """Test user can view own company analytics"""
        user = AnalyticsUser({"company_id": "company_123"})
        result = UserPermissions.can_view_company_analytics(user, "company_123")
        assert result is True

    def test_can_view_company_analytics_different_company(self):
        """Test user cannot view different company analytics"""
        user = AnalyticsUser({"company_id": "company_456"})
        result = UserPermissions.can_view_company_analytics(user, "company_123")
        assert result is False

    def test_can_generate_reports_authenticated(self):
        """Test authenticated user can generate reports"""
        user = AnalyticsUser({"role": "developer"})
        result = UserPermissions.can_generate_reports(user)
        assert result is True

    def test_can_view_individual_analytics_admin(self):
        """Test admin can view individual analytics"""
        admin_user = AnalyticsUser({"role": "admin"})
        result = UserPermissions.can_view_individual_analytics(admin_user, "user_123")
        assert result is True

    def test_can_view_individual_analytics_supervisor(self):
        """Test supervisor can view individual analytics"""
        supervisor_user = AnalyticsUser({"role": "supervisor"})
        result = UserPermissions.can_view_individual_analytics(
            supervisor_user, "user_123"
        )
        assert result is True

    def test_can_view_individual_analytics_own_data(self):
        """Test user can view own analytics"""
        user = AnalyticsUser({"user_id": 123})
        result = UserPermissions.can_view_individual_analytics(user, "123")
        assert result is True

    def test_can_view_individual_analytics_other_user(self):
        """Test user cannot view other user's analytics"""
        user = AnalyticsUser({"user_id": 123, "role": "developer"})
        result = UserPermissions.can_view_individual_analytics(user, "456")
        assert result is False

    def test_can_export_data_supervisor(self):
        """Test supervisor can export data"""
        supervisor_user = AnalyticsUser({"role": "supervisor"})
        result = UserPermissions.can_export_data(supervisor_user)
        assert result is True

    def test_can_export_data_admin(self):
        """Test admin can export data"""
        admin_user = AnalyticsUser({"role": "admin"})
        result = UserPermissions.can_export_data(admin_user)
        assert result is True

    def test_can_export_data_developer(self):
        """Test developer cannot export data"""
        dev_user = AnalyticsUser({"role": "developer"})
        result = UserPermissions.can_export_data(dev_user)
        assert result is False

    def test_can_manage_metrics_admin(self):
        """Test admin can manage metrics"""
        admin_user = AnalyticsUser({"role": "admin"})
        result = UserPermissions.can_manage_metrics(admin_user)
        assert result is True

    def test_can_manage_metrics_non_admin(self):
        """Test non-admin cannot manage metrics"""
        supervisor_user = AnalyticsUser({"role": "supervisor"})
        result = UserPermissions.can_manage_metrics(supervisor_user)
        assert result is False


class TestGetAuthHeaders:
    """Test get_auth_headers function"""

    @patch("apps.analytics.authentication.ServiceAuthentication.create_service_token")
    def test_get_auth_headers(self, mock_create_token):
        """Test getting auth headers"""
        mock_create_token.return_value = "test_service_token"

        headers = get_auth_headers()

        expected_headers = {
            "Authorization": "Bearer test_service_token",
            "Content-Type": "application/json",
        }

        assert headers == expected_headers
        mock_create_token.assert_called_once()
