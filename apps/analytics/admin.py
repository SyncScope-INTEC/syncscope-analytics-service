"""
Django admin configuration for Analytics Service models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    MetricDefinition,
    Report,
    AnalyticsCache,
    AlertRule,
    TimeSeriesData,
    MetricSnapshot,
)


@admin.register(MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    """Admin interface for MetricDefinition model."""

    list_display = [
        "name",
        "category",
        "calculation_method",
        "unit",
        "is_active",
        "requires_ml",
        "cache_duration",
        "created_at",
    ]
    list_filter = [
        "category",
        "calculation_method",
        "is_active",
        "requires_ml",
        "created_at",
    ]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["category", "name"]

    fieldsets = (
        (None, {
            "fields": ("id", "name", "description", "category")
        }),
        ("Calculation Settings", {
            "fields": ("calculation_method", "parameters", "unit", "cache_duration")
        }),
        ("Configuration", {
            "fields": ("data_sources", "is_active", "requires_ml")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("category", "name")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Admin interface for Report model."""

    list_display = [
        "name",
        "type",
        "status",
        "created_by_info",
        "team_info",
        "project_info",
        "created_at",
        "expires_at",
    ]
    list_filter = [
        "type",
        "status",
        "created_at",
        "expires_at",
    ]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_at", "updated_at", "file_size"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {
            "fields": ("id", "name", "description", "type", "status")
        }),
        ("Scope", {
            "fields": ("created_by", "company_id", "team_id", "project_id")
        }),
        ("Content", {
            "fields": ("parameters", "generated_data", "file_path", "file_size")
        }),
        ("Schedule", {
            "fields": ("created_at", "expires_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def created_by_info(self, obj):
        if obj.created_by:
            return f"User {obj.created_by}"
        return "System"
    created_by_info.short_description = "Created By"

    def team_info(self, obj):
        if obj.team_id:
            return f"Team {obj.team_id}"
        return "-"
    team_info.short_description = "Team"

    def project_info(self, obj):
        if obj.project_id:
            return f"Project {obj.project_id}"
        return "-"
    project_info.short_description = "Project"


@admin.register(AnalyticsCache)
class AnalyticsCacheAdmin(admin.ModelAdmin):
    """Admin interface for AnalyticsCache model."""

    list_display = [
        "cache_key",
        "cache_type",
        "source_metric",
        "expires_at",
        "last_accessed",
        "hit_count",
        "created_at",
    ]
    list_filter = [
        "cache_type",
        "expires_at",
        "created_at",
        "last_accessed",
    ]
    search_fields = ["cache_key", "source_metric"]
    readonly_fields = ["id", "created_at", "updated_at", "last_accessed", "hit_count"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {
            "fields": ("id", "cache_key", "cache_type", "source_metric")
        }),
        ("Data", {
            "fields": ("cached_data", "metadata")
        }),
        ("Statistics", {
            "fields": ("hit_count", "last_accessed", "expires_at")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-created_at")


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    """Admin interface for AlertRule model."""

    list_display = [
        "name",
        "metric",
        "condition",
        "threshold",
        "severity",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "severity",
        "condition",
        "is_active",
        "created_at",
    ]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["severity", "name"]

    fieldsets = (
        (None, {
            "fields": ("id", "name", "description", "metric")
        }),
        ("Alert Conditions", {
            "fields": ("condition", "threshold", "severity")
        }),
        ("Configuration", {
            "fields": ("notification_channels", "is_active")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(TimeSeriesData)
class TimeSeriesDataAdmin(admin.ModelAdmin):
    """Admin interface for TimeSeriesData model."""

    list_display = [
        "measurement",
        "source",
        "user_id",
        "project_id",
        "team_id",
        "timestamp",
        "value",
    ]
    list_filter = [
        "measurement",
        "source",
        "timestamp",
    ]
    search_fields = ["measurement", "source"]
    readonly_fields = ["id"]
    ordering = ["-timestamp"]

    fieldsets = (
        (None, {
            "fields": ("id", "measurement", "source", "timestamp")
        }),
        ("Scope", {
            "fields": ("user_id", "project_id", "team_id")
        }),
        ("Data", {
            "fields": ("value", "tags", "metadata")
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-timestamp")


@admin.register(MetricSnapshot)
class MetricSnapshotAdmin(admin.ModelAdmin):
    """Admin interface for MetricSnapshot model."""

    list_display = [
        "metric",
        "user_id",
        "project_id",
        "team_id",
        "period_start",
        "period_end",
        "value",
        "calculated_at",
    ]
    list_filter = [
        "calculated_at",
        "period_start",
        "period_end",
    ]
    search_fields = ["metric__name"]
    readonly_fields = ["id", "calculated_at"]
    ordering = ["-calculated_at"]

    fieldsets = (
        (None, {
            "fields": ("id", "metric", "calculated_at")
        }),
        ("Scope", {
            "fields": ("user_id", "project_id", "team_id")
        }),
        ("Period", {
            "fields": ("period_start", "period_end")
        }),
        ("Result", {
            "fields": ("value", "unit", "metadata", "data_points")
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("metric").order_by("-calculated_at")


# Customize admin site headers
admin.site.site_header = "SyncScope Analytics Administration"
admin.site.site_title = "Analytics Admin"
admin.site.index_title = "Analytics Service Management"