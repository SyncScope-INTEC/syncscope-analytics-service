import pytest
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from unittest.mock import patch

from apps.analytics.models import (
    MetricDefinition,
    Report,
    AnalyticsCache,
    TimeSeriesData,
    RetryableModelMixin
)


@pytest.mark.django_db
class TestMetricDefinition:
    """Test MetricDefinition model."""

    def test_create_metric_definition(self, metric_definition):
        """Test creating a metric definition."""
        assert metric_definition.name == "test_metric"
        assert metric_definition.description == "A test metric for analytics"
        assert metric_definition.calculation_method == "SUM"
        assert metric_definition.category == "performance"
        assert metric_definition.unit == "requests"
        assert metric_definition.is_active is True

    def test_metric_definition_str(self, metric_definition):
        """Test string representation."""
        assert str(metric_definition) == "test_metric"

    def test_metric_definition_with_filters_and_tags(self, metric_definition_complex):
        """Test metric definition with complex data."""
        assert metric_definition_complex.filters == {"status": "active"}
        assert metric_definition_complex.tags == {"priority": "high", "team": "analytics"}
        assert metric_definition_complex.aggregation_period == "daily"

    def test_metric_definition_timestamps(self, metric_definition):
        """Test timestamp fields are auto-populated."""
        assert metric_definition.created_at is not None
        assert metric_definition.updated_at is not None

    def test_metric_definition_update_timestamp(self, metric_definition):
        """Test updated_at changes on save."""
        original_updated = metric_definition.updated_at
        metric_definition.description = "Updated description"
        metric_definition.save()
        assert metric_definition.updated_at > original_updated

    def test_get_active_metrics(self):
        """Test filtering active metrics."""
        MetricDefinition.objects.create(
            name="active_metric",
            description="Active metric",
            calculation_method="COUNT",
            is_active=True
        )
        MetricDefinition.objects.create(
            name="inactive_metric",
            description="Inactive metric",
            calculation_method="COUNT",
            is_active=False
        )

        active_metrics = MetricDefinition.objects.filter(is_active=True)
        assert active_metrics.count() == 1
        assert active_metrics.first().name == "active_metric"

    def test_metric_definition_calculation_methods(self):
        """Test different calculation methods."""
        methods = ["SUM", "AVERAGE", "COUNT", "MIN", "MAX"]
        for method in methods:
            metric = MetricDefinition.objects.create(
                name=f"metric_{method.lower()}",
                description=f"Metric with {method}",
                calculation_method=method
            )
            assert metric.calculation_method == method


@pytest.mark.django_db
class TestReport:
    """Test Report model."""

    def test_create_report(self, report):
        """Test creating a report."""
        assert report.name == "test_report"
        assert report.description == "A test report"
        assert report.report_type == "summary"
        assert report.status == "completed"
        assert report.configuration is not None
        assert report.data is not None

    def test_report_str(self, report):
        """Test string representation."""
        assert str(report) == "test_report"

    def test_report_status_choices(self, user):
        """Test different report statuses."""
        statuses = ["pending", "processing", "completed", "failed"]
        for status in statuses:
            report = Report.objects.create(
                name=f"report_{status}",
                description=f"Report with {status} status",
                report_type="summary",
                status=status,
                generated_by=user
            )
            assert report.status == status

    def test_report_types(self, user):
        """Test different report types."""
        types = ["summary", "detailed", "comparison"]
        for report_type in types:
            report = Report.objects.create(
                name=f"report_{report_type}",
                description=f"{report_type.title()} report",
                report_type=report_type,
                status="pending",
                generated_by=user
            )
            assert report.report_type == report_type

    def test_report_data_structure(self, report):
        """Test report data contains expected structure."""
        assert "total_requests" in report.data
        assert "average_response_time" in report.data
        assert report.data["total_requests"] == 1000
        assert report.data["average_response_time"] == 250

    def test_report_configuration_structure(self, report, metric_definition):
        """Test report configuration contains expected structure."""
        assert "metrics" in report.configuration
        assert "date_range" in report.configuration
        assert metric_definition.id in report.configuration["metrics"]
        assert report.configuration["date_range"] == "last_7_days"

    def test_pending_report(self, pending_report):
        """Test pending report creation."""
        assert pending_report.status == "pending"
        assert pending_report.data is None or pending_report.data == {}

    def test_report_generated_at_auto_now(self, report):
        """Test generated_at timestamp."""
        assert report.generated_at is not None
        assert isinstance(report.generated_at, datetime)


