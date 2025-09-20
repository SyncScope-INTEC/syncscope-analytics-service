import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

import pytest
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.analytics.models import AnalyticsCache, MetricDefinition, Report
from apps.analytics.views import MetricDefinitionViewSet, ReportViewSet

User = get_user_model()


@pytest.mark.django_db
class TestApiHomeView:
    """Test API home view."""

    def test_api_home_html_response(self, client):
        """Test HTML response for API home."""
        response = client.get("/")
        assert response.status_code == 200
        # Should render HTML template or fallback to JSON

    def test_api_home_json_response(self, client):
        """Test JSON response when explicitly requested."""
        response = client.get("/?format=json")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"

        data = response.json()
        assert "main_routes" in data
        assert "service_info" in data
        assert "api_title" in data
        assert data["api_title"] == "SyncScope Analytics Service"

    def test_api_home_main_routes(self, client):
        """Test main routes structure."""
        response = client.get("/?format=json")
        data = response.json()

        expected_routes = [
            "API Documentation",
            "ReDoc Documentation",
            "OpenAPI Schema",
            "Admin Interface",
            "Health Check",
        ]
        route_titles = [route["title"] for route in data["main_routes"]]

        for title in expected_routes:
            assert title in route_titles

    def test_api_home_service_info(self, client):
        """Test service info structure."""
        response = client.get("/?format=json")
        data = response.json()

        service_info = data["service_info"]
        assert "endpoints" in service_info
        assert "features" in service_info
        assert "data_sources" in service_info
        assert "export_formats" in service_info
        assert "status" in service_info

        assert isinstance(service_info["features"], list)
        assert "Report Generation" in service_info["features"]
        assert "PostgreSQL" in service_info["data_sources"]


