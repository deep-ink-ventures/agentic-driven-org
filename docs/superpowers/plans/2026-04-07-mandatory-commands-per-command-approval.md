# Mandatory Commands + Per-Command Approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every task must have a mandatory `command_name`; auto-approval is per-command instead of per-agent.

**Architecture:** Replace `Agent.auto_approve: bool` with `Agent.enabled_commands: JSONField` mapping command slugs to booleans. Make `AgentTask.command_name` non-blank with model-level validation. Remove the leader self-task fallback. Fix scheduled commands to set `command_name`.

**Tech Stack:** Django models, DRF serializers, Next.js frontend (React), Celery tasks

---

### Task 1: Add `enabled_commands` field to Agent model

**Files:**
- Modify: `backend/agents/models/agent.py:36-72`
- Create: `backend/agents/migrations/NNNN_enabled_commands.py` (via makemigrations)
- Test: `backend/agents/tests/test_models.py`

- [ ] **Step 1: Write failing tests for the new field and updated `is_action_enabled`**

In `backend/agents/tests/test_models.py`, replace the three `test_is_action_enabled_*` tests and add new ones:

```python
def test_enabled_commands_default_empty(self, department):
    a = Agent.objects.create(name="New", agent_type="twitter", department=department)
    assert a.enabled_commands == {}

def test_is_action_enabled_true_when_command_enabled(self, department):
    a = Agent.objects.create(
        name="Test",
        agent_type="twitter",
        department=department,
        status=Agent.Status.ACTIVE,
        enabled_commands={"post_content": True},
    )
    assert a.is_action_enabled("post_content") is True

def test_is_action_enabled_false_when_command_disabled(self, department):
    a = Agent.objects.create(
        name="Test",
        agent_type="twitter",
        department=department,
        status=Agent.Status.ACTIVE,
        enabled_commands={"post_content": False},
    )
    assert a.is_action_enabled("post_content") is False

def test_is_action_enabled_false_when_command_absent(self, department):
    a = Agent.objects.create(
        name="Test",
        agent_type="twitter",
        department=department,
        status=Agent.Status.ACTIVE,
        enabled_commands={"research": True},
    )
    assert a.is_action_enabled("post_content") is False

def test_all_commands_enabled(self, department):
    a = Agent.objects.create(
        name="Test",
        agent_type="twitter",
        department=department,
        status=Agent.Status.ACTIVE,
        enabled_commands={"post_content": True, "search_trends": True},
    )
    assert a.all_commands_enabled is True

def test_all_commands_enabled_false_when_mixed(self, department):
    a = Agent.objects.create(
        name="Test",
        agent_type="twitter",
        department=department,
        status=Agent.Status.ACTIVE,
        enabled_commands={"post_content": True, "search_trends": False},
    )
    assert a.all_commands_enabled is False
```

Also update the `agent` fixture to use `enabled_commands` instead of `auto_approve`:

```python
@pytest.fixture
def agent(department):
    return Agent.objects.create(
        name="Twitter Bot",
        agent_type="twitter",
        department=department,
        is_leader=False,
        status=Agent.Status.ACTIVE,
        instructions="Be nice",
        config={"api_key": "xxx"},
        enabled_commands={"post_content": True, "place_content": True, "search_trends": True},
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest agents/tests/test_models.py -v -x`
Expected: FAIL — `enabled_commands` field does not exist.

- [ ] **Step 3: Update Agent model — add `enabled_commands`, update `is_action_enabled`, add `all_commands_enabled`, remove `auto_approve`**

In `backend/agents/models/agent.py`:

Replace:
```python
auto_approve = models.BooleanField(
    default=False,
    help_text="When true, all tasks for this agent skip approval and execute immediately.",
)
```

With:
```python
enabled_commands = models.JSONField(
    default=dict,
    blank=True,
    help_text="Per-command auto-approval: {'command_slug': True/False}. Absent commands default to False (require approval).",
)
```

Replace `is_action_enabled`:
```python
def is_action_enabled(self, command_name: str) -> bool:
    """Check if a specific command is auto-approved."""
    return bool((self.enabled_commands or {}).get(command_name, False))
```

Add `all_commands_enabled` property:
```python
@property
def all_commands_enabled(self) -> bool:
    """True when every command in enabled_commands is True and at least one exists."""
    cmds = self.enabled_commands or {}
    return bool(cmds) and all(cmds.values())
```

