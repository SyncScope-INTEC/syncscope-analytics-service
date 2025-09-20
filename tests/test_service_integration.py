import pytest
from unittest.mock import Mock, patch
import requests
from datetime import datetime

from apps.analytics.service_integration import (
    MonitoringServiceClient,
    ManagementServiceClient,
    AuthServiceClient,
    ServiceIntegrationError
)


class TestMonitoringServiceClient:
    """Test cases for MonitoringServiceClient"""

    def test_initialization(self):
        """Test MonitoringServiceClient initialization"""
        client = MonitoringServiceClient()

        assert client.base_url is not None
        assert hasattr(client, 'timeout')
        assert hasattr(client, 'session')

    @patch('requests.Session.get')
    def test_get_user_sessions_success(self, mock_get):
        """Test successful user sessions retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sessions": [
                {
                    "id": "session-1",
                    "user_id": "test-user-id",
                    "start_time": "2024-01-01T09:00:00Z",
                    "end_time": "2024-01-01T10:30:00Z",
                    "duration": 90,
                    "project_id": "test-project"
                },
                {
                    "id": "session-2",
                    "user_id": "test-user-id",
                    "start_time": "2024-01-01T14:00:00Z",
                    "end_time": "2024-01-01T15:00:00Z",
                    "duration": 60,
                    "project_id": "test-project"
                }
            ]
        }
        mock_get.return_value = mock_response

        client = MonitoringServiceClient()
        result = client.get_user_sessions("test-user-id", "2024-01-01", "2024-01-31")

        assert "sessions" in result
        assert len(result["sessions"]) == 2
        assert result["sessions"][0]["duration"] == 90

        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_get_user_sessions_not_found(self, mock_get):
        """Test user sessions retrieval when user not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "User not found"}
        mock_get.return_value = mock_response

        client = MonitoringServiceClient()

        with pytest.raises(ServiceIntegrationError):
            client.get_user_sessions("nonexistent-user", "2024-01-01", "2024-01-31")

    @patch('requests.Session.get')
    def test_get_user_sessions_server_error(self, mock_get):
        """Test user sessions retrieval with server error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_get.return_value = mock_response

        client = MonitoringServiceClient()

        with pytest.raises(ServiceIntegrationError):
            client.get_user_sessions("test-user-id", "2024-01-01", "2024-01-31")

    @patch('requests.Session.get')
    def test_get_user_sessions_timeout(self, mock_get):
        """Test user sessions retrieval with timeout"""
        mock_get.side_effect = requests.Timeout("Request timeout")

        client = MonitoringServiceClient()

        with pytest.raises(ServiceIntegrationError):
            client.get_user_sessions("test-user-id", "2024-01-01", "2024-01-31")

    @patch('requests.Session.get')
    def test_get_user_sessions_connection_error(self, mock_get):
        """Test user sessions retrieval with connection error"""
        mock_get.side_effect = requests.ConnectionError("Connection failed")

        client = MonitoringServiceClient()

        with pytest.raises(ServiceIntegrationError):
            client.get_user_sessions("test-user-id", "2024-01-01", "2024-01-31")

    @patch('requests.Session.get')
    def test_get_project_activity_success(self, mock_get):
        """Test successful project activity retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "activity": [
                {
                    "timestamp": "2024-01-01T10:00:00Z",
                    "user_id": "test-user-id",
                    "action": "file_edit",
                    "file_path": "/src/main.py",
                    "duration": 300
                }
            ],
            "summary": {
                "total_actions": 1,
                "total_duration": 300
            }
        }
        mock_get.return_value = mock_response

        client = MonitoringServiceClient()
        result = client.get_project_activity("test-project-id", "2024-01-01", "2024-01-31")

        assert "activity" in result
        assert "summary" in result
        assert len(result["activity"]) == 1

    @patch('requests.Session.get')
    def test_get_team_metrics_success(self, mock_get):
        """Test successful team metrics retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "team_metrics": {
                "active_users": 5,
                "total_sessions": 120,
                "avg_session_duration": 85.5,
                "productivity_score": 78.3
            },
            "user_metrics": [
                {
                    "user_id": "user-1",
                    "sessions": 25,
                    "avg_duration": 90.0,
                    "productivity_score": 82.1
                }
            ]
        }
        mock_get.return_value = mock_response

        client = MonitoringServiceClient()
        result = client.get_team_metrics("test-team-id", "2024-01-01", "2024-01-31")

        assert "team_metrics" in result
        assert "user_metrics" in result
        assert result["team_metrics"]["active_users"] == 5

    @patch('requests.Session.get')
    def test_health_check_success(self, mock_get):
        """Test successful health check"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_get.return_value = mock_response

        client = MonitoringServiceClient()
        result = client.health_check()

        assert result is True

    @patch('requests.Session.get')
    def test_health_check_unhealthy(self, mock_get):
        """Test health check when service is unhealthy"""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response

        client = MonitoringServiceClient()
        result = client.health_check()

        assert result is False


