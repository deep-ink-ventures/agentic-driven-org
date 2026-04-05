import logging
import os

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.generics import CreateAPIView, ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated

from agents.blueprints import DEPARTMENTS
from projects.extraction import compute_content_hash, extract_text
from projects.models import Briefing, Project, Source
from projects.serializers import BriefingSerializer
from projects.storage import upload_file

logger = logging.getLogger(__name__)

ALLOWED_FILE_FORMATS = {"pdf", "docx", "txt", "md", "markdown", "csv"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class BriefingListCreateView(ListCreateAPIView):
    """List and create briefings for a project."""

    serializer_class = BriefingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs["project_id"]
        qs = (
            Briefing.objects.filter(
                project_id=project_id,
                project__members=self.request.user,
            )
            .annotate(
                task_count=Count("tasks"),
            )
            .select_related("created_by", "department")
            .prefetch_related("attachments")
        )

        # Filter by status (default: active)
        status = self.request.query_params.get("status", "active")
        if status != "all":
            qs = qs.filter(status=status)

        # Filter by department
        department = self.request.query_params.get("department")
        if department:
            # Include department-specific + project-level briefings
            qs = qs.filter(Q(department_id=department) | Q(department__isnull=True))

        return qs

    def perform_create(self, serializer):
        project = get_object_or_404(Project, id=self.kwargs["project_id"], members=self.request.user)

        # Auto-generate title from content if not provided
        title = serializer.validated_data.get("title") or ""
        if not title:
            content = serializer.validated_data.get("content", "")
            title = content[:50].strip()
            if len(content) > 50:
                title += "..."

        briefing = serializer.save(
            project=project,
            created_by=self.request.user,
            title=title,
        )

        # Trigger leader task proposals for relevant departments
        self._trigger_leaders(briefing, project)

    def _trigger_leaders(self, briefing, project):
        from agents.tasks import create_next_leader_task

        departments = [briefing.department] if briefing.department else list(project.departments.all())

        for dept in departments:
            leader = dept.agents.filter(is_leader=True, status="active").first()
            if not leader:
                continue

            # Respect execution_mode for delay
            dept_def = DEPARTMENTS.get(dept.department_type, {})
            default_mode = dept_def.get("execution_mode", "scheduled")
            exec_mode = (dept.config or {}).get("execution_mode", default_mode)

            if exec_mode == "continuous":
                delay = (dept.config or {}).get(
                    "min_delay_seconds",
                    dept_def.get("min_delay_seconds", 0),
                )
            else:
                delay = 0  # For scheduled mode, trigger immediately so leader can evaluate

            create_next_leader_task.apply_async(
                args=[str(leader.id)],
                countdown=delay,
            )
            logger.info(
                "Briefing %s: triggered leader %s (delay=%ds)",
                briefing.id,
                leader.name,
                delay,
            )


class BriefingDetailView(RetrieveUpdateAPIView):
    """Retrieve or update (archive) a briefing."""

    serializer_class = BriefingSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "briefing_id"

    def get_queryset(self):
        return (
            Briefing.objects.filter(
                project_id=self.kwargs["project_id"],
                project__members=self.request.user,
            )
            .annotate(
                task_count=Count("tasks"),
            )
            .select_related("created_by", "department")
            .prefetch_related("attachments")
        )


class BriefingFileUploadView(CreateAPIView):
    """Upload a file attachment to a briefing."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def create(self, request, *args, **kwargs):
        from rest_framework import status
        from rest_framework.exceptions import ValidationError
        from rest_framework.response import Response

        project = get_object_or_404(
            Project,
            id=self.kwargs["project_id"],
            members=request.user,
        )
        briefing = get_object_or_404(
            Briefing,
            id=self.kwargs["briefing_id"],
            project=project,
        )

        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            raise ValidationError("No file provided.")

        content = uploaded_file.read()
        if len(content) > MAX_FILE_SIZE:
            raise ValidationError(f"File exceeds maximum size of {MAX_FILE_SIZE // (1024 * 1024)}MB.")

        safe_name = os.path.basename(uploaded_file.name)
        file_ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
        if file_ext not in ALLOWED_FILE_FORMATS:
            raise ValidationError(
                f"File type '{file_ext}' is not allowed. Allowed: {', '.join(sorted(ALLOWED_FILE_FORMATS))}"
            )

        source = Source.objects.create(
            project=project,
            briefing=briefing,
            user=request.user,
            source_type="file",
            original_filename=safe_name,
            file_size=len(content),
            content_type=uploaded_file.content_type or "",
            file_format=file_ext,
            content_hash=compute_content_hash(content),
            file_key=upload_file(content, safe_name, str(project.id)),
        )

        # Auto-extract text
        text = extract_text(source)
        if text:
            source.extracted_text = text
            source.word_count = len(text.split())
            source.save(update_fields=["extracted_text", "word_count"])

        from projects.serializers.briefing_serializer import BriefingAttachmentSerializer

        return Response(
            BriefingAttachmentSerializer(source).data,
            status=status.HTTP_201_CREATED,
        )
