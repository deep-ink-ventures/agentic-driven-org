from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.engineering.workforce.backend_engineer.commands import implement

logger = logging.getLogger(__name__)

IMPLEMENTATION_PROMPT_TEMPLATE = """\
TASK: {task_summary}

CONTEXT:
- Repository: {repo}
- Relevant files: {file_paths}
- Existing patterns to follow: {reference_files}
- Tech stack: Python 3.12, Django 5.x, DRF, PostgreSQL, Celery

{prior_context}

REQUIREMENTS:
{requirements}

CONSTRAINTS:
- Follow the existing pattern in {reference_files}
- Do not modify files outside the scope of this ticket
- All new code must have type hints

TESTS:
- Add tests covering happy path and error cases
- Use AAA pattern (Arrange/Act/Assert)
- Every test MUST have meaningful assertions
- Run: pytest --tb=short to verify

DEFINITION OF DONE:
- [ ] Feature works as described
- [ ] All existing tests pass
- [ ] New tests added and passing
- [ ] No linting errors (ruff check)
"""


class BackendEngineerBlueprint(WorkforceBlueprint):
    name = "Backend Engineer"
    slug = "backend_engineer"
    description = "Implements backend code by crafting detailed prompts and triggering GitHub Actions workflows"
    tags = ["engineering", "backend", "implementation", "python", "django"]
    skills = [
        {
            "name": "Build Implementation Prompt",
            "description": "Constructs a spec-grade prompt with structured TASK, CONTEXT, REQUIREMENTS, CONSTRAINTS, TESTS, and DEFINITION OF DONE sections for backend implementation",
        },
        {
            "name": "Read Codebase Context",
            "description": "Fetches relevant files via GitHub API to understand existing patterns before crafting the implementation prompt",
        },
        {
            "name": "Verify Result",
            "description": "When a webhook returns with a PR URL, reads the diff and validates it matches the original requirements",
        },
    ]
    config_schema = {
        "github_repos": {
            "type": "list",
            "required": True,
            "label": "GitHub Repos",
            "description": "Target repositories with path mappings (cascades from department)",
        },
    }

    @property
    def system_prompt(self) -> str:
        return """You are a Backend Engineer agent. You implement backend features by crafting detailed, implementation-ready prompts that are executed by Claude Code Action in GitHub Actions.

## Your Role
You are the BRAIN, not the hands. You hold context, understand the codebase patterns, and produce precise implementation instructions. GitHub Actions (claude-code-action) executes the actual code changes.

## Process
1. Read the task requirements and acceptance criteria
2. Fetch relevant codebase files to understand existing patterns
3. Construct a structured implementation prompt
4. Trigger the claude-implement.yml workflow via GitHub API
5. Track the pending run in internal_state

## Prompt Quality
Your implementation prompts must be:
- Specific: reference exact file paths and function signatures
- Scoped: limited to 4-8 hours of junior engineer work
- Pattern-aware: reference existing code patterns to follow
- Testable: include clear test requirements with AAA pattern

When executing tasks, respond with a JSON object:
{
    "implementation_prompt": "The full prompt to send to claude-code-action",
    "issue_number": 123,
    "branch_name": "feat/issue-123-description",
    "target_repo": "org/repo",
    "file_paths": ["path/to/file.py"],
    "report": "Summary of what will be implemented"
}"""

    # Register commands
    implement = implement

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        return self._execute_implement(agent, task)

    def _get_github_config(self, agent: Agent) -> tuple[str, list[dict]]:
        """Resolve GitHub token and repos from cascading config."""
        token = agent.get_config_value("github_token")
        if not token:
            raise ValueError("github_token not configured. Set it at project or department level.")
        repos = agent.get_config_value("github_repos")
        if not repos:
            raise ValueError("github_repos not configured. Set it at department level.")
        return token, repos

    def _resolve_repo(self, repos: list[dict], file_paths: list[str]) -> str:
        """Determine which repo to target based on file paths."""
        if not file_paths:
            return repos[0]["repo"]
        for repo_config in repos:
            repo_paths = repo_config.get("paths", [])
            for fp in file_paths:
                for rp in repo_paths:
                    if fp.startswith(rp):
                        return repo_config["repo"]
        return repos[0]["repo"]

    def _get_prior_context(self, agent: Agent, file_paths: list[str]) -> str:
        """Retrieve prior context from internal_state for the relevant file areas."""
        context_store = (agent.internal_state or {}).get("context", {})
        if not context_store:
            return ""

        relevant = []
        cutoff = datetime.now(UTC).timestamp() - (7 * 24 * 3600)  # 7 days

        for area_key, ctx in context_store.items():
            # Check if any file path overlaps with this context area
            for fp in file_paths:
                if fp.startswith(area_key) or area_key.startswith(fp.rsplit("/", 1)[0] + "/"):
                    # Check staleness
                    last_updated = ctx.get("last_updated", "")
                    if last_updated:
                        try:
                            ts = datetime.fromisoformat(last_updated).timestamp()
                            if ts < cutoff:
                                continue
                        except (ValueError, TypeError):
                            pass
                    relevant.append(ctx.get("summary", ""))
                    break

        if not relevant:
            return ""
        return (
            "PRIOR CONTEXT (from previous work in this area):\n"
            + "\n".join(relevant)
            + "\nUse this to avoid re-discovering patterns. If something contradicts what you see in the code, trust the code over this summary."
        )

    def _build_implementation_prompt(
        self,
        task_summary: str,
        repo: str,
        file_paths: list[str],
        reference_files: str,
        requirements: str,
        prior_context: str,
    ) -> str:
        """Construct the structured implementation prompt."""
        return IMPLEMENTATION_PROMPT_TEMPLATE.format(
            task_summary=task_summary,
            repo=repo,
            file_paths=", ".join(file_paths) if file_paths else "See task description",
            reference_files=reference_files or "N/A",
            prior_context=prior_context,
            requirements=requirements,
        )

    def _read_codebase_context(self, token: str, repo: str, file_paths: list[str]) -> str:
        """Fetch relevant file contents from GitHub to understand existing patterns."""
        import requests

        from integrations.github_dev import service as gh

        context_parts = []
        for fp in file_paths[:5]:  # Limit to 5 files to avoid token explosion
            try:
                resp = requests.get(
                    f"https://api.github.com/repos/{repo}/contents/{fp}",
                    headers=gh._headers(token),
                    timeout=30,
                )
                if resp.status_code == 200:
                    import base64

                    content = base64.b64decode(resp.json().get("content", "")).decode("utf-8", errors="replace")
                    context_parts.append(f"--- {fp} ---\n{content[:3000]}")
            except Exception as e:
                logger.warning("Failed to fetch %s from %s: %s", fp, repo, e)
        return "\n\n".join(context_parts)

    def _verify_result(self, token: str, repo: str, pr_number: int) -> dict:
        """Read a PR diff and validate it matches requirements."""
        from integrations.github_dev import service as gh

        return gh.get_pr(token, repo, pr_number)

    def _execute_implement(self, agent: Agent, task: AgentTask) -> str:
        """Build implementation prompt and trigger workflow dispatch."""
        from agents.ai.claude_client import call_claude, parse_json_response
        from integrations.github_dev import service as gh

        token, repos = self._get_github_config(agent)

        # Ask Claude to analyze the task and produce the structured prompt
        suffix = """Analyze this task and produce a structured implementation prompt for the claude-code-action.

Extract from the task:
1. The core task summary (one sentence)
2. File paths involved
3. Reference files showing patterns to follow
4. Numbered requirements from acceptance criteria

Return JSON:
{
    "implementation_prompt": "The full structured prompt (TASK, CONTEXT, REQUIREMENTS, CONSTRAINTS, TESTS, DOD)",
    "issue_number": 123,
    "branch_name": "feat/issue-123-short-description",
    "target_repo": "org/repo",
    "file_paths": ["relevant/file/paths.py"],
    "reference_files": "path/to/pattern.py",
    "report": "Summary of what will be implemented and why"
}"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "implement"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        if not data:
            raise ValueError(f"Failed to parse implementation JSON: {response[:200]}")

        file_paths = data.get("file_paths", [])
        target_repo = data.get("target_repo") or self._resolve_repo(repos, file_paths)
        issue_number = data.get("issue_number", "")
        branch_name = data.get("branch_name", f"feat/task-{task.id}")
        implementation_prompt = data.get("implementation_prompt", "")

        if not implementation_prompt:
            raise ValueError("Claude did not produce an implementation prompt")

        # Enrich with prior context
        prior_ctx = self._get_prior_context(agent, file_paths)
        if prior_ctx and prior_ctx not in implementation_prompt:
            implementation_prompt += f"\n\n{prior_ctx}"

        # Build webhook URL
        project = agent.department.project
        webhook_url = f"/api/webhooks/{project.id}/github/"

        # Trigger workflow dispatch
        default_branch = agent.get_config_value("default_branch") or "main"
        gh.dispatch_workflow(
            token=token,
            repo=target_repo,
            workflow_file="claude-implement.yml",
            ref=default_branch,
            inputs={
                "issue_number": str(issue_number),
                "instructions": implementation_prompt,
                "branch_name": branch_name,
                "webhook_url": webhook_url,
            },
        )

        # Store pending run in internal_state
        state = agent.internal_state or {}
        if "pending_runs" not in state:
            state["pending_runs"] = {}
        run_key = f"implement-{issue_number or task.id}"
        state["pending_runs"][run_key] = {
            "workflow": "claude-implement.yml",
            "issue": str(issue_number),
            "branch": branch_name,
            "repo": target_repo,
            "timestamp": datetime.now(UTC).isoformat(),
            "task_id": str(task.id),
        }
        agent.internal_state = state
        agent.save(update_fields=["internal_state"])

        report = data.get("report", "")
        report += f"\n\nWorkflow dispatched to {target_repo} on branch {branch_name}."
        report += f"\nPending run tracked as '{run_key}' in internal_state."
        return report