- [ ] **Step 4: Generate and run migration**

Run: `python manage.py makemigrations agents -n enabled_commands`

- [ ] **Step 5: Write data migration to convert `auto_approve` to `enabled_commands`**

Create a data migration after the schema migration. In the migration:

```python
from django.db import migrations


def forwards(apps, schema_editor):
    Agent = apps.get_model("agents", "Agent")
    for agent in Agent.objects.filter(auto_approve=True):
        try:
            from agents.blueprints import get_blueprint
            bp = get_blueprint(agent.agent_type, agent.department.department_type)
            cmds = bp.get_commands()
            agent.enabled_commands = {c["name"]: True for c in cmds}
            agent.save(update_fields=["enabled_commands"])
        except Exception:
            pass  # Blueprint not found — leave empty


def backwards(apps, schema_editor):
    Agent = apps.get_model("agents", "Agent")
    for agent in Agent.objects.all():
        if agent.enabled_commands and all(agent.enabled_commands.values()):
            agent.auto_approve = True
            agent.save(update_fields=["auto_approve"])


class Migration(migrations.Migration):
    dependencies = [
        ("agents", "PREVIOUS_MIGRATION"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
```

- [ ] **Step 6: Generate migration to remove `auto_approve` field**

Run: `python manage.py makemigrations agents -n remove_auto_approve`

- [ ] **Step 7: Run all migrations**

Run: `python manage.py migrate`

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest agents/tests/test_models.py -v`
Expected: All pass.

- [ ] **Step 9: Commit**

```bash
git add agents/models/agent.py agents/migrations/ agents/tests/test_models.py
git commit -m "feat: replace auto_approve with per-command enabled_commands"
```

---

### Task 2: Make `command_name` required on AgentTask

**Files:**
- Modify: `backend/agents/models/agent_task.py:38-42`
- Create: migration via makemigrations
- Test: `backend/agents/tests/test_models.py`

- [ ] **Step 1: Write failing tests for command_name validation**

In `backend/agents/tests/test_models.py`, add to `TestAgentTaskModel`:

```python
def test_command_name_required(self, agent):
    from django.core.exceptions import ValidationError

    task = AgentTask(
        agent=agent,
        status=AgentTask.Status.AWAITING_APPROVAL,
        exec_summary="No command",
        command_name="",
    )
    with pytest.raises(ValidationError, match="command_name"):
        task.full_clean()

def test_command_name_validated_against_blueprint(self, agent):
    from django.core.exceptions import ValidationError

    task = AgentTask(
        agent=agent,
        status=AgentTask.Status.AWAITING_APPROVAL,
        exec_summary="Invalid command",
        command_name="nonexistent_command",
    )
    with pytest.raises(ValidationError, match="not a valid command"):
        task.full_clean()

def test_valid_command_name_passes_validation(self, agent):
    task = AgentTask(
        agent=agent,
        status=AgentTask.Status.AWAITING_APPROVAL,
        exec_summary="Valid command",
        command_name="post_content",
    )
    task.full_clean()  # Should not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest agents/tests/test_models.py::TestAgentTaskModel -v -x`
Expected: FAIL — blank command_name is still allowed, no clean() validation exists.

- [ ] **Step 3: Update AgentTask model**

In `backend/agents/models/agent_task.py`, change `command_name`:

```python
command_name = models.CharField(
    max_length=100,
    help_text="Command on the agent's blueprint this task executes. Required.",
)
```

Add `clean()` method to `AgentTask`:

```python
def clean(self):
    from django.core.exceptions import ValidationError

    if not self.command_name:
        raise ValidationError({"command_name": "command_name is required for every task."})

    bp = self.agent.get_blueprint()
    if bp:
        valid_commands = {c["name"] for c in bp.get_commands()}
        if valid_commands and self.command_name not in valid_commands:
            raise ValidationError(
                {"command_name": f"'{self.command_name}' is not a valid command for {self.agent.agent_type}. Valid: {sorted(valid_commands)}"}
            )
```

- [ ] **Step 4: Backfill existing tasks and generate migration**

Run a quick check for blank command_names:
```bash
python manage.py shell -c "
from agents.models import AgentTask
blank = AgentTask.objects.filter(command_name='')
print(f'Tasks with blank command_name: {blank.count()}')
"
```

