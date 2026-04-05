"""Ticket Manager command: auto-label and triage incoming issues."""

from agents.blueprints.base import command


@command(
    name="triage-issue",
    description=(
        "Triages an incoming GitHub issue by classifying it across four dimensions: type (feature/bug/chore), "
        "component (api/frontend/auth/data/infra), size (S/M/L estimated effort), and priority (P0 critical "
        "through P3 backlog). Searches existing open issues for duplicates or related work, posts a triage "
        "assessment comment, and applies the computed labels via the GitHub API. Uses Haiku for cost-efficient "
        "classification since triage does not require deep code analysis."
    ),
    schedule=None,
    model="claude-haiku-4-5",
)
def triage_issue(self, agent) -> dict:
    return {
        "exec_summary": "Triage an incoming GitHub issue: auto-label, check duplicates, and assign priority",
        "step_plan": (
            "1. Read the incoming issue content\n"
            "2. Search for duplicate or closely related existing issues\n"
            "3. Classify: type (feature/bug/chore), component, size, priority\n"
            "4. Apply labels via GitHub API\n"
            "5. Add a triage comment noting duplicates or related issues if found"
        ),
    }
