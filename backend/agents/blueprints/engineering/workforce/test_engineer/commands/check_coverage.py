"""Test Engineer command: analyze coverage gaps and write missing tests."""

from agents.blueprints.base import command


@command(
    name="check-coverage",
    description="Analyze PR diff for coverage gaps, write missing tests, and trigger workflow dispatch",
    schedule=None,
    model="claude-sonnet-4-6",
)
def check_coverage(self, agent) -> dict:
    return {
        "exec_summary": "Analyze PR for test coverage gaps and trigger test-writing workflow",
        "step_plan": (
            "1. Read the PR diff to identify changed code paths\n"
            "2. Analyze untested branches, edge cases, and error paths\n"
            "3. Build a test generation prompt with quality rules and anti-patterns\n"
            "4. Trigger claude-implement.yml workflow to write the tests\n"
            "5. Store the pending workflow run for webhook tracking\n"
            "6. Report coverage gap analysis and expected improvements"
        ),
    }
