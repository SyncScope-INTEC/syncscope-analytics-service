"""
Metric calculators for various analytics metrics.
GitHub Issue #6: Implementar calculadoras de métricas
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from django.utils import timezone

import numpy as np
import pandas as pd

from .data_analysis import (
    DataFrameProcessor,
    ProductivityAnalyzer,
    StatisticalAnalyzer,
    TimeSeriesAnalyzer,
    TrendAnalyzer,
)
from .models import MetricDefinition, MetricSnapshot, TimeSeriesData
from .service_integration import ManagementServiceClient, MonitoringServiceClient

logger = logging.getLogger(__name__)


class BaseMetricCalculator(ABC):
    """
    Abstract base class for metric calculators
    """

    def __init__(self, metric_definition):
        self.metric_definition = metric_definition
        self.parameters = metric_definition.parameters or {}

    @abstractmethod
    def calculate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate the metric value based on context

        Args:
            context: Dictionary containing calculation context (user_id, team_id, etc.)

        Returns:
            Dictionary with calculation results
        """
        pass

    def get_cache_key(self, context: Dict[str, Any]) -> str:
        """
        Generate cache key for this calculation
        """
        context_str = "_".join([f"{k}:{v}" for k, v in sorted(context.items())])
        return f"metric:{self.metric_definition.id}:{context_str}"

    def validate_context(
        self, context: Dict[str, Any], required_keys: List[str]
    ) -> bool:
        """
        Validate that context contains required keys
        """
        return all(key in context for key in required_keys)


