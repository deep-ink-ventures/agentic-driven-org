"""Test Engineer command: analyze coverage gaps and write missing tests."""

from agents.blueprints.base import command


@command(
    name="check-coverage",
    description=(
        "Reads a PR diff to identify untested branches, edge cases, and error paths, then crafts a test-generation "
        "prompt enforcing strict quality rules: every test must have meaningful assertions (no assert-no-exception), "
        "use the AAA pattern (Arrange/Act/Assert), and avoid anti-patterns like flaky random data, order-dependent "
        "tests, or asserting implementation details. Targets >80% differential branch coverage on changed lines. "
        "Dispatches the claude-implement.yml workflow to write the tests and stores coverage gap metadata in "
        "internal_state for the leader to track."
    ),
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