If any exist, backfill them before making the field non-blank:
```bash
python manage.py shell -c "
from agents.models import AgentTask
for t in AgentTask.objects.filter(command_name=''):
    bp = t.agent.get_blueprint()
    cmds = bp.get_commands() if bp else []
    if cmds:
        t.command_name = cmds[0]['name']
        t.save(update_fields=['command_name'])
        print(f'Backfilled task {t.id}: {t.command_name}')
"
```

Then generate migration:
Run: `python manage.py makemigrations agents -n command_name_required`
Run: `python manage.py migrate`

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest agents/tests/test_models.py -v`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add agents/models/agent_task.py agents/migrations/ agents/tests/test_models.py
git commit -m "feat: make command_name required on AgentTask with blueprint validation"
```

---

### Task 3: Update task creation paths in `agents/tasks.py`

**Files:**
- Modify: `backend/agents/tasks.py:57-105` (scheduled commands — add `command_name`)
- Modify: `backend/agents/tasks.py:340-425` (leader multi-task — validate command, remove self-task fallback)
- Test: `backend/agents/tests/test_tasks.py`

- [ ] **Step 1: Write failing tests**

In `backend/agents/tests/test_tasks.py`, add tests:

```python
class TestCommandNameValidation:
    """Test that task creation validates command_name."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        from accounts.models import User
        from agents.models import Agent
        from projects.models import Department, Project

        user = User.objects.create_user(email="cmd@test.com", password="pass")
        project = Project.objects.create(name="Cmd Project", owner=user)
        self.dept = Department.objects.create(project=project, department_type="marketing")
        self.leader = Agent.objects.create(
            name="Leader",
            agent_type="leader",
            department=self.dept,
            is_leader=True,
            status=Agent.Status.ACTIVE,
        )
        self.worker = Agent.objects.create(
            name="Twitter Bot",
            agent_type="twitter",
            department=self.dept,
            status=Agent.Status.ACTIVE,
            enabled_commands={"post_content": True},
        )

    @patch("agents.tasks._broadcast_task")
    def test_invalid_command_creates_failed_task(self, mock_broadcast):
        """Leader proposes a command that doesn't exist on the target agent."""
        from agents.tasks import create_next_leader_task

        proposal = {
            "tasks": [{
                "target_agent_type": "twitter",
                "command_name": "nonexistent_command",
                "exec_summary": "Bad command",
                "step_plan": "This should fail",
            }],
            "exec_summary": "Test",
        }

        with patch.object(
            self.leader.get_blueprint().__class__,
            "generate_task_proposal",
            return_value=proposal,
        ):
            create_next_leader_task(str(self.leader.id))

        from agents.models import AgentTask
        task = AgentTask.objects.filter(agent=self.worker).first()
        assert task is not None
        assert task.status == AgentTask.Status.FAILED
        assert "not a valid command" in task.error_message

    @patch("agents.tasks._broadcast_task")
    def test_empty_command_creates_failed_task(self, mock_broadcast):
        """Leader proposes a task with empty command_name."""
        from agents.tasks import create_next_leader_task

        proposal = {
            "tasks": [{
                "target_agent_type": "twitter",
                "command_name": "",
                "exec_summary": "No command",
                "step_plan": "This should fail",
            }],
            "exec_summary": "Test",
        }

        with patch.object(
            self.leader.get_blueprint().__class__,
            "generate_task_proposal",
            return_value=proposal,
        ):
            create_next_leader_task(str(self.leader.id))

        from agents.models import AgentTask
        task = AgentTask.objects.filter(agent=self.worker).first()
        assert task is not None
        assert task.status == AgentTask.Status.FAILED

    @patch("agents.tasks._broadcast_task")
    @patch("agents.tasks.execute_agent_task")
    def test_scheduled_command_sets_command_name(self, mock_exec, mock_broadcast):
        """Scheduled commands must set command_name on the task."""
        from agents.tasks import run_scheduled_actions

        self.worker.enabled_commands = {"post_content": True}
        self.worker.save(update_fields=["enabled_commands"])

        with patch.object(
            self.worker.get_blueprint().__class__,
            "get_scheduled_commands",
            return_value=[{"name": "post_content", "description": "Post content"}],
        ), patch.object(
            self.worker.get_blueprint().__class__,
            "run_command",
            return_value={"exec_summary": "Scheduled post"},
        ):
            run_scheduled_actions("hourly")

        from agents.models import AgentTask
        task = AgentTask.objects.filter(agent=self.worker).last()
        assert task is not None
        assert task.command_name == "post_content"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest agents/tests/test_tasks.py::TestCommandNameValidation -v -x`
