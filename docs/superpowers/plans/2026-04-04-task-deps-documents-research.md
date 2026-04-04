# Task Dependencies, Document Types & Two-Phase Research — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add task dependency chains with auto-queue on resolve, document types with archival lifecycle, and split web research into gather (Haiku) + analyze (Sonnet) phases.

**Architecture:** `AgentTask` gets `command_name` and `blocked_by` FK fields + `awaiting_dependencies` status. `Document` gets `doc_type` and `is_archived`. Web researcher replaces 3 commands with gather/analyze pair. Auto-unblock logic in `execute_agent_task` dispatches dependent tasks on completion.

**Tech Stack:** Django, Celery, existing Claude AI client

---

## File Structure

```
backend/
├── agents/
│   ├── models/
│   │   └── agent_task.py           (modify — add command_name, blocked_by, new status)
│   ├── tasks.py                    (modify — auto-unblock logic, dependency-aware chain creation)
│   ├── serializers/
│   │   └── agent_task_serializer.py (modify — add new fields)
│   └── blueprints/
│       └── marketing/
│           ├── leader/commands/
│           │   └── create_priority_task.py (modify — include command_name, depends_on_previous)
│           └── workforce/web_researcher/
│               ├── agent.py         (modify — split execute_task by command_name)
│               └── commands/
│                   ├── research_gather.py    (create — replaces research_trends etc.)
│                   ├── research_analyze.py   (create)
│                   ├── research_trends.py    (delete)
│                   ├── research_competitors.py (delete)
│                   ├── find_content_opportunities.py (delete)
│                   └── __init__.py  (modify — new command imports)
├── projects/
│   ├── models/
│   │   └── document.py             (modify — add doc_type, is_archived)
│   └── tasks.py                    (modify — add archive_stale_documents beat task)
├── config/
│   └── settings.py                 (modify — add archive beat schedule)
└── frontend/
    └── app/(app)/project/[id]/page.tsx (modify — awaiting_dependencies badge)
```

---

### Task 1: AgentTask model — add command_name, blocked_by, new status

**Files:**
- Modify: `backend/agents/models/agent_task.py`

- [ ] **Step 1: Add new fields and status**

Add to `AgentTask.Status` choices (after AWAITING_APPROVAL):
```python
AWAITING_DEPENDENCIES = "awaiting_dependencies", "Awaiting Dependencies"
```

Add fields after `auto_execute`:
```python
    command_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Command on the agent's blueprint this task executes. Used for auto_actions lookup.",
    )
    blocked_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dependents",
        help_text="This task can't run until the blocker completes.",
    )
```

- [ ] **Step 2: Run makemigrations and migrate**

```bash
cd backend && source venv/bin/activate && python manage.py makemigrations agents && python manage.py migrate
```

- [ ] **Step 3: Commit**

```bash
git add backend/agents/models/ backend/agents/migrations/
git commit -m "feat: AgentTask — command_name, blocked_by FK, awaiting_dependencies status"
```

---

### Task 2: Auto-unblock logic in execute_agent_task

**Files:**
- Modify: `backend/agents/tasks.py`

- [ ] **Step 1: Add unblock logic after task completion**

In `execute_agent_task`, after `task.save(update_fields=["status", "report", "completed_at", "updated_at"])` (the success path, around line 86), add:

```python
        # Unblock dependent tasks
        _unblock_dependents(task)
```

Add the helper function (before `create_next_leader_task`):

```python
def _unblock_dependents(completed_task):
    """When a task completes, unblock any tasks waiting on it."""
    from agents.models import AgentTask

    dependents = AgentTask.objects.filter(
        blocked_by=completed_task,
        status=AgentTask.Status.AWAITING_DEPENDENCIES,
    ).select_related("agent")

    for dep in dependents:
        if dep.command_name and dep.agent.is_action_enabled(dep.command_name):
            dep.status = AgentTask.Status.QUEUED
            dep.save(update_fields=["status", "updated_at"])
            execute_agent_task.delay(str(dep.id))
            logger.info("Auto-unblocked and queued task %s (command: %s)", dep.id, dep.command_name)
        else:
            dep.status = AgentTask.Status.AWAITING_APPROVAL
            dep.save(update_fields=["status", "updated_at"])
            logger.info("Unblocked task %s → awaiting approval", dep.id)
```

