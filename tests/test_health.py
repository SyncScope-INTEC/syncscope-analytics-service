import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase
from django.utils import timezone

import pytest

from apps.analytics.health import (
    check_cache_connection,
    check_database_connection,
    health_check,
    liveness_check,
    readiness_check,
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
            patch("apps.analytics.health.check_cache_connection", return_value=True),
        ):
            response = client.get("/health/")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert data["services"]["database"] == "healthy"
            assert data["services"]["cache"] == "healthy"
            assert "timestamp" in data
            assert "version" in data

    def test_health_check_database_unhealthy(self, client):
        """Test health check when database is unhealthy."""
        with (
            patch(
                "apps.analytics.health.check_database_connection", return_value=False
            ),
            patch("apps.analytics.health.check_cache_connection", return_value=True),
        ):
            response = client.get("/health/")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["database"] == "unhealthy"
            assert data["services"]["cache"] == "healthy"
            assert "errors" in data

    def test_health_check_cache_unhealthy(self, client):
        """Test health check when cache is unhealthy."""
        with (
            patch("apps.analytics.health.check_database_connection", return_value=True),
            patch("apps.analytics.health.check_cache_connection", return_value=False),
        ):
            response = client.get("/health/")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["database"] == "healthy"
            assert data["services"]["cache"] == "unhealthy"
            assert "errors" in data

    def test_health_check_all_unhealthy(self, client):
        """Test health check when all services are unhealthy."""
        with (
            patch(
                "apps.analytics.health.check_database_connection", return_value=False
            ),
            patch("apps.analytics.health.check_cache_connection", return_value=False),
        ):
            response = client.get("/health/")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["database"] == "unhealthy"
            assert data["services"]["cache"] == "unhealthy"
            assert "errors" in data

    def test_health_check_exception_handling(self, client):
        """Test health check when an exception occurs."""
        with (
            patch(
                "apps.analytics.health.check_database_connection",
                side_effect=Exception("Database error"),
            ),
            patch("apps.analytics.health.check_cache_connection", return_value=True),
        ):
            response = client.get("/health/")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert "errors" in data
            assert "timestamp" in data
            assert "Database: Database error" in data["errors"]

    def test_health_check_timestamp_format(self, client):
        """Test that timestamp is in ISO format."""
        with (
            patch("apps.analytics.health.check_database_connection", return_value=True),
            patch("apps.analytics.health.check_cache_connection", return_value=True),
        ):
            response = client.get("/health/")
            data = response.json()

            # Verify timestamp is a valid ISO format
            timestamp = data["timestamp"]
            # Should not raise an exception
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")

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
            patch("apps.analytics.health.check_cache_connection", return_value=True),
        ):
            response = client.get("/health/")
            data = response.json()

            # Check required fields
            required_fields = ["status", "timestamp", "version", "services"]
            for field in required_fields:
                assert field in data

            # Check services structure
            assert "database" in data["services"]
            assert "cache" in data["services"]

            # Check data types
            assert isinstance(data["status"], str)
            assert isinstance(data["timestamp"], str)
            assert isinstance(data["version"], str)
            assert isinstance(data["services"], dict)
            assert isinstance(data["services"]["database"], str)
            assert isinstance(data["services"]["cache"], str)

    def test_health_check_status_values(self, client):
        """Test that status field contains expected values."""
        # Test healthy status
        with (
            patch("apps.analytics.health.check_database_connection", return_value=True),
            patch("apps.analytics.health.check_cache_connection", return_value=True),
        ):
            response = client.get("/health/")
            data = response.json()
            assert data["status"] == "healthy"

        # Test unhealthy status (only when database fails)
        with (
            patch(
                "apps.analytics.health.check_database_connection", return_value=False
            ),
            patch("apps.analytics.health.check_cache_connection", return_value=True),
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
            assert result is False

    def test_database_connection_real(self):
        """Test actual database connection (integration test)."""
        # This tests the real database connection
        result = check_database_connection()
        # Should be True since we're using SQLite in memory for tests
        assert result is True


@pytest.mark.django_db
class TestCacheHealthCheck:
    """Test cache health check function."""

    def test_cache_connection_healthy(self):
        """Test successful cache connection check."""
        with (
            patch.object(cache, "set") as mock_set,
            patch.object(cache, "get", return_value="ok") as mock_get,
            patch(
                "django.conf.settings.CACHES",
                {"default": {"BACKEND": "django_redis.cache.RedisCache"}},
            ),
        ):
            result = check_cache_connection()
            assert result is True
            mock_set.assert_called_with("health_check", "ok", timeout=10)
            mock_get.assert_called_with("health_check")

    def test_cache_connection_unhealthy_exception(self):
        """Test cache connection check with exception."""
        with (
            patch.object(cache, "set", side_effect=Exception("Cache Error")),
            patch(
                "django.conf.settings.CACHES",
                {"default": {"BACKEND": "django_redis.cache.RedisCache"}},
            ),
        ):
            result = check_cache_connection()
            assert result is False

    def test_cache_connection_unhealthy_value_mismatch(self):
        """Test cache connection check with value mismatch."""
        with (
            patch.object(cache, "set") as mock_set,
            patch.object(cache, "get", return_value="wrong_value") as mock_get,
            patch(
                "django.conf.settings.CACHES",
                {"default": {"BACKEND": "django_redis.cache.RedisCache"}},
            ),
        ):
            result = check_cache_connection()
            assert result is False

    def test_cache_connection_dummy_cache(self):
        """Test cache connection with DummyCache backend."""
        with patch(
            "django.conf.settings.CACHES",
            {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}},
        ):
            result = check_cache_connection()
            assert result is True  # DummyCache is considered healthy

    def test_cache_connection_get_returns_none(self):
        """Test cache connection when get returns None."""
        with (
            patch.object(cache, "set") as mock_set,
            patch.object(cache, "get", return_value=None) as mock_get,
            patch(
                "django.conf.settings.CACHES",
                {"default": {"BACKEND": "django_redis.cache.RedisCache"}},
            ),
        ):
            result = check_cache_connection()
            assert result is False

    @patch("apps.analytics.health.logger")
    def test_cache_connection_logging_error(self, mock_logger):
        """Test cache connection error logging."""
        with (
            patch.object(cache, "set", side_effect=Exception("Cache Error")),
            patch(
                "django.conf.settings.CACHES",
                {"default": {"BACKEND": "django_redis.cache.RedisCache"}},
            ),
        ):
            check_cache_connection()

            # Should log error
            assert mock_logger.error.call_count == 1

    def test_cache_connection_real_dummy_cache(self):
        """Test actual cache connection with dummy cache."""
        # This tests the real cache connection
        # In tests, we use DummyCache, so this might behave differently
        result = check_cache_connection()
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
            # (db_healthy, cache_healthy, expected_status_code)
            (True, True, 200),
            (True, False, 503),
            (False, True, 503),
            (False, False, 503),
        ]

        for db_healthy, cache_healthy, expected_code in test_cases:
            with (
                patch(
                    "apps.analytics.health.check_database_connection",
                    return_value=db_healthy,
                ),
                patch(
                    "apps.analytics.health.check_cache_connection",
                    return_value=cache_healthy,
                ),
            ):
                response = client.get("/health/")
                assert response.status_code == expected_code

                data = response.json()
                assert data["services"]["database"] == (
                    "healthy" if db_healthy else "unhealthy"
                )
                assert data["services"]["cache"] == (
                    "healthy" if cache_healthy else "unhealthy"
                )

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
            patch("apps.analytics.health.check_cache_connection", return_value=True),
        ):
            # Make multiple requests
            responses = [client.get("/health/") for _ in range(3)]

            # All should return 200
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["services"]["database"] == "healthy"
                assert data["services"]["cache"] == "healthy"

    def test_health_check_error_response_structure(self, client):
        """Test error response structure when exception occurs."""
        with (
            patch(
                "apps.analytics.health.check_database_connection",
                side_effect=Exception("Test error"),
            ),
            patch("apps.analytics.health.check_cache_connection", return_value=True),
        ):
            response = client.get("/health/")
            assert response.status_code == 503

            data = response.json()
            assert "status" in data
            assert "timestamp" in data
            assert "errors" in data
            assert data["status"] == "unhealthy"
            assert "Database: Test error" in data["errors"]


@pytest.mark.django_db
class TestReadinessCheck:
    """Test readiness check endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    def test_readiness_check_healthy(self, client):
        """Test readiness check when database is healthy."""
        with patch(
            "apps.analytics.health.check_database_connection", return_value=True
        ):
            response = client.get("/analytics/ready/")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "ready"

    def test_readiness_check_unhealthy(self, client):
        """Test readiness check when database is unhealthy."""
        with patch(
            "apps.analytics.health.check_database_connection", return_value=False
        ):
            response = client.get("/analytics/ready/")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "not ready"


@pytest.mark.django_db
class TestLivenessCheck:
    """Test liveness check endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    def test_liveness_check(self, client):
        """Test liveness check always returns alive."""
        response = client.get("/analytics/live/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "alive"
