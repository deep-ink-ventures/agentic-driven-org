"""WebSocket consumer for bootstrap progress updates."""

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


@database_sync_to_async
def is_project_member(user, project_id):
    from projects.models import Project
    return Project.objects.filter(id=project_id, members=user).exists()


class BootstrapConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope["url_route"]["kwargs"]["project_id"]
        self.group_name = f"bootstrap_{self.project_id}"

        user = self.scope.get("user")
        if not user or user.is_anonymous:
            await self.close()
            return

        if not await is_project_member(user, self.project_id):
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def bootstrap_status(self, event):
        """Send bootstrap status update to the client."""
        await self.send(text_data=json.dumps({
            "type": "bootstrap.status",
            "status": event.get("status"),
            "proposal_id": event.get("proposal_id"),
            "error_message": event.get("error_message"),
            "phase": event.get("phase", ""),
        }))