@pytest.mark.django_db
class TestAnalyticsCache:
    """Test AnalyticsCache model."""

    def test_create_cache_entry(self, analytics_cache):
        """Test creating a cache entry."""
        assert analytics_cache.cache_key == "test_cache_key"
        assert analytics_cache.cache_data is not None
        assert analytics_cache.expires_at is not None

    def test_cache_str(self, analytics_cache):
        """Test string representation."""
        assert str(analytics_cache) == "test_cache_key"

    def test_cache_data_structure(self, analytics_cache):
        """Test cache data contains expected structure."""
        assert "metric_values" in analytics_cache.cache_data
        assert "timestamps" in analytics_cache.cache_data
        assert analytics_cache.cache_data["metric_values"] == [100, 200, 300]

    def test_cache_expiration(self, expired_cache):
        """Test expired cache detection."""
        assert expired_cache.expires_at < timezone.now()

    def test_valid_cache(self, analytics_cache):
        """Test valid cache detection."""
        assert analytics_cache.expires_at > timezone.now()

    def test_get_valid_cache_entries(self, analytics_cache, expired_cache):
        """Test filtering valid cache entries."""
        valid_entries = AnalyticsCache.objects.filter(expires_at__gt=timezone.now())
        assert analytics_cache in valid_entries
        assert expired_cache not in valid_entries

    def test_cache_cleanup_expired(self, expired_cache):
        """Test removing expired cache entries."""
        assert AnalyticsCache.objects.filter(cache_key="expired_cache_key").exists()

        # Simulate cleanup of expired entries
        AnalyticsCache.objects.filter(expires_at__lt=timezone.now()).delete()

        assert not AnalyticsCache.objects.filter(cache_key="expired_cache_key").exists()


@pytest.mark.django_db
class TestTimeSeriesData:
    """Test TimeSeriesData model."""

    def test_create_time_series_data(self, time_series_data):
        """Test creating time series data."""
        point = time_series_data[0]
        assert point.measurement == "test_measurement"
        assert point.source == "test_source"
        assert point.value_float == 0.0
        assert point.value_int == 0
        assert point.tags == {"category": "test", "instance": "server_0"}

    def test_time_series_str(self, time_series_data):
        """Test string representation."""
        point = time_series_data[0]
        expected = f"test_measurement from test_source at {point.timestamp}"
        assert str(point) == expected

    def test_time_series_multiple_value_types(self, time_series_string_data, time_series_bool_data):
        """Test different value types."""
        # String value
        assert time_series_string_data.value_string == "healthy"
        assert time_series_string_data.value_float is None
        assert time_series_string_data.value_int is None
        assert time_series_string_data.value_bool is None

        # Boolean value
        assert time_series_bool_data.value_bool is True
        assert time_series_bool_data.value_string is None

    def test_time_series_tags_structure(self, time_series_data):
        """Test tags are properly structured."""
        point = time_series_data[0]
        assert isinstance(point.tags, dict)
        assert "category" in point.tags
        assert "instance" in point.tags

    def test_time_series_ordering(self, time_series_data):
        """Test time series data is ordered by timestamp."""
        timestamps = [point.timestamp for point in time_series_data]
        assert timestamps == sorted(timestamps)

    def test_time_series_query_by_measurement(self, time_series_data):
        """Test querying by measurement."""
        points = TimeSeriesData.objects.filter(measurement="test_measurement")
        assert points.count() == 5

    def test_time_series_query_by_source(self, time_series_data):
        """Test querying by source."""
        points = TimeSeriesData.objects.filter(source="test_source")
        assert points.count() == 5

    def test_time_series_query_by_tags(self, time_series_data):
        """Test querying by tags."""
        points = TimeSeriesData.objects.filter(tags__category="test")
        assert points.count() == 5

    def test_time_series_query_by_time_range(self, time_series_data):
        """Test querying by time range."""
        start_time = time_series_data[1].timestamp
        end_time = time_series_data[3].timestamp

        points = TimeSeriesData.objects.filter(
            timestamp__gte=start_time,
            timestamp__lte=end_time
        )
        assert points.count() == 3

    def test_write_point_method(self):
        """Test the write_point class method."""
        point_data = {
            "measurement": "cpu_usage",
            "source": "server1",
            "timestamp": timezone.now(),
            "value_float": 75.5,
            "tags": {"host": "web-01", "region": "us-east"}
        }

        point = TimeSeriesData.write_point(**point_data)

        assert point.measurement == "cpu_usage"
        assert point.source == "server1"
        assert point.value_float == 75.5
        assert point.tags["host"] == "web-01"

    def test_query_range_method(self, time_series_data):
        """Test the query_range class method."""
        start_time = time_series_data[0].timestamp
        end_time = time_series_data[-1].timestamp

        results = TimeSeriesData.query_range(
            measurement="test_measurement",
            start_time=start_time,
            end_time=end_time
        )

        assert len(results) == 5
        assert all(point.measurement == "test_measurement" for point in results)


