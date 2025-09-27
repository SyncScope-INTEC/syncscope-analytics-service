# Generated manually on 2025-09-27 07:45
# Final cleanup to ensure all auth components work together

from django.db import migrations, connection


def final_auth_cleanup(apps, schema_editor):
    """
    Final cleanup to ensure all auth components work properly.
    """
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        print("Performing final auth cleanup...")

        # Clear all sessions and admin logs to remove any cached numeric IDs
        cursor.execute("DELETE FROM django_session;")
        cursor.execute("DELETE FROM django_admin_log;")

        # Ensure the auth_user view is properly configured
        cursor.execute("DROP VIEW IF EXISTS auth_user CASCADE;")

        # Recreate the view with explicit type casting to prevent any type issues
        cursor.execute("""
            CREATE VIEW auth_user AS
            SELECT
                id::uuid as id,
                password_hash::varchar as password,
                last_login::timestamp with time zone as last_login,
                COALESCE(is_superuser, false)::boolean as is_superuser,
                email::varchar as username,
                COALESCE(first_name, '')::varchar as first_name,
                COALESCE(last_name, '')::varchar as last_name,
                email::varchar as email,
                COALESCE(is_staff, false)::boolean as is_staff,
                COALESCE(is_active, true)::boolean as is_active,
                created_at::timestamp with time zone as date_joined
            FROM auth.users
            WHERE is_active = true;
        """)

        # Ensure our trigger function handles all edge cases
        cursor.execute("DROP TRIGGER IF EXISTS auth_user_instead_trigger ON auth_user;")
        cursor.execute("DROP FUNCTION IF EXISTS handle_auth_user_operations();")

        cursor.execute("""
            CREATE OR REPLACE FUNCTION handle_auth_user_operations()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Always return OLD for updates to prevent any database writes
                -- The custom auth backend handles authentication
                IF TG_OP = 'UPDATE' THEN
                    RETURN OLD;
                END IF;

                -- Prevent inserts and deletes
                IF TG_OP = 'INSERT' OR TG_OP = 'DELETE' THEN
                    RETURN NULL;
                END IF;

                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
        """)

        cursor.execute("""
            CREATE TRIGGER auth_user_instead_trigger
                INSTEAD OF UPDATE OR INSERT OR DELETE ON auth_user
                FOR EACH ROW
                EXECUTE FUNCTION handle_auth_user_operations();
        """)

        print("Final auth cleanup completed")


def reverse_final_auth_cleanup(apps, schema_editor):
    """Reverse the final cleanup"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0007_fix_auth_user_trigger'),
    ]

    operations = [
        migrations.RunPython(
            final_auth_cleanup,
            reverse_final_auth_cleanup,
        ),
    ]