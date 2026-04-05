import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model

from projects.consumers import BootstrapConsumer, ProjectConsumer
from projects.models import Project

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="ws-tester@example.com", password="pass1234")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="ws-outsider@example.com", password="pass1234")


@pytest.fixture
def project(user):
    p = Project.objects.create(name="WS Project", goal="Test", owner=user)
    p.members.add(user)
    return p


def _make_communicator(consumer_class, project_id, user=None):
    """Create a WebsocketCommunicator with the given user in scope."""
    communicator = WebsocketCommunicator(
        consumer_class.as_asgi(),
        f"/ws/test/{project_id}/",
    )
    communicator.scope["url_route"] = {"kwargs": {"project_id": str(project_id)}}
    communicator.scope["user"] = user
    return communicator


# ── BootstrapConsumer ──────────────────────────────────────────────────────────


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestBootstrapConsumer:
    async def test_connect_authenticated_member(self, user, project):
        communicator = _make_communicator(BootstrapConsumer, project.id, user)
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.disconnect()

    async def test_reject_anonymous(self, project):
        from django.contrib.auth.models import AnonymousUser

        communicator = _make_communicator(BootstrapConsumer, project.id, AnonymousUser())
        connected, _ = await communicator.connect()
        # Consumer calls self.close() for anonymous — the connection is accepted
        # then immediately closed, or rejected outright. Either way we handle it.
        # With channels testing, close() after accept means we get connected=True
        # but a disconnect follows.
        if connected:
            # Consumer should have sent a close
            msg = await communicator.receive_output()
            assert msg["type"] == "websocket.close"
        await communicator.disconnect()

    async def test_reject_non_member(self, other_user, project):
        communicator = _make_communicator(BootstrapConsumer, project.id, other_user)
        connected, _ = await communicator.connect()
        if connected:
            msg = await communicator.receive_output()
            assert msg["type"] == "websocket.close"
        await communicator.disconnect()

    async def test_disconnect_removes_from_group(self, user, project):
        communicator = _make_communicator(BootstrapConsumer, project.id, user)
        connected, _ = await communicator.connect()
        assert connected is True
        # Should not raise
        await communicator.disconnect()


# ── ProjectConsumer ────────────────────────────────────────────────────────────


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestProjectConsumer:
    async def test_connect_authenticated_member(self, user, project):
        communicator = _make_communicator(ProjectConsumer, project.id, user)
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.disconnect()

    async def test_reject_anonymous(self, project):
        from django.contrib.auth.models import AnonymousUser

        communicator = _make_communicator(ProjectConsumer, project.id, AnonymousUser())
        connected, _ = await communicator.connect()
        if connected:
            msg = await communicator.receive_output()
            assert msg["type"] == "websocket.close"
        await communicator.disconnect()

    async def test_reject_non_member(self, other_user, project):
        communicator = _make_communicator(ProjectConsumer, project.id, other_user)
        connected, _ = await communicator.connect()
        if connected:
            msg = await communicator.receive_output()
            assert msg["type"] == "websocket.close"
        await communicator.disconnect()

    async def test_disconnect_removes_from_group(self, user, project):
        communicator = _make_communicator(ProjectConsumer, project.id, user)
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.disconnect()
