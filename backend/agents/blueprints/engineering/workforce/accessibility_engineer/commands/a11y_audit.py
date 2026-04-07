"""Accessibility Engineer command: audit frontend PRs for WCAG 2.1 AA compliance."""

from agents.blueprints.base import command


@command(
    name="a11y-audit",
    description=(
        "Audits a frontend PR for WCAG 2.1 AA compliance using a two-pronged approach: automated checks via "
        "axe-core and Lighthouse (~57% of criteria covering contrast, ARIA roles, alt text) combined with "
        "AI-driven manual checks (~43% covering heading hierarchy, focus management, screen reader announcements, "
        "keyboard trap detection, meaningful link text, and skip navigation). Scopes the WCAG checklist to the "
        "specific components changed in the PR and tags findings as BLOCKER (content inaccessible), MAJOR "
        "(significantly impacts usability), or MINOR (sub-optimal but accessible)."
    ),
    schedule=None,
    model="claude-opus-4-6",
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
