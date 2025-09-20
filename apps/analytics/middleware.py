import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Add security headers to all responses"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Security headers
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # HSTS for HTTPS
        if request.is_secure():
            response["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # CSP for API responses
        if request.path.startswith("/analytics/"):
            response["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'none'; object-src 'none'"
            )

        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Custom rate limiting middleware for analytics endpoints"""

    def process_request(self, request):
        if not getattr(settings, "RATELIMIT_ENABLE", True):
            return None

        # Skip rate limiting for admin and static files
        if request.path.startswith("/admin/") or request.path.startswith("/static/"):
            return None

        # Get client IP
        ip = self.get_client_ip(request)

        # Different rate limits for different endpoints
        if request.path.startswith("/analytics/reports/generate"):
            limit = 10  # 10 report generations per hour
            window = 3600
        elif request.path.startswith("/analytics/reports/export"):
            limit = 20  # 20 exports per hour
            window = 3600
        elif request.path.startswith("/analytics/metrics/calculate"):
            limit = 100  # 100 metric calculations per hour
            window = 3600
        elif request.path.startswith("/analytics/"):
            limit = 200  # 200 requests per hour for other analytics endpoints
            window = 3600
        else:
            return None

        # Create cache key
        cache_key = f"ratelimit_analytics:{ip}:{request.path}"

        # Get current count
        current_count = cache.get(cache_key, 0)

        if current_count >= limit:
            return JsonResponse(
                {
                    "error": "Rate limit exceeded",
                    "detail": f"Too many requests. Limit: {limit}/{window//60}min",
                },
                status=429,
            )

        # Increment counter
        cache.set(cache_key, current_count + 1, window)

        # Store rate limit info for response headers
        request._rate_limit_info = {
            "limit": limit,
            "remaining": max(0, limit - current_count - 1),
            "reset": window,
        }

        return None

    def process_response(self, request, response):
        # Add rate limit headers if info is available
        if hasattr(request, "_rate_limit_info"):
            info = request._rate_limit_info
            response["X-RateLimit-Limit"] = str(info["limit"])
            response["X-RateLimit-Remaining"] = str(info["remaining"])
            response["X-RateLimit-Reset"] = str(info["reset"])

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "127.0.0.1")


class RequestLoggingMiddleware:
    """Log API requests for monitoring and analytics"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        # Log request
        logger.info(
            f"Analytics Request: {request.method} {request.path} from {self.get_client_ip(request)}"
        )

        response = self.get_response(request)

        # Log response with performance metrics
        duration = time.time() - start_time
        logger.info(f"Analytics Response: {response.status_code} in {duration:.3f}s")

        # Log slow requests
        if duration > 5.0:  # Log requests taking more than 5 seconds
            logger.warning(
                f"Slow analytics request: {request.method} {request.path} took {duration:.3f}s"
            )

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "127.0.0.1")


class AnalyticsPerformanceMiddleware:
    """Track performance metrics for analytics operations"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        # Track performance for analytics endpoints
        if request.path.startswith("/analytics/"):
            duration = time.time() - start_time

            # Store performance metrics in cache for monitoring
            endpoint = self._get_endpoint_name(request.path)
            cache_key = f"analytics_perf:{endpoint}"

            # Get existing metrics
            metrics = cache.get(
                cache_key, {"total_requests": 0, "total_time": 0, "avg_time": 0}
            )

            # Update metrics
            metrics["total_requests"] += 1
            metrics["total_time"] += duration
            metrics["avg_time"] = metrics["total_time"] / metrics["total_requests"]

            # Store updated metrics (expire after 1 hour)
            cache.set(cache_key, metrics, 3600)

            # Add performance headers
            response["X-Response-Time"] = f"{duration:.3f}s"

        return response

    def _get_endpoint_name(self, path):
        """Extract endpoint name from path for metrics grouping"""
        path_parts = path.strip("/").split("/")
        if len(path_parts) >= 2:
            return f"{path_parts[0]}_{path_parts[1]}"
        return path_parts[0] if path_parts else "unknown"


class CacheControlMiddleware:
    """Add appropriate cache control headers for analytics responses"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Set cache headers for analytics endpoints
        if request.path.startswith("/analytics/"):
            if request.method == "GET":
                # Cache GET requests for analytics data
                if "/reports/" in request.path or "/metrics/" in request.path:
                    response["Cache-Control"] = "max-age=300, private"  # 5 minutes
                else:
                    response["Cache-Control"] = "max-age=60, private"  # 1 minute
            else:
                # Don't cache POST/PUT/DELETE requests
                response["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response["Pragma"] = "no-cache"
                response["Expires"] = "0"

        return response
