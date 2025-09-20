import sys
import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone

from config.database_retry import atomic_with_retry

from .db_mixins import RetryableManager, RetryableModelMixin, TimestampMixin


def get_table_name(base_name):
    """Get table name with or without schema prefix based on test mode."""
    if "test" in sys.argv or "pytest" in sys.modules:
        # SQLite doesn't support schemas, use simple table names for tests
        return base_name
    else:
        # PostgreSQL with analytics schema
        return f"analytics.{base_name}"


class MetricDefinition(RetryableModelMixin, TimestampMixin, models.Model):
    """
    Model representing metric definitions for analytics calculations.
    Maps to the analytics.metric_definitions table.
    GitHub Issue #5: Implementar modelo `MetricDefinition`
    """

    CALCULATION_METHOD_CHOICES = [
        ("sum", "Sum"),
        ("avg", "Average"),
        ("count", "Count"),
        ("percentage", "Percentage"),
        ("ratio", "Ratio"),
        ("growth_rate", "Growth Rate"),
        ("trend", "Trend Analysis"),
        ("correlation", "Correlation"),
        ("standard_deviation", "Standard Deviation"),
        ("min", "Minimum"),
        ("max", "Maximum"),
        ("median", "Median"),
        ("custom", "Custom Formula"),
    ]

    CATEGORY_CHOICES = [
        ("productivity", "Productivity"),
        ("code_quality", "Code Quality"),
        ("performance", "Performance"),
        ("collaboration", "Collaboration"),
        ("time_tracking", "Time Tracking"),
        ("git_activity", "Git Activity"),
        ("deployment", "Deployment"),
        ("security", "Security"),
        ("testing", "Testing"),
        ("documentation", "Documentation"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(help_text="Detailed description of what this metric measures")
    calculation_method = models.CharField(max_length=50, choices=CALCULATION_METHOD_CHOICES)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="productivity")
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON configuration for metric calculation (formulas, filters, etc.)"
    )
    data_sources = models.JSONField(
        default=list,
        blank=True,
        help_text="List of data sources this metric depends on (monitoring, management, etc.)"
    )
    unit = models.CharField(max_length=50, null=True, blank=True, help_text="Unit of measurement (hours, %, count, etc.)")
    is_active = models.BooleanField(default=True)
    requires_ml = models.BooleanField(default=False, help_text="Whether this metric requires ML processing")
    cache_duration = models.IntegerField(default=300, help_text="Cache duration in seconds")

    objects = RetryableManager()

    class Meta:
        db_table = get_table_name("metric_definitions")
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["category"]),
            models.Index(fields=["calculation_method"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.category})"

    @atomic_with_retry()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Report(RetryableModelMixin, TimestampMixin, models.Model):
    """
    Model representing generated reports.
    Maps to the analytics.reports table.
    GitHub Issue #4: Implementar modelo `Report`
    """

    REPORT_TYPE_CHOICES = [
        ("productivity", "Productivity Report"),
        ("code_quality", "Code Quality Report"),
        ("time_tracking", "Time Tracking Report"),
        ("team_performance", "Team Performance Report"),
        ("individual_performance", "Individual Performance Report"),
        ("project_summary", "Project Summary Report"),
        ("git_activity", "Git Activity Report"),
        ("deployment_metrics", "Deployment Metrics Report"),
        ("custom", "Custom Report"),
        ("comparative", "Comparative Analysis"),
        ("trend_analysis", "Trend Analysis"),
        ("anomaly_detection", "Anomaly Detection Report"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("generating", "Generating"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    FORMAT_CHOICES = [
        ("json", "JSON"),
        ("pdf", "PDF"),
        ("csv", "CSV"),
        ("xlsx", "Excel"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=REPORT_TYPE_CHOICES)
    config = models.JSONField(
        default=dict,
        help_text="Report configuration including filters, date ranges, metrics, etc."
    )
    created_by = models.UUIDField(help_text="Reference to auth.users.id")
    company_id = models.UUIDField(null=True, blank=True, help_text="Reference to auth.companies.id")
    team_id = models.UUIDField(null=True, blank=True, help_text="Reference to management.teams.id")
    project_id = models.UUIDField(null=True, blank=True, help_text="Reference to management.projects.id")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default="json")
    generated_at = models.DateTimeField(null=True, blank=True)
    file_path = models.CharField(max_length=500, null=True, blank=True, help_text="Path to generated report file")
    file_size = models.BigIntegerField(null=True, blank=True, help_text="File size in bytes")
    data = models.JSONField(null=True, blank=True, help_text="Report data (for JSON reports)")
    error_message = models.TextField(null=True, blank=True)
    execution_time = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, help_text="Execution time in seconds")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When this report expires")

    objects = RetryableManager()

    class Meta:
        db_table = get_table_name("reports")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_by"]),
            models.Index(fields=["company_id"]),
            models.Index(fields=["team_id"]),
            models.Index(fields=["project_id"]),
            models.Index(fields=["type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.type} ({self.status})"

    @property
    def is_expired(self):
        """Check if report has expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_ready(self):
        """Check if report is ready for download."""
        return self.status == "completed" and not self.is_expired

    def mark_as_generating(self):
        """Mark report as being generated."""
        self.status = "generating"
        self.save()

    def mark_as_completed(self, file_path=None, file_size=None, data=None, execution_time=None):
        """Mark report as completed."""
        self.status = "completed"
        self.generated_at = timezone.now()
        if file_path:
            self.file_path = file_path
        if file_size:
            self.file_size = file_size
        if data:
            self.data = data
        if execution_time:
            self.execution_time = execution_time
        self.save()

    def mark_as_failed(self, error_message):
        """Mark report as failed."""
        self.status = "failed"
        self.error_message = error_message
        self.save()

    @atomic_with_retry()
    def save(self, *args, **kwargs):
        # Set default expiration if not set
        if not self.expires_at and self.status == "completed":
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        super().save(*args, **kwargs)


class AnalyticsCache(RetryableModelMixin, TimestampMixin, models.Model):
    """
    Model for caching analytics calculations and intermediate results.
    Maps to the analytics.analytics_cache table.
    """

    CACHE_TYPE_CHOICES = [
        ("metric_result", "Metric Calculation Result"),
        ("report_data", "Report Data"),
        ("aggregated_data", "Aggregated Data"),
        ("ml_prediction", "ML Prediction Result"),
        ("trend_analysis", "Trend Analysis"),
        ("comparative_data", "Comparative Analysis Data"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cache_key = models.CharField(max_length=255, unique=True, db_index=True)
    cache_type = models.CharField(max_length=50, choices=CACHE_TYPE_CHOICES)
    data = models.JSONField(help_text="Cached data")
    metadata = models.JSONField(default=dict, blank=True, help_text="Cache metadata (source, parameters, etc.)")
    expires_at = models.DateTimeField()
    hit_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(auto_now=True)
    data_size = models.IntegerField(null=True, blank=True, help_text="Size of cached data in bytes")
    source_metric_id = models.UUIDField(null=True, blank=True, help_text="Reference to metric_definitions.id if applicable")

    objects = RetryableManager()

    class Meta:
        db_table = get_table_name("analytics_cache")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cache_key"]),
            models.Index(fields=["cache_type"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["source_metric_id"]),
            models.Index(fields=["last_accessed"]),
        ]

    def __str__(self):
        return f"Cache: {self.cache_key} ({self.cache_type})"

    @property
    def is_expired(self):
        """Check if cache entry has expired."""
        return timezone.now() > self.expires_at

    @property
    def size_mb(self):
        """Get cache size in MB."""
        if self.data_size:
            return round(self.data_size / (1024 * 1024), 2)
        return None

    def increment_hit_count(self):
        """Increment cache hit count."""
        self.hit_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=["hit_count", "last_accessed"])

    @classmethod
    def cleanup_expired(cls):
        """Remove expired cache entries."""
        expired_count = cls.objects.filter(expires_at__lt=timezone.now()).count()
        cls.objects.filter(expires_at__lt=timezone.now()).delete()
        return expired_count

    @classmethod
    def get_cache_stats(cls):
        """Get cache statistics."""
        total_entries = cls.objects.count()
        expired_entries = cls.objects.filter(expires_at__lt=timezone.now()).count()
        total_size = cls.objects.aggregate(
            total_size=models.Sum("data_size")
        )["total_size"] or 0

        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
        }

    @atomic_with_retry()
    def save(self, *args, **kwargs):
        # Calculate data size if not set
        if not self.data_size and self.data:
            import json
            self.data_size = len(json.dumps(self.data).encode('utf-8'))
        super().save(*args, **kwargs)



class AlertRule(RetryableModelMixin, TimestampMixin, models.Model):
    """
    Model for defining alert rules based on metric thresholds.
    """

    CONDITION_CHOICES = [
        ("gt", "Greater than"),
        ("gte", "Greater than or equal"),
        ("lt", "Less than"),
        ("lte", "Less than or equal"),
        ("eq", "Equal to"),
        ("ne", "Not equal to"),
        ("change_gt", "Change greater than"),
        ("change_lt", "Change less than"),
        ("trend_up", "Trending upward"),
        ("trend_down", "Trending downward"),
    ]

    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    metric_definition = models.ForeignKey(
        MetricDefinition,
        on_delete=models.CASCADE,
        related_name="alert_rules",
        db_column="metric_definition_id"
    )
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    threshold_value = models.DecimalField(max_digits=20, decimal_places=6)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="medium")
    is_active = models.BooleanField(default=True)
    notification_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Notification configuration (emails, webhooks, etc.)"
    )
    context_filters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Context filters for when this rule applies"
    )
    cooldown_minutes = models.IntegerField(default=60, help_text="Cooldown period before re-triggering")

    objects = RetryableManager()

    class Meta:
        db_table = get_table_name("alert_rules")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["metric_definition"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["severity"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.metric_definition.name} {self.condition} {self.threshold_value}"

    @atomic_with_retry()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class TimeSeriesData(RetryableModelMixin, models.Model):
    """
    Model for storing time series data that was previously stored in InfluxDB.
    This replaces InfluxDB functionality with PostgreSQL storage.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Measurement identification
    measurement = models.CharField(max_length=255, help_text="Measurement name (e.g., 'code_commits', 'build_duration')")
    source = models.CharField(max_length=255, help_text="Data source (e.g., 'github', 'jenkins', 'jira')")

    # Time dimension
    timestamp = models.DateTimeField(help_text="When the measurement was taken")

    # Value storage
    value_float = models.FloatField(null=True, blank=True, help_text="Numeric value")
    value_int = models.BigIntegerField(null=True, blank=True, help_text="Integer value")
    value_string = models.TextField(null=True, blank=True, help_text="String value")
    value_bool = models.BooleanField(null=True, blank=True, help_text="Boolean value")

    # Metadata and tags
    tags = models.JSONField(default=dict, help_text="Tags as key-value pairs (e.g., {'user': 'john', 'repo': 'myproject'})")
    fields = models.JSONField(default=dict, help_text="Additional field data")

    # Context information
    user_id = models.CharField(max_length=255, null=True, blank=True, help_text="User ID if applicable")
    project_id = models.CharField(max_length=255, null=True, blank=True, help_text="Project ID if applicable")
    team_id = models.CharField(max_length=255, null=True, blank=True, help_text="Team ID if applicable")

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = RetryableManager()

    class Meta:
        db_table = get_table_name("time_series_data")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["measurement", "timestamp"]),
            models.Index(fields=["source", "timestamp"]),
            models.Index(fields=["user_id", "timestamp"]),
            models.Index(fields=["project_id", "timestamp"]),
            models.Index(fields=["team_id", "timestamp"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["measurement", "source"]),
        ]

    def __str__(self):
        return f"{self.measurement} - {self.source} - {self.timestamp}"

    @property
    def value(self):
        """Get the primary value regardless of type"""
        if self.value_float is not None:
            return self.value_float
        elif self.value_int is not None:
            return self.value_int
        elif self.value_string is not None:
            return self.value_string
        elif self.value_bool is not None:
            return self.value_bool
        return None

    @classmethod
    def write_point(cls, measurement, source, value, timestamp=None, tags=None, fields=None,
                   user_id=None, project_id=None, team_id=None):
        """
        Write a time series data point (replaces InfluxDB write functionality)
        """
        if timestamp is None:
            timestamp = timezone.now()

        data = {
            'measurement': measurement,
            'source': source,
            'timestamp': timestamp,
            'tags': tags or {},
            'fields': fields or {},
            'user_id': user_id,
            'project_id': project_id,
            'team_id': team_id,
        }

        # Set appropriate value field based on type
        if isinstance(value, float):
            data['value_float'] = value
        elif isinstance(value, int):
            data['value_int'] = value
        elif isinstance(value, bool):
            data['value_bool'] = value
        else:
            data['value_string'] = str(value)

        return cls.objects.create(**data)

    @classmethod
    def query_range(cls, measurement, start_time, end_time, source=None, user_id=None,
                   project_id=None, team_id=None, tags=None):
        """
        Query time series data for a time range (replaces InfluxDB query functionality)
        """
        queryset = cls.objects.filter(
            measurement=measurement,
            timestamp__gte=start_time,
            timestamp__lte=end_time
        )

        if source:
            queryset = queryset.filter(source=source)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if team_id:
            queryset = queryset.filter(team_id=team_id)

        # Filter by tags if provided
        if tags:
            for key, value in tags.items():
                queryset = queryset.filter(tags__contains={key: value})

        return queryset.order_by('timestamp')


class MetricSnapshot(RetryableModelMixin, models.Model):
    """
    Model for storing periodic snapshots of calculated metrics.
    This provides efficient querying for dashboard and reporting.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Metric identification
    metric_definition = models.ForeignKey(
        MetricDefinition,
        on_delete=models.CASCADE,
        related_name='snapshots'
    )

    # Snapshot metadata
    snapshot_time = models.DateTimeField(help_text="When this snapshot was taken")
    period_start = models.DateTimeField(help_text="Start of the measurement period")
    period_end = models.DateTimeField(help_text="End of the measurement period")

    # Calculated values
    value = models.DecimalField(max_digits=20, decimal_places=6, help_text="Calculated metric value")
    raw_data_count = models.IntegerField(help_text="Number of data points used in calculation")

    # Context
    user_id = models.CharField(max_length=255, null=True, blank=True)
    project_id = models.CharField(max_length=255, null=True, blank=True)
    team_id = models.CharField(max_length=255, null=True, blank=True)

    # Additional metadata
    calculation_metadata = models.JSONField(default=dict, help_text="Additional calculation details")
    confidence_score = models.FloatField(null=True, blank=True, help_text="Confidence in the calculation (0-1)")

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)

    objects = RetryableManager()

    class Meta:
        db_table = get_table_name("metric_snapshots")
        ordering = ["-snapshot_time"]
        indexes = [
            models.Index(fields=["metric_definition", "snapshot_time"]),
            models.Index(fields=["user_id", "snapshot_time"]),
            models.Index(fields=["project_id", "snapshot_time"]),
            models.Index(fields=["team_id", "snapshot_time"]),
            models.Index(fields=["period_start", "period_end"]),
        ]
        unique_together = [
            ["metric_definition", "snapshot_time", "user_id", "project_id", "team_id"]
        ]

    def __str__(self):
        return f"{self.metric_definition.name} - {self.snapshot_time} - {self.value}"