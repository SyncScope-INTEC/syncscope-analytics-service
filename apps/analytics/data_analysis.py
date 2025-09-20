"""
Data analysis utilities using pandas and numpy for analytics calculations.
GitHub Issue #3: Configurar pandas/numpy para análisis
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Union, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class DataFrameProcessor:
    """
    Core data processing utilities using pandas
    """

    @staticmethod
    def create_dataframe(data: List[Dict], index_col: Optional[str] = None) -> pd.DataFrame:
        """
        Create a pandas DataFrame from a list of dictionaries
        """
        try:
            df = pd.DataFrame(data)
            if index_col and index_col in df.columns:
                df.set_index(index_col, inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error creating DataFrame: {e}")
            return pd.DataFrame()

    @staticmethod
    def clean_data(df: pd.DataFrame, drop_na: bool = True, fill_na_value: Any = 0) -> pd.DataFrame:
        """
        Clean DataFrame by handling missing values
        """
        try:
            if drop_na:
                df = df.dropna()
            else:
                df = df.fillna(fill_na_value)
            return df
        except Exception as e:
            logger.error(f"Error cleaning data: {e}")
            return df

    @staticmethod
    def filter_by_date_range(df: pd.DataFrame, date_col: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Filter DataFrame by date range
        """
        try:
            df[date_col] = pd.to_datetime(df[date_col])
            return df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]
        except Exception as e:
            logger.error(f"Error filtering by date range: {e}")
            return df

    @staticmethod
    def group_by_period(df: pd.DataFrame, date_col: str, period: str = 'D') -> pd.DataFrame:
        """
        Group data by time period (D=daily, W=weekly, M=monthly)
        """
        try:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)
            return df.groupby(pd.Grouper(freq=period))
        except Exception as e:
            logger.error(f"Error grouping by period: {e}")
            return df


class StatisticalAnalyzer:
    """
    Statistical analysis functions using numpy and pandas
    """

    @staticmethod
    def calculate_basic_stats(data: Union[List, pd.Series]) -> Dict[str, float]:
        """
        Calculate basic statistical measures
        """
        try:
            series = pd.Series(data) if isinstance(data, list) else data

            return {
                'count': len(series),
                'mean': float(series.mean()),
                'median': float(series.median()),
                'std': float(series.std()),
                'min': float(series.min()),
                'max': float(series.max()),
                'q25': float(series.quantile(0.25)),
                'q75': float(series.quantile(0.75)),
                'sum': float(series.sum())
            }
        except Exception as e:
            logger.error(f"Error calculating basic stats: {e}")
            return {}

    @staticmethod
    def calculate_percentage_change(current_value: float, previous_value: float) -> float:
        """
        Calculate percentage change between two values
        """
        try:
            if previous_value == 0:
                return 100.0 if current_value > 0 else 0.0
            return ((current_value - previous_value) / previous_value) * 100
        except Exception as e:
            logger.error(f"Error calculating percentage change: {e}")
            return 0.0

    @staticmethod
    def calculate_moving_average(data: Union[List, pd.Series], window: int = 7) -> pd.Series:
        """
        Calculate moving average
        """
        try:
            series = pd.Series(data) if isinstance(data, list) else data
            return series.rolling(window=window, min_periods=1).mean()
        except Exception as e:
            logger.error(f"Error calculating moving average: {e}")
            return pd.Series()

    @staticmethod
    def detect_anomalies(data: Union[List, pd.Series], threshold: float = 2.0) -> List[int]:
        """
        Detect anomalies using standard deviation method
        """
        try:
            series = pd.Series(data) if isinstance(data, list) else data
            mean = series.mean()
            std = series.std()

            # Find values that are more than threshold standard deviations away from mean
            anomalies = []
            for i, value in enumerate(series):
                if abs(value - mean) > threshold * std:
                    anomalies.append(i)

            return anomalies
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []

    @staticmethod
    def calculate_correlation(x: Union[List, pd.Series], y: Union[List, pd.Series]) -> float:
        """
        Calculate correlation coefficient between two variables
        """
        try:
            series_x = pd.Series(x) if isinstance(x, list) else x
            series_y = pd.Series(y) if isinstance(y, list) else y

            return float(series_x.corr(series_y))
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.0


