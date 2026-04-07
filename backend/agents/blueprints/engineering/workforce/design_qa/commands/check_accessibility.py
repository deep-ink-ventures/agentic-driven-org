"""Design QA command: deep accessibility audit beyond automated tools."""

from agents.blueprints.base import command


@command(
    name="check_accessibility",
    description=(
        "Deep accessibility audit beyond what automated tools catch. Checks WCAG 2.1 AA compliance, "
        "semantic HTML structure, ARIA usage correctness, keyboard navigation (tab order, focus management, "
        "escape handling), color contrast (4.5:1 text, 3:1 large, 3:1 UI components), focus indicators "
        "(visible, high-contrast ring), screen reader experience, touch targets (44x44 minimum), reduced "
        "motion handling, and error states and form validation. Produces severity-scored accessibility "
        "findings with specific remediation instructions."
    ),
    schedule=None,
    model="claude-opus-4-6",
)
def check_accessibility(self, agent) -> dict:
    return {
        "exec_summary": "Deep accessibility audit: WCAG 2.1 AA, keyboard nav, contrast, ARIA, screen reader, touch targets",
        "step_plan": (
            "1. Retrieve the frontend implementation to audit\n"
            "2. Check semantic HTML structure (proper use of landmarks, headings, lists)\n"
            "3. Validate ARIA usage (roles, properties, states -- no ARIA is better than bad ARIA)\n"
            "4. Test keyboard navigation: tab order, focus management, escape handling\n"
            "5. Verify color contrast ratios (4.5:1 text, 3:1 large text, 3:1 UI components)\n"
            "6. Check focus indicators (visible, high-contrast ring on all interactive elements)\n"
            "7. Evaluate screen reader experience (announce state changes, live regions)\n"
            "8. Verify touch targets (44x44 minimum)\n"
            "9. Check reduced motion handling (prefers-reduced-motion media query)\n"
            "10. Review error states and form validation for accessibility\n"
            "11. Compile severity-scored findings with specific fix instructions"
        ),
    }
