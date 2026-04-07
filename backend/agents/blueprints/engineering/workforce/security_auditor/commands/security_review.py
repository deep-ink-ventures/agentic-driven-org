"""Security Auditor command: trigger security review on a PR."""

from agents.blueprints.base import command


@command(
    name="security-review",
    description=(
        "Assesses a PR's security risk by analyzing which file paths were changed against a sensitivity map "
        "(auth/, crypto/, permissions/, middleware/, API boundaries, dependency files). Classifies risk as "
        "low/medium/high/critical and, if warranted, dispatches the claude-security-review.yml workflow. The audit "
        "covers injection attacks, broken auth, data exposure, cryptographic issues, race conditions, supply chain "
        "risks, and XSS -- while explicitly suppressing noise categories (DoS, rate limiting, generic input "
        "validation). Only findings with confidence >= 0.8 are reported."
    ),
    schedule=None,
    model="claude-opus-4-6",
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
