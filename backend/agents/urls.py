from django.urls import path

from agents import views

urlpatterns = [
    path("agents/add/", views.AddAgentView.as_view(), name="agent-add"),
    path("agents/<uuid:pk>/", views.AgentUpdateView.as_view(), name="agent-update"),
    path("agents/<uuid:pk>/blueprint/", views.AgentBlueprintView.as_view(), name="agent-blueprint"),
]
