from django.urls import path
from integrations.webhooks.views import WebhookReceiveView

urlpatterns = [
    path(
        "webhooks/<slug:integration_slug>/<uuid:project_id>/<str:webhook_secret>/",
        WebhookReceiveView.as_view(),
        name="webhook-receive",
    ),
]
