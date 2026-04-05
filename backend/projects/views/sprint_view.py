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

        source_ids = serializer.validated_data.get("source_ids", [])
        if source_ids:
            Source.objects.filter(
                id__in=source_ids,
                project_id=self.kwargs["project_id"],
            ).update(sprint=sprint)

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

        if old_status == Sprint.Status.PAUSED and new_status == Sprint.Status.RUNNING:
            from agents.models import Agent
            from agents.tasks import create_next_leader_task

            for dept in sprint.departments.all():
                leader = Agent.objects.filter(
                    department=dept,
                    is_leader=True,
                    status=Agent.Status.ACTIVE,
                ).first()
                if leader:
                    create_next_leader_task.delay(str(leader.id))


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
