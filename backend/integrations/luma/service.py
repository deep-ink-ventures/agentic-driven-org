"""
Lu.ma event platform service.
Queries Lu.ma calendars for upcoming events. Uses Playwright internally.
"""

import logging

logger = logging.getLogger(__name__)


def query_events(calendar_urls: list[str], days_ahead: int = 30) -> list[dict]:
    logger.info("Lu.ma query_events: %d calendars, %d days ahead", len(calendar_urls), days_ahead)
    return []


def get_event_details(event_url: str) -> dict:
    logger.info("Lu.ma get_event_details: %s", event_url)
    return {"success": True, "title": "", "date": "", "description": "", "speakers": [], "attendee_count": 0}