@pytest.mark.django_db
class TestRetryableModelMixin:
    """Test RetryableModelMixin functionality."""

    def test_retry_count_default(self, metric_definition):
        """Test default retry count."""
        assert metric_definition.retry_count == 0

    def test_last_retry_default(self, metric_definition):
        """Test default last retry."""
        assert metric_definition.last_retry is None

    @patch('time.sleep')
    def test_retryable_save_success(self, mock_sleep, metric_definition):
        """Test successful save without retries."""
        # This should not raise an exception
        metric_definition.name = "updated_name"
        metric_definition.save()
        assert metric_definition.name == "updated_name"
        mock_sleep.assert_not_called()

    def test_retry_count_increment(self, metric_definition):
        """Test retry count can be incremented."""
        metric_definition.retry_count = 1
        metric_definition.save()
        assert metric_definition.retry_count == 1

    def test_last_retry_update(self, metric_definition):
        """Test last retry timestamp update."""
        now = timezone.now()
        metric_definition.last_retry = now
        metric_definition.save()
        assert metric_definition.last_retry == now


@pytest.mark.django_db
class TestModelIntegration:
    """Test model interactions and relationships."""

    def test_report_with_metric_definition(self, user, metric_definition):
        """Test report creation with metric definition reference."""
        report = Report.objects.create(
            name="integration_report",
            description="Report with metric",
            report_type="summary",
            status="completed",
            generated_by=user,
            configuration={"metrics": [metric_definition.id]}
        )

        assert metric_definition.id in report.configuration["metrics"]
        assert MetricDefinition.objects.get(id=metric_definition.id) == metric_definition

    def test_cache_with_report_data(self, report):
        """Test caching report data."""
        cache_entry = AnalyticsCache.objects.create(
            cache_key=f"report_{report.id}",
            cache_data=report.data,
            expires_at=timezone.now() + timedelta(hours=1)
        )

        assert cache_entry.cache_data == report.data

    def test_time_series_with_metric_context(self, metric_definition):
        """Test time series data in context of metrics."""
        point = TimeSeriesData.objects.create(
            measurement=metric_definition.name,
            source="analytics_service",
            timestamp=timezone.now(),
            value_float=100.0,
            tags={
                "metric_id": str(metric_definition.id),
                "category": metric_definition.category,
                "unit": metric_definition.unit
            }
        )

        assert point.measurement == metric_definition.name
        assert point.tags["category"] == metric_definition.category
        assert point.tags["unit"] == metric_definition.unit