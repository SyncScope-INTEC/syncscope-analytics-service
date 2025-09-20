import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from django.utils import timezone

from apps.analytics.influxdb_client import InfluxDBManager, influxdb_manager


class TestInfluxDBManager:
    """Test cases for InfluxDBManager"""

    @patch('influxdb_client.InfluxDBClient')
    def test_initialization(self, mock_client_class):
        """Test InfluxDB manager initialization"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager(
            url="http://localhost:8086",
            token="test-token",
            org="test-org",
            bucket="test-bucket"
        )

        assert manager.client == mock_client
        assert manager.org == "test-org"
        assert manager.bucket == "test-bucket"
        mock_client_class.assert_called_once_with(
            url="http://localhost:8086",
            token="test-token",
            org="test-org"
        )

    @patch('influxdb_client.InfluxDBClient')
    def test_initialization_with_defaults(self, mock_client_class):
        """Test initialization with default parameters"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        with patch('django.conf.settings') as mock_settings:
            mock_settings.INFLUXDB_URL = "http://default:8086"
            mock_settings.INFLUXDB_TOKEN = "default-token"
            mock_settings.INFLUXDB_ORG = "default-org"
            mock_settings.INFLUXDB_BUCKET = "default-bucket"

            manager = InfluxDBManager()

            assert manager.org == "default-org"
            assert manager.bucket == "default-bucket"

    @patch('influxdb_client.InfluxDBClient')
    def test_write_metric_basic(self, mock_client_class):
        """Test basic metric writing"""
        mock_client = Mock()
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        measurement = "productivity"
        tags = {"user_id": "test-user", "project_id": "test-project"}
        fields = {"score": 85.5, "sessions": 10}

        result = manager.write_metric(measurement, tags, fields)

        assert result is True
        mock_write_api.write.assert_called_once()

    @patch('influxdb_client.InfluxDBClient')
    def test_write_metric_with_timestamp(self, mock_client_class):
        """Test metric writing with custom timestamp"""
        mock_client = Mock()
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        measurement = "productivity"
        tags = {"user_id": "test-user"}
        fields = {"score": 85.5}
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        result = manager.write_metric(measurement, tags, fields, timestamp)

        assert result is True
        mock_write_api.write.assert_called_once()

    @patch('influxdb_client.InfluxDBClient')
    def test_write_metric_exception(self, mock_client_class):
        """Test metric writing with exception"""
        mock_client = Mock()
        mock_write_api = Mock()
        mock_write_api.write.side_effect = Exception("Write failed")
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        measurement = "productivity"
        tags = {"user_id": "test-user"}
        fields = {"score": 85.5}

        result = manager.write_metric(measurement, tags, fields)

        assert result is False

    @patch('influxdb_client.InfluxDBClient')
    def test_write_bulk_metrics(self, mock_client_class):
        """Test bulk metric writing"""
        mock_client = Mock()
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        metrics = [
            {
                "measurement": "productivity",
                "tags": {"user_id": "user1"},
                "fields": {"score": 85.5},
                "time": datetime(2024, 1, 1, 12, 0, 0)
            },
            {
                "measurement": "productivity",
                "tags": {"user_id": "user2"},
                "fields": {"score": 75.0},
                "time": datetime(2024, 1, 1, 13, 0, 0)
            }
        ]

        result = manager.write_bulk_metrics(metrics)

        assert result is True
        assert mock_write_api.write.call_count == 2

    @patch('influxdb_client.InfluxDBClient')
    def test_query_metrics_basic(self, mock_client_class):
        """Test basic metric querying"""
        mock_client = Mock()
        mock_query_api = Mock()

        # Mock query result
        mock_record = Mock()
        mock_record.get_measurement.return_value = "productivity"
        mock_record.get_field.return_value = "score"
        mock_record.get_value.return_value = 85.5
        mock_record.get_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_record.values = {"user_id": "test-user", "_value": 85.5}

        mock_table = Mock()
        mock_table.records = [mock_record]

        mock_query_api.query.return_value = [mock_table]
        mock_client.query_api.return_value = mock_query_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 1, 23, 59, 59)

        results = manager.query_metrics("productivity", start_time, end_time)

        assert len(results) == 1
        assert results[0]["measurement"] == "productivity"
        assert results[0]["value"] == 85.5
        mock_query_api.query.assert_called_once()

    @patch('influxdb_client.InfluxDBClient')
    def test_query_metrics_with_filters(self, mock_client_class):
        """Test metric querying with filters"""
        mock_client = Mock()
        mock_query_api = Mock()
        mock_query_api.query.return_value = []
        mock_client.query_api.return_value = mock_query_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 1, 23, 59, 59)
        filters = {"user_id": "test-user", "project_id": "test-project"}

        results = manager.query_metrics("productivity", start_time, end_time, filters)

        # Verify query was called with filters
        mock_query_api.query.assert_called_once()
        call_args = mock_query_api.query.call_args[0][0]
        assert "user_id" in call_args
        assert "test-user" in call_args

    @patch('influxdb_client.InfluxDBClient')
    def test_query_metrics_exception(self, mock_client_class):
        """Test metric querying with exception"""
        mock_client = Mock()
        mock_query_api = Mock()
        mock_query_api.query.side_effect = Exception("Query failed")
        mock_client.query_api.return_value = mock_query_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 1, 23, 59, 59)

        results = manager.query_metrics("productivity", start_time, end_time)

        assert results == []

    @patch('influxdb_client.InfluxDBClient')
    def test_get_latest_metrics(self, mock_client_class):
        """Test getting latest metrics"""
        mock_client = Mock()
        mock_query_api = Mock()

        # Mock latest metric result
        mock_record = Mock()
        mock_record.get_measurement.return_value = "productivity"
        mock_record.get_value.return_value = 90.0
        mock_record.get_time.return_value = datetime(2024, 1, 1, 15, 0, 0)
        mock_record.values = {"user_id": "test-user", "_value": 90.0}

        mock_table = Mock()
        mock_table.records = [mock_record]

        mock_query_api.query.return_value = [mock_table]
        mock_client.query_api.return_value = mock_query_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        results = manager.get_latest_metrics("productivity", {"user_id": "test-user"})

        assert len(results) == 1
        assert results[0]["value"] == 90.0
        mock_query_api.query.assert_called_once()

    @patch('influxdb_client.InfluxDBClient')
    def test_aggregate_metrics_sum(self, mock_client_class):
        """Test metric aggregation with sum"""
        mock_client = Mock()
        mock_query_api = Mock()

        # Mock aggregation result
        mock_record = Mock()
        mock_record.get_value.return_value = 500.0  # Sum result
        mock_record.values = {"_value": 500.0}

        mock_table = Mock()
        mock_table.records = [mock_record]

        mock_query_api.query.return_value = [mock_table]
        mock_client.query_api.return_value = mock_query_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 1, 23, 59, 59)

        result = manager.aggregate_metrics(
            "productivity",
            start_time,
            end_time,
            aggregation="sum"
        )

        assert result == 500.0
        mock_query_api.query.assert_called_once()

    @patch('influxdb_client.InfluxDBClient')
    def test_aggregate_metrics_mean(self, mock_client_class):
        """Test metric aggregation with mean"""
        mock_client = Mock()
        mock_query_api = Mock()

        # Mock aggregation result
        mock_record = Mock()
        mock_record.get_value.return_value = 82.5  # Mean result
        mock_record.values = {"_value": 82.5}

        mock_table = Mock()
        mock_table.records = [mock_record]

        mock_query_api.query.return_value = [mock_table]
        mock_client.query_api.return_value = mock_query_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 1, 23, 59, 59)

        result = manager.aggregate_metrics(
            "productivity",
            start_time,
            end_time,
            aggregation="mean",
            filters={"user_id": "test-user"}
        )

        assert result == 82.5

    @patch('influxdb_client.InfluxDBClient')
    def test_get_time_series_data(self, mock_client_class):
        """Test getting time series data"""
        mock_client = Mock()
        mock_query_api = Mock()

        # Mock time series results
        times = [
            datetime(2024, 1, 1, 12, 0, 0),
            datetime(2024, 1, 1, 13, 0, 0),
            datetime(2024, 1, 1, 14, 0, 0)
        ]
        values = [80.0, 85.0, 90.0]

        mock_records = []
        for time, value in zip(times, values):
            mock_record = Mock()
            mock_record.get_time.return_value = time
            mock_record.get_value.return_value = value
            mock_record.values = {"_value": value, "_time": time}
            mock_records.append(mock_record)

        mock_table = Mock()
        mock_table.records = mock_records

        mock_query_api.query.return_value = [mock_table]
        mock_client.query_api.return_value = mock_query_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 1, 23, 59, 59)

        results = manager.get_time_series_data(
            "productivity",
            start_time,
            end_time,
            window="1h"
        )

        assert len(results) == 3
        assert results[0]["time"] == times[0]
        assert results[0]["value"] == values[0]

    @patch('influxdb_client.InfluxDBClient')
    def test_health_check_success(self, mock_client_class):
        """Test health check success"""
        mock_client = Mock()
        mock_health_api = Mock()
        mock_health_api.check.return_value = Mock(status="pass")
        mock_client.health.return_value = mock_health_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        is_healthy = manager.health_check()

        assert is_healthy is True

    @patch('influxdb_client.InfluxDBClient')
    def test_health_check_failure(self, mock_client_class):
        """Test health check failure"""
        mock_client = Mock()
        mock_health_api = Mock()
        mock_health_api.check.side_effect = Exception("Health check failed")
        mock_client.health.return_value = mock_health_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        is_healthy = manager.health_check()

        assert is_healthy is False

    @patch('influxdb_client.InfluxDBClient')
    def test_close_connection(self, mock_client_class):
        """Test closing connection"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()
        manager.close()

        mock_client.close.assert_called_once()

    @patch('influxdb_client.InfluxDBClient')
    def test_context_manager(self, mock_client_class):
        """Test using InfluxDBManager as context manager"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        with InfluxDBManager() as manager:
            assert manager.client == mock_client

        mock_client.close.assert_called_once()


