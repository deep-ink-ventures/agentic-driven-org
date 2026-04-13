"""Market Analyst command: analyze market fit and positioning."""

from agents.blueprints.base import command

DESCRIPTION = (
    "Run a full market positioning assessment: comp scoring matrix with 4-6 comparable titles, "
    "platform/publisher fit analysis against current commissioning trends, audience alignment check, "
    "and zeitgeist relevance scoring. Each finding is flagged with severity "
    "(critical/major/minor/strength) and paired with an actionable fix or pitch strategy."
)


@command(
    name="analyze",
    description=DESCRIPTION,
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
