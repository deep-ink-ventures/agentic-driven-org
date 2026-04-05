"""Prospector command: research and qualify targets."""

from agents.blueprints.base import command


@command(
    name="research-targets",
    description=(
        "Research and qualify potential targets based on the leader's criteria. Uses web search to gather "
        "company info, key contacts, and recent activity. Returns a structured lead list with qualification "
        "notes and scoring for each prospect."
    ),
    model="claude-sonnet-4-6",
)
def research_targets(self, agent) -> dict:
    return {
        "exec_summary": "Research and qualify a batch of prospect targets",
        "step_plan": (
            "1. Review target criteria from task instructions\n"
            "2. Research each target via web search\n"
            "3. Build structured profiles with key contacts\n"
            "4. Score each prospect on qualification criteria\n"
            "5. Return ranked list with research notes"
        ),
    }
