from rest_framework import generics, permissions

from projects.models import Source, SprintNote
from projects.serializers.sprint_note_serializer import SprintNoteSerializer


class SprintNoteListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SprintNoteSerializer

    def get_queryset(self):
        return (
            SprintNote.objects.filter(
                sprint_id=self.kwargs["sprint_id"],
                sprint__project_id=self.kwargs["project_id"],
            )
            .select_related("user")
            .prefetch_related("sources")
        )

    def perform_create(self, serializer):
        note = serializer.save(
            sprint_id=self.kwargs["sprint_id"],
            user=self.request.user,
        )

        source_ids = serializer.validated_data.get("source_ids", [])
        if source_ids:
            sources = Source.objects.filter(
                id__in=source_ids,
                project_id=self.kwargs["project_id"],
            )
            note.sources.set(sources)
