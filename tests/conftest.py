from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

import pytest

from apps.analytics.models import (
    AnalyticsCache,
    MetricDefinition,
    Report,
    TimeSeriesData,
)

User = get_user_model()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def metric_definition():
    """Create a test metric definition."""
    return MetricDefinition.objects.create(
        name="test_metric",
        description="A test metric for analytics",
        calculation_method="sum",
        category="performance",
        unit="requests",
        is_active=True,
    )


@pytest.fixture
def metric_definition_complex():
    """Create a more complex metric definition."""
    return MetricDefinition.objects.create(
        name="complex_metric",
        description="A complex test metric",
        calculation_method="avg",
        category="performance",
        unit="percentage",
        is_active=True,
        parameters={
            "aggregation_period": "daily",
            "filters": {"status": "active"},
            "tags": {"priority": "high", "team": "analytics"},
        },
        data_sources=["monitoring", "management"],
    )


@pytest.fixture
def report(user, metric_definition):
    """Create a test report."""
    return Report.objects.create(
        name="test_report",
        type="custom",
        status="completed",
        created_by=user.id if hasattr(user, "id") else user,
        config={"metrics": [str(metric_definition.id)], "date_range": "last_7_days"},
        data={"total_requests": 1000, "average_response_time": 250},
    )


@pytest.fixture
def pending_report(user):
    """Create a pending report."""
    return Report.objects.create(
        name="pending_report",
        type="custom",
        status="pending",
        created_by=user.id if hasattr(user, "id") else user,
        config={"metrics": [], "date_range": "last_30_days"},
    )


@pytest.fixture
def analytics_cache():
    """Create a test analytics cache entry."""
    return AnalyticsCache.objects.create(
        cache_key="test_cache_key",
        cache_type="metric_result",
        data={
            "metric_values": [100, 200, 300],
            "timestamps": ["2024-01-01", "2024-01-02", "2024-01-03"],
        },
        expires_at=timezone.now() + timedelta(hours=1),
    )


@pytest.fixture
def expired_cache():
    """Create an expired cache entry."""
    return AnalyticsCache.objects.create(
        cache_key="expired_cache_key",
        cache_type="metric_result",
        data={"old_data": "value"},
        expires_at=timezone.now() - timedelta(hours=1),
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
            tags={"category": "test", "instance": f"server_{i}"},
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
        tags={"service": "api", "environment": "test"},
    )


@pytest.fixture
def time_series_bool_data():
    """Create time series data with boolean values."""
    return TimeSeriesData.objects.create(
        measurement="alert_measurement",
        source="monitoring_system",
        timestamp=timezone.now(),
        value_bool=True,
        tags={"severity": "high", "type": "threshold"},
    )
