#!/usr/bin/env python
"""
Simple health check script that can be used as a backup
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


def simple_health_check():
    """Ultra-simple health check that just verifies Django is working"""
    try:
        return JsonResponse(
            {
                "status": "healthy",
                "timestamp": timezone.now().isoformat(),
                "service": "analytics-simple",
                "message": "Basic Django setup working",
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "status": "error",
                "timestamp": timezone.now().isoformat(),
                "error": str(e),
            },
            status=500,
        )


if __name__ == "__main__":
    # Test the simple health check
    try:
        response = simple_health_check()
        print("Simple health check successful!")
        print(f"Response: {response.content.decode()}")
    except Exception as e:
        print(f"Simple health check failed: {e}")
        sys.exit(1)
