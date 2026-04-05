"""Ticket Manager command: create GitHub issues from leader's story breakdown."""

from agents.blueprints.base import command


@command(
    name="create-issues",
    description="Create GitHub issues from the leader's story breakdown with labels, acceptance criteria, and dependency links",
    schedule=None,
    model="claude-sonnet-4-6",
)
def create_issues(self, agent) -> dict:
    return {
        "exec_summary": "Create structured GitHub issues from the task plan with proper labels and dependency links",
        "step_plan": (
            "1. Parse the story breakdown from the task plan\n"
            "2. Search existing issues for duplicates using title and keyword matching\n"
            "3. For each new story, structure a GitHub issue using the standard template\n"
            "4. Apply labels: type (feature/bug/chore), component, size (S/M/L), priority (P0-P3)\n"
            "5. Create issues via GitHub API and cross-reference dependencies\n"
            "6. Return summary of created issues with numbers and URLs"
        ),
    }
