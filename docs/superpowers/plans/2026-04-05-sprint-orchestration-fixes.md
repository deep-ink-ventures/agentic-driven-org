# Sprint Orchestration Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all gaps in the sprint lifecycle — failed task chain recovery, operator precedence bug, missing WebSocket broadcasts, fix-task routing, sprint auto-completion, sprint leader trigger validation, and stuck-task recovery.

**Architecture:** Seven independent fixes to the sprint orchestration pipeline. Each task targets a specific gap identified in the code review. All changes are in the backend — no frontend changes needed.

**Tech Stack:** Django, Celery, Django Channels (WebSocket), pytest

---

### Task 1: Failed tasks must unblock dependents and re-trigger the leader (C1 + M5)

**Files:**
- Modify: `backend/agents/tasks.py:151-158` (execute_agent_task exception handler)
- Modify: `backend/agents/tasks.py:208-214` (recover_stuck_tasks)
- Test: `backend/agents/tests/test_tasks.py`

When a task fails, dependents stuck in `AWAITING_DEPENDENCIES` are never transitioned, and the leader is never re-triggered. The sprint silently stalls.

- [ ] **Step 1: Write failing test for failed task cascading to dependents**

In `backend/agents/tests/test_tasks.py`, add:

```python
@pytest.mark.django_db
class TestFailedTaskCascade:
    def test_failed_task_fails_dependents(self, twitter_agent):
        """When a task fails, its dependents should also be failed."""
        parent = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Parent task",
        )
        child = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.AWAITING_DEPENDENCIES,
            blocked_by=parent,
            exec_summary="Child task",
        )

        from agents.tasks import _fail_dependents

        _fail_dependents(parent)

        child.refresh_from_db()
        assert child.status == AgentTask.Status.FAILED
        assert "upstream task failed" in child.error_message.lower()

    def test_failed_task_cascades_chain(self, twitter_agent):
        """A → B → C: if A fails, both B and C should fail."""
        a = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Task A",
        )
        b = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.AWAITING_DEPENDENCIES,
            blocked_by=a,
            exec_summary="Task B",
        )
        c = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.AWAITING_DEPENDENCIES,
            blocked_by=b,
            exec_summary="Task C",
        )

        from agents.tasks import _fail_dependents

        _fail_dependents(a)

        b.refresh_from_db()
        c.refresh_from_db()
        assert b.status == AgentTask.Status.FAILED
        assert c.status == AgentTask.Status.FAILED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest backend/agents/tests/test_tasks.py::TestFailedTaskCascade -v`
Expected: FAIL — `_fail_dependents` does not exist

- [ ] **Step 3: Implement `_fail_dependents` and wire it into `execute_agent_task` and `recover_stuck_tasks`**

In `backend/agents/tasks.py`, add this new function after `_unblock_dependents`:

```python
def _fail_dependents(failed_task):
    """When a task fails, cascade failure to all dependents recursively."""
    from agents.models import AgentTask

    dependents = AgentTask.objects.filter(
        blocked_by=failed_task,
        status=AgentTask.Status.AWAITING_DEPENDENCIES,
    ).select_related("agent", "agent__department__project", "blocked_by", "created_by_agent")

    for dep in dependents:
        dep.status = AgentTask.Status.FAILED
        dep.error_message = f"Upstream task failed: {failed_task.exec_summary[:100]}"
        dep.completed_at = timezone.now()
        dep.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        _broadcast_task(dep)
        logger.info("Cascaded failure to task %s (blocked by %s)", dep.id, failed_task.id)
        # Recurse for chain dependencies
        _fail_dependents(dep)
```

In the `execute_agent_task` exception handler (line 151-158), add after `_broadcast_task(task)`:

```python
        _fail_dependents(task)
        _trigger_next_sprint_work(task)
```

In `recover_stuck_tasks` (line 208-214), add after `_broadcast_task(task)`:

```python
        _fail_dependents(task)
        _trigger_next_sprint_work(task)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest backend/agents/tests/test_tasks.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agents/tasks.py backend/agents/tests/test_tasks.py
git commit -m "fix: cascade failure to dependent tasks and re-trigger leader on task failure"
```

---

### Task 2: Fix operator precedence bug in auto-approve logic (C2)

