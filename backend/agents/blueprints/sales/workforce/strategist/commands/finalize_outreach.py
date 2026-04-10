"""Strategist command: consolidate clone outputs into exec summary + CSV."""

from agents.blueprints.base import command


@command(
    name="finalize-outreach",
    description=(
        "Consolidate all personalizer outputs into two deliverables: "
        "a 1-page exec summary and a machine-readable CSV with columns: "
        "channel, identifier, subject, content."
    ),
    model="claude-opus-4-6",
    max_tokens=16384,
)
def finalize_outreach(self, agent) -> dict:
    return {
        "exec_summary": "Consolidate personalizer outputs into exec summary + CSV",
        "step_plan": (
            "1. Review all personalizer clone outputs — one per target area\n"
            "2. Write Exec Summary: max 1 page — what this is about, why it is the right approach, "
            "whom we target with what. No chat, no filler.\n"
            "3. Write CSV output with columns: channel, identifier, subject, content\n"
            "   - channel: outreach agent identifier (e.g. email)\n"
            "   - identifier: email address, Reddit username, Twitter handle, phone, etc.\n"
            "   - subject: subject line or headline\n"
            "   - content: the outreach message\n"
            "4. Output both documents clearly separated with headers"
        ),
    }
