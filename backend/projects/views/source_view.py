from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated

from projects.models import Source, Project
from projects.serializers import SourceSerializer
from projects.extraction import extract_text


class ProjectSourceListView(ListCreateAPIView):
    """List and create sources for a project. Auto-extracts text on creation."""
    serializer_class = SourceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Source.objects.filter(
            project_id=self.kwargs["project_id"],
            project__owner=self.request.user,
        )

    def perform_create(self, serializer):
        project = Project.objects.get(id=self.kwargs["project_id"], owner=self.request.user)
        source = serializer.save(project=project, user=self.request.user)

        # Auto-extract text
        if source.source_type == "text" and source.raw_content:
            source.extracted_text = source.raw_content
            source.word_count = len(source.raw_content.split())
            source.save(update_fields=["extracted_text", "word_count"])
        elif source.source_type in ("file", "url"):
            text = extract_text(source)
            if text:
                source.extracted_text = text
                source.word_count = len(text.split())
                source.save(update_fields=["extracted_text", "word_count"])
