# Generated manually to fix index rename issues
from django.db import migrations, connection


def check_and_rename_indexes(apps, schema_editor):
    """
    Safely rename indexes only if they exist and target names don't exist.
    """
    if connection.vendor != 'sqlite':
        # For PostgreSQL, we can proceed with normal index operations
        return

    # For SQLite, check if indexes exist before renaming
    cursor = connection.cursor()

    # Get all existing indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
    existing_indexes = set(row[0] for row in cursor.fetchall())

    # Index mappings: old_name -> new_name
    index_mappings = {
        'alert_rules_metric_idx': 'analytics.a_metric__4b656a_idx',
        'alert_rules_active_idx': 'analytics.a_is_acti_53066b_idx',
        'alert_rules_severity_idx': 'analytics.a_severit_e4196c_idx',
        'analytics_cache_key_idx': 'analytics.a_cache_k_033971_idx',
        'analytics_cache_type_idx': 'analytics.a_cache_t_ad5219_idx',
        'analytics_cache_expires_idx': 'analytics.a_expires_110ff1_idx',
        'analytics_cache_metric_idx': 'analytics.a_source__c073b2_idx',
        'analytics_cache_accessed_idx': 'analytics.a_last_ac_8793b0_idx',
        'metric_definitions_name_idx': 'analytics.m_name_0fc87f_idx',
        'metric_definitions_category_idx': 'analytics.m_categor_b29ce5_idx',
        'metric_definitions_method_idx': 'analytics.m_calcula_b6d501_idx',
        'metric_definitions_active_idx': 'analytics.m_is_acti_f904fd_idx',
        'metric_snapshots_metric_ts_idx': 'analytics.m_metric__19ef62_idx',
        'metric_snapshots_user_ts_idx': 'analytics.m_user_id_a94f3c_idx',
        'metric_snapshots_project_ts_idx': 'analytics.m_project_7e664e_idx',
        'metric_snapshots_team_ts_idx': 'analytics.m_team_id_30fc83_idx',
        'metric_snapshots_period_idx': 'analytics.m_period__951d20_idx',
        'reports_created_by_idx': 'analytics.r_created_9859d6_idx',
        'reports_company_idx': 'analytics.r_company_4eade5_idx',
        'reports_team_idx': 'analytics.r_team_id_07ad55_idx',
        'reports_project_idx': 'analytics.r_project_634ad2_idx',
        'reports_type_idx': 'analytics.r_type_3dcf36_idx',
        'reports_status_idx': 'analytics.r_status_e33acc_idx',
        'reports_created_at_idx': 'analytics.r_created_6b7c5f_idx',
        'reports_expires_idx': 'analytics.r_expires_f8fd32_idx',
        'time_series_measurement_ts_idx': 'analytics.t_measure_ca6e56_idx',
        'time_series_source_ts_idx': 'analytics.t_source_aceab8_idx',
        'time_series_user_ts_idx': 'analytics.t_user_id_f510c9_idx',
        'time_series_project_ts_idx': 'analytics.t_project_7e4faa_idx',
        'time_series_team_ts_idx': 'analytics.t_team_id_8cd44b_idx',
        'time_series_timestamp_idx': 'analytics.t_timesta_5ae1c9_idx',
        'time_series_measurement_source_idx': 'analytics.t_measure_849f3b_idx',
    }

    # Check which indexes actually need renaming
    for old_name, new_name in index_mappings.items():
        if old_name in existing_indexes and new_name not in existing_indexes:
            # Only rename if old exists and new doesn't exist
            try:
                cursor.execute(f"ALTER INDEX {old_name} RENAME TO '{new_name}';")
                print(f"Renamed index {old_name} to {new_name}")
            except Exception as e:
                print(f"Could not rename {old_name} to {new_name}: {e}")
        elif new_name in existing_indexes:
            # New name already exists, migration already applied
            print(f"Index {new_name} already exists, skipping rename from {old_name}")
        else:
            # Old name doesn't exist, probably already renamed or never existed
            print(f"Index {old_name} not found, skipping rename to {new_name}")


def reverse_rename_indexes(apps, schema_editor):
    """
    Reverse the index renames if needed.
    """
    # For reverse migration, we'd rename back, but this is usually not needed
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            check_and_rename_indexes,
            reverse_rename_indexes,
        ),
    ]