Expected: FAIL

- [ ] **Step 3: Fix scheduled commands path — add `command_name`**

In `backend/agents/tasks.py`, `run_scheduled_actions`, update the `AgentTask.objects.create` call (around line 86):

```python
task = AgentTask.objects.create(
    agent=agent,
    status=AgentTask.Status.QUEUED,
    auto_execute=True,
    command_name=cmd_name,
    exec_summary=result.get("exec_summary", cmd["description"]),
    step_plan=result.get("step_plan", ""),
)
```

- [ ] **Step 4: Add command validation to leader multi-task path**

In `backend/agents/tasks.py`, in `create_next_leader_task`, in the multi-task loop (around line 355), after getting `command_name` and `target_agent`, add validation:

```python
command_name = task_data.get("command_name", "")
target_agent = workforce_agents.get(target_type)
if not target_agent:
    logger.warning("Leader %s: no active agent of type %s", agent.name, target_type)
    continue

# Validate command_name
bp = target_agent.get_blueprint()
valid_commands = {c["name"] for c in bp.get_commands()} if bp else set()

if not command_name or command_name not in valid_commands:
    error_msg = (
        f"Invalid command '{command_name}' for {target_type}. "
        f"Valid commands: {sorted(valid_commands)}"
    )
    logger.warning("Leader %s: %s", agent.name, error_msg)
    failed_task = AgentTask.objects.create(
        agent=target_agent,
        created_by_agent=agent,
        status=AgentTask.Status.FAILED,
        command_name=command_name or "INVALID",
        sprint_id=sprint_id,
        exec_summary=task_data.get("exec_summary", "Invalid task"),
        error_message=error_msg,
        completed_at=timezone.now(),
    )
    failed_task = AgentTask.objects.select_related(
        "agent__department__project",
        "blocked_by",
        "created_by_agent",
    ).get(id=failed_task.id)
    _broadcast_task(failed_task, "task.created")
    continue
```

- [ ] **Step 5: Remove leader self-task fallback**

In `backend/agents/tasks.py`, in `create_next_leader_task`, delete the entire fallback block (lines ~408-425):

```python
        # Fallback: single task on the leader itself
        if proposal.get("exec_summary"):
            initial_status = AgentTask.Status.QUEUED if agent.auto_approve else AgentTask.Status.AWAITING_APPROVAL
            new_task = AgentTask.objects.create(
                agent=agent,
                status=initial_status,
                auto_execute=False,
                sprint_id=sprint_id,
                exec_summary=proposal.get("exec_summary", "Leader task"),
                step_plan=proposal.get("step_plan", ""),
            )
            ...
```

Replace with nothing — if `tasks_data` is empty and there's no valid multi-task proposal, the function returns without creating any task.

- [ ] **Step 6: Update `auto_approve` references in task creation**

In `backend/agents/tasks.py`, around line 371, replace:

```python
elif (command_name and target_agent.is_action_enabled(command_name)) or target_agent.auto_approve:
```

With:

```python
elif command_name and target_agent.is_action_enabled(command_name):
```

