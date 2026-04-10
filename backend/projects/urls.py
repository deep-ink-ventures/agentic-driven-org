from django.urls import path

from agents import views as views_agents
from projects import views
from projects.views.document_view import DocumentListView

urlpatterns = [
    path("projects/", views.ProjectListView.as_view(), name="project-list"),
    path("projects/<slug:slug>/detail/", views.ProjectDetailView.as_view(), name="project-detail"),
    path("projects/<slug:slug>/config/", views.ProjectConfigView.as_view(), name="project-config"),
    path("projects/<uuid:project_id>/sources/", views.ProjectSourceListView.as_view(), name="project-sources"),
    path("projects/<uuid:project_id>/tasks/", views_agents.ProjectTaskListView.as_view(), name="project-tasks"),
    path(
        "projects/<uuid:project_id>/tasks/<uuid:task_id>/approve/",
        views_agents.TaskApproveView.as_view(),
        name="task-approve",
    ),
    path(
        "projects/<uuid:project_id>/tasks/<uuid:task_id>/reject/",
        views_agents.TaskRejectView.as_view(),
        name="task-reject",
    ),
    path(
        "projects/<uuid:project_id>/tasks/<uuid:task_id>/retry/",
        views_agents.TaskRetryView.as_view(),
        name="task-retry",
    ),
    path("projects/<uuid:project_id>/bootstrap/", views.BootstrapTriggerView.as_view(), name="bootstrap-trigger"),
    path("projects/<uuid:project_id>/bootstrap/latest/", views.BootstrapLatestView.as_view(), name="bootstrap-latest"),
    path(
        "projects/<uuid:project_id>/bootstrap/<uuid:proposal_id>/approve/",
        views.BootstrapApproveView.as_view(),
        name="bootstrap-approve",
    ),
    path("bootstrap/schema/", views.BootstrapSchemaView.as_view(), name="bootstrap-schema"),
    path(
        "projects/<uuid:project_id>/departments/available/",
        views.AvailableDepartmentsView.as_view(),
        name="available-departments",
    ),
    path("projects/<uuid:project_id>/departments/add/", views.AddDepartmentView.as_view(), name="add-department"),
    path(
        "projects/<uuid:project_id>/departments/<uuid:dept_id>/available-agents/",
        views.AvailableAgentsView.as_view(),
        name="available-agents",
    ),
    path("departments/<uuid:pk>/config/", views.DepartmentConfigView.as_view(), name="department-config"),
    path("projects/<uuid:project_id>/sprints/", views.SprintListCreateView.as_view(), name="sprint-list"),
    path(
        "projects/<uuid:project_id>/sprints/<uuid:sprint_id>/",
        views.SprintDetailView.as_view(),
        name="sprint-detail",
    ),
    path(
        "projects/<uuid:project_id>/sprints/<uuid:sprint_id>/reset/",
        views.SprintResetView.as_view(),
        name="sprint-reset",
    ),
    path(
        "projects/<uuid:project_id>/departments/<uuid:department_id>/documents/",
        DocumentListView.as_view(),
        name="document-list",
    ),
]
