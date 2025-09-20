from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.utils import timezone

import pytest

from apps.analytics.metric_calculators import (
    CodeQualityMetricCalculator,
    MetricCalculationService,
    MetricCalculatorFactory,
    MetricCalculatorRegistry,
    ProductivityMetricCalculator,
    TeamCollaborationMetricCalculator,
)
from apps.analytics.models import MetricDefinition


@pytest.mark.django_db
class TestMetricCalculatorFactory:
    """Test cases for MetricCalculatorFactory"""

    def test_create_productivity_calculator(self, metric_definition):
        """Test creating productivity calculator"""
        metric_definition.calculation_method = "productivity"
        calculator = MetricCalculatorFactory.create_calculator(metric_definition)

        assert isinstance(calculator, ProductivityMetricCalculator)
        assert calculator.metric_definition == metric_definition

    def test_create_code_quality_calculator(self):
        """Test creating code quality calculator"""
        metric_definition = MetricDefinition.objects.create(
            name="Code Quality Metric",
            description="Test code quality metric",
            calculation_method="code_quality",
        )

        calculator = MetricCalculatorFactory.create_calculator(metric_definition)
        assert isinstance(calculator, CodeQualityMetricCalculator)

    def test_create_collaboration_calculator(self):
        """Test creating team collaboration calculator"""
        metric_definition = MetricDefinition.objects.create(
            name="Collaboration Metric",
            description="Test collaboration metric",
            calculation_method="team_collaboration",
        )

        calculator = MetricCalculatorFactory.create_calculator(metric_definition)
        assert isinstance(calculator, TeamCollaborationMetricCalculator)

    def test_unsupported_calculation_method(self):
        """Test handling unsupported calculation method"""
        metric_definition = MetricDefinition.objects.create(
            name="Unsupported Metric",
            description="Test unsupported metric",
            calculation_method="unsupported_method",
        )

        with pytest.raises(ValueError, match="Unsupported calculation method"):
            MetricCalculatorFactory.create_calculator(metric_definition)

    def test_get_available_categories(self):
        """Test getting available calculator categories"""
        categories = MetricCalculatorFactory.get_available_categories()

        expected_categories = [
            "productivity",
            "code_quality",
            "team_collaboration",
            "performance",
            "security",
            "efficiency",
            "engagement",
            "learning",
            "deployment",
            "innovation",
        ]

        for category in expected_categories:
            assert category in categories


