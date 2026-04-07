"""UX Designer command: review existing UI against Impeccable Style guidelines."""

from agents.blueprints.base import command


@command(
    name="critique",
    description=(
        "Review existing UI against the Impeccable Style guidelines: AI Slop Test (would someone "
        "immediately guess AI made this?), Nielsen's 10 heuristics with 0-4 scoring, cognitive "
        "load assessment (intrinsic/extraneous/germane), persona testing (5 personas: power user, "
        "new user, accessibility-dependent, stressed/rushing, non-native speaker), specific "
        "violations with fix suggestions. Every finding must be actionable."
    ),
    model="claude-opus-4-6",
)
def critique(self, agent, **kwargs):
    pass  # Dispatched via execute_task
