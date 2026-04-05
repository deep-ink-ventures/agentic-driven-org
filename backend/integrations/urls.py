from django.urls import path

from integrations.extensions.views import GenerateExtensionTokenView, SyncSessionView
from integrations.webhooks.views import WebhookReceiveView

urlpatterns = [
    # Extension endpoints
    path(
        "projects/<slug:slug>/extension-token/",
        GenerateExtensionTokenView.as_view(),
        name="extension-token",
    ),
    path(
        "extensions/sync-session/",
        SyncSessionView.as_view(),
        name="extension-sync-session",
    ),
    # Webhook endpoint
    path(
        "webhooks/<slug:integration_slug>/<uuid:project_id>/",
        WebhookReceiveView.as_view(),
        name="webhook-receive",
    ),
]
