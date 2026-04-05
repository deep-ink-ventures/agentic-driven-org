from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import EXCELLENCE_THRESHOLD, WorkforceBlueprint
from agents.blueprints.engineering.workforce.review_engineer.commands import review_pr

logger = logging.getLogger(__name__)

MAX_PR_REVIEW_ROUNDS = 10  # Per-PR internal cap (distinct from the leader-level MAX_PR_REVIEW_ROUNDS)

REVIEW_CRITERIA = """\
WHAT TO CHECK:
- Correctness: Does the code do what the PR description says?
- Tests: Are new behaviors covered?
- Security: No hardcoded credentials, proper input validation
- Breaking changes: API contracts preserved
- Pattern consistency: Follows existing codebase conventions

WHAT NOT TO COMMENT ON:
- Style issues (handled by linter)
- Minor naming preferences
- Theoretical improvements not relevant to this PR
- Unchanged code

SEVERITY LEVELS:
- BLOCKER: Must fix before merge (bugs, security, breaking changes)
- SUGGESTION: Recommended but not blocking
- QUESTION: Seeking clarification
"""

SIGNAL_NOISE_RULES = """\
HIGH SIGNAL (keep):
- Bugs and logic errors
- Security vulnerabilities
- Architectural drift from established patterns
- Missing tests for new behavior
- Breaking API changes

LOW SIGNAL (suppress):
- Style nitpicks covered by linters
- "Consider renaming this variable"
- Theoretical performance concerns
- Comments on unchanged code
- Boilerplate suggestions
"""


