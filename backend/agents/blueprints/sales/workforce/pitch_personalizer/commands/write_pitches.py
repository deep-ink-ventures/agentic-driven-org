"""Pitch Personalizer command: write B2B partnership pitches from verified prospect data."""

from agents.blueprints.base import command


@command(
    name="write-pitches",
    description=(
        "Write personalized B2B partnership pitches for verified prospects in one target area. "
        "Prospects are pre-verified — no web search needed. Pure copywriting."
    ),
    model="claude-sonnet-4-6",
)
def write_pitches(self, agent) -> dict:
    return {
        "exec_summary": "Write personalized pitches for verified prospects",
        "step_plan": (
            "1. Read the target area brief and messaging angle\n"
            "2. Read the verified prospect list\n"
            "3. For each prospect: adapt the messaging angle using their specific details\n"
            "4. Write subject line, body (80-150 words), follow-ups, and closer briefing\n"
            "5. Frame every pitch as a B2B partnership opportunity, not a room booking"
        ),
    }
