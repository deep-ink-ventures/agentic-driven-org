from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.engineering.workforce.design_qa.commands import (
    check_accessibility,
    check_consistency,
    check_responsive,
    review_design,
)
from agents.blueprints.engineering.workforce.design_qa.skills import format_skills

logger = logging.getLogger(__name__)

NIELSEN_HEURISTICS = """\
## Nielsen's 10 Usability Heuristics -- Score each 0-4

Score every heuristic for the implementation under review:
- 0 = No usability problem
- 1 = Cosmetic problem only -- fix if extra time
- 2 = Minor usability problem -- low priority fix
- 3 = Major usability problem -- important to fix, high priority
- 4 = Usability catastrophe -- imperative to fix before release

1. **Visibility of system status**: Does the system keep users informed about what is going on through appropriate feedback within reasonable time?
2. **Match between system and the real world**: Does the system speak the user's language, with familiar words, phrases, and concepts?
3. **User control and freedom**: Can users easily undo/redo? Is there a clearly marked emergency exit?
4. **Consistency and standards**: Do similar elements behave the same way? Are platform conventions followed?
5. **Error prevention**: Does the design prevent errors before they occur? Confirmation dialogs for destructive actions?
6. **Recognition rather than recall**: Is information visible or easily retrievable? Are instructions visible or accessible?
7. **Flexibility and efficiency of use**: Are there accelerators for expert users? Can frequent actions be streamlined?
8. **Aesthetic and minimalist design**: Does every element serve a purpose? Is there visual noise that does not help the user?
9. **Help users recognize, diagnose, and recover from errors**: Are error messages in plain language? Do they suggest a solution?
10. **Help and documentation**: Is help available in context? Is documentation searchable and task-focused?
"""

AI_SLOP_TEST = """\
## AI Slop Test -- Reject if ANY of these are true

Check the implementation for these telltale signs of generic AI-generated design:
- Gratuitous gradients that serve no informational purpose
- Card-heavy layouts where a simple list would work better
- Decorative icons on every element without functional meaning
- Excessive border-radius making everything look like a toy
- Overly generous padding that wastes screen real estate
- Drop shadows on everything regardless of elevation hierarchy
- Generic stock-photo hero sections with no real content
- "Dashboard-itis": everything crammed into a grid of identical cards
- Animated transitions that slow down task completion
- Color used decoratively rather than to communicate meaning
"""

COGNITIVE_LOAD_ASSESSMENT = """\
## Cognitive Load Assessment

Evaluate three types of cognitive load:
- **Intrinsic load**: inherent complexity of the task itself (cannot be reduced, only managed)
- **Extraneous load**: unnecessary complexity from poor design (MUST be eliminated)
- **Germane load**: productive effort spent building mental models (should be supported)

8-item checklist:
1. Can the user complete the primary task without reading instructions?
2. Is the information hierarchy clear within 5 seconds of looking at the page?
3. Are related items grouped and unrelated items separated?
4. Is the number of choices at any decision point manageable (ideally 5-7)?
5. Are defaults provided for common choices?
6. Is progressive disclosure used (advanced options hidden until needed)?
7. Does the design avoid requiring the user to remember info across screens?
8. Are actions reversible, reducing the cost of mistakes?
"""

PERSONA_WALKTHROUGHS = """\
## Persona Walkthroughs -- Test with ALL 5 personas

Walk through every major user flow with each persona and note friction points:

### Alex (Power User)
- Wants keyboard shortcuts and bulk actions
- Frustrated by too many confirmation dialogs
- Needs high information density -- do not hide things behind extra clicks
- Red flags: no keyboard shortcuts, forced step-by-step wizards, low information density, no bulk operations

### Jordan (New User)
- Needs clear onboarding and progressive disclosure
- Wants obvious next steps at every point
- Red flags: jargon without explanation, no empty states with guidance, hidden primary actions, unclear navigation

### Sam (Accessibility-Dependent)
- Uses screen reader, keyboard-only navigation, high contrast mode, reduced motion
- Needs everything to work without a mouse
- Red flags: missing focus indicators, unlabeled interactive elements, motion without prefers-reduced-motion, poor contrast

### Riley (Stressed/Rushing)
- Scanning, not reading -- needs visual hierarchy that supports quick decisions
- Wants clear CTAs and easy error recovery
- Red flags: wall of text, ambiguous button labels ("Submit" instead of "Save Changes"), destructive actions without confirmation, poor error messages

### Casey (Non-Native English Speaker)
- Needs clear, simple language -- no idioms, colloquialisms, or cultural references
- Wants consistent terminology (same word for same concept everywhere)
- Red flags: idioms ("piece of cake"), inconsistent terminology, humor that does not translate, abbreviations without explanation
"""

