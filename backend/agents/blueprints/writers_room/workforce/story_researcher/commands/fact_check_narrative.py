"""Story Researcher command: forensic fact-checking of narrative claims."""

from agents.blueprints.base import command


@command(
    name="fact_check_narrative",
    description=(
        "Forensic verification of manuscript claims: historical accuracy (dates, events, figures), "
        "technical/professional accuracy (industry processes, legal mechanics), geographic/cultural "
        "authenticity (locations, customs, local knowledge), and internal consistency (timeline, "
        "character knowledge, established rules). Each finding rated and fix-suggested."
    ),
    model="claude-opus-4-6",
)
def fact_check_narrative(self, agent, **kwargs):
    pass  # Dispatched via execute_task
