"""Generic webhook receive endpoint."""
import logging

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.webhooks import get_adapter
from projects.models import Project

logger = logging.getLogger(__name__)


class WebhookReceiveView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, integration_slug, project_id, webhook_secret):
        adapter = get_adapter(integration_slug)
        if not adapter:
            return Response({"error": "Unknown integration"}, status=404)

        if not adapter.verify(request, webhook_secret):
            logger.warning("Webhook verification failed for %s/%s", integration_slug, project_id)
            return Response({"error": "Verification failed"}, status=403)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=404)

        event = adapter.parse_event(request)
        logger.info("Webhook received: %s %s for project %s", integration_slug, event["event_type"], project.name)

        try:
            adapter.handle_event(project, event)
        except Exception:
            logger.exception("Webhook handler failed for %s", integration_slug)

        return Response({"status": "ok"})
