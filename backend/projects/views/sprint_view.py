import logging

from django.utils import timezone
from rest_framework import generics, permissions

from projects.models import Source, Sprint

logger = logging.getLogger(__name__)


class SprintListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        from projects.serializers import SprintSerializer

        return SprintSerializer

    def get_queryset(self):
        qs = Sprint.objects.filter(
            project_id=self.kwargs["project_id"],
        ).prefetch_related("departments")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status__in=status_filter.split(","))
        dept_filter = self.request.query_params.get("department")
        if dept_filter:
            qs = qs.filter(departments__id=dept_filter)
        return qs

    def perform_create(self, serializer):
        from agents.tasks import create_next_leader_task

        sprint = serializer.save(
            project_id=self.kwargs["project_id"],
            created_by=self.request.user,
            status=Sprint.Status.RUNNING,
        )

        from projects.models import Department

        department_ids = serializer.validated_data.get("department_ids", [])
        valid_dept_ids = list(
            Department.objects.filter(
                id__in=department_ids,
                project_id=self.kwargs["project_id"],
            ).values_list("id", flat=True)
        )
        sprint.departments.set(valid_dept_ids)

        from projects.tasks import classify_source_priority

        source_ids = serializer.validated_data.get("source_ids", [])
        if source_ids:
            Source.objects.filter(
                id__in=source_ids,
                project_id=self.kwargs["project_id"],
            ).update(sprint=sprint)
            # Classify priority for user-uploaded sources
            for sid in source_ids:
                classify_source_priority.delay(str(sid))

        # Convert outputs from referenced done sprints into Sources
        progress_sprint_ids = serializer.validated_data.get("progress_from_sprint_ids", [])
        if progress_sprint_ids:
            from projects.models import Output

            # Validate: must be done sprints in same project
            valid_sprints = Sprint.objects.filter(
                id__in=progress_sprint_ids,
                project_id=self.kwargs["project_id"],
                status=Sprint.Status.DONE,
            )
            if valid_sprints.count() != len(progress_sprint_ids):
                from rest_framework.exceptions import ValidationError

                raise ValidationError(
                    {
                        "progress_from_sprint_ids": "All referenced sprints must exist, belong to this project, and be done."
                    }
                )

            outputs = Output.objects.filter(
                sprint__in=valid_sprints,
                output_type__in=[Output.OutputType.MARKDOWN, Output.OutputType.PLAINTEXT],
            ).exclude(content="")

            from projects.tasks import summarize_source

            for output in outputs:
                src = Source.objects.create(
                    project_id=self.kwargs["project_id"],
                    source_type=Source.SourceType.TEXT,
                    original_filename=f"{output.title}.md",
                    raw_content=output.content,
                    extracted_text=output.content,
                    word_count=len(output.content.split()),
                    user=self.request.user,
                    sprint=sprint,
                )
                summarize_source.delay(str(src.id))
                classify_source_priority.delay(str(src.id))

        _broadcast_sprint(sprint, "sprint.created")

        from agents.models import Agent

        for dept_id in valid_dept_ids:
            leader = Agent.objects.filter(
                department_id=dept_id,
                is_leader=True,
                status=Agent.Status.ACTIVE,
            ).first()
            if leader:
                create_next_leader_task.delay(str(leader.id))
                logger.info("Sprint created — triggered leader %s", leader.name)


class SprintDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        from projects.serializers import SprintSerializer

        return SprintSerializer

    def get_queryset(self):
        return Sprint.objects.filter(
            project_id=self.kwargs["project_id"],
        ).prefetch_related("departments")

    lookup_url_kwarg = "sprint_id"

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        new_status = self.request.data.get("status")

        update_fields = {}
        if new_status and new_status != old_status:
            update_fields["status"] = new_status
            if new_status == Sprint.Status.DONE:
                update_fields["completed_at"] = timezone.now()
                update_fields["completion_summary"] = self.request.data.get("completion_summary", "")

        sprint = serializer.save(**update_fields)
        _broadcast_sprint(sprint, "sprint.updated")

        if old_status != Sprint.Status.RUNNING and new_status == Sprint.Status.RUNNING:
            from agents.models import Agent, AgentTask
            from agents.tasks import create_next_leader_task, execute_agent_task

            for dept in sprint.departments.all():
                # Skip if already has active work (processing)
                has_processing = AgentTask.objects.filter(
                    agent__department=dept,
                    sprint=sprint,
                    status=AgentTask.Status.PROCESSING,
                ).exists()
                if has_processing:
                    continue

                # Re-dispatch any orphaned queued tasks
                queued_tasks = list(
                    AgentTask.objects.filter(
                        agent__department=dept,
                        sprint=sprint,
                        status=AgentTask.Status.QUEUED,
                    )
                )
                if queued_tasks:
                    for task in queued_tasks:
                        execute_agent_task.delay(str(task.id))
                    continue

                # No active work at all — kick the leader
                leader = Agent.objects.filter(
                    department=dept,
                    is_leader=True,
                    status=Agent.Status.ACTIVE,
                ).first()
                if leader:
                    create_next_leader_task.delay(str(leader.id))


class SprintResetView(generics.GenericAPIView):
    """POST /api/projects/{project_id}/sprints/{sprint_id}/reset/ — reset and restart a done sprint."""

    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "sprint_id"

    def get_queryset(self):
        return Sprint.objects.filter(project_id=self.kwargs["project_id"])

    def post(self, request, *args, **kwargs):
        from rest_framework.response import Response

        sprint = self.get_object()

        from agents.models import AgentTask, ClonedAgent
        from agents.tasks import create_next_leader_task
        from projects.models import Document, Output

        AgentTask.objects.filter(sprint=sprint).delete()
        ClonedAgent.objects.filter(sprint=sprint).delete()
        Document.objects.filter(sprint=sprint).delete()
        Output.objects.filter(sprint=sprint).delete()

        sprint.department_state = {}
        sprint.status = Sprint.Status.RUNNING
        sprint.completion_summary = ""
        sprint.completed_at = None
        sprint.save(
            update_fields=[
                "department_state",
                "status",
                "completion_summary",
                "completed_at",
                "updated_at",
            ]
        )

        _broadcast_sprint(sprint, "sprint.updated")

        for dept in sprint.departments.all():
            leader = dept.agents.filter(is_leader=True, status="active").first()
            if leader:
                create_next_leader_task.delay(str(leader.id))

        logger.info("SPRINT_RESET sprint=%s via API", str(sprint.id)[:8])

        from projects.serializers import SprintSerializer

        return Response(SprintSerializer(sprint).data)


def _broadcast_sprint(sprint, event_type="sprint.updated"):
    import json

    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    from rest_framework.utils.encoders import JSONEncoder

    try:
        from projects.serializers import SprintSerializer

        # Serialize to JSON-safe dict (converts UUIDs, datetimes, etc.)
        data = json.loads(json.dumps(SprintSerializer(sprint).data, cls=JSONEncoder))
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"project_{sprint.project_id}",
            {
                "type": event_type.replace(".", "_"),
                "sprint": data,
            },
        )
    except Exception:
        logger.exception("Failed to broadcast sprint update")
