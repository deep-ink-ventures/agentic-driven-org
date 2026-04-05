# Sprints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace seed-first-task and execution modes with user-driven Sprints that persist in the sidebar and drive departments until leaders declare them done.

**Architecture:** New `Sprint` model with M2M to departments. AgentTask and Source get sprint FK. Leader's `generate_task_proposal` queries running sprints instead of inventing work. Frontend gets sprint input at top of task queue, sprint list in sidebar, and Haiku-powered suggestions.

**Tech Stack:** Django, DRF, Celery, Next.js, WebSocket (Django Channels), Claude Haiku for suggestions

**Spec:** `docs/superpowers/specs/2026-04-05-sprints-design.md`

---

### Task 1: Sprint Model + Migration

**Files:**
- Create: `backend/projects/models/sprint.py`
- Modify: `backend/projects/models/__init__.py`
- Modify: `backend/projects/models/source.py` (add sprint FK)
- Modify: `backend/agents/models/agent_task.py` (add sprint FK)

- [ ] **Step 1: Create the Sprint model**

```python
# backend/projects/models/sprint.py
import uuid

from django.conf import settings
from django.db import models


class Sprint(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        DONE = "done", "Done"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="sprints",
    )
    departments = models.ManyToManyField(
        "projects.Department",
        related_name="sprints",
    )
    text = models.TextField(help_text="The work instruction from the user")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.RUNNING,
        db_index=True,
    )
    completion_summary = models.TextField(
        blank=True,
        help_text="Leader-provided summary when marking sprint done",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sprints",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.status}] {self.text[:60]} — {self.project.name}"
```

- [ ] **Step 2: Register Sprint in models __init__**

In `backend/projects/models/__init__.py`, add:

```python
from .sprint import Sprint
```

And add `"Sprint"` to `__all__`.

The file should look like:

```python
from .bootstrap_proposal import BootstrapProposal
from .department import Department
from .document import Document
from .project import Project
from .project_config import ProjectConfig
from .source import Source
from .sprint import Sprint
from .tag import Tag

__all__ = ["ProjectConfig", "Project", "Department", "Tag", "Document", "Source", "BootstrapProposal", "Sprint"]
```

- [ ] **Step 3: Add sprint FK to Source**

In `backend/projects/models/source.py`, add after the `user` FK (after line 42):

```python
    sprint = models.ForeignKey(
        "projects.Sprint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sources",
    )
```

- [ ] **Step 4: Add sprint FK to AgentTask**

In `backend/agents/models/agent_task.py`, add after the `blocked_by` FK (after line 50):

```python
    sprint = models.ForeignKey(
        "projects.Sprint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
```

- [ ] **Step 5: Generate and run migration**

Run:
```bash
cd backend && source venv/bin/activate
python manage.py makemigrations projects agents
python manage.py migrate
```

Expected: Migration creates `projects_sprint` table, `projects_sprint_departments` M2M table, adds `sprint_id` column to `projects_source` and `agents_agenttask`.

- [ ] **Step 6: Commit**

```bash
git add backend/projects/models/sprint.py backend/projects/models/__init__.py backend/projects/models/source.py backend/agents/models/agent_task.py backend/projects/migrations/ backend/agents/migrations/
git commit -m "feat: add Sprint model with FK on Source and AgentTask"
```

---

### Task 2: Sprint Serializer + API Views

**Files:**
- Create: `backend/projects/serializers/sprint_serializer.py`
- Modify: `backend/projects/serializers/__init__.py`
- Create: `backend/projects/views/sprint_view.py`
- Modify: `backend/projects/views/__init__.py`
- Modify: `backend/projects/urls.py`

- [ ] **Step 1: Create Sprint serializer**

```python
# backend/projects/serializers/sprint_serializer.py
from rest_framework import serializers

from projects.models import Sprint


class SprintSerializer(serializers.ModelSerializer):
    department_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
    )
    source_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        default=list,
    )
    departments = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Sprint
        fields = [
            "id",
            "project",
            "text",
            "status",
            "completion_summary",
            "departments",
            "department_ids",
            "source_ids",
            "task_count",
            "created_by_email",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "status",
            "completion_summary",
            "created_by_email",
            "created_at",
            "updated_at",
            "completed_at",
        ]

    def get_departments(self, obj):
        return [
            {"id": str(d.id), "department_type": d.department_type, "display_name": d.display_name}
            for d in obj.departments.all()
        ]

    def get_task_count(self, obj):
        return obj.tasks.count()
```

- [ ] **Step 2: Register serializer in __init__**

In `backend/projects/serializers/__init__.py`, add:

```python
from .sprint_serializer import SprintSerializer
```

Add `"SprintSerializer"` to `__all__`.

- [ ] **Step 3: Create Sprint views**

```python
# backend/projects/views/sprint_view.py
import json
import logging

from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Sprint, Source

logger = logging.getLogger(__name__)


class SprintListCreateView(generics.ListCreateAPIView):
    """List sprints for a project, or create a new sprint."""

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

        # Link departments
        department_ids = serializer.validated_data.get("department_ids", [])
        sprint.departments.set(department_ids)

        # Link sources
        source_ids = serializer.validated_data.get("source_ids", [])
        if source_ids:
            Source.objects.filter(
                id__in=source_ids,
                project_id=self.kwargs["project_id"],
            ).update(sprint=sprint)

        # Broadcast sprint creation
        _broadcast_sprint(sprint, "sprint.created")

        # Trigger leaders for each department
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
    """Get or update a sprint (status changes)."""

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

        # If resumed (paused → running), trigger leaders
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
    """Generate 3 suggestions for what to work on next."""

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

        # Gather context
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
    """Send sprint update via WebSocket to the project channel."""
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
```

