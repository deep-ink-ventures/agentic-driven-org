"""Backend Engineer command: craft implementation prompt and trigger workflow dispatch."""

from agents.blueprints.base import command


@command(
    name="implement",
    description=(
        "Analyzes a task's requirements and acceptance criteria, then crafts a structured implementation prompt "
        "targeting the Python/Django/DRF/Celery stack. The prompt follows a rigid template (TASK, CONTEXT, "
        "REQUIREMENTS, CONSTRAINTS, TESTS with AAA pattern, DEFINITION OF DONE) with exact file paths, reference "
        "patterns, and type-hint requirements. Enriches the prompt with prior context from internal_state to avoid "
        "re-discovering codebase patterns. Dispatches the claude-implement.yml GitHub Actions workflow and tracks "
        "the pending run for webhook-based completion notification."
    ),
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
