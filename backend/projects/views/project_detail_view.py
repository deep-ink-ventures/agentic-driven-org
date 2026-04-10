from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from projects.models import Project
from projects.serializers.project_detail_serializer import ProjectDetailSerializer


class ProjectDetailView(RetrieveUpdateAPIView):
    """GET/PATCH /api/projects/{slug}/detail/ — full project with departments + agents."""

    serializer_class = ProjectDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return Project.objects.filter(members=self.request.user).prefetch_related(
            "departments__agents",
        )

    def perform_update(self, serializer):
        old_goal = serializer.instance.goal or ""
        instance = serializer.save()
        new_goal = instance.goal or ""

        # If the goal changed, trigger instructions review across all departments
        if new_goal != old_goal:
            from projects.tasks_consolidation import review_agent_instructions_after_goal_change

            review_agent_instructions_after_goal_change.delay(str(instance.id))
