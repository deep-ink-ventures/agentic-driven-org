"""Accessibility Engineer command: audit frontend PRs for WCAG 2.1 AA compliance."""

from agents.blueprints.base import command


@command(
    name="a11y-audit",
    description="Audit a frontend PR for WCAG 2.1 AA compliance using axe-core and manual checks",
    schedule=None,
    model="claude-sonnet-4-6",
)
def a11y_audit(self, agent) -> dict:
    return {
        "exec_summary": "Audit frontend PR for WCAG 2.1 AA compliance via claude-a11y-audit workflow",
        "step_plan": (
            "1. Read the PR diff to identify UI components and interactive elements\n"
            "2. Build WCAG 2.1 AA checklist scoped to the changed components\n"
            "3. Prepare axe-core and Lighthouse audit instructions\n"
            "4. Prepare manual check instructions for non-automatable criteria\n"
            "5. Trigger claude-a11y-audit.yml workflow with combined instructions\n"
            "6. Store the pending workflow run for webhook tracking"
        ),
    }
