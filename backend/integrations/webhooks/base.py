"""Base webhook adapter interface."""
from abc import ABC, abstractmethod


class BaseWebhookAdapter(ABC):
    slug: str = ""

    @abstractmethod
    def verify(self, request, webhook_secret: str) -> bool:
        """Verify the webhook is authentic."""

    @abstractmethod
    def parse_event(self, request) -> dict:
        """Parse webhook payload into normalized event dict."""

    @abstractmethod
    def handle_event(self, project, event: dict) -> None:
        """Process the event."""

    def check_pending(self, events: list[dict], config: dict) -> list[dict]:
        """Check pending events via polling. Default: no polling support."""
        return []
