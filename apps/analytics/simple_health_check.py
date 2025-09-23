#!/usr/bin/env python
"""
Ultra-simple health check that just returns 200 OK
This can be used as a backup if the main health check is too strict
"""

import os
import sys

# Set Django settings if not already set
if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.http import JsonResponse
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def ultra_simple_health_check(request):
    """Ultra-simple health check that just verifies the service is running"""
    return Response(
        {
            "status": "alive",
            "timestamp": timezone.now().isoformat(),
            "service": "analytics",
            "message": "Service is running",
        }
    )


if __name__ == "__main__":
    # Test the simple health check
    try:
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/health/")
        response = ultra_simple_health_check(request)
        print("Simple health check successful!")
        print(f"Response: {response.data}")
        sys.exit(0)
    except Exception as e:
        print(f"Simple health check failed: {e}")
        sys.exit(1)
