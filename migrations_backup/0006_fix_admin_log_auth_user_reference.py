# Generated manually on 2025-09-27 06:35
# Fix django_admin_log to properly reference auth.users instead of auth_user

from django.db import connection, migrations


def fix_admin_log_auth_reference(apps, schema_editor):
    """
    Fix django_admin_log to reference the correct auth.users table with UUID IDs
    instead of the default auth_user table with integer IDs.

    This migration handles the mismatch between Django's default admin log
    that expects integer user IDs and our auth service that uses UUID user IDs.
    """
    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        # Check if auth.users table exists (production environment)
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'auth' AND table_name = 'users'
            );
        """
        )
        auth_users_exists = cursor.fetchone()[0]

        if not auth_users_exists:
            # In test environment - skip this migration
            return

        print("Fixing django_admin_log to reference auth.users with UUID...")

        # Clear existing admin log data to avoid conflicts
        cursor.execute("DELETE FROM django_admin_log;")

        # Drop all existing foreign key constraints on user_id
        cursor.execute(
            """
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'django_admin_log'
            AND constraint_type = 'FOREIGN KEY'
            AND constraint_name LIKE '%user_id%';
        """
        )

        constraints = cursor.fetchall()
        for constraint in constraints:
            print(f"Dropping constraint: {constraint[0]}")
            cursor.execute(
                f"ALTER TABLE django_admin_log DROP CONSTRAINT IF EXISTS {constraint[0]} CASCADE;"
            )

        # Check and fix user_id column type
        cursor.execute(
            """
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'django_admin_log' AND column_name = 'user_id'
        """
        )
        current_type = cursor.fetchone()

        if current_type and current_type[0] != "uuid":
            print(f"Converting user_id from {current_type[0]} to UUID...")
            cursor.execute(
                "ALTER TABLE django_admin_log ALTER COLUMN user_id TYPE UUID USING NULL;"
            )

        # Add the correct foreign key constraint to auth.users
        print("Adding foreign key constraint to auth.users...")
        cursor.execute(
            """
            ALTER TABLE django_admin_log
            ADD CONSTRAINT django_admin_log_user_id_auth_users_fkey
            FOREIGN KEY (user_id) REFERENCES auth.users(id)
            ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
        """
        )

        print("django_admin_log fix completed successfully!")


def reverse_fix_admin_log_auth_reference(apps, schema_editor):
    """Reverse operation - not implemented as this is a corrective fix"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0005_revert_admin_log_fix"),
    ]

    operations = [
        migrations.RunPython(
            fix_admin_log_auth_reference,
            reverse_fix_admin_log_auth_reference,
        ),
    ]
