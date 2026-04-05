from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import AgentTask
from agents.serializers import AgentTaskSerializer


class ProjectTaskListView(ListAPIView):
    """GET /api/projects/{project_id}/tasks/ — list tasks for a project.

    Query params:
        status      — comma-separated status filter (e.g. queued,awaiting_approval)
        department  — UUID, filter by department
        agent       — UUID, filter by agent
        limit       — page size (default 25, max 100)
        before      — ISO timestamp cursor, return tasks created before this
    """

    serializer_class = AgentTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs["project_id"]
        qs = (
            AgentTask.objects.filter(
                agent__department__project_id=project_id,
                agent__department__project__members=self.request.user,
            )
            .select_related("agent", "created_by_agent")
            .order_by("-created_at")
        )

        # ?status=queued,awaiting_approval  (comma-separated)
        status_param = self.request.query_params.get("status")
        if status_param:
            statuses = [s.strip() for s in status_param.split(",") if s.strip()]
            qs = qs.filter(status__in=statuses)

        department = self.request.query_params.get("department")
        if department:
            qs = qs.filter(agent__department_id=department)

        agent = self.request.query_params.get("agent")
        if agent:
            qs = qs.filter(agent_id=agent)

        before = self.request.query_params.get("before")
        if before:
            dt = parse_datetime(before)
            if dt:
                qs = qs.filter(created_at__lt=dt)

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        total_count = queryset.count()

        limit = min(int(request.query_params.get("limit", 25)), 100)
        page = list(queryset[:limit])

        serializer = self.get_serializer(page, many=True)
        response = Response(serializer.data)
        response["X-Total-Count"] = str(total_count)
        response["Access-Control-Expose-Headers"] = "X-Total-Count"
        return response


class TaskApproveView(APIView):
    """POST /api/projects/{project_id}/tasks/{task_id}/approve/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, task_id):
        task = get_object_or_404(
            AgentTask,
            id=task_id,
            agent__department__project_id=project_id,
            agent__department__project__members=request.user,
        )
        if task.status != AgentTask.Status.AWAITING_APPROVAL:
            return Response(
                {"error": f"Task is {task.status}, not awaiting_approval"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Allow editing step_plan and exec_summary before approval
        edited_step_plan = request.data.get("step_plan")
        edited_summary = request.data.get("exec_summary")
        update_fields = []
        if edited_step_plan is not None:
            task.step_plan = edited_step_plan
            update_fields.append("step_plan")
        if edited_summary is not None:
            task.exec_summary = edited_summary
            update_fields.append("exec_summary")
        if update_fields:
            task.save(update_fields=update_fields + ["updated_at"])

        task.approve()
        task.refresh_from_db()
        return Response(AgentTaskSerializer(task).data)


class TaskRejectView(APIView):
    """POST /api/projects/{project_id}/tasks/{task_id}/reject/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, task_id):
        task = get_object_or_404(
            AgentTask,
            id=task_id,
            agent__department__project_id=project_id,
            agent__department__project__members=request.user,
        )
        if task.status != AgentTask.Status.AWAITING_APPROVAL:
            return Response(
                {"error": f"Task is {task.status}, not awaiting_approval"}, status=status.HTTP_400_BAD_REQUEST
            )

        task.status = AgentTask.Status.FAILED
        task.error_message = "Rejected"
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        return Response(AgentTaskSerializer(task).data)
