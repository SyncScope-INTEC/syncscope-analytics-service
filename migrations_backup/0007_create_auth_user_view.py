# Generated manually on 2025-09-27 06:50
# Create auth_user view that maps to auth.users to fix Django admin compatibility

from django.db import connection, migrations


def create_auth_user_view(apps, schema_editor):
    """
    Create a view called auth_user that maps to auth.users.
    This allows Django's admin to work with our UUID-based auth.users table
    while still expecting the standard auth_user table structure.
    """
    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        # Check if auth.users table exists
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

        # Drop auth_user table if it exists (Django's default)
        cursor.execute("DROP TABLE IF EXISTS auth_user CASCADE;")

        # Create auth_user view that maps to auth.users
        cursor.execute(
            """
            CREATE VIEW auth_user AS
            SELECT
                id,
                password_hash as password,
                last_login,
                is_superuser,
                email as username,  -- Map email to username for Django compatibility
                first_name,
                last_name,
                email,
                is_staff,
                is_active,
                created_at as date_joined
            FROM auth.users;
        """
        )

        print("Created auth_user view mapping to auth.users")


def drop_auth_user_view(apps, schema_editor):
    """Drop the auth_user view"""
    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        cursor.execute("DROP VIEW IF EXISTS auth_user CASCADE;")


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0006_fix_admin_log_auth_user_reference"),
    ]

    operations = [
        migrations.RunPython(
            create_auth_user_view,
            drop_auth_user_view,
        ),
    ]
