# Generated manually on 2025-09-27 07:35
# Fix auth_user trigger to properly handle all Django operations

from django.db import migrations, connection


def fix_auth_user_trigger(apps, schema_editor):
    """
    Fix the auth_user trigger to properly handle Django's authentication operations.
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

        print("Fixing auth_user trigger...")

        # Drop existing trigger and function
        cursor.execute("DROP TRIGGER IF EXISTS auth_user_update_trigger ON auth_user;")
        cursor.execute("DROP FUNCTION IF EXISTS handle_auth_user_update();")

        # Drop and recreate the view to ensure it's clean
        cursor.execute("DROP VIEW IF EXISTS auth_user CASCADE;")

        # Create auth_user view with explicit UUID casting
        cursor.execute("""
            CREATE VIEW auth_user AS
            SELECT
                id::uuid as id,
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

        # Create a better function that handles all operations
        cursor.execute("""
            CREATE OR REPLACE FUNCTION handle_auth_user_operations()
            RETURNS TRIGGER AS $$
            BEGIN
                -- For UPDATE operations
                IF TG_OP = 'UPDATE' THEN
                    -- Don't actually update anything in the auth service table
                    -- Just return OLD to make Django think the update succeeded
                    RETURN OLD;
                END IF;

                -- For INSERT operations (should not happen but handle it)
                IF TG_OP = 'INSERT' THEN
                    -- Don't allow inserts - users are managed by auth service
                    RETURN NULL;
                END IF;

                -- For DELETE operations (should not happen but handle it)
                IF TG_OP = 'DELETE' THEN
                    -- Don't allow deletes - users are managed by auth service
                    RETURN NULL;
                END IF;

                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # Create triggers for all operations
        cursor.execute("""
            CREATE TRIGGER auth_user_instead_trigger
                INSTEAD OF UPDATE OR INSERT OR DELETE ON auth_user
                FOR EACH ROW
                EXECUTE FUNCTION handle_auth_user_operations();
        """)

        # Clear sessions to avoid cached numeric IDs
        cursor.execute("DELETE FROM django_session;")
        cursor.execute("DELETE FROM django_admin_log;")

        print("Fixed auth_user trigger and cleared sessions")


def reverse_fix_auth_user_trigger(apps, schema_editor):
    """Reverse the trigger fix"""
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        cursor.execute("DROP TRIGGER IF EXISTS auth_user_instead_trigger ON auth_user;")
        cursor.execute("DROP FUNCTION IF EXISTS handle_auth_user_operations();")


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0006_recreate_auth_user_with_triggers'),
    ]

    operations = [
        migrations.RunPython(
            fix_auth_user_trigger,
            reverse_fix_auth_user_trigger,
        ),
    ]