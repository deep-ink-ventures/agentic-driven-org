"""Problem Solver leader command: decompose problem into first principles."""

from agents.blueprints.base import command


@command(
    name="decompose-problem",
    description=(
        "Break a problem into its fundamental building blocks using first-principles thinking. "
        "Identify actors, dynamics, and variants. Define a falsifiable definition of done. "
        "Reject problems that cannot have a clear DoD."
    ),
    model="claude-opus-4-6",
    max_tokens=8000,
)
def decompose_problem(self, agent) -> dict:
    return {
        "exec_summary": "Decompose problem into first principles and define definition of done",
        "step_plan": (
            "1. List all assumptions about the problem explicitly\n"
            "2. Challenge each: physical law, mathematical truth, convention, or unknown?\n"
            "3. Discard conventions, keep only laws and verified data\n"
            "4. Identify core actors, dynamics, and variants\n"
            "5. Define a falsifiable, measurable definition of done\n"
            "6. If no clear DoD is possible, reject the problem as invalid"
        ),
    }
