from django.urls import path
from projects.consumers import BootstrapConsumer

websocket_urlpatterns = [
    path("ws/bootstrap/<uuid:project_id>/", BootstrapConsumer.as_asgi()),
]
