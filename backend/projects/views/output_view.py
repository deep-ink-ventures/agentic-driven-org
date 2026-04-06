from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from projects.models import Output
from projects.serializers import OutputDetailSerializer, OutputListSerializer


class SprintOutputListView(ListAPIView):
    """List outputs for a sprint. Filter by ?department=, ?output_type=."""

    serializer_class = OutputListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Output.objects.filter(
            sprint_id=self.kwargs["sprint_id"],
            sprint__project__members=self.request.user,
        ).select_related("created_by_task")

        department = self.request.query_params.get("department")
        if department:
            qs = qs.filter(department_id=department)

        output_type = self.request.query_params.get("output_type")
        if output_type:
            qs = qs.filter(output_type=output_type)

        return qs


class SprintOutputDetailView(RetrieveAPIView):
    """Retrieve a single output with full content."""

    serializer_class = OutputDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "output_id"

    def get_queryset(self):
        return Output.objects.filter(
            sprint_id=self.kwargs["sprint_id"],
            sprint__project__members=self.request.user,
        ).select_related("created_by_task")
