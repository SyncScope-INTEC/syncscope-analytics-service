"""
Database mixins for the Analytics Service with retry logic and reliability features.
"""

import logging
from typing import Any

from django.db import models

from config.database_retry import atomic_with_retry, retry_on_database_error

logger = logging.getLogger(__name__)


class RetryableManager(models.Manager):
    """Custom manager with retry logic for database operations"""

    @retry_on_database_error(max_retries=3)
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    @retry_on_database_error(max_retries=3)
    def filter(self, *args, **kwargs):
        return super().filter(*args, **kwargs)

    @retry_on_database_error(max_retries=3)
    def create(self, *args, **kwargs):
        return super().create(*args, **kwargs)

    @retry_on_database_error(max_retries=3)
    def get_or_create(self, *args, **kwargs):
        return super().get_or_create(*args, **kwargs)

    @retry_on_database_error(max_retries=3)
    def update_or_create(self, *args, **kwargs):
        return super().update_or_create(*args, **kwargs)

    @retry_on_database_error(max_retries=3)
    def bulk_create(self, *args, **kwargs):
        return super().bulk_create(*args, **kwargs)

    @retry_on_database_error(max_retries=3)
    def bulk_update(self, *args, **kwargs):
        return super().bulk_update(*args, **kwargs)

    @retry_on_database_error(max_retries=3)
    def count(self):
        return super().count()

    @retry_on_database_error(max_retries=3)
    def exists(self):
        return super().exists()


class RetryableModelMixin(models.Model):
    """Mixin to add retry logic to model operations"""

    objects = RetryableManager()

    class Meta:
        abstract = True

    @atomic_with_retry()
    def save(self, *args, **kwargs):
        """Save with retry logic"""
        try:
            super().save(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error saving {self.__class__.__name__}: {e}")
            raise

    @atomic_with_retry()
    def delete(self, *args, **kwargs):
        """Delete with retry logic"""
        try:
            return super().delete(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting {self.__class__.__name__}: {e}")
            raise

    @classmethod
    @retry_on_database_error(max_retries=3)
    def get_by_id(cls, obj_id):
        """Get object by ID with retry logic"""
        try:
            return cls.objects.get(id=obj_id)
        except cls.DoesNotExist:
            logger.warning(f"{cls.__name__} with id {obj_id} does not exist")
            raise

    def refresh_from_db_with_retry(self, fields=None):
        """Refresh from database with retry logic"""

        @retry_on_database_error(max_retries=3)
        def _refresh():
            self.refresh_from_db(fields=fields)

        return _refresh()


class TimestampMixin(models.Model):
    """Mixin to add created_at and updated_at timestamps"""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """Mixin to add soft delete functionality"""

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete the object"""
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using)

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete the object"""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restore a soft-deleted object"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class SoftDeleteManager(RetryableManager):
    """Manager for soft delete functionality"""

    def get_queryset(self):
        """Return only non-deleted objects by default"""
        return super().get_queryset().filter(is_deleted=False)

    def with_deleted(self):
        """Return all objects including deleted ones"""
        return super().get_queryset()

    def deleted_only(self):
        """Return only deleted objects"""
        return super().get_queryset().filter(is_deleted=True)


class CacheableMixin:
    """Mixin to add caching functionality to models"""

    CACHE_TTL = 300  # 5 minutes default

    @classmethod
    def get_cache_key(cls, identifier: Any) -> str:
        """Generate cache key for the model instance"""
        return f"{cls.__name__.lower()}:{identifier}"

    def get_instance_cache_key(self) -> str:
        """Get cache key for this instance"""
        return self.get_cache_key(self.pk)

    def cache_instance(self, ttl: int = None):
        """Cache this instance"""
        from django.core.cache import cache

        cache_key = self.get_instance_cache_key()
        cache.set(cache_key, self, ttl or self.CACHE_TTL)

    @classmethod
    def get_from_cache(cls, identifier: Any):
        """Get instance from cache"""
        from django.core.cache import cache

        cache_key = cls.get_cache_key(identifier)
        return cache.get(cache_key)

    def invalidate_cache(self):
        """Remove this instance from cache"""
        from django.core.cache import cache

        cache_key = self.get_instance_cache_key()
        cache.delete(cache_key)


class ServerlessViewMixin:
    """
    Mixin for views to optimize for serverless environments
    """

    def get_queryset(self):
        """
        Override to add common optimizations for serverless
        """
        if hasattr(super(), "get_queryset"):
            queryset = super().get_queryset()
            # Add common optimizations like select_related, prefetch_related
            return queryset
        return None

    def dispatch(self, request, *args, **kwargs):
        """
        Override dispatch to add connection management for serverless
        """
        try:
            response = super().dispatch(request, *args, **kwargs)
            return response
        finally:
            # Ensure database connections are closed properly in serverless
            from django.db import connections

            for conn in connections.all():
                conn.close()
