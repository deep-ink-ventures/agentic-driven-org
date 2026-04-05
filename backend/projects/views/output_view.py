from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from projects.models import Output
from projects.serializers import OutputDetailSerializer, OutputListSerializer


class ProjectOutputListView(ListAPIView):
    """List outputs for a project. Filter by ?department=, ?label=, ?output_type=."""

    serializer_class = OutputListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Output.objects.filter(
            project_id=self.kwargs["project_id"],
            project__members=self.request.user,
        ).select_related("created_by_task")

        department = self.request.query_params.get("department")
        if department:
            qs = qs.filter(department_id=department)

        label = self.request.query_params.get("label")
        if label:
            qs = qs.filter(label=label)

        output_type = self.request.query_params.get("output_type")
        if output_type:
            qs = qs.filter(output_type=output_type)

        return qs


class ProjectOutputDetailView(RetrieveAPIView):
    """Retrieve a single output with full content."""

    serializer_class = OutputDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "output_id"

    def get_queryset(self):
        return Output.objects.filter(
            project_id=self.kwargs["project_id"],
            project__members=self.request.user,
        ).select_related("created_by_task")
