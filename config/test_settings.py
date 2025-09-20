"""
Test settings for syncscope-analytics-service project.
"""

from .settings import *

# Override settings for testing
DEBUG = True

# Use in-memory SQLite for faster tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Use dummy cache for testing
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Use console email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["console"],
    },
}

# Test-specific settings
SECRET_KEY = "test-secret-key-for-testing-only"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Disable rate limiting in tests
RATELIMIT_ENABLE = False

# Mock service URLs for testing
AUTH_SERVICE_URL = "http://mock-auth:8001"
MONITORING_SERVICE_URL = "http://mock-monitoring:8002"
MANAGEMENT_SERVICE_URL = "http://mock-management:8003"

# Test JWT settings
JWT_SECRET_KEY = "test-jwt-secret-key"

# Disable ML predictions in tests
ENABLE_ML_PREDICTIONS = False

# Reduce report size limit for testing
MAX_REPORT_SIZE = 1000

# Fast password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]