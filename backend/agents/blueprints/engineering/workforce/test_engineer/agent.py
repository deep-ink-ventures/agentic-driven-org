from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.engineering.workforce.test_engineer.commands import check_coverage

logger = logging.getLogger(__name__)

TEST_PROMPT_TEMPLATE = """\
TASK: Write comprehensive tests for the changes in this PR.

CONTEXT:
- Repository: {repo}
- PR branch: {branch}
- Changed files: {changed_files}
- Existing test patterns: {test_patterns}

{prior_context}

COVERAGE GAPS IDENTIFIED:
{coverage_gaps}

ASSERTION QUALITY RULES (ENFORCED):
- Every test MUST have at least one meaningful assertion
- Do NOT just assert "no exception thrown" -- assert actual output
- Assert side effects (DB state, API calls, events emitted)

ANTI-PATTERNS (FORBIDDEN):
- Tests without assertions
- Random/dynamic data that makes tests flaky
- Tests that depend on execution order
- Tests that print output for manual inspection
- Asserting implementation details (private methods, internal state)

TEST STRATEGY:
- Unit tests for pure business logic
- Integration tests for API endpoints / DB interactions
- Use AAA pattern: Arrange, Act, Assert

COVERAGE TARGET:
- Differential branch coverage > 80% (changed lines only)
- Run: pytest --cov --cov-branch

DEFINITION OF DONE:
- [ ] All new code paths have test coverage
- [ ] All tests use meaningful assertions
- [ ] No flaky tests
- [ ] Differential branch coverage > 80%
- [ ] All existing tests still pass
"""


