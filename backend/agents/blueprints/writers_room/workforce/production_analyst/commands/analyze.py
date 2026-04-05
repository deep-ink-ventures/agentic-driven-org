"""Production Analyst command: analyze production feasibility and readiness."""

from agents.blueprints.base import command

DESCRIPTION = (
    "Run per-scene budget impact estimation with tiered cost flags, cast size and complexity assessment, "
    "location feasibility analysis, and VFX/practical effects requirements breakdown. Evaluates schedule "
    "implications, IP/rights considerations, and castability analysis including star attachment potential. "
    "For novels and theatre, applies equivalent publishing feasibility and production scale checks."
)


@command(
    name="analyze",
    description=DESCRIPTION,
    model="claude-sonnet-4-6",
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
