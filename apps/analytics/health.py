"""
Health check functions for SyncScope Analytics Service
"""

import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from config.database_retry import retry_on_database_error

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Health"],
    summary="Health check endpoint",
    description="Check the health status of the service including database and cache connections.",
    responses={
        200: {
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "healthy"},
                "timestamp": {"type": "string", "example": "2024-01-01T12:00:00Z"},
                "version": {"type": "string", "example": "1.0.0"},
                "services": {
                    "type": "object",
                    "properties": {
                        "database": {"type": "string", "example": "healthy"},
                        "cache": {"type": "string", "example": "healthy"},
                    },
                },
            },
        },
        503: {
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "unhealthy"},
                "errors": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for monitoring and load balancers.
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": getattr(settings, "VERSION", "1.0.0"),
        "services": {},
    }

    errors = []

    # Check database connection with retry logic
    try:
        if check_database_connection():
            health_status["services"]["database"] = "healthy"
        else:
            health_status["services"]["database"] = "unhealthy"
            errors.append("Database: Connection failed after retries")
    except Exception as e:
        health_status["services"]["database"] = "unhealthy"
        errors.append(f"Database: {str(e)}")

    # Check cache/Redis connection
    try:
        if check_cache_connection():
            health_status["services"]["cache"] = "healthy"
        else:
            health_status["services"]["cache"] = "unhealthy"
            errors.append("Cache: Connection failed")
    except Exception as e:
        health_status["services"]["cache"] = "unhealthy"
        errors.append(f"Cache: {str(e)}")

    # Determine overall status
    if errors:
        health_status["status"] = "unhealthy"
        health_status["errors"] = errors
        return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(health_status, status=status.HTTP_200_OK)


@retry_on_database_error(max_retries=2)
def check_database_connection() -> bool:
    """Check database connectivity with retry logic"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return result is not None
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def check_cache_connection() -> bool:
    """Check cache connectivity"""
    try:
        # Check if cache is configured
        cache_backend = settings.CACHES["default"]["BACKEND"]

        # If using DummyCache, consider it "healthy" since it's intentional
        if "dummy" in cache_backend.lower():
            logger.info("Using DummyCache backend - considering cache healthy")
            return True

        # Try to set and get a test value
        cache.set("health_check", "ok", timeout=10)
        result = cache.get("health_check")
        if result == "ok":
            return True
        else:
            logger.warning(
                f"Cache health check: Value mismatch - expected 'ok', got '{result}'"
            )
            return False

    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return False


@extend_schema(
    tags=["Health"],
    summary="Readiness check endpoint",
    description="Check if the service is ready to accept requests.",
    responses={
        200: {
            "type": "object",
            "properties": {"status": {"type": "string", "example": "ready"}},
        },
        503: {
            "type": "object",
            "properties": {"status": {"type": "string", "example": "not ready"}},
        },
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    Readiness check endpoint for Kubernetes/Railway deployments.
    """
    try:
        # Database check with retry logic
        if check_database_connection():
            return Response({"status": "ready"}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"status": "not ready"}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    except Exception:
        return Response(
            {"status": "not ready"}, status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@extend_schema(
    tags=["Health"],
    summary="Liveness check endpoint",
    description="Check if the service is alive (basic endpoint for load balancers).",
    responses={
        200: {
            "type": "object",
            "properties": {"status": {"type": "string", "example": "alive"}},
        }
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def liveness_check(request):
    """
    Simple liveness check - just returns 200 if the service is running.
    """
    return Response({"status": "alive"}, status=status.HTTP_200_OK)
