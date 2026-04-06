"""Shared base class for Writers Room feedback agents."""
from agents.blueprints.base import WorkforceBlueprint


class WritersRoomFeedbackBlueprint(WorkforceBlueprint):
    """Base for all Writers Room feedback/review agents.

    Overrides get_context() to strip sibling task reports — feedback agents
    analyse the synthesised Stage Deliverable document only, not raw creative
    fragments from individual creative agents.
    """

    _system_prompt: str = "You are a feedback agent for the Writers Room."

    @property
    def system_prompt(self) -> str:
        """Placeholder system prompt for feedback base class. Override in concrete subclasses."""
        return self._system_prompt

    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        """Allow setting system_prompt for testing."""
        self._system_prompt = value

    def get_context(self, agent):
        ctx = super().get_context(agent)
        ctx["sibling_agents"] = (
            "Sibling task reports are not available to feedback agents. "
            "Focus your analysis exclusively on the Stage Deliverable document above."
        )
        return ctx
