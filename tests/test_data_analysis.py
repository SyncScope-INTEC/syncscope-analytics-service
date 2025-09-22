"""
Tests for data_analysis.py module.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from apps.analytics.data_analysis import (
    DataFrameProcessor,
    ProductivityAnalyzer,
    ReportGenerator,
    StatisticalAnalyzer,
    TimeSeriesAnalyzer,
    TrendAnalyzer,
    optimize_dataframe_memory,
)


class TestDataFrameProcessor:
    """Test DataFrameProcessor class."""

    def test_create_dataframe_from_list(self):
        """Test creating DataFrame from list of dictionaries."""
        data = [
            {"name": "John", "age": 25, "score": 85},
            {"name": "Jane", "age": 30, "score": 92},
            {"name": "Bob", "age": 35, "score": 78},
        ]

        df = DataFrameProcessor.create_dataframe(data)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["name", "age", "score"]
        assert df.iloc[0]["name"] == "John"

    def test_create_dataframe_with_index(self):
        """Test creating DataFrame with index column."""
        data = [
            {"id": 1, "value": 100},
            {"id": 2, "value": 200},
        ]

        df = DataFrameProcessor.create_dataframe(data, index_col="id")

        assert df.index.name == "id"
        assert df.loc[1, "value"] == 100

    def test_create_dataframe_empty_data(self):
        """Test creating DataFrame from empty data."""
        df = DataFrameProcessor.create_dataframe([])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    @patch("apps.analytics.data_analysis.logger")
    def test_create_dataframe_error_handling(self, mock_logger):
        """Test error handling in create_dataframe."""
        # Pass invalid data that will cause an error
        with patch(
            "apps.analytics.data_analysis.pd.DataFrame",
            side_effect=Exception("Test error"),
        ):
            df = DataFrameProcessor.create_dataframe([{"test": "data"}])

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 0
            mock_logger.error.assert_called_once()

    def test_clean_data_drop_na(self):
        """Test cleaning data by dropping NA values."""
        df = pd.DataFrame({"A": [1, 2, np.nan, 4], "B": [5, np.nan, 7, 8]})

        cleaned_df = DataFrameProcessor.clean_data(df, drop_na=True)

        assert len(cleaned_df) == 2  # Only rows without NaN
        assert not cleaned_df.isnull().any().any()

    def test_clean_data_fill_na(self):
        """Test cleaning data by filling NA values."""
        df = pd.DataFrame({"A": [1, 2, np.nan, 4], "B": [5, np.nan, 7, 8]})

        cleaned_df = DataFrameProcessor.clean_data(df, drop_na=False, fill_na_value=0)

        assert len(cleaned_df) == 4  # All original rows
        assert not cleaned_df.isnull().any().any()
        assert cleaned_df.iloc[2, 0] == 0  # NaN filled with 0

    @patch("apps.analytics.data_analysis.logger")
    def test_clean_data_error_handling(self, mock_logger):
        """Test error handling in clean_data."""
        df = pd.DataFrame({"A": [1, 2, 3]})

        with patch.object(df, "dropna", side_effect=Exception("Test error")):
            result_df = DataFrameProcessor.clean_data(df)

            mock_logger.error.assert_called_once()
            # Should return original DataFrame on error
            assert len(result_df) == 3

    def test_filter_by_date_range(self):
        """Test filtering DataFrame by date range."""
        df = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-15", "2024-02-01", "2024-02-15"],
                "value": [10, 20, 30, 40],
            }
        )

        start_date = datetime(2024, 1, 10)
        end_date = datetime(2024, 2, 5)

        filtered_df = DataFrameProcessor.filter_by_date_range(
            df, "date", start_date, end_date
        )

        assert len(filtered_df) == 2
        assert filtered_df.iloc[0]["value"] == 20
        assert filtered_df.iloc[1]["value"] == 30

    @patch("apps.analytics.data_analysis.logger")
    def test_filter_by_date_range_error(self, mock_logger):
        """Test error handling in filter_by_date_range."""
        df = pd.DataFrame({"date": ["invalid-date"], "value": [10]})

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 2, 1)

        result_df = DataFrameProcessor.filter_by_date_range(
            df, "date", start_date, end_date
        )

        mock_logger.error.assert_called_once()
        # Should return original DataFrame on error
        assert len(result_df) == 1

    def test_group_by_period(self):
        """Test grouping data by time period."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=10, freq="D"),
                "value": range(10),
            }
        )

        grouped = DataFrameProcessor.group_by_period(df, "date", "D")

        # Should return a GroupBy object
        assert hasattr(grouped, "sum")

    @patch("apps.analytics.data_analysis.logger")
    def test_group_by_period_error(self, mock_logger):
        """Test error handling in group_by_period."""
        df = pd.DataFrame({"date": ["invalid"], "value": [10]})

        result = DataFrameProcessor.group_by_period(df, "date", "D")

        mock_logger.error.assert_called_once()


