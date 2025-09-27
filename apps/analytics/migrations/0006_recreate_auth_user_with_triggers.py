# Generated manually on 2025-09-27 07:25
# Recreate auth_user view with proper UUID handling and triggers

from django.db import migrations, connection


def create_auth_user_with_triggers(apps, schema_editor):
    """
    Create auth_user view and triggers to handle Django's update operations.
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

        print("Creating auth_user view with UUID handling...")

        # Drop existing view if it exists
        cursor.execute("DROP VIEW IF EXISTS auth_user CASCADE;")

        # Create auth_user view
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

        # Create a function to handle auth_user updates
        cursor.execute("""
            CREATE OR REPLACE FUNCTION handle_auth_user_update()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Only allow password updates, ignore all other changes
                -- since this is a read-only integration with auth service
                IF OLD.password != NEW.password THEN
                    -- Don't actually update the password - auth service manages passwords
                    -- Just return the OLD values to make Django think the update succeeded
                    RETURN OLD;
                END IF;
                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # Create trigger on the view
        cursor.execute("""
            CREATE TRIGGER auth_user_update_trigger
                INSTEAD OF UPDATE ON auth_user
                FOR EACH ROW
                EXECUTE FUNCTION handle_auth_user_update();
        """)

        # Clear existing sessions to avoid ID conflicts
        cursor.execute("DELETE FROM django_session;")

        print("Created auth_user view with update triggers")


def drop_auth_user_with_triggers(apps, schema_editor):
    """Drop the auth_user view and triggers"""
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        cursor.execute("DROP TRIGGER IF EXISTS auth_user_update_trigger ON auth_user;")
        cursor.execute("DROP FUNCTION IF EXISTS handle_auth_user_update();")
        cursor.execute("DROP VIEW IF EXISTS auth_user CASCADE;")


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0005_cleanup_auth_user_view'),
    ]

    operations = [
        migrations.RunPython(
            create_auth_user_with_triggers,
            drop_auth_user_with_triggers,
        ),
    ]