- [ ] **Step 2: Update create_next_leader_task to wire dependencies**

Replace the task creation loop in `create_next_leader_task` (the `if tasks:` block):

```python
        tasks_data = proposal.get("tasks", [])
        if tasks_data:
            workforce_agents = {
                a.agent_type: a
                for a in Agent.objects.filter(
                    department=agent.department,
                    is_active=True,
                    is_leader=False,
                )
            }
            previous_task = None
            created = 0
            for task_data in tasks_data:
                target_type = task_data.get("target_agent_type")
                target_agent = workforce_agents.get(target_type)
                if not target_agent:
                    logger.warning("Leader %s: no active agent of type %s", agent.name, target_type)
                    continue

                depends_on_previous = task_data.get("depends_on_previous", False)
                command_name = task_data.get("command_name", "")

                # Determine initial status
                if depends_on_previous and previous_task:
                    initial_status = AgentTask.Status.AWAITING_DEPENDENCIES
                    blocked_by = previous_task
                elif command_name and target_agent.is_action_enabled(command_name):
                    initial_status = AgentTask.Status.QUEUED
                    blocked_by = None
                else:
                    initial_status = AgentTask.Status.AWAITING_APPROVAL
                    blocked_by = None

                new_task = AgentTask.objects.create(
                    agent=target_agent,
                    created_by_agent=agent,
                    status=initial_status,
                    command_name=command_name,
                    blocked_by=blocked_by,
                    exec_summary=task_data.get("exec_summary", "Priority task"),
                    step_plan=task_data.get("step_plan", ""),
                )

                # Auto-dispatch if queued
                if initial_status == AgentTask.Status.QUEUED:
                    execute_agent_task.delay(str(new_task.id))

                previous_task = new_task
                created += 1
            logger.info("Leader %s proposed %d task(s): %s", agent.name, created, proposal.get("exec_summary", "")[:80])
            return
```

- [ ] **Step 3: Commit**

```bash
git add backend/agents/tasks.py
git commit -m "feat: auto-unblock dependent tasks on completion, dependency-aware chain creation"
```

---

### Task 3: Document model — add doc_type and is_archived

**Files:**
- Modify: `backend/projects/models/document.py`

- [ ] **Step 1: Add fields**

```python
import uuid

from django.db import models


class Document(models.Model):
    class DocType(models.TextChoices):
        GENERAL = "general", "General"
        RESEARCH = "research", "Research"
        BRANDING = "branding", "Branding"
        STRATEGY = "strategy", "Strategy"
        CAMPAIGN = "campaign", "Campaign"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, help_text="Document content in markdown")
    department = models.ForeignKey(
        "projects.Department",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(
        max_length=20,
        choices=DocType.choices,
        default=DocType.GENERAL,
        db_index=True,
    )
    is_archived = models.BooleanField(default=False)
    tags = models.ManyToManyField("projects.Tag", blank=True, related_name="documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
```

- [ ] **Step 2: Run makemigrations and migrate**

```bash
python manage.py makemigrations projects && python manage.py migrate
```

- [ ] **Step 3: Data migration — set existing research docs**

```bash
python manage.py shell -c "
from projects.models import Document
updated = Document.objects.filter(tags__name='research').update(doc_type='research')
print(f'Set {updated} docs to research type')
"
```

- [ ] **Step 4: Commit**

```bash
git add backend/projects/models/document.py backend/projects/migrations/
git commit -m "feat: Document doc_type (general/research/branding/strategy/campaign) + is_archived"
```

---

### Task 4: Update context to exclude archived docs and group by type

**Files:**
- Modify: `backend/agents/blueprints/base.py`

- [ ] **Step 1: Update get_context to filter and group**

In `BaseBlueprint.get_context()`, replace the docs query:

