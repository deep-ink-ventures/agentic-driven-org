from django.urls import path
from projects import views

urlpatterns = [
    path("projects/", views.ProjectListView.as_view(), name="project-list"),
    path("projects/<uuid:project_id>/sources/", views.ProjectSourceListView.as_view(), name="project-sources"),
    path("projects/<uuid:project_id>/bootstrap/", views.BootstrapTriggerView.as_view(), name="bootstrap-trigger"),
    path("projects/<uuid:project_id>/bootstrap/latest/", views.BootstrapLatestView.as_view(), name="bootstrap-latest"),
    path("projects/<uuid:project_id>/bootstrap/<uuid:proposal_id>/approve/", views.BootstrapApproveView.as_view(), name="bootstrap-approve"),
    path("bootstrap/schema/", views.BootstrapSchemaView.as_view(), name="bootstrap-schema"),
]
