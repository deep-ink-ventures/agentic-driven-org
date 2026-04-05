from django.urls import path

from projects.consumers import BootstrapConsumer, ProjectConsumer

websocket_urlpatterns = [
    path("ws/bootstrap/<uuid:project_id>/", BootstrapConsumer.as_asgi()),
    path("ws/project/<uuid:project_id>/", ProjectConsumer.as_asgi()),
]
