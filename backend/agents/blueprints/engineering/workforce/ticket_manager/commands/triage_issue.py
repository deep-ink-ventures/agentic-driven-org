"""Ticket Manager command: auto-label and triage incoming issues."""

from agents.blueprints.base import command


@command(
    name="triage-issue",
    description="Auto-label an incoming issue, check for duplicates, and prioritize",
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
