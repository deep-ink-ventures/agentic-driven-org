"""Backend Engineer command: craft implementation prompt and trigger workflow dispatch."""

from agents.blueprints.base import command


@command(
    name="implement",
    description="Build a detailed implementation prompt and trigger the claude-implement workflow for backend code",
    schedule=None,
    model="claude-sonnet-4-6",
)
def implement(self, agent) -> dict:
    return {
        "exec_summary": "Build implementation-ready prompt and trigger GitHub Actions workflow for backend implementation",
        "step_plan": (
            "1. Read the issue/task requirements and acceptance criteria\n"
            "2. Fetch relevant codebase files to understand existing patterns\n"
            "3. Check for prior context from previous work in the same area\n"
            "4. Construct a structured implementation prompt (TASK, CONTEXT, REQUIREMENTS, CONSTRAINTS, TESTS, DOD)\n"
            "5. Trigger claude-implement.yml workflow dispatch with the prompt\n"
            "6. Store the pending workflow run in internal_state for webhook tracking"
        ),
    }
