"""
InfluxDB client for time series metrics storage and retrieval.
GitHub Issue #2: Configurar InfluxDB para métricas de series temporales
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal

from django.conf import settings
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException

logger = logging.getLogger(__name__)


class InfluxDBManager:
    """
    Manager class for InfluxDB operations
    """

    def __init__(self):
        self.client = None
        self.write_api = None
        self.query_api = None
        self.bucket = settings.INFLUXDB_BUCKET
        self.org = settings.INFLUXDB_ORG
        self._initialize_client()

    def _initialize_client(self):
        """
        Initialize InfluxDB client with configuration from settings
        """
        try:
            self.client = InfluxDBClient(
                url=settings.INFLUXDB_URL,
                token=settings.INFLUXDB_TOKEN,
                org=self.org,
                timeout=30000  # 30 second timeout
            )

            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()

            # Test connection
            if self._test_connection():
                logger.info("InfluxDB connection established successfully")
            else:
                logger.warning("InfluxDB connection test failed")

        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB client: {e}")
            self.client = None

    def _test_connection(self) -> bool:
        """
        Test InfluxDB connection
        """
        try:
            if not self.client:
                return False

            # Try to query bucket info
            query = f'buckets() |> filter(fn: (r) => r.name == "{self.bucket}") |> limit(n:1)'
            result = self.query_api.query(query, org=self.org)
            return True
        except Exception as e:
            logger.error(f"InfluxDB connection test failed: {e}")
            return False

    def is_available(self) -> bool:
        """
        Check if InfluxDB is available
        """
        return self.client is not None and self._test_connection()

    def write_metric(self, measurement: str, tags: Dict[str, str], fields: Dict[str, Union[int, float, str]],
                    timestamp: Optional[datetime] = None) -> bool:
        """
        Write a single metric point to InfluxDB

        Args:
            measurement: The measurement name (table name)
            tags: Dictionary of tag key-value pairs (indexed fields)
            fields: Dictionary of field key-value pairs (data values)
            timestamp: Optional timestamp, defaults to current time

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.is_available():
                logger.warning("InfluxDB not available for writing")
                return False

            point = Point(measurement)

            # Add tags
            for key, value in tags.items():
                point = point.tag(key, str(value))

            # Add fields
            for key, value in fields.items():
                if isinstance(value, (int, float, Decimal)):
                    point = point.field(key, float(value))
                elif isinstance(value, bool):
                    point = point.field(key, value)
                else:
                    point = point.field(key, str(value))

            # Set timestamp
            if timestamp:
                point = point.time(timestamp, WritePrecision.S)

            # Write to InfluxDB
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True

        except Exception as e:
            logger.error(f"Failed to write metric to InfluxDB: {e}")
            return False

    def write_metrics_batch(self, points: List[Dict[str, Any]]) -> bool:
        """
        Write multiple metrics in batch

        Args:
            points: List of point dictionaries with keys: measurement, tags, fields, timestamp

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.is_available():
                logger.warning("InfluxDB not available for batch writing")
                return False

            influx_points = []

            for point_data in points:
                measurement = point_data.get('measurement')
                tags = point_data.get('tags', {})
                fields = point_data.get('fields', {})
                timestamp = point_data.get('timestamp')

                if not measurement or not fields:
                    logger.warning(f"Skipping invalid point: {point_data}")
                    continue

                point = Point(measurement)

                # Add tags
                for key, value in tags.items():
                    point = point.tag(key, str(value))

                # Add fields
                for key, value in fields.items():
                    if isinstance(value, (int, float, Decimal)):
                        point = point.field(key, float(value))
                    elif isinstance(value, bool):
                        point = point.field(key, value)
                    else:
                        point = point.field(key, str(value))

                # Set timestamp
                if timestamp:
                    point = point.time(timestamp, WritePrecision.S)

                influx_points.append(point)

            if influx_points:
                self.write_api.write(bucket=self.bucket, org=self.org, record=influx_points)
                logger.info(f"Successfully wrote {len(influx_points)} points to InfluxDB")
                return True
            else:
                logger.warning("No valid points to write")
                return False

        except Exception as e:
            logger.error(f"Failed to write batch metrics to InfluxDB: {e}")
            return False

    def query_metrics(self, query: str, start_time: Optional[datetime] = None,
                     stop_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Query metrics from InfluxDB

        Args:
            query: Flux query string
            start_time: Optional start time filter
            stop_time: Optional stop time filter

        Returns:
            List of dictionaries containing query results
        """
        try:
            if not self.is_available():
                logger.warning("InfluxDB not available for querying")
                return []

            # Add time range to query if provided
            if start_time or stop_time:
                start_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ') if start_time else '-30d'
                stop_str = stop_time.strftime('%Y-%m-%dT%H:%M:%SZ') if stop_time else 'now()'

                query = f'from(bucket:"{self.bucket}") |> range(start: {start_str}, stop: {stop_str}) |> ' + query
            else:
                query = f'from(bucket:"{self.bucket}") |> range(start: -30d) |> ' + query

            result = self.query_api.query(org=self.org, query=query)

            # Convert result to list of dictionaries
            data = []
            for table in result:
                for record in table.records:
                    row = {
                        'time': record.get_time(),
                        'measurement': record.get_measurement(),
                        'value': record.get_value(),
                        'field': record.get_field()
                    }

                    # Add tags
                    for key, value in record.values.items():
                        if key.startswith('_') or key in ['result', 'table']:
                            continue
                        row[key] = value

                    data.append(row)

            return data

        except Exception as e:
            logger.error(f"Failed to query metrics from InfluxDB: {e}")
            return []

    def get_latest_metrics(self, measurement: str, tags: Optional[Dict[str, str]] = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get latest metrics for a measurement

        Args:
            measurement: Measurement name
            tags: Optional tag filters
            limit: Maximum number of results

        Returns:
            List of latest metric records
        """
        try:
            query_parts = [f'filter(fn: (r) => r._measurement == "{measurement}")']

            # Add tag filters
            if tags:
                for key, value in tags.items():
                    query_parts.append(f'filter(fn: (r) => r.{key} == "{value}")')

            # Sort by time and limit
            query_parts.append('sort(columns: ["_time"], desc: true)')
            query_parts.append(f'limit(n: {limit})')

            query = ' |> '.join(query_parts)

            return self.query_metrics(query)

        except Exception as e:
            logger.error(f"Failed to get latest metrics: {e}")
            return []

    def aggregate_metrics(self, measurement: str, aggregation: str = 'mean',
                         window: str = '1h', tags: Optional[Dict[str, str]] = None,
                         start_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Aggregate metrics over time windows

        Args:
            measurement: Measurement name
            aggregation: Aggregation function (mean, sum, count, etc.)
            window: Time window for aggregation (1h, 1d, etc.)
            tags: Optional tag filters
            start_time: Optional start time

        Returns:
            List of aggregated metric records
        """
        try:
            query_parts = [f'filter(fn: (r) => r._measurement == "{measurement}")']

            # Add tag filters
            if tags:
                for key, value in tags.items():
                    query_parts.append(f'filter(fn: (r) => r.{key} == "{value}")')

            # Add aggregation
            query_parts.append(f'aggregateWindow(every: {window}, fn: {aggregation})')

            query = ' |> '.join(query_parts)

            return self.query_metrics(query, start_time=start_time)

        except Exception as e:
            logger.error(f"Failed to aggregate metrics: {e}")
            return []

    def delete_metrics(self, measurement: str, start_time: datetime,
                      stop_time: Optional[datetime] = None,
                      tags: Optional[Dict[str, str]] = None) -> bool:
        """
        Delete metrics from InfluxDB

        Args:
            measurement: Measurement name
            start_time: Start time for deletion
            stop_time: Stop time for deletion (defaults to now)
            tags: Optional tag filters for deletion

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.is_available():
                logger.warning("InfluxDB not available for deletion")
                return False

            delete_api = self.client.delete_api()

            if not stop_time:
                stop_time = datetime.utcnow()

            # Create predicate string
            predicate = f'_measurement="{measurement}"'
            if tags:
                for key, value in tags.items():
                    predicate += f' AND {key}="{value}"'

            # Perform deletion
            delete_api.delete(
                start=start_time,
                stop=stop_time,
                predicate=predicate,
                bucket=self.bucket,
                org=self.org
            )

            logger.info(f"Successfully deleted metrics for {measurement}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete metrics: {e}")
            return False

    def close(self):
        """
        Close InfluxDB client connection
        """
        try:
            if self.client:
                self.client.close()
                logger.info("InfluxDB client connection closed")
        except Exception as e:
            logger.error(f"Error closing InfluxDB client: {e}")


# Global InfluxDB manager instance
influxdb_manager = InfluxDBManager()


class MetricsCollector:
    """
    Helper class for collecting and storing analytics metrics
    """

    @staticmethod
    def store_productivity_metric(user_id: str, metric_type: str, value: Union[int, float],
                                 context: Optional[Dict[str, str]] = None,
                                 timestamp: Optional[datetime] = None) -> bool:
        """
        Store productivity metric in InfluxDB
        """
        tags = {
            'user_id': user_id,
            'metric_type': metric_type,
        }

        if context:
            tags.update(context)

        fields = {'value': float(value)}

        return influxdb_manager.write_metric(
            measurement='productivity_metrics',
            tags=tags,
            fields=fields,
            timestamp=timestamp
        )

    @staticmethod
    def store_code_quality_metric(project_id: str, user_id: str, quality_score: float,
                                 metrics: Dict[str, float], timestamp: Optional[datetime] = None) -> bool:
        """
        Store code quality metrics in InfluxDB
        """
        tags = {
            'project_id': project_id,
            'user_id': user_id
        }

        fields = {'quality_score': quality_score}
        fields.update({k: float(v) for k, v in metrics.items()})

        return influxdb_manager.write_metric(
            measurement='code_quality_metrics',
            tags=tags,
            fields=fields,
            timestamp=timestamp
        )

    @staticmethod
    def store_team_metric(team_id: str, metric_type: str, value: Union[int, float],
                         timestamp: Optional[datetime] = None) -> bool:
        """
        Store team-level metrics in InfluxDB
        """
        tags = {
            'team_id': team_id,
            'metric_type': metric_type
        }

        fields = {'value': float(value)}

        return influxdb_manager.write_metric(
            measurement='team_metrics',
            tags=tags,
            fields=fields,
            timestamp=timestamp
        )

    @staticmethod
    def get_user_productivity_trend(user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get user productivity trend from InfluxDB
        """
        start_time = datetime.utcnow() - timedelta(days=days)

        return influxdb_manager.aggregate_metrics(
            measurement='productivity_metrics',
            aggregation='mean',
            window='1d',
            tags={'user_id': user_id},
            start_time=start_time
        )