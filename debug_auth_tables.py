#!/usr/bin/env python3
"""Debug script to check auth table configuration"""

import os
import sys
import django
from django.conf import settings

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection
from django.contrib.auth import get_user_model


def debug_auth_tables():
    """Debug auth table configuration"""
    print("=== Django Auth Configuration ===")

    # Check AUTH_USER_MODEL setting
    auth_user_model = getattr(settings, "AUTH_USER_MODEL", "auth.User")
    print(f"AUTH_USER_MODEL setting: {auth_user_model}")

    # Check the actual User model Django is using
    User = get_user_model()
    print(f"Active User model: {User}")
    print(f"User model table: {User._meta.db_table}")
    print(f"User model app: {User._meta.app_label}")

    print("\n=== Database Tables ===")
    with connection.cursor() as cursor:
        # Check what auth tables exist
        cursor.execute(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name IN ('auth_user', 'users')
            ORDER BY table_schema, table_name
        """
        )
        tables = cursor.fetchall()

        print("Available auth tables:")
        for schema, table in tables:
            print(f"  {schema}.{table}")

            # Check the id column type for each table
            cursor.execute(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s AND column_name = 'id'
            """,
                [schema, table],
            )
            id_type = cursor.fetchone()
            if id_type:
                print(f"    id column type: {id_type[0]}")

        print("\n=== Admin Log Table ===")
        cursor.execute(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'django_admin_log' AND column_name = 'user_id'
        """
        )
        admin_log_type = cursor.fetchone()
        if admin_log_type:
            print(f"django_admin_log.user_id type: {admin_log_type[0]}")

        # Check current foreign key constraint
        cursor.execute(
            """
            SELECT
                tc.constraint_name,
                ccu.table_schema,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'django_admin_log'
        """
        )

        constraints = cursor.fetchall()
        print("\nAdmin log foreign key constraints:")
        for constraint in constraints:
            schema = constraint[1] if constraint[1] else "public"
            print(f"  {constraint[0]} -> {schema}.{constraint[2]}.{constraint[3]}")


if __name__ == "__main__":
    debug_auth_tables()
