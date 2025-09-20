from rest_framework import serializers
from .models import Report, MetricDefinition, AnalyticsCache


class MetricDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricDefinition
        fields = [
            'id', 'name', 'description', 'calculation_method', 'parameters',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            'id', 'name', 'type', 'config', 'created_by', 'status',
            'generated_at', 'data', 'file_path', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'generated_at', 'data', 'file_path']


class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['name', 'type', 'config']

    def validate_type(self, value):
        """Validate report type is supported"""
        valid_types = [choice[0] for choice in Report.REPORT_TYPE_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid report type. Must be one of: {valid_types}")
        return value

    def validate_config(self, value):
        """Validate report configuration"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Config must be a JSON object")

        # Validate required fields based on report type
        report_type = self.initial_data.get('type')
        if report_type == 'productivity':
            required_fields = ['start_date', 'end_date']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(f"Config must include '{field}' for productivity reports")

        return value


class ReportExportSerializer(serializers.Serializer):
    format = serializers.ChoiceField(
        choices=['pdf', 'excel', 'csv', 'json'],
        default='pdf',
        help_text="Export format for the report"
    )
    include_charts = serializers.BooleanField(
        default=True,
        help_text="Include charts and visualizations in PDF/Excel exports"
    )
    detailed = serializers.BooleanField(
        default=False,
        help_text="Include detailed breakdown and raw data"
    )


class AnalyticsCacheSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsCache
        fields = [
            'id', 'cache_key', 'cache_type', 'data', 'expires_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MetricCalculationSerializer(serializers.Serializer):
    metric_name = serializers.CharField(help_text="Name of the metric to calculate")
    context = serializers.JSONField(help_text="Context data for metric calculation")
    cache_duration = serializers.IntegerField(
        default=3600,
        help_text="Cache duration in seconds (default: 1 hour)"
    )


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField(help_text="Error message")
    details = serializers.JSONField(required=False, help_text="Additional error details")


class ReportGenerationResponseSerializer(serializers.Serializer):
    message = serializers.CharField(help_text="Success message")
    report_id = serializers.UUIDField(help_text="Generated report ID")
    status = serializers.CharField(help_text="Report generation status")
    estimated_completion = serializers.DateTimeField(
        required=False,
        help_text="Estimated completion time for async reports"
    )