class TestInfluxDBManagerIntegration:
    """Integration tests for InfluxDB operations"""

    @patch('influxdb_client.InfluxDBClient')
    def test_write_and_query_workflow(self, mock_client_class):
        """Test complete write and query workflow"""
        mock_client = Mock()
        mock_write_api = Mock()
        mock_query_api = Mock()

        # Setup write API
        mock_client.write_api.return_value = mock_write_api

        # Setup query API with expected result
        mock_record = Mock()
        mock_record.get_measurement.return_value = "productivity"
        mock_record.get_value.return_value = 85.5
        mock_record.get_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_record.values = {"user_id": "test-user", "_value": 85.5}

        mock_table = Mock()
        mock_table.records = [mock_record]
        mock_query_api.query.return_value = [mock_table]
        mock_client.query_api.return_value = mock_query_api

        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        # Write metric
        write_result = manager.write_metric(
            "productivity",
            {"user_id": "test-user"},
            {"score": 85.5}
        )
        assert write_result is True

        # Query metric back
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 1, 23, 59, 59)

        query_results = manager.query_metrics("productivity", start_time, end_time)
        assert len(query_results) == 1
        assert query_results[0]["value"] == 85.5

    @patch('influxdb_client.InfluxDBClient')
    def test_bulk_operations(self, mock_client_class):
        """Test bulk write and aggregation operations"""
        mock_client = Mock()
        mock_write_api = Mock()
        mock_query_api = Mock()

        mock_client.write_api.return_value = mock_write_api

        # Mock aggregation result
        mock_record = Mock()
        mock_record.get_value.return_value = 167.0  # Sum of two values
        mock_record.values = {"_value": 167.0}

        mock_table = Mock()
        mock_table.records = [mock_record]
        mock_query_api.query.return_value = [mock_table]
        mock_client.query_api.return_value = mock_query_api

        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        # Bulk write
        metrics = [
            {
                "measurement": "productivity",
                "tags": {"user_id": "user1"},
                "fields": {"score": 85.5},
                "time": datetime(2024, 1, 1, 12, 0, 0)
            },
            {
                "measurement": "productivity",
                "tags": {"user_id": "user1"},
                "fields": {"score": 81.5},
                "time": datetime(2024, 1, 1, 13, 0, 0)
            }
        ]

        bulk_result = manager.write_bulk_metrics(metrics)
        assert bulk_result is True
        assert mock_write_api.write.call_count == 2

        # Aggregate query
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 1, 23, 59, 59)

        total = manager.aggregate_metrics(
            "productivity",
            start_time,
            end_time,
            aggregation="sum",
            filters={"user_id": "user1"}
        )
        assert total == 167.0


