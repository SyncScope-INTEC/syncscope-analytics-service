# Generated manually on 2025-09-27 07:05
# Cleanup and properly create auth_user view

from django.db import migrations, connection


def cleanup_and_create_auth_user_view(apps, schema_editor):
    """
    Cleanup existing auth_user and create proper view mapping to auth.users
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
            print("Skipping - auth.users table not found")
            return

        print("Cleaning up auth_user view...")

        # Drop existing view first
        cursor.execute("DROP VIEW IF EXISTS auth_user CASCADE;")

        # Create new auth_user view
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

        # Clear existing sessions to avoid ID conflicts
        cursor.execute("DELETE FROM django_session;")

        print("Auth user view cleanup completed!")


def reverse_cleanup(apps, schema_editor):
    """Reverse the cleanup"""
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        cursor.execute("DROP VIEW IF EXISTS auth_user CASCADE;")


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0004_uuid_auth_integration'),
    ]

    operations = [
        migrations.RunPython(
            cleanup_and_create_auth_user_view,
            reverse_cleanup,
        ),
    ]