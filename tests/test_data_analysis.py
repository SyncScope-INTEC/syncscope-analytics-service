from io import BytesIO
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from apps.analytics.data_analysis import (
    DataAnalyzer,
    DataFrameProcessor,
    ProductivityAnalyzer,
    ReportGenerator,
    StatisticalAnalyzer,
    TimeSeriesAnalyzer,
    TrendAnalyzer,
)


class TestStatisticalAnalyzer:
    """Test cases for StatisticalAnalyzer"""

    def test_calculate_basic_stats_list(self):
        """Test basic statistics calculation with list input"""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        stats = StatisticalAnalyzer.calculate_basic_stats(data)

        assert stats["count"] == 10
        assert stats["mean"] == 5.5
        assert stats["median"] == 5.5
        assert stats["min"] == 1
        assert stats["max"] == 10
        assert abs(stats["std"] - 3.0276503540974917) < 1e-10

    def test_calculate_basic_stats_pandas_series(self):
        """Test basic statistics calculation with pandas Series"""
        data = pd.Series([10, 20, 30, 40, 50])
        stats = StatisticalAnalyzer.calculate_basic_stats(data)

        assert stats["count"] == 5
        assert stats["mean"] == 30.0
        assert stats["median"] == 30.0
        assert stats["min"] == 10
        assert stats["max"] == 50

    def test_calculate_basic_stats_empty_data(self):
        """Test basic statistics with empty data"""
        stats = StatisticalAnalyzer.calculate_basic_stats([])

        assert stats["count"] == 0
        assert pd.isna(stats["mean"])
        assert pd.isna(stats["median"])

    def test_calculate_percentiles(self):
        """Test percentile calculations"""
        data = list(range(1, 101))  # 1 to 100
        percentiles = StatisticalAnalyzer.calculate_percentiles(data)

        assert percentiles["p25"] == 25.75
        assert percentiles["p50"] == 50.5  # median
        assert percentiles["p75"] == 75.25
        assert percentiles["p90"] == 90.1
        assert percentiles["p95"] == 95.05

    def test_calculate_percentiles_custom(self):
        """Test custom percentile calculations"""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        custom_percentiles = [10, 30, 70, 99]
        percentiles = StatisticalAnalyzer.calculate_percentiles(
            data, custom_percentiles
        )

        assert len(percentiles) == 4
        assert "p10" in percentiles
        assert "p99" in percentiles

    def test_detect_outliers_iqr(self):
        """Test outlier detection using IQR method"""
        # Data with obvious outliers
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100, 200]
        outliers = StatisticalAnalyzer.detect_outliers(data, method="iqr")

        assert 100 in outliers
        assert 200 in outliers
        assert 5 not in outliers

    def test_detect_outliers_zscore(self):
        """Test outlier detection using Z-score method"""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100]
        outliers = StatisticalAnalyzer.detect_outliers(
            data, method="zscore", threshold=2
        )

        assert 100 in outliers
        assert 5 not in outliers

    def test_correlation_analysis(self):
        """Test correlation analysis"""
        data = {
            "x": [1, 2, 3, 4, 5],
            "y": [2, 4, 6, 8, 10],  # Perfect positive correlation
            "z": [5, 4, 3, 2, 1],  # Perfect negative correlation with x
        }
        df = pd.DataFrame(data)

        correlations = StatisticalAnalyzer.correlation_analysis(df)

        assert abs(correlations.loc["x", "y"] - 1.0) < 1e-10  # Perfect positive
        assert abs(correlations.loc["x", "z"] - (-1.0)) < 1e-10  # Perfect negative
        assert abs(correlations.loc["y", "z"] - (-1.0)) < 1e-10


