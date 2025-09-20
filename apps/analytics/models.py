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


class MetricSnapshot(RetryableModelMixin, TimestampMixin, models.Model):
    """
    Model for storing metric snapshots at specific points in time.
    Used for tracking metric values over time and trend analysis.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metric_definition = models.ForeignKey(
        MetricDefinition,
        on_delete=models.CASCADE,
        related_name="snapshots",
        db_column="metric_definition_id"
    )
    value = models.DecimalField(max_digits=20, decimal_places=6)
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Context data (user_id, team_id, project_id, etc.)"
    )
    calculation_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadata about how this value was calculated"
    )
    snapshot_date = models.DateTimeField(default=timezone.now)
    data_period_start = models.DateTimeField(null=True, blank=True)
    data_period_end = models.DateTimeField(null=True, blank=True)

    objects = RetryableManager()

    class Meta:
        db_table = get_table_name("metric_snapshots")
        ordering = ["-snapshot_date"]
        indexes = [
            models.Index(fields=["metric_definition", "snapshot_date"]),
            models.Index(fields=["snapshot_date"]),
            models.Index(fields=["data_period_start", "data_period_end"]),
        ]

    def __str__(self):
        return f"{self.metric_definition.name}: {self.value} at {self.snapshot_date}"

    @atomic_with_retry()
    def save(self, *args, **kwargs):
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