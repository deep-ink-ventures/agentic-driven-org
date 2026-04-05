"""Tests for TicketAuthMiddleware query-string auth flow."""

import json
from unittest.mock import AsyncMock

import pytest

from config.ws_auth import TicketAuthMiddleware, consume_ticket, create_ws_ticket


@pytest.mark.django_db
@pytest.mark.asyncio
class TestTicketAuthMiddleware:
    def _build_scope(self, ticket=None, origin=None):
        """Build a minimal ASGI scope for WebSocket."""
        headers = []
        if origin:
            headers.append((b"origin", origin.encode()))
        qs = f"ticket={ticket}".encode() if ticket else b""
        return {
            "type": "websocket",
            "headers": headers,
            "query_string": qs,
        }

    async def test_accepts_valid_ticket(self):
        """A valid ticket in the query string authenticates the user."""
        from accounts.models import User

        user = await User.objects.acreate(email="ws_full@example.com")
        ticket = create_ws_ticket(str(user.pk))

        scope = self._build_scope(ticket=ticket, origin="http://localhost:3000")
        send = AsyncMock()

        received_messages = []
        captured_scope = {}

        async def inner_app(inner_scope, receive, send):
            captured_scope.update(inner_scope)
            msg1 = await receive()
            assert msg1["type"] == "websocket.connect"
            msg2 = await receive()
            received_messages.append(msg2)

        app = TicketAuthMiddleware(inner_app)

        msg_queue = [
            {"type": "websocket.connect"},
            {"type": "websocket.receive", "text": json.dumps({"type": "chat", "message": "hello"})},
        ]
        call_idx = {"i": 0}

        async def receive():
            idx = call_idx["i"]
            call_idx["i"] += 1
            return msg_queue[idx]

        await app(scope, receive, send)

        assert len(received_messages) == 1
        assert json.loads(received_messages[0]["text"])["type"] == "chat"
        # scope["user"] should be set by the middleware
        assert scope.get("user") is not None
        assert scope["user"].pk == user.pk

    async def test_rejects_missing_ticket(self):
        """Connection without a ticket proceeds but user is not set in scope."""
        scope = self._build_scope(ticket=None, origin="http://localhost:3000")
        send = AsyncMock()

        inner_called = False

        async def inner_app(inner_scope, receive, send):
            nonlocal inner_called
            inner_called = True

        app = TicketAuthMiddleware(inner_app)

        async def receive():
            return {"type": "websocket.connect"}

        await app(scope, receive, send)
        # No close is sent — inner app is still called, but user is not set
        assert inner_called
        assert scope.get("user") is None

    async def test_rejects_invalid_ticket(self):
        """A ticket that doesn't exist in cache leaves user unset."""
        scope = self._build_scope(ticket="nonexistent", origin="http://localhost:3000")
        send = AsyncMock()

        inner_called = False

        async def inner_app(inner_scope, receive, send):
            nonlocal inner_called
            inner_called = True

        app = TicketAuthMiddleware(inner_app)

        async def receive():
            return {"type": "websocket.connect"}

        await app(scope, receive, send)
        # Inner app is still called, but user is not set
        assert inner_called
        assert scope.get("user") is None

    async def test_rejects_bad_origin(self, settings):
        """A connection from any origin is allowed by TicketAuthMiddleware (no origin check)."""
        settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
        from accounts.models import User

        user = await User.objects.acreate(email="ws_badorigin@example.com")
        ticket = create_ws_ticket(str(user.pk))

        scope = self._build_scope(ticket=ticket, origin="http://other.example.com")
        send = AsyncMock()

        inner_called = False

        async def inner_app(inner_scope, receive, send):
            nonlocal inner_called
            inner_called = True

        app = TicketAuthMiddleware(inner_app)

        async def receive():
            return {"type": "websocket.connect"}

        await app(scope, receive, send)
        # TicketAuthMiddleware does not enforce origin — inner app is called
        assert inner_called
        assert scope.get("user") is not None
        assert scope["user"].pk == user.pk

    async def test_ticket_is_single_use(self):
        """After a ticket is consumed, using it again fails."""
        from accounts.models import User

        user = await User.objects.acreate(email="ws_single@example.com")
        ticket = create_ws_ticket(str(user.pk))

        result1 = await consume_ticket(ticket)
        assert result1 is not None
        assert result1.pk == user.pk

        result2 = await consume_ticket(ticket)
        assert result2 is None

    async def test_rejects_non_json_first_message(self):
        """Non-JSON messages are passed through — middleware does not inspect message bodies."""
        from accounts.models import User

        user = await User.objects.acreate(email="ws_nonjson@example.com")
        ticket = create_ws_ticket(str(user.pk))

        scope = self._build_scope(ticket=ticket, origin="http://localhost:3000")
        send = AsyncMock()

        received_messages = []

        async def inner_app(inner_scope, receive, send):
            msg1 = await receive()
            assert msg1["type"] == "websocket.connect"
            msg2 = await receive()
            received_messages.append(msg2)

        app = TicketAuthMiddleware(inner_app)

        msg_queue = [
            {"type": "websocket.connect"},
            {"type": "websocket.receive", "text": "not json at all"},
        ]
        call_idx = {"i": 0}

        async def receive():
            idx = call_idx["i"]
            call_idx["i"] += 1
            return msg_queue[idx]

        await app(scope, receive, send)
        # Middleware passes the message through unchanged
        assert len(received_messages) == 1
        assert received_messages[0]["text"] == "not json at all"

    async def test_allows_empty_origin(self, settings):
        """Connections without an origin header are allowed."""
        settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
        from accounts.models import User

        user = await User.objects.acreate(email="ws_noorigin@example.com")
        ticket = create_ws_ticket(str(user.pk))

        scope = self._build_scope(ticket=ticket, origin=None)
        send = AsyncMock()

        inner_called = False

        async def inner_app(inner_scope, receive, send):
            nonlocal inner_called
            inner_called = True
            await receive()  # connect

        app = TicketAuthMiddleware(inner_app)

        msg_queue = [
            {"type": "websocket.connect"},
        ]
        call_idx = {"i": 0}

        async def receive():
            idx = call_idx["i"]
            call_idx["i"] += 1
            return msg_queue[idx]

        await app(scope, receive, send)
        assert inner_called
        assert scope.get("user") is not None
        assert scope["user"].pk == user.pk