```python
        # Department documents — exclude archived, include type
        docs = list(
            department.documents
            .filter(is_archived=False)
            .values_list("title", "content", "doc_type", "created_at")
        )
        docs_text = ""
        for title, content, doc_type, created_at in docs:
            from django.utils import timezone
            age = (timezone.now() - created_at).days
            age_str = f", {age}d ago" if doc_type == "research" else ""
            docs_text += f"\n\n--- [{doc_type}{age_str}] {title} ---\n{content[:3000]}"
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/blueprints/base.py
git commit -m "feat: context excludes archived docs, shows doc_type and age for research"
```

---

### Task 5: Archive stale documents beat task

**Files:**
- Modify: `backend/projects/tasks.py`
- Modify: `backend/config/settings.py`

- [ ] **Step 1: Add archive task**

Add to `backend/projects/tasks.py`:

```python
@shared_task
def archive_stale_documents():
    """Daily: archive research documents older than 30 days."""
    from datetime import timedelta
    from django.utils import timezone
    from projects.models import Document

    cutoff = timezone.now() - timedelta(days=30)
    count = Document.objects.filter(
        doc_type=Document.DocType.RESEARCH,
        is_archived=False,
        created_at__lt=cutoff,
    ).update(is_archived=True)

    if count:
        logger.info("Archived %d stale research documents", count)
```

- [ ] **Step 2: Add to beat schedule in settings.py**

Add to `CELERY_BEAT_SCHEDULE`:

```python
    "archive-stale-documents": {
        "task": "projects.tasks.archive_stale_documents",
        "schedule": 86400,  # daily
    },
```

- [ ] **Step 3: Commit**

```bash
git add backend/projects/tasks.py backend/config/settings.py
git commit -m "feat: daily beat task to archive research documents older than 30 days"
```

---

### Task 6: Two-phase research — gather and analyze commands

**Files:**
- Create: `backend/agents/blueprints/marketing/workforce/web_researcher/commands/research_gather.py`
- Create: `backend/agents/blueprints/marketing/workforce/web_researcher/commands/research_analyze.py`
- Delete: `backend/agents/blueprints/marketing/workforce/web_researcher/commands/research_trends.py`
- Delete: `backend/agents/blueprints/marketing/workforce/web_researcher/commands/research_competitors.py`
- Delete: `backend/agents/blueprints/marketing/workforce/web_researcher/commands/find_content_opportunities.py`
- Modify: `backend/agents/blueprints/marketing/workforce/web_researcher/commands/__init__.py`
- Modify: `backend/agents/blueprints/marketing/workforce/web_researcher/agent.py`

- [ ] **Step 1: Create research_gather.py**

```python
"""Web researcher command: gather raw research data (cheap model)."""
from agents.blueprints.base import command


@command(
    name="research-gather",
    description="Search the web and collect raw findings on a topic",
    schedule="hourly",
    model="claude-haiku-4-5",
)
def research_gather(self, agent) -> dict:
    return {
        "exec_summary": "Search for trends and opportunities in the project's domain",
        "step_plan": "1. Search for relevant industry trends\n2. Collect raw findings with URLs\n3. Organize by relevance",
    }
```

- [ ] **Step 2: Create research_analyze.py**

```python
"""Web researcher command: analyze gathered research (expensive model)."""
from agents.blueprints.base import command


@command(
    name="research-analyze",
    description="Analyze gathered research and produce strategic recommendations",
    model="claude-sonnet-4-6",
)
def research_analyze(self, agent) -> dict:
    return {
        "exec_summary": "Analyze research findings and produce strategic recommendations",
        "step_plan": "1. Review raw findings from gather phase\n2. Connect to project goals\n3. Produce actionable recommendations with angles",
    }
```

- [ ] **Step 3: Delete old commands**

```bash
rm backend/agents/blueprints/marketing/workforce/web_researcher/commands/research_trends.py
rm backend/agents/blueprints/marketing/workforce/web_researcher/commands/research_competitors.py
rm backend/agents/blueprints/marketing/workforce/web_researcher/commands/find_content_opportunities.py
```

- [ ] **Step 4: Update commands/__init__.py**

```python
"""Web researcher commands registry."""
from .research_gather import research_gather
from .research_analyze import research_analyze

ALL_COMMANDS = [research_gather, research_analyze]
```

