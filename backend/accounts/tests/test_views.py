from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from accounts.models import AllowList

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="alice@example.com", password="secret1234")


@pytest.fixture
def authed_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


# ── SessionView ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSessionView:
    def test_authenticated_returns_user(self, authed_client, user):
        resp = authed_client.get("/api/auth/session/")
        assert resp.status_code == 200
        assert resp.data["user"]["email"] == "alice@example.com"
        assert resp.data["user"]["id"] == str(user.id)

    def test_anonymous_returns_null(self, api_client):
        resp = api_client.get("/api/auth/session/")
        assert resp.status_code == 200
        assert resp.data["user"] is None


# ── SignupView ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSignupView:
    def test_creates_user_and_returns_201(self, api_client, settings):
        settings.ONLY_ALLOWLIST_CAN_SIGN_UP = False
        resp = api_client.post(
            "/api/auth/signup/",
            {
                "email": "new@example.com",
                "password": "strongpass9",
                "terms_accepted": True,
            },
        )
        assert resp.status_code == 201
        assert resp.data["user"]["email"] == "new@example.com"
        assert User.objects.filter(email="new@example.com").exists()

    def test_sets_session_on_signup(self, api_client, settings):
        settings.ONLY_ALLOWLIST_CAN_SIGN_UP = False
        resp = api_client.post(
            "/api/auth/signup/",
            {
                "email": "sess@example.com",
                "password": "strongpass9",
                "terms_accepted": True,
            },
        )
        assert resp.status_code == 201
        # Subsequent session check should show the user
        session_resp = api_client.get("/api/auth/session/")
        assert session_resp.data["user"]["email"] == "sess@example.com"

    def test_allowlist_blocks_unregistered_email(self, api_client, settings):
        settings.ONLY_ALLOWLIST_CAN_SIGN_UP = True
        resp = api_client.post(
            "/api/auth/signup/",
            {
                "email": "blocked@example.com",
                "password": "strongpass9",
                "terms_accepted": True,
            },
        )
        assert resp.status_code == 403
        assert "allow list" in resp.data["error"].lower()

    def test_allowlist_allows_registered_email(self, api_client, settings):
        settings.ONLY_ALLOWLIST_CAN_SIGN_UP = True
        AllowList.objects.create(email="vip@example.com")
        resp = api_client.post(
            "/api/auth/signup/",
            {
                "email": "VIP@example.com",  # case insensitive
                "password": "strongpass9",
                "terms_accepted": True,
            },
        )
        assert resp.status_code == 201

    def test_duplicate_email_returns_400(self, api_client, user, settings):
        settings.ONLY_ALLOWLIST_CAN_SIGN_UP = False
        resp = api_client.post(
            "/api/auth/signup/",
            {
                "email": "alice@example.com",
                "password": "strongpass9",
                "terms_accepted": True,
            },
        )
        assert resp.status_code == 400

    def test_short_password_returns_400(self, api_client, settings):
        settings.ONLY_ALLOWLIST_CAN_SIGN_UP = False
        resp = api_client.post(
            "/api/auth/signup/",
            {
                "email": "short@example.com",
                "password": "abc",
                "terms_accepted": True,
            },
        )
        assert resp.status_code == 400

    def test_terms_not_accepted_returns_400(self, api_client, settings):
        settings.ONLY_ALLOWLIST_CAN_SIGN_UP = False
        resp = api_client.post(
            "/api/auth/signup/",
            {
                "email": "noterms@example.com",
                "password": "strongpass9",
                "terms_accepted": False,
            },
        )
        assert resp.status_code == 400


# ── LoginView ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLoginView:
    def test_valid_credentials(self, api_client, user):
        resp = api_client.post(
            "/api/auth/login/",
            {
                "email": "alice@example.com",
                "password": "secret1234",
            },
        )
        assert resp.status_code == 200
        assert resp.data["user"]["email"] == "alice@example.com"

    def test_invalid_credentials_returns_400(self, api_client, user):
        resp = api_client.post(
            "/api/auth/login/",
            {
                "email": "alice@example.com",
                "password": "wrongpassword",
            },
        )
        assert resp.status_code == 400
        assert "invalid" in resp.data["error"].lower()

    def test_failed_login_logs_warning(self, api_client, user):
        with patch("accounts.views.auth_view.logger") as mock_logger:
            api_client.post(
                "/api/auth/login/",
                {
                    "email": "alice@example.com",
                    "password": "wrong",
                },
            )
            mock_logger.warning.assert_called_once()
            args = mock_logger.warning.call_args[0]
            assert "alice@example.com" in args[1]


# ── LogoutView ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLogoutView:
    def test_logout_clears_session(self, authed_client):
        resp = authed_client.post("/api/auth/logout/")
        assert resp.status_code == 200
        assert resp.data["detail"] == "Logged out"

    def test_logout_requires_auth(self, api_client):
        resp = api_client.post("/api/auth/logout/")
        assert resp.status_code in (401, 403)


# ── WsTicketView ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWsTicketView:
    def test_returns_ticket(self, authed_client):
        resp = authed_client.post("/api/auth/ws-ticket/")
        assert resp.status_code == 200
        assert "ticket" in resp.data
        assert len(resp.data["ticket"]) > 0

    def test_requires_auth(self, api_client):
        resp = api_client.post("/api/auth/ws-ticket/")
        assert resp.status_code in (401, 403)
