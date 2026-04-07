"""Leader command: decompose project goal into epics, stories, and tasks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(
    name="plan-sprint",
    description=(
        "Daily planning command that decomposes the project goal into a hierarchical sprint plan: 2-5 epics "
        "(user-facing capabilities) each containing 3-8 stories with GIVEN/WHEN/THEN acceptance criteria, "
        "each story containing 1-3 tasks scoped to 4-8 hours of junior engineer work. Routes each task to the "
        "correct specialist agent by file-path analysis (.py -> backend_engineer, .tsx -> frontend_engineer, "
        "test tasks -> test_engineer, auth/crypto -> security_auditor, UI components -> accessibility_engineer). "
        "Checks file locks before assignment, maps dependencies for sequential execution, and maximizes "
        "parallelism between backend and frontend work streams."
    ),
    schedule="daily",
    model="claude-opus-4-6",
)
def plan_sprint(self, agent: Agent) -> dict:
    from agents.ai.claude_client import call_claude, parse_json_response
    from agents.models import AgentTask

    context = self._build_engineering_context(agent)

    # Gather current GitHub issues/PR status for each repo
    department = agent.department
    project = department.project
    config = {**project.config, **department.config, **agent.config}
    github_token = config.get("github_token", "")
    github_repos = config.get("github_repos", [])

    github_status = ""
    if github_token and github_repos:
        github_status = _fetch_github_status(github_token, github_repos)

    # Get completed tasks for context
    completed = list(
        AgentTask.objects.filter(
            agent__department=department,
            status=AgentTask.Status.COMPLETED,
        )
        .order_by("-completed_at")[:20]
        .values_list("exec_summary", "report")
    )
    completed_text = "\n".join(f"- {es}" for es, _ in completed) if completed else "No completed tasks yet."

    # Get in-progress / queued tasks
    active = list(
        AgentTask.objects.filter(
            agent__department=department,
            status__in=[AgentTask.Status.PROCESSING, AgentTask.Status.QUEUED, AgentTask.Status.PROCESSING],
        ).values_list("exec_summary", "status", "agent__agent_type")
    )
    active_text = "\n".join(f"- [{st}] ({at}) {es}" for es, st, at in active) if active else "No active tasks."

    # Incremental context
    internal_state = agent.internal_state or {}
    area_contexts = internal_state.get("context", {})
    context_text = ""
    if area_contexts:
        for area, ctx in area_contexts.items():
            context_text += f"\n- {area}: {ctx.get('summary', '')[:200]}"

    msg = f"""{context}

# GitHub Status
{github_status or "No GitHub status available — repos may not be configured yet."}

# Completed Tasks
{completed_text}

# Active Tasks
{active_text}

# Prior Area Context
{context_text or "No prior context."}

# Task
Analyze the project goal and current state. Decompose remaining work into a sprint plan.

DECOMPOSITION PROCESS:
1. Break the goal into 2-5 epics (user-facing capabilities)
2. Each epic -> 3-8 stories with acceptance criteria
3. Each story -> 1-3 tasks, each scoped to 4-8 hours of junior engineer work
4. Map dependencies: which tasks block others? Parallelize the rest.

For each task, specify the target_agent_type based on file paths:
- .py files in api/, models/, services/, views/ -> backend_engineer
- .tsx, .css files in components/, app/, pages/ -> frontend_engineer
- Test tasks -> test_engineer
- PR review -> review_engineer
- Auth/crypto/API boundary changes -> security_auditor
- UI component changes -> accessibility_engineer
- Issue creation -> ticket_manager

Respond with JSON:
{{
    "sprint_summary": "Brief description of what this sprint covers",
    "epics": [
        {{
            "name": "Epic name",
            "stories": [
                {{
                    "name": "Story name",
                    "acceptance_criteria": "GIVEN/WHEN/THEN",
                    "tasks": [
                        {{
                            "target_agent_type": "ticket_manager|backend_engineer|frontend_engineer|test_engineer|review_engineer|security_auditor|accessibility_engineer",
                            "exec_summary": "What to do",
                            "step_plan": "Detailed steps",
                            "file_paths": ["paths/this/task/touches"],
                            "depends_on_previous": false
                        }}
                    ]
                }}
            ]
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
        logger.warning("Failed to parse plan-sprint response: %s", response[:300])
        return None

    # Flatten epics -> stories -> tasks into a flat task list with metadata
    tasks = []
    for epic in data.get("epics", []):
        epic_name = epic.get("name", "")
        for story in epic.get("stories", []):
            story_name = story.get("name", "")
            for task in story.get("tasks", []):
                task["epic"] = epic_name
                task["story"] = story_name
                # Check file locks before including
                file_paths = task.get("file_paths", [])
                conflict = self._check_file_lock_conflicts(agent, file_paths)
                if conflict:
                    task["blocked_by_file_lock"] = conflict
                tasks.append(task)

    return {
        "exec_summary": data.get("sprint_summary", "Sprint plan"),
        "tasks": tasks,
    }


def _fetch_github_status(token: str, repos: list) -> str:
    """Fetch open issues and PRs from all configured repos."""

    lines = []
    for repo_config in repos:
        repo = repo_config if isinstance(repo_config, str) else repo_config.get("repo", "")
        if not repo:
            continue
        try:
            # Use raw requests since the service doesn't have list_issues yet
            import requests

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            # Open issues
            resp = requests.get(
                f"https://api.github.com/repos/{repo}/issues",
                headers=headers,
                params={"state": "open", "per_page": 20},
                timeout=30,
            )
            if resp.status_code == 200:
                issues = resp.json()
                issue_lines = []
                pr_lines = []
                for issue in issues:
                    labels = ", ".join(lbl["name"] for lbl in issue.get("labels", []))
                    title = issue["title"][:100]
                    if issue.get("pull_request"):
                        pr_lines.append(f"  PR #{issue['number']}: {title} [{labels}]")
                    else:
                        issue_lines.append(f"  Issue #{issue['number']}: {title} [{labels}]")

                lines.append(f"\n## {repo}")
                if issue_lines:
                    lines.append(f"Open issues ({len(issue_lines)}):")
                    lines.extend(issue_lines[:10])
                if pr_lines:
                    lines.append(f"Open PRs ({len(pr_lines)}):")
                    lines.extend(pr_lines[:10])
                if not issue_lines and not pr_lines:
                    lines.append("No open issues or PRs.")
        except Exception as e:
            lines.append(f"\n## {repo}\nError fetching status: {e}")

    return "\n".join(lines) if lines else "Could not fetch GitHub status."