SEVERITY_FRAMEWORK = """\
## Severity Framework

Classify every finding:
- **P0 -- Blocks Ship**: Broken functionality, accessibility failure that prevents use, data loss risk, security issue. MUST fix before release.
- **P1 -- Fix Before Next Release**: Significant usability problem, major inconsistency, accessibility issue that degrades experience. Fix in current sprint.
- **P2 -- Fix Soon**: Minor usability issue, cosmetic inconsistency, could-be-better interaction. Fix within next 2 sprints.
- **P3 -- Nice to Have**: Polish item, minor enhancement, edge case improvement. Add to backlog.
"""

DO_DONT_CHECKLIST = """\
## Impeccable Style DO/DON'T Checklist

### DO:
- Use semantic HTML elements (<nav>, <main>, <article>, <section>, <aside>, <header>, <footer>)
- Provide visible focus indicators on ALL interactive elements
- Use consistent spacing from the design system's spacing scale
- Ensure every interactive element has a minimum 44x44px touch target
- Use color to reinforce meaning, not as the sole indicator
- Provide loading skeletons that match the shape of the content they replace
- Write error messages that explain what happened AND what to do next
- Use progressive disclosure to manage complexity
- Ensure every form field has a visible label (not just placeholder text)
- Test with real content lengths (not just "Lorem ipsum")

### DON'T:
- Use div/span for interactive elements (use button, a, input)
- Rely on color alone to convey information
- Disable the browser's native focus outline without providing a better one
- Use fixed heights on text containers (content will vary)
- Hide essential functionality behind hover-only interactions
- Use modal dialogs for non-blocking information
- Auto-play animations without respecting prefers-reduced-motion
- Use vague button labels ("Click Here", "Submit", "OK")
- Truncate text without providing access to the full content
- Mix interaction patterns (if checkboxes select items in one list, do the same everywhere)
"""


