"""WebSocket authentication via one-time tickets."""
import uuid
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.core.cache import cache

TICKET_PREFIX = "ws_ticket:"
TICKET_TTL = 30

def create_ws_ticket(user_id) -> str:
    ticket = uuid.uuid4().hex
    cache.set(f"{TICKET_PREFIX}{ticket}", str(user_id), timeout=TICKET_TTL)
    return ticket

@database_sync_to_async
def consume_ticket(ticket: str):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    key = f"{TICKET_PREFIX}{ticket}"
    user_id = cache.get(key)
    if user_id is None:
        return None
    cache.delete(key)
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None

class TicketAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        ticket = params.get("ticket", [None])[0]
        if ticket:
            user = await consume_ticket(ticket)
            if user:
                scope["user"] = user
        return await super().__call__(scope, receive, send)