class ProductivityMetricCalculator(BaseMetricCalculator):
    """
    Calculator for productivity-related metrics
    """

    def calculate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate productivity metrics
        """
        try:
            user_id = context.get("user_id")
            team_id = context.get("team_id")
            start_date = context.get("start_date", timezone.now() - timedelta(days=30))
            end_date = context.get("end_date", timezone.now())

            if not user_id and not team_id:
                raise ValueError("Either user_id or team_id must be provided")

            # Get monitoring data
            monitoring_client = MonitoringServiceClient()

            if user_id:
                sessions_data = monitoring_client.get_user_sessions(
                    user_id, start_date, end_date
                )
                commits_data = monitoring_client.get_user_git_activity(
                    user_id, start_date, end_date
                )
            else:
                sessions_data = monitoring_client.get_team_sessions(
                    team_id, start_date, end_date
                )
                # Get team git activity from management service
                management_client = ManagementServiceClient()
                commits_data = management_client.get_team_git_activity(
                    team_id, start_date, end_date
                )

            # Calculate metrics based on calculation method
            method = self.metric_definition.calculation_method

            if method == "avg_session_duration":
                return self._calculate_avg_session_duration(sessions_data)
            elif method == "commits_per_day":
                return self._calculate_commits_per_day(commits_data)
            elif method == "code_lines_per_day":
                return self._calculate_code_lines_per_day(commits_data)
            elif method == "productivity_score":
                return self._calculate_productivity_score(sessions_data, commits_data)
            else:
                return {"error": f"Unknown calculation method: {method}"}

        except Exception as e:
            logger.error(f"Error calculating productivity metric: {e}")
            return {"error": str(e)}

    def _calculate_avg_session_duration(
        self, sessions_data: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate average session duration"""
        if not sessions_data:
            return {"value": 0, "unit": "minutes", "data_points": 0}

        durations = [
            session.get("session_duration_minutes", 0) for session in sessions_data
        ]
        durations = [d for d in durations if d > 0]  # Filter out invalid durations

        if not durations:
            return {"value": 0, "unit": "minutes", "data_points": 0}

        stats = StatisticalAnalyzer.calculate_basic_stats(durations)

        return {
            "value": round(stats["mean"], 2),
            "unit": "minutes",
            "data_points": len(durations),
            "statistics": stats,
        }

    def _calculate_commits_per_day(self, commits_data: List[Dict]) -> Dict[str, Any]:
        """Calculate commits per day"""
        if not commits_data:
            return {"value": 0, "unit": "commits/day", "data_points": 0}

        # Group commits by date
        df = pd.DataFrame(commits_data)
        if "timestamp" not in df.columns:
            return {"value": 0, "unit": "commits/day", "data_points": 0}

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date

        daily_commits = df.groupby("date").size().values
        stats = StatisticalAnalyzer.calculate_basic_stats(daily_commits)

        return {
            "value": round(stats["mean"], 2),
            "unit": "commits/day",
            "data_points": len(daily_commits),
            "statistics": stats,
        }

    def _calculate_code_lines_per_day(self, commits_data: List[Dict]) -> Dict[str, Any]:
        """Calculate lines of code changed per day"""
        if not commits_data:
            return {"value": 0, "unit": "lines/day", "data_points": 0}

        df = pd.DataFrame(commits_data)
        required_cols = ["timestamp", "insertions", "deletions"]

        if not all(col in df.columns for col in required_cols):
            return {"value": 0, "unit": "lines/day", "data_points": 0}

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date
        df["total_lines"] = df["insertions"] + df["deletions"]

        daily_lines = df.groupby("date")["total_lines"].sum().values
        stats = StatisticalAnalyzer.calculate_basic_stats(daily_lines)

        return {
            "value": round(stats["mean"], 2),
            "unit": "lines/day",
            "data_points": len(daily_lines),
            "statistics": stats,
        }

    def _calculate_productivity_score(
        self, sessions_data: List[Dict], commits_data: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate overall productivity score (0-100)"""
        try:
            # Session-based metrics (weight: 40%)
            session_score = 0
            if sessions_data:
                avg_duration = self._calculate_avg_session_duration(sessions_data)[
                    "value"
                ]
                # Normalize to 0-100 (optimal session: 4-6 hours)
                session_score = min(100, max(0, (avg_duration / 300) * 100))

            # Commit-based metrics (weight: 60%)
            commit_score = 0
            if commits_data:
                commits_result = self._calculate_commits_per_day(commits_data)
                commits_per_day = commits_result["value"]
                # Normalize to 0-100 (optimal: 2-5 commits per day)
                commit_score = min(100, max(0, (commits_per_day / 5) * 100))

            # Weighted overall score
            overall_score = (session_score * 0.4) + (commit_score * 0.6)

            return {
                "value": round(overall_score, 2),
                "unit": "score",
                "components": {
                    "session_score": round(session_score, 2),
                    "commit_score": round(commit_score, 2),
                },
                "data_points": len(sessions_data) + len(commits_data),
            }

        except Exception as e:
            logger.error(f"Error calculating productivity score: {e}")
            return {"value": 0, "unit": "score", "error": str(e)}


class CodeQualityMetricCalculator(BaseMetricCalculator):
    """
    Calculator for code quality metrics
    """

    def calculate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate code quality metrics
        """
        try:
            user_id = context.get("user_id")
            project_id = context.get("project_id")
            start_date = context.get("start_date", timezone.now() - timedelta(days=30))
            end_date = context.get("end_date", timezone.now())

            # Get monitoring data
            monitoring_client = MonitoringServiceClient()
            code_metrics = monitoring_client.get_code_metrics(
                user_id=user_id,
                project_id=project_id,
                start_date=start_date,
                end_date=end_date,
            )

            method = self.metric_definition.calculation_method

            if method == "complexity_score":
                return self._calculate_complexity_score(code_metrics)
            elif method == "test_coverage":
                return self._calculate_test_coverage(code_metrics)
            elif method == "code_quality_trend":
                return self._calculate_quality_trend(code_metrics)
            else:
                return {"error": f"Unknown calculation method: {method}"}

        except Exception as e:
            logger.error(f"Error calculating code quality metric: {e}")
            return {"error": str(e)}

    def _calculate_complexity_score(self, code_metrics: List[Dict]) -> Dict[str, Any]:
        """Calculate average code complexity score"""
        if not code_metrics:
            return {"value": 0, "unit": "complexity", "data_points": 0}

        complexities = [metric.get("complexity_score", 0) for metric in code_metrics]
        complexities = [c for c in complexities if c > 0]

        if not complexities:
            return {"value": 0, "unit": "complexity", "data_points": 0}

        stats = StatisticalAnalyzer.calculate_basic_stats(complexities)

        return {
            "value": round(stats["mean"], 2),
            "unit": "complexity",
            "data_points": len(complexities),
            "statistics": stats,
        }

    def _calculate_test_coverage(self, code_metrics: List[Dict]) -> Dict[str, Any]:
        """Calculate test coverage percentage"""
        # This would require additional test data from monitoring service
        # For now, return a placeholder implementation
        return {
            "value": 0,
            "unit": "percentage",
            "data_points": 0,
            "note": "Test coverage calculation requires additional test metrics",
        }

    def _calculate_quality_trend(self, code_metrics: List[Dict]) -> Dict[str, Any]:
        """Calculate code quality trend over time"""
        if not code_metrics:
            return {"value": 0, "unit": "trend", "data_points": 0}

        df = pd.DataFrame(code_metrics)
        if "calculated_at" not in df.columns or "complexity_score" not in df.columns:
            return {"value": 0, "unit": "trend", "data_points": 0}

        # Sort by time and calculate trend
        df["calculated_at"] = pd.to_datetime(df["calculated_at"])
        df = df.sort_values("calculated_at")

        complexities = df["complexity_score"].tolist()
        trend = TrendAnalyzer.calculate_trend(complexities)

        return {
            "value": round(trend["slope"], 4),
            "unit": "trend",
            "trend_direction": trend["direction"],
            "trend_strength": round(trend["strength"], 3),
            "data_points": len(complexities),
        }


class CollaborationMetricCalculator(BaseMetricCalculator):
    """
    Calculator for team collaboration metrics
    """

    def calculate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate collaboration metrics
        """
        try:
            team_id = context.get("team_id")
            start_date = context.get("start_date", timezone.now() - timedelta(days=30))
            end_date = context.get("end_date", timezone.now())

            if not team_id:
                raise ValueError("team_id is required for collaboration metrics")

            # Get team data
            management_client = ManagementServiceClient()
            monitoring_client = MonitoringServiceClient()

            team_members = management_client.get_team_members(team_id)
            git_events = management_client.get_team_git_activity(
                team_id, start_date, end_date
            )

            method = self.metric_definition.calculation_method

            if method == "collaboration_score":
                return self._calculate_collaboration_score(team_members, git_events)
            elif method == "team_collaboration":
                # Use collaboration_score as default for team_collaboration
                return self._calculate_collaboration_score(team_members, git_events)
            elif method == "code_review_participation":
                return self._calculate_review_participation(git_events)
            elif method == "knowledge_sharing_index":
                return self._calculate_knowledge_sharing(git_events)
            else:
                return {"error": f"Unknown calculation method: {method}"}

        except Exception as e:
            logger.error(f"Error calculating collaboration metric: {e}")
            return {"error": str(e)}

    def _calculate_collaboration_score(
        self, team_members: List[Dict], git_events: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate team collaboration score"""
        if not team_members or not git_events:
            return {"value": 0, "unit": "score", "data_points": 0}

        # Create interaction matrix from git events
        interactions = []
        for event in git_events:
            if event.get("event_type") in ["merge", "pull"]:
                interactions.append(
                    {
                        "user_a": event.get("author_email"),
                        "user_b": event.get("reviewer_email", "unknown"),
                        "interaction_count": 1,
                        "interaction_type": event.get("event_type"),
                    }
                )

        if not interactions:
            return {"value": 0, "unit": "score", "data_points": 0}

        collaboration_score = ProductivityAnalyzer.calculate_team_collaboration_score(
            interactions
        )

        return {
            "value": round(collaboration_score, 2),
            "unit": "score",
            "data_points": len(interactions),
            "team_size": len(team_members),
        }

    def _calculate_review_participation(self, git_events: List[Dict]) -> Dict[str, Any]:
        """Calculate code review participation rate"""
        if not git_events:
            return {"value": 0, "unit": "percentage", "data_points": 0}

        review_events = [
            e for e in git_events if e.get("event_type") in ["merge", "pull"]
        ]
        total_commits = len([e for e in git_events if e.get("event_type") == "commit"])

        if total_commits == 0:
            return {"value": 0, "unit": "percentage", "data_points": 0}

        participation_rate = (len(review_events) / total_commits) * 100

        return {
            "value": round(participation_rate, 2),
            "unit": "percentage",
            "review_events": len(review_events),
            "total_commits": total_commits,
        }

    def _calculate_knowledge_sharing(self, git_events: List[Dict]) -> Dict[str, Any]:
        """Calculate knowledge sharing index"""
        if not git_events:
            return {"value": 0, "unit": "index", "data_points": 0}

        # Count unique authors and files modified
        authors = set()
        files = set()

        for event in git_events:
            if event.get("author_email"):
                authors.add(event["author_email"])
            if event.get("files_changed"):
                files.add(event.get("file_path", "unknown"))

        # Knowledge sharing index: ratio of files touched by multiple authors
        if not files:
            return {"value": 0, "unit": "index", "data_points": 0}

        # Simplified calculation - in reality would need more sophisticated analysis
        sharing_index = min(100, (len(authors) / max(1, len(files))) * 100)

        return {
            "value": round(sharing_index, 2),
            "unit": "index",
            "unique_authors": len(authors),
            "unique_files": len(files),
        }


class PerformanceMetricCalculator(BaseMetricCalculator):
    """
    Calculator for performance-related metrics
    """

    def calculate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate performance metrics
        """
        try:
            start_date = context.get("start_date", timezone.now() - timedelta(days=30))
            end_date = context.get("end_date", timezone.now())

            # Get performance data from PostgreSQL
            performance_data = self._get_performance_data(context, start_date, end_date)

            method = self.metric_definition.calculation_method

            if method == "response_time_avg":
                return self._calculate_avg_response_time(performance_data)
            elif method == "throughput":
                return self._calculate_throughput(performance_data)
            elif method == "error_rate":
                return self._calculate_error_rate(performance_data)
            else:
                return {"error": f"Unknown calculation method: {method}"}

        except Exception as e:
            logger.error(f"Error calculating performance metric: {e}")
            return {"error": str(e)}

    def _get_performance_data(
        self, context: Dict[str, Any], start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get performance data from PostgreSQL TimeSeriesData"""
        try:
            queryset = TimeSeriesData.query_range(
                measurement="system_performance",
                start_time=start_date,
                end_time=end_date,
            )

            # Add context filters
            if context.get("service_name"):
                queryset = queryset.filter(
                    tags__contains={"service": context["service_name"]}
                )

            # Convert to list of dictionaries for compatibility
            results = []
            for data_point in queryset:
                results.append(
                    {
                        "timestamp": data_point.timestamp,
                        "value": data_point.value,
                        "tags": data_point.tags,
                        "fields": data_point.fields,
                        "source": data_point.source,
                    }
                )

            return results
        except Exception as e:
            logger.error(f"Error getting performance data: {e}")
            return []

    def _calculate_avg_response_time(
        self, performance_data: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate average response time"""
        response_times = [
            d["value"] for d in performance_data if d.get("field") == "response_time"
        ]

        if not response_times:
            return {"value": 0, "unit": "ms", "data_points": 0}

        stats = StatisticalAnalyzer.calculate_basic_stats(response_times)

        return {
            "value": round(stats["mean"], 2),
            "unit": "ms",
            "data_points": len(response_times),
            "statistics": stats,
        }

    def _calculate_throughput(self, performance_data: List[Dict]) -> Dict[str, Any]:
        """Calculate request throughput"""
        request_counts = [
            d["value"] for d in performance_data if d.get("field") == "request_count"
        ]

        if not request_counts:
            return {"value": 0, "unit": "requests/sec", "data_points": 0}

        total_requests = sum(request_counts)
        time_period_hours = len(request_counts)  # Assuming hourly data points

        if time_period_hours == 0:
            return {"value": 0, "unit": "requests/sec", "data_points": 0}

        throughput = total_requests / (
            time_period_hours * 3600
        )  # Convert to requests per second

        return {
            "value": round(throughput, 2),
            "unit": "requests/sec",
            "data_points": len(request_counts),
            "total_requests": total_requests,
        }

    def _calculate_error_rate(self, performance_data: List[Dict]) -> Dict[str, Any]:
        """Calculate error rate percentage"""
        total_requests = sum(
            [d["value"] for d in performance_data if d.get("field") == "request_count"]
        )
        error_requests = sum(
            [d["value"] for d in performance_data if d.get("field") == "error_count"]
        )

        if total_requests == 0:
            return {"value": 0, "unit": "percentage", "data_points": 0}

        error_rate = (error_requests / total_requests) * 100

        return {
            "value": round(error_rate, 2),
            "unit": "percentage",
            "total_requests": total_requests,
            "error_requests": error_requests,
        }


class MetricCalculatorFactory:
    """
    Factory class to create appropriate metric calculators
    """

    _calculators = {
        "productivity": ProductivityMetricCalculator,
        "code_quality": CodeQualityMetricCalculator,
        "collaboration": CollaborationMetricCalculator,
        "team_collaboration": CollaborationMetricCalculator,  # Add alias for team_collaboration
        "performance": PerformanceMetricCalculator,
        # Add fallback mappings for other categories using existing calculators
        "security": CodeQualityMetricCalculator,  # Security metrics can use code quality calculator
        "efficiency": ProductivityMetricCalculator,  # Efficiency metrics can use productivity calculator
        "engagement": CollaborationMetricCalculator,  # Engagement metrics can use collaboration calculator
        "learning": ProductivityMetricCalculator,  # Learning metrics can use productivity calculator
        "deployment": PerformanceMetricCalculator,  # Deployment metrics can use performance calculator
        "innovation": ProductivityMetricCalculator,  # Innovation metrics can use productivity calculator
    }

    @classmethod
    def create_calculator(cls, metric_definition) -> BaseMetricCalculator:
        """
        Create appropriate calculator based on metric category
        """
        category = metric_definition.category
        calculator_class = cls._calculators.get(category)

        if not calculator_class:
            raise ValueError(f"No calculator found for category: {category}")

        return calculator_class(metric_definition)

    @classmethod
    def get_available_categories(cls) -> List[str]:
        """
        Get list of available metric categories
        """
        return list(cls._calculators.keys())


class MetricCalculationService:
    """
    Service for orchestrating metric calculations
    """

    @staticmethod
    def calculate_metric(metric_definition, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate a metric using the appropriate calculator
        """
        try:
            calculator = MetricCalculatorFactory.create_calculator(metric_definition)
            result = calculator.calculate(context)

            # Add metadata
            result["metric_id"] = str(metric_definition.id)
            result["metric_name"] = metric_definition.name
            result["calculation_method"] = metric_definition.calculation_method
            result["calculated_at"] = timezone.now().isoformat()

            return result

        except Exception as e:
            logger.error(f"Error calculating metric {metric_definition.name}: {e}")
            return {
                "error": str(e),
                "metric_id": str(metric_definition.id),
                "metric_name": metric_definition.name,
            }

    @staticmethod
    def calculate_multiple_metrics(
        metric_definitions: List, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Calculate multiple metrics efficiently
        """
        results = []

        for metric_definition in metric_definitions:
            result = MetricCalculationService.calculate_metric(
                metric_definition, context
            )
            results.append(result)

        return results


class MetricCalculatorRegistry:
    """Registry for metric calculators"""

    def __init__(self):
        self._calculators = {
            "productivity": "productivity",
            "code_quality": "code_quality",
            "team_collaboration": "team_collaboration",
            "performance": "performance",
            "security": "security",
            "efficiency": "efficiency",
            "engagement": "engagement",
            "learning": "learning",
            "deployment": "deployment",
            "innovation": "innovation",
        }

    def get_calculator(self, metric_type: str):
        """Get calculator by type"""
        if metric_type in self._calculators:
            # Create mock metric definition for the calculator
            from .models import MetricDefinition

            mock_definition = type(
                "MockMetricDefinition",
                (),
                {
                    "calculation_method": metric_type,
                    "parameters": {},
                    "id": None,
                    "name": metric_type,
                    "category": metric_type,  # Add missing category attribute
                },
            )()
            return MetricCalculatorFactory.create_calculator(mock_definition)
        return None

    def get_calculator_by_name(self, metric_name: str):
        """Get calculator by metric name (alias for type)"""
        return self.get_calculator(metric_name)

    def list_calculators(self) -> List[str]:
        """List available calculator types"""
        return list(self._calculators.keys())
