"""
Project config API — read and update project-level config.

GET  /api/projects/{slug}/config/ — returns current config + schema
PATCH /api/projects/{slug}/config/ — updates config values
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Project, ProjectConfig


class ProjectConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_project(self, request, slug):
        try:
            return Project.objects.get(slug=slug, members=request.user)
        except Project.DoesNotExist:
            return None

    def get(self, request, slug):
        project = self._get_project(request, slug)
        if not project:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        config_data = {}
        if project.config:
            config_data = project.config.config or {}

        return Response(
            {
                "config": config_data,
                "schema": ProjectConfig.get_schema(),
            }
        )

    def patch(self, request, slug):
        project = self._get_project(request, slug)
        if not project:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        new_config = request.data.get("config", {})

        # Create ProjectConfig if it doesn't exist
        if not project.config:
            pc = ProjectConfig.objects.create(
                name=f"{project.name} Config",
                config=new_config,
            )
            project.config = pc
            project.save(update_fields=["config"])
        else:
            # Merge with existing config
            merged = {**(project.config.config or {}), **new_config}
            project.config.config = merged
            errors = project.config.validate_config()
            if errors:
                return Response({"error": errors}, status=status.HTTP_400_BAD_REQUEST)
            project.config.save(update_fields=["config", "updated_at"])

        return Response(
            {
                "config": project.config.config,
                "schema": ProjectConfig.get_schema(),
            }
        )
