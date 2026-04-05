from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.engineering.workforce.accessibility_engineer.commands import a11y_audit

logger = logging.getLogger(__name__)

WCAG_CHECKLIST = """\
PERCEIVABLE:
- All images have meaningful alt text (1.1.1)
- Color is not the only means of conveying info (1.4.1)
- Contrast >= 4.5:1 for text, 3:1 for large text (1.4.3)
- Text resizable to 200% without loss (1.4.4)
- Content reflows at 320px width (1.4.10)

OPERABLE:
- All functionality available via keyboard (2.1.1)
- No keyboard traps (2.1.2)
- Skip navigation link present (2.4.1)
- Focus order is logical (2.4.3)
- Focus visible on all interactive elements (2.4.7)
- Touch target >= 44x44 CSS pixels (2.5.5)

UNDERSTANDABLE:
- Page language declared (3.1.1)
- Form inputs have visible labels (3.3.2)
- Error messages identify field and describe error (3.3.1)

ROBUST:
- Valid HTML (4.1.1)
- ARIA roles/states/properties correct (4.1.2)
- Status messages use aria-live (4.1.3)
"""

AUTOMATED_CHECKS = """\
Run these automated tools:
1. axe-core: npx @axe-core/cli http://localhost:3000 --tags wcag2a,wcag2aa
2. Lighthouse: npx lighthouse http://localhost:3000 --only-categories=accessibility --output=json

These cover ~57% of WCAG criteria automatically.
"""

MANUAL_CHECKS = """\
The following ~43% CANNOT be automated and require manual/AI review:
- Heading hierarchy: h1 -> h2 -> h3 (no skipped levels)
- Focus management: focus moves logically after interactions (modals, route changes)
- Screen reader announcements: dynamic content updates use aria-live regions
- Keyboard trap detection: can Tab/Escape out of every interactive element
- Meaningful link text: no "click here" or "read more" without context
- Form error association: error messages programmatically linked to inputs
- Alternative text quality: alt text is descriptive, not just "image"
- Skip navigation: first focusable element is a skip-to-main link
"""


