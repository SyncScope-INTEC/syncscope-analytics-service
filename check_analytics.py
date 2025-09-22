#!/usr/bin/env python
"""
Helper script to check analytics dependencies with proper Django configuration.
This ensures Django is properly configured before importing analytics modules.
"""

import os
import sys

# Set up Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()


def test_data_analysis_dependencies():
    """Test data analysis dependencies"""
    try:
        import apps.analytics.data_analysis

        print("[OK] Data analysis dependencies working")
        return True
    except Exception as e:
        print(f"[FAIL] Data analysis dependencies failed: {e}")
        return False


def test_metric_calculators():
    """Test metric calculators"""
    try:
        import apps.analytics.metric_calculators

        print("[OK] Metric calculators working")
        return True
    except Exception as e:
        print(f"[FAIL] Metric calculators failed: {e}")
        return False


def test_service_integration():
    """Test service integration"""
    try:
        import apps.analytics.service_integration

        print("[OK] Service integration working")
        return True
    except Exception as e:
        print(f"[FAIL] Service integration failed: {e}")
        return False


def test_models():
    """Test models"""
    try:
        import apps.analytics.models

        print("[OK] Models working")
        return True
    except Exception as e:
        print(f"[FAIL] Models failed: {e}")
        return False


def main():
    """Run all analytics checks"""
    print("Testing analytics service components...")

    tests = [
        test_data_analysis_dependencies,
        test_metric_calculators,
        test_service_integration,
        test_models,
    ]

    results = []
    for test in tests:
        results.append(test())

    if all(results):
        print("\n[SUCCESS] All analytics checks passed!")
        sys.exit(0)
    else:
        print("\n[ERROR] Some analytics checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