class ReviewEngineerBlueprint(WorkforceBlueprint):
    name = "Review Engineer"
    slug = "review_engineer"
    controls = ["backend_engineer", "frontend_engineer"]
    description = "Reviews PRs with structured criteria, severity-tagged comments, and iterative re-review capability"
    tags = ["engineering", "review", "quality", "code-review"]
    skills = [
        {
            "name": "Structured Review",
            "description": "Reviews PRs against team standards with signal/noise filtering, targeting >80% comment acceptance rate",
        },
        {
            "name": "Incremental Re-review",
            "description": "On fix commits, reviews only the new diff and auto-resolves previously addressed comments",
        },
        {
            "name": "Judge Filter",
            "description": "Self-filters review output before posting: removes style nitpicks, theoretical concerns, and comments on unchanged code",
        },
    ]
    review_dimensions = ["correctness", "test_coverage", "security", "design_quality", "accessibility", "code_quality"]
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
        return f"""You are a Review Engineer agent. You review pull requests by crafting structured review instructions that are executed by Claude Code Action in GitHub Actions.

## Your Role
You produce high-signal code reviews that developers actually want to read. Your target is >80% comment acceptance rate.

## Review Process
1. Read the PR diff and description
2. Check review round count (max {MAX_PR_REVIEW_ROUNDS})
3. Apply structured review criteria
4. Self-filter output (judge filter) before posting
5. On re-review: focus only on new changes

## Review Criteria
{REVIEW_CRITERIA}

## Signal vs Noise
{SIGNAL_NOISE_RULES}

## Iteration Management
- Track review rounds per PR in internal_state["review_rounds"][pr_number]
- After {MAX_PR_REVIEW_ROUNDS} rounds on the same PR: stop reviewing, create escalation task for leader
- On re-review: review only the new diff against prior findings

When executing tasks, respond with a JSON object:
{{
    "review_instructions": "Structured review criteria for claude-code-action",
    "pr_number": 123,
    "target_repo": "org/repo",
    "is_rereview": false,
    "round_number": 1,
    "report": "Summary of review approach"
}}

## Quality Scoring (REQUIRED when consolidating reviews)
When consolidating feedback from test_engineer, security_auditor, design_qa, and accessibility_engineer:
- Score each dimension 1.0-10.0 (use decimals)
- Overall score = MINIMUM of all dimension scores
- The bar is EXCELLENCE — {EXCELLENCE_THRESHOLD}/10 is the threshold

End your consolidated report with exactly one of:
VERDICT: APPROVED (score: N.N/10)
VERDICT: CHANGES_REQUESTED (score: N.N/10)"""

    # Register commands
    review_pr = review_pr

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        return self._execute_review(agent, task)

    def _get_github_config(self, agent: Agent) -> tuple[str, list[dict]]:
        """Resolve GitHub token and repos from cascading config."""
        token = agent.get_config_value("github_token")
        if not token:
            raise ValueError("github_token not configured. Set it at project or department level.")
        repos = agent.get_config_value("github_repos")
        if not repos:
            raise ValueError("github_repos not configured. Set it at department level.")
        return token, repos

    def _get_review_round(self, agent: Agent, pr_number: str) -> int:
        """Get the current review round for a PR."""
        state = agent.internal_state or {}
        rounds = state.get("review_rounds", {})
        return rounds.get(str(pr_number), 0)

    def _increment_review_round(self, agent: Agent, pr_number: str) -> int:
        """Increment and return the review round counter for a PR."""
        state = agent.internal_state or {}
        if "review_rounds" not in state:
            state["review_rounds"] = {}
        current = state["review_rounds"].get(str(pr_number), 0)
        new_round = current + 1
        state["review_rounds"][str(pr_number)] = new_round
        agent.internal_state = state
        agent.save(update_fields=["internal_state"])
        return new_round

    def _structured_review(self, pr_data: dict, is_rereview: bool) -> str:
        """Build structured review instructions based on PR data."""
        base_criteria = REVIEW_CRITERIA
        if is_rereview:
            base_criteria += "\n\nRE-REVIEW INSTRUCTIONS:\n- Focus ONLY on new changes since last review\n- Auto-resolve previously addressed comments\n- Do not repeat prior feedback that was already fixed"
        return base_criteria

    def _incremental_rereview(self, prior_findings: list[str]) -> str:
        """Build re-review context from prior findings."""
        if not prior_findings:
            return ""
        return "PRIOR FINDINGS (check if addressed):\n" + "\n".join(f"- {f}" for f in prior_findings)

    def _judge_filter(self, review_output: str) -> str:
        """Filter instructions for the review action to self-filter."""
        return f"""{SIGNAL_NOISE_RULES}

Before posting any comment, apply these filters:
1. Would a senior engineer find this comment useful? If not, suppress it.
2. Is this about unchanged code? If yes, suppress it.
3. Is this a style/formatting issue handled by linters? If yes, suppress it.
4. Is this a theoretical concern with no practical impact? If yes, suppress it.

Only post comments that are BLOCKER, high-value SUGGESTION, or genuine QUESTION."""

    def _execute_review(self, agent: Agent, task: AgentTask) -> str:
        """Review a PR with structured criteria and signal/noise filtering."""
        from agents.ai.claude_client import call_claude, parse_json_response
        from integrations.github_dev import service as gh

        token, repos = self._get_github_config(agent)
        max_rounds = agent.get_config_value("max_review_iterations") or MAX_PR_REVIEW_ROUNDS

        suffix = """Analyze this task and produce structured review instructions for the claude-code-action.

Extract from the task:
1. The PR number to review
2. The target repository
3. Whether this is a first review or a re-review

IMPORTANT: Apply the judge filter. Your review instructions should tell the action to:
- Tag every comment with severity: BLOCKER, SUGGESTION, or QUESTION
- Suppress style nitpicks, theoretical concerns, and comments on unchanged code
- Focus on correctness, tests, security, breaking changes, and pattern consistency

Return JSON:
{
    "review_instructions": "Full structured review instructions for claude-code-action",
    "pr_number": 123,
    "target_repo": "org/repo",
    "is_rereview": false,
    "prior_findings": ["finding 1", "finding 2"],
    "report": "Summary of review approach"
}"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "review-pr"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        if not data:
            raise ValueError(f"Failed to parse review JSON: {response[:200]}")

        pr_number = data.get("pr_number")
        target_repo = data.get("target_repo") or repos[0]["repo"]
        is_rereview = data.get("is_rereview", False)
        review_instructions = data.get("review_instructions", "")

        if not pr_number:
            raise ValueError("No PR number found in task. Cannot review without a PR reference.")

        if not review_instructions:
            raise ValueError("Claude did not produce review instructions")

        # Check review round cap
        current_round = self._get_review_round(agent, str(pr_number))
        if current_round >= max_rounds:
            return (
                f"ESCALATION: PR #{pr_number} has reached {max_rounds} review rounds. "
                f"Stopping automated review. Human intervention required.\n"
                f"This PR needs manual review and resolution of recurring issues."
            )

        # Enrich with re-review context if applicable
        if is_rereview:
            prior = data.get("prior_findings", [])
            rereview_ctx = self._incremental_rereview(prior)
            if rereview_ctx:
                review_instructions += f"\n\n{rereview_ctx}"

        # Add judge filter instructions
        judge_instructions = self._judge_filter(review_instructions)
        review_instructions += f"\n\n## SELF-FILTER RULES\n{judge_instructions}"

        # Build webhook URL
        project = agent.department.project
        webhook_url = f"/api/webhooks/{project.id}/github/"

        # Trigger review workflow
        default_branch = agent.get_config_value("default_branch") or "main"
        gh.dispatch_workflow(
            token=token,
            repo=target_repo,
            workflow_file="claude-review.yml",
            ref=default_branch,
            inputs={
                "pr_number": str(pr_number),
                "review_instructions": review_instructions,
                "webhook_url": webhook_url,
            },
        )

        # Increment review round and store pending run
        new_round = self._increment_review_round(agent, str(pr_number))

        state = agent.internal_state or {}
        if "pending_runs" not in state:
            state["pending_runs"] = {}
        run_key = f"review-pr-{pr_number}-round-{new_round}"
        state["pending_runs"][run_key] = {
            "workflow": "claude-review.yml",
            "pr": str(pr_number),
            "round": new_round,
            "repo": target_repo,
            "timestamp": datetime.now(UTC).isoformat(),
            "task_id": str(task.id),
        }
        agent.internal_state = state
        agent.save(update_fields=["internal_state"])

        report = data.get("report", "")
        report += f"\n\nReview round {new_round}/{max_rounds} for PR #{pr_number}."
        report += f"\nWorkflow dispatched to {target_repo}."
        report += f"\nPending run tracked as '{run_key}' in internal_state."
        if new_round >= max_rounds:
            report += "\nWARNING: Next review will trigger escalation (round cap reached)."
        return report