The `auto_approve` fallback is gone — everything goes through `is_action_enabled`.

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest agents/tests/test_tasks.py -v`
Expected: All pass.

- [ ] **Step 8: Commit**

```bash
git add agents/tasks.py agents/tests/test_tasks.py
git commit -m "feat: validate command_name on task creation, remove leader self-task fallback"
```

---

### Task 4: Update serializers and API

**Files:**
- Modify: `backend/agents/serializers/agent_update_serializer.py`
- Modify: `backend/projects/serializers/project_detail_serializer.py:34-49`
- Test: `backend/agents/tests/test_serializers.py`

- [ ] **Step 1: Write failing tests**

In `backend/agents/tests/test_serializers.py`, add:

```python
@pytest.mark.django_db
class TestAgentUpdateSerializer:
    def _create_agent(self):
        from accounts.models import User
        from agents.models import Agent
        from projects.models import Department, Project

        user = User.objects.create_user(email="upd@test.com", password="pass")
        project = Project.objects.create(name="Upd Project", owner=user)
        dept = Department.objects.create(project=project, department_type="marketing")
        return Agent.objects.create(
            name="Test Agent",
            agent_type="twitter",
            department=dept,
            status="active",
        )

    def test_update_enabled_commands(self):
        from agents.serializers import AgentUpdateSerializer

        agent = self._create_agent()
        serializer = AgentUpdateSerializer(
            agent,
            data={"enabled_commands": {"post_content": True, "search_trends": False}},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        agent.refresh_from_db()
        assert agent.enabled_commands == {"post_content": True, "search_trends": False}

    def test_agent_summary_includes_enabled_commands(self):
        from projects.serializers.project_detail_serializer import AgentSummarySerializer

        agent = self._create_agent()
        agent.enabled_commands = {"post_content": True}
        agent.save(update_fields=["enabled_commands"])
        serializer = AgentSummarySerializer(agent)
        assert "enabled_commands" in serializer.data
        assert serializer.data["enabled_commands"] == {"post_content": True}

    def test_agent_summary_does_not_include_auto_approve(self):
        from projects.serializers.project_detail_serializer import AgentSummarySerializer

        agent = self._create_agent()
        serializer = AgentSummarySerializer(agent)
        assert "auto_approve" not in serializer.data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest agents/tests/test_serializers.py::TestAgentUpdateSerializer -v -x`
Expected: FAIL — `enabled_commands` not in serializer fields.

- [ ] **Step 3: Update AgentUpdateSerializer**

In `backend/agents/serializers/agent_update_serializer.py`:

```python
from rest_framework import serializers

from agents.models import Agent


class AgentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ["instructions", "config", "enabled_commands", "status"]

    def validate_config(self, value):
        agent = self.instance
        if agent:
            bp = agent.get_blueprint()
            errors = bp.validate_config(value)
            if errors:
                raise serializers.ValidationError(errors)
        return value
```

- [ ] **Step 4: Update AgentSummarySerializer**

In `backend/projects/serializers/project_detail_serializer.py`, in `AgentSummarySerializer`:

Replace `"auto_approve"` with `"enabled_commands"` in the fields list.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest agents/tests/test_serializers.py -v`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add agents/serializers/ projects/serializers/ agents/tests/test_serializers.py
git commit -m "feat: update serializers for enabled_commands, remove auto_approve"
```

---

### Task 5: Update remaining backend references to `auto_approve`

**Files:**
- Modify: `backend/agents/tasks.py` (any remaining `auto_approve` references)
- Modify: `backend/agents/admin/agent_admin.py`
- Modify: `backend/agents/admin/agent_task_admin.py`
- Modify: `backend/projects/tasks.py` (provisioning — set `enabled_commands` instead of nothing)
- Test: run full test suite

- [ ] **Step 1: Search and fix all remaining `auto_approve` references**

Run: `grep -rn "auto_approve" backend/agents/ backend/projects/`

For each hit:
- `agents/admin/agent_admin.py`: Replace `auto_approve` with `enabled_commands` in `list_display` / `list_filter`.
- `agents/admin/agent_task_admin.py`: Remove `auto_approve` if referenced.
- `agents/tasks.py`: Line ~371 was fixed in Task 3. Check for any others — the `run_scheduled_actions` comment at line 63 references `auto_approve`; update the docstring.
- `projects/tasks.py`: In `provision_single_agent`, the agent is activated. No `enabled_commands` setup is needed — all commands default to requiring approval (empty dict), which is correct for newly provisioned agents.

- [ ] **Step 2: Update `_unblock_dependents` in agents/tasks.py**

Line 218 currently has:
```python
if dep.command_name and dep.agent.is_action_enabled(dep.command_name):
```

Since `command_name` is now always non-empty, simplify to:
```python
if dep.agent.is_action_enabled(dep.command_name):
```

- [ ] **Step 3: Run full test suite**

Run: `pytest agents/ projects/ -v`
Expected: All pass. Fix any remaining references to `auto_approve` in test fixtures.

- [ ] **Step 4: Commit**

```bash
git add agents/ projects/
git commit -m "chore: remove all remaining auto_approve references"
```

---

### Task 6: Update frontend types, API client, and agent card

**Files:**
- Modify: `frontend/lib/types.ts:63`
- Modify: `frontend/lib/api.ts:174`
- Modify: `frontend/components/agent-card.tsx`
- Modify: `frontend/components/department-view.tsx:56,70-78,161`

- [ ] **Step 1: Update TypeScript types**

In `frontend/lib/types.ts`, replace `auto_approve: boolean` with:

```typescript
enabled_commands: Record<string, boolean>;
```

- [ ] **Step 2: Update API client**

In `frontend/lib/api.ts`, in the `updateAgent` function, replace `auto_approve?: boolean` with:

```typescript
enabled_commands?: Record<string, boolean>;
```

- [ ] **Step 3: Update AgentCard — "Auto" badge uses `all_commands_enabled` logic**

In `frontend/components/agent-card.tsx`:

Replace the auto-approve button (lines 60-69):

```tsx
{toggleable && onToggleAutoApprove && (
  <button
    onClick={(e) => { e.stopPropagation(); onToggleAutoApprove(); }}
    className={`flex items-center gap-1 text-[10px] transition-colors ${allEnabled ? "text-accent-violet" : "text-text-secondary/50 hover:text-accent-violet"}`}
    title={allEnabled ? "Revoke auto-approve" : "Auto-approve all"}
    disabled={toggling}
  >
    {toggling ? (
      <CheckCircle className="h-3 w-3 animate-pulse opacity-50" />
    ) : (
      <CheckCircle className="h-3 w-3" />
    )}
    <span className={toggling ? "animate-pulse opacity-50" : ""}>Auto</span>
  </button>
)}
```

Where `allEnabled` is computed from the agent's `enabled_commands`:

```tsx
const allEnabled = Object.keys(agent.enabled_commands).length > 0
  && Object.values(agent.enabled_commands).every(Boolean);
```

The `toggling` state and `onToggleAutoApprove` will need to be async-aware. Update the component to accept a `toggling?: boolean` prop.

- [ ] **Step 4: Update DepartmentView — toggle all commands on/off**

In `frontend/components/department-view.tsx`:

Update `toggleAutoApprove` (line 70) to fetch the agent's blueprint commands and set all to true/false:

```tsx
async function toggleAutoApprove(agent: AgentSummary) {
  setTogglingAgents((prev) => new Set(prev).add(agent.id));
  try {
    const allEnabled = Object.keys(agent.enabled_commands).length > 0
      && Object.values(agent.enabled_commands).every(Boolean);
    if (allEnabled) {
      // Revoke all
      await api.updateAgent(agent.id, { enabled_commands: {} });
    } else {
      // Enable all — fetch available commands from blueprint info
      const info = await api.getAgentBlueprint(agent.id);
      const allCommands: Record<string, boolean> = {};
      for (const cmd of info.commands) {
        allCommands[cmd.name] = true;
      }
      await api.updateAgent(agent.id, { enabled_commands: allCommands });
    }
    onRefresh();
  } finally {
    setTogglingAgents((prev) => {
      const next = new Set(prev);
      next.delete(agent.id);
      return next;
    });
  }
}
```

Add state: `const [togglingAgents, setTogglingAgents] = useState<Set<string>>(new Set());`

Pass `toggling={togglingAgents.has(agent.id)}` to each `AgentCard`.

Update `toggleAllAutoApprove` similarly — iterate all active agents and set all their commands.

Also update `deptAllApproved` computation (line 161):

```tsx
const deptAllApproved = activeAgents.length > 0 && activeAgents.every((a) => {
  const cmds = a.enabled_commands;
  return Object.keys(cmds).length > 0 && Object.values(cmds).every(Boolean);
});
```

- [ ] **Step 5: Check that `getAgentBlueprint` API exists or add it**

In `frontend/lib/api.ts`, verify there's an endpoint to get blueprint info. If not, add:

```typescript
getAgentBlueprint: (agentId: string) => request<BlueprintInfo>(`/api/agents/${agentId}/blueprint/`),
```

Check the backend has this endpoint. Look for an existing blueprint info endpoint in `agents/views/agent_view.py`. If it exists, use it. If not, add a `@action` on the agent viewset.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts frontend/components/agent-card.tsx frontend/components/department-view.tsx
git commit -m "feat: frontend per-command auto-approve with pulsating toggle"
```

---

### Task 7: Update AgentConfigEditor — per-command toggles

**Files:**
- Modify: `frontend/components/agent-config-editor.tsx`

- [ ] **Step 1: Replace single auto-approve toggle with per-command list**

In `frontend/components/agent-config-editor.tsx`:

Replace the auto-approve toggle section (lines 90-108) with a per-command section. The component already receives `blueprint` which has `commands`.

```tsx
{/* Per-command auto-approve */}
<div>
  <div className="flex items-center justify-between mb-3">
    <h3 className="text-xs uppercase text-text-secondary font-medium">
      Command Approval
    </h3>
    <button
      onClick={toggleAllCommands}
      disabled={saving}
      className={`text-[10px] transition-colors ${saving ? "animate-pulse opacity-50" : "hover:text-accent-violet"} ${allEnabled ? "text-accent-violet" : "text-text-secondary"}`}
    >
      {allEnabled ? "Revoke all" : "Auto-approve all"}
    </button>
  </div>
  <div className="space-y-2">
    {blueprint.commands.map((cmd: { name: string; description: string }) => (
      <div
        key={cmd.name}
        className="flex items-center justify-between p-3 rounded-lg border border-border bg-bg-surface"
      >
        <div>
          <p className="text-sm font-medium text-text-primary">{cmd.name}</p>
          <p className="text-xs text-text-secondary mt-0.5">{cmd.description}</p>
        </div>
        <button
          onClick={() => toggleCommand(cmd.name)}
          disabled={saving}
          className={`transition-colors ${saving ? "animate-pulse opacity-50" : ""} ${enabledCommands[cmd.name] ? "text-accent-violet" : "text-text-secondary hover:text-accent-violet"}`}
        >
          {enabledCommands[cmd.name] ? (
            <ToggleRight className="h-6 w-6" />
          ) : (
            <ToggleLeft className="h-6 w-6" />
          )}
        </button>
      </div>
    ))}
  </div>
</div>
```

Add state and handlers:

```tsx
const [enabledCommands, setEnabledCommands] = useState<Record<string, boolean>>(
  agent.enabled_commands || {},
);

const allEnabled = blueprint.commands.length > 0
  && blueprint.commands.every((cmd: { name: string }) => enabledCommands[cmd.name]);

function toggleCommand(name: string) {
  setEnabledCommands((prev) => ({ ...prev, [name]: !prev[name] }));
}

function toggleAllCommands() {
  const newValue = !allEnabled;
  const updated: Record<string, boolean> = {};
  for (const cmd of blueprint.commands) {
    updated[cmd.name] = newValue;
  }
  setEnabledCommands(updated);
}
```

Update `save()` to include `enabled_commands`:

```tsx
async function save() {
  setSaving(true);
  try {
    await api.updateAgent(agent.id, {
      config,
      enabled_commands: enabledCommands,
    });
    onSaved();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  } finally {
    setSaving(false);
  }
}
```

Remove the old `autoApprove` state variable entirely.

- [ ] **Step 2: Commit**

```bash
git add frontend/components/agent-config-editor.tsx
git commit -m "feat: per-command approval toggles in agent config editor"
```

---

### Task 8: Update WebSocket broadcast and remaining frontend references

**Files:**
- Modify: `frontend/lib/useProjectWebSocket.ts` (if it references `auto_approve`)
- Modify: `frontend/app/(app)/project/[...path]/page.tsx` (if it references `auto_approve`)

- [ ] **Step 1: Search and fix all remaining `auto_approve` in frontend**

Run: `grep -rn "auto_approve\|autoApprove" frontend/`

Fix each hit:
- `page.tsx`: The `agent.status` WS handler updates agent fields — make sure it doesn't reference `auto_approve`.
- Any other component that reads `agent.auto_approve` should use `enabled_commands` logic instead.

- [ ] **Step 2: Verify the WebSocket broadcast in `agents/tasks.py`**

The `_broadcast_task` function (line 10-53) doesn't include `auto_approve` — it broadcasts task data, not agent data. No change needed.

The `_broadcast_agent` function in `projects/tasks.py` only sends `agent_id`, `status`, `error_message`. No change needed.

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "chore: remove remaining auto_approve references from frontend"
```

---

### Task 9: Final integration test

**Files:**
- Test: full backend test suite
- Test: manual frontend verification

- [ ] **Step 1: Run full backend tests**

Run: `pytest agents/ projects/ -v`
Expected: All pass.

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: No TypeScript errors.

- [ ] **Step 3: Manual verification**

1. Open the app, navigate to a department
2. Verify agent cards show "Auto" badge (violet when all commands enabled)
3. Click "Auto" on an agent — should pulsate then toggle
4. Open agent detail → Config tab — verify per-command toggles appear
5. Toggle individual commands, save, verify persistence
6. Create a sprint — verify leader proposes tasks with valid command_names
7. Verify tasks with invalid commands show as FAILED

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: integration test fixes for per-command approval"
```
