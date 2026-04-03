import pytest
from accounts.models import User, AllowList


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")
        assert not user.is_staff
        assert not user.is_superuser
        assert user.pk is not None

    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(email="Test@EXAMPLE.com", password="testpass123")
        assert user.email == "Test@example.com"

    def test_create_user_without_email_raises(self):
        with pytest.raises(ValueError, match="Email is required"):
            User.objects.create_user(email="", password="testpass123")

    def test_create_superuser(self):
        user = User.objects.create_superuser(email="admin@example.com", password="adminpass123")
        assert user.is_staff
        assert user.is_superuser

    def test_user_str(self):
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        assert str(user) == "test@example.com"

    def test_user_has_uuid_pk(self):
        import uuid
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        assert isinstance(user.pk, uuid.UUID)

    def test_user_has_no_username(self):
        assert User.USERNAME_FIELD == "email"
        assert User.REQUIRED_FIELDS == []


@pytest.mark.django_db
class TestAllowListModel:
    def test_create_allow_list_entry(self):
        entry = AllowList.objects.create(email="test@example.com")
        assert entry.email == "test@example.com"

    def test_email_lowercased_on_save(self):
        entry = AllowList.objects.create(email="Test@EXAMPLE.COM")
        assert entry.email == "test@example.com"

    def test_str(self):
        entry = AllowList.objects.create(email="test@example.com")
        assert str(entry) == "test@example.com"

    def test_unique_email(self):
        from django.db import IntegrityError
        AllowList.objects.create(email="test@example.com")
        with pytest.raises(IntegrityError):
            AllowList.objects.create(email="test@example.com")