**Files:**
- Modify: `backend/agents/tasks.py:298`

- [ ] **Step 1: Add parentheses to fix precedence**

In `backend/agents/tasks.py`, line 298, change:

```python
elif command_name and target_agent.is_action_enabled(command_name) or target_agent.auto_approve:
```

to:

```python
elif (command_name and target_agent.is_action_enabled(command_name)) or target_agent.auto_approve:
```

- [ ] **Step 2: Run existing tests to verify no regression**

Run: `./venv/bin/python -m pytest backend/agents/tests/test_tasks.py -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add backend/agents/tasks.py
git commit -m "fix: add parentheses to clarify operator precedence in auto-approve logic"
```

---

### Task 3: Broadcast WebSocket updates on task approve/reject (I1)

**Files:**
- Modify: `backend/agents/views/agent_task_view.py:106-131`
- Test: `backend/agents/tests/test_views.py`

- [ ] **Step 1: Write failing test for approve broadcast**

In `backend/agents/tests/test_views.py`, add:

```python
@pytest.mark.django_db
class TestTaskApproveRejectBroadcast:
    @patch("agents.views.agent_task_view._broadcast_task")
    @patch("agents.tasks.execute_agent_task.delay")
    def test_approve_broadcasts(self, mock_exec, mock_broadcast, authed_client, project, department):
        leader = Agent.objects.create(
            name="Leader", agent_type="leader", department=department,
            is_leader=True, status="active",
        )
        task = AgentTask.objects.create(
            agent=leader, status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="Test task",
        )
        with patch("agents.tasks.create_next_leader_task.delay"):
            resp = authed_client.post(
                f"/api/projects/{project.id}/tasks/{task.id}/approve/",
            )
        assert resp.status_code == 200
        mock_broadcast.assert_called_once()

    @patch("agents.views.agent_task_view._broadcast_task")
    def test_reject_broadcasts(self, mock_broadcast, authed_client, project, department):
        agent = Agent.objects.create(
            name="Worker", agent_type="twitter", department=department, status="active",
        )
        task = AgentTask.objects.create(
            agent=agent, status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="Test task",
        )
        resp = authed_client.post(
            f"/api/projects/{project.id}/tasks/{task.id}/reject/",
        )
        assert resp.status_code == 200
        mock_broadcast.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest backend/agents/tests/test_views.py::TestTaskApproveRejectBroadcast -v`
Expected: FAIL — `_broadcast_task` is never called in the views

- [ ] **Step 3: Add broadcast calls to approve and reject views**

In `backend/agents/views/agent_task_view.py`, add import at top:

```python
from agents.tasks import _broadcast_task
```

In `TaskApproveView.post`, after `task.approve()` (line 106), before `task.refresh_from_db()`, add:

```python
        # Reload with relations for broadcast
        broadcast_task = AgentTask.objects.select_related(
            "agent__department__project", "blocked_by", "created_by_agent",
        ).get(id=task.id)
        _broadcast_task(broadcast_task)
```

In `TaskRejectView.post`, after the `task.save(...)` (line 131), add:

```python
        task = AgentTask.objects.select_related(
            "agent__department__project", "blocked_by", "created_by_agent",
        ).get(id=task.id)
        _broadcast_task(task)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest backend/agents/tests/test_views.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agents/views/agent_task_view.py backend/agents/tests/test_views.py
git commit -m "fix: broadcast WebSocket updates on task approve and reject"
```

---

