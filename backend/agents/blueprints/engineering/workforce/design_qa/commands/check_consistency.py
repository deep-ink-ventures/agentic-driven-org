"""Design QA command: cross-component and cross-page consistency audit."""

from agents.blueprints.base import command


@command(
    name="check_consistency",
    description=(
        "Cross-component and cross-page consistency audit. Checks type scale adherence, color palette "
        "compliance, spacing rhythm consistency, component variant usage, interaction pattern consistency "
        "(do similar things work the same way?), loading state consistency, empty state consistency, and "
        "error handling consistency. Produces severity-scored consistency findings with specific fix "
        "instructions."
    ),
    schedule=None,
    model="claude-opus-4-6",
)
def check_consistency(self, agent) -> dict:
    return {
        "exec_summary": "Cross-component and cross-page consistency audit: type scale, colors, spacing, interactions, states",
        "step_plan": (
            "1. Retrieve the frontend implementation and related pages/components\n"
            "2. Check type scale adherence (font sizes, weights, line heights match design system)\n"
            "3. Verify color palette compliance (only design token colors used)\n"
            "4. Audit spacing rhythm consistency (consistent use of spacing scale)\n"
            "5. Check component variant usage (correct variants for context)\n"
            "6. Verify interaction pattern consistency (similar actions behave the same way)\n"
            "7. Check loading state consistency (same skeleton/spinner patterns throughout)\n"
            "8. Check empty state consistency (consistent messaging and illustration patterns)\n"
            "9. Verify error handling consistency (same error display patterns throughout)\n"
            "10. Compile severity-scored findings with specific fix instructions"
        ),
    }