class TrendAnalyzer:
    """
    Trend analysis utilities
    """

    @staticmethod
    def calculate_trend(data: Union[List, pd.Series], periods: int = None) -> Dict[str, Any]:
        """
        Calculate trend direction and strength
        """
        try:
            series = pd.Series(data) if isinstance(data, list) else data

            if len(series) < 2:
                return {'direction': 'insufficient_data', 'strength': 0, 'slope': 0}

            # Calculate linear trend using least squares
            x = np.arange(len(series))
            slope, intercept = np.polyfit(x, series, 1)

            # Determine trend direction
            if abs(slope) < 0.01:
                direction = 'stable'
            elif slope > 0:
                direction = 'increasing'
            else:
                direction = 'decreasing'

            # Calculate R-squared to measure trend strength
            y_pred = slope * x + intercept
            ss_res = np.sum((series - y_pred) ** 2)
            ss_tot = np.sum((series - np.mean(series)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            return {
                'direction': direction,
                'strength': float(r_squared),
                'slope': float(slope),
                'intercept': float(intercept)
            }
        except Exception as e:
            logger.error(f"Error calculating trend: {e}")
            return {'direction': 'error', 'strength': 0, 'slope': 0}

    @staticmethod
    def forecast_simple(data: Union[List, pd.Series], periods: int = 7) -> List[float]:
        """
        Simple linear forecasting
        """
        try:
            series = pd.Series(data) if isinstance(data, list) else data

            if len(series) < 2:
                return [series.iloc[-1]] * periods if len(series) == 1 else [0.0] * periods

            # Calculate linear trend
            x = np.arange(len(series))
            slope, intercept = np.polyfit(x, series, 1)

            # Forecast future values
            future_x = np.arange(len(series), len(series) + periods)
            forecast = slope * future_x + intercept

            return forecast.tolist()
        except Exception as e:
            logger.error(f"Error in simple forecast: {e}")
            return [0.0] * periods


class ProductivityAnalyzer:
    """
    Specialized analytics for developer productivity metrics
    """

    @staticmethod
    def calculate_velocity(commits_per_day: List[int], window_days: int = 7) -> Dict[str, float]:
        """
        Calculate development velocity metrics
        """
        try:
            if not commits_per_day:
                return {'current_velocity': 0, 'average_velocity': 0, 'velocity_trend': 0}

            series = pd.Series(commits_per_day)

            # Current velocity (recent window average)
            current_velocity = series.tail(window_days).mean()

            # Overall average velocity
            average_velocity = series.mean()

            # Velocity trend (comparing recent vs previous periods)
            if len(series) >= window_days * 2:
                recent_avg = series.tail(window_days).mean()
                previous_avg = series.iloc[-window_days*2:-window_days].mean()
                velocity_trend = StatisticalAnalyzer.calculate_percentage_change(recent_avg, previous_avg)
            else:
                velocity_trend = 0

            return {
                'current_velocity': float(current_velocity),
                'average_velocity': float(average_velocity),
                'velocity_trend': float(velocity_trend)
            }
        except Exception as e:
            logger.error(f"Error calculating velocity: {e}")
            return {'current_velocity': 0, 'average_velocity': 0, 'velocity_trend': 0}

    @staticmethod
    def analyze_code_quality_trend(quality_scores: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """
        Analyze code quality trends over time
        """
        try:
            if len(quality_scores) != len(timestamps):
                raise ValueError("Scores and timestamps must have same length")

            df = pd.DataFrame({
                'timestamp': timestamps,
                'quality_score': quality_scores
            })

            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')

            # Calculate trend
            trend = TrendAnalyzer.calculate_trend(df['quality_score'])

            # Calculate quality metrics
            current_quality = quality_scores[-1] if quality_scores else 0
            average_quality = np.mean(quality_scores) if quality_scores else 0

            # Detect quality anomalies
            anomalies = StatisticalAnalyzer.detect_anomalies(quality_scores)

            return {
                'current_quality': float(current_quality),
                'average_quality': float(average_quality),
                'trend': trend,
                'anomaly_count': len(anomalies),
                'anomaly_indices': anomalies
            }
        except Exception as e:
            logger.error(f"Error analyzing code quality trend: {e}")
            return {}

    @staticmethod
    def calculate_team_collaboration_score(interaction_data: List[Dict]) -> float:
        """
        Calculate team collaboration score based on interaction data
        """
        try:
            if not interaction_data:
                return 0.0

            df = pd.DataFrame(interaction_data)

            # Expected columns: 'user_a', 'user_b', 'interaction_count', 'interaction_type'
            required_columns = ['user_a', 'user_b', 'interaction_count']
            if not all(col in df.columns for col in required_columns):
                logger.warning("Missing required columns for collaboration score")
                return 0.0

            # Calculate unique interactions
            unique_pairs = len(df[['user_a', 'user_b']].drop_duplicates())
            total_interactions = df['interaction_count'].sum()

            # Simple collaboration score (can be enhanced)
            if unique_pairs == 0:
                return 0.0

            collaboration_score = min(100.0, (total_interactions / unique_pairs) * 10)

            return float(collaboration_score)
        except Exception as e:
            logger.error(f"Error calculating collaboration score: {e}")
            return 0.0


class TimeSeriesAnalyzer:
    """
    Time series analysis utilities
    """

    @staticmethod
    def resample_timeseries(df: pd.DataFrame, timestamp_col: str, value_col: str, frequency: str = 'D') -> pd.DataFrame:
        """
        Resample time series data to different frequency
        """
        try:
            df[timestamp_col] = pd.to_datetime(df[timestamp_col])
            df.set_index(timestamp_col, inplace=True)

            return df[value_col].resample(frequency).mean().to_frame()
        except Exception as e:
            logger.error(f"Error resampling time series: {e}")
            return pd.DataFrame()

    @staticmethod
    def calculate_seasonality(data: Union[List, pd.Series], period: int = 7) -> Dict[str, Any]:
        """
        Detect seasonality patterns in time series data
        """
        try:
            series = pd.Series(data) if isinstance(data, list) else data

            if len(series) < period * 2:
                return {'has_seasonality': False, 'seasonal_strength': 0}

            # Simple seasonality detection using autocorrelation
            autocorr = series.autocorr(lag=period)

            # Consider significant if autocorrelation > 0.3
            has_seasonality = abs(autocorr) > 0.3
            seasonal_strength = abs(autocorr)

            return {
                'has_seasonality': has_seasonality,
                'seasonal_strength': float(seasonal_strength),
                'period': period
            }
        except Exception as e:
            logger.error(f"Error calculating seasonality: {e}")
            return {'has_seasonality': False, 'seasonal_strength': 0}


def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimize DataFrame memory usage by downcasting numeric types
    """
    try:
        for col in df.columns:
            col_type = df[col].dtype

            if col_type != 'object':
                c_min = df[col].min()
                c_max = df[col].max()

                if str(col_type)[:3] == 'int':
                    if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                        df[col] = df[col].astype(np.int8)
                    elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                        df[col] = df[col].astype(np.int16)
                    elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                        df[col] = df[col].astype(np.int32)
                else:
                    if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                        df[col] = df[col].astype(np.float32)

        return df
    except Exception as e:
        logger.error(f"Error optimizing DataFrame memory: {e}")
        return df