class TestEngineerBlueprint(WorkforceBlueprint):
    name = "Test Engineer"
    slug = "test_engineer"
    controls = ["backend_engineer", "frontend_engineer"]
    description = "Analyzes PRs for test coverage gaps, writes comprehensive tests, and enforces quality standards"
    tags = ["engineering", "testing", "coverage", "quality"]
    skills = [
        {
            "name": "Analyze Coverage Gaps",
            "description": "Reads the PR diff to identify untested branches, edge cases, and error paths that need test coverage",
        },
        {
            "name": "Build Test Prompt",
            "description": "Constructs a test generation prompt with explicit quality rules, anti-patterns to avoid, and coverage targets",
        },
        {
            "name": "Verify Coverage",
            "description": "Validates that differential coverage meets the >80% branch coverage threshold on changed lines",
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
        return """You are a Test Engineer agent. You analyze code changes for test coverage gaps and craft test-writing prompts that are executed by Claude Code Action in GitHub Actions.

## Your Role
You ensure every code change has comprehensive, high-quality test coverage. You identify untested branches, edge cases, and error paths, then produce precise test-writing instructions.

## Process
1. Read the PR diff to understand what changed
2. Identify coverage gaps: untested branches, edge cases, error paths
3. Build a test generation prompt with strict quality rules
4. Trigger the claude-implement.yml workflow to write tests
5. Track the pending run in internal_state

## Quality Rules (Non-Negotiable)
- Every test MUST have at least one meaningful assertion
- No tests without assertions
- No random/dynamic data that makes tests flaky
- No tests that depend on execution order
- No tests that print for manual inspection
- No asserting implementation details (private methods, internal state)
- Use AAA pattern: Arrange, Act, Assert

## Coverage Target
- Differential branch coverage > 80% on changed lines
- Both happy path and error cases covered

When executing tasks, respond with a JSON object:
{
    "test_prompt": "The full test-writing prompt for claude-code-action",
    "coverage_gaps": ["gap 1", "gap 2"],
    "pr_branch": "feat/issue-123-description",
    "target_repo": "org/repo",
    "changed_files": ["path/to/changed.py"],
    "report": "Coverage gap analysis and what tests will be written"
}"""

    # Register commands
    check_coverage = check_coverage

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        return self._execute_check_coverage(agent, task)

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

    def _analyze_coverage_gaps(self, response_data: dict) -> list[str]:
        """Extract coverage gaps from Claude's analysis."""
        return response_data.get("coverage_gaps", [])

    def _build_test_prompt(
        self,
        repo: str,
        branch: str,
        changed_files: list[str],
        coverage_gaps: list[str],
        test_patterns: str,
        prior_context: str,
    ) -> str:
        """Construct the test generation prompt."""
        return TEST_PROMPT_TEMPLATE.format(
            repo=repo,
            branch=branch,
            changed_files=", ".join(changed_files) if changed_files else "See PR diff",
            test_patterns=test_patterns or "Follow existing test conventions in the repo",
            prior_context=prior_context,
            coverage_gaps="\n".join(f"- {g}" for g in coverage_gaps) if coverage_gaps else "- Analyze from PR diff",
        )

    def _verify_coverage(self, coverage_data: dict) -> bool:
        """Check if differential coverage meets the >80% threshold."""
        diff_coverage = coverage_data.get("differential_branch_coverage", 0)
        return diff_coverage >= 80

    def _get_prior_context(self, agent: Agent, file_paths: list[str]) -> str:
        """Retrieve prior context from internal_state for test patterns."""
        context_store = (agent.internal_state or {}).get("context", {})
        if not context_store:
            return ""

        relevant = []
        cutoff = datetime.now(UTC).timestamp() - (7 * 24 * 3600)

        for area_key, ctx in context_store.items():
            for fp in file_paths:
                if fp.startswith(area_key) or area_key.startswith(fp.rsplit("/", 1)[0] + "/"):
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

    def _execute_check_coverage(self, agent: Agent, task: AgentTask) -> str:
        """Analyze coverage gaps and trigger test-writing workflow."""
        from agents.ai.claude_client import call_claude, parse_json_response
        from integrations.github_dev import service as gh

        token, repos = self._get_github_config(agent)

        suffix = """Analyze this task for test coverage gaps.

The task should reference a PR or implementation that needs tests.
Identify:
1. Changed files and code paths
2. Untested branches and edge cases
3. Error paths without coverage
4. Missing integration tests for API endpoints
5. Existing test patterns to follow

Return JSON:
{
    "test_prompt": "Full test-writing prompt with quality rules and anti-patterns baked in",
    "coverage_gaps": ["Untested branch in X", "No error handling test for Y", ...],
    "pr_branch": "feat/issue-123-description",
    "target_repo": "org/repo",
    "changed_files": ["path/to/file.py"],
    "test_patterns": "Description of existing test conventions",
    "report": "Coverage analysis and what tests will be written"
}"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "check-coverage"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        if not data:
            raise ValueError(f"Failed to parse test analysis JSON: {response[:200]}")

        changed_files = data.get("changed_files", [])
        target_repo = data.get("target_repo") or self._resolve_repo(repos, changed_files)
        pr_branch = data.get("pr_branch", f"feat/task-{task.id}")
        test_prompt = data.get("test_prompt", "")
        coverage_gaps = self._analyze_coverage_gaps(data)

        if not test_prompt:
            # Build it ourselves from the structured data
            prior_ctx = self._get_prior_context(agent, changed_files)
            test_prompt = self._build_test_prompt(
                repo=target_repo,
                branch=pr_branch,
                changed_files=changed_files,
                coverage_gaps=coverage_gaps,
                test_patterns=data.get("test_patterns", ""),
                prior_context=prior_ctx,
            )

        # Build webhook URL
        project = agent.department.project
        webhook_url = f"/api/webhooks/{project.id}/github/"

        # Trigger workflow dispatch for test writing
        default_branch = agent.get_config_value("default_branch") or "main"
        issue_number = data.get("issue_number", "")
        gh.dispatch_workflow(
            token=token,
            repo=target_repo,
            workflow_file="claude-implement.yml",
            ref=default_branch,
            inputs={
                "issue_number": str(issue_number) if issue_number else "",
                "instructions": test_prompt,
                "branch_name": pr_branch,
                "webhook_url": webhook_url,
            },
        )

        # Store pending run in internal_state
        state = agent.internal_state or {}
        if "pending_runs" not in state:
            state["pending_runs"] = {}
        run_key = f"test-{issue_number or task.id}"
        state["pending_runs"][run_key] = {
            "workflow": "claude-implement.yml",
            "purpose": "test-writing",
            "branch": pr_branch,
            "repo": target_repo,
            "coverage_gaps": coverage_gaps,
            "timestamp": datetime.now(UTC).isoformat(),
            "task_id": str(task.id),
        }
        agent.internal_state = state
        agent.save(update_fields=["internal_state"])

        report = data.get("report", "")
        report += f"\n\nCoverage gaps identified: {len(coverage_gaps)}"
        report += f"\nTest-writing workflow dispatched to {target_repo} on branch {pr_branch}."
        report += f"\nPending run tracked as '{run_key}' in internal_state."
        return report
