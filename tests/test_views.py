import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.urls import reverse
from django.utils import timezone

import pytest
from rest_framework import status

from apps.analytics.models import AnalyticsCache, MetricDefinition, Report


@pytest.mark.django_db
class TestAPIHomeView:
    """Test cases for API home endpoint"""

    def test_api_home_json_response(self, api_client):
        """Test API home returns JSON by default"""
        response = api_client.get("/?format=json")

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/json"

        data = response.json()
        assert "api_title" in data
        assert data["api_title"] == "SyncScope Analytics Service"
        assert "main_routes" in data
        assert len(data["main_routes"]) > 0

    def test_api_home_html_fallback(self, api_client):
        """Test API home HTML fallback when template missing"""
        response = api_client.get("/")

        # Should fallback to JSON when template doesn't exist
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "api_title" in data

    def test_api_home_service_info(self, api_client):
        """Test service information in API home"""
        response = api_client.get("/?format=json")
        data = response.json()

        assert "service_info" in data
        service_info = data["service_info"]
        assert "features" in service_info
        assert "Report Generation" in service_info["features"]
        assert "status" in service_info
        assert service_info["status"] == "Operational"


@pytest.mark.django_db
class TestReportViewSet:
    """Test cases for Report ViewSet"""

    def test_list_reports_unauthenticated(self, api_client):
        """Test listing reports without authentication"""
        response = api_client.get("/api/reports/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("apps.analytics.views.ReportViewSet._generate_report_async")
    def test_create_report_authenticated(
        self, mock_generate, authenticated_client, mock_user
    ):
        """Test creating a report with authentication"""
        with patch("apps.analytics.views.ReportViewSet.request") as mock_request:
            mock_request.user.id = mock_user.id

            data = {
                "name": "Test Productivity Report",
                "type": "productivity",
                "config": {"start_date": "2024-01-01", "end_date": "2024-01-31"},
            }

            response = authenticated_client.post("/api/reports/", data, format="json")

            assert response.status_code == status.HTTP_201_CREATED
            assert Report.objects.count() == 1

            report = Report.objects.first()
            assert report.name == "Test Productivity Report"
            assert report.type == "productivity"
            assert report.status == "pending"

    def test_list_reports_authenticated(self, authenticated_client, mock_user):
        """Test listing reports for authenticated user"""
        # Create reports for the user
        Report.objects.create(
            name="User Report 1",
            type="productivity",
            config={},
            created_by=mock_user.id,
        )
        Report.objects.create(
            name="User Report 2",
            type="code_quality",
            config={},
            created_by=mock_user.id,
        )

        # Create report for different user
        other_user_id = str(uuid.uuid4())
        Report.objects.create(
            name="Other User Report",
            type="productivity",
            config={},
            created_by=other_user_id,
        )

        with patch("apps.analytics.views.ReportViewSet.get_queryset") as mock_queryset:
            mock_queryset.return_value = Report.objects.filter(created_by=mock_user.id)

            response = authenticated_client.get("/api/reports/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["results"]) == 2

    def test_retrieve_report(self, authenticated_client, completed_report, mock_user):
        """Test retrieving a specific report"""
        with patch("apps.analytics.views.ReportViewSet.get_queryset") as mock_queryset:
            mock_queryset.return_value = Report.objects.filter(created_by=mock_user.id)

            response = authenticated_client.get(f"/api/reports/{completed_report.id}/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["name"] == completed_report.name
            assert data["status"] == "completed"
            assert "data" in data

    @patch("apps.analytics.views.ReportGenerator")
    def test_export_report_pdf(
        self, mock_generator, authenticated_client, completed_report, mock_user
    ):
        """Test exporting report as PDF"""
        mock_generator_instance = Mock()
        mock_generator_instance.export_report.return_value = (
            b"mock_pdf_content",
            "application/pdf",
            "test_report.pdf",
        )
        mock_generator.return_value = mock_generator_instance

        with patch("apps.analytics.views.ReportViewSet.get_object") as mock_get_object:
            mock_get_object.return_value = completed_report

            response = authenticated_client.post(
                f"/api/reports/{completed_report.id}/export/",
                {"format": "pdf", "include_charts": True},
                format="json",
            )

            assert response.status_code == status.HTTP_200_OK
            assert response["Content-Type"] == "application/pdf"
            assert "attachment" in response["Content-Disposition"]

    def test_export_report_not_ready(
        self, authenticated_client, sample_report, mock_user
    ):
        """Test exporting report that's not ready"""
        with patch("apps.analytics.views.ReportViewSet.get_object") as mock_get_object:
            mock_get_object.return_value = sample_report  # Status is 'pending'

            response = authenticated_client.post(
                f"/api/reports/{sample_report.id}/export/",
                {"format": "pdf"},
                format="json",
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "not ready for export" in data["error"]

    @patch("apps.analytics.views.ReportViewSet._generate_report_async")
    def test_regenerate_report(
        self, mock_generate, authenticated_client, completed_report, mock_user
    ):
        """Test regenerating a report"""
        with patch("apps.analytics.views.ReportViewSet.get_object") as mock_get_object:
            mock_get_object.return_value = completed_report

            response = authenticated_client.post(
                f"/api/reports/{completed_report.id}/regenerate/"
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "regeneration started" in data["message"]

            # Check that report status was reset
            completed_report.refresh_from_db()
            assert completed_report.status == "pending"


@pytest.mark.django_db
class TestMetricDefinitionViewSet:
    """Test cases for MetricDefinition ViewSet"""

    def test_list_metric_definitions(self, authenticated_client, metric_definition):
        """Test listing metric definitions"""
        response = authenticated_client.get("/api/metrics/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) >= 1

        # Find our test metric
        test_metric = next(
            (m for m in data["results"] if m["name"] == metric_definition.name), None
        )
        assert test_metric is not None
        assert test_metric["calculation_method"] == "productivity"

    def test_create_metric_definition(self, authenticated_client):
        """Test creating a new metric definition"""
        data = {
            "name": "New Test Metric",
            "description": "A new metric for testing",
            "calculation_method": "avg",
            "parameters": {"threshold": 50},
            "is_active": True,
        }

        response = authenticated_client.post("/api/metrics/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert MetricDefinition.objects.filter(name="New Test Metric").exists()

    def test_retrieve_metric_definition(self, authenticated_client, metric_definition):
        """Test retrieving a specific metric definition"""
        response = authenticated_client.get(f"/api/metrics/{metric_definition.id}/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == metric_definition.name
        assert data["calculation_method"] == metric_definition.calculation_method

    def test_list_only_active_metrics(self, authenticated_client):
        """Test that only active metrics are listed"""
        # Create active metric
        active_metric = MetricDefinition.objects.create(
            name="Active Metric",
            description="Active test metric",
            calculation_method="sum",
            is_active=True,
        )

        # Create inactive metric
        MetricDefinition.objects.create(
            name="Inactive Metric",
            description="Inactive test metric",
            calculation_method="sum",
            is_active=False,
        )

        response = authenticated_client.get("/api/metrics/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should only contain active metrics
        metric_names = [m["name"] for m in data["results"]]
        assert "Active Metric" in metric_names
        assert "Inactive Metric" not in metric_names


@pytest.mark.django_db
class TestCalculateMetricView:
    """Test cases for calculate metric endpoint"""

    @patch("apps.analytics.views.MetricCalculatorRegistry")
    @patch("apps.analytics.views.AnalyticsCache.get_cached_data")
    def test_calculate_metric_success(
        self, mock_cache, mock_registry, authenticated_client
    ):
        """Test successful metric calculation"""
        # Mock cache miss
        mock_cache.return_value = None

        # Mock calculator
        mock_calculator = Mock()
        mock_calculator.calculate.return_value = {
            "productivity_score": 85.5,
            "session_count": 120,
        }

        mock_registry_instance = Mock()
        mock_registry_instance.get_calculator_by_name.return_value = mock_calculator
        mock_registry.return_value = mock_registry_instance

        with patch("apps.analytics.views.AnalyticsCache.cache_data"):
            data = {
                "metric_name": "productivity",
                "context": {
                    "user_id": "test-user-id",
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31",
                },
                "cache_duration": 3600,
            }

            response = authenticated_client.post("/api/calculate/", data, format="json")

            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["metric"] == "productivity"
            assert result["cached"] is False
            assert result["result"]["productivity_score"] == 85.5

    @patch("apps.analytics.views.AnalyticsCache.get_cached_data")
    def test_calculate_metric_cached(self, mock_cache, authenticated_client):
        """Test metric calculation with cached result"""
        # Mock cache hit
        cached_data = {"productivity_score": 90.0, "session_count": 150}
        mock_cache.return_value = cached_data

        data = {
            "metric_name": "productivity",
            "context": {"user_id": "test-user-id"},
            "cache_duration": 3600,
        }

        response = authenticated_client.post("/api/calculate/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["metric"] == "productivity"
        assert result["cached"] is True
        assert result["result"] == cached_data

    @patch("apps.analytics.views.MetricCalculatorRegistry")
    def test_calculate_metric_not_found(self, mock_registry, authenticated_client):
        """Test calculation with non-existent metric"""
        mock_registry_instance = Mock()
        mock_registry_instance.get_calculator_by_name.return_value = None
        mock_registry.return_value = mock_registry_instance

        data = {
            "metric_name": "nonexistent_metric",
            "context": {"user_id": "test-user-id"},
        }

        response = authenticated_client.post("/api/calculate/", data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        result = response.json()
        assert "not found" in result["error"]

    def test_calculate_metric_invalid_data(self, authenticated_client):
        """Test calculation with invalid data"""
        data = {
            "metric_name": "",  # Empty metric name
            "context": "invalid_context",  # Should be dict
        }

        response = authenticated_client.post("/api/calculate/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAnalyticsDashboardView:
    """Test cases for analytics dashboard endpoint"""

    @patch("apps.analytics.views.MetricCalculatorRegistry")
    def test_dashboard_default_dates(
        self, mock_registry, authenticated_client, mock_user, sample_dashboard_data
    ):
        """Test dashboard with default date range"""
        # Mock calculators
        mock_productivity_calc = Mock()
        mock_productivity_calc.calculate.return_value = sample_dashboard_data[
            "metrics"
        ]["productivity"]

        mock_code_quality_calc = Mock()
        mock_code_quality_calc.calculate.return_value = sample_dashboard_data[
            "metrics"
        ]["code_quality"]

        mock_collaboration_calc = Mock()
        mock_collaboration_calc.calculate.return_value = sample_dashboard_data[
            "metrics"
        ]["collaboration"]

        mock_registry_instance = Mock()
        mock_registry_instance.get_calculator.side_effect = lambda calc_type: {
            "productivity": mock_productivity_calc,
            "code_quality": mock_code_quality_calc,
            "team_collaboration": mock_collaboration_calc,
        }.get(calc_type)
        mock_registry.return_value = mock_registry_instance

        with patch("apps.analytics.views.request") as mock_request:
            mock_request.user.id = mock_user.id

            response = authenticated_client.get("/api/dashboard/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "period" in data
            assert "metrics" in data
            assert "productivity" in data["metrics"]
            assert data["metrics"]["productivity"]["score"] == 85.5

    @patch("apps.analytics.views.MetricCalculatorRegistry")
    def test_dashboard_custom_dates(
        self, mock_registry, authenticated_client, mock_user
    ):
        """Test dashboard with custom date range"""
        mock_registry_instance = Mock()
        mock_calculator = Mock()
        mock_calculator.calculate.return_value = {"score": 80.0}
        mock_registry_instance.get_calculator.return_value = mock_calculator
        mock_registry.return_value = mock_registry_instance

        with patch("apps.analytics.views.request") as mock_request:
            mock_request.user.id = mock_user.id

            params = {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
            }

            response = authenticated_client.get("/api/dashboard/", params)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            period = data["period"]
            assert "2024-01-01" in str(period["start_date"])
            assert "2024-01-31" in str(period["end_date"])

    def test_dashboard_unauthenticated(self, api_client):
        """Test dashboard without authentication"""
        response = api_client.get("/api/dashboard/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestViewPermissions:
    """Test permission handling across views"""

    def test_report_viewset_permissions(self, api_client, sample_report):
        """Test that report endpoints require authentication"""
        endpoints = [
            "/api/reports/",
            f"/api/reports/{sample_report.id}/",
            f"/api/reports/{sample_report.id}/export/",
            f"/api/reports/{sample_report.id}/regenerate/",
        ]

        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_metric_viewset_permissions(self, api_client, metric_definition):
        """Test that metric endpoints require authentication"""
        endpoints = ["/api/metrics/", f"/api/metrics/{metric_definition.id}/"]

        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_calculate_metric_permissions(self, api_client):
        """Test that calculate endpoint requires authentication"""
        response = api_client.post("/api/calculate/", {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_dashboard_permissions(self, api_client):
        """Test that dashboard endpoint requires authentication"""
        response = api_client.get("/api/dashboard/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestErrorHandling:
    """Test error handling in views"""

    def test_report_export_exception_handling(
        self, authenticated_client, completed_report, mock_user
    ):
        """Test error handling in report export"""
        with (
            patch("apps.analytics.views.ReportViewSet.get_object") as mock_get_object,
            patch("apps.analytics.views.ReportGenerator") as mock_generator,
        ):
            mock_get_object.return_value = completed_report
            mock_generator_instance = Mock()
            mock_generator_instance.export_report.side_effect = Exception(
                "Export failed"
            )
            mock_generator.return_value = mock_generator_instance

            response = authenticated_client.post(
                f"/api/reports/{completed_report.id}/export/",
                {"format": "pdf"},
                format="json",
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Export failed" in data["error"]

    @patch("apps.analytics.views.MetricCalculatorRegistry")
    def test_calculate_metric_exception_handling(
        self, mock_registry, authenticated_client
    ):
        """Test error handling in metric calculation"""
        mock_calculator = Mock()
        mock_calculator.calculate.side_effect = Exception("Calculation error")

        mock_registry_instance = Mock()
        mock_registry_instance.get_calculator_by_name.return_value = mock_calculator
        mock_registry.return_value = mock_registry_instance

        with (
            patch(
                "apps.analytics.views.AnalyticsCache.get_cached_data", return_value=None
            ),
            patch("apps.analytics.views.AnalyticsCache.cache_data"),
        ):
            data = {
                "metric_name": "productivity",
                "context": {"user_id": "test-user-id"},
            }

            response = authenticated_client.post("/api/calculate/", data, format="json")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            result = response.json()
            assert "Calculation error" in result["error"]
