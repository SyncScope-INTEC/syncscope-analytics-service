"""
Health check functions for SyncScope Analytics Service
"""
import logging
from datetime import datetime
from typing import Dict, Any

from django.db import connection
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from drf_spectacular.utils import extend_schema
import requests

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
                "external_services": {
                    "type": "object",
                    "properties": {
                        "auth_service": {"type": "boolean"},
                        "monitoring_service": {"type": "boolean"},
                        "management_service": {"type": "boolean"}
                    }
                }
            }
        },
        503: {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "error": {"type": "string"}
            }
        }
    }
)
@api_view(['GET'])
def health_check(request):
    """
    Comprehensive health check endpoint
    """
    try:
        # Get health status for all components
        db_healthy = check_database_connection()
        redis_healthy = check_redis_connection()
        external_services = check_external_services()

        # Determine overall status
        all_healthy = (
            db_healthy and
            redis_healthy and
            all(external_services.values())
        )

        status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

        response_data = {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": timezone.now().isoformat(),
            "database": db_healthy,
            "redis": redis_healthy,
            "external_services": external_services,
        }

        return JsonResponse(response_data, status=status_code)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse(
            {
                "status": "unhealthy",
                "timestamp": timezone.now().isoformat(),
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
    """Check Redis connectivity"""
    try:
        # Try to set and get a test value
        cache.set('health_check', 'ok', timeout=10)
        return cache.get('health_check') == 'ok'
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False



def check_external_services() -> Dict[str, bool]:
    """Check external service connectivity"""
    import os

    services = {
        'auth_service': os.getenv('AUTH_SERVICE_URL', 'http://localhost:8001'),
        'monitoring_service': os.getenv('MONITORING_SERVICE_URL', 'http://localhost:8002'),
        'management_service': os.getenv('MANAGEMENT_SERVICE_URL', 'http://localhost:8003'),
    }

    results = {}

    for service_name, service_url in services.items():
        try:
            # Try to reach the health endpoint of each service
            health_url = f"{service_url.rstrip('/')}/health/"
            response = requests.get(health_url, timeout=5)
            results[service_name] = response.status_code == 200
        except Exception as e:
            logger.warning(f"External service {service_name} health check failed: {e}")
            results[service_name] = False

    return results