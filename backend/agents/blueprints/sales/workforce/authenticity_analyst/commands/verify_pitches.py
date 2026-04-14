"""Authenticity Analyst command: verify pitch content against prospect data."""

from agents.blueprints.base import command


@command(
    name="verify-pitches",
    description=(
        "Audit personalized pitches for fabricated claims. For each pitch, verify that "
        "all references are supported by the verified prospect data. Flag invented "
        "social media posts, conference talks, or misattributed roles."
    ),
    model="claude-sonnet-4-6",
    max_tokens=8192,
)
def verify_pitches(self, agent) -> dict:
    return {
        "exec_summary": "Verify pitch content against verified prospect data",
        "step_plan": (
            "1. Read all personalizer clone outputs\n"
            "2. For each pitch: does it reference claims not in the verified prospect data?\n"
            "3. Flag pitches that invent social media posts, conference talks, or quotes\n"
            "4. Flag pitches that misattribute the prospect's role or organization\n"
            "5. Output PASS or FAIL per pitch with specific issues"
        ),
    }
