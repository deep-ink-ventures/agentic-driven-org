"""Authenticity Analyst command: verify prospect list from researcher clones."""

from agents.blueprints.base import command


@command(
    name="verify-prospects",
    description=(
        "Audit researcher prospect lists for fabrication. For each prospect, verify that "
        "the cited source supports the claimed identity and role. Output pass/fail per prospect."
    ),
    model="claude-sonnet-4-6",
    max_tokens=8192,
)
def verify_prospects(self, agent) -> dict:
    return {
        "exec_summary": "Verify prospect lists from researcher clones",
        "step_plan": (
            "1. Read all researcher clone outputs\n"
            "2. For each prospect: does the cited verification source support the claimed identity/role?\n"
            "3. Flag prospects with vague verification (e.g., 'LinkedIn search' vs specific URL)\n"
            "4. Flag prospects that may be outdated (left role, org shut down)\n"
            "5. Output PASS or FAIL per prospect with reasoning\n"
            "6. Do NOT re-search — audit citations only"
        ),
    }