- [ ] **Step 4: Register views in __init__**

In `backend/projects/views/__init__.py`, add:

```python
from .sprint_view import SprintDetailView, SprintListCreateView, SprintSuggestView
```

Add `"SprintListCreateView"`, `"SprintDetailView"`, `"SprintSuggestView"` to `__all__`.

- [ ] **Step 5: Add URL patterns**

In `backend/projects/urls.py`, add before the closing `]`:

```python
    path("projects/<uuid:project_id>/sprints/", views.SprintListCreateView.as_view(), name="sprint-list"),
    path("projects/<uuid:project_id>/sprints/suggest/", views.SprintSuggestView.as_view(), name="sprint-suggest"),
    path(
        "projects/<uuid:project_id>/sprints/<uuid:sprint_id>/",
        views.SprintDetailView.as_view(),
        name="sprint-detail",
    ),
```

- [ ] **Step 6: Add sprint admin**

Create `backend/projects/admin/sprint_admin.py`:

```python
from django.contrib import admin

from projects.models import Sprint


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("text_preview", "status", "project", "created_at")
    list_filter = ("status", "project")
    search_fields = ("text",)
    readonly_fields = ("created_at", "updated_at", "completed_at")

    def text_preview(self, obj):
        return obj.text[:80]

    text_preview.short_description = "Text"
```

- [ ] **Step 7: Add WebSocket handlers for sprint events**

In `backend/projects/consumers.py`, add two methods to `ProjectConsumer` after the `task_updated` method:

```python
    async def sprint_created(self, event):
        """Forward sprint created event."""
        await self.send(text_data=json.dumps({"type": "sprint.created", "sprint": event.get("sprint")}))

    async def sprint_updated(self, event):
        """Forward sprint updated event."""
        await self.send(text_data=json.dumps({"type": "sprint.updated", "sprint": event.get("sprint")}))
```

- [ ] **Step 8: Add sprint field to task serializer and broadcast**

In `backend/agents/serializers/agent_task_serializer.py`, add `"sprint"` to the `fields` list after `"blocked_by_summary"`.

In `backend/agents/tasks.py`, in the `_broadcast_task` function, add after the `"review_score"` line (line 44):

```python
                    "sprint": str(task.sprint_id) if task.sprint_id else None,
```

- [ ] **Step 9: Commit**

```bash
git add backend/projects/serializers/sprint_serializer.py backend/projects/views/sprint_view.py backend/projects/admin/sprint_admin.py backend/projects/serializers/__init__.py backend/projects/views/__init__.py backend/projects/urls.py backend/projects/consumers.py backend/agents/serializers/agent_task_serializer.py backend/agents/tasks.py
git commit -m "feat: add Sprint API endpoints, serializer, and WebSocket events"
```

---

### Task 3: Leader Behavior — Sprint-Driven Proposals

**Files:**
- Modify: `backend/agents/blueprints/base.py` (rewrite `generate_task_proposal`)
- Modify: `backend/agents/tasks.py` (replace `_trigger_continuous_mode`, update `create_next_leader_task`)
- Modify: `backend/agents/admin/agent_admin.py` (remove `seed_first_task`)

- [ ] **Step 1: Rewrite `generate_task_proposal` on LeaderBlueprint**

In `backend/agents/blueprints/base.py`, replace the entire `generate_task_proposal` method (lines 930-1052) with:

