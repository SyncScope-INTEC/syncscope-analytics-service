#!/usr/bin/env python3
"""Script to verify the UUID fix is working"""

import os
import sys

import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection


def verify_admin_log_fix():
    """Verify the django_admin_log table is properly configured"""
    with connection.cursor() as cursor:
        # Check the user_id column type
        cursor.execute(
            """
            SELECT data_type, column_name
            FROM information_schema.columns
            WHERE table_name = 'django_admin_log'
            AND column_name = 'user_id'
        """
        )
        result = cursor.fetchone()

        if result:
            data_type, column_name = result
            print(f"OK django_admin_log.user_id column type: {data_type}")
            assert data_type == "uuid", f"Expected UUID, got {data_type}"
        else:
            raise Exception("Could not find django_admin_log.user_id column")

        # Check foreign key constraints
        cursor.execute(
            """
            SELECT
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_schema,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'django_admin_log'
            AND kcu.column_name = 'user_id'
        """
        )

        constraints = cursor.fetchall()
        print("\nOK Foreign key constraints for django_admin_log.user_id:")

        found_auth_users = False
        for constraint in constraints:
            schema = constraint[3] if constraint[3] else "public"
            print(
                f"  {constraint[0]}: {constraint[1]}.{constraint[2]} -> {schema}.{constraint[4]}.{constraint[5]}"
            )
            if constraint[4] == "users" and schema == "auth":
                found_auth_users = True

        assert found_auth_users, "Expected foreign key to auth.users not found"

        # Check auth.users table id type
        cursor.execute(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'auth'
            AND table_name = 'users'
            AND column_name = 'id'
        """
        )
        result = cursor.fetchone()

        if result:
            print(f"\nOK auth.users.id column type: {result[0]}")
            assert result[0] == "uuid", f"Expected UUID, got {result[0]}"
        else:
            raise Exception("auth.users table not found")

        print("\nSUCCESS All checks passed! The UUID fix is working correctly.")


if __name__ == "__main__":
    try:
        verify_admin_log_fix()
    except Exception as e:
        print(f"ERROR Verification failed: {e}")
        sys.exit(1)
