"""Design QA command: responsive design verification."""

from agents.blueprints.base import command


@command(
    name="check_responsive",
    description=(
        "Responsive design verification across 5 breakpoints: 320px (small mobile), 480px (large mobile), "
        "768px (tablet), 1024px (small desktop), 1440px (large desktop). Checks touch target sizes on mobile, "
        "verifies no horizontal scrolling, checks content priority changes (what is hidden vs reordered), "
        "verifies fluid typography and spacing, checks container queries, verifies safe area handling for "
        "notched devices. Produces severity-scored responsive findings with specific fix instructions."
    ),
    schedule=None,
    model="claude-opus-4-6",
)
def check_responsive(self, agent) -> dict:
    return {
        "exec_summary": "Responsive verification at 5 breakpoints: 320/480/768/1024/1440px with touch targets and fluid layout checks",
        "step_plan": (
            "1. Retrieve the frontend implementation to verify\n"
            "2. Test at 320px (small mobile): layout, touch targets, no horizontal scroll\n"
            "3. Test at 480px (large mobile): layout adjustments, content priority\n"
            "4. Test at 768px (tablet): layout transition, touch vs pointer considerations\n"
            "5. Test at 1024px (small desktop): full layout, information density\n"
            "6. Test at 1440px (large desktop): max-width constraints, whitespace handling\n"
            "7. Verify fluid typography scaling between breakpoints\n"
            "8. Verify spacing rhythm scales appropriately\n"
            "9. Check container queries for component-level responsiveness\n"
            "10. Verify safe area handling (env(safe-area-inset-*)) for notched devices\n"
            "11. Compile severity-scored findings with specific fix instructions"
        ),
    }
