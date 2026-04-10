"""Synthesizer command: build and validate proof of concept."""

from agents.blueprints.base import command


@command(
    name="build-poc",
    description=(
        "Build a proof of concept from a high-scoring hypothesis. Push code to the "
        "playground repo, trigger GitHub Action, validate results against definition of done."
    ),
    model="claude-opus-4-6",
    max_tokens=16000,
)
def build_poc(self, agent) -> dict:
    return {
        "exec_summary": "Build and validate proof of concept against definition of done",
        "step_plan": (
            "1. Review the hypothesis and pseudocode sketch\n"
            "2. Translate pseudocode into executable code\n"
            "3. Push code to playground repo via GitHub API\n"
            "4. Trigger GitHub Action workflow\n"
            "5. Read back results and validate against definition of done\n"
            "6. Self-score 1-10 on how well the DoD is met"
        ),
    }
