"""
Tests for service_integration.py module.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import override_settings

import pytest
import requests

from apps.analytics.service_integration import (
    AuthServiceClient,
    BaseServiceClient,
    ManagementServiceClient,
    MonitoringServiceClient,
    ServiceIntegrationManager,
)


class TestBaseServiceClient:
    """Test BaseServiceClient class."""

    def test_init(self):
        """Test BaseServiceClient initialization."""
        client = BaseServiceClient("http://example.com/", "test_service")

        assert client.service_url == "http://example.com"
        assert client.service_name == "test_service"
        assert client.timeout == 30  # Default timeout
        assert isinstance(client.session, requests.Session)

    def test_init_with_trailing_slash(self):
        """Test BaseServiceClient strips trailing slash."""
        client = BaseServiceClient("http://example.com/", "test_service")

        assert client.service_url == "http://example.com"

    @override_settings(SERVICE_TIMEOUT=60)
    def test_init_with_custom_timeout(self):
        """Test BaseServiceClient with custom timeout from settings."""
        client = BaseServiceClient("http://example.com", "test_service")

        assert client.timeout == 60

    def test_base_url_property(self):
        """Test base_url property."""
        client = BaseServiceClient("http://example.com", "test_service")

        assert client.base_url == "http://example.com"

    @patch("apps.analytics.service_integration.get_auth_headers")
    @patch("apps.analytics.service_integration.cache")
    def test_make_request_get_success(self, mock_cache, mock_auth_headers):
        """Test successful GET request without cache."""
        # Setup mocks
        mock_auth_headers.return_value = {"Authorization": "Bearer token"}
        mock_cache.get.return_value = None  # No cached result

        client = BaseServiceClient("http://example.com", "test_service")

        # Mock the session.get method
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        client.session.get = MagicMock(return_value=mock_response)

        result = client._make_request("GET", "/api/test", params={"key": "value"})

        assert result == {"data": "test"}
        client.session.get.assert_called_once_with(
            "http://example.com/api/test",
            headers={"Authorization": "Bearer token"},
            params={"key": "value"},
            timeout=30,
        )
        mock_cache.set.assert_called_once()

    @patch("apps.analytics.service_integration.get_auth_headers")
    @patch("apps.analytics.service_integration.cache")
    def test_make_request_get_cached(self, mock_cache, mock_auth_headers):
        """Test GET request returns cached result."""
        # Setup cache to return cached result
        cached_data = {"cached": True}
        mock_cache.get.return_value = cached_data

        client = BaseServiceClient("http://example.com", "test_service")
        client.session.get = MagicMock()  # Should not be called

        result = client._make_request("GET", "/api/test")

        assert result == cached_data
        client.session.get.assert_not_called()

    @patch("apps.analytics.service_integration.get_auth_headers")
    def test_make_request_post_success(self, mock_auth_headers):
        """Test successful POST request."""
        mock_auth_headers.return_value = {"Authorization": "Bearer token"}

        client = BaseServiceClient("http://example.com", "test_service")

        # Mock the session.post method
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"created": True}
        client.session.post = MagicMock(return_value=mock_response)

        data = {"name": "test"}
        result = client._make_request("POST", "/api/create", data=data)

        assert result == {"created": True}
        client.session.post.assert_called_once_with(
            "http://example.com/api/create",
            headers={"Authorization": "Bearer token"},
            json=data,
            params=None,
            timeout=30,
        )

    @patch("apps.analytics.service_integration.get_auth_headers")
    def test_make_request_404_response(self, mock_auth_headers):
        """Test handling of 404 response."""
        mock_auth_headers.return_value = {"Authorization": "Bearer token"}

        client = BaseServiceClient("http://example.com", "test_service")

        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        client.session.get = MagicMock(return_value=mock_response)

        with pytest.raises(requests.RequestException, match="404 Not Found"):
            client._make_request("GET", "/api/notfound")

    @patch("apps.analytics.service_integration.get_auth_headers")
    @patch("apps.analytics.service_integration.logger")
    def test_make_request_500_response(self, mock_logger, mock_auth_headers):
        """Test handling of 500 response."""
        mock_auth_headers.return_value = {"Authorization": "Bearer token"}

        client = BaseServiceClient("http://example.com", "test_service")

        # Mock 500 response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        client.session.get = MagicMock(return_value=mock_response)

        with pytest.raises(requests.RequestException, match="500 Error"):
            client._make_request("GET", "/api/error")

        mock_logger.error.assert_called_once()

    @patch("apps.analytics.service_integration.get_auth_headers")
    @patch("apps.analytics.service_integration.logger")
    def test_make_request_connection_error(self, mock_logger, mock_auth_headers):
        """Test handling of connection error."""
        mock_auth_headers.return_value = {"Authorization": "Bearer token"}

        client = BaseServiceClient("http://example.com", "test_service")

        # Mock connection error
        client.session.get = MagicMock(
            side_effect=requests.ConnectionError("Connection failed")
        )

        with pytest.raises(requests.RequestException, match="Connection error"):
            client._make_request("GET", "/api/test")

        mock_logger.error.assert_called_once()

    @patch("apps.analytics.service_integration.get_auth_headers")
    def test_make_request_timeout_error(self, mock_auth_headers):
        """Test handling of timeout error."""
        mock_auth_headers.return_value = {"Authorization": "Bearer token"}

        client = BaseServiceClient("http://example.com", "test_service")

        # Mock timeout error
        client.session.get = MagicMock(
            side_effect=requests.Timeout("Request timed out")
        )

        with pytest.raises(requests.RequestException, match="Timeout"):
            client._make_request("GET", "/api/test")

    @patch("apps.analytics.service_integration.get_auth_headers")
    def test_make_request_no_cache(self, mock_auth_headers):
        """Test GET request without caching."""
        mock_auth_headers.return_value = {"Authorization": "Bearer token"}

        client = BaseServiceClient("http://example.com", "test_service")

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        client.session.get = MagicMock(return_value=mock_response)

        with patch("apps.analytics.service_integration.cache") as mock_cache:
            result = client._make_request("GET", "/api/test", use_cache=False)

            assert result == {"data": "test"}
            mock_cache.get.assert_not_called()
            mock_cache.set.assert_not_called()


@pytest.mark.django_db
class TestMonitoringServiceClient:
    """Test MonitoringServiceClient class."""

    @override_settings(MONITORING_SERVICE_URL="http://monitoring.test")
    def test_init(self):
        """Test MonitoringServiceClient initialization."""
        client = MonitoringServiceClient()

        assert client.service_url == "http://monitoring.test"
        assert client.service_name == "monitoring"

    @override_settings(MONITORING_SERVICE_URL="http://monitoring.test")
    @patch.object(MonitoringServiceClient, "_make_request")
    def test_get_user_sessions(self, mock_make_request):
        """Test get_user_sessions method."""
        mock_make_request.return_value = {
            "sessions": [
                {"session_id": "123", "duration": 120},
                {"session_id": "456", "duration": 90},
            ]
        }

        client = MonitoringServiceClient()
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)

        result = client.get_user_sessions(123, start_date, end_date)

        assert "sessions" in result
        assert len(result["sessions"]) == 2
        mock_make_request.assert_called_once_with(
            "GET",
            "/api/sessions/",
            params={
                "user_id": 123,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

    @override_settings(MONITORING_SERVICE_URL="http://monitoring.test")
    @patch.object(MonitoringServiceClient, "_make_request")
    def test_get_user_sessions_none_response(self, mock_make_request):
        """Test get_user_sessions with None response."""
        mock_make_request.return_value = None

        client = MonitoringServiceClient()
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)

        result = client.get_user_sessions(123, start_date, end_date)

        assert result == {"sessions": []}

    @override_settings(MONITORING_SERVICE_URL="http://monitoring.test")
    @patch.object(MonitoringServiceClient, "_make_request")
    def test_get_team_git_activity(self, mock_make_request):
        """Test get_team_git_activity method."""
        mock_make_request.return_value = [
            {"commit_id": "abc123", "lines_added": 50},
            {"commit_id": "def456", "lines_added": 30},
        ]

        client = MonitoringServiceClient()
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)

        result = client.get_team_git_activity("456", start_date, end_date)

        assert len(result) == 2
        mock_make_request.assert_called_once()

    @override_settings(MONITORING_SERVICE_URL="http://monitoring.test")
    def test_check_health(self):
        """Test check_health method."""
        client = MonitoringServiceClient()

        # Mock successful health check
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        client.session.get = MagicMock(return_value=mock_response)

        result = client.check_health()

        assert result == {"status": "healthy"}

    @override_settings(MONITORING_SERVICE_URL="http://monitoring.test")
    def test_check_health_failure(self):
        """Test check_health method with service failure."""
        client = MonitoringServiceClient()

        # Mock failed health check
        client.session.get = MagicMock(side_effect=requests.ConnectionError())

        result = client.check_health()

        assert result is None


@pytest.mark.django_db
class TestManagementServiceClient:
    """Test ManagementServiceClient class."""

    @override_settings(MANAGEMENT_SERVICE_URL="http://management.test")
    def test_init(self):
        """Test ManagementServiceClient initialization."""
        client = ManagementServiceClient()

        assert client.service_url == "http://management.test"
        assert client.service_name == "management"

    @override_settings(MANAGEMENT_SERVICE_URL="http://management.test")
    @patch.object(ManagementServiceClient, "_make_request")
    def test_get_team_members(self, mock_make_request):
        """Test get_team_members method."""
        mock_make_request.return_value = [
            {"user_id": 1, "role": "developer"},
            {"user_id": 2, "role": "manager"},
        ]

        client = ManagementServiceClient()

        result = client.get_team_members(123)

        assert len(result) == 2
        mock_make_request.assert_called_once_with("GET", "/api/teams/123/members")

    @override_settings(MANAGEMENT_SERVICE_URL="http://management.test")
    @patch.object(ManagementServiceClient, "_make_request")
    def test_get_user_projects(self, mock_make_request):
        """Test get_user_projects method."""
        mock_make_request.return_value = [
            {"project_id": 1, "name": "Project A"},
            {"project_id": 2, "name": "Project B"},
        ]

        client = ManagementServiceClient()

        result = client.get_user_projects(456)

        assert len(result) == 2
        mock_make_request.assert_called_once_with("GET", "/api/users/456/projects")

    @override_settings(MANAGEMENT_SERVICE_URL="http://management.test")
    @patch.object(ManagementServiceClient, "_make_request")
    def test_get_project_details(self, mock_make_request):
        """Test get_project_details method."""
        mock_make_request.return_value = {
            "project_id": 789,
            "name": "Test Project",
            "status": "active",
        }

        client = ManagementServiceClient()

        result = client.get_project_details(789)

        assert result["name"] == "Test Project"
        mock_make_request.assert_called_once_with("GET", "/api/projects/789")


@pytest.mark.django_db
class TestAuthServiceClient:
    """Test AuthServiceClient class."""

    @override_settings(AUTH_SERVICE_URL="http://auth.test")
    def test_init(self):
        """Test AuthServiceClient initialization."""
        client = AuthServiceClient()

        assert client.service_url == "http://auth.test"
        assert client.service_name == "auth"

    @override_settings(AUTH_SERVICE_URL="http://auth.test")
    @patch.object(AuthServiceClient, "_make_request")
    def test_get_user_profile(self, mock_make_request):
        """Test get_user_profile method."""
        mock_make_request.return_value = {
            "user_id": 123,
            "username": "testuser",
            "email": "test@example.com",
        }

        client = AuthServiceClient()

        result = client.get_user_profile(123)

        assert result["username"] == "testuser"
        mock_make_request.assert_called_once_with("GET", "/api/users/123/profile")

    @override_settings(AUTH_SERVICE_URL="http://auth.test")
    @patch.object(AuthServiceClient, "_make_request")
    def test_validate_token(self, mock_make_request):
        """Test validate_token method."""
        mock_make_request.return_value = {"valid": True, "user_id": 123}

        client = AuthServiceClient()

        result = client.validate_token("test_token")

        assert result["valid"] is True
        mock_make_request.assert_called_once_with(
            "POST", "/api/auth/validate", data={"token": "test_token"}
        )

    @override_settings(AUTH_SERVICE_URL="http://auth.test")
    @patch.object(AuthServiceClient, "_make_request")
    def test_get_user_permissions(self, mock_make_request):
        """Test get_user_permissions method."""
        mock_make_request.return_value = ["read_analytics", "write_reports"]

        client = AuthServiceClient()

        result = client.get_user_permissions(123)

        assert "read_analytics" in result
        mock_make_request.assert_called_once_with("GET", "/api/users/123/permissions")


@pytest.mark.django_db
class TestServiceIntegrationManager:
    """Test ServiceIntegrationManager class."""

    def test_init(self):
        """Test ServiceIntegrationManager initialization."""
        manager = ServiceIntegrationManager()

        assert hasattr(manager, "monitoring")
        assert hasattr(manager, "management")
        assert hasattr(manager, "auth")
        assert isinstance(manager.monitoring, MonitoringServiceClient)
        assert isinstance(manager.management, ManagementServiceClient)
        assert isinstance(manager.auth, AuthServiceClient)

    @patch.object(MonitoringServiceClient, "check_health")
    @patch.object(ManagementServiceClient, "check_health")
    @patch.object(AuthServiceClient, "check_health")
    def test_check_all_services_healthy(
        self, mock_auth_health, mock_mgmt_health, mock_mon_health
    ):
        """Test check_all_services when all are healthy."""
        mock_mon_health.return_value = {"status": "healthy"}
        mock_mgmt_health.return_value = {"status": "healthy"}
        mock_auth_health.return_value = {"status": "healthy"}

        manager = ServiceIntegrationManager()
        result = manager.check_all_services()

        assert result["monitoring"]["status"] == "healthy"
        assert result["management"]["status"] == "healthy"
        assert result["auth"]["status"] == "healthy"
        assert result["overall_status"] == "healthy"

    @patch.object(MonitoringServiceClient, "check_health")
    @patch.object(ManagementServiceClient, "check_health")
    @patch.object(AuthServiceClient, "check_health")
    def test_check_all_services_partial_failure(
        self, mock_auth_health, mock_mgmt_health, mock_mon_health
    ):
        """Test check_all_services with partial service failure."""
        mock_mon_health.return_value = {"status": "healthy"}
        mock_mgmt_health.return_value = None  # Service down
        mock_auth_health.return_value = {"status": "healthy"}

        manager = ServiceIntegrationManager()
        result = manager.check_all_services()

        assert result["monitoring"]["status"] == "healthy"
        assert result["management"]["status"] == "unhealthy"
        assert result["auth"]["status"] == "healthy"
        assert result["overall_status"] == "degraded"

    @patch.object(MonitoringServiceClient, "check_health")
    @patch.object(ManagementServiceClient, "check_health")
    @patch.object(AuthServiceClient, "check_health")
    def test_check_all_services_all_down(
        self, mock_auth_health, mock_mgmt_health, mock_mon_health
    ):
        """Test check_all_services when all services are down."""
        mock_mon_health.return_value = None
        mock_mgmt_health.return_value = None
        mock_auth_health.return_value = None

        manager = ServiceIntegrationManager()
        result = manager.check_all_services()

        assert result["monitoring"]["status"] == "unhealthy"
        assert result["management"]["status"] == "unhealthy"
        assert result["auth"]["status"] == "unhealthy"
        assert result["overall_status"] == "unhealthy"

    @patch.object(MonitoringServiceClient, "get_user_sessions")
    @patch.object(AuthServiceClient, "get_user_profile")
    def test_get_comprehensive_user_data(self, mock_get_profile, mock_get_sessions):
        """Test get_comprehensive_user_data method."""
        mock_get_profile.return_value = {"user_id": 123, "username": "testuser"}
        mock_get_sessions.return_value = [{"session_id": "abc", "duration": 120}]

        manager = ServiceIntegrationManager()
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)

        result = manager.get_comprehensive_user_data(123, start_date, end_date)

        assert "profile" in result
        assert "sessions" in result
        assert result["profile"]["username"] == "testuser"
        assert len(result["sessions"]) == 1

    @patch.object(MonitoringServiceClient, "get_team_sessions")
    @patch.object(ManagementServiceClient, "get_team_members")
    def test_get_comprehensive_team_data(self, mock_get_members, mock_get_sessions):
        """Test get_comprehensive_team_data method."""
        mock_get_members.return_value = [
            {"user_id": 1, "role": "developer"},
            {"user_id": 2, "role": "manager"},
        ]
        mock_get_sessions.return_value = [{"team_id": 456, "total_hours": 40}]

        manager = ServiceIntegrationManager()
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)

        result = manager.get_comprehensive_team_data(456, start_date, end_date)

        assert "members" in result
        assert "sessions" in result
        assert len(result["members"]) == 2
        assert len(result["sessions"]) == 1


@pytest.mark.django_db
class TestIntegrationScenarios:
    """Integration tests for service clients."""

    @override_settings(
        MONITORING_SERVICE_URL="http://monitoring.test",
        MANAGEMENT_SERVICE_URL="http://management.test",
        AUTH_SERVICE_URL="http://auth.test",
    )
    def test_service_integration_manager_initialization(self):
        """Test that ServiceIntegrationManager properly initializes all clients."""
        manager = ServiceIntegrationManager()

        assert manager.monitoring.service_url == "http://monitoring.test"
        assert manager.management.service_url == "http://management.test"
        assert manager.auth.service_url == "http://auth.test"

    @patch("apps.analytics.service_integration.get_auth_headers")
    def test_cross_service_data_flow(self, mock_auth_headers):
        """Test data flow across multiple services."""
        mock_auth_headers.return_value = {"Authorization": "Bearer token"}

        # Create manager and mock service responses
        manager = ServiceIntegrationManager()

        # Mock auth service response
        auth_response = MagicMock()
        auth_response.status_code = 200
        auth_response.json.return_value = {"user_id": 123, "username": "testuser"}
        manager.auth.session.get = MagicMock(return_value=auth_response)

        # Mock monitoring service response
        monitoring_response = MagicMock()
        monitoring_response.status_code = 200
        monitoring_response.json.return_value = [{"session_id": "abc", "duration": 120}]
        manager.monitoring.session.get = MagicMock(return_value=monitoring_response)

        # Get user profile and sessions
        user_profile = manager.auth.get_user_profile(123)
        user_sessions = manager.monitoring.get_user_sessions(
            123, datetime.now(), datetime.now()
        )

        assert user_profile["username"] == "testuser"
        assert len(user_sessions) == 1
        assert user_sessions[0]["duration"] == 120

    @patch("apps.analytics.service_integration.cache")
    def test_caching_behavior_across_requests(self, mock_cache):
        """Test that caching works properly across multiple requests."""
        # Setup cache behavior
        mock_cache.get.side_effect = [None, {"cached": True}]  # First miss, then hit

        client = BaseServiceClient("http://example.com", "test")

        # Mock successful response for first request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "fresh"}
        client.session.get = MagicMock(return_value=mock_response)

        # First request - should hit the service
        result1 = client._make_request("GET", "/api/test")
        assert result1 == {"data": "fresh"}

        # Second request - should return cached result
        result2 = client._make_request("GET", "/api/test")
        assert result2 == {"cached": True}

        # Verify cache.set was called for first request
        mock_cache.set.assert_called_once()
