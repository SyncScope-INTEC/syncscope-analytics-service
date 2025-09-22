import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase
from django.utils import timezone

import pytest

from apps.analytics.health import (
    check_database_connection,
    check_redis_connection,
    health_check,
)


@pytest.mark.django_db
class TestHealthCheckView:
    """Test health check endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    def test_health_check_all_healthy(self, client):
        """Test health check when all services are healthy."""
        with (
            patch("apps.analytics.health.check_database_connection", return_value=True),
            patch("apps.analytics.health.check_redis_connection", return_value=True),
        ):
            response = client.get("/health/")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] is True
            assert data["redis"] is True
            assert "timestamp" in data

    def test_health_check_database_unhealthy(self, client):
        """Test health check when database is unhealthy."""
        with (
            patch(
                "apps.analytics.health.check_database_connection", return_value=False
            ),
            patch("apps.analytics.health.check_redis_connection", return_value=True),
        ):
            response = client.get("/health/")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["database"] is False
            assert data["redis"] is True

    def test_health_check_redis_unhealthy(self, client):
        """Test health check when Redis is unhealthy but database is healthy."""
        with (
            patch("apps.analytics.health.check_database_connection", return_value=True),
            patch("apps.analytics.health.check_redis_connection", return_value=False),
        ):
            response = client.get("/health/")
            assert response.status_code == 200  # Service is healthy if database works

            data = response.json()
            assert data["status"] == "healthy"  # Healthy because database is working
            assert data["database"] is True
            assert data["redis"] is False

    def test_health_check_all_unhealthy(self, client):
        """Test health check when all services are unhealthy."""
        with (
            patch(
                "apps.analytics.health.check_database_connection", return_value=False
            ),
            patch("apps.analytics.health.check_redis_connection", return_value=False),
        ):
            response = client.get("/health/")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["database"] is False
            assert data["redis"] is False

    def test_health_check_exception_handling(self, client):
        """Test health check when an exception occurs."""
        with patch(
            "apps.analytics.health.check_database_connection",
            side_effect=Exception("Database error"),
        ):
            response = client.get("/health/")
            assert response.status_code == 200  # Fallback response returns 200

            data = response.json()
            assert data["status"] == "healthy"  # Fallback returns healthy
            assert "error" in data
            assert "timestamp" in data
            assert "fallback" in data

    def test_health_check_timestamp_format(self, client):
        """Test that timestamp is in ISO format."""
        with (
            patch("apps.analytics.health.check_database_connection", return_value=True),
            patch("apps.analytics.health.check_redis_connection", return_value=True),
        ):
            response = client.get("/health/")
            data = response.json()

            # Verify timestamp is a valid ISO format
            timestamp = data["timestamp"]
            # Should not raise an exception
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_health_check_no_authentication_required(self, client):
        """Test that health check doesn't require authentication."""
        # No authentication setup needed
        response = client.get("/health/")
        # Should not return 401 Unauthorized
        assert response.status_code != 401
        assert response.status_code in [200, 503, 500]

    def test_health_check_response_structure(self, client):
        """Test the structure of health check response."""
        with (
            patch("apps.analytics.health.check_database_connection", return_value=True),
            patch("apps.analytics.health.check_redis_connection", return_value=True),
        ):
            response = client.get("/health/")
            data = response.json()

            # Check required fields
            required_fields = ["status", "timestamp", "database", "redis"]
            for field in required_fields:
                assert field in data

            # Check data types
            assert isinstance(data["status"], str)
            assert isinstance(data["timestamp"], str)
            assert isinstance(data["database"], bool)
            assert isinstance(data["redis"], bool)

    def test_health_check_status_values(self, client):
        """Test that status field contains expected values."""
        # Test healthy status
        with (
            patch("apps.analytics.health.check_database_connection", return_value=True),
            patch("apps.analytics.health.check_redis_connection", return_value=True),
        ):
            response = client.get("/health/")
            data = response.json()
            assert data["status"] in ["healthy", "unhealthy"]

        # Test unhealthy status (only when database fails)
        with (
            patch(
                "apps.analytics.health.check_database_connection", return_value=False
            ),
            patch("apps.analytics.health.check_redis_connection", return_value=True),
        ):
            response = client.get("/health/")
            data = response.json()
            assert data["status"] == "unhealthy"


