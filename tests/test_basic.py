"""
Basic tests to verify test infrastructure works
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


def test_basic_math():
    """Basic test to verify pytest works."""
    assert 2 + 2 == 4


def test_basic_string():
    """Basic string test."""
    assert "hello" + " world" == "hello world"


class TestBasicDjango(TestCase):
    """Basic Django test class."""

    def test_user_creation(self):
        """Test basic user creation."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")

    def test_database_connection(self):
        """Test database connection works."""
        # Simple query to verify DB is working
        user_count = User.objects.count()
        self.assertIsInstance(user_count, int)