class TestTrendAnalyzer:
    """Test cases for TrendAnalyzer"""

    def test_calculate_trend_increasing(self):
        """Test trend calculation for increasing data"""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        values = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]  # Clear upward trend

        trend = TrendAnalyzer.calculate_trend(dates, values)

        assert trend["direction"] == "increasing"
        assert trend["slope"] > 0
        assert trend["r_squared"] > 0.9  # Strong correlation

    def test_calculate_trend_decreasing(self):
        """Test trend calculation for decreasing data"""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        values = [20, 18, 16, 14, 12, 10, 8, 6, 4, 2]  # Clear downward trend

        trend = TrendAnalyzer.calculate_trend(dates, values)

        assert trend["direction"] == "decreasing"
        assert trend["slope"] < 0
        assert trend["r_squared"] > 0.9  # Strong correlation

    def test_calculate_trend_stable(self):
        """Test trend calculation for stable data"""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        values = [5, 5.1, 4.9, 5.05, 4.95, 5.02, 4.98, 5.01, 4.99, 5.0]

        trend = TrendAnalyzer.calculate_trend(dates, values)

        assert trend["direction"] == "stable"
        assert abs(trend["slope"]) < 0.1

    def test_detect_seasonality_weekly(self):
        """Test weekly seasonality detection"""
        # Create data with weekly pattern (higher on weekdays)
        dates = pd.date_range("2024-01-01", periods=28, freq="D")
        values = []
        for date in dates:
            if date.weekday() < 5:  # Monday-Friday
                values.append(100 + np.random.normal(0, 5))
            else:  # Weekend
                values.append(50 + np.random.normal(0, 5))

        seasonality = TrendAnalyzer.detect_seasonality(dates, values)

        assert "weekly" in seasonality
        assert seasonality["weekly"]["detected"] is True

    def test_detect_seasonality_monthly(self):
        """Test monthly seasonality detection"""
        # Create data spanning multiple months
        dates = pd.date_range("2024-01-01", periods=365, freq="D")
        values = []
        for date in dates:
            # Higher values at beginning/end of month
            if date.day <= 5 or date.day >= 25:
                values.append(100 + np.random.normal(0, 10))
            else:
                values.append(70 + np.random.normal(0, 10))

        seasonality = TrendAnalyzer.detect_seasonality(
            dates, values, periods=["monthly"]
        )

        assert "monthly" in seasonality

    def test_forecast_values_linear(self):
        """Test linear forecasting"""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        values = [i * 2 + 1 for i in range(10)]  # Linear progression

        forecast = TrendAnalyzer.forecast_values(
            dates, values, periods=5, method="linear"
        )

        assert len(forecast["dates"]) == 5
        assert len(forecast["values"]) == 5
        assert forecast["values"][0] > values[-1]  # Should continue trend

    def test_moving_average(self):
        """Test moving average calculation"""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        ma = TrendAnalyzer.calculate_moving_average(values, window=3)

        expected_length = len(values) - 3 + 1  # Rolling window
        assert len(ma) == expected_length
        assert ma[0] == 2.0  # (1+2+3)/3
        assert ma[1] == 3.0  # (2+3+4)/3


class TestProductivityAnalyzer:
    """Test cases for ProductivityAnalyzer"""

    def test_analyze_session_patterns(self):
        """Test session pattern analysis"""
        sessions_data = [
            {"start_time": "2024-01-01T09:00:00Z", "duration": 120},
            {"start_time": "2024-01-01T14:00:00Z", "duration": 90},
            {"start_time": "2024-01-02T09:30:00Z", "duration": 150},
            {"start_time": "2024-01-02T15:00:00Z", "duration": 75},
        ]

        patterns = ProductivityAnalyzer.analyze_session_patterns(sessions_data)

        assert "total_sessions" in patterns
        assert "avg_duration" in patterns
        assert "peak_hours" in patterns
        assert patterns["total_sessions"] == 4
        assert patterns["avg_duration"] == 108.75

    def test_analyze_session_patterns_empty(self):
        """Test session pattern analysis with empty data"""
        patterns = ProductivityAnalyzer.analyze_session_patterns([])

        assert patterns["total_sessions"] == 0
        assert patterns["avg_duration"] == 0

    def test_calculate_productivity_score(self):
        """Test productivity score calculation"""
        metrics = {
            "session_count": 20,
            "avg_session_duration": 90,
            "commit_count": 15,
            "pr_count": 5,
        }

        score = ProductivityAnalyzer.calculate_productivity_score(metrics)

        assert isinstance(score, (int, float))
        assert 0 <= score <= 100

    def test_analyze_commit_patterns(self):
        """Test commit pattern analysis"""
        commits_data = [
            {
                "timestamp": "2024-01-01T10:00:00Z",
                "lines_added": 50,
                "lines_deleted": 10,
            },
            {
                "timestamp": "2024-01-01T15:00:00Z",
                "lines_added": 30,
                "lines_deleted": 5,
            },
            {
                "timestamp": "2024-01-02T11:00:00Z",
                "lines_added": 80,
                "lines_deleted": 20,
            },
        ]

        patterns = ProductivityAnalyzer.analyze_commit_patterns(commits_data)

        assert "total_commits" in patterns
        assert "avg_lines_added" in patterns
        assert "avg_lines_deleted" in patterns
        assert patterns["total_commits"] == 3
        assert patterns["avg_lines_added"] == 53.33

    def test_identify_peak_hours(self):
        """Test peak hours identification"""
        time_data = [
            "2024-01-01T09:00:00Z",
            "2024-01-01T09:30:00Z",
            "2024-01-01T10:00:00Z",
            "2024-01-01T14:00:00Z",
            "2024-01-01T15:00:00Z",
        ]

        peak_hours = ProductivityAnalyzer.identify_peak_hours(time_data)

        assert isinstance(peak_hours, list)
        assert len(peak_hours) > 0
        assert all(0 <= hour <= 23 for hour in peak_hours)


