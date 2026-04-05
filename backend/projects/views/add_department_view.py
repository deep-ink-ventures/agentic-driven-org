import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.blueprints import (
    DEPARTMENTS,
    get_department_config_schema,
    get_workforce_for_department,
    get_workforce_metadata,
)
from agents.models import Agent
from projects.models import Department, Project
from projects.tasks import configure_new_department

logger = logging.getLogger(__name__)


def _get_recommendations(project):
    """Wrapper for easy mocking in tests."""
    from projects.tasks import get_department_recommendations

    return get_department_recommendations(project)


class AvailableDepartmentsView(APIView):
    """GET /api/projects/{project_id}/departments/available/ — all departments with Claude recommendations."""

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, members=request.user)
        installed = set(project.departments.values_list("department_type", flat=True))

        try:
            recommendations = _get_recommendations(project)
        except Exception:
            logger.exception("Failed to get recommendations")
            recommendations = {"departments": [], "agents": {}}

        recommended_depts = set(recommendations.get("departments", []))
        recommended_agents = recommendations.get("agents", {})

        departments = []
        for slug, dept in DEPARTMENTS.items():
            if slug in installed:
                continue
            metadata = get_workforce_metadata(slug)
            rec_agents = set(recommended_agents.get(slug, []))

            workforce = [
                {
                    "agent_type": m["agent_type"],
                    "name": m["name"],
                    "description": m["description"],
                    "recommended": m["agent_type"] in rec_agents,
                    "essential": m["essential"],
                    "controls": m["controls"],
                }
                for m in metadata
            ]

            departments.append(
                {
                    "department_type": slug,
                    "name": dept["name"],
                    "description": dept["description"],
                    "recommended": slug in recommended_depts,
                    "config_schema": get_department_config_schema(slug),
                    "workforce": workforce,
                }
            )

        return Response({"departments": departments})


class AvailableAgentsView(APIView):
    """GET /api/projects/{project_id}/departments/{dept_id}/available-agents/ — unprovisioned agents for an installed department."""

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, dept_id):
        project = get_object_or_404(Project, id=project_id, members=request.user)
        department = get_object_or_404(Department, id=dept_id, project=project)
        metadata = get_workforce_metadata(department.department_type)
        provisioned = set(department.agents.values_list("agent_type", flat=True))
        available = [m for m in metadata if m["agent_type"] not in provisioned]
        return Response({"agents": available})


class AddDepartmentView(APIView):
    """POST /api/projects/{project_id}/departments/add/ — add departments with explicit agent selection."""

    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, members=request.user)
        departments_data = request.data.get("departments", [])
        context = request.data.get("context", "")

        if not departments_data:
            return Response({"error": "departments is required."}, status=status.HTTP_400_BAD_REQUEST)

        for dept_data in departments_data:
            dt = dept_data.get("department_type")
            if not dt or dt not in DEPARTMENTS:
                return Response(
                    {"error": f"Unknown department type: {dt}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        created = []
        for dept_data in departments_data:
            dt = dept_data["department_type"]
            if project.departments.filter(department_type=dt).exists():
                continue
            dept = Department.objects.create(project=project, department_type=dt)
            created.append(dept)

            # Create leader as provisioning
            Agent.objects.create(
                name=f"Head of {dept.name}",
                agent_type="leader",
                department=dept,
                is_leader=True,
                status=Agent.Status.PROVISIONING,
                instructions="",
            )

            # Create selected agents as provisioning
            selected_types = set(dept_data.get("agents", []))
            available_workforce = get_workforce_for_department(dt)

            # Add essential + controller agents
            metadata = get_workforce_metadata(dt)
            for m in metadata:
                if m["essential"] and m["agent_type"] not in selected_types:
                    selected_types.add(m["agent_type"])
            for m in metadata:
                if not m["controls"]:
                    continue
                controls_list = m["controls"] if isinstance(m["controls"], list) else [m["controls"]]
                if any(c in selected_types for c in controls_list) and m["agent_type"] not in selected_types:
                    selected_types.add(m["agent_type"])

            for agent_type in selected_types:
                if agent_type not in available_workforce:
                    continue
                bp = available_workforce[agent_type]
                Agent.objects.create(
                    name=bp.name,
                    agent_type=agent_type,
                    department=dept,
                    is_leader=False,
                    status=Agent.Status.PROVISIONING,
                    instructions="",
                )

        if not created:
            return Response(
                {"error": "No new departments to add — all requested are already installed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for dept in created:
            configure_new_department.delay(str(dept.id), context)

        return Response(
            {
                "departments": [{"id": str(d.id), "department_type": d.department_type} for d in created],
                "status": "configuring",
            },
            status=status.HTTP_202_ACCEPTED,
        )