@pytest.mark.django_db
class TestProductivityMetricCalculator:
    """Test cases for ProductivityMetricCalculator"""

    @pytest.fixture
    def productivity_metric(self):
        return MetricDefinition.objects.create(
            name="Productivity Test Metric",
            description="Test productivity calculation",
            calculation_method="productivity",
            parameters={
                "weight_sessions": 0.4,
                "weight_commits": 0.6,
                "baseline_sessions_per_day": 3,
                "baseline_commits_per_day": 5,
            },
        )

    @patch("apps.analytics.service_integration.MonitoringServiceClient")
    @patch("apps.analytics.service_integration.ManagementServiceClient")
    def test_productivity_calculation(
        self, mock_management, mock_monitoring, productivity_metric
    ):
        """Test productivity metric calculation"""
        # Mock monitoring service response
        mock_monitoring_instance = Mock()
        mock_monitoring_instance.get_user_sessions.return_value = {
            "sessions": [
                {
                    "user_id": "test-user-id",
                    "start_time": "2024-01-01T09:00:00Z",
                    "end_time": "2024-01-01T10:30:00Z",
                    "duration": 90,
                },
                {
                    "user_id": "test-user-id",
                    "start_time": "2024-01-01T14:00:00Z",
                    "end_time": "2024-01-01T15:00:00Z",
                    "duration": 60,
                },
            ]
        }
        mock_monitoring.return_value = mock_monitoring_instance

        # Mock management service response
        mock_management_instance = Mock()
        mock_management_instance.get_user_commits.return_value = {
            "commits": [
                {"user_id": "test-user-id", "date": "2024-01-01", "count": 3},
                {"user_id": "test-user-id", "date": "2024-01-02", "count": 5},
            ]
        }
        mock_management.return_value = mock_management_instance

        calculator = ProductivityMetricCalculator(productivity_metric)
        context = {
            "user_id": "test-user-id",
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 1, 31),
        }

        result = calculator.calculate(context)

        assert "productivity_score" in result
        assert "session_metrics" in result
        assert "commit_metrics" in result
        assert isinstance(result["productivity_score"], (int, float))
        assert 0 <= result["productivity_score"] <= 100

    def test_productivity_calculation_no_data(self, productivity_metric):
        """Test productivity calculation with no data"""
        with (
            patch(
                "apps.analytics.service_integration.MonitoringServiceClient"
            ) as mock_monitoring,
            patch(
                "apps.analytics.service_integration.ManagementServiceClient"
            ) as mock_management,
        ):

            # Mock empty responses
            mock_monitoring_instance = Mock()
            mock_monitoring_instance.get_user_sessions.return_value = {"sessions": []}
            mock_monitoring.return_value = mock_monitoring_instance

            mock_management_instance = Mock()
            mock_management_instance.get_user_commits.return_value = {"commits": []}
            mock_management.return_value = mock_management_instance

            calculator = ProductivityMetricCalculator(productivity_metric)
            context = {
                "user_id": "test-user-id",
                "start_date": datetime(2024, 1, 1),
                "end_date": datetime(2024, 1, 31),
            }

            result = calculator.calculate(context)

            assert result["productivity_score"] == 0
            assert result["session_metrics"]["total_sessions"] == 0
            assert result["commit_metrics"]["total_commits"] == 0

    def test_get_cache_key(self, productivity_metric):
        """Test cache key generation"""
        calculator = ProductivityMetricCalculator(productivity_metric)
        context = {
            "user_id": "test-user-id",
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 1, 31),
        }

        cache_key = calculator.get_cache_key(context)
        assert isinstance(cache_key, str)
        assert "productivity" in cache_key
        assert "test-user-id" in cache_key


@pytest.mark.django_db
class TestCodeQualityMetricCalculator:
    """Test cases for CodeQualityMetricCalculator"""

    @pytest.fixture
    def code_quality_metric(self):
        return MetricDefinition.objects.create(
            name="Code Quality Test Metric",
            description="Test code quality calculation",
            calculation_method="code_quality",
            parameters={
                "weight_complexity": 0.3,
                "weight_coverage": 0.4,
                "weight_duplication": 0.3,
            },
        )

    @patch("apps.analytics.service_integration.ManagementServiceClient")
    def test_code_quality_calculation(self, mock_management, code_quality_metric):
        """Test code quality metric calculation"""
        # Mock management service response
        mock_management_instance = Mock()
        mock_management_instance.get_code_quality_metrics.return_value = {
            "complexity": {"average": 2.5, "files": 45},
            "coverage": {
                "percentage": 87.5,
                "lines_covered": 1250,
                "total_lines": 1429,
            },
            "duplication": {"percentage": 3.2, "duplicated_lines": 46},
        }
        mock_management.return_value = mock_management_instance

        calculator = CodeQualityMetricCalculator(code_quality_metric)
        context = {
            "user_id": "test-user-id",
            "project_id": "test-project-id",
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 1, 31),
        }

        result = calculator.calculate(context)

        assert "code_quality_score" in result
        assert "complexity_metrics" in result
        assert "coverage_metrics" in result
        assert "duplication_metrics" in result
        assert isinstance(result["code_quality_score"], (int, float))
        assert 0 <= result["code_quality_score"] <= 100

    def test_code_quality_calculation_no_data(self, code_quality_metric):
        """Test code quality calculation with no data"""
        with patch(
            "apps.analytics.service_integration.ManagementServiceClient"
        ) as mock_management:
            mock_management_instance = Mock()
            mock_management_instance.get_code_quality_metrics.return_value = {}
            mock_management.return_value = mock_management_instance

            calculator = CodeQualityMetricCalculator(code_quality_metric)
            context = {"user_id": "test-user-id", "project_id": "test-project-id"}

            result = calculator.calculate(context)

            assert result["code_quality_score"] == 0