class AccessibilityEngineerBlueprint(WorkforceBlueprint):
    name = "Accessibility Engineer"
    slug = "accessibility_engineer"
    controls = "frontend_engineer"
    description = "Audits frontend PRs for WCAG 2.1 AA compliance using axe-core, Lighthouse, and manual checks"
    tags = ["engineering", "accessibility", "a11y", "wcag", "frontend"]
    skills = [
        {
            "name": "WCAG Checklist",
            "description": "Full WCAG 2.1 AA audit organized by principle: Perceivable, Operable, Understandable, Robust",
        },
        {
            "name": "axe-core Analysis",
            "description": "Triggers axe-core via workflow for automated WCAG testing (~57% automated coverage) and interprets results",
        },
        {
            "name": "Manual Checks",
            "description": "Prompts for the ~43% of WCAG checks that cannot be automated: heading hierarchy, focus management, screen reader announcements, keyboard trap detection",
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
        return f"""You are an Accessibility Engineer agent. You audit frontend PRs for WCAG 2.1 AA compliance by crafting comprehensive audit instructions that are executed by Claude Code Action in GitHub Actions.

## Your Role
You ensure every frontend change meets WCAG 2.1 AA standards. You combine automated tools (axe-core, Lighthouse) with manual review criteria to achieve comprehensive coverage.

## WCAG 2.1 AA Checklist
{WCAG_CHECKLIST}

## Automated Checks (~57% coverage)
{AUTOMATED_CHECKS}

## Manual Checks (~43% coverage)
{MANUAL_CHECKS}

## Process
1. Read the PR diff to identify changed UI components
2. Scope the WCAG checklist to relevant criteria for the changes
3. Build audit instructions combining automated + manual checks
4. Trigger the claude-a11y-audit.yml workflow
5. Track the pending run in internal_state

## Severity Levels for Findings
- BLOCKER: Prevents users from accessing content (missing alt text, keyboard trap, no focus indicator)
- MAJOR: Significantly impacts usability (poor contrast, missing labels, broken focus order)
- MINOR: Sub-optimal but content still accessible (non-ideal heading hierarchy, verbose alt text)

When executing tasks, respond with a JSON object:
{{
    "audit_instructions": "Full accessibility audit instructions for claude-code-action",
    "pr_number": 123,
    "target_repo": "org/repo",
    "wcag_criteria_in_scope": ["1.1.1", "2.1.1", "4.1.2"],
    "report": "Summary of audit scope and approach"
}}"""

    # Register commands
    a11y_audit = a11y_audit

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        return self._execute_a11y_audit(agent, task)

    def _get_github_config(self, agent: Agent) -> tuple[str, list[dict]]:
        """Resolve GitHub token and repos from cascading config."""
        token = agent.get_config_value("github_token")
        if not token:
            raise ValueError("github_token not configured. Set it at project or department level.")
        repos = agent.get_config_value("github_repos")
        if not repos:
            raise ValueError("github_repos not configured. Set it at department level.")
        return token, repos

    def _wcag_checklist(self, changed_components: list[str]) -> str:
        """Return the full WCAG checklist, noting which criteria are most relevant."""
        return WCAG_CHECKLIST

    def _axe_core_analysis(self) -> str:
        """Return axe-core audit instructions."""
        return AUTOMATED_CHECKS

    def _manual_checks(self) -> str:
        """Return manual check instructions for non-automatable criteria."""
        return MANUAL_CHECKS

    def _execute_a11y_audit(self, agent: Agent, task: AgentTask) -> str:
        """Audit a frontend PR for WCAG 2.1 AA compliance."""
        from agents.ai.claude_client import call_claude, parse_json_response
        from integrations.github_dev import service as gh

        token, repos = self._get_github_config(agent)

        # Check if a11y review is required
        require_a11y = agent.get_config_value("require_a11y_review")
        if require_a11y is False:
            return "Accessibility review is disabled for this department. Skipping."

        suffix = f"""Analyze this task and produce comprehensive accessibility audit instructions.

Extract from the task:
1. The PR number
2. The target repository
3. Changed UI components and interactive elements

Build audit instructions that combine:

## Automated Checks
{AUTOMATED_CHECKS}

## Manual Checks
{MANUAL_CHECKS}

Scope the WCAG checklist to the most relevant criteria for the changed components.

Return JSON:
{{
    "audit_instructions": "Full accessibility audit instructions combining automated + manual checks",
    "pr_number": 123,
    "target_repo": "org/repo",
    "changed_components": ["ComponentA", "ComponentB"],
    "wcag_criteria_in_scope": ["1.1.1", "2.1.1", "2.4.7", "4.1.2"],
    "report": "Summary of audit scope: which components, which WCAG criteria"
}}"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "a11y-audit"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        if not data:
            raise ValueError(f"Failed to parse a11y audit JSON: {response[:200]}")

        pr_number = data.get("pr_number")
        target_repo = data.get("target_repo") or repos[0]["repo"]
        audit_instructions = data.get("audit_instructions", "")

        if not pr_number:
            raise ValueError("No PR number found in task. Cannot audit without a PR reference.")

        if not audit_instructions:
            raise ValueError("Claude did not produce audit instructions")

        # Build webhook URL
        project = agent.department.project
        webhook_url = f"/api/webhooks/{project.id}/github/"

        # Trigger a11y audit workflow
        default_branch = agent.get_config_value("default_branch") or "main"
        gh.dispatch_workflow(
            token=token,
            repo=target_repo,
            workflow_file="claude-a11y-audit.yml",
            ref=default_branch,
            inputs={
                "pr_number": str(pr_number),
                "instructions": audit_instructions,
                "webhook_url": webhook_url,
            },
        )

        # Store pending run in internal_state
        state = agent.internal_state or {}
        if "pending_runs" not in state:
            state["pending_runs"] = {}
        run_key = f"a11y-pr-{pr_number}"
        state["pending_runs"][run_key] = {
            "workflow": "claude-a11y-audit.yml",
            "pr": str(pr_number),
            "repo": target_repo,
            "wcag_criteria": data.get("wcag_criteria_in_scope", []),
            "timestamp": datetime.now(UTC).isoformat(),
            "task_id": str(task.id),
        }
        agent.internal_state = state
        agent.save(update_fields=["internal_state"])

        report = data.get("report", "")
        wcag_criteria = data.get("wcag_criteria_in_scope", [])
        report += f"\n\nWCAG criteria in scope: {', '.join(wcag_criteria) if wcag_criteria else 'Full checklist'}"
        report += f"\nA11y audit workflow dispatched to {target_repo} for PR #{pr_number}."
        report += f"\nPending run tracked as '{run_key}' in internal_state."
        return report
