"""Review Engineer command: review a PR with structured criteria."""

from agents.blueprints.base import command


@command(
    name="review-pr",
    description=(
        "Reviews a PR using structured criteria (correctness, tests, security, breaking changes, pattern consistency) "
        "and posts severity-tagged comments (BLOCKER/SUGGESTION/QUESTION). Applies a judge filter that suppresses "
        "low-signal noise: style nitpicks handled by linters, theoretical concerns, and comments on unchanged code -- "
        "targeting >80% comment acceptance rate. Tracks review rounds per PR in internal_state (max 10); on re-review "
        "focuses only on new changes since last round. Escalates to the leader if the iteration cap is reached."
    ),
    schedule=None,
    model="claude-opus-4-6",
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
