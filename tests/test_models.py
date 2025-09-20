import uuid
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

import pytest

from apps.analytics.models import AnalyticsCache, MetricDefinition, Report


@pytest.mark.django_db
class TestReportModel:
    """Test cases for Report model"""

    def test_create_report(self, mock_user):
        """Test creating a new report"""
        report = Report.objects.create(
            name="Test Report",
            type="productivity",
            config={"start_date": "2024-01-01", "end_date": "2024-01-31"},
            created_by=mock_user.id,
        )

        assert report.id is not None
        assert report.name == "Test Report"
        assert report.type == "productivity"
        assert report.status == "pending"
        assert report.created_by == mock_user.id
        assert report.data is None
        assert report.file_path is None

    def test_report_str_representation(self, sample_report):
        """Test string representation of report"""
        expected = f"{sample_report.name} ({sample_report.type})"
        assert str(sample_report) == expected

    def test_report_status_choices(self, mock_user):
        """Test report status validation"""
        # Valid status
        report = Report.objects.create(
            name="Test Report",
            type="productivity",
            config={},
            created_by=mock_user.id,
            status="completed",
        )
        assert report.status == "completed"

        # Invalid status should be handled by Django validation
        with pytest.raises(ValidationError):
            report = Report(
                name="Invalid Report",
                type="productivity",
                config={},
                created_by=mock_user.id,
                status="invalid_status",
            )
            report.full_clean()

    def test_report_type_choices(self, mock_user):
        """Test report type validation"""
        # Valid type
        report = Report.objects.create(
            name="Test Report", type="code_quality", config={}, created_by=mock_user.id
        )
        assert report.type == "code_quality"

    def test_report_uuid_field(self, mock_user):
        """Test that report ID is a valid UUID"""
        report = Report.objects.create(
            name="Test Report", type="productivity", config={}, created_by=mock_user.id
        )

        # Should be a valid UUID
        assert isinstance(report.id, uuid.UUID)
        assert str(report.id) != ""

    def test_report_timestamps(self, mock_user):
        """Test timestamp fields"""
        before_creation = timezone.now()
        report = Report.objects.create(
            name="Test Report", type="productivity", config={}, created_by=mock_user.id
        )
        after_creation = timezone.now()

        assert before_creation <= report.created_at <= after_creation
        assert before_creation <= report.updated_at <= after_creation

    def test_report_update_timestamps(self, sample_report):
        """Test that updated_at changes on save"""
        original_updated = sample_report.updated_at
        sample_report.name = "Updated Name"
        sample_report.save()

        assert sample_report.updated_at > original_updated

    def test_report_config_json_field(self, mock_user):
        """Test JSON config field"""
        config_data = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "include_weekends": False,
            "metrics": ["productivity", "code_quality"],
        }

        report = Report.objects.create(
            name="Test Report",
            type="productivity",
            config=config_data,
            created_by=mock_user.id,
        )

        assert report.config == config_data
        assert report.config["include_weekends"] is False
        assert len(report.config["metrics"]) == 2


@pytest.mark.django_db
class TestMetricDefinitionModel:
    """Test cases for MetricDefinition model"""

    def test_create_metric_definition(self):
        """Test creating a metric definition"""
        metric = MetricDefinition.objects.create(
            name="Test Metric",
            description="A test metric for validation",
            calculation_method="sum",
            parameters={"threshold": 10},
        )

        assert metric.id is not None
        assert metric.name == "Test Metric"
        assert metric.calculation_method == "sum"
        assert metric.is_active is True
        assert metric.parameters == {"threshold": 10}

    def test_metric_definition_str_representation(self, metric_definition):
        """Test string representation"""
        assert str(metric_definition) == metric_definition.name

    def test_metric_definition_unique_name(self, metric_definition):
        """Test unique constraint on metric name"""
        with pytest.raises(IntegrityError):
            MetricDefinition.objects.create(
                name=metric_definition.name,  # Same name
                description="Different description",
                calculation_method="avg",
            )

    def test_metric_definition_calculation_methods(self):
        """Test different calculation methods"""
        methods = ["sum", "avg", "count", "percentage", "ratio"]

        for method in methods:
            metric = MetricDefinition.objects.create(
                name=f"Test {method} Metric",
                description=f"Test {method} calculation",
                calculation_method=method,
            )
            assert metric.calculation_method == method

    def test_metric_definition_parameters_field(self):
        """Test parameters JSON field"""
        complex_params = {
            "weights": {"sessions": 0.4, "commits": 0.6},
            "thresholds": {"min": 0, "max": 100},
            "filters": ["active_only", "exclude_weekends"],
        }

        metric = MetricDefinition.objects.create(
            name="Complex Metric",
            description="Metric with complex parameters",
            calculation_method="custom",
            parameters=complex_params,
        )

        assert metric.parameters == complex_params
        assert metric.parameters["weights"]["sessions"] == 0.4

    def test_metric_definition_active_flag(self):
        """Test active/inactive functionality"""
        metric = MetricDefinition.objects.create(
            name="Test Metric",
            description="Test description",
            calculation_method="sum",
            is_active=False,
        )

        assert metric.is_active is False

        # Test filtering active metrics
        active_metrics = MetricDefinition.objects.filter(is_active=True)
        assert metric not in active_metrics