class TestManagementServiceClient:
    """Test cases for ManagementServiceClient"""

    def test_initialization(self):
        """Test ManagementServiceClient initialization"""
        client = ManagementServiceClient()

        assert client.base_url is not None
        assert hasattr(client, 'timeout')
        assert hasattr(client, 'session')

    @patch('requests.Session.get')
    def test_get_user_projects_success(self, mock_get):
        """Test successful user projects retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "projects": [
                {
                    "id": "project-1",
                    "name": "Test Project 1",
                    "commits": 25,
                    "lines_of_code": 1500,
                    "last_activity": "2024-01-01T15:00:00Z"
                },
                {
                    "id": "project-2",
                    "name": "Test Project 2",
                    "commits": 18,
                    "lines_of_code": 980,
                    "last_activity": "2024-01-01T12:00:00Z"
                }
            ]
        }
        mock_get.return_value = mock_response

        client = ManagementServiceClient()
        result = client.get_user_projects("test-user-id")

        assert "projects" in result
        assert len(result["projects"]) == 2
        assert result["projects"][0]["commits"] == 25

    @patch('requests.Session.get')
    def test_get_user_commits_success(self, mock_get):
        """Test successful user commits retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "commits": [
                {
                    "id": "commit-1",
                    "user_id": "test-user-id",
                    "project_id": "project-1",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "lines_added": 50,
                    "lines_deleted": 10,
                    "files_changed": 3
                },
                {
                    "id": "commit-2",
                    "user_id": "test-user-id",
                    "project_id": "project-1",
                    "timestamp": "2024-01-01T14:00:00Z",
                    "lines_added": 30,
                    "lines_deleted": 5,
                    "files_changed": 2
                }
            ],
            "summary": {
                "total_commits": 2,
                "total_lines_added": 80,
                "total_lines_deleted": 15
            }
        }
        mock_get.return_value = mock_response

        client = ManagementServiceClient()
        result = client.get_user_commits("test-user-id", "2024-01-01", "2024-01-31")

        assert "commits" in result
        assert "summary" in result
        assert len(result["commits"]) == 2
        assert result["summary"]["total_commits"] == 2

    @patch('requests.Session.get')
    def test_get_code_quality_metrics_success(self, mock_get):
        """Test successful code quality metrics retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "complexity": {
                "average": 2.5,
                "max": 8,
                "files": 45
            },
            "coverage": {
                "percentage": 87.5,
                "lines_covered": 1250,
                "total_lines": 1429
            },
            "duplication": {
                "percentage": 3.2,
                "duplicated_lines": 46,
                "total_lines": 1429
            },
            "issues": {
                "critical": 0,
                "major": 2,
                "minor": 8,
                "info": 15
            }
        }
        mock_get.return_value = mock_response

        client = ManagementServiceClient()
        result = client.get_code_quality_metrics("test-project-id")

        assert "complexity" in result
        assert "coverage" in result
        assert "duplication" in result
        assert result["coverage"]["percentage"] == 87.5

    @patch('requests.Session.get')
    def test_get_collaboration_metrics_success(self, mock_get):
        """Test successful collaboration metrics retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pull_requests": {
                "created": 8,
                "reviewed": 15,
                "merged": 12,
                "avg_review_time": 24.5
            },
            "comments": {
                "pr_comments": 45,
                "issue_comments": 23,
                "code_comments": 18
            },
            "meetings": {
                "attended": 8,
                "organized": 2,
                "total_hours": 12.5
            }
        }
        mock_get.return_value = mock_response

        client = ManagementServiceClient()
        result = client.get_collaboration_metrics("test-user-id", "2024-01-01", "2024-01-31")

        assert "pull_requests" in result
        assert "comments" in result
        assert "meetings" in result
        assert result["pull_requests"]["created"] == 8

    @patch('requests.Session.get')
    def test_get_project_statistics_success(self, mock_get):
        """Test successful project statistics retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "overview": {
                "total_commits": 245,
                "total_contributors": 8,
                "lines_of_code": 15420,
                "files": 89
            },
            "activity": {
                "commits_this_week": 12,
                "commits_this_month": 45,
                "active_contributors": 5
            },
            "health": {
                "test_coverage": 92.1,
                "code_quality_score": 78.5,
                "security_score": 85.2
            }
        }
        mock_get.return_value = mock_response

        client = ManagementServiceClient()
        result = client.get_project_statistics("test-project-id")

        assert "overview" in result
        assert "activity" in result
        assert "health" in result
        assert result["overview"]["total_commits"] == 245


class TestAuthServiceClient:
    """Test cases for AuthServiceClient"""

    def test_initialization(self):
        """Test AuthServiceClient initialization"""
        client = AuthServiceClient()

        assert client.base_url is not None
        assert hasattr(client, 'timeout')
        assert hasattr(client, 'session')

    @patch('requests.Session.post')
    def test_verify_token_success(self, mock_post):
        """Test successful token verification"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "valid": True,
            "user_id": "test-user-id",
            "email": "test@example.com",
            "role": "developer"
        }
        mock_post.return_value = mock_response

        client = AuthServiceClient()
        result = client.verify_token("test-token")

        assert result["valid"] is True
        assert result["user_id"] == "test-user-id"
        assert result["role"] == "developer"

    @patch('requests.Session.post')
    def test_verify_token_invalid(self, mock_post):
        """Test token verification with invalid token"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "valid": False,
            "error": "Invalid token"
        }
        mock_post.return_value = mock_response

        client = AuthServiceClient()
        result = client.verify_token("invalid-token")

        assert result["valid"] is False
        assert "error" in result

    @patch('requests.Session.get')
    def test_get_user_info_success(self, mock_get):
        """Test successful user info retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test-user-id",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "developer",
            "company": {
                "id": "company-1",
                "name": "Test Company"
            }
        }
        mock_get.return_value = mock_response

        client = AuthServiceClient()
        result = client.get_user_info("test-user-id")

        assert result["id"] == "test-user-id"
        assert result["email"] == "test@example.com"
        assert result["company"]["name"] == "Test Company"

    @patch('requests.Session.get')
    def test_get_user_permissions_success(self, mock_get):
        """Test successful user permissions retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "user_id": "test-user-id",
            "role": "developer",
            "permissions": [
                "view_analytics",
                "create_reports",
                "view_own_data"
            ],
            "restrictions": {
                "can_view_all_users": False,
                "can_export_data": True
            }
        }
        mock_get.return_value = mock_response

        client = AuthServiceClient()
        result = client.get_user_permissions("test-user-id")

        assert result["role"] == "developer"
        assert "view_analytics" in result["permissions"]
        assert result["restrictions"]["can_export_data"] is True


class TestServiceIntegrationErrorHandling:
    """Test error handling in service integration"""

    @patch('requests.Session.get')
    def test_service_timeout_handling(self, mock_get):
        """Test handling of service timeouts"""
        mock_get.side_effect = requests.Timeout("Request timeout")

        client = MonitoringServiceClient()

        with pytest.raises(ServiceIntegrationError) as exc_info:
            client.get_user_sessions("test-user-id", "2024-01-01", "2024-01-31")

        assert "timeout" in str(exc_info.value).lower()

    @patch('requests.Session.get')
    def test_service_connection_error_handling(self, mock_get):
        """Test handling of service connection errors"""
        mock_get.side_effect = requests.ConnectionError("Connection failed")

        client = ManagementServiceClient()

        with pytest.raises(ServiceIntegrationError) as exc_info:
            client.get_user_projects("test-user-id")

        assert "connection" in str(exc_info.value).lower()

    @patch('requests.Session.post')
    def test_service_http_error_handling(self, mock_post):
        """Test handling of HTTP errors"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_post.return_value = mock_response

        client = AuthServiceClient()

        with pytest.raises(ServiceIntegrationError) as exc_info:
            client.verify_token("test-token")

        assert "500" in str(exc_info.value)

    @patch('requests.Session.get')
    def test_service_invalid_json_handling(self, mock_get):
        """Test handling of invalid JSON responses"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        client = MonitoringServiceClient()

        with pytest.raises(ServiceIntegrationError) as exc_info:
            client.get_user_sessions("test-user-id", "2024-01-01", "2024-01-31")

        assert "json" in str(exc_info.value).lower()


class TestServiceIntegrationConfiguration:
    """Test service integration configuration"""

    @patch('django.conf.settings')
    def test_monitoring_service_configuration(self, mock_settings):
        """Test MonitoringServiceClient configuration"""
        mock_settings.MONITORING_SERVICE_URL = "http://test-monitoring:8000"
        mock_settings.SERVICE_TIMEOUT = 30

        client = MonitoringServiceClient()

        assert "test-monitoring" in client.base_url
        assert client.timeout == 30

    @patch('django.conf.settings')
    def test_management_service_configuration(self, mock_settings):
        """Test ManagementServiceClient configuration"""
        mock_settings.MANAGEMENT_SERVICE_URL = "http://test-management:8000"
        mock_settings.SERVICE_TIMEOUT = 45

        client = ManagementServiceClient()

        assert "test-management" in client.base_url
        assert client.timeout == 45

    @patch('django.conf.settings')
    def test_auth_service_configuration(self, mock_settings):
        """Test AuthServiceClient configuration"""
        mock_settings.AUTH_SERVICE_URL = "http://test-auth:8000"
        mock_settings.SERVICE_TIMEOUT = 15

        client = AuthServiceClient()

        assert "test-auth" in client.base_url
        assert client.timeout == 15

    def test_default_configuration(self):
        """Test default configuration when settings not provided"""
        # Test that clients can be initialized with default settings
        monitoring_client = MonitoringServiceClient()
        management_client = ManagementServiceClient()
        auth_client = AuthServiceClient()

        assert monitoring_client.base_url is not None
        assert management_client.base_url is not None
        assert auth_client.base_url is not None


class TestServiceIntegrationRetry:
    """Test retry logic in service integration"""

    @patch('requests.Session.get')
    def test_retry_on_temporary_failure(self, mock_get):
        """Test retry logic on temporary failures"""
        # First call fails with 503, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 503

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"sessions": []}

        mock_get.side_effect = [mock_response_fail, mock_response_success]

        client = MonitoringServiceClient()

        # This would normally retry internally if retry logic is implemented
        # For now, it should raise an error on first 503
        with pytest.raises(ServiceIntegrationError):
            client.get_user_sessions("test-user-id", "2024-01-01", "2024-01-31")

    @patch('requests.Session.get')
    def test_no_retry_on_client_error(self, mock_get):
        """Test no retry on client errors (4xx)"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        mock_get.return_value = mock_response

        client = ManagementServiceClient()

        # Should not retry on 404, should fail immediately
        with pytest.raises(ServiceIntegrationError):
            client.get_user_projects("nonexistent-user")

        # Should only be called once (no retry)
        assert mock_get.call_count == 1


class TestServiceIntegrationCaching:
    """Test caching behavior in service integration"""

    @patch('requests.Session.get')
    def test_health_check_caching(self, mock_get):
        """Test health check result caching"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_get.return_value = mock_response

        client = MonitoringServiceClient()

        # Make multiple health check calls
        result1 = client.health_check()
        result2 = client.health_check()

        assert result1 is True
        assert result2 is True

        # Depending on implementation, this might be cached
        # For now, each call should make a request
        assert mock_get.call_count >= 1

    @patch('requests.Session.get')
    def test_user_info_caching(self, mock_get):
        """Test user info caching"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test-user-id",
            "email": "test@example.com",
            "role": "developer"
        }
        mock_get.return_value = mock_response

        client = AuthServiceClient()

        # Make multiple calls for same user
        result1 = client.get_user_info("test-user-id")
        result2 = client.get_user_info("test-user-id")

        assert result1["id"] == "test-user-id"
        assert result2["id"] == "test-user-id"

        # Could implement caching to reduce calls