```python
    def generate_task_proposal(self, agent: Agent) -> dict | None:
        """
        Propose the next task by examining running sprints for this department.

        Picks the sprint with least recent activity (round-robin fairness),
        reviews what's been done, and proposes subtasks to advance it.
        Returns None if no running sprints exist.
        """
        import json
        import logging

        from agents.ai.claude_client import call_claude, parse_json_response

        logger = logging.getLogger(__name__)

        department = agent.department
        project = department.project

        # Find running sprints for this department
        from projects.models import Sprint

        running_sprints = list(
            Sprint.objects.filter(
                departments=department,
                status=Sprint.Status.RUNNING,
            )
            .prefetch_related("sources")
            .order_by("updated_at")  # Least recently touched first
        )

        if not running_sprints:
            return None

        # Pick sprint with least recent activity
        sprint = running_sprints[0]

        # Gather available workforce agents
        workforce = Agent.objects.filter(
            department=department,
            is_leader=False,
            status=Agent.Status.ACTIVE,
        )
        if not workforce.exists():
            return None

        agents_desc = []
        for a in workforce:
            bp = a.get_blueprint()
            cmds = bp.get_commands() if bp else []
            cmd_names = [c["name"] for c in cmds]
            agents_desc.append(
                {
                    "agent_type": a.agent_type,
                    "name": a.name,
                    "description": bp.description if bp else "",
                    "commands": cmd_names,
                }
            )

        # Gather completed tasks for this sprint
        completed_tasks = list(
            AgentTask.objects.filter(
                sprint=sprint,
                status__in=[AgentTask.Status.DONE, AgentTask.Status.PROCESSING],
            )
            .order_by("-created_at")
            .values_list("exec_summary", "report")[:20]
        )
        completed_text = []
        for summary, report in completed_tasks:
            entry = summary
            if report:
                entry += f"\n  Result: {report[:300]}"
            completed_text.append(entry)

        # Gather department documents
        from projects.models import Document

        docs = list(Document.objects.filter(department=department).values_list("title", flat=True)[:20])

        # Sprint source context
        source_context = ""
        for src in sprint.sources.all()[:5]:
            text = src.summary or src.extracted_text[:500] or src.raw_content[:500]
            if text:
                source_context += f"\n- {src.original_filename or 'Attached file'}: {text[:400]}"

        locale = agent.get_config_value("locale") or "en"

        system_prompt = f"""You are a department leader advancing a specific work instruction (sprint).

You MUST respond with valid JSON only. No markdown fences, no explanation.

## Your Process
1. READ the sprint instruction carefully — this is what the user wants done.
2. REVIEW what has been completed so far for this sprint.
3. ASSESS: What's still missing? What would move this sprint closest to completion?
4. PROPOSE: The most impactful next task(s) to advance the sprint.
5. COMPLETE: If the sprint goal has been fully met with excellence, set "sprint_done" to true.

## Rules
- Every task MUST advance the sprint instruction. Do not invent unrelated work.
- Propose ONE task (or a small chain if they form a logical unit).
- Each task must target a specific agent by agent_type with a specific command_name.
- The step_plan must be detailed — reference specific project details, characters, themes, goals.
- All output in {locale}.
- If you believe the sprint is COMPLETE (goal fully met), set "sprint_done": true and provide "completion_summary".

## Response JSON Schema
{{{{
    "sprint_done": false,
    "completion_summary": "",
    "exec_summary": "Brief description of what this task achieves",
    "tasks": [
        {{{{
            "target_agent_type": "agent_type_slug",
            "command_name": "command_name",
            "exec_summary": "What this specific agent should deliver",
            "step_plan": "Detailed, actionable instructions for the agent...",
            "depends_on_previous": false
        }}}}
    ]
}}}}"""

        user_message = f"""# Project: {project.name}

## Project Goal
{project.goal or "No goal set."}

## Sprint Instruction
{sprint.text}

## Sprint Context Files
{source_context or "None."}

## Leader Instructions
{agent.instructions or "No specific instructions."}

## Available Agents
{json.dumps(agents_desc, indent=2)}

## Work Completed So Far (for this sprint)
{json.dumps(completed_text) if completed_text else "Nothing yet — this sprint just started."}

## Department Documents
{json.dumps(docs) if docs else "None yet."}

What is the next step to advance this sprint toward completion?"""

        try:
            response, _usage = call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=4096,
            )
            result = parse_json_response(response)
            if not result:
                logger.warning("Leader %s: failed to parse sprint proposal", agent.name)
                return None

            # Check if leader declares sprint done
            if result.get("sprint_done"):
                sprint.status = Sprint.Status.DONE
                sprint.completion_summary = result.get("completion_summary", "Sprint completed.")
                sprint.completed_at = timezone.now()
                sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])

                from projects.views.sprint_view import _broadcast_sprint

                _broadcast_sprint(sprint, "sprint.updated")
                logger.info("Leader %s declared sprint done: %s", agent.name, sprint.text[:60])
                return None

            # Tag the proposal with the sprint ID so create_next_leader_task can set it
            result["_sprint_id"] = str(sprint.id)
            return result

        except Exception as e:
            logger.exception("Leader %s: sprint proposal failed: %s", agent.name, e)
            return None
```

- [ ] **Step 2: Update `create_next_leader_task` to propagate sprint FK**

In `backend/agents/tasks.py`, in the `create_next_leader_task` function, after line 270 (`proposal = blueprint.generate_task_proposal(agent)`), extract the sprint ID:

```python
        # Extract sprint ID from proposal (set by generate_task_proposal)
        sprint_id = proposal.pop("_sprint_id", None) if proposal else None
```

Then in every `AgentTask.objects.create()` call within this function, add `sprint_id=sprint_id`:

At line 314 (multi-task creation):
```python
                new_task = AgentTask.objects.create(
                    agent=target_agent,
                    created_by_agent=agent,
                    status=initial_status,
                    command_name=command_name,
                    blocked_by=blocked_by,
                    exec_summary=task_data.get("exec_summary", "Priority task"),
                    step_plan=task_data.get("step_plan", ""),
                    sprint_id=sprint_id,
                )
```

At line 342 (fallback single task):
```python
            new_task = AgentTask.objects.create(
                agent=agent,
                status=initial_status,
                auto_execute=False,
                exec_summary=proposal.get("exec_summary", "Leader task"),
                step_plan=proposal.get("step_plan", ""),
                sprint_id=sprint_id,
            )
```

- [ ] **Step 3: Replace `_trigger_continuous_mode` with sprint-aware trigger**

In `backend/agents/tasks.py`, replace the entire `_trigger_continuous_mode` function (lines 216-243) with:

```python
def _trigger_next_sprint_work(completed_task):
    """After task completion, trigger leader if department has running sprints."""
    from projects.models import Sprint

    department = completed_task.agent.department

    has_running_sprints = Sprint.objects.filter(
        departments=department,
        status=Sprint.Status.RUNNING,
    ).exists()

    if not has_running_sprints:
        return

    leader = department.agents.filter(is_leader=True, status="active").first()
    if leader:
        create_next_leader_task.delay(str(leader.id))
        logger.info("Sprint work: triggering leader %s after task completion", leader.name)
```

- [ ] **Step 4: Update `execute_agent_task` to call new trigger**

In `backend/agents/tasks.py`, in `execute_agent_task`, replace the call to `_trigger_continuous_mode(task)` (line 146) with:

