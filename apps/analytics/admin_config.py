"""
Custom admin configuration to avoid UUID/integer mismatch issues.
"""

from django.contrib.admin import AdminSite
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import reverse


class NoLogAdminSite(AdminSite):
    """
    Custom admin site that disables admin logging to avoid UUID/integer conflicts.
    """
    site_header = "SyncScope Analytics Administration"
    site_title = "Analytics Admin"
    index_title = "Analytics Service Management"

    def log_action(self, user_id, content_type_id, object_id, object_repr, action_flag, change_message=''):
        """Override to disable admin logging."""
        # Don't create admin log entries to avoid UUID/integer type conflicts
        pass


# Create custom admin site instance
admin_site = NoLogAdminSite(name='no_log_admin')

# Register models with the custom admin site instead of default admin
from .admin import *  # Import all existing admin configurations

# Re-register all models with our custom admin site
admin_site.register(MetricDefinition, MetricDefinitionAdmin)
admin_site.register(Report, ReportAdmin)
admin_site.register(AnalyticsCache, AnalyticsCacheAdmin)
admin_site.register(AlertRule, AlertRuleAdmin)
admin_site.register(TimeSeriesData, TimeSeriesDataAdmin)
admin_site.register(MetricSnapshot, MetricSnapshotAdmin)