"""Frontend Engineer command: craft UI implementation prompt and trigger workflow dispatch."""

from agents.blueprints.base import command


@command(
    name="implement",
    description="Build a detailed UI implementation prompt with design spec and accessibility requirements, then trigger the claude-implement workflow",
    schedule=None,
    model="claude-sonnet-4-6",
)
def implement(self, agent) -> dict:
    return {
        "exec_summary": "Build UI implementation-ready prompt and trigger GitHub Actions workflow for frontend implementation",
        "step_plan": (
            "1. Read the issue/task requirements, acceptance criteria, and design spec\n"
            "2. Fetch relevant UI component files to understand existing patterns and design tokens\n"
            "3. Check for prior context from previous work in the same area\n"
            "4. Construct a structured prompt (TASK, CONTEXT, REQUIREMENTS, DESIGN SPEC, ACCESSIBILITY, RESPONSIVE, CONSTRAINTS, TESTS, DOD)\n"
            "5. Trigger claude-implement.yml workflow dispatch with the prompt\n"
            "6. Store the pending workflow run in internal_state for webhook tracking"
        ),
    }
