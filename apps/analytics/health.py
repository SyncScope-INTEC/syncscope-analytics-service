"""
Health check functions for SyncScope Analytics Service
"""

import logging
from datetime import datetime
from typing import Any, Dict

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Health"],
    summary="Health check endpoint",
    description="Check the health status of the analytics service including database, Redis, and external services connectivity.",
    responses={
        200: {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["healthy", "unhealthy"]},
                "timestamp": {"type": "string", "format": "date-time"},
                "database": {"type": "boolean"},
                "redis": {"type": "boolean"},
            },
        },
        503: {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "error": {"type": "string"},
            },
        },
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Comprehensive health check endpoint
    """
    try:
        # Get health status for core components only
        db_healthy = check_database_connection()
        redis_healthy = check_redis_connection()

        # Determine overall status
        all_healthy = db_healthy and redis_healthy

        status_code = (
            status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        response_data = {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": timezone.now().isoformat(),
            "database": db_healthy,
            "redis": redis_healthy,
        }

        return JsonResponse(response_data, status=status_code)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse(
            {
                "status": "unhealthy",
                "timestamp": timezone.now().isoformat(),
                "error": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def check_database_connection() -> bool:
    """Check database connectivity"""
    try:
        connection.ensure_connection()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def check_redis_connection() -> bool:
    """Check Redis connectivity with retry logic"""
    from django.conf import settings

    # Log Redis configuration for debugging
    redis_url = getattr(settings, "REDIS_URL", None)
    cache_location = settings.CACHES["default"].get("LOCATION", "N/A (DummyCache)")
    logger.info(
        f"Redis health check - REDIS_URL: {redis_url}, Cache location: {cache_location}"
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Try to set and get a test value
            cache.set("health_check", "ok", timeout=10)
            result = cache.get("health_check")
            if result == "ok":
                return True
            else:
                logger.warning(
                    f"Redis health check attempt {attempt + 1}: Value mismatch - expected 'ok', got '{result}'"
                )
        except Exception as e:
            logger.error(f"Redis health check attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                return False
            # Brief delay before retry
            import time

            time.sleep(0.5)

    return False