class TestInfluxDBGlobalInstance:
    """Test global InfluxDB manager instance"""

    @patch('apps.analytics.influxdb_client.InfluxDBManager')
    def test_global_instance_creation(self, mock_manager_class):
        """Test that global instance is created correctly"""
        # Import should create the global instance
        from apps.analytics.influxdb_client import influxdb_manager

        assert influxdb_manager is not None
        mock_manager_class.assert_called_once()

    def test_global_instance_usage(self):
        """Test using the global instance"""
        # This test verifies the global instance exists and has expected methods
        assert hasattr(influxdb_manager, 'write_metric')
        assert hasattr(influxdb_manager, 'query_metrics')
        assert hasattr(influxdb_manager, 'health_check')


class TestInfluxDBErrorHandling:
    """Test error handling and edge cases"""

    @patch('influxdb_client.InfluxDBClient')
    def test_write_metric_with_invalid_data(self, mock_client_class):
        """Test writing metrics with invalid data"""
        mock_client = Mock()
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        # Test with empty fields
        result = manager.write_metric("test", {"user_id": "test"}, {})
        assert result is False

        # Test with None values
        result = manager.write_metric("test", None, {"score": 85.5})
        assert result is False

    @patch('influxdb_client.InfluxDBClient')
    def test_query_with_invalid_time_range(self, mock_client_class):
        """Test querying with invalid time range"""
        mock_client = Mock()
        mock_query_api = Mock()
        mock_client.query_api.return_value = mock_query_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        # End time before start time
        start_time = datetime(2024, 1, 2, 0, 0, 0)
        end_time = datetime(2024, 1, 1, 0, 0, 0)

        results = manager.query_metrics("productivity", start_time, end_time)
        assert results == []

    @patch('influxdb_client.InfluxDBClient')
    def test_connection_failure_handling(self, mock_client_class):
        """Test handling connection failures"""
        mock_client_class.side_effect = Exception("Connection failed")

        # Should handle initialization failure gracefully
        try:
            manager = InfluxDBManager()
            # Operations should fail gracefully
            result = manager.write_metric("test", {"user_id": "test"}, {"score": 85.5})
            assert result is False
        except Exception:
            # Or raise appropriate exception
            pytest.fail("Should handle connection failure gracefully")

    @patch('influxdb_client.InfluxDBClient')
    def test_malformed_query_response(self, mock_client_class):
        """Test handling malformed query responses"""
        mock_client = Mock()
        mock_query_api = Mock()

        # Mock malformed response
        mock_record = Mock()
        mock_record.get_measurement.side_effect = Exception("Malformed record")
        mock_record.get_value.return_value = None

        mock_table = Mock()
        mock_table.records = [mock_record]
        mock_query_api.query.return_value = [mock_table]
        mock_client.query_api.return_value = mock_query_api
        mock_client_class.return_value = mock_client

        manager = InfluxDBManager()

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 1, 23, 59, 59)

        # Should handle malformed records gracefully
        results = manager.query_metrics("productivity", start_time, end_time)
        # Should return empty list or filtered results
        assert isinstance(results, list)