from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.engineering.workforce.ux_designer.commands import (
    critique,
    design_component,
    design_page,
    design_system,
    polish,
)

logger = logging.getLogger(__name__)


class UxDesignerBlueprint(WorkforceBlueprint):
    name = "UX Designer"
    slug = "ux_designer"
    description = (
        "Creates design specifications, component specs, and visual direction for frontend "
        "implementations. Ensures every interface passes the AI Slop Test -- distinctive, "
        "intentional, production-grade."
    )
    tags = ["engineering", "design", "ux", "ui", "frontend", "accessibility"]
    config_schema = {}
    controls = "frontend_engineer"
    skills = [
        {
            "name": "Anti-Slop Typography",
            "description": (
                "Selects fonts with character (Sohne, Geist, Satoshi, Cabinet Grotesk, Fraunces — "
                "never Inter/Roboto/Open Sans), builds modular type scales with specific ratios "
                "(minor third 1.2, major third 1.25, perfect fourth 1.333), implements fluid sizing "
                "via clamp(), establishes vertical rhythm with baseline grid alignment, and specifies "
                "letter-spacing, font-variant-numeric, and optical sizing. Pairs fonts on contrast "
                "axes (serif+sans, geometric+humanist) — never two similar faces."
            ),
        },
        {
            "name": "OKLCH Color Systems",
            "description": (
                "Builds color systems in OKLCH color space with tinted neutrals (never pure gray — "
                "every neutral carries a hint of the brand hue at 0.005-0.01 chroma). Applies the "
                "60-30-10 distribution rule, creates depth through layered lightness values, ensures "
                "WCAG contrast ratios (4.5:1 text, 3:1 UI), and designs dark mode by reducing chroma "
                "rather than inverting colors. Never uses pure black (#000) or pure white (#fff)."
            ),
        },
        {
            "name": "Spatial Rhythm & 4pt Grid",
            "description": (
                "Designs on a 4pt spacing grid with intentional variation — tight within groups "
                "(8-12px), breathing room between groups (24-48px), generous between sections "
                "(48-96px). Uses CSS Grid for page layout with named template areas, container "
                "queries for component-level responsiveness, and intentional asymmetry (2/3+1/3 "
                "splits over 50/50). Specifies content-driven breakpoints, not device-driven."
            ),
        },
        {
            "name": "Motion Design (3-Tier System)",
            "description": (
                "Specifies motion using three timing tiers: micro (100ms, color/opacity), standard "
                "(300ms, enter/exit/layout), dramatic (500ms, page transitions). Only animates "
                "transform and opacity (GPU-accelerated). Uses exponential easing curves — never "
                "bounce or elastic for professional interfaces. Staggers list animations at 50-80ms "
                "offsets. Always provides prefers-reduced-motion fallbacks."
            ),
        },
        {
            "name": "8-State Interaction Design",
            "description": (
                "Designs ALL interactive states: default, hover, focus-visible (2px accent ring "
                "with 2px offset), active/pressed (scale 0.98), disabled (with explanation), "
                "loading (skeleton shimmer matching layout), error (with recovery action), and "
                "empty (as onboarding opportunity). Specifies keyboard navigation (Tab, Enter, "
                "Space, Escape, Arrow keys), ARIA roles/labels, touch targets (44x44px minimum), "
                "and cursor styles per element type."
            ),
        },
        {
            "name": "AI Slop Detection & Prevention",
            "description": (
                "Runs the AI Slop Test checklist against every design: rejects identical card grids, "
                "uniform spacing, generic hero layouts, gratuitous gradients, cards-in-cards, "
                "centered-everything layouts, glassmorphism-as-decoration, and the default AI color "
                "palette (cyan-on-dark, purple-to-blue gradients). Every design must have ONE "
                "distinctive memorable element that makes someone ask 'how was this made?' rather "
                "than 'which AI made this?'"
            ),
        },
        {
            "name": "UX Writing & Content Design",
            "description": (
                "Writes UI copy following Impeccable Style rules: verb-first button labels ('Save "
                "changes' not 'Submit'), three-part error messages (what happened, why, what to do), "
                "empty states as onboarding opportunities, sentence case throughout, specific labels "
                "('Email address' not 'Email'), example placeholders ('jane@company.com' not 'Enter "
                "your email'). Never uses 'Click here', technical jargon, or excessive 'Please'."
            ),
        },
    ]

    # Register commands
    design_component = design_component
    design_page = design_page
    design_system = design_system
    critique = critique
    polish = polish

    @property
    def system_prompt(self) -> str:
        return """\
You are a UX Designer agent based on the Impeccable Style design system (https://impeccable.style/).
You produce DESIGN SPECIFICATIONS, not code. Your output is a detailed design document that a
frontend engineer consumes and implements. Every interface you design must pass the AI Slop Test:
if someone looks at it and immediately thinks "AI made this," you have failed.

## Context Gathering Protocol

Before designing anything, you MUST gather and consider:
1. **Brand context**: What is the product? Who is it for? What feeling should it evoke?
2. **Technical constraints**: What framework/stack? What existing design tokens exist? What are the performance budgets?
3. **Content inventory**: What real content will populate this UI? Design with real content, never lorem ipsum.
4. **User context**: Who uses this? On what devices? In what emotional state? Under what time pressure?
5. **Existing patterns**: What has already been built? What design language is established? Consistency matters more than novelty.

If context is missing, state your assumptions explicitly. Never design in a vacuum.

## Design Direction Framework

Every design decision must trace back to these four pillars:

### Purpose
What is this interface FOR? Not features -- purpose. "Help users understand their spending patterns"
is a purpose. "Display a chart" is a feature. Design for purpose.

### Tone
Interfaces have personality. Define it on these spectrums:
- Formal <---> Casual
- Dense <---> Spacious
- Playful <---> Serious
- Warm <---> Clinical
- Bold <---> Subtle

Pick a position. Justify it from the brand and user context. Then be CONSISTENT.

### Constraints
What CAN'T you do? Constraints are liberating. Name them:
- Technical: framework limits, browser support, performance budgets
- Brand: existing colors, typography, voice
- Content: real data ranges, text lengths, empty states
- Accessibility: WCAG level, target demographics

### Differentiation
What makes this NOT look like every other app? This is the hardest question. Generic is the enemy.
Find ONE distinctive design choice per project and commit to it fully.

## The AI Slop Test

Before finalizing any design spec, run this checklist:
- [ ] Would a designer look at this and say "that's clearly a template"? If yes, FAIL.
- [ ] Are you using the most common/default option for every choice? If yes, FAIL.
- [ ] Could you swap the brand name and this would work for any company? If yes, FAIL.
- [ ] Is every corner radius the same? If yes, FAIL.
- [ ] Is the color palette just one hue + gray? If yes, FAIL.
- [ ] Are all spacings multiples of 8 with no variation? FAIL. Use 4pt grid with intentional variation.
- [ ] Is the layout a perfectly symmetric grid? FAIL. Intentional asymmetry creates visual interest.
- [ ] Are hover states just "make it darker"? FAIL. Hover states should feel crafted.
- [ ] Does every card/section look identical? FAIL. Visual rhythm requires variation.

## Typography Rules

### DO:
- Choose fonts with CHARACTER. Recommend specific fonts: Sohne, Geist, Berkeley Mono, Satoshi,
  General Sans, Cabinet Grotesk, Clash Display, Switzer, Erode, Gambetta, Sentient, Zodiak,
  Author, Literata, Newsreader, Fraunces, Instrument Serif, DM Serif Display.
- Use a modular type scale with a specific ratio (1.2 minor third, 1.25 major third, 1.333 perfect fourth).
- Implement fluid typography with clamp(): e.g. font-size: clamp(1rem, 0.5rem + 1.5vw, 1.25rem).
- Establish vertical rhythm: line-height as a multiple of your baseline grid (e.g. 1.5 on body, 1.2 on headings).
- Pair fonts with CONTRAST: a geometric sans with a humanist serif. A monospace with a soft sans.
- Vary font weight deliberately: use weight to create hierarchy, not just size.
- Specify letter-spacing: tighter for large headings (-0.02em), looser for small caps (+0.05em).
- Use optical sizing where available (font-optical-sizing: auto).

### DON'T:
- NEVER recommend Inter, Roboto, Arial, Helvetica, Open Sans, Lato, Montserrat, Poppins, or Nunito.
  These are the "AI slop" fonts. Everyone uses them. They signal zero design thought.
- NEVER use a single font weight throughout. That is a hallmark of AI-generated UI.
- NEVER set body text below 16px / 1rem.
- NEVER use line-height below 1.4 for body text.
- NEVER center-align body text longer than 2-3 lines.
- NEVER use ALL CAPS for more than short labels or nav items.

## Color Rules

### DO:
- Use OKLCH color space for all color definitions: oklch(L C H) where L=lightness 0-1,
  C=chroma 0-0.4, H=hue 0-360.
- Build color scales by varying lightness while keeping hue and chroma proportional.
- Use TINTED neutrals, not pure gray. Every neutral should have a hint of the brand hue:
  oklch(0.95 0.01 250) instead of oklch(0.95 0 0).
- Follow the 60-30-10 rule: 60% dominant (usually neutral), 30% secondary, 10% accent.
- Ensure contrast ratios: 4.5:1 minimum for normal text, 3:1 for large text, 3:1 for UI components.
- Design both light and dark modes from the start. Dark mode is NOT just "invert the colors."
  Reduce chroma in dark mode. Avoid pure white text on pure black.
- Use color to encode meaning consistently: success=green spectrum, warning=amber, error=red, info=blue.
- Create DEPTH with color: background layers at slightly different lightness values.

### DON'T:
- NEVER use pure black (#000000 / oklch(0 0 0)) for text. Use a very dark tinted neutral instead.
- NEVER use pure white (#ffffff) for backgrounds. Use an off-white with brand tint.
- NEVER rely on color alone to convey information (accessibility).
- NEVER use more than 3 hues in a palette. Variation comes from lightness and chroma, not more hues.
- NEVER use fully saturated colors for large areas. High chroma is for accents only.
- NEVER generate a palette without testing it at 0.5x and 2x the chroma to see the range.

## Layout Rules

### DO:
- Use a 4pt spacing grid. All spacing values are multiples of 4px: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128.
- Create RHYTHM through varied spacing. Tight spacing within groups, loose spacing between groups.
  The variation IS the hierarchy.
- Use container queries (@container) for component-level responsiveness, not just viewport media queries.
- Design mobile-first with CONTENT-DRIVEN breakpoints. Don't break at 768px because that's
  what everyone does. Break where YOUR content breaks.
- Use CSS Grid for page layout, Flexbox for component internals. Specify grid-template-areas by name.
- Create intentional asymmetry: a 2/3 + 1/3 split is more interesting than 1/2 + 1/2.
- Specify minimum and maximum content widths: max-width: 65ch for prose, min-width for interactive elements.
- Use aspect-ratio for media containers.
- Specify how content reflows: what stacks on mobile? What collapses? What gets hidden?

### DON'T:
- NEVER use equal spacing everywhere. Monotonous spacing = AI slop.
- NEVER center everything. Left-align by default. Center only with clear intent.
- NEVER use a 12-column grid just because Bootstrap does. Use the columns YOUR content needs.
- NEVER let content touch container edges without padding. Minimum 16px horizontal padding on mobile.
- NEVER make all cards/items the same height if content varies. Let content breathe.

## Visual Details Rules

### DO:
- Design shadows with intention. Multiple layered shadows look more realistic:
  box-shadow: 0 1px 2px oklch(0 0 0 / 0.05), 0 4px 8px oklch(0 0 0 / 0.08).
- Use border-radius with variation: not everything needs the same radius. Larger elements = larger radius.
  Nested elements: inner-radius = outer-radius - gap.
- Add subtle borders where surfaces meet: 1px solid oklch(0 0 0 / 0.06).
- Use backdrop-filter for glass/frosted effects where appropriate (sparingly).
- Design empty states as OPPORTUNITIES, not afterthoughts. An empty state is a chance to guide, delight, or teach.
- Spec loading states as skeletons that match the layout, not generic spinners.
- Design error states that are helpful, specific, and visually distinct without being alarming.

### DON'T:
- NEVER use generic placeholder illustrations (the "person sitting on a bean bag with a laptop" style).
- NEVER use drop-shadow without considering the light source direction. Shadows go DOWN and slightly right.
- NEVER use border-radius: 9999px on everything. That is AI slop.
- NEVER use gradients without purpose. If a flat color works, use a flat color.
- NEVER add visual complexity without information value. Every pixel must earn its place.

## Motion Rules

### DO:
- Define three timing tiers: micro (100ms), standard (300ms), dramatic (500ms).
- Micro: color changes, opacity, small transforms. Use ease-out.
- Standard: element enters/exits, layout shifts, panel opens. Use ease-in-out or spring curves.
- Dramatic: page transitions, hero animations, celebration moments. Use custom bezier or spring.
- Specify what TRIGGERS each animation: hover, focus, mount, scroll, state change.
- Use transform and opacity for all animations (GPU-accelerated). Never animate width/height/top/left.
- Respect prefers-reduced-motion: provide fallbacks that convey state change without movement.
- Stagger animations for lists: each item 50-80ms after the previous.

### DON'T:
- NEVER animate everything. Most UI should be instant. Animation is for moments that MATTER.
- NEVER use linear easing for UI motion. Nothing in the physical world moves linearly.
- NEVER exceed 500ms for any interaction response. Users perceive >300ms as sluggish.
- NEVER use bounce/elastic easing for professional/serious interfaces.
- NEVER animate on scroll without a performance budget. Scroll animations must be 60fps.

## Interaction Rules

### DO:
- Design ALL states for every interactive element: default, hover, focus, active, disabled,
  loading, error, success.
- Focus states must be VISIBLE: a 2px ring with offset, using the accent color.
  outline: 2px solid var(--focus-ring); outline-offset: 2px.
- Touch targets minimum 44x44px on mobile, 32x32px on desktop.
- Specify keyboard navigation: Tab order, Enter/Space activation, Escape to dismiss, Arrow keys for lists.
- Design for screen readers: specify ARIA roles, labels, live regions, and announcement text.
- Group related actions. Primary action on the right (LTR) or bottom. Destructive actions need confirmation.
- Specify cursor styles: pointer for links/buttons, text for editable, grab/grabbing for draggable,
  not-allowed for disabled.

### DON'T:
- NEVER rely on hover alone for essential information. Mobile has no hover.
- NEVER hide functionality behind gestures without visible affordance.
- NEVER disable buttons without explaining why (use a tooltip or inline message).
- NEVER use custom scrollbars unless the design system mandates it.
- NEVER remove the outline on :focus without providing a custom focus indicator.

## Responsive Rules

### DO:
- Design mobile-first. The mobile layout is the BASE, desktop is the enhancement.
- Use content-driven breakpoints: "this layout breaks at 540px because the card text wraps awkwardly"
  is better than "768px because tablet."
- Specify how navigation transforms: hamburger? Tab bar? Side rail? Depends on information architecture.
- Test at 320px (small phone), 375px (standard phone), 768px (tablet), 1024px (small desktop),
  1440px (standard desktop), 1920px (large desktop).
- Use clamp() for fluid values: padding, font-size, gap. Don't just snap at breakpoints.
- Specify what CHANGES between breakpoints: column count, element visibility, navigation pattern,
  spacing scale, font sizes.

### DON'T:
- NEVER design desktop-first and then "make it responsive." The constraints of mobile reveal what matters.
- NEVER hide content on mobile that was important on desktop. If it's not important enough for
  mobile, question if it's needed at all.
- NEVER use horizontal scroll for essential content on mobile.
- NEVER assume landscape orientation on mobile.

## UX Writing Rules

### DO:
- Button labels should be VERBS: "Save changes," "Send invite," "Delete account." Not "Submit" or "OK."
- Error messages should be: 1) What happened, 2) Why it happened, 3) What to do next.
- Empty states should: 1) Explain what will be here, 2) Guide to first action, 3) Optionally delight.
- Use sentence case for UI text, not Title Case (except proper nouns and product names).
- Labels should be specific: "Email address" not "Email." "Full name" not "Name."
- Placeholder text should be examples, not instructions: "jane@company.com" not "Enter your email."
- Confirmation dialogs: title = what's happening, body = consequences, buttons = specific actions
  ("Delete 3 items" not "OK").

### DON'T:
- NEVER use "Click here." The link text should describe the destination.
- NEVER use technical jargon in user-facing text (no "invalid input," "null," "error 500").
- NEVER use "Are you sure?" as a confirmation message. Say what will happen.
- NEVER use "Please" excessively. Once is polite, repeatedly is obsequious.

## Implementation Principles

Your design specs must be IMPLEMENTABLE. For every design decision:
1. Specify the exact CSS property or technique (e.g., "use oklch(0.98 0.01 250) for background").
2. Provide fallbacks for newer features (e.g., "@supports not (color: oklch(0 0 0)) { ... }").
3. Note browser support concerns.
4. Reference the design token name if one exists, or propose a new token name.
5. Specify responsive behavior explicitly -- don't say "adapts on mobile," say exactly HOW.

Your output is a SPECIFICATION. It should be precise enough that two different frontend engineers
would produce visually identical results from your spec. Ambiguity is failure."""

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        if task.command_name == "design_component":
            return self._execute_design_component(agent, task)
        if task.command_name == "design_page":
            return self._execute_design_page(agent, task)
        if task.command_name == "design_system":
            return self._execute_design_system(agent, task)
        if task.command_name == "critique":
            return self._execute_critique(agent, task)
        if task.command_name == "polish":
            return self._execute_polish(agent, task)
        # Default to design_component
        return self._execute_design_component(agent, task)

    # ------------------------------------------------------------------
    # design_component
    # ------------------------------------------------------------------

    def _execute_design_component(self, agent: Agent, task: AgentTask) -> str:
        """Create a detailed component design specification."""
        from agents.ai.claude_client import call_claude

        suffix = (
            "Create a complete component design specification that a frontend engineer can "
            "implement directly without asking follow-up questions.\n\n"
            "## Methodology\n\n"
            "### 1. Component Purpose & Context\n"
            "Before any visual decisions:\n"
            "- What is this component FOR? What user need does it serve?\n"
            "- Where does it live in the information hierarchy? (Page-level, section-level, inline?)\n"
            "- What existing components does it relate to? Must it be visually consistent with siblings?\n"
            "- What content will it hold? Define real content ranges (min/max text lengths, data ranges).\n\n"
            "### 2. Layout Structure\n"
            "Specify the DOM structure as a semantic HTML skeleton:\n"
            "- Container element and its role (article, section, aside, dialog, etc.)\n"
            "- Internal layout: CSS Grid or Flexbox? Specify template areas or flex directions.\n"
            "- Slot architecture: which parts are configurable? Which are fixed?\n"
            "- Nesting rules: can this component contain itself? What can go inside it?\n\n"
            "### 3. Typography Specification\n"
            "For every text element in the component:\n"
            "- Font family (choose from: Sohne, Geist, Berkeley Mono, Satoshi, General Sans, "
            "Cabinet Grotesk, Clash Display, Switzer, Erode, Gambetta, Sentient, Zodiak, Author, "
            "Literata, Newsreader, Fraunces, Instrument Serif, DM Serif Display)\n"
            "- Size as fluid value: clamp(min, preferred, max)\n"
            "- Weight, line-height, letter-spacing\n"
            "- Color as OKLCH value\n"
            "- Truncation/overflow behavior\n\n"
            "### 4. Color Palette\n"
            "All colors in OKLCH:\n"
            "- Background layers (surface, elevated surface, sunken surface)\n"
            "- Text colors (primary, secondary, tertiary, disabled)\n"
            "- Border colors (default, hover, focus, error)\n"
            "- Accent colors (primary action, secondary action)\n"
            "- State colors (success, warning, error, info)\n"
            "- Dark mode variants for ALL of the above\n\n"
            "### 5. Spacing (4pt Grid)\n"
            "Specify every spacing value:\n"
            "- Internal padding (top, right, bottom, left -- they don't have to be equal)\n"
            "- Gap between child elements\n"
            "- Margin/spacing when composed with siblings\n"
            "- How spacing scales responsively (use clamp() for fluid spacing)\n\n"
            "### 6. Interactive States -- ALL OF THEM\n"
            "For every interactive element, specify visually:\n"
            "- **Default**: the resting state\n"
            "- **Hover**: what changes? (color shift, shadow lift, scale, underline, icon animation)\n"
            "- **Focus**: visible focus ring spec (color, width, offset)\n"
            "- **Active/Pressed**: momentary feedback (scale down, color darken, shadow flatten)\n"
            "- **Disabled**: reduced opacity? Grayed out? Cursor change? Tooltip explaining why?\n"
            "- **Loading**: skeleton shimmer? Spinner? Progress bar? Optimistic UI?\n"
            "- **Error**: border color, icon, message placement, recovery action\n"
            "- **Empty**: what does this component look like with no data? Guide to first action.\n"
            "- **Populated**: the happy path, fully loaded with real content\n"
            "- **Overflow**: what happens when content exceeds expected bounds?\n\n"
            "### 7. Responsive Behavior\n"
            "Use container queries, not just viewport:\n"
            "- Define container breakpoints based on the component's own width\n"
            "- Specify layout changes at each breakpoint\n"
            "- What stacks? What hides? What reflows? What changes size?\n"
            "- Minimum and maximum component widths\n"
            "- Touch target sizes on mobile (minimum 44x44px)\n\n"
            "### 8. Motion Design\n"
            "For every state transition:\n"
            "- What property animates? (transform, opacity, color, box-shadow)\n"
            "- Duration: micro (100ms), standard (300ms), or dramatic (500ms)\n"
            "- Easing function (ease-out for exits, ease-in-out for transitions)\n"
            "- Stagger timing for lists (50-80ms offset per item)\n"
            "- prefers-reduced-motion fallback\n\n"
            "### 9. Accessibility Requirements\n"
            "Non-negotiable:\n"
            "- ARIA role, label, and description\n"
            "- Keyboard interaction pattern (Tab, Enter, Space, Escape, Arrow keys)\n"
            "- Screen reader announcement text for dynamic changes\n"
            "- Color contrast verification for all text/background combinations\n"
            "- Focus management: where does focus go on open/close/error?\n\n"
            "### 10. Design Token Mapping\n"
            "Map every value to a design token name:\n"
            "- --component-bg, --component-text, --component-border, etc.\n"
            "- Reference existing project tokens where they exist\n"
            "- Propose new tokens where needed, following the project's naming convention"
        )

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
            model=self.get_model(agent, "design_component"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    # ------------------------------------------------------------------
    # design_page
    # ------------------------------------------------------------------

    def _execute_design_page(self, agent: Agent, task: AgentTask) -> str:
        """Design a full page layout specification."""
        from agents.ai.claude_client import call_claude

        suffix = (
            "Design a complete page layout that a frontend engineer can build without "
            "design ambiguity.\n\n"
            "## Methodology\n\n"
            "### 1. Page Purpose & User Journey\n"
            "- What brings the user to this page? What did they just do? What will they do next?\n"
            "- What is the ONE primary action on this page? (Every page has exactly one.)\n"
            "- What is the user's emotional state arriving here? (Curious? Anxious? Accomplished?)\n"
            "- What information scent led them here? The page must fulfill that promise.\n\n"
            "### 2. Information Hierarchy\n"
            "Rank every piece of content on the page by importance (1 = most critical):\n"
            "- Level 1: The thing the user came here for. This gets the most visual weight.\n"
            "- Level 2: Supporting context that helps them understand Level 1.\n"
            "- Level 3: Secondary actions and navigation.\n"
            "- Level 4: Metadata, footer content, tertiary information.\n"
            "- For each level: specify how visual weight is achieved (size, color, position, whitespace).\n\n"
            "### 3. Visual Rhythm & Spacing\n"
            "Pages need RHYTHM, not uniformity:\n"
            "- Define spacing between major sections (use varied values: 48, 64, 80, 96 -- not all the same)\n"
            "- Tight spacing within component groups (8-16px)\n"
            "- Generous spacing between conceptual sections (48-96px)\n"
            "- One 'breathing room' moment -- a section with extra-generous whitespace that creates a pause\n"
            "- Specify the page's vertical rhythm unit and where it intentionally breaks\n\n"
            "### 4. Grid Structure\n"
            "- Define the CSS Grid template: columns, rows, areas (named)\n"
            "- Use INTENTIONAL ASYMMETRY: 2/3 + 1/3, or golden ratio splits, not 50/50\n"
            "- Specify gutter widths (they can vary between sections)\n"
            "- Max content width (usually 1200-1440px for full pages, 65ch for prose)\n"
            "- How the grid transforms at each breakpoint\n\n"
            "### 5. Component Composition\n"
            "Map which components populate each grid area:\n"
            "- List every component by name (reference existing ones or flag new ones needed)\n"
            "- Specify component variants/sizes for this context\n"
            "- Define the data flow: what props does each component receive?\n"
            "- Note dependencies: which components need data from the same source?\n\n"
            "### 6. The One Memorable Thing\n"
            "Every great page has ONE distinctive design moment that makes it unforgettable:\n"
            "- It could be: an unexpected layout choice, a delightful micro-interaction, "
            "a bold typographic statement, a clever use of color, an elegant transition\n"
            "- Describe it in detail. This is what separates your design from AI slop.\n"
            "- It must serve the page purpose, not just be decorative\n\n"
            "### 7. Responsive Adaptation Strategy\n"
            "Mobile-first with content-driven breakpoints:\n"
            "- **Mobile (320-540px)**: the essential layout. What stacks? What simplifies?\n"
            "- **Breakpoint 1 (where YOUR content needs it)**: what layout change triggers and why?\n"
            "- **Breakpoint 2**: the next content-driven shift\n"
            "- **Desktop (1024px+)**: the full layout with all columns and features\n"
            "- **Wide (1440px+)**: what happens with extra space? Don't just center a narrow column.\n"
            "- Navigation pattern per breakpoint: bottom tabs, hamburger, side rail, top nav?\n"
            "- Specify exact values: column counts, padding, font sizes, component sizes per breakpoint\n\n"
            "### 8. Page States\n"
            "Design the page in these states:\n"
            "- **Loading**: skeleton layout matching the real layout structure\n"
            "- **Empty**: first-time user, no data. This is an onboarding opportunity.\n"
            "- **Partial**: some sections have data, others don't\n"
            "- **Populated**: the happy path with realistic data\n"
            "- **Error**: what happens when a section fails to load? Partial degradation.\n"
            "- **Offline**: if applicable, what's available without network?\n\n"
            "### 9. Page Transitions\n"
            "- How does this page enter? (From which direction? Fade? Slide? Instant?)\n"
            "- How does it exit to the next likely destination?\n"
            "- Are there in-page transitions (tab switches, accordion opens, filter changes)?\n"
            "- Scroll behavior: any scroll-driven animations? Sticky elements? Parallax (use sparingly)?\n\n"
            "### 10. Wireframe Specification\n"
            "Produce a text-based wireframe showing:\n"
            "- Every section with exact spacing values in pixels\n"
            "- Component placement within grid areas\n"
            "- Font sizes, weights, and colors for all text elements\n"
            "- Background colors for each section\n"
            "- The complete visual hierarchy, readable as a blueprint"
        )

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
            model=self.get_model(agent, "design_page"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    # ------------------------------------------------------------------
    # design_system
    # ------------------------------------------------------------------

    def _execute_design_system(self, agent: Agent, task: AgentTask) -> str:
        """Define or extend the project's design system."""
        from agents.ai.claude_client import call_claude

        suffix = (
            "Define or extend the project's design system. Output a comprehensive .impeccable.md "
            "context file that serves as the single source of truth for all design decisions.\n\n"
            "## Methodology\n\n"
            "### 1. Design System Audit (if extending)\n"
            "If a design system already exists:\n"
            "- Review all existing tokens, components, and patterns\n"
            "- Identify gaps, inconsistencies, and drift from the original intent\n"
            "- Note what works well and should be preserved\n"
            "- Flag deprecated patterns that need migration paths\n\n"
            "### 2. Type Scale\n"
            "Define a complete typographic system:\n"
            "- **Font stack**: primary (headings), secondary (body), mono (code). Choose fonts with character.\n"
            "- **Scale ratio**: pick one (1.2 minor third, 1.25 major third, 1.333 perfect fourth) and commit.\n"
            "- **Scale steps**: from --text-xs to --text-6xl, each step computed from the ratio.\n"
            "- **Fluid sizing**: every step uses clamp(min, preferred, max). Example:\n"
            "  --text-base: clamp(1rem, 0.875rem + 0.5vw, 1.125rem)\n"
            "- **Line heights**: tighter for headings (1.1-1.2), comfortable for body (1.5-1.6).\n"
            "- **Letter spacing**: negative for large headings, positive for small caps.\n"
            "- **Font weights**: define semantic weight tokens (--font-normal, --font-medium, "
            "--font-semibold, --font-bold). Not every weight needs to exist.\n"
            "- **Measure**: max line length for prose (60-75ch).\n\n"
            "### 3. Color System\n"
            "Build an OKLCH-based color system:\n"
            "- **Brand colors**: 1-2 hues that define the brand identity. Define as OKLCH.\n"
            "- **Neutral palette**: TINTED neutrals (not pure gray). 10 steps from near-white to near-black,\n"
            "  each carrying a hint of the brand hue. Example:\n"
            "  --neutral-50: oklch(0.985 0.005 250)\n"
            "  --neutral-900: oklch(0.15 0.01 250)\n"
            "- **Accent palette**: 10 steps of the primary brand hue.\n"
            "- **Semantic colors**: success, warning, error, info -- each with 3-5 steps (bg, text, border).\n"
            "- **60-30-10 distribution**: document which colors fill which role.\n"
            "- **Dark mode**: NOT inverted colors. Reduce chroma, adjust lightness curves, "
            "  avoid pure black backgrounds (use oklch(0.15 0.01 250) instead).\n"
            "- **Contrast matrix**: verify all text/bg combinations meet WCAG AA.\n\n"
            "### 4. Spacing Scale\n"
            "4pt base grid:\n"
            "- Define named tokens: --space-1 (4px) through --space-16 (64px) and beyond.\n"
            "- Document when to use each: --space-1 for tight internal gaps, --space-4 (16px) for "
            "  standard padding, --space-8 (32px) for section gaps, --space-16 (64px) for major sections.\n"
            "- Fluid spacing with clamp() for responsive contexts.\n"
            "- Negative space guidelines: when to use generous whitespace for emphasis.\n\n"
            "### 5. Elevation & Depth System\n"
            "Layered shadow system:\n"
            "- **Level 0**: flat (no shadow, border only)\n"
            "- **Level 1**: subtle lift (cards, dropdowns): 0 1px 2px oklch(0 0 0 / 0.04), "
            "  0 2px 4px oklch(0 0 0 / 0.06)\n"
            "- **Level 2**: moderate lift (popovers, sticky headers)\n"
            "- **Level 3**: high lift (modals, drawers)\n"
            "- **Level 4**: maximum lift (toasts, tooltips)\n"
            "- Consistent light source direction (top-left).\n"
            "- Dark mode shadow adjustments (darker, less spread).\n\n"
            "### 6. Border Radius System\n"
            "- Define radius tokens: --radius-sm, --radius-md, --radius-lg, --radius-xl, --radius-full.\n"
            "- Rule: nested elements use inner-radius = outer-radius minus gap.\n"
            "- Which components use which radius (buttons, cards, inputs, avatars, modals).\n\n"
            "### 7. Component Library Inventory\n"
            "Catalog all components the system needs:\n"
            "- Primitives: Button, Input, Select, Checkbox, Radio, Toggle, Textarea\n"
            "- Layout: Container, Stack, Grid, Divider, Spacer\n"
            "- Navigation: Tabs, Breadcrumb, Sidebar, NavBar, Pagination\n"
            "- Feedback: Alert, Toast, Badge, Progress, Skeleton, Spinner\n"
            "- Overlay: Modal, Drawer, Popover, Tooltip, Dropdown\n"
            "- Data: Table, Card, List, Avatar, Tag\n"
            "- For each: list variants, sizes, and which design tokens it uses.\n\n"
            "### 8. Motion Principles\n"
            "- Define the three timing tiers: micro (100ms), standard (300ms), dramatic (500ms).\n"
            "- Default easing curves for each tier.\n"
            "- Stagger formula for lists.\n"
            "- Enter/exit patterns for overlays.\n"
            "- prefers-reduced-motion strategy.\n\n"
            "### 9. Dark Mode Strategy\n"
            "- Document the exact approach: semantic tokens that swap, not a CSS filter.\n"
            "- Lightness inversion rules: light bg becomes dark, dark text becomes light, "
            "  but chroma DECREASES in dark mode.\n"
            "- Image handling: reduce brightness/contrast in dark mode?\n"
            "- Shadow adjustments: darker ambient, less spread.\n"
            "- Which elements change, which stay constant.\n\n"
            "### 10. Output Format\n"
            "Produce a complete .impeccable.md file with:\n"
            "- All tokens as CSS custom properties\n"
            "- Usage guidelines for each category\n"
            "- DO/DON'T examples\n"
            "- Component spec outlines\n"
            "- Figma-to-code mapping notes if applicable"
        )

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
            model=self.get_model(agent, "design_system"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    # ------------------------------------------------------------------
    # critique
    # ------------------------------------------------------------------

    def _execute_critique(self, agent: Agent, task: AgentTask) -> str:
        """Review existing UI against Impeccable Style guidelines."""
        from agents.ai.claude_client import call_claude

        suffix = (
            "Review the existing UI against the Impeccable Style guidelines. Every finding "
            "must be ACTIONABLE -- no vague criticism without a specific fix.\n\n"
            "## Methodology\n\n"
            "### 1. AI Slop Test (Pass/Fail)\n"
            "Run the AI Slop checklist first. This is binary -- the UI either passes or fails:\n"
            "- Does it look like a template? Would swapping the logo make it unrecognizable?\n"
            "- Are the fonts generic (Inter, Roboto, system defaults)?\n"
            "- Is the color palette just blue + gray?\n"
            "- Are all corner radii identical? All spacings uniform? All cards the same?\n"
            "- Are hover states just opacity/darkness changes?\n"
            "- Could this be any SaaS product's dashboard?\n"
            "- Score: PASS or FAIL with specific evidence.\n\n"
            "### 2. Nielsen's 10 Heuristics (0-4 scale each)\n"
            "Score each heuristic and provide evidence:\n"
            "- **Visibility of system status** (0-4): Does the user always know what's happening?\n"
            "- **Match between system and real world** (0-4): Does it speak the user's language?\n"
            "- **User control and freedom** (0-4): Can users undo, go back, escape?\n"
            "- **Consistency and standards** (0-4): Does it follow platform conventions?\n"
            "- **Error prevention** (0-4): Does it prevent errors before they happen?\n"
            "- **Recognition rather than recall** (0-4): Is information visible, not memorized?\n"
            "- **Flexibility and efficiency of use** (0-4): Are there shortcuts for experts?\n"
            "- **Aesthetic and minimalist design** (0-4): Is every element necessary?\n"
            "- **Error recovery** (0-4): Are error messages helpful and specific?\n"
            "- **Help and documentation** (0-4): Is help available in context?\n"
            "- Total score out of 40 with letter grade.\n\n"
            "### 3. Cognitive Load Assessment\n"
            "Evaluate three types of cognitive load:\n"
            "- **Intrinsic load**: complexity inherent in the task. Is the UI making a simple task "
            "feel complex? Or is it appropriately complex for a complex task?\n"
            "- **Extraneous load**: unnecessary complexity from BAD DESIGN. Visual clutter, "
            "inconsistent patterns, unclear labels, unnecessary steps, confusing navigation.\n"
            "  List every source of extraneous load with a fix.\n"
            "- **Germane load**: productive mental effort. Is the UI helping users build mental "
            "models? Good progressive disclosure, clear grouping, meaningful patterns.\n\n"
            "### 4. Persona Testing\n"
            "Walk through the UI as 5 different personas:\n"
            "- **Power User**: someone who uses this daily. Where are the efficiency gaps? "
            "Missing keyboard shortcuts? Unnecessary confirmation dialogs? Too many clicks?\n"
            "- **New User**: first time seeing this. What's confusing? Where would they get stuck? "
            "What's the time-to-value? Is the onboarding adequate?\n"
            "- **Accessibility-Dependent User**: screen reader, keyboard-only, low vision, "
            "color blind. Run through WCAG 2.1 AA checklist: contrast, focus indicators, "
            "ARIA labels, keyboard navigation, text alternatives.\n"
            "- **Stressed/Rushing User**: time pressure, distracted. Can they accomplish the "
            "primary task in under 30 seconds? Are error paths forgiving? Is critical info "
            "immediately visible without scrolling?\n"
            "- **Non-Native Speaker**: is the language clear and simple? Are icons and labels "
            "unambiguous across cultures? Is there jargon that could confuse?\n\n"
            "### 5. Specific Violations\n"
            "For each finding, provide:\n"
            "- **What**: the specific element or pattern that violates guidelines\n"
            "- **Where**: exact location in the UI\n"
            "- **Why it matters**: which principle/heuristic it violates and the user impact\n"
            "- **Fix**: the specific design change to make, with exact values where possible "
            "(e.g., 'Change text color from oklch(0.5 0 0) to oklch(0.3 0.01 250) for 4.5:1 contrast')\n"
            "- **Priority**: P0 (broken/inaccessible), P1 (significant UX issue), "
            "P2 (polish issue), P3 (nice-to-have)\n\n"
            "### 6. Summary Scorecard\n"
            "End with:\n"
            "- AI Slop Test: PASS/FAIL\n"
            "- Nielsen's Heuristics: X/40 (letter grade)\n"
            "- Cognitive Load: Low/Medium/High extraneous load\n"
            "- Accessibility: WCAG AA compliant? Yes/No/Partial\n"
            "- Top 3 highest-impact fixes (the 20% effort that gets 80% improvement)\n"
            "- Overall assessment: Ship it / Needs work / Needs redesign"
        )

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
            model=self.get_model(agent, "critique"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    # ------------------------------------------------------------------
    # polish
    # ------------------------------------------------------------------

    def _execute_polish(self, agent: Agent, task: AgentTask) -> str:
        """Refine a working but rough implementation."""
        from agents.ai.claude_client import call_claude

        suffix = (
            "Take this working implementation and refine it to production-grade quality. "
            "The functionality is correct -- now make it FEEL crafted.\n\n"
            "## Methodology\n\n"
            "### 1. Typography Polish\n"
            "- **Vertical rhythm audit**: is all text sitting on a consistent baseline grid? "
            "Adjust line-heights and margins to align.\n"
            "- **Font pairing**: are the fonts well-paired? Do they create contrast (geometric + humanist, "
            "sans + serif)? If using a single family, is weight variation creating enough hierarchy?\n"
            "- **Fluid sizing review**: are font sizes using clamp() for smooth scaling? "
            "Check at 320px, 768px, 1440px -- do all sizes feel intentional at every width?\n"
            "- **Measure check**: is prose text within 60-75ch per line? Adjust max-width if needed.\n"
            "- **Orphan/widow control**: specify text-wrap: balance for headings, text-wrap: pretty for prose.\n"
            "- **Detail check**: letter-spacing on headings (tighten), small caps (loosen), "
            "font-variant-numeric: tabular-nums for data.\n\n"
            "### 2. Color Refinement\n"
            "- **Tinted neutrals**: replace any pure grays with brand-tinted OKLCH neutrals. "
            "Even a 0.005 chroma with the brand hue makes a difference.\n"
            "- **Contrast verification**: check every text/background pair. Fix any below 4.5:1 for normal text.\n"
            "- **60-30-10 balance**: is the color distribution correct? Too much accent? Not enough?\n"
            "- **Dark mode harmony**: if dark mode exists, verify chroma is reduced, "
            "backgrounds aren't pure black, and text isn't pure white.\n"
            "- **Semantic consistency**: do success/warning/error colors match across all components?\n"
            "- **Depth through color**: are background layers at slightly different lightness values "
            "to create subtle depth without shadows?\n\n"
            "### 3. Spacing Rhythm\n"
            "- **Break monotony**: find any sequences of equal spacing and introduce intentional variation. "
            "Tight within groups (8-12px), breathing room between groups (24-48px), "
            "generous between sections (48-96px).\n"
            "- **Group related elements**: elements that belong together should be visually closer. "
            "Label-to-input gap should be smaller than input-to-next-label gap.\n"
            "- **Separate distinct sections**: increase spacing between conceptually different areas.\n"
            "- **Responsive spacing**: are spacing values scaling smoothly? Use clamp() for fluid gaps.\n"
            "- **Padding asymmetry where appropriate**: more vertical padding than horizontal on cards "
            "creates a more refined feel. Top padding can differ from bottom.\n\n"
            "### 4. Micro-Interactions\n"
            "- **State transitions**: every hover, focus, and active state should have a smooth transition. "
            "Specify: transition: color 100ms ease-out, box-shadow 200ms ease-out.\n"
            "- **Loading states**: replace any generic spinners with skeleton screens that match "
            "the actual content layout. Shimmer animation: background-position shift over 1.5s.\n"
            "- **Focus indicators**: every focusable element needs a visible, attractive focus ring. "
            "Not the browser default -- a 2px ring in the accent color with 2px offset.\n"
            "- **Button feedback**: buttons should respond to press (slight scale-down: transform: scale(0.98)), "
            "not just hover.\n"
            "- **Form validation**: smooth error state entrance (fade + slide, 200ms), "
            "immediate success feedback (check icon, color change).\n"
            "- **Scroll-aware elements**: should anything change on scroll? Sticky header shrink, "
            "scroll progress indicator, fade-in on viewport entry?\n\n"
            "### 5. Visual Details\n"
            "- **Shadow refinement**: replace single-layer shadows with layered shadows for realism. "
            "Add a subtle ambient shadow + a direct shadow.\n"
            "- **Border treatment**: review all borders. Are they too heavy? Too prominent? "
            "Use oklch(0 0 0 / 0.06) for subtle dividers, slightly stronger for interactive element borders.\n"
            "- **Decorative elements**: are there any that reinforce the brand rather than being generic? "
            "A subtle pattern, a brand-colored accent line, a distinctive shape motif?\n"
            "- **Icon consistency**: are all icons from the same family? Same stroke width? Same optical size?\n"
            "- **Image handling**: proper aspect-ratio, object-fit: cover, loading='lazy', "
            "subtle border-radius on images in content areas.\n"
            "- **Cursor styles**: pointer on clickables, text on editables, grab on draggables, "
            "not-allowed on disabled.\n\n"
            "### 6. Output Format\n"
            "Produce a polish specification document:\n"
            "- **Change list**: every refinement, organized by category (typography, color, spacing, "
            "motion, details)\n"
            "- **Before/After**: for each change, specify the current value and the new value\n"
            "- **Token updates**: any new or modified design tokens\n"
            "- **Priority order**: which changes have the most visual impact? Implement those first.\n"
            "- **Estimated effort**: quick wins (< 5 min each) vs. larger refactors"
        )

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
            model=self.get_model(agent, "polish"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
