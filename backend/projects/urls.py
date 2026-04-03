from django.urls import path
from projects import views

urlpatterns = [
    path("projects/", views.ProjectListView.as_view(), name="project-list"),
]