@pytest.mark.django_db
class TestAnalyticsCacheModel:
    """Test cases for AnalyticsCache model"""

    def test_create_cache_entry(self):
        """Test creating a cache entry"""
        cache_entry = AnalyticsCache.objects.create(
            cache_key="test_key_123",
            cache_type="metric_calculation",
            data={"result": 85.5, "calculation_time": 0.5},
            expires_at=timezone.now() + timedelta(hours=1),
        )

        assert cache_entry.id is not None
        assert cache_entry.cache_key == "test_key_123"
        assert cache_entry.cache_type == "metric_calculation"
        assert cache_entry.data == {"result": 85.5, "calculation_time": 0.5}

    def test_cache_str_representation(self, analytics_cache):
        """Test string representation"""
        expected = f"{analytics_cache.cache_key} ({analytics_cache.cache_type})"
        assert str(analytics_cache) == expected

    def test_cache_expiration(self):
        """Test cache expiration logic"""
        # Create expired cache
        expired_cache = AnalyticsCache.objects.create(
            cache_key="expired_key",
            cache_type="metric_calculation",
            data={"result": 100},
            expires_at=timezone.now() - timedelta(hours=1),
        )

        # Create active cache
        active_cache = AnalyticsCache.objects.create(
            cache_key="active_key",
            cache_type="metric_calculation",
            data={"result": 200},
            expires_at=timezone.now() + timedelta(hours=1),
        )

        # Test filtering expired entries
        expired_entries = AnalyticsCache.objects.filter(expires_at__lt=timezone.now())
        active_entries = AnalyticsCache.objects.filter(expires_at__gt=timezone.now())

        assert expired_cache in expired_entries
        assert active_cache in active_entries
        assert active_cache not in expired_entries

    def test_cache_key_uniqueness(self, analytics_cache):
        """Test cache key should be unique per type and key combination"""
        # Different cache type, same key - should work
        AnalyticsCache.objects.create(
            cache_key=analytics_cache.cache_key,
            cache_type="dashboard_data",
            data={"different": "data"},
            expires_at=timezone.now() + timedelta(hours=1),
        )

        # Same cache type and key - should work (overwrite scenario)
        AnalyticsCache.objects.create(
            cache_key=analytics_cache.cache_key,
            cache_type=analytics_cache.cache_type,
            data={"updated": "data"},
            expires_at=timezone.now() + timedelta(hours=2),
        )

        # Should have 3 total cache entries
        assert AnalyticsCache.objects.count() == 3

    def test_cache_data_json_field(self):
        """Test JSON data field functionality"""
        complex_data = {
            "metrics": {"productivity": 85.5, "code_quality": 78.3},
            "metadata": {
                "calculation_time": 1.25,
                "source": "postgresql",
                "cached_at": timezone.now().isoformat(),
            },
            "charts": [{"x": "2024-01-01", "y": 80.0}, {"x": "2024-01-02", "y": 82.5}],
        }

        cache_entry = AnalyticsCache.objects.create(
            cache_key="complex_data_key",
            cache_type="dashboard_data",
            data=complex_data,
            expires_at=timezone.now() + timedelta(hours=1),
        )

        assert cache_entry.data == complex_data
        assert cache_entry.data["metrics"]["productivity"] == 85.5
        assert len(cache_entry.data["charts"]) == 2

    def test_cache_type_choices(self):
        """Test different cache types"""
        cache_types = [
            "metric_calculation",
            "dashboard_data",
            "report_data",
            "analysis_result",
        ]

        for cache_type in cache_types:
            cache_entry = AnalyticsCache.objects.create(
                cache_key=f"test_key_{cache_type}",
                cache_type=cache_type,
                data={"test": "data"},
                expires_at=timezone.now() + timedelta(hours=1),
            )
            assert cache_entry.cache_type == cache_type

    @pytest.mark.parametrize(
        "cache_type",
        ["metric_calculation", "dashboard_data", "report_data", "analysis_result"],
    )
    def test_cache_types_parametrized(self, cache_type):
        """Parametrized test for cache types"""
        cache_entry = AnalyticsCache.objects.create(
            cache_key=f"param_test_{cache_type}",
            cache_type=cache_type,
            data={"param_test": True},
            expires_at=timezone.now() + timedelta(hours=1),
        )

        assert cache_entry.cache_type == cache_type
        assert cache_entry.data["param_test"] is True


@pytest.mark.django_db
class TestModelRelationships:
    """Test model relationships and constraints"""

    def test_report_without_user_id(self):
        """Test that report requires created_by"""
        with pytest.raises(IntegrityError):
            Report.objects.create(
                name="Test Report",
                type="productivity",
                config={},
                created_by=None,  # Should not be allowed
            )

    def test_metric_definition_without_name(self):
        """Test that metric definition requires name"""
        with pytest.raises(IntegrityError):
            MetricDefinition.objects.create(
                name=None,  # Should not be allowed
                description="Test description",
                calculation_method="sum",
            )

    def test_cache_without_expiration(self):
        """Test cache entry without expiration"""
        # This should work - expiration is optional
        cache_entry = AnalyticsCache.objects.create(
            cache_key="no_expiration_key",
            cache_type="metric_calculation",
            data={"result": 100},
            # No expires_at set
        )

        assert cache_entry.expires_at is None
