# Generated manually on 2025-09-27 07:00
# Comprehensive UUID auth integration for analytics service
# This migration ensures proper compatibility with auth service UUID-based users

from django.db import migrations, connection


def setup_uuid_auth_integration(apps, schema_editor):
    """
    Set up proper UUID auth integration for analytics service.
    This handles all the necessary database changes to work with auth service UUID users.
    """
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        # Check if auth.users table exists (production environment)
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'auth' AND table_name = 'users'
            );
        """)
        auth_users_exists = cursor.fetchone()[0]

        if not auth_users_exists:
            # In test environment - skip this migration
            print("Skipping UUID auth integration - auth.users table not found")
            return

        print("Setting up UUID auth integration...")

        # Step 1: Clear django_admin_log to avoid conversion issues
        cursor.execute("DELETE FROM django_admin_log;")
        print("Cleared django_admin_log table")

        # Step 2: Drop all foreign key constraints on django_admin_log.user_id
        cursor.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'django_admin_log'
            AND constraint_type = 'FOREIGN KEY'
            AND constraint_name LIKE '%user_id%';
        """)
        constraints = cursor.fetchall()

        for constraint in constraints:
            print(f"Dropping constraint: {constraint[0]}")
            cursor.execute(f"ALTER TABLE django_admin_log DROP CONSTRAINT IF EXISTS {constraint[0]} CASCADE;")

        # Step 3: Ensure django_admin_log.user_id is UUID type
        cursor.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'django_admin_log' AND column_name = 'user_id'
        """)
        current_type = cursor.fetchone()

        if current_type and current_type[0] != 'uuid':
            print(f"Converting django_admin_log.user_id from {current_type[0]} to UUID")
            cursor.execute("ALTER TABLE django_admin_log ALTER COLUMN user_id TYPE UUID USING NULL;")

        # Step 4: Drop any existing auth_user table/view (order matters!)
        cursor.execute("DROP VIEW IF EXISTS auth_user CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS auth_user CASCADE;")
        print("Removed existing auth_user table/view")

        # Step 5: Create auth_user view that properly maps to auth.users
        cursor.execute("""
            CREATE VIEW auth_user AS
            SELECT
                id,
                password_hash as password,
                last_login,
                COALESCE(is_superuser, false) as is_superuser,
                email as username,
                COALESCE(first_name, '') as first_name,
                COALESCE(last_name, '') as last_name,
                email,
                COALESCE(is_staff, false) as is_staff,
                COALESCE(is_active, true) as is_active,
                created_at as date_joined
            FROM auth.users;
        """)
        print("Created auth_user view mapping to auth.users")

        # Step 6: Add proper foreign key constraint from django_admin_log to auth.users
        cursor.execute("""
            ALTER TABLE django_admin_log
            ADD CONSTRAINT django_admin_log_user_id_auth_users_fkey
            FOREIGN KEY (user_id) REFERENCES auth.users(id)
            ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
        """)
        print("Added foreign key constraint to auth.users")

        # Step 7: Clear any existing sessions to avoid ID conflicts
        cursor.execute("DELETE FROM django_session;")
        print("Cleared existing sessions to prevent ID conflicts")

        print("UUID auth integration setup completed successfully!")


def reverse_uuid_auth_integration(apps, schema_editor):
    """Reverse the UUID auth integration changes"""
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        # Drop the view and constraints
        cursor.execute("DROP VIEW IF EXISTS auth_user CASCADE;")
        cursor.execute("ALTER TABLE django_admin_log DROP CONSTRAINT IF EXISTS django_admin_log_user_id_auth_users_fkey CASCADE;")
        cursor.execute("DELETE FROM django_admin_log;")
        cursor.execute("DELETE FROM django_session;")


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0003_rename_alert_rules_metric_idx_analytics_a_metric__4b656a_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(
            setup_uuid_auth_integration,
            reverse_uuid_auth_integration,
        ),
    ]