```python
        _trigger_next_sprint_work(task)
```

- [ ] **Step 5: Remove `seed_first_task` admin action**

In `backend/agents/admin/agent_admin.py`, remove `actions = ["seed_first_task"]` (line 29) and the entire `seed_first_task` method (lines 31-39).

The file should look like:

```python
from django.contrib import admin

from agents.models import Agent, AgentTask


class AgentTaskInline(admin.TabularInline):
    model = AgentTask
    fk_name = "agent"
    extra = 0
    fields = ("status", "exec_summary", "auto_execute", "proposed_exec_at", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    show_change_link = True
    max_num = 10


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "agent_type", "department", "is_leader", "auto_approve", "status")
    list_filter = ("agent_type", "status", "is_leader", "auto_approve", "department__project")
    search_fields = ("name", "department__name")
    ordering = ("department", "-is_leader", "name")
    fieldsets = (
        (None, {"fields": ("name", "agent_type", "department", "is_leader")}),
        ("Configuration", {"fields": ("instructions", "config", "auto_approve", "status")}),
        ("Internal State", {"fields": ("internal_state",), "classes": ("collapse",)}),
    )
    inlines = [AgentTaskInline]
```

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/base.py backend/agents/tasks.py backend/agents/admin/agent_admin.py
git commit -m "feat: sprint-driven leader proposals, replace continuous mode trigger"
```

---

### Task 4: Frontend Types + API Client

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Add Sprint type and update AgentTask**

In `frontend/lib/types.ts`, add after the `ProjectDetail` interface (after line 92):

```typescript
export interface SprintDepartment {
  id: string;
  department_type: string;
  display_name: string;
}

export interface Sprint {
  id: string;
  project: string;
  text: string;
  status: "running" | "paused" | "done";
  completion_summary: string;
  departments: SprintDepartment[];
  task_count: number;
  created_by_email: string;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}
```

In the `AgentTask` interface, add after `blocked_by_summary` (after line 105):

```typescript
  sprint: string | null;
