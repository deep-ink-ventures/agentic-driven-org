from django.urls import path
from projects import views
from agents import views as views_agents

urlpatterns = [
    path("projects/", views.ProjectListView.as_view(), name="project-list"),
    path("projects/<uuid:pk>/detail/", views.ProjectDetailView.as_view(), name="project-detail"),
    path("projects/<uuid:project_id>/sources/", views.ProjectSourceListView.as_view(), name="project-sources"),
    path("projects/<uuid:project_id>/tasks/", views_agents.ProjectTaskListView.as_view(), name="project-tasks"),
    path("projects/<uuid:project_id>/tasks/<uuid:task_id>/approve/", views_agents.TaskApproveView.as_view(), name="task-approve"),
    path("projects/<uuid:project_id>/tasks/<uuid:task_id>/reject/", views_agents.TaskRejectView.as_view(), name="task-reject"),
    path("projects/<uuid:project_id>/bootstrap/", views.BootstrapTriggerView.as_view(), name="bootstrap-trigger"),
    path("projects/<uuid:project_id>/bootstrap/latest/", views.BootstrapLatestView.as_view(), name="bootstrap-latest"),
    path("projects/<uuid:project_id>/bootstrap/<uuid:proposal_id>/approve/", views.BootstrapApproveView.as_view(), name="bootstrap-approve"),
    path("bootstrap/schema/", views.BootstrapSchemaView.as_view(), name="bootstrap-schema"),
]
