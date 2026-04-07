"""Frontend Engineer command: craft UI implementation prompt and trigger workflow dispatch."""

from agents.blueprints.base import command


@command(
    name="implement",
    description=(
        "Analyzes a UI task and crafts a structured implementation prompt for the TypeScript/React/Next.js/Tailwind "
        "CSS 4 stack. Unlike the backend engineer, every prompt mandates three additional sections: DESIGN SPEC "
        "(component patterns, design tokens, all four UI states: loading/empty/error/populated), ACCESSIBILITY "
        "(semantic HTML, ARIA labels, keyboard navigation, focus management, 4.5:1 contrast ratio), and RESPONSIVE "
        "(mobile-first breakpoints at 768px and 1024px). Enriches with prior context from internal_state and "
        "dispatches the claude-implement.yml workflow, tracking the pending run for webhook completion."
    ),
    schedule=None,
    model="claude-opus-4-6",
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