```

- [ ] **Step 2: Add sprint API functions**

In `frontend/lib/api.ts`, add before the closing `};` (before line 258):

```typescript
  listSprints: (projectId: string, params?: { status?: string; department?: string }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set("status", params.status);
    if (params?.department) sp.set("department", params.department);
    const qs = sp.toString();
    return request<import("./types").Sprint[]>(
      `/api/projects/${projectId}/sprints/${qs ? `?${qs}` : ""}`,
    );
  },

  createSprint: (projectId: string, data: { text: string; department_ids: string[]; source_ids?: string[] }) =>
    request<import("./types").Sprint>(`/api/projects/${projectId}/sprints/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateSprint: (projectId: string, sprintId: string, data: { status?: string; completion_summary?: string }) =>
    request<import("./types").Sprint>(`/api/projects/${projectId}/sprints/${sprintId}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  suggestSprints: (projectId: string, departmentIds: string[]) =>
    request<{ suggestions: string[] }>(`/api/projects/${projectId}/sprints/suggest/`, {
      method: "POST",
      body: JSON.stringify({ department_ids: departmentIds }),
    }),
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts
git commit -m "feat: add Sprint types and API client functions"
```

---

### Task 5: Sprint Input Component

**Files:**
- Create: `frontend/components/sprint-input.tsx`

- [ ] **Step 1: Create the sprint input component**

```typescript
// frontend/components/sprint-input.tsx
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { DepartmentDetail } from "@/lib/types";
import { Loader2, Paperclip, X, Sparkles } from "lucide-react";

interface SprintInputProps {
  projectId: string;
  departments: DepartmentDetail[];
  defaultDepartmentId?: string;
  onCreated?: () => void;
}

export function SprintInput({
  projectId,
  departments,
  defaultDepartmentId,
  onCreated,
}: SprintInputProps) {
  const [text, setText] = useState("");
  const [selectedDeptIds, setSelectedDeptIds] = useState<Set<string>>(
    () => new Set(defaultDepartmentId ? [defaultDepartmentId] : []),
  );
  const [files, setFiles] = useState<File[]>([]);
  const [showDropZone, setShowDropZone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);

  // Load suggestions on mount and when departments change
  const loadSuggestions = useCallback(async () => {
    const deptIds = Array.from(selectedDeptIds);
    if (deptIds.length === 0) {
      setSuggestions([]);
      return;
    }
    setLoadingSuggestions(true);
    try {
      const res = await api.suggestSprints(projectId, deptIds);
      setSuggestions(res.suggestions || []);
    } catch {
      setSuggestions([]);
    } finally {
      setLoadingSuggestions(false);
    }
  }, [projectId, selectedDeptIds]);

  useEffect(() => {
    loadSuggestions();
  }, [loadSuggestions]);

  function toggleDept(deptId: string) {
    setSelectedDeptIds((prev) => {
      const next = new Set(prev);
      if (next.has(deptId)) {
        next.delete(deptId);
      } else {
        next.add(deptId);
      }
      return next;
    });
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setShowDropZone(false);
    const dropped = Array.from(e.dataTransfer.files);
    setFiles((prev) => [...prev, ...dropped]);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setShowDropZone(true);
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit() {
    if (!text.trim() || selectedDeptIds.size === 0) return;
    setSubmitting(true);
    try {
      // Upload files as sources first
      const sourceIds: string[] = [];
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
        const source = await api.uploadSource(projectId, formData);
        sourceIds.push(source.id);
      }

      await api.createSprint(projectId, {
        text: text.trim(),
        department_ids: Array.from(selectedDeptIds),
        source_ids: sourceIds,
      });

      setText("");
      setFiles([]);
      setShowDropZone(false);
      onCreated?.();
      loadSuggestions();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mb-6">
      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {loadingSuggestions ? (
            <div className="flex items-center gap-1.5 text-xs text-text-secondary">
              <Loader2 className="h-3 w-3 animate-spin" />
              Loading suggestions…
            </div>
          ) : (
            suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => setText(s)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs bg-accent-violet/8 text-accent-violet border border-accent-violet/20 hover:bg-accent-violet/15 transition-colors"
              >
                <Sparkles className="h-3 w-3" />
                {s}
              </button>
            ))
          )}
        </div>
      )}

      {/* Input area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={() => setShowDropZone(false)}
        onDrop={handleDrop}
        className="rounded-lg border border-border bg-bg-surface"
      >
        <div className="flex gap-2 p-3">
          <textarea
            ref={textRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="What should this department work on?"
            rows={1}
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-secondary/50 resize-none focus:outline-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="shrink-0 p-1.5 text-text-secondary hover:text-text-primary transition-colors"
            title="Attach files"
          >
            <Paperclip className="h-4 w-4" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            accept=".pdf,.docx,.txt,.md,.csv"
            onChange={(e) => {
              if (e.target.files) {
                setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
              }
            }}
          />
        </div>

        {/* Drop zone */}
        {showDropZone && (
          <div className="mx-3 mb-3 rounded-lg border-2 border-dashed border-accent-violet/30 bg-accent-violet/5 p-4 text-center text-xs text-accent-violet">
            Drop files here
          </div>
        )}

        {/* File chips */}
        {files.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-3 pb-2">
            {files.map((f, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-bg-input border border-border text-[10px] text-text-secondary"
              >
                {f.name}
                <button onClick={() => removeFile(i)} className="hover:text-flag-critical">
                  <X className="h-2.5 w-2.5" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Department selector + submit */}
        <div className="flex items-center justify-between border-t border-border px-3 py-2">
          <div className="flex flex-wrap gap-1.5">
            {departments.map((d) => (
              <button
                key={d.id}
                onClick={() => toggleDept(d.id)}
                className={`px-2 py-0.5 rounded-full text-[10px] border transition-colors ${
                  selectedDeptIds.has(d.id)
                    ? "bg-accent-violet/15 text-accent-violet border-accent-violet/30"
                    : "bg-bg-input text-text-secondary border-border hover:border-accent-violet/30"
                }`}
              >
                {d.display_name}
              </button>
            ))}
          </div>
          <button
            onClick={handleSubmit}
            disabled={submitting || !text.trim() || selectedDeptIds.size === 0}
            className="shrink-0 px-4 py-1.5 rounded-lg text-xs font-semibold bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50 transition-colors"
          >
            {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Start Sprint"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add `uploadSource` to api.ts if not present**

Check if `api.uploadSource` exists. If not, add before the closing `};`:

```typescript
  uploadSource: (projectId: string, formData: FormData) =>
    fetch(`/api/projects/${projectId}/sources/`, {
      method: "POST",
      headers: { "X-CSRFToken": getCsrf() },
      credentials: "include",
      body: formData,
    }).then(async (r) => {
      if (!r.ok) throw new Error(await r.text());
      return r.json() as Promise<import("./types").Source>;
    }),
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/sprint-input.tsx frontend/lib/api.ts
git commit -m "feat: add SprintInput component with suggestions and file drop"
```

---

### Task 6: Integrate Sprint Input into Task Queue + Department View

**Files:**
- Modify: `frontend/components/task-queue.tsx`
- Modify: `frontend/components/department-view.tsx`

- [ ] **Step 1: Add sprint input to TaskQueue**

In `frontend/components/task-queue.tsx`, update the `TaskQueue` component props and add the sprint input. Replace the `TaskQueue` export (lines 499-541) with:

```typescript
export function TaskQueue({
  projectId,
  department,
  agent,
  wsEvent,
  departments,
  onSprintCreated,
}: {
  projectId: string;
  department?: string;
  agent?: string;
  wsEvent?: { type: string; task: AgentTask } | null;
  departments?: import("@/lib/types").DepartmentDetail[];
  onSprintCreated?: () => void;
}) {
  return (
    <div>
      {/* Sprint input — show when on department or dashboard view (not agent) */}
      {!agent && departments && departments.length > 0 && (
        <>
          <div className="mb-6">
            {/* Lazy-load to avoid circular deps */}
            <SprintInputWrapper
              projectId={projectId}
              departments={departments}
              defaultDepartmentId={department}
              onCreated={onSprintCreated}
            />
          </div>
          <div className="border-t border-border mb-6" />
        </>
      )}

      {/* Two lanes side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <TaskLane
          config={{ title: "Needs Attention", statuses: "awaiting_approval,failed" }}
          projectId={projectId}
          department={department}
          agent={agent}
          wsEvent={wsEvent}
        />
        <TaskLane
          config={{ title: "In Progress", statuses: "queued,processing,awaiting_dependencies,planned", pulse: true }}
          projectId={projectId}
          department={department}
          agent={agent}
          wsEvent={wsEvent}
        />
      </div>

      {/* Collapsed completed stack */}
      <TaskLane
        config={{ title: "Completed", statuses: "done", collapsible: true }}
        projectId={projectId}
        department={department}
        agent={agent}
        wsEvent={wsEvent}
      />
    </div>
  );
}

function SprintInputWrapper(props: {
  projectId: string;
  departments: import("@/lib/types").DepartmentDetail[];
  defaultDepartmentId?: string;
  onCreated?: () => void;
}) {
  const { SprintInput } = require("@/components/sprint-input");
  return <SprintInput {...props} />;
}
```

Add the import at the top of the file:

```typescript
import { SprintInput } from "@/components/sprint-input";
```

And remove the `SprintInputWrapper` — use SprintInput directly:

```typescript
      {!agent && departments && departments.length > 0 && (
        <>
          <div className="mb-6">
            <SprintInput
              projectId={projectId}
              departments={departments}
              defaultDepartmentId={department}
              onCreated={onSprintCreated}
            />
          </div>
          <div className="border-t border-border mb-6" />
        </>
      )}
```

- [ ] **Step 2: Pass departments to TaskQueue from DepartmentView**

In `frontend/components/department-view.tsx`, update the Tasks tab rendering (line 240-242) to pass `departments`:

```typescript
      {tab === "tasks" && (
        <TaskQueue
          projectId={projectId}
          department={dept.id}
          wsEvent={taskWsEvent}
          departments={[dept]}
        />
      )}
```

- [ ] **Step 3: Pass departments to TaskQueue from dashboard**

In `frontend/app/(app)/project/[...path]/page.tsx`, update the dashboard view (lines 359-364) to pass departments:

```typescript
        {view === "dashboard" && (
          <>
            <h2 className="text-2xl font-semibold mb-1">Task Queue</h2>
            <p className="text-sm text-text-secondary mb-6">Monitor and manage your agents&apos; work</p>
            <TaskQueue
              projectId={project.id}
              wsEvent={taskWsEvent}
              departments={project.departments}
            />
          </>
        )}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/task-queue.tsx frontend/components/department-view.tsx frontend/app/\(app\)/project/\[...path\]/page.tsx
git commit -m "feat: integrate SprintInput into TaskQueue and department/dashboard views"
```

---

### Task 7: Sidebar Sprint List + Popover

**Files:**
- Create: `frontend/components/sprint-sidebar.tsx`
- Modify: `frontend/app/(app)/project/[...path]/page.tsx`

- [ ] **Step 1: Create sprint sidebar component**

```typescript
// frontend/components/sprint-sidebar.tsx
"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Sprint } from "@/lib/types";
import { Pause, Play, Check, X } from "lucide-react";

interface SprintSidebarProps {
  sprints: Sprint[];
  onUpdate: () => void;
  projectId: string;
}

export function SprintSidebar({ sprints, onUpdate, projectId }: SprintSidebarProps) {
  const [popoverId, setPopoverId] = useState<string | null>(null);
  const [acting, setActing] = useState(false);

  const visible = sprints.filter((s) => s.status !== "done");

  async function updateStatus(sprint: Sprint, newStatus: "running" | "paused" | "done") {
    setActing(true);
    try {
      await api.updateSprint(projectId, sprint.id, { status: newStatus });
      onUpdate();
      setPopoverId(null);
    } finally {
      setActing(false);
    }
  }

  if (visible.length === 0) return null;

  return (
    <div className="px-2 py-2">
      <p className="text-[10px] uppercase text-text-secondary font-medium px-2 mb-2">
        Sprints
      </p>
      {visible.map((sprint) => (
        <div key={sprint.id} className="relative">
          <button
            onClick={() => setPopoverId(popoverId === sprint.id ? null : sprint.id)}
            className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
              sprint.status === "running"
                ? "border border-flag-strength/15 bg-flag-strength/4"
                : "border border-border bg-bg-surface"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs truncate max-w-[140px] text-text-primary">
                {sprint.text.length > 35 ? sprint.text.slice(0, 35) + "…" : sprint.text}
              </span>
              <div className="flex items-center gap-1 shrink-0 ml-2">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    sprint.status === "running" ? "bg-flag-strength animate-pulse" : "bg-text-secondary/30"
                  }`}
                />
                <span
                  className={`text-[9px] ${
                    sprint.status === "running" ? "text-flag-strength" : "text-text-secondary/50"
                  }`}
                >
                  {sprint.status}
                </span>
              </div>
            </div>
            <span className="block text-[9px] mt-0.5 text-text-secondary/60 truncate">
              {sprint.departments.map((d) => d.display_name).join(" · ")}
            </span>
          </button>

          {/* Popover */}
          {popoverId === sprint.id && (
            <div className="absolute left-0 right-0 top-full mt-1 z-50 rounded-lg border border-border bg-bg-surface shadow-lg p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-text-heading">{sprint.text}</span>
                <button
                  onClick={() => setPopoverId(null)}
                  className="text-text-secondary hover:text-text-primary"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
              <p className="text-[10px] text-text-secondary mb-3">
                {sprint.departments.map((d) => d.display_name).join(" · ")} ·{" "}
                {new Date(sprint.created_at).toLocaleDateString()}
              </p>
              <div className="flex gap-1.5">
                {sprint.status === "running" ? (
                  <button
                    onClick={() => updateStatus(sprint, "paused")}
                    disabled={acting}
                    className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-md text-[10px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30 hover:bg-amber-500/25 transition-colors"
                  >
                    <Pause className="h-3 w-3" /> Pause
                  </button>
                ) : (
                  <button
                    onClick={() => updateStatus(sprint, "running")}
                    disabled={acting}
                    className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-md text-[10px] font-semibold bg-flag-strength/10 text-flag-strength border border-flag-strength/20 hover:bg-flag-strength/20 transition-colors"
                  >
                    <Play className="h-3 w-3" /> Resume
                  </button>
                )}
                <button
                  onClick={() => updateStatus(sprint, "done")}
                  disabled={acting}
                  className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-md text-[10px] font-semibold bg-flag-strength/10 text-flag-strength border border-flag-strength/20 hover:bg-flag-strength/20 transition-colors"
                >
                  <Check className="h-3 w-3" /> Done
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Integrate sprint sidebar into project page**

In `frontend/app/(app)/project/[...path]/page.tsx`:

Add import:
```typescript
import { SprintSidebar } from "@/components/sprint-sidebar";
```

Add state for sprints after the `activeTasks` state:
```typescript
  const [sprints, setSprints] = useState<import("@/lib/types").Sprint[]>([]);
```

Add sprint loading in the `load` callback (after `setProject`):
```typescript
      api.listSprints(proj.id, { status: "running,paused" }).then(setSprints).catch(() => {});
```

In the WebSocket handler (where task events are handled), add sprint event handling:
```typescript
      if (data.type === "sprint.created" || data.type === "sprint.updated") {
        // Refresh sprints list
        api.listSprints(project!.id, { status: "running,paused" }).then(setSprints).catch(() => {});
      }
```

In the `sidebarContent`, add the SprintSidebar after the departments list (after line 291, before the bottom section):

```typescript
      <SprintSidebar
        sprints={sprints}
        onUpdate={() => {
          api.listSprints(project!.id, { status: "running,paused" }).then(setSprints).catch(() => {});
        }}
        projectId={project.id}
      />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/sprint-sidebar.tsx frontend/app/\(app\)/project/\[...path\]/page.tsx
git commit -m "feat: add sprint sidebar with popover controls"
```

---

### Task 8: Department Sprints Tab + Settings History

**Files:**
- Modify: `frontend/components/department-view.tsx`
- Modify: `frontend/app/(app)/project/[...path]/page.tsx` (settings view)

- [ ] **Step 1: Add Sprints tab to department view**

In `frontend/components/department-view.tsx`:

Add import:
```typescript
import { Zap } from "lucide-react";
```

Change the tab state type (line 31) to:
```typescript
  const [tab, setTab] = useState<"agents" | "tasks" | "sprints" | "config">("agents");
```

Add state for sprints:
```typescript
  const [deptSprints, setDeptSprints] = useState<import("@/lib/types").Sprint[]>([]);
```

Load sprints when tab changes:
```typescript
  useEffect(() => {
    if (tab === "sprints") {
      api.listSprints(projectId, { department: dept.id }).then(setDeptSprints).catch(() => {});
    }
  }, [tab, projectId, dept.id]);
```

Add the Sprints tab button after Tasks tab button (after line 145):
```typescript
        <button
          onClick={() => setTab("sprints")}
          className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
            tab === "sprints"
              ? "border-accent-violet text-accent-violet"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          <Zap className="h-3.5 w-3.5" />
          Sprints
        </button>
```

Add the Sprints tab content after the Tasks tab content (after line 242):

```typescript
      {tab === "sprints" && (
        <div className="space-y-3">
          {deptSprints.length === 0 ? (
            <p className="text-sm text-text-secondary">No sprints for this department yet.</p>
          ) : (
            deptSprints.map((sprint) => (
              <div
                key={sprint.id}
                className={`rounded-lg border p-4 ${
                  sprint.status === "running"
                    ? "border-flag-strength/20 bg-flag-strength/4"
                    : sprint.status === "paused"
                      ? "border-border bg-bg-surface"
                      : "border-border bg-bg-surface opacity-60"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-text-heading">{sprint.text}</span>
                  <span
                    className={`text-[10px] font-medium uppercase px-2 py-0.5 rounded-full ${
                      sprint.status === "running"
                        ? "bg-flag-strength/15 text-flag-strength"
                        : sprint.status === "paused"
                          ? "bg-bg-input text-text-secondary"
                          : "bg-bg-input text-text-secondary"
                    }`}
                  >
                    {sprint.status}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-[10px] text-text-secondary">
                  <span>{new Date(sprint.created_at).toLocaleDateString()}</span>
                  <span>{sprint.task_count} tasks</span>
                  <span>{sprint.created_by_email}</span>
                </div>
                {sprint.status === "done" && sprint.completion_summary && (
                  <p className="mt-2 text-xs text-text-secondary border-t border-border pt-2">
                    {sprint.completion_summary}
                  </p>
                )}
              </div>
            ))
          )}
        </div>
      )}
```

- [ ] **Step 2: Add sprint history to settings**

In `frontend/app/(app)/project/[...path]/page.tsx`, update the settings view (lines 393-404):

```typescript
        {view === "settings" && (
          <SettingsView projectId={project.id} />
        )}
```

Create a `SettingsView` component inline (or as separate file — inline is simpler):

Add before the `return` statement:

```typescript
  function SettingsView({ projectId: pid }: { projectId: string }) {
    const [allSprints, setAllSprints] = useState<import("@/lib/types").Sprint[]>([]);
    const [settingsTab, setSettingsTab] = useState<"general" | "history">("general");

    useEffect(() => {
      if (settingsTab === "history") {
        api.listSprints(pid).then(setAllSprints).catch(() => {});
      }
    }, [pid, settingsTab]);

    return (
      <div>
        <h2 className="text-2xl font-semibold mb-4">Project Settings</h2>
        <div className="flex gap-1 border-b border-border mb-6">
          <button
            onClick={() => setSettingsTab("general")}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
              settingsTab === "general"
                ? "border-accent-violet text-accent-violet"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            General
          </button>
          <button
            onClick={() => setSettingsTab("history")}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
              settingsTab === "history"
                ? "border-accent-violet text-accent-violet"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            Sprint History
          </button>
        </div>
        {settingsTab === "general" && (
          <div className="rounded-lg border border-border bg-bg-surface p-6">
            <p className="text-sm text-text-secondary">
              Project configuration coming soon.
            </p>
          </div>
        )}
        {settingsTab === "history" && (
          <div className="space-y-3">
            {allSprints.length === 0 ? (
              <p className="text-sm text-text-secondary">No sprints yet.</p>
            ) : (
              allSprints.map((sprint) => (
                <div key={sprint.id} className="rounded-lg border border-border bg-bg-surface p-4">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-text-heading">{sprint.text}</span>
                    <span
                      className={`text-[10px] font-medium uppercase px-2 py-0.5 rounded-full ${
                        sprint.status === "running"
                          ? "bg-flag-strength/15 text-flag-strength"
                          : sprint.status === "paused"
                            ? "bg-amber-500/15 text-amber-400"
                            : "bg-bg-input text-text-secondary"
                      }`}
                    >
                      {sprint.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-text-secondary">
                    <span>{sprint.departments.map((d) => d.display_name).join(", ")}</span>
                    <span>{new Date(sprint.created_at).toLocaleDateString()}</span>
                    <span>{sprint.task_count} tasks</span>
                  </div>
                  {sprint.completion_summary && (
                    <p className="mt-2 text-xs text-text-secondary border-t border-border pt-2">
                      {sprint.completion_summary}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    );
  }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/department-view.tsx frontend/app/\(app\)/project/\[...path\]/page.tsx
git commit -m "feat: add Sprints tab to department view and sprint history to settings"
```

---

### Task 9: Writers Room Integration

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`

The writers room leader overrides `generate_task_proposal` with its own stage machine. It needs to be gated by running sprints.

- [ ] **Step 1: Gate writers room proposal on running sprints**

In `backend/agents/blueprints/writers_room/leader/agent.py`, at the top of the `generate_task_proposal` method (after line 222 `from agents.models import AgentTask`), add:

```python
        # Gate on running sprints — no sprints, no work
        from projects.models import Sprint

        running_sprints = Sprint.objects.filter(
            departments=agent.department,
            status=Sprint.Status.RUNNING,
        )
        if not running_sprints.exists():
            return None

        # Use the least recently touched sprint for context
        sprint = running_sprints.order_by("updated_at").first()
```

Then in the method, wherever tasks are returned (in `_propose_creative_tasks`, `_propose_feedback_tasks`, `_propose_review_task`), the returned dicts need `"_sprint_id"` set. The easiest approach: add it at the end of `generate_task_proposal`, before each `return` of a dict result. After any `return self._propose_creative_tasks(...)` or similar call, wrap it:

Add a helper at the bottom of `generate_task_proposal`, before the state machine section:

```python
        def _tag_sprint(result):
            """Tag proposal with sprint ID for task creation."""
            if result and isinstance(result, dict):
                result["_sprint_id"] = str(sprint.id)
            return result
```

Then wrap every return that returns a proposal dict:

```python
        # Replace: return self._propose_creative_tasks(agent, current_stage, config)
        # With:
        return _tag_sprint(self._propose_creative_tasks(agent, current_stage, config))
```

Do this for every `return self._propose_*` call in the method. There are approximately 8-10 such returns throughout the state machine. Each one gets wrapped with `_tag_sprint(...)`.

- [ ] **Step 2: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py
git commit -m "feat: gate writers room on running sprints, tag proposals with sprint ID"
```

---

### Task 10: Cleanup — Remove Execution Mode Config

**Files:**
- Modify: `backend/agents/blueprints/__init__.py`

- [ ] **Step 1: Remove execution_mode and min_delay_seconds from DEPARTMENTS**

In `backend/agents/blueprints/__init__.py`, remove the `"execution_mode"` and `"min_delay_seconds"` keys from every department definition. These are in the dictionaries at approximately lines 53-54, 101, 114-115, 147, 186.

For each department dict, remove lines like:
```python
        "execution_mode": "scheduled",
        "min_delay_seconds": 0,
```

and:
```python
        "execution_mode": "continuous",
        "min_delay_seconds": 0,
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/blueprints/__init__.py
git commit -m "chore: remove execution_mode and min_delay_seconds config from departments"
```

---

### Task 11: Verify End-to-End

- [ ] **Step 1: Run backend tests**

```bash
cd backend && source venv/bin/activate && python manage.py test --verbosity=2
```

Fix any failures.

- [ ] **Step 2: Run frontend build**

```bash
cd frontend && npm run build
```

Fix any type errors.

- [ ] **Step 3: Manual smoke test**

1. Start dev environment: `./start-dev.sh`
2. Navigate to a project
3. Check sidebar — Sprints section should be empty
4. Go to a department → Tasks tab → type a sprint instruction → click Start Sprint
5. Sprint should appear in sidebar with green running indicator
6. Leader should pick up the sprint and propose tasks
7. Click sprint in sidebar → popover with Pause/Done
8. Pause → verify no new tasks proposed
9. Resume → verify tasks resume
10. Check Settings → Sprint History tab

- [ ] **Step 4: Commit any fixes**

```bash
git add -A && git commit -m "fix: end-to-end sprint integration fixes"
```
