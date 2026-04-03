import pytest
from unittest.mock import patch, AsyncMock
from config.ws_auth import create_ws_ticket, consume_ticket, TICKET_PREFIX


@pytest.mark.django_db
class TestWsTicketAuth:
    def test_create_ws_ticket_returns_string(self):
        ticket = create_ws_ticket("some-user-id")
        assert isinstance(ticket, str)
        assert len(ticket) == 32  # uuid hex

    def test_create_ws_ticket_stores_in_cache(self):
        from django.core.cache import cache
        ticket = create_ws_ticket("user-123")
        stored = cache.get(f"{TICKET_PREFIX}{ticket}")
        assert stored == "user-123"

    @pytest.mark.asyncio
    async def test_consume_ticket_returns_user(self):
        from accounts.models import User
        from django.core.cache import cache

        user = await User.objects.acreate(email="ws@example.com")
        ticket = create_ws_ticket(str(user.pk))

        result = await consume_ticket(ticket)
        assert result is not None
        assert result.pk == user.pk

    @pytest.mark.asyncio
    async def test_consume_ticket_is_one_time(self):
        from accounts.models import User

        user = await User.objects.acreate(email="ws2@example.com")
        ticket = create_ws_ticket(str(user.pk))

        result1 = await consume_ticket(ticket)
        assert result1 is not None

        result2 = await consume_ticket(ticket)
        assert result2 is None

    @pytest.mark.asyncio
    async def test_consume_invalid_ticket_returns_none(self):
        result = await consume_ticket("nonexistent-ticket")
        assert result is None
