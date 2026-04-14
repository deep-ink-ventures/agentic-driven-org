"""Strategist command: identify multiplier target areas."""

from agents.blueprints.base import command


@command(
    name="identify-targets",
    description=(
        "Identify 3-5 multiplier target areas for outreach. Each area targets "
        "organizations or influential individuals who control many bookings, "
        "not individual customers."
    ),
    model="claude-sonnet-4-6",
    max_tokens=4096,
)
def identify_targets(self, agent) -> dict:
    return {
        "exec_summary": "Identify multiplier target areas for outreach campaign",
        "step_plan": (
            "1. Read the sprint instruction and project goal\n"
            "2. Identify 3-5 target areas focused on MULTIPLIER relationships:\n"
            "   - Tier 1: Organizations (accelerators, VC firms, corporate programs) — one deal = many bookings\n"
            "   - Tier 2: Influential individuals (community leaders, event organizers) — one relationship = referral stream\n"
            "3. For each area: define scope, decision-maker profile, messaging angle, timing signal\n"
            "4. Use numbered headers (### Target Area 1, etc.) for system parsing\n"
            "5. Keep each area to ~300-500 words. Total output ~3K max."
        ),
    }
