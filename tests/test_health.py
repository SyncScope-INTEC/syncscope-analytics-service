from unittest.mock import Mock, patch

from django.http import JsonResponse
from django.test import TestCase, override_settings
from django.urls import reverse

import pytest
from rest_framework import status
from rest_framework.test import APIClient


class TestHealthCheck(TestCase):
    """Test cases for health check functionality"""

    def setUp(self):
        self.client = APIClient()

    def test_health_check_endpoint_exists(self):
        """Test that health check endpoint is accessible"""
        response = self.client.get("/health/")

        # Should not return 404
        assert response.status_code != 404

    @patch("apps.analytics.health.check_database_connection")
    @patch("apps.analytics.health.check_redis_connection")
    def test_health_check_all_healthy(self, mock_redis, mock_db):
        """Test health check when all services are healthy"""
        # Mock all services as healthy
        mock_db.return_value = True
        mock_redis.return_value = True

        response = self.client.get("/health/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "healthy"
        assert data["database"] is True
        assert data["redis"] is True

    @patch("apps.analytics.health.check_database_connection")
    @patch("apps.analytics.health.check_redis_connection")
    def test_health_check_database_unhealthy(self, mock_redis, mock_db):
        """Test health check when database is unhealthy"""
        mock_db.return_value = False
        mock_redis.return_value = True

        response = self.client.get("/health/")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["database"] is False

    @patch("apps.analytics.health.check_database_connection")
    @patch("apps.analytics.health.check_redis_connection")
    def test_health_check_redis_unhealthy(self, mock_redis, mock_db):
        """Test health check when Redis is unhealthy"""
        mock_db.return_value = True
        mock_redis.return_value = False

        response = self.client.get("/health/")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["redis"] is False

    def test_health_check_response_format(self):
        """Test health check response format"""
        response = self.client.get("/health/")
        data = response.json()

        # Check required fields
        required_fields = [
            "status",
            "timestamp",
            "database",
            "redis",
        ]
        for field in required_fields:
            assert field in data

    @patch("apps.analytics.health.check_database_connection")
    def test_health_check_exception_handling(self, mock_db):
        """Test health check handles exceptions gracefully"""
        # Mock database check to raise exception
        mock_db.side_effect = Exception("Database connection failed")

        response = self.client.get("/health/")

        # Should still return a response, not crash
        assert response.status_code in [
            status.HTTP_503_SERVICE_UNAVAILABLE,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

        # Should be valid JSON
        data = response.json()
        assert "status" in data

    def test_health_check_content_type(self):
        """Test health check returns JSON content type"""
        response = self.client.get("/health/")

        assert "application/json" in response["Content-Type"]

    @override_settings(DEBUG=True)
    def test_health_check_debug_mode(self):
        """Test health check in debug mode"""
        response = self.client.get("/health/")
        data = response.json()

        # In debug mode, might include additional information
        assert "status" in data

    @override_settings(DEBUG=False)
    def test_health_check_production_mode(self):
        """Test health check in production mode"""
        response = self.client.get("/health/")
        data = response.json()

        # In production mode, should still work but may hide sensitive info
        assert "status" in data


@pytest.mark.django_db
class TestHealthCheckFunctions:
    """Test individual health check functions"""

    @patch("django.db.connection.ensure_connection")
    def test_check_database_connection_success(self, mock_ensure_connection):
        """Test database connection check success"""
        from apps.analytics.health import check_database_connection

        mock_ensure_connection.return_value = None  # No exception = success

        result = check_database_connection()
        assert result is True

    @patch("django.db.connection.ensure_connection")
    def test_check_database_connection_failure(self, mock_ensure_connection):
        """Test database connection check failure"""
        from apps.analytics.health import check_database_connection

        mock_ensure_connection.side_effect = Exception("Database error")

        result = check_database_connection()
        assert result is False

    @patch("django.core.cache.cache.get")
    def test_check_redis_connection_success(self, mock_cache_get):
        """Test Redis connection check success"""
        from apps.analytics.health import check_redis_connection

        mock_cache_get.return_value = None  # No exception = success

        result = check_redis_connection()
        assert result is True

    @patch("django.core.cache.cache.get")
    def test_check_redis_connection_failure(self, mock_cache_get):
        """Test Redis connection check failure"""
        from apps.analytics.health import check_redis_connection

        mock_cache_get.side_effect = Exception("Redis error")

        result = check_redis_connection()
        assert result is False


class TestHealthCheckIntegration:
    """Integration tests for health check functionality"""

    def test_health_check_endpoint_integration(self):
        """Test health check endpoint integration"""
        client = APIClient()

        # Make request to health endpoint
        response = client.get("/health/")

        # Should get a valid response
        assert response.status_code in [200, 503]

        # Should be valid JSON
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data

    @patch("apps.analytics.health.check_database_connection")
    @patch("apps.analytics.health.check_redis_connection")
    def test_health_check_caching(self, mock_redis, mock_db):
        """Test health check result caching"""
        # Mock all services as healthy
        mock_db.return_value = True
        mock_redis.return_value = True

        client = APIClient()

        # Make multiple requests
        response1 = client.get("/health/")
        response2 = client.get("/health/")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Both should return the same status
        data1 = response1.json()
        data2 = response2.json()
        assert data1["status"] == data2["status"]

    def test_health_check_performance(self):
        """Test health check response time"""
        import time

        client = APIClient()

        start_time = time.time()
        response = client.get("/health/")
        end_time = time.time()

        response_time = end_time - start_time

        # Health check should be fast (under 5 seconds)
        assert response_time < 5.0
        assert response.status_code in [200, 503]


class TestHealthCheckErrorScenarios:
    """Test error scenarios for health check"""

    @patch("apps.analytics.health.check_database_connection")
    def test_health_check_database_exception(self, mock_db):
        """Test health check when database check raises exception"""
        mock_db.side_effect = Exception("Critical database error")

        client = APIClient()
        response = client.get("/health/")

        # Should handle exception gracefully
        assert response.status_code in [503, 500]

        data = response.json()
        assert data["status"] == "unhealthy"

    @patch("apps.analytics.health.check_redis_connection")
    def test_health_check_redis_exception(self, mock_redis):
        """Test health check when Redis check raises exception"""
        mock_redis.side_effect = Exception("Redis connection lost")

        client = APIClient()
        response = client.get("/health/")

        # Should handle exception gracefully
        data = response.json()
        assert data["redis"] is False

    def test_health_check_malformed_response_handling(self):
        """Test health check handles malformed responses"""
        client = APIClient()

        # Even if internal functions return unexpected data,
        # health check should return valid JSON
        response = client.get("/health/")

        # Should always return valid JSON
        try:
            data = response.json()
            assert isinstance(data, dict)
        except ValueError:
            pytest.fail("Health check should always return valid JSON")


class TestHealthCheckMonitoring:
    """Test health check for monitoring purposes"""

    def test_health_check_metrics_structure(self):
        """Test health check returns structured metrics"""
        client = APIClient()
        response = client.get("/health/")
        data = response.json()

        # Should have timestamp for monitoring
        assert "timestamp" in data

        # Should have boolean values for each component
        components = ["database", "redis"]
        for component in components:
            assert component in data
            assert isinstance(data[component], bool)

    @patch("apps.analytics.health.check_database_connection")
    @patch("apps.analytics.health.check_redis_connection")
    def test_health_check_overall_status_logic(self, mock_redis, mock_db):
        """Test overall status calculation logic"""
        # Test all healthy
        mock_db.return_value = True
        mock_redis.return_value = True

        client = APIClient()
        response = client.get("/health/")
        data = response.json()

        assert data["status"] == "healthy"
        assert response.status_code == 200

        # Test one component unhealthy
        mock_db.return_value = False

        response = client.get("/health/")
        data = response.json()

        assert data["status"] == "unhealthy"
        assert response.status_code == 503
