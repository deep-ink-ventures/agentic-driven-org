from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import AgentTask
from agents.serializers import AgentTaskSerializer
from projects.models import Project


class ProjectTaskListView(ListAPIView):
    """GET /api/projects/{project_id}/tasks/ — list tasks for a project."""
    serializer_class = AgentTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs["project_id"]
        return (
            AgentTask.objects.filter(
                agent__department__project_id=project_id,
                agent__department__project__members=self.request.user,
            )
            .select_related("agent", "created_by_agent")
            .order_by("-created_at")[:100]
        )


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
            return Response({"error": f"Task is {task.status}, not awaiting_approval"}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"error": f"Task is {task.status}, not awaiting_approval"}, status=status.HTTP_400_BAD_REQUEST)

        task.status = AgentTask.Status.FAILED
        task.error_message = "Rejected"
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        return Response(AgentTaskSerializer(task).data)