class TestStatisticalAnalyzer:
    """Test StatisticalAnalyzer class."""

    def test_calculate_basic_stats_with_list(self):
        """Test calculating basic stats from list."""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        stats = StatisticalAnalyzer.calculate_basic_stats(data)

        assert "mean" in stats
        assert "median" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats
        assert stats["mean"] == 5.5
        assert stats["median"] == 5.5
        assert stats["min"] == 1
        assert stats["max"] == 10

    def test_calculate_basic_stats_with_series(self):
        """Test calculating basic stats from pandas Series."""
        series = pd.Series([2, 4, 6, 8, 10])

        stats = StatisticalAnalyzer.calculate_basic_stats(series)

        assert stats["mean"] == 6.0
        assert stats["median"] == 6.0

    def test_calculate_basic_stats_empty_data(self):
        """Test calculating stats with empty data."""
        stats = StatisticalAnalyzer.calculate_basic_stats([])

        assert isinstance(stats, dict)
        assert len(stats) == 0

    @patch("apps.analytics.data_analysis.logger")
    def test_calculate_basic_stats_error(self, mock_logger):
        """Test error handling in calculate_basic_stats."""
        with patch("pandas.Series.mean", side_effect=Exception("Test error")):
            stats = StatisticalAnalyzer.calculate_basic_stats([1, 2, 3])

            mock_logger.error.assert_called_once()
            assert isinstance(stats, dict)
            assert len(stats) == 0

    def test_calculate_percentage_change_normal(self):
        """Test percentage change calculation."""
        change = StatisticalAnalyzer.calculate_percentage_change(120, 100)
        assert change == 20.0

        change = StatisticalAnalyzer.calculate_percentage_change(80, 100)
        assert change == -20.0

    def test_calculate_percentage_change_zero_previous(self):
        """Test percentage change with zero previous value."""
        change = StatisticalAnalyzer.calculate_percentage_change(50, 0)
        assert change == 100.0

        change = StatisticalAnalyzer.calculate_percentage_change(0, 0)
        assert change == 0.0

    @patch("apps.analytics.data_analysis.logger")
    def test_calculate_percentage_change_error(self, mock_logger):
        """Test error handling in percentage change calculation."""
        with patch("builtins.float", side_effect=Exception("Test error")):
            change = StatisticalAnalyzer.calculate_percentage_change(100, 80)

            mock_logger.error.assert_called_once()
            assert change == 0.0

    def test_calculate_moving_average(self):
        """Test moving average calculation."""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        ma = StatisticalAnalyzer.calculate_moving_average(data, window=3)

        assert isinstance(ma, pd.Series)
        assert len(ma) == 10
        # First value should be just the first element
        assert ma.iloc[0] == 1.0
        # Third value should be average of first 3
        assert ma.iloc[2] == 2.0

    def test_calculate_moving_average_with_series(self):
        """Test moving average with pandas Series."""
        series = pd.Series([2, 4, 6, 8, 10])

        ma = StatisticalAnalyzer.calculate_moving_average(series, window=2)

        assert isinstance(ma, pd.Series)
        assert ma.iloc[1] == 3.0  # (2+4)/2

    @patch("apps.analytics.data_analysis.logger")
    def test_calculate_moving_average_error(self, mock_logger):
        """Test error handling in moving average calculation."""
        with patch("pandas.Series.rolling", side_effect=Exception("Test error")):
            ma = StatisticalAnalyzer.calculate_moving_average([1, 2, 3])

            mock_logger.error.assert_called_once()
            assert isinstance(ma, pd.Series)
            assert len(ma) == 0

    def test_detect_anomalies(self):
        """Test anomaly detection."""
        # Data with clear outliers
        data = [1, 2, 2, 3, 2, 1, 2, 100, 2, 1]  # 100 is an outlier

        anomalies = StatisticalAnalyzer.detect_anomalies(data, threshold=2.0)

        assert isinstance(anomalies, list)
        assert 7 in anomalies  # Index of value 100

    def test_detect_anomalies_no_anomalies(self):
        """Test anomaly detection with no anomalies."""
        data = [1, 2, 2, 3, 2, 1, 2, 3, 2, 1]  # No clear outliers

        anomalies = StatisticalAnalyzer.detect_anomalies(data, threshold=3.0)

        assert isinstance(anomalies, list)
        # With high threshold, should find no anomalies
        assert len(anomalies) == 0

    @patch("apps.analytics.data_analysis.logger")
    def test_detect_anomalies_error(self, mock_logger):
        """Test error handling in anomaly detection."""
        with patch("pandas.Series.mean", side_effect=Exception("Test error")):
            anomalies = StatisticalAnalyzer.detect_anomalies([1, 2, 3])

            mock_logger.error.assert_called_once()
            assert isinstance(anomalies, list)
            assert len(anomalies) == 0

    def test_calculate_correlation(self):
        """Test correlation calculation."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]  # Perfect positive correlation

        corr = StatisticalAnalyzer.calculate_correlation(x, y)

        assert isinstance(corr, float)
        assert abs(corr - 1.0) < 0.001  # Should be close to 1

    def test_calculate_correlation_negative(self):
        """Test negative correlation calculation."""
        x = [1, 2, 3, 4, 5]
        y = [5, 4, 3, 2, 1]  # Perfect negative correlation

        corr = StatisticalAnalyzer.calculate_correlation(x, y)

        assert isinstance(corr, float)
        assert abs(corr - (-1.0)) < 0.001  # Should be close to -1

    def test_calculate_correlation_with_series(self):
        """Test correlation with pandas Series."""
        x = pd.Series([1, 2, 3, 4])
        y = pd.Series([1, 2, 3, 4])

        corr = StatisticalAnalyzer.calculate_correlation(x, y)

        assert abs(corr - 1.0) < 0.001

    @patch("apps.analytics.data_analysis.logger")
    def test_calculate_correlation_error(self, mock_logger):
        """Test error handling in correlation calculation."""
        with patch("pandas.Series.corr", side_effect=Exception("Test error")):
            corr = StatisticalAnalyzer.calculate_correlation([1, 2, 3], [4, 5, 6])

            mock_logger.error.assert_called_once()
            assert corr == 0.0


class TestTimeSeriesAnalyzer:
    """Test TimeSeriesAnalyzer class."""

    def test_create_time_series(self):
        """Test creating time series from data."""
        data = [10, 20, 15, 25, 30]
        dates = pd.date_range("2024-01-01", periods=5, freq="D")

        ts = TimeSeriesAnalyzer.create_time_series(data, dates)

        assert isinstance(ts, pd.Series)
        assert len(ts) == 5
        assert ts.iloc[0] == 10

    def test_create_time_series_default_dates(self):
        """Test creating time series with default dates."""
        data = [10, 20, 30]

        ts = TimeSeriesAnalyzer.create_time_series(data)

        assert isinstance(ts, pd.Series)
        assert len(ts) == 3
        # Should have generated dates
        assert hasattr(ts.index, "date")

    @patch("apps.analytics.data_analysis.logger")
    def test_create_time_series_error(self, mock_logger):
        """Test error handling in create_time_series."""
        with patch("pandas.Series", side_effect=Exception("Test error")):
            ts = TimeSeriesAnalyzer.create_time_series([1, 2, 3])

            mock_logger.error.assert_called_once()
            assert isinstance(ts, pd.Series)


class TestTrendAnalyzer:
    """Test TrendAnalyzer class."""

    def test_calculate_trend_increasing(self):
        """Test calculating trend for increasing data."""
        data = [1, 2, 3, 4, 5]

        trend = TrendAnalyzer.calculate_trend(data)

        assert trend["direction"] == "increasing"
        assert trend["slope"] > 0

    def test_calculate_trend_decreasing(self):
        """Test calculating trend for decreasing data."""
        data = [5, 4, 3, 2, 1]

        trend = TrendAnalyzer.calculate_trend(data)

        assert trend["direction"] == "decreasing"
        assert trend["slope"] < 0

    def test_calculate_trend_stable(self):
        """Test calculating trend for stable data."""
        data = [5, 5, 5, 5, 5]

        trend = TrendAnalyzer.calculate_trend(data)

        assert trend["direction"] == "stable"
        assert abs(trend["slope"]) < 0.1

    def test_calculate_trend_insufficient_data(self):
        """Test calculating trend with insufficient data."""
        trend = TrendAnalyzer.calculate_trend([1])

        assert trend["direction"] == "insufficient_data"
        assert trend["slope"] == 0

    @patch("apps.analytics.data_analysis.logger")
    def test_calculate_trend_error(self, mock_logger):
        """Test error handling in calculate_trend."""
        with patch("numpy.polyfit", side_effect=Exception("Test error")):
            trend = TrendAnalyzer.calculate_trend([1, 2, 3])

            mock_logger.error.assert_called_once()
            assert trend["direction"] == "error"


@pytest.mark.django_db
class TestDataAnalysisIntegration:
    """Integration tests for data analysis components."""

    def test_full_analysis_pipeline(self):
        """Test complete data analysis pipeline."""
        # Create sample data
        raw_data = [
            {"date": "2024-01-01", "commits": 5, "loc": 100},
            {"date": "2024-01-02", "commits": 8, "loc": 150},
            {"date": "2024-01-03", "commits": 6, "loc": 120},
            {"date": "2024-01-04", "commits": 7, "loc": 140},
            {"date": "2024-01-05", "commits": 9, "loc": 180},
        ]

        # Step 1: Create DataFrame
        df = DataFrameProcessor.create_dataframe(raw_data)
        assert len(df) == 5

        # Step 2: Clean data (should be clean already)
        clean_df = DataFrameProcessor.clean_data(df)
        assert len(clean_df) == 5

        # Step 3: Calculate statistics
        commit_stats = StatisticalAnalyzer.calculate_basic_stats(df["commits"])
        assert commit_stats["mean"] == 7.0

        # Step 4: Trend analysis
        commit_trend = TrendAnalyzer.calculate_trend(df["commits"].tolist())
        assert commit_trend["direction"] in ["increasing", "decreasing", "stable"]

        # Step 5: Velocity analysis
        velocity_metrics = ProductivityAnalyzer.calculate_velocity(
            df["commits"].tolist()
        )
        assert velocity_metrics["average_velocity"] == 7.0

    def test_date_filtering_integration(self):
        """Test date filtering integration."""
        # Create DataFrame with date range
        df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=10, freq="D"),
                "value": range(10),
            }
        )

        # Filter to middle 5 days
        start_date = datetime(2024, 1, 3)
        end_date = datetime(2024, 1, 7)

        filtered_df = DataFrameProcessor.filter_by_date_range(
            df, "date", start_date, end_date
        )

        assert len(filtered_df) == 5
        assert filtered_df["value"].min() == 2
        assert filtered_df["value"].max() == 6


class TestTrendAnalyzer:
    """Test TrendAnalyzer class."""

    def test_calculate_trend_increasing(self):
        """Test calculating trend for increasing data."""
        data = [1, 2, 3, 4, 5]

        trend = TrendAnalyzer.calculate_trend(data)

        assert trend["direction"] == "increasing"
        assert trend["slope"] > 0
        assert "strength" in trend
        assert "intercept" in trend

    def test_calculate_trend_decreasing(self):
        """Test calculating trend for decreasing data."""
        data = [5, 4, 3, 2, 1]

        trend = TrendAnalyzer.calculate_trend(data)

        assert trend["direction"] == "decreasing"
        assert trend["slope"] < 0

    def test_calculate_trend_stable(self):
        """Test calculating trend for stable data."""
        data = [5.01, 5.02, 4.99, 5.01, 5.00]  # Very small variations

        trend = TrendAnalyzer.calculate_trend(data)

        assert trend["direction"] == "stable"
        assert abs(trend["slope"]) < 0.01

    def test_calculate_trend_insufficient_data(self):
        """Test calculating trend with insufficient data."""
        trend = TrendAnalyzer.calculate_trend([1])

        assert trend["direction"] == "insufficient_data"
        assert trend["slope"] == 0
        assert trend["strength"] == 0

    def test_calculate_trend_empty_data(self):
        """Test calculating trend with empty data."""
        trend = TrendAnalyzer.calculate_trend([])

        assert trend["direction"] == "insufficient_data"
        assert trend["slope"] == 0

    def test_calculate_trend_with_series(self):
        """Test calculating trend with pandas Series."""
        data = pd.Series([10, 20, 30, 40, 50])

        trend = TrendAnalyzer.calculate_trend(data)

        assert trend["direction"] == "increasing"
        assert trend["slope"] > 0

    def test_forecast_simple_increasing(self):
        """Test simple forecasting with increasing trend."""
        data = [1, 2, 3, 4, 5]

        forecast = TrendAnalyzer.forecast_simple(data, periods=3)

        assert len(forecast) == 3
        assert isinstance(forecast, list)
        assert all(isinstance(x, float) for x in forecast)
        # Should continue increasing trend
        assert forecast[0] > 5

    def test_forecast_simple_insufficient_data(self):
        """Test forecasting with insufficient data."""
        # Single point
        forecast = TrendAnalyzer.forecast_simple([5], periods=3)
        assert forecast == [5, 5, 5]

        # Empty data
        forecast = TrendAnalyzer.forecast_simple([], periods=3)
        assert forecast == [0.0, 0.0, 0.0]

    def test_forecast_simple_with_series(self):
        """Test forecasting with pandas Series."""
        data = pd.Series([10, 15, 20, 25])

        forecast = TrendAnalyzer.forecast_simple(data, periods=2)

        assert len(forecast) == 2
        assert forecast[0] > 25  # Should continue trend

    @patch("apps.analytics.data_analysis.logger")
    def test_calculate_trend_error(self, mock_logger):
        """Test error handling in calculate_trend."""
        with patch("numpy.polyfit", side_effect=Exception("Test error")):
            trend = TrendAnalyzer.calculate_trend([1, 2, 3])

            mock_logger.error.assert_called_once()
            assert trend["direction"] == "error"
            assert trend["slope"] == 0

    @patch("apps.analytics.data_analysis.logger")
    def test_forecast_simple_error(self, mock_logger):
        """Test error handling in forecast_simple."""
        with patch("numpy.polyfit", side_effect=Exception("Test error")):
            forecast = TrendAnalyzer.forecast_simple([1, 2, 3], periods=2)

            mock_logger.error.assert_called_once()
            assert forecast == [0.0, 0.0]


class TestProductivityAnalyzer:
    """Test ProductivityAnalyzer class."""

    def test_calculate_velocity_normal_data(self):
        """Test calculating velocity with normal data."""
        commits_per_day = [3, 5, 4, 6, 7, 5, 8, 6, 7, 9, 5, 6, 8, 7]

        velocity = ProductivityAnalyzer.calculate_velocity(
            commits_per_day, window_days=7
        )

        assert "current_velocity" in velocity
        assert "average_velocity" in velocity
        assert "velocity_trend" in velocity
        assert velocity["current_velocity"] > 0
        assert velocity["average_velocity"] > 0

    def test_calculate_velocity_empty_data(self):
        """Test calculating velocity with empty data."""
        velocity = ProductivityAnalyzer.calculate_velocity([])

        assert velocity["current_velocity"] == 0
        assert velocity["average_velocity"] == 0
        assert velocity["velocity_trend"] == 0

    def test_calculate_velocity_insufficient_for_trend(self):
        """Test velocity calculation with insufficient data for trend."""
        commits_per_day = [3, 5, 4, 6]  # Less than 2 * window_days

        velocity = ProductivityAnalyzer.calculate_velocity(
            commits_per_day, window_days=7
        )

        assert velocity["velocity_trend"] == 0

    def test_analyze_code_quality_trend(self):
        """Test analyzing code quality trends."""
        quality_scores = [85.5, 87.2, 84.1, 88.9, 86.3, 89.1]
        timestamps = [
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 2, 12, 0),
            datetime(2024, 1, 3, 12, 0),
            datetime(2024, 1, 4, 12, 0),
            datetime(2024, 1, 5, 12, 0),
            datetime(2024, 1, 6, 12, 0),
        ]

        analysis = ProductivityAnalyzer.analyze_code_quality_trend(
            quality_scores, timestamps
        )

        assert "current_quality" in analysis
        assert "average_quality" in analysis
        assert "trend" in analysis
        assert "anomaly_count" in analysis
        assert "anomaly_indices" in analysis
        assert analysis["current_quality"] == 89.1

    def test_analyze_code_quality_trend_mismatched_lengths(self):
        """Test error handling with mismatched score and timestamp lengths."""
        quality_scores = [85, 87, 84]
        timestamps = [datetime(2024, 1, 1), datetime(2024, 1, 2)]  # One less

        analysis = ProductivityAnalyzer.analyze_code_quality_trend(
            quality_scores, timestamps
        )

        assert analysis == {}

    def test_calculate_team_collaboration_score(self):
        """Test calculating team collaboration score."""
        interaction_data = [
            {
                "user_a": "user1",
                "user_b": "user2",
                "interaction_count": 5,
                "interaction_type": "code_review",
            },
            {
                "user_a": "user1",
                "user_b": "user3",
                "interaction_count": 3,
                "interaction_type": "pair_programming",
            },
            {
                "user_a": "user2",
                "user_b": "user3",
                "interaction_count": 7,
                "interaction_type": "code_review",
            },
        ]

        score = ProductivityAnalyzer.calculate_team_collaboration_score(
            interaction_data
        )

        assert isinstance(score, float)
        assert score >= 0
        assert score <= 100

    def test_calculate_team_collaboration_score_empty_data(self):
        """Test collaboration score with empty data."""
        score = ProductivityAnalyzer.calculate_team_collaboration_score([])

        assert score == 0.0

    def test_calculate_team_collaboration_score_missing_columns(self):
        """Test collaboration score with missing required columns."""
        interaction_data = [
            {"user_a": "user1", "interaction_count": 5},  # Missing user_b
        ]

        score = ProductivityAnalyzer.calculate_team_collaboration_score(
            interaction_data
        )

        assert score == 0.0

    @patch("apps.analytics.data_analysis.logger")
    def test_calculate_velocity_error(self, mock_logger):
        """Test error handling in velocity calculation."""
        with patch("pandas.Series.mean", side_effect=Exception("Test error")):
            velocity = ProductivityAnalyzer.calculate_velocity([1, 2, 3])

            mock_logger.error.assert_called_once()
            assert velocity["current_velocity"] == 0

    @patch("apps.analytics.data_analysis.logger")
    def test_analyze_code_quality_trend_error(self, mock_logger):
        """Test error handling in quality trend analysis."""
        with patch("pandas.DataFrame", side_effect=Exception("Test error")):
            analysis = ProductivityAnalyzer.analyze_code_quality_trend(
                [85, 87], [datetime.now(), datetime.now()]
            )

            mock_logger.error.assert_called_once()
            assert analysis == {}

    @patch("apps.analytics.data_analysis.logger")
    def test_calculate_team_collaboration_score_error(self, mock_logger):
        """Test error handling in collaboration score calculation."""
        with patch("pandas.DataFrame", side_effect=Exception("Test error")):
            score = ProductivityAnalyzer.calculate_team_collaboration_score(
                [{"user_a": "a", "user_b": "b", "interaction_count": 1}]
            )

            mock_logger.error.assert_called_once()
            assert score == 0.0


class TestTimeSeriesAnalyzer:
    """Test TimeSeriesAnalyzer class."""

    def test_resample_timeseries_daily(self):
        """Test resampling time series to daily frequency."""
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01 00:00", periods=48, freq="H"),
                "value": range(48),
            }
        )

        resampled = TimeSeriesAnalyzer.resample_timeseries(
            df, "timestamp", "value", "D"
        )

        assert len(resampled) == 2  # 2 full days
        assert "value" in resampled.columns

    def test_resample_timeseries_hourly(self):
        """Test resampling time series to hourly frequency."""
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2024-01-01 00:00", periods=120, freq="T"
                ),  # 2 hours of minutes
                "value": range(120),
            }
        )

        resampled = TimeSeriesAnalyzer.resample_timeseries(
            df, "timestamp", "value", "H"
        )

        assert len(resampled) == 2

    def test_calculate_seasonality_with_pattern(self):
        """Test seasonality detection with a clear pattern."""
        # Create data with weekly pattern
        data = [10, 5, 5, 5, 5, 5, 15] * 4  # 4 weeks of pattern

        seasonality = TimeSeriesAnalyzer.calculate_seasonality(data, period=7)

        assert "has_seasonality" in seasonality
        assert "seasonal_strength" in seasonality
        assert "period" in seasonality
        assert seasonality["period"] == 7
        assert isinstance(seasonality["has_seasonality"], bool)

    def test_calculate_seasonality_no_pattern(self):
        """Test seasonality detection with random data."""
        # Random data with no pattern
        np.random.seed(42)
        data = np.random.normal(10, 2, 28).tolist()

        seasonality = TimeSeriesAnalyzer.calculate_seasonality(data, period=7)

        assert (
            seasonality["has_seasonality"] is False
            or seasonality["seasonal_strength"] < 0.3
        )

    def test_calculate_seasonality_insufficient_data(self):
        """Test seasonality detection with insufficient data."""
        data = [1, 2, 3]  # Less than 2 periods

        seasonality = TimeSeriesAnalyzer.calculate_seasonality(data, period=7)

        assert seasonality["has_seasonality"] is False
        assert seasonality["seasonal_strength"] == 0

    def test_calculate_seasonality_with_series(self):
        """Test seasonality detection with pandas Series."""
        data = pd.Series([10, 5, 5, 5, 5, 5, 15] * 3)

        seasonality = TimeSeriesAnalyzer.calculate_seasonality(data, period=7)

        assert "has_seasonality" in seasonality

    @patch("apps.analytics.data_analysis.logger")
    def test_resample_timeseries_error(self, mock_logger):
        """Test error handling in resample_timeseries."""
        df = pd.DataFrame({"timestamp": ["invalid_date"], "value": [1]})

        with patch("pandas.to_datetime", side_effect=Exception("Test error")):
            result = TimeSeriesAnalyzer.resample_timeseries(df, "timestamp", "value")

            mock_logger.error.assert_called_once()
            assert result.empty

    @patch("apps.analytics.data_analysis.logger")
    def test_calculate_seasonality_error(self, mock_logger):
        """Test error handling in calculate_seasonality."""
        with patch("pandas.Series.autocorr", side_effect=Exception("Test error")):
            seasonality = TimeSeriesAnalyzer.calculate_seasonality(
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
            )

            mock_logger.error.assert_called_once()
            assert seasonality["has_seasonality"] is False
            assert seasonality["seasonal_strength"] == 0


class TestOptimizeDataframeMemory:
    """Test optimize_dataframe_memory utility function."""

    def test_optimize_int_columns(self):
        """Test optimization of integer columns."""
        df = pd.DataFrame(
            {
                "small_int": [1, 2, 3, 4, 5],  # Can be int8
                "medium_int": [1000, 2000, 3000, 4000, 5000],  # Needs int16 or int32
                "large_int": [100000, 200000, 300000, 400000, 500000],  # Needs int32
            }
        )

        optimized = optimize_dataframe_memory(df)

        assert optimized["small_int"].dtype in [np.int8, np.int16, np.int32]
        assert len(optimized) == len(df)

    def test_optimize_float_columns(self):
        """Test optimization of float columns."""
        df = pd.DataFrame(
            {
                "float_col": [1.1, 2.2, 3.3, 4.4, 5.5],
                "string_col": ["a", "b", "c", "d", "e"],
            }
        )

        optimized = optimize_dataframe_memory(df)

        # Float column should be optimized
        assert optimized["float_col"].dtype in [np.float32, np.float64]
        # String column should remain unchanged
        assert optimized["string_col"].dtype == "object"

    def test_optimize_mixed_types(self):
        """Test optimization with mixed data types."""
        df = pd.DataFrame(
            {
                "int_col": [1, 2, 3],
                "float_col": [1.1, 2.2, 3.3],
                "str_col": ["x", "y", "z"],
                "bool_col": [True, False, True],
            }
        )

        optimized = optimize_dataframe_memory(df)

        assert len(optimized.columns) == 4
        assert optimized["str_col"].dtype == "object"

    def test_optimize_empty_dataframe(self):
        """Test optimization with empty DataFrame."""
        df = pd.DataFrame()

        optimized = optimize_dataframe_memory(df)

        assert optimized.empty

    @patch("apps.analytics.data_analysis.logger")
    def test_optimize_dataframe_memory_error(self, mock_logger):
        """Test error handling in optimize_dataframe_memory."""
        df = pd.DataFrame({"col": [1, 2, 3]})

        with patch("pandas.Series.min", side_effect=Exception("Test error")):
            result = optimize_dataframe_memory(df)

            mock_logger.error.assert_called_once()
            # Should return original DataFrame on error
            assert len(result) == 3


@pytest.mark.django_db
class TestReportGenerator:
    """Test ReportGenerator class."""

    def test_init(self):
        """Test ReportGenerator initialization."""
        with patch("apps.analytics.data_analysis.DataAnalyzer") as mock_analyzer:
            generator = ReportGenerator()
            assert hasattr(generator, "data_analyzer")
            mock_analyzer.assert_called_once()

    def test_export_report_json(self, report):
        """Test exporting report as JSON."""
        with patch("apps.analytics.data_analysis.DataAnalyzer"):
            generator = ReportGenerator()

            content, content_type, filename = generator.export_report(report, "json")

            assert content_type == "application/json"
            assert filename.endswith(".json")

    def test_export_report_csv(self, report):
        """Test exporting report as CSV."""
        with patch("apps.analytics.data_analysis.DataAnalyzer"):
            generator = ReportGenerator()

            content, content_type, filename = generator.export_report(report, "csv")

            assert content_type == "text/csv"
            assert filename.endswith(".csv")

    def test_export_report_unsupported_format(self, report):
        """Test exporting report with unsupported format."""
        with patch("apps.analytics.data_analysis.DataAnalyzer"):
            generator = ReportGenerator()

            with pytest.raises(ValueError, match="Unsupported export format"):
                generator.export_report(report, "unsupported_format")

    def test_export_json(self, report):
        """Test JSON export functionality."""
        with patch("apps.analytics.data_analysis.DataAnalyzer"):
            generator = ReportGenerator()

            content, content_type, filename = generator._export_json(
                report, detailed=True
            )

            assert content_type == "application/json"
            assert filename.endswith(".json")
            assert report.name in filename

            # Parse JSON to verify structure
            import json

            data = json.loads(content.decode("utf-8"))
            assert "report_id" in data
            assert "name" in data
            assert "config" in data  # Should include config when detailed=True

    def test_export_csv(self, report):
        """Test CSV export functionality."""
        with patch("apps.analytics.data_analysis.DataAnalyzer"):
            generator = ReportGenerator()

            content, content_type, filename = generator._export_csv(
                report, detailed=False
            )

            assert content_type == "text/csv"
            assert filename.endswith(".csv")

            # Verify CSV content
            csv_content = content.decode("utf-8")
            assert report.name in csv_content
            assert report.type in csv_content

    def test_export_excel(self, report):
        """Test Excel export functionality."""
        with patch("apps.analytics.data_analysis.DataAnalyzer"):
            generator = ReportGenerator()

            content, content_type, filename = generator._export_excel(
                report, include_charts=True, detailed=True
            )

            assert (
                content_type
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            assert filename.endswith(".xlsx")
            assert isinstance(content, bytes)

    def test_export_pdf(self, report):
        """Test PDF export functionality."""
        with patch("apps.analytics.data_analysis.DataAnalyzer"):
            generator = ReportGenerator()

            content, content_type, filename = generator._export_pdf(
                report, include_charts=True, detailed=True
            )

            assert content_type == "application/pdf"
            assert filename.endswith(".pdf")
            assert isinstance(content, bytes)
            # PDF should start with PDF header
            assert content.startswith(b"%PDF")

    def test_export_report_error(self, report):
        """Test error handling in export_report."""
        with patch("apps.analytics.data_analysis.DataAnalyzer"):
            generator = ReportGenerator()

            with patch.object(
                generator, "_export_json", side_effect=Exception("Export error")
            ):
                with pytest.raises(Exception, match="Export error"):
                    generator.export_report(report, "json")
