import io
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from django.http import FileResponse, HttpResponse
from django.template import loader
from django.utils import timezone
from django.utils.decorators import method_decorator

from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from config.database_retry import atomic_with_retry

from .data_analysis import ReportGenerator
from .db_mixins import ServerlessViewMixin
from .metric_calculators import MetricCalculatorRegistry
from .models import AnalyticsCache, MetricDefinition, Report
from .serializers import (
    MetricDefinitionSerializer,
    ReportCreateSerializer,
    ReportExportSerializer,
    ReportSerializer,
)

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_home(request):
    """
    API Home page showing main navigation routes and service links.
    """
    # Define the main navigation routes
    main_routes = [
        {
            "title": "API Documentation",
            "description": "Interactive API documentation with live testing",
            "url": request.build_absolute_uri("/api/docs/"),
            "icon": "📖",
            "category": "documentation",
        },
        {
            "title": "ReDoc Documentation",
            "description": "Clean, three-panel OpenAPI documentation",
            "url": request.build_absolute_uri("/api/redoc/"),
            "icon": "📚",
            "category": "documentation",
        },
        {
            "title": "OpenAPI Schema",
            "description": "Raw OpenAPI specification in JSON format",
            "url": request.build_absolute_uri("/api/schema/"),
            "icon": "⚙️",
            "category": "documentation",
        },
        {
            "title": "Admin Interface",
            "description": "Django admin panel for analytics and system management",
            "url": request.build_absolute_uri("/admin/"),
            "icon": "🔧",
            "category": "admin",
        },
        {
            "title": "Health Check",
            "description": "Service health status and monitoring",
            "url": request.build_absolute_uri("/health/"),
            "icon": "❤️",
            "category": "monitoring",
        },
    ]

    # Quick stats about the service
    service_info = {
        "endpoints": 12,
        "features": [
            "Report Generation",
            "Metric Calculations",
            "Data Analysis",
            "Time Series Storage",
        ],
        "data_sources": ["PostgreSQL", "Service APIs", "Time Series Data"],
        "export_formats": ["PDF", "Excel", "CSV", "JSON"],
        "status": "Operational",
    }

    context = {
        "main_routes": main_routes,
        "service_info": service_info,
        "api_title": "SyncScope Analytics Service",
        "api_version": "1.0.0",
        "api_description": "Analytics and reporting service for SyncScope platform with advanced data processing capabilities",
        "base_url": request.build_absolute_uri("/"),
    }

    # Check if JSON format is explicitly requested
    if request.GET.get("format") == "json":
        return Response(context, status=status.HTTP_200_OK)

    # Try to render HTML template first, fallback to JSON
    try:
        template = loader.get_template("analytics/api_home.html")
        return HttpResponse(template.render(context, request))
    except Exception as e:
        logger.error(f"Failed to render HTML template: {e}")
        # Fallback to JSON response if template doesn't exist
        return Response(context, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        tags=["Reports"],
        summary="List reports",
        description="Get a list of reports created by the current user or all reports if admin.",
        responses={200: ReportSerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Reports"],
        summary="Create new report",
        description="Create a new report with specified type and configuration.",
        request=ReportCreateSerializer,
        responses={
            201: ReportSerializer,
            400: "ErrorResponseSerializer",
        },
    ),
    retrieve=extend_schema(
        tags=["Reports"],
        summary="Get report details",
        description="Retrieve details of a specific report.",
        responses={200: ReportSerializer, 404: "ErrorResponseSerializer"},
    ),
    update=extend_schema(
        tags=["Reports"],
        summary="Update report",
        description="Update a specific report.",
        request=ReportSerializer,
        responses={200: ReportSerializer, 404: "ErrorResponseSerializer"},
    ),
    partial_update=extend_schema(
        tags=["Reports"],
        summary="Partially update report",
        description="Partially update a specific report.",
        request=ReportSerializer,
        responses={200: ReportSerializer, 404: "ErrorResponseSerializer"},
    ),
    destroy=extend_schema(
        tags=["Reports"],
        summary="Delete report",
        description="Delete a specific report.",
        responses={204: None, 404: "ErrorResponseSerializer"},
    ),
)
@method_decorator(ratelimit(key="user", rate="10/m", method="POST"), name="create")
class ReportViewSet(ServerlessViewMixin, viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter reports based on user permissions"""
        user = self.request.user
        if hasattr(user, "role") and user.role == "admin":
            return Report.objects.all()
        return Report.objects.filter(created_by=user.id)

    def get_serializer_class(self):
        if self.action == "create":
            return ReportCreateSerializer
        return ReportSerializer

    @atomic_with_retry()
    def perform_create(self, serializer):
        """Create report and trigger generation"""
        report = serializer.save(created_by=self.request.user.id, status="pending")

        # Trigger async report generation
        self._generate_report_async(report)

    def _generate_report_async(self, report):
        """Generate report data asynchronously"""
        try:
            # Create report generator
            generator = ReportGenerator()

            # Generate report based on type
            if report.type == "productivity":
                report.data = generator.generate_productivity_report(report.config)
            elif report.type == "code_quality":
                report.data = generator.generate_code_quality_report(report.config)
            elif (
                report.type == "team_collaboration" or report.type == "team_performance"
            ):
                report.data = generator.generate_collaboration_report(report.config)
            elif report.type == "custom":
                report.data = generator.generate_custom_report(report.config)
            else:
                report.data = {"error": f"Unknown report type: {report.type}"}
                report.status = "failed"
                report.save(update_fields=["status", "data"])
                return

            # Mark as completed
            report.status = "completed"
            report.generated_at = timezone.now()
            report.save(update_fields=["status", "data", "generated_at"])

        except Exception as e:
            logger.error(f"Report generation failed for {report.id}: {e}")
            report.status = "failed"
            report.data = {"error": str(e)}
            report.save(update_fields=["status", "data"])

    @extend_schema(
        tags=["Export"],
        summary="Export report",
        description="Export report in specified format (PDF, Excel, CSV, JSON).",
        request=ReportExportSerializer,
        responses={
            200: {"type": "string", "format": "binary", "description": "Report file"},
            404: "ErrorResponseSerializer",
            400: "ErrorResponseSerializer",
        },
    )
    @action(detail=True, methods=["post"])
    def export(self, request, pk=None):
        """Export report in specified format"""
        report = self.get_object()

        if report.status != "completed":
            return Response(
                {"error": "Report is not ready for export"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReportExportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        export_format = serializer.validated_data["format"]
        include_charts = serializer.validated_data["include_charts"]
        detailed = serializer.validated_data["detailed"]

        try:
            # Create report generator for export
            generator = ReportGenerator()

            # Generate export file
            file_data, content_type, filename = generator.export_report(
                report, export_format, include_charts, detailed
            )

            # Return file response
            response = HttpResponse(file_data, content_type=content_type)
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            logger.error(f"Report export failed for {report.id}: {e}")
            return Response(
                {"error": f"Export failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        tags=["Reports"],
        summary="Regenerate report",
        description="Regenerate report data with current metrics.",
        responses={200: ReportSerializer, 404: "ErrorResponseSerializer"},
    )
    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """Regenerate report with fresh data"""
        report = self.get_object()

        # Reset report status
        report.status = "pending"
        report.data = None
        report.generated_at = None
        report.save(update_fields=["status", "data", "generated_at"])

        # Trigger regeneration
        self._generate_report_async(report)

        return Response(
            {"message": "Report regeneration started", "report_id": report.id},
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    list=extend_schema(
        tags=["Metrics"],
        summary="List metric definitions",
        description="Get available metric definitions for report generation.",
        responses={200: MetricDefinitionSerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Metrics"],
        summary="Create metric definition",
        description="Create a new metric definition for calculations.",
        request=MetricDefinitionSerializer,
        responses={201: MetricDefinitionSerializer, 400: "ErrorResponseSerializer"},
    ),
    retrieve=extend_schema(
        tags=["Metrics"],
        summary="Get metric definition details",
        description="Retrieve details of a specific metric definition.",
        responses={200: MetricDefinitionSerializer, 404: "ErrorResponseSerializer"},
    ),
    update=extend_schema(
        tags=["Metrics"],
        summary="Update metric definition",
        description="Update a specific metric definition.",
        request=MetricDefinitionSerializer,
        responses={200: MetricDefinitionSerializer, 404: "ErrorResponseSerializer"},
    ),
    partial_update=extend_schema(
        tags=["Metrics"],
        summary="Partially update metric definition",
        description="Partially update a specific metric definition.",
        request=MetricDefinitionSerializer,
        responses={200: MetricDefinitionSerializer, 404: "ErrorResponseSerializer"},
    ),
    destroy=extend_schema(
        tags=["Metrics"],
        summary="Delete metric definition",
        description="Delete a specific metric definition.",
        responses={204: None, 404: "ErrorResponseSerializer"},
    ),
)
class MetricDefinitionViewSet(ServerlessViewMixin, viewsets.ModelViewSet):
    queryset = MetricDefinition.objects.filter(is_active=True)
    serializer_class = MetricDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter active metrics"""
        return MetricDefinition.objects.filter(is_active=True).order_by("name")


@extend_schema(
    tags=["Analytics"],
    summary="Calculate metric",
    description="Calculate a specific metric with provided context data.",
    request="MetricCalculationSerializer",
    responses={
        200: {"type": "object", "description": "Metric calculation result"},
        400: "ErrorResponseSerializer",
        404: "ErrorResponseSerializer",
    },
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@ratelimit(key="user", rate="30/m", method="POST")
def calculate_metric(request):
    """Calculate a specific metric"""
    from .serializers import MetricCalculationSerializer

    serializer = MetricCalculationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    metric_name = serializer.validated_data["metric_name"]
    context = serializer.validated_data["context"]
    cache_duration = serializer.validated_data["cache_duration"]

    try:
        # Check cache first
        cache_key = f"metric_{metric_name}_{hash(str(context))}"
        cached_result = AnalyticsCache.get_cached_data(cache_key)

        if cached_result:
            return Response(
                {
                    "metric": metric_name,
                    "result": cached_result,
                    "cached": True,
                    "calculated_at": timezone.now(),
                }
            )

        # Calculate metric using the registry
        registry = MetricCalculatorRegistry()
        calculator = registry.get_calculator(metric_name)

        if not calculator:
            return Response(
                {"error": f"Metric calculator '{metric_name}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Calculate the metric
        result = calculator.calculate(context)

        # Cache the result
        AnalyticsCache.cache_data(cache_key, result, cache_duration)

        return Response(
            {
                "metric": metric_name,
                "result": result,
                "cached": False,
                "calculated_at": timezone.now(),
            }
        )

    except Exception as e:
        return Response(
            {"error": f"Metric calculation failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    tags=["Analytics"],
    summary="Get analytics dashboard data",
    description="Get aggregated analytics data for dashboard display.",
    responses={
        200: {"type": "object", "description": "Dashboard analytics data"},
        400: "ErrorResponseSerializer",
    },
)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def analytics_dashboard(request):
    """Get dashboard analytics data"""
    try:
        # Get query parameters
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if not start_date or not end_date:
            # Default to last 30 days
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        context = {
            "user_id": request.user.id,
            "start_date": start_date,
            "end_date": end_date,
            "dashboard": True,
        }

        # Calculate key metrics
        calculator_registry = MetricCalculatorRegistry()

        dashboard_data = {
            "period": {"start_date": start_date, "end_date": end_date},
            "metrics": {},
            "charts": {},
            "summary": {},
        }

        # Get productivity metrics
        productivity_calc = calculator_registry.get_calculator("productivity")
        if productivity_calc:
            dashboard_data["metrics"]["productivity"] = productivity_calc.calculate(
                context
            )

        # Get code quality metrics
        code_quality_calc = calculator_registry.get_calculator("code_quality")
        if code_quality_calc:
            dashboard_data["metrics"]["code_quality"] = code_quality_calc.calculate(
                context
            )

        # Get team collaboration metrics
        collaboration_calc = calculator_registry.get_calculator("team_collaboration")
        if collaboration_calc:
            dashboard_data["metrics"]["collaboration"] = collaboration_calc.calculate(
                context
            )

        return Response(dashboard_data)

    except Exception as e:
        return Response(
            {"error": f"Dashboard data generation failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
