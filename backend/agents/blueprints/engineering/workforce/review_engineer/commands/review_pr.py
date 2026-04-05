"""Review Engineer command: review a PR with structured criteria."""

from agents.blueprints.base import command


@command(
    name="review-pr",
    description="Review a PR against team standards, post inline comments with severity levels, and track review rounds",
    schedule=None,
    model="claude-sonnet-4-6",
)
def review_pr(self, agent) -> dict:
    return {
        "exec_summary": "Review PR against team standards with structured criteria and severity-tagged comments",
        "step_plan": (
            "1. Read the PR diff and description\n"
            "2. Check review round count in internal_state (cap at 10)\n"
            "3. If re-review, focus only on new changes since last review\n"
            "4. Apply structured review criteria: correctness, tests, security, breaking changes, patterns\n"
            "5. Self-filter output: remove style nitpicks, theoretical concerns, comments on unchanged code\n"
            "6. Trigger claude-review.yml workflow with filtered review instructions\n"
            "7. Increment review round counter in internal_state"
        ),
    }
