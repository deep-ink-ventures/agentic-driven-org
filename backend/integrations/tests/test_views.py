from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache

from agents.models import Agent
from integrations.extensions.views import TOKEN_SALT, decrypt_cookies
from projects.models import Department, Project

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="ext-tester@example.com", password="pass1234")


@pytest.fixture
def project(user):
    p = Project.objects.create(name="Ext Project", goal="Test", owner=user)
    p.members.add(user)
    return p


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="marketing", project=project)


@pytest.fixture
def twitter_agent(department):
    return Agent.objects.create(
        name="Twitter Bot",
        agent_type="twitter",
        department=department,
        status="active",
    )


@pytest.fixture
def authed_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def extension_token(project, user):
    return signing.dumps(
        {"project_id": str(project.id), "user_id": str(user.id)},
        salt=TOKEN_SALT,
    )


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


# ── GenerateExtensionTokenView ────────────────────────────────────────────────


@pytest.mark.django_db
class TestGenerateExtensionTokenView:
    def test_generates_token(self, authed_client, project):
        resp = authed_client.post(f"/api/projects/{project.slug}/extension-token/")
        assert resp.status_code == 200
        assert "token" in resp.data
        assert resp.data["project"] == project.name
        # Token should be verifiable
        payload = signing.loads(resp.data["token"], salt=TOKEN_SALT)
        assert payload["project_id"] == str(project.id)

    def test_requires_auth(self, api_client, project):
        resp = api_client.post(f"/api/projects/{project.slug}/extension-token/")
        assert resp.status_code in (401, 403)

    def test_non_member_gets_404(self, api_client, project):
        other = User.objects.create_user(email="nonmember@example.com", password="pass")
        api_client.force_authenticate(user=other)
        resp = api_client.post(f"/api/projects/{project.slug}/extension-token/")
        assert resp.status_code == 404


# ── SyncSessionView ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSyncSessionView:
    @patch("integrations.extensions.views._fetch_reddit_username", return_value={})
    @patch("integrations.extensions.views._fetch_twitter_handle", return_value={})
    def test_syncs_cookies_with_valid_token(self, mock_tw, mock_rd, api_client, extension_token, twitter_agent):
        resp = api_client.post(
            "/api/extensions/sync-session/",
            {"platform": "twitter", "cookies": {"auth_token": "abc123"}},
            format="json",
            HTTP_X_EXTENSION_TOKEN=extension_token,
        )
        assert resp.status_code == 200
        assert resp.data["synced"] is True
        assert resp.data["platform"] == "twitter"
        assert resp.data["cookie_count"] == 1

    def test_rejects_missing_token(self, api_client):
        resp = api_client.post(
            "/api/extensions/sync-session/",
            {"platform": "twitter", "cookies": {"a": "b"}},
            format="json",
        )
        assert resp.status_code == 401

    def test_rejects_invalid_token(self, api_client):
        resp = api_client.post(
            "/api/extensions/sync-session/",
            {"platform": "twitter", "cookies": {"a": "b"}},
            format="json",
            HTTP_X_EXTENSION_TOKEN="completely-invalid-token",
        )
        assert resp.status_code == 401

    def test_rejects_expired_token(self, api_client, project, user):
        # Create a token that is immediately expired by using max_age=0 on verify
        token = signing.dumps(
            {"project_id": str(project.id), "user_id": str(user.id)},
            salt=TOKEN_SALT,
        )
        with patch("integrations.extensions.views.signing.loads", side_effect=signing.BadSignature("expired")):
            resp = api_client.post(
                "/api/extensions/sync-session/",
                {"platform": "twitter", "cookies": {"a": "b"}},
                format="json",
                HTTP_X_EXTENSION_TOKEN=token,
            )
        assert resp.status_code == 401

    @patch("integrations.extensions.views._fetch_twitter_handle", return_value={})
    def test_rate_limiting(self, mock_tw, api_client, extension_token, twitter_agent):
        # Send 10 requests — all should succeed
        for i in range(10):
            resp = api_client.post(
                "/api/extensions/sync-session/",
                {"platform": "twitter", "cookies": {"auth_token": f"tok{i}"}},
                format="json",
                HTTP_X_EXTENSION_TOKEN=extension_token,
            )
            assert resp.status_code == 200, f"Request {i + 1} failed unexpectedly"
        # 11th should be rate limited
        resp = api_client.post(
            "/api/extensions/sync-session/",
            {"platform": "twitter", "cookies": {"auth_token": "final"}},
            format="json",
            HTTP_X_EXTENSION_TOKEN=extension_token,
        )
        assert resp.status_code == 429

    @patch("integrations.extensions.views._fetch_twitter_handle", return_value={})
    def test_cookies_are_encrypted(self, mock_tw, api_client, extension_token, twitter_agent):
        cookies = {"auth_token": "super_secret_value_12345"}
        api_client.post(
            "/api/extensions/sync-session/",
            {"platform": "twitter", "cookies": cookies},
            format="json",
            HTTP_X_EXTENSION_TOKEN=extension_token,
        )
        twitter_agent.refresh_from_db()
        stored = twitter_agent.config.get("twitter_session", "")
        # Stored value should NOT be plaintext
        assert "super_secret_value_12345" not in stored
        # But should be decryptable
        decrypted = decrypt_cookies(stored)
        assert decrypted["auth_token"] == "super_secret_value_12345"


# ── WebhookReceiveView ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWebhookReceiveView:
    def test_returns_200_for_unknown_integration(self, api_client, project):
        resp = api_client.post(
            f"/api/webhooks/unknown/{project.id}/",
            {"data": "test"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["status"] == "ok"

    def test_returns_200_for_nonexistent_project(self, api_client):
        fake_id = "00000000-0000-0000-0000-000000000000"
        with patch("integrations.webhooks.views.get_adapter") as mock_get:
            adapter = MagicMock()
            adapter.verify.return_value = True
            adapter.parse_event.return_value = {"event_type": "test"}
            mock_get.return_value = adapter
            resp = api_client.post(
                f"/api/webhooks/github/{fake_id}/",
                {"data": "test"},
                format="json",
            )
        assert resp.status_code == 200
        assert resp.data["status"] == "ok"

    def test_reads_webhook_signature_header(self, api_client, project):
        with patch("integrations.webhooks.views.get_adapter") as mock_get:
            adapter = MagicMock()
            adapter.verify.return_value = False
            mock_get.return_value = adapter
            resp = api_client.post(
                f"/api/webhooks/github/{project.id}/",
                {"data": "test"},
                format="json",
                HTTP_X_WEBHOOK_SIGNATURE="sig123",
            )
        # verify was called with the signature from header
        adapter.verify.assert_called_once()
        assert adapter.verify.call_args[0][1] == "sig123"
        # Still returns 200 even on verification failure (no enumeration)
        assert resp.status_code == 200

    def test_returns_200_even_on_handler_error(self, api_client, project):
        with patch("integrations.webhooks.views.get_adapter") as mock_get:
            adapter = MagicMock()
            adapter.verify.return_value = True
            adapter.parse_event.return_value = {"event_type": "push"}
            adapter.handle_event.side_effect = Exception("boom")
            mock_get.return_value = adapter
            resp = api_client.post(
                f"/api/webhooks/github/{project.id}/",
                {"data": "test"},
                format="json",
                HTTP_X_WEBHOOK_SIGNATURE="sig",
            )
        assert resp.status_code == 200