class TestDataFrameProcessor:
    """Test cases for DataFrameProcessor"""

    def test_clean_data(self):
        """Test data cleaning functionality"""
        data = {
            "col1": [1, 2, None, 4, 5],
            "col2": [10, None, 30, 40, 50],
            "col3": [100, 200, 300, 400, 500],
        }
        df = pd.DataFrame(data)

        cleaned_df = DataFrameProcessor.clean_data(df)

        # Should remove rows with any NaN values
        assert len(cleaned_df) < len(df)
        assert not cleaned_df.isnull().any().any()

    def test_normalize_data(self):
        """Test data normalization"""
        data = {"col1": [1, 2, 3, 4, 5], "col2": [10, 20, 30, 40, 50]}
        df = pd.DataFrame(data)

        normalized_df = DataFrameProcessor.normalize_data(df)

        # Check that values are normalized (0-1 range)
        assert normalized_df.min().min() >= 0
        assert normalized_df.max().max() <= 1

    def test_aggregate_by_period_daily(self):
        """Test daily aggregation"""
        dates = pd.date_range("2024-01-01", periods=10, freq="H")
        data = {"timestamp": dates, "value": range(10)}
        df = pd.DataFrame(data)

        aggregated = DataFrameProcessor.aggregate_by_period(df, "timestamp", "D")

        assert len(aggregated) <= len(df)  # Should have fewer rows
        assert "value" in aggregated.columns

    def test_filter_by_date_range(self):
        """Test date range filtering"""
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        data = {"date": dates, "value": range(30)}
        df = pd.DataFrame(data)

        start_date = "2024-01-10"
        end_date = "2024-01-20"

        filtered_df = DataFrameProcessor.filter_by_date_range(
            df, "date", start_date, end_date
        )

        assert len(filtered_df) <= len(df)
        assert filtered_df["date"].min() >= pd.to_datetime(start_date)
        assert filtered_df["date"].max() <= pd.to_datetime(end_date)


class TestTimeSeriesAnalyzer:
    """Test cases for TimeSeriesAnalyzer"""

    def test_resample_data_daily(self):
        """Test daily resampling"""
        dates = pd.date_range("2024-01-01", periods=48, freq="H")  # 2 days hourly
        values = range(48)

        resampled = TimeSeriesAnalyzer.resample_data(dates, values, frequency="D")

        assert len(resampled["dates"]) == 2  # 2 days
        assert len(resampled["values"]) == 2

    def test_detect_anomalies_zscore(self):
        """Test anomaly detection using Z-score"""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        values = [50 + np.random.normal(0, 5) for _ in range(98)] + [
            150,
            200,
        ]  # Add anomalies

        anomalies = TimeSeriesAnalyzer.detect_anomalies(dates, values, method="zscore")

        assert len(anomalies["anomaly_dates"]) > 0
        assert len(anomalies["anomaly_values"]) > 0

    def test_calculate_volatility(self):
        """Test volatility calculation"""
        values = [100, 105, 98, 102, 97, 108, 95, 103]

        volatility = TimeSeriesAnalyzer.calculate_volatility(values)

        assert isinstance(volatility, float)
        assert volatility >= 0

    def test_decompose_trend_seasonal(self):
        """Test trend and seasonal decomposition"""
        # Create data with trend and seasonality
        dates = pd.date_range("2024-01-01", periods=365, freq="D")
        trend = np.linspace(100, 200, 365)
        seasonal = 10 * np.sin(2 * np.pi * np.arange(365) / 7)  # Weekly pattern
        values = trend + seasonal + np.random.normal(0, 2, 365)

        decomposition = TimeSeriesAnalyzer.decompose_trend_seasonal(dates, values)

        assert "trend" in decomposition
        assert "seasonal" in decomposition
        assert "residual" in decomposition


class TestDataAnalyzer:
    """Test cases for DataAnalyzer (main class)"""

    def test_initialization(self):
        """Test DataAnalyzer initialization"""
        analyzer = DataAnalyzer()

        assert hasattr(analyzer, "statistical")
        assert hasattr(analyzer, "trend")
        assert hasattr(analyzer, "productivity")
        assert hasattr(analyzer, "dataframe")
        assert hasattr(analyzer, "timeseries")

    def test_comprehensive_analysis(self):
        """Test comprehensive analysis method"""
        analyzer = DataAnalyzer()

        # Sample data
        data = {
            "date": pd.date_range("2024-01-01", periods=30, freq="D"),
            "productivity_score": np.random.normal(75, 10, 30),
            "session_duration": np.random.normal(90, 20, 30),
        }

        analysis = analyzer.comprehensive_analysis(data)

        assert "statistical_summary" in analysis
        assert "trend_analysis" in analysis
        assert "correlations" in analysis


