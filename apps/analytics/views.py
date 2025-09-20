import io
import json
from datetime import datetime, timedelta
from typing import Dict, Any

from django.http import HttpResponse, FileResponse
from django.template import loader
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, generics
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets

from config.database_retry import atomic_with_retry
from .db_mixins import ServerlessViewMixin
from .models import Report, MetricDefinition, AnalyticsCache
from .serializers import ReportSerializer, ReportCreateSerializer, MetricDefinitionSerializer
from .metric_calculators import MetricCalculatorRegistry
from .data_analysis import DataAnalyzer, ReportGenerator


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
        "features": ["Report Generation", "Metric Calculations", "Data Analysis", "InfluxDB Integration"],
        "data_sources": ["PostgreSQL", "InfluxDB", "Service APIs"],
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
        # Check if this is a test case that explicitly uses a mock template
        import sys

        is_testing = "pytest" in sys.modules or "test" in sys.argv
        template = loader.get_template("analytics/api_home.html")
        return HttpResponse(template.render(context, request))
    except:
        # Fallback to JSON response if template doesn't exist
        return Response(context, status=status.HTTP_200_OK)