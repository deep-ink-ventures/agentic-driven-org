from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from django.utils import timezone

from agents.blueprints.base import (
    EXCELLENCE_THRESHOLD,
    MAX_REVIEW_ROUNDS,
    LeaderBlueprint,
)
from agents.blueprints.engineering.leader.commands import (
    bootstrap,
    check_progress,
    plan_sprint,
)
from agents.blueprints.engineering.leader.workflows import WORKFLOW_FILES

logger = logging.getLogger(__name__)

# ── File-path routing rules ─────────────────────────────────────────────────

BACKEND_PATTERNS = ("api/", "models/", "services/", "views/", "serializers/", "tasks/", "management/")
FRONTEND_PATTERNS = ("components/", "app/", "pages/", "hooks/", "lib/", "styles/")
SECURITY_PATTERNS = ("auth/", "crypto/", "permissions/", "middleware/", "security/")
A11Y_PATTERNS = ("components/", "app/", "pages/")
BACKEND_EXTENSIONS = (".py",)
FRONTEND_EXTENSIONS = (".tsx", ".ts", ".jsx", ".js", ".css", ".scss")


class EngineeringLeaderBlueprint(LeaderBlueprint):
    name = "Engineering Leader"
    slug = "leader"
    description = "Engineering department leader — decomposes goals into implementable tasks, orchestrates specialist agents, tracks progress across repos"
    tags = ["leadership", "engineering", "orchestration", "github", "code-review"]
    skills = [
        {
            "name": "Decompose Goal",
            "description": "Break high-level goals into Epic -> Story -> Task hierarchy. Each task scoped to 4-8 hours of junior engineer work.",
        },
        {"name": "Route Task", "description": "Route tasks to specialist agents based on file paths and issue labels."},
        {
            "name": "Manage Dependencies",
            "description": "Create task chains with blocked_by relationships. Track progress in internal_state.",
        },
        {
            "name": "Manage File Locks",
            "description": "Maintain files_claimed map in internal_state. Prevents two agents from editing the same file simultaneously.",
        },
        {
            "name": "Incremental Context",
            "description": "Store and retrieve context summaries per codebase area. Avoids re-discovering patterns across stateless workflow runs.",
        },
        {
            "name": "Setup Repo",
            "description": "Push GitHub Actions workflow files and generate CLAUDE.md for target repos via GitHub API during bootstrap.",
        },
        {
            "name": "Escalate",
            "description": "After 10 review iterations or agent failure, escalate to human with full context.",
        },
    ]
    config_schema = {
        "github_repos": {
            "type": "list",
            "required": True,
            "label": "GitHub Repos",
            "description": 'Target repos — list of {"repo": "org/name", "paths": ["backend/", "frontend/"]}',
        },
        "github_token": {
            "type": "str",
            "required": True,
            "label": "GitHub Token",
            "description": "PAT with repo + workflow permissions",
        },
        "webhook_secret": {
            "type": "str",
            "required": True,
            "label": "Webhook Secret",
            "description": "Shared secret for webhook signature verification",
        },
    }

    @property
    def system_prompt(self) -> str:
        return """You are the Engineering Leader. You decompose high-level goals into
implementable tickets and orchestrate a team of specialist agents.

DECOMPOSITION PROCESS:
1. Break the goal into 2-5 epics (user-facing capabilities)
2. Each epic -> 3-8 stories with acceptance criteria
3. Each story -> 1-3 tasks, each scoped to 4-8 hours of junior engineer work
4. Map dependencies: which tasks block others? Parallelize the rest.

ROUTING RULES:
- Route by file paths and domain, not by guessing
- Check files_claimed before assigning — if conflict, queue with blocked_by
- Backend + Frontend can run in PARALLEL on independent stories
- Security Auditor + Accessibility Engineer run in PARALLEL with Review
- Test Engineer runs AFTER implementation, BEFORE review

FILE LOCKING:
- Maintain internal_state["files_claimed"] = {filepath: {task_id, agent}}
- Before routing: check for overlaps. If conflict, block new task on existing.
- On task completion: clear claimed files for that task.

ITERATION TRACKING:
- Track review iterations in internal_state["review_rounds"][pr_number]
- After 10 rounds on the same PR: stop, create a human escalation task

BOOTSTRAP:
On first run, push workflow files and CLAUDE.md to each target repo.
Create a GitHub Project board with columns: Backlog, In Progress, In Review, Done.

You don't write code directly — you create tasks for specialist agents:
- ticket_manager: creates GitHub issues with labels, acceptance criteria
- backend_engineer: implements backend code via claude-code-action
- frontend_engineer: implements frontend code via claude-code-action
- ux_designer: creates design specs before frontend implementation
- test_engineer: writes tests, checks coverage
- review_engineer: reviews PRs, consolidates all review feedback
- security_auditor: audits PRs for vulnerabilities
- design_qa: reviews frontend implementations against design specs
- accessibility_engineer: audits frontend PRs for WCAG compliance

REVIEW CHAIN (AUTOMATIC — do not manually propose reviews):
When an implementation task (backend_engineer or frontend_engineer) completes,
the system automatically triggers a review chain:
1. test_engineer + security_auditor run in PARALLEL (+ design_qa + a11y for frontend)
2. review_engineer runs AFTER all above, consolidates findings into a single report
3. If APPROVED → move to next work
4. If CHANGES_REQUESTED → fix task auto-created for the original implementer
5. After fix → review chain runs again (ping-pong until approved or max iterations)

Do NOT manually create review tasks after implementation — the system handles this.
Only create implementation tasks and the review chain triggers automatically.

Each task you create should include:
- Clear acceptance criteria
- Relevant file paths for routing and lock checking
- Reference to existing patterns in the codebase
- Dependencies on other tasks where applicable"""

    # ── Register commands ────────────────────────────────────────────────
    bootstrap = bootstrap
    plan_sprint = plan_sprint
    check_progress = check_progress

    # ── Bootstrap hook ───────────────────────────────────────────────────

    def get_bootstrap_command(self, agent: Agent) -> dict | None:
        internal_state = agent.internal_state or {}
        if internal_state.get("bootstrapped"):
            return None
        return self.bootstrap(agent)

    # ── Task execution ───────────────────────────────────────────────────

    def _get_delegation_context(self, agent):
        internal_state = agent.internal_state or {}
        files_claimed = internal_state.get("files_claimed", {})
        if files_claimed:
            locks_text = "\n".join(
                f"- {fp}: locked by {info.get('agent')} (task {info.get('task_id', '?')[:8]})"
                for fp, info in files_claimed.items()
            )
        else:
            locks_text = "No files currently locked."
        return f"# Current File Locks\n{locks_text}"

    def _get_delegation_schema_extras(self):
        return ',\n            "file_paths": ["paths/this/task/touches"]'

    def _on_subtask_created(self, agent, sub_task, dt):
        file_paths = dt.get("file_paths", [])
        if not file_paths:
            return
        conflict = self._check_file_lock_conflicts(agent, file_paths)
        if conflict:
            # Downgrade to awaiting approval if file conflict
            from agents.models import AgentTask as TaskModel

            sub_task.status = TaskModel.Status.AWAITING_APPROVAL
            sub_task.auto_execute = False
            sub_task.save(update_fields=["status", "auto_execute", "updated_at"])
        else:
            self._manage_file_locks(agent, file_paths, str(sub_task.id), sub_task.agent.agent_type, action="claim")

    # ── Task proposal (called by beat/continuous mode) ───────────────────

    # ── Implementation → Review ping-pong ──────────────────────────────

    def get_review_pairs(self):
        return [
            {
                "creator": "backend_engineer",
                "creator_fix_command": "implement",
                "reviewer": "review_engineer",
                "reviewer_command": "review-pr",
                "dimensions": ["correctness", "test_coverage", "security", "code_quality"],
            },
            {
                "creator": "frontend_engineer",
                "creator_fix_command": "implement",
                "reviewer": "review_engineer",
                "reviewer_command": "review-pr",
                "dimensions": [
                    "correctness",
                    "test_coverage",
                    "security",
                    "design_quality",
                    "accessibility",
                    "code_quality",
                ],
            },
        ]

    def generate_task_proposal(self, agent: Agent) -> dict:
        from agents.models import AgentTask

        workforce = list(
            agent.department.agents.filter(status="active", is_leader=False).values_list("id", "name", "agent_type")
        )
        if not workforce:
            return None

        # ── Check for review cycle triggers (universal from base class) ──
        review_result = self._check_review_trigger(agent)
        if review_result:
            return review_result

        # ── Standard flow: ask Claude for next task ──────────────────
        workforce_desc = ""
        for _wid, wname, wtype in workforce:
            workforce_desc += f"- {wname} ({wtype})"
            try:
                from agents.blueprints import get_blueprint

                bp = get_blueprint(wtype, agent.department.department_type)
                cmds = bp.get_commands()
                if cmds:
                    cmd_names = ", ".join(c["name"] for c in cmds)
                    workforce_desc += f"\n  Commands: {cmd_names}"
            except Exception:  # noqa: BLE001, S110
                pass
            workforce_desc += "\n"

        active_tasks = list(
            AgentTask.objects.filter(
                agent__department=agent.department,
                status__in=[
                    AgentTask.Status.PROCESSING,
                    AgentTask.Status.QUEUED,
                    AgentTask.Status.AWAITING_APPROVAL,
                    AgentTask.Status.AWAITING_DEPENDENCIES,
                    AgentTask.Status.PLANNED,
                ],
            ).values_list("exec_summary", "status", "agent__agent_type", "agent__name")
        )
        active_text = (
            "\n".join(f"- [{st}] ({at}) {es[:120]}" for es, st, at, _ in active_tasks)
            if active_tasks
            else "No active tasks."
        )

        internal_state = agent.internal_state or {}
        files_claimed = internal_state.get("files_claimed", {})
        locks_text = (
            "\n".join(f"- {fp}: {info.get('agent')}" for fp, info in files_claimed.items())
            if files_claimed
            else "No files locked."
        )

        area_contexts = internal_state.get("context", {})
        context_text = ""
        if area_contexts:
            for area, ctx in area_contexts.items():
                context_text += f"\n- {area}: {ctx.get('summary', '')[:150]}"

        has_active_work = len(active_tasks) > 0
        if has_active_work:
            return self._propose_sprint_task(agent, workforce_desc, active_text, locks_text, context_text)
        else:
            return self._propose_improvement(agent, workforce_desc, context_text)

    def _propose_review_chain(self, agent: Agent, impl_task, workforce_types: set) -> dict | None:
        """After implementation completes, trigger the full review chain.

        Flow: test + security + design_qa + a11y run in parallel →
              review_engineer consolidates and scores → leader evaluates score.
        """
        is_frontend = impl_task.agent.agent_type == "frontend_engineer"

        # Track review round and active chain key
        internal_state = agent.internal_state or {}
        review_rounds = internal_state.get("review_rounds", {})
        task_key = str(impl_task.id)
        round_num = review_rounds.get(task_key, 0) + 1
        review_rounds[task_key] = round_num
        internal_state["review_rounds"] = review_rounds
        internal_state["active_review_key"] = task_key
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

        if round_num > MAX_REVIEW_ROUNDS:
            return {
                "exec_summary": f"Escalation: {round_num} review rounds on {impl_task.exec_summary[:60]}",
                "tasks": [
                    {
                        "target_agent_type": "ticket_manager",
                        "command_name": "create-issues",
                        "exec_summary": f"Human review needed: {impl_task.exec_summary[:80]} — exceeded {MAX_REVIEW_ROUNDS} rounds",
                        "step_plan": f"Create an issue flagging that this task has gone through {round_num} review rounds without reaching quality threshold ({EXCELLENCE_THRESHOLD}/10). A human engineer needs to step in.",
                        "depends_on_previous": False,
                    }
                ],
            }

        impl_report_snippet = (impl_task.report or "")[:3000]

        # Build parallel review tasks — all feed into review_engineer
        tasks = []

        # Test engineer always runs
        if "test_engineer" in workforce_types:
            tasks.append(
                {
                    "target_agent_type": "test_engineer",
                    "command_name": "check-coverage",
                    "exec_summary": f"Test coverage check for: {impl_task.exec_summary[:80]}",
                    "step_plan": (
                        f"Review round {round_num}.\n\n"
                        f"Implementation report:\n{impl_report_snippet}\n\n"
                        "Check test coverage. Identify untested branches, edge cases, error paths. "
                        "Score your findings 1-10 (10 = excellent coverage, 1 = critical gaps)."
                    ),
                    "depends_on_previous": False,
                }
            )

        # Security auditor always runs
        if "security_auditor" in workforce_types:
            tasks.append(
                {
                    "target_agent_type": "security_auditor",
                    "command_name": "security-review",
                    "exec_summary": f"Security review for: {impl_task.exec_summary[:80]}",
                    "step_plan": (
                        f"Review round {round_num}.\n\n"
                        f"Implementation report:\n{impl_report_snippet}\n\n"
                        "Assess security implications. Check injection, auth, data exposure, XSS, supply chain. "
                        "Score your findings 1-10 (10 = no issues, 1 = critical vulnerabilities)."
                    ),
                    "depends_on_previous": False,
                }
            )

        # Design QA + accessibility always run for frontend
        if is_frontend:
            if "design_qa" in workforce_types:
                tasks.append(
                    {
                        "target_agent_type": "design_qa",
                        "command_name": "review_design",
                        "exec_summary": f"Design QA for: {impl_task.exec_summary[:80]}",
                        "step_plan": (
                            f"Review round {round_num}.\n\n"
                            f"Implementation report:\n{impl_report_snippet}\n\n"
                            "Review against design specs and Impeccable Style guidelines. "
                            "Score using Nielsen's heuristics. Test with all 5 personas. "
                            "Score your findings 1-10 (10 = production-ready design, 1 = needs full redesign)."
                        ),
                        "depends_on_previous": False,
                    }
                )
            if "accessibility_engineer" in workforce_types:
                tasks.append(
                    {
                        "target_agent_type": "accessibility_engineer",
                        "command_name": "a11y-audit",
                        "exec_summary": f"Accessibility audit for: {impl_task.exec_summary[:80]}",
                        "step_plan": (
                            f"Review round {round_num}.\n\n"
                            f"Implementation report:\n{impl_report_snippet}\n\n"
                            "Audit for WCAG 2.1 AA compliance — automated + manual checks. "
                            "Score your findings 1-10 (10 = fully accessible, 1 = blocker-level issues)."
                        ),
                        "depends_on_previous": False,
                    }
                )

        # Review engineer consolidates — depends on all above
        if "review_engineer" in workforce_types:
            tasks.append(
                {
                    "target_agent_type": "review_engineer",
                    "command_name": "review-pr",
                    "exec_summary": f"Consolidated review (round {round_num}): {impl_task.exec_summary[:60]}",
                    "step_plan": (
                        f"Review round {round_num}. Quality threshold: {EXCELLENCE_THRESHOLD}/10.\n\n"
                        f"Implementation report:\n{impl_report_snippet}\n\n"
                        "## Your job\n"
                        "1. Review the implementation yourself for correctness, patterns, and tests.\n"
                        "2. Read the reports from test_engineer, security_auditor, design_qa, and "
                        "accessibility_engineer (in recently completed department tasks).\n"
                        "3. Consolidate ALL findings into a single review report.\n\n"
                        "## Scoring (REQUIRED)\n"
                        "Score each dimension 1.0-10.0 (use decimals — 8.5, 9.0, 9.5 etc.):\n"
                        "- **Correctness**: Does it work? Edge cases handled?\n"
                        "- **Test coverage**: Are critical paths tested?\n"
                        "- **Security**: Any vulnerabilities?\n"
                        "- **Design quality**: Does it look intentional and polished? (frontend only)\n"
                        "- **Accessibility**: WCAG compliant? (frontend only)\n"
                        "- **Code quality**: Clean, maintainable, follows patterns?\n\n"
                        "Compute the **overall score** as the MINIMUM of all dimension scores.\n"
                        "An implementation is only as strong as its weakest dimension.\n"
                        "The bar is EXCELLENCE — 9.5/10 is the threshold. We don't ship 'good enough'.\n\n"
                        "## Verdict (REQUIRED)\n"
                        f"- If overall score >= {EXCELLENCE_THRESHOLD}: **APPROVED** (score: N/10)\n"
                        f"- If overall score < {EXCELLENCE_THRESHOLD}: **CHANGES_REQUESTED** (score: N/10)\n\n"
                        "For CHANGES_REQUESTED: list ONLY the issues that need fixing to reach the threshold. "
                        "Do not list nice-to-haves. Every issue must have a file path and fix suggestion.\n\n"
                        "End your report with exactly one of these lines:\n"
                        "VERDICT: APPROVED (score: N.N/10)\n"
                        "VERDICT: CHANGES_REQUESTED (score: N.N/10)"
                    ),
                    "depends_on_previous": True,
                }
            )

        return {
            "exec_summary": f"Review chain (round {round_num}) for: {impl_task.exec_summary[:80]}",
            "tasks": tasks,
        }

    def _propose_sprint_task(
        self, agent: Agent, workforce_desc: str, active_text: str, locks_text: str, context_text: str
    ) -> dict | None:
        """Propose next sprint task when there's active work to coordinate."""
        from agents.ai.claude_client import call_claude, parse_json_response

        context_msg = self.build_context_message(agent)
        msg = f"""{context_msg}

# Workforce Agents
{workforce_desc}

# Active Tasks
{active_text}

# File Locks
{locks_text}

# Prior Area Context
{context_text or "No prior context."}

# Task
Propose the single highest-value next task for this department.

Consider:
- Incomplete stories or epics from the sprint plan
- PRs needing review, security audit, or a11y audit
- Stalled work that needs unblocking
- New work from the project goal

ROUTING: Route to the correct agent type based on file paths.
FILE LOCKS: Check locks before assigning — if conflict, set depends_on_previous.
PARALLELISM: Backend + Frontend can work in parallel on independent stories.

Respond with JSON:
{{
    "exec_summary": "One-line description of the initiative",
    "tasks": [
        {{
            "target_agent_type": "agent type",
            "command_name": "specific command",
            "exec_summary": "What this agent should do",
            "step_plan": "Detailed steps with acceptance criteria",
            "file_paths": ["paths/this/task/touches"],
            "depends_on_previous": false
        }}
    ]
}}"""

        response, _usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=msg,
            model=self.get_model(agent, command_name="check-progress"),
        )

        data = parse_json_response(response)
        if not data:
            logger.warning("Failed to parse task proposal response: %s", response[:200])
            return None
        tasks = data.get("tasks", [])
        if not tasks:
            return None
        return {
            "exec_summary": data.get("exec_summary", "Engineering initiative"),
            "tasks": tasks,
        }

    def _propose_improvement(self, agent: Agent, workforce_desc: str, context_text: str) -> dict | None:
        """
        Improvement mode: all sprint work is done. Scan for quality improvements
        and propose the highest-impact one. Stop when nothing scores above threshold.
        """
        from agents.ai.claude_client import call_claude, parse_json_response
        from agents.models import AgentTask

        config = {**(agent.department.project.config or {}), **(agent.department.config or {}), **(agent.config or {})}
        min_score = float(config.get("min_improvement_score", 0.3))

        # Gather completed work summary for context
        completed_count = AgentTask.objects.filter(
            agent__department=agent.department,
            status=AgentTask.Status.DONE,
        ).count()

        recent_completed = list(
            AgentTask.objects.filter(
                agent__department=agent.department,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")[:30]
            .values_list("exec_summary", "agent__agent_type")
        )
        completed_text = (
            "\n".join(f"- ({at}) {es[:150]}" for es, at in recent_completed) if recent_completed else "None."
        )

        context_msg = self.build_context_message(agent)
        msg = f"""{context_msg}

# Mode: IMPROVEMENT
All sprint tasks are complete ({completed_count} tasks done). The initial goal has been implemented.
Now scan for quality improvements worth making.

# Workforce Agents
{workforce_desc}

# Recent Completed Work
{completed_text}

# Prior Area Context
{context_text or "No prior context."}

# Task
Score potential improvements by impact (0.0 to 1.0):

SCORING GUIDE:
- 0.9+: Critical gap (no tests for auth, security vulnerability, broken functionality)
- 0.7-0.9: High value (missing error handling, no CI, major coverage gaps)
- 0.5-0.7: Medium value (coverage below 80%, missing API docs, performance issues)
- 0.3-0.5: Low value (minor refactoring, better naming, code comments)
- <0.3: Diminishing returns (style tweaks, trivial improvements)

CATEGORIES TO SCAN:
1. Test coverage gaps — untested modules, missing edge cases, low branch coverage
2. Security hardening — full-repo sweep for OWASP vulnerabilities
3. Accessibility — pages missing a11y, WCAG violations
4. Refactoring — dead code, duplicated logic, pattern inconsistencies
5. Documentation — missing README, undocumented APIs, architecture docs
6. Dependency updates — outdated packages, known vulnerabilities

MINIMUM THRESHOLD: {min_score}
Only propose improvements scoring >= {min_score}. If nothing scores above the threshold, return empty tasks.

Respond with JSON:
{{
    "improvements_assessed": [
        {{"category": "...", "description": "...", "score": 0.0}}
    ],
    "exec_summary": "Highest-impact improvement to make next (or 'Project complete' if none above threshold)",
    "tasks": [
        {{
            "target_agent_type": "agent type",
            "command_name": "specific command",
            "exec_summary": "What this agent should do",
            "step_plan": "Detailed steps",
            "file_paths": ["paths"],
            "depends_on_previous": false,
            "improvement_score": 0.0
        }}
    ]
}}"""

        response, _usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=msg,
            model=self.get_model(agent, command_name="plan-sprint"),
        )

        data = parse_json_response(response)
        if not data:
            logger.warning("Failed to parse improvement proposal: %s", response[:200])
            return None

        # Log assessed improvements
        for imp in data.get("improvements_assessed", []):
            logger.info(
                "Improvement assessed: [%.2f] %s — %s",
                imp.get("score", 0),
                imp.get("category", "?"),
                imp.get("description", "")[:100],
            )

        tasks = data.get("tasks", [])

        # Filter by threshold
        tasks = [t for t in tasks if float(t.get("improvement_score", 0)) >= min_score]

        if not tasks:
            logger.info(
                "Improvement mode: no improvements above threshold %.2f — project complete",
                min_score,
            )
            return None

        logger.info(
            "Improvement mode: proposing %d task(s), top score %.2f",
            len(tasks),
            max(float(t.get("improvement_score", 0)) for t in tasks),
        )

        return {
            "exec_summary": data.get("exec_summary", "Quality improvement"),
            "tasks": tasks,
        }

    # ── Skills (internal methods) ────────────────────────────────────────

    def _build_engineering_context(self, agent: Agent) -> str:
        """Build the context message with engineering-specific additions."""
        return self.build_context_message(agent)

    def _decompose_goal(self, agent: Agent, context: dict) -> str:
        """Build prompt for Claude to break a goal into tasks."""
        return f"""Break down the following goal into implementable tasks:

Goal: {context.get("goal", "")}

Current state:
{context.get("current_state", "No prior work.")}

DECOMPOSITION RULES:
1. 2-5 epics (user-facing capabilities)
2. Each epic -> 3-8 stories with GIVEN/WHEN/THEN acceptance criteria
3. Each story -> 1-3 tasks, each 4-8 hours of junior engineer work
4. Map dependencies explicitly
5. Maximize parallelism — backend and frontend can work simultaneously on independent stories
"""

    def _route_task(self, file_paths: list[str], labels: list[str] | None = None) -> str:
        """Determine target agent type based on file paths and labels."""
        labels = labels or []

        has_backend = False
        has_frontend = False
        has_security = False
        has_a11y = False

        for fp in file_paths:
            fp_lower = fp.lower()
            # Check extensions
            if any(fp_lower.endswith(ext) for ext in BACKEND_EXTENSIONS) and any(
                pat in fp_lower for pat in BACKEND_PATTERNS
            ):
                has_backend = True
            if any(fp_lower.endswith(ext) for ext in FRONTEND_EXTENSIONS) and any(
                pat in fp_lower for pat in FRONTEND_PATTERNS
            ):
                has_frontend = True
            # Security patterns
            if any(pat in fp_lower for pat in SECURITY_PATTERNS):
                has_security = True
            # A11y patterns (frontend files in UI dirs)
            if any(fp_lower.endswith(ext) for ext in FRONTEND_EXTENSIONS) and any(
                pat in fp_lower for pat in A11Y_PATTERNS
            ):
                has_a11y = True

        # Check labels
        if any(label in labels for label in ("security", "auth", "crypto")):
            has_security = True  # noqa: F841
        if any(label in labels for label in ("a11y", "accessibility", "wcag")):
            has_a11y = True  # noqa: F841

        # Priority: if it's a review task, route to review_engineer
        if any(label in labels for label in ("review", "pr-review")):
            return "review_engineer"

        # If it's a test task
        if any(label in labels for label in ("test", "coverage", "testing")):
            return "test_engineer"

        # Default routing by file type
        if has_frontend and not has_backend:
            return "frontend_engineer"
        if has_backend and not has_frontend:
            return "backend_engineer"
        if has_backend and has_frontend:
            # Mixed — prefer backend for now, leader will split in decomposition
            return "backend_engineer"

        # Fallback
        return "backend_engineer"

    def _manage_file_locks(
        self,
        agent: Agent,
        task_files: list[str],
        task_id: str,
        agent_type: str = "",
        action: str = "claim",
    ) -> None:
        """Maintain files_claimed in internal_state."""
        internal_state = agent.internal_state or {}
        files_claimed = internal_state.get("files_claimed", {})

        if action == "claim":
            for fp in task_files:
                files_claimed[fp] = {
                    "task_id": task_id,
                    "agent": agent_type,
                    "claimed_at": timezone.now().isoformat(),
                }
        elif action == "release":
            for fp in list(files_claimed.keys()):
                if files_claimed[fp].get("task_id") == task_id:
                    del files_claimed[fp]

        internal_state["files_claimed"] = files_claimed
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

    def _check_file_lock_conflicts(self, agent: Agent, file_paths: list[str]) -> str | None:
        """Check if any file paths conflict with existing locks. Returns conflict description or None."""
        internal_state = agent.internal_state or {}
        files_claimed = internal_state.get("files_claimed", {})

        conflicts = []
        for fp in file_paths:
            if fp in files_claimed:
                lock = files_claimed[fp]
                conflicts.append(f"{fp} locked by {lock.get('agent')} (task {lock.get('task_id', '?')[:8]})")

        return "; ".join(conflicts) if conflicts else None

    def _get_context_for_area(self, agent: Agent, area_key: str) -> str | None:
        """Retrieve incremental context for a codebase area."""
        internal_state = agent.internal_state or {}
        contexts = internal_state.get("context", {})
        ctx = contexts.get(area_key)
        if not ctx:
            return None

        # Check staleness (7 days)
        last_updated = ctx.get("last_updated")
        if last_updated:
            from django.utils.dateparse import parse_datetime

            dt = parse_datetime(last_updated) if isinstance(last_updated, str) else last_updated
            if dt and (timezone.now() - dt).days > 7:
                # Stale — remove it
                del contexts[area_key]
                internal_state["context"] = contexts
                agent.internal_state = internal_state
                agent.save(update_fields=["internal_state"])
                return None

        return ctx.get("summary")

    def _store_context(self, agent: Agent, area_key: str, summary: str, task_id: str) -> None:
        """Store a context summary after task completion."""
        internal_state = agent.internal_state or {}
        contexts = internal_state.get("context", {})

        contexts[area_key] = {
            "summary": summary[:1000],  # Cap length
            "last_updated": timezone.now().isoformat(),
            "from_task": task_id,
        }

        internal_state["context"] = contexts
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

    def _setup_repo(self, agent: Agent, repo: str, token: str, config: dict) -> dict:
        """Push workflow files and CLAUDE.md to a single repo."""

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        default_branch = config.get("default_branch", "main")
        results = []

        # Push each workflow file
        for filename, content in WORKFLOW_FILES.items():
            path = f".github/workflows/{filename}"
            result = _push_file_to_repo(
                repo=repo,
                path=path,
                content=content,
                message=f"chore: add {filename} workflow for engineering agents",
                branch=default_branch,
                headers=headers,
            )
            results.append(f"{filename}: {result}")

        # Generate and push CLAUDE.md
        project = agent.department.project
        claude_md = self._generate_claude_md(project, config)
        claude_result = _push_file_to_repo(
            repo=repo,
            path="CLAUDE.md",
            content=claude_md,
            message="chore: add CLAUDE.md for engineering agents",
            branch=default_branch,
            headers=headers,
        )
        results.append(f"CLAUDE.md: {claude_result}")

        return {
            "repo": repo,
            "status": "done",
            "details": results,
        }

    def _generate_claude_md(self, project, config: dict) -> str:
        """Generate a CLAUDE.md describing the project for claude-code-action."""
        return f"""# {project.name}

{project.goal}

## Development Guidelines

- Follow existing patterns in the codebase
- All new code must have type hints (Python) or TypeScript types
- Write tests for new functionality
- Keep PRs focused and small
- Do not modify files outside the scope of your task

## Tech Stack

Refer to the project's package files for exact versions.

## Testing

- Run tests before committing
- Aim for >80% branch coverage on changed lines
- Use AAA pattern: Arrange, Act, Assert

## Code Style

- Follow existing linter configuration
- No hardcoded secrets or credentials
- Use environment variables for configuration
"""


def _push_file_to_repo(repo: str, path: str, content: str, message: str, branch: str, headers: dict) -> str:
    """Create or update a file in a GitHub repo via the Contents API."""
    import requests

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    # Check if file already exists (to get SHA for update)
    sha = None
    resp = requests.get(url, headers=headers, params={"ref": branch}, timeout=15)
    if resp.status_code == 200:
        sha = resp.json().get("sha")

    encoded = base64.b64encode(content.encode()).decode()
    data = {
        "message": message,
        "content": encoded,
        "branch": branch,
    }
    if sha:
        data["sha"] = sha

    resp = requests.put(url, headers=headers, json=data, timeout=15)
    if resp.status_code in (200, 201):
        return "ok" if not sha else "updated"
    else:
        logger.warning("Failed to push %s to %s: %s %s", path, repo, resp.status_code, resp.text[:300])
        return f"failed ({resp.status_code})"