@pytest.mark.django_db
class TestReportGenerator:
    """Test cases for ReportGenerator"""

    def test_initialization(self):
        """Test ReportGenerator initialization"""
        generator = ReportGenerator()
        assert hasattr(generator, "data_analyzer")

    def test_export_json(self, completed_report):
        """Test JSON export"""
        generator = ReportGenerator()

        content, content_type, filename = generator._export_json(
            completed_report, detailed=False
        )

        assert content_type == "application/json"
        assert filename.endswith(".json")
        assert isinstance(content, bytes)

        # Parse JSON to verify structure
        import json

        data = json.loads(content.decode("utf-8"))
        assert "report_id" in data
        assert "name" in data
        assert "data" in data

    def test_export_csv(self, completed_report):
        """Test CSV export"""
        generator = ReportGenerator()

        content, content_type, filename = generator._export_csv(
            completed_report, detailed=False
        )

        assert content_type == "text/csv"
        assert filename.endswith(".csv")
        assert isinstance(content, bytes)

        # Verify CSV structure
        csv_content = content.decode("utf-8")
        assert "Report Name" in csv_content
        assert completed_report.name in csv_content

    @patch("pandas.ExcelWriter")
    def test_export_excel(self, mock_excel_writer, completed_report):
        """Test Excel export"""
        # Mock Excel writer
        mock_writer_instance = Mock()
        mock_excel_writer.return_value.__enter__.return_value = mock_writer_instance

        generator = ReportGenerator()

        content, content_type, filename = generator._export_excel(
            completed_report, include_charts=True, detailed=False
        )

        expected_content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert content_type == expected_content_type
        assert filename.endswith(".xlsx")

    @patch("reportlab.platypus.SimpleDocTemplate")
    def test_export_pdf(self, mock_doc, completed_report):
        """Test PDF export"""
        # Mock PDF document
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance

        generator = ReportGenerator()

        content, content_type, filename = generator._export_pdf(
            completed_report, include_charts=True, detailed=False
        )

        assert content_type == "application/pdf"
        assert filename.endswith(".pdf")

    def test_export_report_unsupported_format(self, completed_report):
        """Test export with unsupported format"""
        generator = ReportGenerator()

        with pytest.raises(ValueError, match="Unsupported export format"):
            generator.export_report(completed_report, "unsupported_format")

    def test_export_report_json_detailed(self, completed_report):
        """Test detailed JSON export"""
        generator = ReportGenerator()

        content, _, _ = generator._export_json(completed_report, detailed=True)

        # Parse JSON to verify detailed structure
        import json

        data = json.loads(content.decode("utf-8"))
        assert "config" in data  # Should include config in detailed mode


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling"""

    def test_statistical_analyzer_with_invalid_data(self):
        """Test statistical analyzer with invalid data types"""
        with pytest.raises((TypeError, ValueError)):
            StatisticalAnalyzer.calculate_basic_stats("invalid_data")

    def test_trend_analyzer_with_mismatched_lengths(self):
        """Test trend analyzer with mismatched date/value lengths"""
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        values = [1, 2, 3]  # Different length

        with pytest.raises((ValueError, IndexError)):
            TrendAnalyzer.calculate_trend(dates, values)

    def test_dataframe_processor_with_empty_dataframe(self):
        """Test DataFrame processor with empty DataFrame"""
        df = pd.DataFrame()

        cleaned_df = DataFrameProcessor.clean_data(df)
        assert len(cleaned_df) == 0

    def test_productivity_analyzer_with_malformed_data(self):
        """Test productivity analyzer with malformed data"""
        invalid_sessions = [
            {"invalid_key": "invalid_value"},
            {"start_time": "invalid_time"},
        ]

        # Should handle gracefully and return sensible defaults
        patterns = ProductivityAnalyzer.analyze_session_patterns(invalid_sessions)
        assert isinstance(patterns, dict)

    def test_timeseries_analyzer_insufficient_data(self):
        """Test time series analyzer with insufficient data"""
        dates = pd.date_range("2024-01-01", periods=2, freq="D")
        values = [1, 2]

        # Should handle gracefully for operations requiring more data
        volatility = TimeSeriesAnalyzer.calculate_volatility(values)
        assert isinstance(volatility, (int, float))
