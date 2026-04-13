"""Strategist command: consolidate clone outputs into exec summary."""

from agents.blueprints.base import command


@command(
    name="finalize-outreach",
    description=(
        "Consolidate all personalizer outputs into a 1-page executive summary. "
        "The CSV is assembled programmatically from personalizer outputs — do NOT generate it."
    ),
    model="claude-sonnet-4-6",
    max_tokens=4096,
)
def finalize_outreach(self, agent) -> dict:
    return {
        "exec_summary": "Consolidate personalizer outputs into executive summary",
        "step_plan": (
            "1. Review all personalizer clone outputs — one per target area\n"
            "2. Write a concise Executive Summary (max 1 page):\n"
            "   - What this campaign is\n"
            "   - Why this approach (timing, market signals)\n"
            "   - Who we target: table with segment, prospect count, speed-to-revenue, room potential\n"
            "   - Multiplier leads to escalate to human closer\n"
            "   - Dispatch priority (wave 1, 2, 3)\n"
            "   - Key risks\n"
            "3. Do NOT generate the CSV — it will be assembled from personalizer outputs by code.\n"
            "4. Do NOT reproduce individual email content — just summarize segments and counts."
        ),
    }
