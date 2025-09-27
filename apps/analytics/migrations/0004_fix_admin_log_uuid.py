# Generated manually on 2025-09-27 08:10
# Simple fix for django_admin_log UUID compatibility

from django.db import migrations, connection


def fix_admin_log_uuid(apps, schema_editor):
    """
    Simple fix for django_admin_log to work with UUID users.
    """
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        # Check if auth.users table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'auth' AND table_name = 'users'
            );
        """)
        auth_users_exists = cursor.fetchone()[0]

        if not auth_users_exists:
            return

        print("Fixing django_admin_log for UUID users...")

        # Clear existing data to avoid conflicts
        cursor.execute("DELETE FROM django_admin_log;")
        cursor.execute("DELETE FROM django_session;")

        # Ensure user_id is UUID type
        cursor.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'django_admin_log' AND column_name = 'user_id'
        """)
        current_type = cursor.fetchone()

        if current_type and current_type[0] != 'uuid':
            # Drop existing constraint
            cursor.execute("ALTER TABLE django_admin_log DROP CONSTRAINT IF EXISTS django_admin_log_user_id_fkey CASCADE;")
            # Convert to UUID
            cursor.execute("ALTER TABLE django_admin_log ALTER COLUMN user_id TYPE UUID USING NULL;")

        # Add proper foreign key to auth.users
        cursor.execute("ALTER TABLE django_admin_log DROP CONSTRAINT IF EXISTS django_admin_log_user_id_fkey CASCADE;")
        cursor.execute("""
            ALTER TABLE django_admin_log
            ADD CONSTRAINT django_admin_log_user_id_auth_users_fkey
            FOREIGN KEY (user_id) REFERENCES auth.users(id)
            ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
        """)

        print("Fixed django_admin_log for UUID users")


def reverse_fix_admin_log_uuid(apps, schema_editor):
    """Reverse the fix"""
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        cursor.execute("ALTER TABLE django_admin_log DROP CONSTRAINT IF EXISTS django_admin_log_user_id_auth_users_fkey CASCADE;")


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0003_rename_alert_rules_metric_idx_analytics_a_metric__4b656a_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(
            fix_admin_log_uuid,
            reverse_fix_admin_log_uuid,
        ),
    ]