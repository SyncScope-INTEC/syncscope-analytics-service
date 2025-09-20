"""
URL patterns for Analytics Service API endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .health import health_check

# Create router for ViewSets
router = DefaultRouter()
router.register(r'reports', views.ReportViewSet, basename='report')
router.register(r'metrics', views.MetricDefinitionViewSet, basename='metric')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Custom function-based views
    path('calculate/', views.calculate_metric, name='calculate-metric'),
    path('dashboard/', views.analytics_dashboard, name='analytics-dashboard'),
    path('health/', health_check, name='analytics-health-check'),
]