@pytest.mark.django_db
class TestTeamCollaborationMetricCalculator:
    """Test cases for TeamCollaborationMetricCalculator"""

    @pytest.fixture
    def collaboration_metric(self):
        return MetricDefinition.objects.create(
            name="Collaboration Test Metric",
            description="Test collaboration calculation",
            calculation_method="team_collaboration",
            parameters={
                "weight_pr_reviews": 0.4,
                "weight_comments": 0.3,
                "weight_meetings": 0.3,
            },
        )

    @patch("apps.analytics.service_integration.ManagementServiceClient")
    def test_collaboration_calculation(self, mock_management, collaboration_metric):
        """Test team collaboration metric calculation"""
        # Mock management service response
        mock_management_instance = Mock()
        mock_management_instance.get_collaboration_metrics.return_value = {
            "pull_requests": {
                "reviews_given": 15,
                "reviews_received": 8,
                "total_prs": 12,
            },
            "comments": {"pr_comments": 45, "issue_comments": 23, "code_comments": 18},
            "meetings": {"attended": 8, "organized": 2, "total_hours": 12.5},
        }
        mock_management.return_value = mock_management_instance

        calculator = TeamCollaborationMetricCalculator(collaboration_metric)
        context = {
            "user_id": "test-user-id",
            "team_id": "test-team-id",
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 1, 31),
        }

        result = calculator.calculate(context)

        assert "collaboration_score" in result
        assert "pr_metrics" in result
        assert "comment_metrics" in result
        assert "meeting_metrics" in result
        assert isinstance(result["collaboration_score"], (int, float))
        assert 0 <= result["collaboration_score"] <= 100


@pytest.mark.django_db
class TestMetricCalculatorRegistry:
    """Test cases for MetricCalculatorRegistry"""

    def test_registry_initialization(self):
        """Test registry initialization"""
        registry = MetricCalculatorRegistry()
        assert registry is not None

    def test_get_calculator_by_type(self):
        """Test getting calculator by type"""
        registry = MetricCalculatorRegistry()
        calculator = registry.get_calculator("productivity")

        assert calculator is not None
        assert hasattr(calculator, "calculate")

    def test_get_calculator_by_name(self):
        """Test getting calculator by name"""
        registry = MetricCalculatorRegistry()
        calculator = registry.get_calculator_by_name("productivity")

        assert calculator is not None
        assert hasattr(calculator, "calculate")

    def test_get_nonexistent_calculator(self):
        """Test getting non-existent calculator"""
        registry = MetricCalculatorRegistry()
        calculator = registry.get_calculator("nonexistent_type")

        assert calculator is None

    def test_list_calculators(self):
        """Test listing available calculators"""
        registry = MetricCalculatorRegistry()
        calculators = registry.list_calculators()

        assert isinstance(calculators, list)
        assert len(calculators) > 0
        assert "productivity" in calculators
        assert "code_quality" in calculators
        assert "team_collaboration" in calculators


