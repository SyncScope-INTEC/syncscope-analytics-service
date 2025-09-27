"""
Custom authentication backend that properly handles UUID users from auth service.
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.db import connection


class UUIDAuthBackend(ModelBackend):
    """
    Custom authentication backend that works with UUID-based auth service users.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user against auth service data.
        """
        if username is None or password is None:
            return None

        User = get_user_model()

        try:
            # Query directly from auth.users table to avoid view issues
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, email, password_hash, first_name, last_name,
                           is_staff, is_active, is_superuser, last_login, created_at
                    FROM auth.users
                    WHERE email = %s AND is_active = true
                """, [username])

                user_data = cursor.fetchone()

                if not user_data:
                    return None

                # Check password against the stored hash
                stored_password_hash = user_data[2]  # password_hash
                if not self._check_auth_service_password(password, stored_password_hash):
                    return None

                # Create a User instance without saving it to the database
                user = User(
                    id=user_data[0],  # UUID id
                    email=user_data[1],
                    first_name=user_data[3] or '',
                    last_name=user_data[4] or '',
                    is_staff=user_data[5] or False,
                    is_active=user_data[6] or True,
                    is_superuser=user_data[7] or False,
                    last_login=user_data[8],
                    date_joined=user_data[9],
                )
                user.username = user.email  # Set username to email for Django compatibility

                # Override save method to prevent database writes
                def readonly_save(*args, **kwargs):
                    pass
                user.save = readonly_save

                return user

        except Exception as e:
            # Log the error but don't raise it
            print(f"Authentication error: {e}")
            return None

    def _check_auth_service_password(self, raw_password, stored_hash):
        """
        Check password against auth service hash.
        For now, this is a simple check - you may need to adjust based on
        how your auth service hashes passwords.
        """
        try:
            # Use Django's password checking with the stored hash
            return check_password(raw_password, stored_hash)
        except Exception:
            return False

    def get_user(self, user_id):
        """
        Get user by ID from auth service.
        """
        User = get_user_model()

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, email, password_hash, first_name, last_name,
                           is_staff, is_active, is_superuser, last_login, created_at
                    FROM auth.users
                    WHERE id = %s AND is_active = true
                """, [str(user_id)])

                user_data = cursor.fetchone()

                if not user_data:
                    return None

                user = User(
                    id=user_data[0],
                    email=user_data[1],
                    first_name=user_data[3] or '',
                    last_name=user_data[4] or '',
                    is_staff=user_data[5] or False,
                    is_active=user_data[6] or True,
                    is_superuser=user_data[7] or False,
                    last_login=user_data[8],
                    date_joined=user_data[9],
                )
                user.username = user.email

                # Override save method to prevent database writes
                def readonly_save(*args, **kwargs):
                    pass
                user.save = readonly_save

                return user

        except Exception as e:
            print(f"Get user error: {e}")
            return None