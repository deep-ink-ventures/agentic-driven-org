"""WebSocket authentication via one-time tickets."""

import logging
import uuid
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.core.cache import cache

logger = logging.getLogger(__name__)

TICKET_PREFIX = "ws_ticket:"
TICKET_TTL = 30


def create_ws_ticket(user_id) -> str:
    ticket = uuid.uuid4().hex
    cache.set(f"{TICKET_PREFIX}{ticket}", str(user_id), timeout=TICKET_TTL)
    logger.debug("WS ticket created: user=%s ticket=%s...", user_id, ticket[:8])
    return ticket


@database_sync_to_async
def consume_ticket(ticket: str):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    key = f"{TICKET_PREFIX}{ticket}"
    user_id = cache.get(key)
    if user_id is None:
        logger.warning("WS ticket not found or expired: %s...", ticket[:8])
        return None
    cache.delete(key)
    try:
        user = User.objects.get(pk=user_id)
        logger.debug("WS ticket consumed: user=%s ticket=%s...", user_id, ticket[:8])
        return user
    except User.DoesNotExist:
        logger.warning("WS ticket user not found: user_id=%s", user_id)
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
                logger.debug("WS auth success: user=%s", user.pk)
            else:
                logger.warning("WS auth failed: ticket=%s...", ticket[:8])
        else:
            logger.debug("WS connection without ticket")
        return await super().__call__(scope, receive, send)