@pytest.mark.django_db
class TestMetricCalculationService:
    """Test cases for MetricCalculationService"""

    @patch(
        "apps.analytics.metric_calculators.MetricCalculatorFactory.create_calculator"
    )
    def test_calculate_metric_success(self, mock_create_calculator, metric_definition):
        """Test successful metric calculation"""
        # Mock calculator
        mock_calculator = Mock()
        mock_calculator.calculate.return_value = {
            "test_score": 85.5,
            "test_data": "success",
        }
        mock_create_calculator.return_value = mock_calculator

        context = {"user_id": "test-user-id"}
        result = MetricCalculationService.calculate_metric(metric_definition, context)

        assert result["test_score"] == 85.5
        assert result["metric_id"] == str(metric_definition.id)
        assert result["metric_name"] == metric_definition.name
        assert result["calculation_method"] == metric_definition.calculation_method
        assert "calculated_at" in result

    @patch(
        "apps.analytics.metric_calculators.MetricCalculatorFactory.create_calculator"
    )
    def test_calculate_metric_exception(
        self, mock_create_calculator, metric_definition
    ):
        """Test metric calculation with exception"""
        # Mock calculator that raises exception
        mock_calculator = Mock()
        mock_calculator.calculate.side_effect = Exception("Calculation failed")
        mock_create_calculator.return_value = mock_calculator

        context = {"user_id": "test-user-id"}
        result = MetricCalculationService.calculate_metric(metric_definition, context)

        assert "error" in result
        assert "Calculation failed" in result["error"]
        assert result["metric_id"] == str(metric_definition.id)
        assert result["metric_name"] == metric_definition.name

    @patch(
        "apps.analytics.metric_calculators.MetricCalculationService.calculate_metric"
    )
    def test_calculate_multiple_metrics(self, mock_calculate_single, metric_definition):
        """Test calculating multiple metrics"""
        # Create additional metric definitions
        metric2 = MetricDefinition.objects.create(
            name="Second Metric",
            description="Second test metric",
            calculation_method="code_quality",
        )

        metric3 = MetricDefinition.objects.create(
            name="Third Metric",
            description="Third test metric",
            calculation_method="team_collaboration",
        )

        # Mock single calculation results
        mock_calculate_single.side_effect = [
            {"metric_1": "result_1"},
            {"metric_2": "result_2"},
            {"metric_3": "result_3"},
        ]

        context = {"user_id": "test-user-id"}
        metrics = [metric_definition, metric2, metric3]

        results = MetricCalculationService.calculate_multiple_metrics(metrics, context)

        assert len(results) == 3
        assert results[0]["metric_1"] == "result_1"
        assert results[1]["metric_2"] == "result_2"
        assert results[2]["metric_3"] == "result_3"

        # Verify single calculation was called for each metric
        assert mock_calculate_single.call_count == 3


@pytest.mark.django_db
class TestCalculatorEdgeCases:
    """Test edge cases and error conditions"""

    def test_calculator_with_missing_parameters(self):
        """Test calculator behavior with missing parameters"""
        metric_definition = MetricDefinition.objects.create(
            name="Minimal Metric",
            description="Metric with minimal parameters",
            calculation_method="productivity",
            # No parameters provided
        )

        calculator = MetricCalculatorFactory.create_calculator(metric_definition)
        assert calculator.parameters == {}

    def test_calculator_with_invalid_dates(self, metric_definition):
        """Test calculator with invalid date context"""
        calculator = ProductivityMetricCalculator(metric_definition)

        # Invalid date format
        context = {
            "user_id": "test-user-id",
            "start_date": "invalid-date",
            "end_date": "invalid-date",
        }

        # Should handle gracefully or raise appropriate exception
        with pytest.raises((ValueError, TypeError)):
            calculator.calculate(context)

    def test_calculator_with_missing_context(self, metric_definition):
        """Test calculator with missing context data"""
        calculator = ProductivityMetricCalculator(metric_definition)

        # Missing required context
        context = {}

        # Should handle gracefully
        result = calculator.calculate(context)
        assert isinstance(result, dict)

    @patch("apps.analytics.service_integration.MonitoringServiceClient")
    def test_calculator_with_service_error(self, mock_monitoring, metric_definition):
        """Test calculator behavior when external service fails"""
        # Mock service to raise exception
        mock_monitoring_instance = Mock()
        mock_monitoring_instance.get_user_sessions.side_effect = Exception(
            "Service unavailable"
        )
        mock_monitoring.return_value = mock_monitoring_instance

        calculator = ProductivityMetricCalculator(metric_definition)
        context = {
            "user_id": "test-user-id",
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 1, 31),
        }

        # Should handle service errors gracefully
        result = calculator.calculate(context)
        assert isinstance(result, dict)
        # Should either return default values or include error information
