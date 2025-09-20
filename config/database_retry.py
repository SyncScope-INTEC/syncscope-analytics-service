import functools
import logging
import time
from typing import Any, Callable

from django.db import transaction
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)


def atomic_with_retry(max_retries: int = 3, delay: float = 0.5) -> Callable:
    """
    Decorator that wraps database operations in atomic transactions with retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    with transaction.atomic():
                        return func(*args, **kwargs)
                except OperationalError as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {delay} seconds..."
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"Database operation failed after {max_retries + 1} attempts: {e}")
                        raise
                except Exception as e:
                    # Don't retry for non-operational errors
                    logger.error(f"Non-retryable database error: {e}")
                    raise

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def retry_on_database_error(max_retries: int = 3, delay: float = 0.5) -> Callable:
    """
    Simple retry decorator for database operations without atomic wrapper.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {delay} seconds..."
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"Database operation failed after {max_retries + 1} attempts: {e}")
                        raise
                except Exception as e:
                    # Don't retry for non-operational errors
                    logger.error(f"Non-retryable database error: {e}")
                    raise

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator