import pytest
from unittest.mock import MagicMock, patch
from django.test import RequestFactory
from accounts.adapter import CustomAccountAdapter, CustomSocialAccountAdapter
from accounts.models import User, AllowList


@pytest.mark.django_db
class TestCustomAccountAdapter:
    def test_login_redirect_url(self):
        adapter = CustomAccountAdapter()
        request = RequestFactory().get("/")
        url = adapter.get_login_redirect_url(request)
        assert "/dashboard" in url


@pytest.mark.django_db
class TestCustomSocialAccountAdapter:
    def test_auto_signup_allowed(self):
        adapter = CustomSocialAccountAdapter()
        request = RequestFactory().get("/")
        sociallogin = MagicMock()
        assert adapter.is_auto_signup_allowed(request, sociallogin) is True

    @patch("accounts.adapter.AllowList")
    def test_pre_social_login_connects_existing_user(self, mock_allowlist):
        adapter = CustomSocialAccountAdapter()
        request = RequestFactory().get("/")

        user = User.objects.create_user(email="existing@example.com", password="pass")

        sociallogin = MagicMock()
        sociallogin.is_existing = False
        sociallogin.user.email = "existing@example.com"

        adapter.pre_social_login(request, sociallogin)

        sociallogin.connect.assert_called_once()

    def test_pre_social_login_blocks_non_allowlist_user(self, settings):
        from allauth.core.exceptions import ImmediateHttpResponse

        settings.ONLY_ALLOWLIST_CAN_SIGN_UP = True
        adapter = CustomSocialAccountAdapter()
        request = RequestFactory().get("/")

        sociallogin = MagicMock()
        sociallogin.is_existing = False
        sociallogin.user.email = "blocked@example.com"

        with pytest.raises(ImmediateHttpResponse):
            adapter.pre_social_login(request, sociallogin)

    def test_pre_social_login_allows_allowlisted_user(self, settings):
        settings.ONLY_ALLOWLIST_CAN_SIGN_UP = True
        AllowList.objects.create(email="allowed@example.com")
        adapter = CustomSocialAccountAdapter()
        request = RequestFactory().get("/")

        sociallogin = MagicMock()
        sociallogin.is_existing = False
        sociallogin.user.email = "allowed@example.com"

        # Should not raise
        adapter.pre_social_login(request, sociallogin)
