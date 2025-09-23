import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase
from django.utils import timezone

import pytest

from apps.analytics.health import (
    health_check,
    liveness_check,
    readiness_check,
    simple_health_check,
)


@pytest.mark.django_db
class TestSimpleHealthCheckView:
    """Test simple health check endpoint (default /health/)."""

    @pytest.fixture
    def client(self):
        return Client()

    def test_simple_health_check(self, client):
        """Test simple health check always returns ok."""
        response = client.get("/health/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "analytics-service"

    def test_simple_health_check_no_authentication_required(self, client):
        """Test that simple health check doesn't require authentication."""
        response = client.get("/health/")
        assert response.status_code == 200
        assert response.status_code != 401


@pytest.mark.django_db
class TestDetailedHealthCheckView:
    """Test detailed health check endpoint (/health/detailed/)."""

    @pytest.fixture
    def client(self):
        return Client()

    def test_detailed_health_check_all_healthy(self, client):
        """Test detailed health check when all services are healthy."""
        with (
            patch(
                "config.database_retry.DatabaseHealthCheck.is_healthy",
                return_value=True,
            ),
            patch("django.core.cache.cache.set"),
            patch("django.core.cache.cache.get", return_value="ok"),
        ):
            response = client.get("/health/detailed/")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert data["services"]["database"] == "healthy"
            assert data["services"]["cache"] == "healthy"
            assert "timestamp" in data
            assert "version" in data

    def test_detailed_health_check_database_unhealthy(self, client):
        """Test detailed health check when database is unhealthy."""
        with (
            patch(
                "config.database_retry.DatabaseHealthCheck.is_healthy",
                return_value=False,
            ),
            patch("django.core.cache.cache.set"),
            patch("django.core.cache.cache.get", return_value="ok"),
        ):
            response = client.get("/health/detailed/")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["database"] == "unhealthy"
            assert data["services"]["cache"] == "healthy"
            assert "errors" in data
            assert any("Database:" in error for error in data["errors"])

    def test_detailed_health_check_cache_unhealthy(self, client):
        """Test detailed health check when cache is unhealthy."""
        with (
            patch(
                "config.database_retry.DatabaseHealthCheck.is_healthy",
                return_value=True,
            ),
            patch("django.core.cache.cache.set", side_effect=Exception("Cache Error")),
        ):
            response = client.get("/health/detailed/")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["database"] == "healthy"
            assert data["services"]["cache"] == "unhealthy"
            assert "errors" in data
            assert any("Cache:" in error for error in data["errors"])

    def test_detailed_health_check_all_unhealthy(self, client):
        """Test detailed health check when all services are unhealthy."""
        with (
            patch(
                "config.database_retry.DatabaseHealthCheck.is_healthy",
                return_value=False,
            ),
            patch("django.core.cache.cache.set", side_effect=Exception("Cache Error")),
        ):
            response = client.get("/health/detailed/")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["database"] == "unhealthy"
            assert data["services"]["cache"] == "unhealthy"
            assert "errors" in data

    def test_detailed_health_check_exception_handling(self, client):
        """Test detailed health check when an exception occurs."""
        with patch(
            "config.database_retry.DatabaseHealthCheck.is_healthy",
            side_effect=Exception("Database error"),
        ):
            response = client.get("/health/detailed/")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "unhealthy"
            assert "errors" in data
            assert "timestamp" in data
            assert any("Database:" in error for error in data["errors"])

    def test_detailed_health_check_response_structure(self, client):
        """Test the structure of detailed health check response."""
        with (
            patch(
                "config.database_retry.DatabaseHealthCheck.is_healthy",
                return_value=True,
            ),
            patch("django.core.cache.cache.set"),
            patch("django.core.cache.cache.get", return_value="ok"),
        ):
            response = client.get("/health/detailed/")
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

    def test_detailed_health_check_timestamp_format(self, client):
        """Test that timestamp is in ISO format."""
        with (
            patch(
                "config.database_retry.DatabaseHealthCheck.is_healthy",
                return_value=True,
            ),
            patch("django.core.cache.cache.set"),
            patch("django.core.cache.cache.get", return_value="ok"),
        ):
            response = client.get("/health/detailed/")
            data = response.json()

            # Verify timestamp is a valid ISO format
            timestamp = data["timestamp"]
            # Should not raise an exception
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.django_db
class TestReadinessCheck:
    """Test readiness check endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    def test_readiness_check_healthy(self, client):
        """Test readiness check when database is healthy."""
        with patch(
            "config.database_retry.DatabaseHealthCheck.is_healthy", return_value=True
        ):
            response = client.get("/health/ready/")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "ready"

    def test_readiness_check_unhealthy(self, client):
        """Test readiness check when database is unhealthy."""
        with patch(
            "config.database_retry.DatabaseHealthCheck.is_healthy", return_value=False
        ):
            response = client.get("/health/ready/")
            assert response.status_code == 503

            data = response.json()
            assert data["status"] == "not ready"

    def test_readiness_check_exception(self, client):
        """Test readiness check when exception occurs."""
        with patch(
            "config.database_retry.DatabaseHealthCheck.is_healthy",
            side_effect=Exception("Error"),
        ):
            response = client.get("/health/ready/")
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
        response = client.get("/health/live/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "alive"
        assert data["service"] == "analytics"

    def test_liveness_check_no_auth_required(self, client):
        """Test liveness check doesn't require authentication."""
        response = client.get("/health/live/")
        assert response.status_code == 200
        assert response.status_code != 401


@pytest.mark.django_db
class TestHealthCheckIntegration:
    """Integration tests for health check functionality."""

    @pytest.fixture
    def client(self):
        return Client()

    def test_simple_health_endpoint_integration(self, client):
        """Test simple health check endpoint integration."""
        response = client.get("/health/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "analytics-service"

    def test_detailed_health_endpoint_integration(self, client):
        """Test detailed health check endpoint integration."""
        response = client.get("/health/detailed/")

        # Should return a valid response
        assert response.status_code in [200, 503]

        # Should return valid JSON
        data = response.json()
        assert isinstance(data, dict)

        # Should have required structure
        assert "status" in data
        assert "timestamp" in data

    def test_health_check_response_headers(self, client):
        """Test health check response headers."""
        response = client.get("/health/")
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

    def test_all_health_endpoints_accessible(self, client):
        """Test that all health endpoints are accessible."""
        endpoints = [
            "/health/",  # Simple health check
            "/health/detailed/",  # Detailed health check
            "/health/ready/",  # Readiness check
            "/health/live/",  # Liveness check
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 503]  # Should return valid status
            assert response["Content-Type"].startswith("application/json")
