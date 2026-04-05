import json
import logging

from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

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

        for dept_id in department_ids:
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


class SprintSuggestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, project_id):
        from agents.ai.claude_client import call_claude, parse_json_response
        from projects.models import Department, Document, Project

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        department_ids = request.data.get("department_ids", [])
        departments = Department.objects.filter(id__in=department_ids, project=project)

        dept_info = []
        for dept in departments:
            docs = list(Document.objects.filter(department=dept).values_list("title", flat=True)[:10])
            from agents.models import AgentTask

            recent_tasks = list(
                AgentTask.objects.filter(
                    agent__department=dept,
                    status=AgentTask.Status.DONE,
                )
                .order_by("-completed_at")
                .values_list("exec_summary", flat=True)[:10]
            )
            dept_info.append(
                {
                    "name": dept.display_name,
                    "type": dept.department_type,
                    "documents": docs,
                    "recent_completed_tasks": recent_tasks,
                }
            )

        running_sprints = list(
            Sprint.objects.filter(
                project=project,
                status=Sprint.Status.RUNNING,
            ).values_list("text", flat=True)
        )

        system_prompt = (
            "You are a project strategist. Given the project goal and current state, "
            "suggest 3 high-impact actions that would move the project forward. "
            "Be specific and actionable. Don't suggest anything already in progress. "
            "Respond with a JSON array of exactly 3 strings. No markdown fences."
        )

        user_message = f"""# Project: {project.name}

## Project Goal
{project.goal or "No goal set."}

## Departments
{json.dumps(dept_info, indent=2)}

## Currently Running Sprints
{json.dumps(running_sprints) if running_sprints else "None — nothing is in progress."}

Suggest 3 specific, actionable next steps. Return as JSON array of 3 strings."""

        try:
            response, _usage = call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
            )
            suggestions = parse_json_response(response)
            if isinstance(suggestions, list):
                return Response({"suggestions": suggestions[:3]})
            return Response({"suggestions": []})
        except Exception:
            logger.exception("Failed to generate sprint suggestions")
            return Response({"suggestions": []})


def _broadcast_sprint(sprint, event_type="sprint.updated"):
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    try:
        from projects.serializers import SprintSerializer

        data = SprintSerializer(sprint).data
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
