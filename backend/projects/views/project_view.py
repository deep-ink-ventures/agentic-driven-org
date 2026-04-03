from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated

from projects.models import Project
from projects.serializers import ProjectSerializer


class ProjectListView(ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(members=self.request.user).order_by("-updated_at")

    def perform_create(self, serializer):
        project = serializer.save(owner=self.request.user)
        project.members.add(self.request.user)
