from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from projects.models import Project
from projects.serializers.project_detail_serializer import ProjectDetailSerializer


class ProjectDetailView(RetrieveAPIView):
    """GET /api/projects/{id}/detail/ — full project with departments + agents."""
    serializer_class = ProjectDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return Project.objects.filter(members=self.request.user).prefetch_related(
            "departments__agents",
        )