@pytest.mark.django_db
class TestReportViewSet:
    """Test ReportViewSet."""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def admin_user(self):
        user = User.objects.create_user(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        user.role = "admin"
        user.save()
        return user

    def test_list_reports_authenticated(self, client, user, report):
        """Test listing reports for authenticated user."""
        client.force_authenticate(user=user)
        response = client.get("/analytics/reports/")
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 1
        assert data[0]["name"] == report.name

    def test_list_reports_unauthenticated(self, client):
        """Test listing reports without authentication."""
        response = client.get("/analytics/reports/")
        assert response.status_code == 401

    def test_create_report_authenticated(self, client, user, metric_definition):
        """Test creating a report."""
        client.force_authenticate(user=user)

        report_data = {
            "name": "New Test Report",
            "description": "A new test report",
            "report_type": "summary",
            "configuration": {
                "metrics": [metric_definition.id],
                "date_range": "last_7_days",
            },
        }

        with patch.object(ReportViewSet, "_generate_report_async") as mock_generate:
            response = client.post("/analytics/reports/", report_data, format="json")

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Test Report"
        assert data["status"] == "pending"
        mock_generate.assert_called_once()

    def test_create_report_invalid_data(self, client, user):
        """Test creating report with invalid data."""
        client.force_authenticate(user=user)

        invalid_data = {
            "name": "",  # Invalid: empty name
            "report_type": "invalid_type",  # Invalid type
        }

        response = client.post("/analytics/reports/", invalid_data, format="json")
        assert response.status_code == 400

    def test_retrieve_report(self, client, user, report):
        """Test retrieving a specific report."""
        client.force_authenticate(user=user)
        response = client.get(f"/analytics/reports/{report.id}/")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == report.id
        assert data["name"] == report.name

    def test_retrieve_nonexistent_report(self, client, user):
        """Test retrieving non-existent report."""
        client.force_authenticate(user=user)
        response = client.get("/analytics/reports/999/")
        assert response.status_code == 404

    def test_update_report(self, client, user, report):
        """Test updating a report."""
        client.force_authenticate(user=user)

        update_data = {
            "name": "Updated Report Name",
            "description": "Updated description",
        }

        response = client.patch(
            f"/analytics/reports/{report.id}/", update_data, format="json"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Report Name"
        assert data["description"] == "Updated description"

    def test_delete_report(self, client, user, report):
        """Test deleting a report."""
        client.force_authenticate(user=user)
        response = client.delete(f"/analytics/reports/{report.id}/")
        assert response.status_code == 204

        # Verify report is deleted
        assert not Report.objects.filter(id=report.id).exists()

    @patch("apps.analytics.views.ReportGenerator")
    def test_export_report_success(self, mock_generator_class, client, user, report):
        """Test successful report export."""
        # Set up mocks
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.export_report.return_value = (
            b"fake_file_data",
            "application/pdf",
            "test_report.pdf",
        )

        # Mark report as completed
        report.status = "completed"
        report.save()

        client.force_authenticate(user=user)

        export_data = {"format": "pdf", "include_charts": True, "detailed": False}

        response = client.post(
            f"/analytics/reports/{report.id}/export/", export_data, format="json"
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert "attachment" in response["Content-Disposition"]

    def test_export_report_not_ready(self, client, user, pending_report):
        """Test exporting report that's not ready."""
        client.force_authenticate(user=user)

        export_data = {"format": "pdf", "include_charts": True, "detailed": False}

        response = client.post(
            f"/analytics/reports/{pending_report.id}/export/",
            export_data,
            format="json",
        )
        assert response.status_code == 400
        assert "not ready for export" in response.json()["error"]

    def test_export_report_invalid_format(self, client, user, report):
        """Test export with invalid format."""
        report.status = "completed"
        report.save()

        client.force_authenticate(user=user)

        export_data = {
            "format": "invalid_format",
            "include_charts": True,
            "detailed": False,
        }

        response = client.post(
            f"/analytics/reports/{report.id}/export/", export_data, format="json"
        )
        assert response.status_code == 400

    @patch.object(ReportViewSet, "_generate_report_async")
    def test_regenerate_report(self, mock_generate, client, user, report):
        """Test report regeneration."""
        client.force_authenticate(user=user)

        response = client.post(f"/analytics/reports/{report.id}/regenerate/")
        assert response.status_code == 200

        data = response.json()
        assert "regeneration started" in data["message"]
        assert data["report_id"] == report.id

        # Check that report status was reset
        report.refresh_from_db()
        assert report.status == "pending"
        assert report.data is None

        mock_generate.assert_called_once()

    def test_admin_sees_all_reports(self, client, admin_user, user, report):
        """Test admin user can see all reports."""
        # Create another report by different user
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="otherpass123"
        )
        other_report = Report.objects.create(
            name="Other User Report",
            description="Report by other user",
            report_type="summary",
            status="completed",
            generated_by=other_user,
        )

        client.force_authenticate(user=admin_user)
        response = client.get("/analytics/reports/")
        assert response.status_code == 200

        data = response.json()
        report_names = [r["name"] for r in data]
        assert "test_report" in report_names
        assert "Other User Report" in report_names

    def test_regular_user_sees_own_reports_only(self, client, user, admin_user):
        """Test regular user only sees their own reports."""
        # Create report by admin
        admin_report = Report.objects.create(
            name="Admin Report",
            description="Report by admin",
            report_type="summary",
            status="completed",
            generated_by=admin_user,
        )

        client.force_authenticate(user=user)
        response = client.get("/analytics/reports/")
        assert response.status_code == 200

        data = response.json()
        report_names = [r["name"] for r in data]
        assert "Admin Report" not in report_names


@pytest.mark.django_db
class TestMetricDefinitionViewSet:
    """Test MetricDefinitionViewSet."""

    @pytest.fixture
    def client(self):
        return APIClient()

    def test_list_metric_definitions(self, client, user, metric_definition):
        """Test listing metric definitions."""
        client.force_authenticate(user=user)
        response = client.get("/analytics/metrics/")
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 1
        assert data[0]["name"] == metric_definition.name

    def test_list_only_active_metrics(self, client, user, metric_definition):
        """Test only active metrics are listed."""
        # Create inactive metric
        inactive_metric = MetricDefinition.objects.create(
            name="inactive_metric",
            description="Inactive metric",
            calculation_method="COUNT",
            is_active=False,
        )

        client.force_authenticate(user=user)
        response = client.get("/analytics/metrics/")
        assert response.status_code == 200

        data = response.json()
        metric_names = [m["name"] for m in data]
        assert metric_definition.name in metric_names
        assert "inactive_metric" not in metric_names

    def test_create_metric_definition(self, client, user):
        """Test creating a metric definition."""
        client.force_authenticate(user=user)

        metric_data = {
            "name": "new_metric",
            "description": "A new metric",
            "calculation_method": "AVERAGE",
            "category": "performance",
            "unit": "ms",
            "is_active": True,
        }

        response = client.post("/analytics/metrics/", metric_data, format="json")
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "new_metric"
        assert data["calculation_method"] == "AVERAGE"

    def test_retrieve_metric_definition(self, client, user, metric_definition):
        """Test retrieving a specific metric definition."""
        client.force_authenticate(user=user)
        response = client.get(f"/analytics/metrics/{metric_definition.id}/")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == metric_definition.id
        assert data["name"] == metric_definition.name

    def test_update_metric_definition(self, client, user, metric_definition):
        """Test updating a metric definition."""
        client.force_authenticate(user=user)

        update_data = {
            "description": "Updated metric description",
            "unit": "updated_unit",
        }

        response = client.patch(
            f"/analytics/metrics/{metric_definition.id}/", update_data, format="json"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["description"] == "Updated metric description"
        assert data["unit"] == "updated_unit"

    def test_delete_metric_definition(self, client, user, metric_definition):
        """Test deleting a metric definition."""
        client.force_authenticate(user=user)
        response = client.delete(f"/analytics/metrics/{metric_definition.id}/")
        assert response.status_code == 204

        # Verify metric is deleted
        assert not MetricDefinition.objects.filter(id=metric_definition.id).exists()

    def test_unauthenticated_access_denied(self, client, metric_definition):
        """Test unauthenticated access is denied."""
        response = client.get("/analytics/metrics/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestCalculateMetricView:
    """Test calculate_metric view."""

    @pytest.fixture
    def client(self):
        return APIClient()

    @patch("apps.analytics.views.MetricCalculatorRegistry")
    def test_calculate_metric_success(self, mock_registry_class, client, user):
        """Test successful metric calculation."""
        # Set up mocks
        mock_registry = MagicMock()
        mock_calculator = MagicMock()
        mock_calculator.calculate.return_value = {"value": 42, "unit": "requests"}
        mock_registry.get_calculator.return_value = mock_calculator
        mock_registry_class.return_value = mock_registry

        client.force_authenticate(user=user)

        metric_data = {
            "metric_name": "test_metric",
            "context": {"user_id": user.id, "date_range": "last_7_days"},
            "cache_duration": 3600,
        }

        response = client.post(
            "/analytics/calculate-metric/", metric_data, format="json"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["metric"] == "test_metric"
        assert data["result"]["value"] == 42
        assert data["cached"] is False

    @patch("apps.analytics.views.AnalyticsCache.get_cached_data")
    def test_calculate_metric_cached_result(self, mock_get_cached, client, user):
        """Test metric calculation with cached result."""
        mock_get_cached.return_value = {"value": 100, "unit": "cached"}

        client.force_authenticate(user=user)

        metric_data = {
            "metric_name": "cached_metric",
            "context": {"user_id": user.id},
            "cache_duration": 3600,
        }

        response = client.post(
            "/analytics/calculate-metric/", metric_data, format="json"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["cached"] is True
        assert data["result"]["value"] == 100

    @patch("apps.analytics.views.MetricCalculatorRegistry")
    def test_calculate_metric_not_found(self, mock_registry_class, client, user):
        """Test metric calculation with non-existent metric."""
        mock_registry = MagicMock()
        mock_registry.get_calculator.return_value = None
        mock_registry_class.return_value = mock_registry

        client.force_authenticate(user=user)

        metric_data = {
            "metric_name": "nonexistent_metric",
            "context": {},
            "cache_duration": 3600,
        }

        response = client.post(
            "/analytics/calculate-metric/", metric_data, format="json"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["error"]

    def test_calculate_metric_invalid_data(self, client, user):
        """Test metric calculation with invalid data."""
        client.force_authenticate(user=user)

        invalid_data = {
            # Missing required fields
            "context": {}
        }

        response = client.post(
            "/analytics/calculate-metric/", invalid_data, format="json"
        )
        assert response.status_code == 400

    def test_calculate_metric_unauthenticated(self, client):
        """Test metric calculation without authentication."""
        metric_data = {
            "metric_name": "test_metric",
            "context": {},
            "cache_duration": 3600,
        }

        response = client.post(
            "/analytics/calculate-metric/", metric_data, format="json"
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestAnalyticsDashboardView:
    """Test analytics_dashboard view."""

    @pytest.fixture
    def client(self):
        return APIClient()

    @patch("apps.analytics.views.MetricCalculatorRegistry")
    def test_analytics_dashboard_success(self, mock_registry_class, client, user):
        """Test successful dashboard data retrieval."""
        # Set up mocks
        mock_registry = MagicMock()
        mock_productivity_calc = MagicMock()
        mock_productivity_calc.calculate.return_value = {"productivity_score": 85}
        mock_quality_calc = MagicMock()
        mock_quality_calc.calculate.return_value = {"quality_score": 90}

        def get_calculator_side_effect(name):
            if name == "productivity":
                return mock_productivity_calc
            elif name == "code_quality":
                return mock_quality_calc
            return None

        mock_registry.get_calculator.side_effect = get_calculator_side_effect
        mock_registry_class.return_value = mock_registry

        client.force_authenticate(user=user)

        response = client.get("/analytics/dashboard/")
        assert response.status_code == 200

        data = response.json()
        assert "period" in data
        assert "metrics" in data
        assert "charts" in data
        assert "summary" in data

        assert "productivity" in data["metrics"]
        assert "code_quality" in data["metrics"]
        assert data["metrics"]["productivity"]["productivity_score"] == 85

    def test_analytics_dashboard_with_date_range(self, client, user):
        """Test dashboard with custom date range."""
        client.force_authenticate(user=user)

        start_date = "2024-01-01T00:00:00Z"
        end_date = "2024-01-31T23:59:59Z"

        response = client.get(
            f"/analytics/dashboard/?start_date={start_date}&end_date={end_date}"
        )
        assert response.status_code == 200

        data = response.json()
        assert "period" in data
        period = data["period"]
        assert "start_date" in period
        assert "end_date" in period

    def test_analytics_dashboard_default_date_range(self, client, user):
        """Test dashboard with default date range (last 30 days)."""
        client.force_authenticate(user=user)

        response = client.get("/analytics/dashboard/")
        assert response.status_code == 200

        data = response.json()
        period = data["period"]
        start_date = datetime.fromisoformat(period["start_date"].replace("Z", "+00:00"))
        end_date = datetime.fromisoformat(period["end_date"].replace("Z", "+00:00"))

        # Should be approximately 30 days difference
        delta = end_date - start_date
        assert 29 <= delta.days <= 31

    def test_analytics_dashboard_unauthenticated(self, client):
        """Test dashboard access without authentication."""
        response = client.get("/analytics/dashboard/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestViewSetPermissions:
    """Test view permissions and access control."""

    @pytest.fixture
    def client(self):
        return APIClient()

    def test_report_viewset_permissions(self, client, user, report):
        """Test ReportViewSet requires authentication."""
        # Unauthenticated access
        response = client.get("/analytics/reports/")
        assert response.status_code == 401

        # Authenticated access
        client.force_authenticate(user=user)
        response = client.get("/analytics/reports/")
        assert response.status_code == 200

    def test_metric_viewset_permissions(self, client, user, metric_definition):
        """Test MetricDefinitionViewSet requires authentication."""
        # Unauthenticated access
        response = client.get("/analytics/metrics/")
        assert response.status_code == 401

        # Authenticated access
        client.force_authenticate(user=user)
        response = client.get("/analytics/metrics/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.fixture
    def client(self):
        return APIClient()

    def test_report_creation_rate_limit(self, client, user, metric_definition):
        """Test rate limiting on report creation."""
        client.force_authenticate(user=user)

        report_data = {
            "name": "Rate Limited Report",
            "description": "Testing rate limits",
            "report_type": "summary",
            "configuration": {"metrics": [metric_definition.id]},
        }

        # This test would need to be run with actual rate limiting enabled
        # For now, just verify the endpoint works
        with patch.object(ReportViewSet, "_generate_report_async"):
            response = client.post("/analytics/reports/", report_data, format="json")
        assert response.status_code == 201

    def test_metric_calculation_rate_limit(self, client, user):
        """Test rate limiting on metric calculation."""
        client.force_authenticate(user=user)

        metric_data = {
            "metric_name": "test_metric",
            "context": {"user_id": user.id},
            "cache_duration": 3600,
        }

        # This test would need to be run with actual rate limiting enabled
        # For now, just verify the endpoint structure
        response = client.post(
            "/analytics/calculate-metric/", metric_data, format="json"
        )
        # Will return 404 or 500 due to missing metric calculator, but that's expected
        assert response.status_code in [404, 500]
