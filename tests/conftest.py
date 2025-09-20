import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import django
from django.conf import settings
from django.utils import timezone

import pytest

# Configure Django settings before importing anything else
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.test_settings")
    django.setup()

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.analytics.models import AnalyticsCache, MetricDefinition, Report


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def mock_user():
    """Mock user for testing without auth service dependency"""
    user = Mock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.role = "developer"
    user.is_active = True
    return user


@pytest.fixture
def mock_admin_user():
    """Mock admin user for testing"""
    user = Mock()
    user.id = uuid.uuid4()
    user.email = "admin@example.com"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def authenticated_client(api_client, mock_user):
    """Mock authenticated client"""
    with patch("apps.analytics.authentication.verify_jwt_token") as mock_verify:
        mock_verify.return_value = {
            "user_id": str(mock_user.id),
            "email": mock_user.email,
            "role": mock_user.role,
        }
        api_client.defaults["HTTP_AUTHORIZATION"] = "Bearer mock_token"
        return api_client


@pytest.fixture
def admin_authenticated_client(api_client, mock_admin_user):
    """Mock admin authenticated client"""
    with patch("apps.analytics.authentication.verify_jwt_token") as mock_verify:
        mock_verify.return_value = {
            "user_id": str(mock_admin_user.id),
            "email": mock_admin_user.email,
            "role": mock_admin_user.role,
        }
        api_client.defaults["HTTP_AUTHORIZATION"] = "Bearer mock_admin_token"
        return api_client


@pytest.fixture
def metric_definition():
    """Create a test metric definition"""
    return MetricDefinition.objects.create(
        name="Test Productivity Metric",
        description="A test metric for productivity calculation",
        calculation_method="productivity",
        parameters={
            "weight_sessions": 0.4,
            "weight_commits": 0.6,
            "baseline_sessions_per_day": 3,
            "baseline_commits_per_day": 5,
        },
        is_active=True,
    )


@pytest.fixture
def sample_report(mock_user):
    """Create a sample report"""
    return Report.objects.create(
        name="Test Productivity Report",
        type="productivity",
        config={
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "include_weekends": False,
        },
        created_by=mock_user.id,
        status="pending",
    )


@pytest.fixture
def completed_report(mock_user):
    """Create a completed report with data"""
    return Report.objects.create(
        name="Completed Test Report",
        type="productivity",
        config={"start_date": "2024-01-01", "end_date": "2024-01-31"},
        created_by=mock_user.id,
        status="completed",
        generated_at=timezone.now(),
        data={
            "metrics": {
                "productivity_score": 85.5,
                "session_count": 120,
                "commit_count": 45,
                "avg_session_duration": 45.2,
            },
            "summary": {"total_active_days": 22, "avg_productivity_score": 82.3},
        },
    )


@pytest.fixture
def analytics_cache():
    """Create sample analytics cache entry"""
    return AnalyticsCache.objects.create(
        cache_key="test_metric_123",
        cache_type="metric_calculation",
        data={"result": 85.5, "calculation_time": 0.45, "metadata": {"source": "test"}},
        expires_at=timezone.now() + timedelta(hours=1),
    )




@pytest.fixture
def mock_service_clients():
    """Mock external service clients"""
    with (
        patch(
            "apps.analytics.service_integration.MonitoringServiceClient"
        ) as mock_monitoring,
        patch(
            "apps.analytics.service_integration.ManagementServiceClient"
        ) as mock_management,
    ):
        # Mock monitoring service responses
        mock_monitoring_instance = Mock()
        mock_monitoring_instance.get_user_sessions.return_value = {
            "sessions": [
                {
                    "id": "session-1",
                    "user_id": "test-user-id",
                    "start_time": "2024-01-01T09:00:00Z",
                    "end_time": "2024-01-01T10:30:00Z",
                    "duration": 90,
                }
            ]
        }
        mock_monitoring.return_value = mock_monitoring_instance

        # Mock management service responses
        mock_management_instance = Mock()
        mock_management_instance.get_user_projects.return_value = {
            "projects": [
                {
                    "id": "project-1",
                    "name": "Test Project",
                    "commits": 25,
                    "last_activity": "2024-01-01T15:00:00Z",
                }
            ]
        }
        mock_management.return_value = mock_management_instance

        yield {
            "monitoring": mock_monitoring_instance,
            "management": mock_management_instance,
        }


@pytest.fixture
def sample_dashboard_data():
    """Sample dashboard data for testing"""
    return {
        "period": {
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-31T23:59:59Z",
        },
        "metrics": {
            "productivity": {
                "score": 85.5,
                "trend": "increasing",
                "sessions_count": 120,
                "avg_session_duration": 45.2,
            },
            "code_quality": {
                "score": 78.3,
                "complexity_avg": 2.4,
                "test_coverage": 92.1,
            },
            "collaboration": {"score": 88.7, "pr_reviews": 15, "comments": 48},
        },
        "charts": {
            "productivity_trend": [
                {"date": "2024-01-01", "value": 80.0},
                {"date": "2024-01-02", "value": 82.5},
                {"date": "2024-01-03", "value": 85.0},
            ]
        },
        "summary": {
            "total_sessions": 120,
            "total_commits": 45,
            "avg_daily_productivity": 82.3,
        },
    }


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests automatically"""
    pass


@pytest.fixture
def mock_report_export_data():
    """Mock data for report export testing"""
    return {
        "pdf_content": b"Mock PDF content",
        "excel_content": b"Mock Excel content",
        "csv_content": "Metric,Value\nproductivity_score,85.5\nsession_count,120",
        "json_content": '{"metrics": {"productivity_score": 85.5}}',
    }