class DesignQaBlueprint(WorkforceBlueprint):
    name = "Design QA Specialist"
    slug = "design_qa"
    controls = "frontend_engineer"
    description = (
        "Reviews frontend implementations against design specifications and the Impeccable Style "
        "guidelines. Scores issues by severity using Nielsen's heuristics and tests with 5 user "
        "personas. The quality gate before frontend work ships."
    )
    tags = ["engineering", "qa", "design", "ux", "accessibility", "review"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return f"""You are a Design QA Specialist agent. You review frontend implementations AFTER they are built, checking them against design specs and the Impeccable Style guidelines. You are the quality gate before frontend work is considered done.

## Your Role
You produce structured QA reports with severity-scored findings and specific fix instructions. You do NOT produce code. You produce the critique that ensures the code meets the bar.

## Process
1. Receive a frontend implementation to review (PR, deployed preview, or screenshots)
2. Compare against the design spec from UX Designer
3. Run the AI Slop Test -- reject anything that looks generically AI-generated
4. Score against Nielsen's 10 heuristics (0-4 severity)
5. Assess cognitive load (intrinsic, extraneous, germane)
6. Walk through with 5 test personas
7. Apply the DO/DON'T checklist
8. Compile findings into a severity-scored report (P0-P3)

## Output Format
Your output is always a structured QA report:
- Executive summary (pass/fail with P0 count)
- Heuristic scores table (10 rows, scored 0-4)
- Cognitive load assessment (3 types with specific findings)
- Persona walkthrough results (5 personas, friction points per persona)
- Detailed findings list sorted by severity (P0 first)
- Each finding: severity, category, description, location, fix instruction

{AI_SLOP_TEST}

{NIELSEN_HEURISTICS}

{COGNITIVE_LOAD_ASSESSMENT}

{PERSONA_WALKTHROUGHS}

{SEVERITY_FRAMEWORK}

{DO_DONT_CHECKLIST}

## Critical Rules
- You NEVER produce code. You produce QA reports.
- Every finding MUST include a specific fix instruction (not just "fix this").
- P0 findings block ship -- the implementation does not pass QA until all P0s are resolved.
- Be specific about location: reference exact components, elements, or screens.
- When in doubt, walk through the flow as each persona and note where they would struggle.

When executing tasks, respond with a JSON object:
{{
    "qa_report": "The full structured QA report in markdown",
    "verdict": "PASS" | "FAIL",
    "p0_count": 0,
    "p1_count": 0,
    "p2_count": 0,
    "p3_count": 0,
    "heuristic_scores": {{"h1": 0, "h2": 0, ...}},
    "persona_friction": {{"alex": [], "jordan": [], "sam": [], "riley": [], "casey": []}},
    "report": "Executive summary"
}}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands
    review_design = review_design
    check_accessibility = check_accessibility
    check_responsive = check_responsive
    check_consistency = check_consistency

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        command_name = (task.command or "").strip()
        dispatch = {
            "review_design": self._execute_review_design,
            "check_accessibility": self._execute_check_accessibility,
            "check_responsive": self._execute_check_responsive,
            "check_consistency": self._execute_check_consistency,
        }
        handler = dispatch.get(command_name, self._execute_review_design)
        return handler(agent, task)

    # ------------------------------------------------------------------
    # Command executors
    # ------------------------------------------------------------------

    def _execute_review_design(self, agent: Agent, task: AgentTask) -> str:
        """Full design QA review with heuristics, personas, and Impeccable Style."""
        from agents.ai.claude_client import call_claude, parse_json_response

        suffix = (
            "Perform a full design QA review of this frontend implementation.\n\n"
            "You MUST include ALL of the following sections in your QA report:\n"
            "1. AI Slop Test -- check for generic AI-generated design patterns\n"
            "2. Nielsen's 10 Heuristics -- score each 0-4\n"
            "3. Cognitive Load Assessment -- evaluate intrinsic, extraneous, germane load with 8-item checklist\n"
            "4. Persona Walkthroughs -- test as Alex, Jordan, Sam, Riley, Casey and note friction points\n"
            "5. DO/DON'T Checklist -- verify compliance with Impeccable Style rules\n"
            "6. Severity-scored findings (P0-P3) with specific fix instructions\n\n"
            "Return JSON:\n"
            "{\n"
            '    "qa_report": "Full markdown QA report",\n'
            '    "verdict": "PASS or FAIL",\n'
            '    "p0_count": 0,\n'
            '    "p1_count": 0,\n'
            '    "p2_count": 0,\n'
            '    "p3_count": 0,\n'
            '    "heuristic_scores": {"h1": 0, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0, "h7": 0, "h8": 0, "h9": 0, "h10": 0},\n'
            '    "persona_friction": {"alex": [], "jordan": [], "sam": [], "riley": [], "casey": []},\n'
            '    "report": "Executive summary"\n'
            "}"
        )

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "review_design"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        if not data:
            return response

        verdict = data.get("verdict", "UNKNOWN")
        p0 = data.get("p0_count", 0)
        report = data.get("report", "")
        qa_report = data.get("qa_report", "")

        summary = f"Design QA Verdict: {verdict}\n"
        summary += f"P0: {p0} | P1: {data.get('p1_count', 0)} | P2: {data.get('p2_count', 0)} | P3: {data.get('p3_count', 0)}\n"
        if report:
            summary += f"\n{report}\n"
        if qa_report:
            summary += f"\n---\n\n{qa_report}"
        return summary

    def _execute_check_accessibility(self, agent: Agent, task: AgentTask) -> str:
        """Deep accessibility audit."""
        from agents.ai.claude_client import call_claude, parse_json_response

        suffix = (
            "Perform a deep accessibility audit of this frontend implementation.\n\n"
            "Check ALL of the following:\n"
            "- WCAG 2.1 AA compliance\n"
            "- Semantic HTML structure (landmarks, headings, lists)\n"
            "- ARIA usage correctness (roles, properties, states -- no ARIA is better than bad ARIA)\n"
            "- Keyboard navigation: tab order, focus management, escape handling\n"
            "- Color contrast: 4.5:1 for normal text, 3:1 for large text, 3:1 for UI components\n"
            "- Focus indicators: visible, high-contrast ring on all interactive elements\n"
            "- Screen reader experience: state announcements, live regions, meaningful alt text\n"
            "- Touch targets: 44x44px minimum\n"
            "- Reduced motion: prefers-reduced-motion handling\n"
            "- Error states and form validation accessibility\n\n"
            "Return JSON:\n"
            "{\n"
            '    "accessibility_report": "Full markdown accessibility audit report",\n'
            '    "wcag_level": "AA" or "below AA",\n'
            '    "p0_count": 0,\n'
            '    "p1_count": 0,\n'
            '    "findings": [{"severity": "P0", "category": "keyboard", "description": "...", "fix": "..."}],\n'
            '    "report": "Executive summary"\n'
            "}"
        )

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "check_accessibility"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        if not data:
            return response

        wcag = data.get("wcag_level", "unknown")
        p0 = data.get("p0_count", 0)
        report = data.get("report", "")
        full_report = data.get("accessibility_report", "")

        summary = f"Accessibility Audit: WCAG {wcag}\n"
        summary += f"P0: {p0} | P1: {data.get('p1_count', 0)}\n"
        if report:
            summary += f"\n{report}\n"
        if full_report:
            summary += f"\n---\n\n{full_report}"
        return summary

    def _execute_check_responsive(self, agent: Agent, task: AgentTask) -> str:
        """Responsive design verification."""
        from agents.ai.claude_client import call_claude, parse_json_response

        suffix = (
            "Perform a responsive design verification of this frontend implementation.\n\n"
            "Test at ALL 5 breakpoints:\n"
            "- 320px (small mobile)\n"
            "- 480px (large mobile)\n"
            "- 768px (tablet)\n"
            "- 1024px (small desktop)\n"
            "- 1440px (large desktop)\n\n"
            "Check:\n"
            "- Touch target sizes on mobile (44x44px minimum)\n"
            "- No horizontal scrolling at any breakpoint\n"
            "- Content priority changes (what is hidden vs reordered)\n"
            "- Fluid typography and spacing between breakpoints\n"
            "- Container queries for component-level responsiveness\n"
            "- Safe area handling for notched devices (env(safe-area-inset-*))\n\n"
            "Return JSON:\n"
            "{\n"
            '    "responsive_report": "Full markdown responsive audit report",\n'
            '    "breakpoint_results": {"320": "pass/fail", "480": "pass/fail", "768": "pass/fail", "1024": "pass/fail", "1440": "pass/fail"},\n'
            '    "p0_count": 0,\n'
            '    "p1_count": 0,\n'
            '    "findings": [{"severity": "P0", "breakpoint": "320px", "description": "...", "fix": "..."}],\n'
            '    "report": "Executive summary"\n'
            "}"
        )

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "check_responsive"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        if not data:
            return response

        bp_results = data.get("breakpoint_results", {})
        p0 = data.get("p0_count", 0)
        report = data.get("report", "")
        full_report = data.get("responsive_report", "")

        summary = "Responsive Verification:\n"
        for bp, result in sorted(bp_results.items(), key=lambda x: int(x[0])):
            summary += f"  {bp}px: {result}\n"
        summary += f"P0: {p0} | P1: {data.get('p1_count', 0)}\n"
        if report:
            summary += f"\n{report}\n"
        if full_report:
            summary += f"\n---\n\n{full_report}"
        return summary

    def _execute_check_consistency(self, agent: Agent, task: AgentTask) -> str:
        """Cross-component and cross-page consistency audit."""
        from agents.ai.claude_client import call_claude, parse_json_response

        suffix = (
            "Perform a cross-component and cross-page consistency audit.\n\n"
            "Check ALL of the following:\n"
            "- Type scale adherence (font sizes, weights, line heights match design system)\n"
            "- Color palette compliance (only design token colors used)\n"
            "- Spacing rhythm consistency (consistent use of spacing scale)\n"
            "- Component variant usage (correct variants for context)\n"
            "- Interaction pattern consistency (similar actions behave the same way)\n"
            "- Loading state consistency (same skeleton/spinner patterns throughout)\n"
            "- Empty state consistency (consistent messaging and illustration patterns)\n"
            "- Error handling consistency (same error display patterns throughout)\n\n"
            "Return JSON:\n"
            "{\n"
            '    "consistency_report": "Full markdown consistency audit report",\n'
            '    "categories": {"type_scale": "pass/fail", "color_palette": "pass/fail", "spacing": "pass/fail", "components": "pass/fail", "interactions": "pass/fail", "loading_states": "pass/fail", "empty_states": "pass/fail", "error_handling": "pass/fail"},\n'
            '    "p0_count": 0,\n'
            '    "p1_count": 0,\n'
            '    "findings": [{"severity": "P1", "category": "type_scale", "description": "...", "fix": "..."}],\n'
            '    "report": "Executive summary"\n'
            "}"
        )

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "check_consistency"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        if not data:
            return response

        categories = data.get("categories", {})
        p0 = data.get("p0_count", 0)
        report = data.get("report", "")
        full_report = data.get("consistency_report", "")

        summary = "Consistency Audit:\n"
        for cat, result in categories.items():
            summary += f"  {cat}: {result}\n"
        summary += f"P0: {p0} | P1: {data.get('p1_count', 0)}\n"
        if report:
            summary += f"\n{report}\n"
        if full_report:
            summary += f"\n---\n\n{full_report}"
        return summary