### Task 4: Route fix tasks to the correct creative agent (I6)

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py:1078-1091`

- [ ] **Step 1: Read the review task to determine which analyst flagged issues**

The `_propose_fix_task` method receives `current_stage` and `config`. The stage tells us which creative agents are involved. When the creative_reviewer consolidates feedback and requests changes, the fix should go to the appropriate creative agent based on which analyst raised the most issues.

However, the simpler and correct approach: route fixes to ALL creative agents active in the current stage, not just `story_architect`. The `CREATIVE_MATRIX` already defines which agents work at each stage.

In `backend/agents/blueprints/writers_room/leader/agent.py`, replace the `_propose_fix_task` method's task list (lines 1078-1091):

```python
        # Route fixes to all creative agents active in this stage
        creative_agents = CREATIVE_MATRIX.get(current_stage, ["story_architect"])
        tasks = []
        for i, agent_type in enumerate(creative_agents):
            tasks.append({
                "target_agent_type": agent_type,
                "command_name": "write",
                "exec_summary": f"Fix review issues for stage '{current_stage}' (score {score}/10)",
                "step_plan": (
                    f"Current quality score: {score}/10. Target: {EXCELLENCE_THRESHOLD}/10.\n"
                    f"Review round: {round_num}. Locale: {locale}\n\n"
                    f"The creative reviewer has requested changes. Fix the issues below.\n\n"
                    f"## Review Report\n{review_snippet}\n\n"
                    f"Address every CHANGES_REQUESTED item relevant to your role. "
                    f"Focus on the weakest dimensions first."
                ),
                "depends_on_previous": i > 0,
            })

        return {
            "exec_summary": f"Fix review issues (score {score}/10, need {EXCELLENCE_THRESHOLD}){polish_msg}",
            "tasks": tasks,
        }
```

- [ ] **Step 2: Run existing tests**

Run: `./venv/bin/python -m pytest backend/agents/tests/ -v -q`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py
git commit -m "fix: route fix tasks to all creative agents in current stage, not just story_architect"
```

---

### Task 5: Auto-complete writers room sprints when target stage is reached (I8)

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py:377-380`

- [ ] **Step 1: Add sprint completion logic when target stage passes**

In `backend/agents/blueprints/writers_room/leader/agent.py`, replace lines 377-380:

```python
            logger.info("Writers Room: target stage '%s' PASSED — project complete", current_stage)
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
            return None
```

with:

```python
            logger.info("Writers Room: target stage '%s' PASSED — sprint complete", current_stage)
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])

            # Auto-complete the sprint
            from projects.models import Sprint

            running_sprint = Sprint.objects.filter(
                departments=agent.department,
                status=Sprint.Status.RUNNING,
            ).first()
            if running_sprint:
                from django.utils import timezone as tz

                running_sprint.status = Sprint.Status.DONE
                running_sprint.completion_summary = (
                    f"Target stage '{current_stage}' reached and passed review. "
                    f"Writers room completed all planned stages."
                )
                running_sprint.completed_at = tz.now()
                running_sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])

                from projects.views.sprint_view import _broadcast_sprint

                _broadcast_sprint(running_sprint, "sprint.updated")
                logger.info("Writers Room: auto-completed sprint '%s'", running_sprint.text[:60])

            return None
```

- [ ] **Step 2: Run existing tests**

Run: `./venv/bin/python -m pytest backend/agents/tests/ -v -q`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py
git commit -m "feat: auto-complete writers room sprint when target stage passes review"
```

---

### Task 6: Use validated department IDs for leader trigger on sprint create (M3)

**Files:**
- Modify: `backend/projects/views/sprint_view.py:65`

- [ ] **Step 1: Fix the leader trigger loop to use validated department IDs**

In `backend/projects/views/sprint_view.py`, line 65, change:

```python
        for dept_id in department_ids:
```

to:

```python
        for dept_id in valid_dept_ids:
```

- [ ] **Step 2: Run existing tests**

Run: `./venv/bin/python -m pytest backend/projects/tests/test_sprints.py -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add backend/projects/views/sprint_view.py
git commit -m "fix: use validated department IDs for leader trigger on sprint create"
```

---

### Task 7: Add reject broadcast for failed dependents + reject re-triggers leader (I1 continued)

**Files:**
- Modify: `backend/agents/views/agent_task_view.py:128-131`

Rejecting a task should also cascade failure to dependents and re-trigger the leader, same as a task failure.

- [ ] **Step 1: Add cascade and leader re-trigger to reject view**

In `backend/agents/views/agent_task_view.py`, in `TaskRejectView.post`, after the existing broadcast code added in Task 3, add:

```python
        from agents.tasks import _fail_dependents, _trigger_next_sprint_work

        _fail_dependents(task)
        _trigger_next_sprint_work(task)
```

- [ ] **Step 2: Run all tests**

Run: `./venv/bin/python -m pytest backend/agents/tests/ backend/projects/tests/ -v -q`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add backend/agents/views/agent_task_view.py
git commit -m "fix: cascade failure and re-trigger leader when task is rejected"
```
