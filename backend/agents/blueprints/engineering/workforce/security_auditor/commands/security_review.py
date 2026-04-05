"""Security Auditor command: trigger security review on a PR."""

from agents.blueprints.base import command


@command(
    name="security-review",
    description="Assess PR risk level and trigger the claude-security-review workflow for security audit",
    schedule=None,
    model="claude-sonnet-4-6",
)
def security_review(self, agent) -> dict:
    return {
        "exec_summary": "Assess PR risk and trigger security audit via claude-security-review workflow",
        "step_plan": (
            "1. Read the PR diff to identify security-sensitive file paths\n"
            "2. Assess risk based on: auth, crypto, API boundaries, dependencies, user input\n"
            "3. If risk warrants review, trigger claude-security-review.yml workflow\n"
            "4. Store the pending workflow run for webhook tracking\n"
            "5. Report risk assessment and expected audit scope"
        ),
    }