- [ ] **Step 5: Update agent.py — split execute_task by command_name**

Replace the `execute_task` method in `WebResearcherBlueprint`:

```python
    # Register commands
    research_gather = research_gather
    research_analyze = research_analyze

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        if task.command_name == "research-analyze":
            return self._execute_analyze(agent, task)
        return self._execute_gather(agent, task)

    def _execute_gather(self, agent: Agent, task: AgentTask) -> str:
        """Phase 1: Search and collect raw findings (Haiku)."""
        from agents.ai.claude_client import call_claude
        from integrations.websearch.service import search

        query = task.exec_summary or ""
        search_results = search(query)

        suffix = f"""Here are the web search results to organize:

<search_results>
{json.dumps(search_results, default=str, indent=2) if search_results else 'No results found.'}
</search_results>

Organize these results. Extract key facts, URLs, and relevance. Return structured JSON:
{{
    "findings": [
        {{"title": "...", "url": "...", "relevance": "high|medium|low", "summary": "...", "raw_data": "..."}}
    ]
}}"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model="claude-haiku-4-5",
            max_tokens=8192,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        # Create the analyze task as a dependent
        from agents.models import AgentTask as TaskModel
        TaskModel.objects.create(
            agent=agent,
            command_name="research-analyze",
            status=TaskModel.Status.AWAITING_DEPENDENCIES,
            blocked_by=task,
            exec_summary=f"Analyze: {task.exec_summary}",
            step_plan="Analyze the gathered research and produce strategic recommendations.",
        )
        logger.info("Created research-analyze task dependent on %s", task.id)

        return response

    def _execute_analyze(self, agent: Agent, task: AgentTask) -> str:
        """Phase 2: Deep analysis of gathered data (Sonnet). Stores results as document."""
        from agents.ai.claude_client import call_claude, parse_json_response
        from projects.models import Document, Tag

        # Read raw findings from the blocker task
        raw_findings = ""
        if task.blocked_by and task.blocked_by.report:
            raw_findings = task.blocked_by.report

        suffix = f"""Here are the raw research findings to analyze:

<raw_research>
{raw_findings or 'No raw findings available.'}
</raw_research>

Analyze these findings in the context of the project goal. Produce strategic recommendations.
Return JSON:
{{
    "findings": [
        {{"title": "...", "url": "...", "relevance": "high|medium|low", "summary": "...", "suggested_angle": "..."}}
    ],
    "report": "Executive summary of the analysis with key takeaways and recommended actions"
}}"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model="claude-sonnet-4-6",
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        report = data.get("report", response) if data else response

        # Store analysis as a research document
        department = agent.department
        findings = data.get("findings", []) if data else []
        if findings:
            doc_content = f"# Research Analysis: {task.exec_summary}\n\n"
            for f in findings:
                doc_content += f"## {f.get('title', 'Finding')}\n"
                if f.get("url"):
                    doc_content += f"**Source:** {f['url']}\n"
                if f.get("relevance"):
                    doc_content += f"**Relevance:** {f['relevance']}\n"
                doc_content += f"\n{f.get('summary', '')}\n"
                if f.get("suggested_angle"):
                    doc_content += f"\n**Suggested angle:** {f['suggested_angle']}\n"
                doc_content += "\n---\n\n"

            doc = Document.objects.create(
                title=f"Research: {task.exec_summary[:80]}",
                content=doc_content,
                department=department,
                doc_type=Document.DocType.RESEARCH,
            )
            tag, _ = Tag.objects.get_or_create(name="research")
            doc.tags.add(tag)
            logger.info("Stored research analysis as document %s", doc.id)

        return report
```

Also update the imports at the top of agent.py:

```python
from agents.blueprints.marketing.workforce.web_researcher.commands import research_gather, research_analyze
```

