import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta

from apps.analytics.models import MetricDefinition, Report, AnalyticsCache, TimeSeriesData

User = get_user_model()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )


@pytest.fixture
def metric_definition():
    """Create a test metric definition."""
    return MetricDefinition.objects.create(
        name="test_metric",
        description="A test metric for analytics",
        calculation_method="SUM",
        category="performance",
        unit="requests",
        is_active=True
    )


@pytest.fixture
def metric_definition_complex():
    """Create a more complex metric definition."""
    return MetricDefinition.objects.create(
        name="complex_metric",
        description="A complex test metric",
        calculation_method="AVERAGE",
        category="business",
        unit="percentage",
        is_active=True,
        aggregation_period="daily",
        filters={"status": "active"},
        tags={"priority": "high", "team": "analytics"}
    )


@pytest.fixture
def report(user, metric_definition):
    """Create a test report."""
    return Report.objects.create(
        name="test_report",
        description="A test report",
        report_type="summary",
        status="completed",
        generated_by=user,
        configuration={
            "metrics": [metric_definition.id],
            "date_range": "last_7_days"
        },
        data={
            "total_requests": 1000,
            "average_response_time": 250
        }
    )


@pytest.fixture
def pending_report(user):
    """Create a pending report."""
    return Report.objects.create(
        name="pending_report",
        description="A pending test report",
        report_type="detailed",
        status="pending",
        generated_by=user,
        configuration={"metrics": [], "date_range": "last_30_days"}
    )


@pytest.fixture
def analytics_cache():
    """Create a test analytics cache entry."""
    return AnalyticsCache.objects.create(
        cache_key="test_cache_key",
        cache_data={
            "metric_values": [100, 200, 300],
            "timestamps": ["2024-01-01", "2024-01-02", "2024-01-03"]
        },
        expires_at=timezone.now() + timedelta(hours=1)
    )


@pytest.fixture
def expired_cache():
    """Create an expired cache entry."""
    return AnalyticsCache.objects.create(
        cache_key="expired_cache_key",
        cache_data={"old_data": "value"},
        expires_at=timezone.now() - timedelta(hours=1)
    )


@pytest.fixture
def time_series_data():
    """Create test time series data."""
    base_time = timezone.now()
    data_points = []

    for i in range(5):
        point = TimeSeriesData.objects.create(
            measurement="test_measurement",
            source="test_source",
            timestamp=base_time + timedelta(minutes=i),
            value_float=float(i * 10),
            value_int=i * 100,
            tags={"category": "test", "instance": f"server_{i}"}
        )
        data_points.append(point)

    return data_points


@pytest.fixture
def time_series_string_data():
    """Create time series data with string values."""
    return TimeSeriesData.objects.create(
        measurement="status_measurement",
        source="system_monitor",
        timestamp=timezone.now(),
        value_string="healthy",
        tags={"service": "api", "environment": "test"}
    )


@pytest.fixture
def time_series_bool_data():
    """Create time series data with boolean values."""
    return TimeSeriesData.objects.create(
        measurement="alert_measurement",
        source="monitoring_system",
        timestamp=timezone.now(),
        value_bool=True,
        tags={"severity": "high", "type": "threshold"}
    )