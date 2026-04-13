from rest_framework.generics import ListCreateAPIView
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from projects.extraction import compute_content_hash, extract_text
from projects.models import Project, Source
from projects.serializers import SourceSerializer
from projects.storage import upload_file


class ProjectSourceListView(ListCreateAPIView):
    """List and create sources for a project. Accepts JSON or multipart file uploads."""

    serializer_class = SourceSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser]

    def get_queryset(self):
        return Source.objects.filter(
            project_id=self.kwargs["project_id"],
            project__members=self.request.user,
        )

    def perform_create(self, serializer):
        project = Project.objects.get(id=self.kwargs["project_id"], members=self.request.user)

        # Handle file upload via multipart
        uploaded_file = self.request.FILES.get("file")
        extra = {}
        if uploaded_file:
            content = uploaded_file.read()
            extra["source_type"] = "file"
            extra["original_filename"] = uploaded_file.name
            extra["file_size"] = len(content)
            extra["content_type"] = uploaded_file.content_type or ""
            extra["file_format"] = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
            extra["content_hash"] = compute_content_hash(content)
            extra["file_key"] = upload_file(content, uploaded_file.name, str(project.id))

        source = serializer.save(project=project, user=self.request.user, **extra)

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

        # Generate summary and classify priority asynchronously
        from projects.tasks import classify_source_priority, summarize_source

        summarize_source.delay(str(source.id))
        classify_source_priority.delay(str(source.id))