And remove old command imports/registrations.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: two-phase research — gather (Haiku) + analyze (Sonnet) with task dependency"
```

---

### Task 7: Update leader prompt for command_name and depends_on_previous

**Files:**
- Modify: `backend/agents/blueprints/marketing/leader/commands/create_priority_task.py`

- [ ] **Step 1: Update the prompt to include command_name**

In the JSON response schema in the prompt, add `command_name` and `depends_on_previous`:

```
Respond with JSON:
{{
    "exec_summary": "One-line description of the initiative",
    "tasks": [
        {{
            "target_agent_type": "agent type from the list above",
            "command_name": "the specific command to invoke on that agent (from the commands list)",
            "exec_summary": "What this agent should do",
            "step_plan": "Detailed step-by-step plan with branding/tone guidance",
            "depends_on_previous": false
        }}
    ]
}}

IMPORTANT: Set depends_on_previous to true if this task should wait for the previous task to complete first.
For research tasks, always create a research-gather task first, then a research-analyze task with depends_on_previous: true.
```

Also add the available commands per agent in the prompt context:

After the workforce agents list, add:
```python
    # Add available commands per agent
    for _, wname, wtype in workforce:
        bp = None
        try:
            from agents.blueprints import get_blueprint
            bp = get_blueprint(wtype, agent.department.department_type)
        except Exception:
            pass
        if bp:
            cmds = bp.get_commands()
            if cmds:
                workforce_desc += f"\n  Commands: {', '.join(c['name'] for c in cmds)}"
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/blueprints/marketing/leader/commands/create_priority_task.py
git commit -m "feat: leader prompt includes command_name and depends_on_previous in task proposals"
```

---

### Task 8: Update serializers and frontend

**Files:**
- Modify: `backend/agents/serializers/agent_task_serializer.py`
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/app/(app)/project/[id]/page.tsx`

- [ ] **Step 1: Add fields to AgentTaskSerializer**

Add `command_name`, `blocked_by`, and `blocked_by_summary` to the serializer:

```python
    blocked_by_summary = serializers.SerializerMethodField()

    class Meta:
        model = AgentTask
        fields = [
            "id", "agent", "agent_name", "agent_type",
            "created_by_agent", "created_by_agent_name",
            "status", "auto_execute", "command_name",
            "blocked_by", "blocked_by_summary",
            "exec_summary", "step_plan", "report", "error_message",
            "proposed_exec_at", "scheduled_at", "started_at", "completed_at",
            "token_usage", "created_at", "updated_at",
        ]

    def get_blocked_by_summary(self, obj):
        if obj.blocked_by:
            return obj.blocked_by.exec_summary[:100]
        return None
```

- [ ] **Step 2: Update frontend types**

Add to `AgentTask` interface:
```typescript
  command_name: string;
  blocked_by: string | null;
  blocked_by_summary: string | null;
```

- [ ] **Step 3: Update frontend TaskCard**

Add `awaiting_dependencies` to status colors:
```typescript
  awaiting_dependencies: "bg-bg-surface text-text-secondary border-border",
```

In the expanded task view, show blocker info for `awaiting_dependencies`:
```tsx
{task.status === "awaiting_dependencies" && task.blocked_by_summary && (
  <div className="flex items-center gap-2 text-xs text-text-secondary p-2 rounded-lg bg-bg-input">
    <Clock className="h-3.5 w-3.5 shrink-0" />
    <span>Waiting on: {task.blocked_by_summary}</span>
  </div>
)}
```

No approve/reject buttons on `awaiting_dependencies` tasks.

- [ ] **Step 4: Build and verify**

```bash
cd frontend && npm run build
cd ../backend && source venv/bin/activate && python manage.py check
```

- [ ] **Step 5: Commit**

```bash
git add backend/agents/serializers/ frontend/
git commit -m "feat: awaiting_dependencies status in frontend, blocker info display"
```

---

### Task 9: Verify and final commit

- [ ] **Step 1: Run all tests**

```bash
cd backend && source venv/bin/activate && python -m pytest -q
```

Fix any failures.

- [ ] **Step 2: Run Django check**

```bash
python manage.py check
```

- [ ] **Step 3: Verify Celery discovers tasks**

```bash
celery -A config worker --loglevel=info
```

Should discover: `execute_agent_task`, `create_next_leader_task`, `run_scheduled_actions`, `bootstrap_project`, `recover_stuck_proposals`, `archive_stale_documents`

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete task dependencies, document types, two-phase research"
```