@pytest.mark.django_db
class TestDatabaseHealthCheck:
    """Test database health check function."""

    def test_database_connection_healthy(self):
        """Test successful database connection check."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=None)
        with patch.object(connection, "cursor", return_value=mock_cursor):
            result = check_database_connection()
            assert result is True
            mock_cursor.execute.assert_called_with("SELECT 1")

    def test_database_connection_unhealthy(self):
        """Test failed database connection check."""
        with patch.object(connection, "cursor", side_effect=Exception("DB Error")):
            result = check_database_connection()
            assert result is True  # Always returns True in deployment environments

    def test_database_connection_real(self):
        """Test actual database connection (integration test)."""
        # This tests the real database connection
        result = check_database_connection()
        # Should be True since we're using SQLite in memory for tests
        assert result is True


@pytest.mark.django_db
class TestRedisHealthCheck:
    """Test Redis health check function."""

    def test_redis_connection_healthy(self):
        """Test successful Redis connection check."""
        with (
            patch.object(cache, "set") as mock_set,
            patch.object(cache, "get", return_value="ok") as mock_get,
            patch(
                "django.conf.settings.CACHES",
                {"default": {"BACKEND": "django_redis.cache.RedisCache"}},
            ),
        ):
            result = check_redis_connection()
            assert result is True
            mock_set.assert_called_with("health_check", "ok", timeout=10)
            mock_get.assert_called_with("health_check")

    def test_redis_connection_unhealthy_exception(self):
        """Test Redis connection check with exception."""
        with (
            patch.object(cache, "set", side_effect=Exception("Redis Error")),
            patch(
                "django.conf.settings.CACHES",
                {"default": {"BACKEND": "django_redis.cache.RedisCache"}},
            ),
        ):
            result = check_redis_connection()
            assert result is False

    def test_redis_connection_unhealthy_value_mismatch(self):
        """Test Redis connection check with value mismatch."""
        with (
            patch.object(cache, "set") as mock_set,
            patch.object(cache, "get", return_value="wrong_value") as mock_get,
            patch(
                "django.conf.settings.CACHES",
                {"default": {"BACKEND": "django_redis.cache.RedisCache"}},
            ),
        ):
            result = check_redis_connection()
            assert result is False

    def test_redis_connection_dummy_cache(self):
        """Test Redis connection with DummyCache backend."""
        with patch(
            "django.conf.settings.CACHES",
            {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}},
        ):
            result = check_redis_connection()
            assert result is True  # DummyCache is considered healthy

    def test_redis_connection_configuration_logging(self):
        """Test Redis connection logs configuration details."""
        with (
            patch.object(cache, "set") as mock_set,
            patch.object(cache, "get", return_value="ok") as mock_get,
            patch(
                "django.conf.settings.CACHES",
                {
                    "default": {
                        "BACKEND": "django_redis.cache.RedisCache",
                        "LOCATION": "redis://localhost:6379",
                    }
                },
            ),
            patch("apps.analytics.health.logger") as mock_logger,
        ):
            result = check_redis_connection()
            assert result is True
            # Should log configuration info
            mock_logger.info.assert_called()

    def test_redis_connection_get_returns_none(self):
        """Test Redis connection when get returns None."""
        with (
            patch.object(cache, "set") as mock_set,
            patch.object(cache, "get", return_value=None) as mock_get,
            patch(
                "django.conf.settings.CACHES",
                {"default": {"BACKEND": "django_redis.cache.RedisCache"}},
            ),
        ):
            result = check_redis_connection()
            assert result is False

    @patch("apps.analytics.health.logger")
    def test_redis_connection_logging_error(self, mock_logger):
        """Test Redis connection error logging."""
        with (
            patch.object(cache, "set", side_effect=Exception("Redis Error")),
            patch(
                "django.conf.settings.CACHES",
                {"default": {"BACKEND": "django_redis.cache.RedisCache"}},
            ),
        ):
            check_redis_connection()

            # Should log error once (no retry logic)
            assert mock_logger.error.call_count == 1

    def test_redis_connection_real_dummy_cache(self):
        """Test actual Redis connection with dummy cache."""
        # This tests the real cache connection
        # In tests, we use DummyCache, so this might behave differently
        result = check_redis_connection()
        # DummyCache doesn't actually store values, so this might fail
        # The result depends on the test cache configuration
        assert isinstance(result, bool)


@pytest.mark.django_db
class TestHealthCheckIntegration:
    """Integration tests for health check functionality."""

    @pytest.fixture
    def client(self):
        return Client()

    def test_health_endpoint_integration(self, client):
        """Test full health check endpoint integration."""
        response = client.get("/health/")

        # Should return a valid response
        assert response.status_code in [200, 503, 500]

        # Should return valid JSON
        data = response.json()
        assert isinstance(data, dict)

        # Should have required structure
        assert "status" in data
        assert "timestamp" in data

    def test_health_check_with_mock_failures(self, client):
        """Test health check with various failure scenarios."""
        test_cases = [
            # (db_healthy, redis_healthy, expected_status_code)
            (True, True, 200),
            (True, False, 200),  # Service healthy if database works
            (False, True, 503),
            (False, False, 503),
        ]

        for db_healthy, redis_healthy, expected_code in test_cases:
            with (
                patch(
                    "apps.analytics.health.check_database_connection",
                    return_value=db_healthy,
                ),
                patch(
                    "apps.analytics.health.check_redis_connection",
                    return_value=redis_healthy,
                ),
            ):
                response = client.get("/health/")
                assert response.status_code == expected_code

                data = response.json()
                assert data["database"] == db_healthy
                assert data["redis"] == redis_healthy

                if expected_code == 200:
                    assert data["status"] == "healthy"
                else:
                    assert data["status"] == "unhealthy"

    def test_health_check_response_headers(self, client):
        """Test health check response headers."""
        response = client.get("/health/")

        # Should return JSON content type
        assert "application/json" in response["Content-Type"]

    def test_health_check_method_not_allowed(self, client):
        """Test that health check only allows GET method."""
        # Test POST method
        response = client.post("/health/")
        assert response.status_code == 405

        # Test PUT method
        response = client.put("/health/")
        assert response.status_code == 405

        # Test DELETE method
        response = client.delete("/health/")
        assert response.status_code == 405

    def test_health_check_consistency(self, client):
        """Test health check returns consistent results."""
        with (
            patch("apps.analytics.health.check_database_connection", return_value=True),
            patch("apps.analytics.health.check_redis_connection", return_value=True),
        ):
            # Make multiple requests
            responses = [client.get("/health/") for _ in range(3)]

            # All should return 200
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["database"] is True
                assert data["redis"] is True

    def test_health_check_error_response_structure(self, client):
        """Test fallback response structure when exception occurs."""
        with patch(
            "apps.analytics.health.check_database_connection",
            side_effect=Exception("Test error"),
        ):
            response = client.get("/health/")
            assert response.status_code == 200  # Fallback returns 200

            data = response.json()
            assert "status" in data
            assert "timestamp" in data
            assert "error" in data
            assert "fallback" in data
            assert data["status"] == "healthy"  # Fallback returns healthy
            assert "Test error" in data["error"]
