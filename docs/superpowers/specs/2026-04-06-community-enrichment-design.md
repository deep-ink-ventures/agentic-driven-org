# Community Department Enrichment — Design Spec

**Date:** 2026-04-06

## Goal

Enrich the Community department's existing agents with deeper methodology extracted from knowledge-work-plugins (sales skills), adapted for ecosystem/partnership context. No new agents. No architectural changes. Just richer prompts.

## Scope

Three changes:

1. **Ecosystem Researcher** — Enrich with account-research methodology (systematic research execution)
2. **Partnership Writer** — Enrich with draft-outreach methodology (personalization, hooks, anti-patterns)
3. **Community Leader** — Add `monitor-ecosystem` scheduled command for ongoing ecosystem intelligence

Agents left unchanged: **Ecosystem Analyst**, **Partnership Reviewer** (already strong reviewers with clear rubrics and 9.5/10 thresholds).

---

## 1. Ecosystem Researcher Enrichment

**Source:** `knowledge-work-plugins/sales/skills/account-research/SKILL.md`

### 1.1 Skills (add to `skills` list)

Add two new skills alongside the existing three:

```python
{
    "name": "Systematic Web Research",
    "description": (
        "Execute structured multi-query research for each entity: "
        "[entity] overview, [entity] news, [entity] funding/growth, "
        "[entity] leadership, [entity] partnerships, [entity] events, "
        "[entity] community/audience. Extract from each: positioning, "
        "recent activity (last 90 days), key people, growth signals, "
        "audience composition"
    ),
},
{
    "name": "Qualification Signals",
    "description": (
        "Classify signals for each entity: "
        "Positive (active community, recent events, growing team, "
        "complementary audience, open to partnerships). "
        "Concerns (dormant, shrinking, competitive overlap, "
        "exclusive existing partnerships). "
        "Unknown (flag for deeper research)"
    ),
},
```

### 1.2 System Prompt (extend, do not replace)

Append the following to the existing system prompt, after the JSON schema:

```
## Research Execution

For EACH entity you research, run these searches:
1. "[Entity name]" — homepage, about page, mission
2. "[Entity name] news" — announcements, press, blog (last 90 days)
3. "[Entity name] events" — hosted or sponsored events, meetups, conferences
4. "[Entity name] leadership OR team" — key people, founders, community managers
5. "[Entity name] partnerships OR sponsors" — existing collaborations
6. "[Entity name] community OR members OR audience" — size, composition, engagement

Extract from each search:
- What they do and who they serve (positioning)
- Recent activity and momentum (growing, stable, declining)
- Key people to contact (name, role, public presence)
- Existing partnerships (who they already work with)
- Audience composition and overlap with ours

## Qualification Signals

For each entity, classify:

### Positive Signals
- Active event calendar or content output
- Growing team (hiring signals)
- Complementary (not competitive) audience
- History of partnerships with orgs like ours
- Recent expansion or new initiatives

### Concerns
- Dormant (no activity in 90+ days)
- Exclusive partnerships that block us
- Competitive overlap (they offer what we offer)
- Shrinking presence or leadership turnover

### Unknown (flag for deeper research)
- Audience size/composition unclear
- Partnership openness unclear
- Decision-maker not identified
```

### 1.3 Task Suffix (extend, do not replace)

Append after the existing "Connection Mapping" section:

```
## Research Rigor
- Run at minimum 4 web searches per entity — do not profile from a single source
- For entities scoring 7+, run the full 6-search sequence
- Distinguish between verified facts and inferences — label accordingly
- Include sources: note which URLs provided which information
- Recency matters: flag any entity where the most recent activity is >6 months old

## Entity JSON Extension
For each entity, also include:
- "qualification_signals": {"positive": [...], "concerns": [...], "unknown": [...]}
- "sources": ["url1", "url2"]
- "last_active": "YYYY-MM or 'unknown'"
```

### 1.4 JSON Schema Extension

Extend the entity schema in `system_prompt`:

```json
{
    "name": "...",
    "type": "organization|community|event_series|influencer|business",
    "profile": "What they do and why they matter",
    "key_contacts": ["Name — Role — how found"],
    "audience_overlap": "How their audience connects to ours",
    "partnership_potential": "1-10",
    "partnership_angle": "Specific partnership idea",
    "recent_activity": "Most recent news, event, or content (with date)",
    "qualification_signals": {
        "positive": ["Signal with evidence"],
        "concerns": ["Concern with evidence"],
        "unknown": ["Gap to investigate"]
    },
    "existing_partnerships": ["Partner name — nature of partnership"],
    "sources": ["URL"],
    "last_active": "YYYY-MM or unknown"
}
```

---

## 2. Partnership Writer Enrichment

**Source:** `knowledge-work-plugins/sales/skills/draft-outreach/SKILL.md`

### 2.1 Skills (add to `skills` list)

Add three new skills alongside the existing three:

```python
{
    "name": "Hook Identification",
    "description": (
        "Identify the strongest personalization hook for each partner, "
        "in priority order: (1) trigger event — their recent news, launch, "
        "funding, expansion; (2) mutual connection — shared partners or "
        "community; (3) their content — recent post, talk, publication; "
        "(4) their initiative — announced program or goal; "
        "(5) role-based relevance — least personal but still grounded"
    ),
},
{
    "name": "Anti-Pattern Detection",
    "description": (
        "Avoid these in every proposal: generic openers ('I hope this finds "
        "you well', 'I wanted to reach out'), feature dumps (long paragraphs "
        "about us), fake personalization ('I noticed you work at [Company]' "
        "without depth), vague CTAs ('let's chat sometime'), one-sided framing "
        "(only describing what we gain)"
    ),
},
{
    "name": "Scenario Adaptation",
    "description": (
        "Adapt proposal tone and structure by scenario: "
        "Cold (no prior relationship) — lead with their trigger event + "
        "specific mutual value; "
        "Warm (met at event, mutual contact) — reference shared context; "
        "Re-engagement (prior conversation went cold) — acknowledge gap, "
        "bring new reason; "
        "Post-event (met at conference/meetup) — reference specific "
        "conversation, offer concrete follow-up"
    ),
},
```

### 2.2 System Prompt (extend, do not replace)

Append after the existing JSON schema:

```
## Hook Priority

Before drafting any proposal, identify the strongest personalization hook. In priority order:
1. **Trigger event** — their recent news, launch, funding, expansion, new hire (most timely)
2. **Mutual connection** — shared partners, community membership, co-attended events
3. **Their content** — recent blog post, talk, podcast, social media activity
4. **Their initiative** — announced program, community goal, strategic direction
5. **Role-based relevance** — least personal, but still grounded in their actual work

Always lead with the best available hook. Never draft without one.

## Proposal Structure (AIDA adapted for partnerships)

- **Attention**: Personal hook — shows you know them specifically
- **Interest**: Their opportunity — framed in terms of THEIR goals, not ours
- **Desire**: Mutual value — concrete, specific, measurable where possible
- **Action**: Clear, low-friction next step — one specific ask

## What NOT To Do

Never use these patterns:
- Generic openers: "I hope this email finds you well", "I'm reaching out because..."
- Feature dumps: long paragraphs about what we do
- Fake personalization: "I noticed you work at [Company]" without depth
- Vague CTAs: "Let's find time to chat", "Would love to connect sometime"
- One-sided framing: only describing what we gain from the partnership
- Template language: anything that reads like it could be sent to 100 orgs unchanged

Instead:
- Lead with something specific you learned about them
- One clear mutual value proposition
- One clear, specific ask
- Keep it scannable — short paragraphs, 2-3 sentences each
```

### 2.3 Task Suffix (extend, do not replace)

Append after the existing "Professional Tone" section:

```
## Scenario Templates

Adapt your approach based on relationship context:

### Cold (no prior relationship)
- Lead with trigger event or their recent activity
- 1 sentence on mutual audience/value overlap
- Brief proof: "We've partnered with [Similar Org] on [specific thing]"
- CTA: specific, low-commitment ("Would a 20-min call next week make sense to explore this?")

### Warm (met at event, mutual contact)
- Reference how you know them / who connected you
- Why reaching out now — their trigger
- Specific value you're proposing
- CTA: continue the conversation

### Re-engagement (prior conversation went cold)
- Acknowledge time passed without guilt-tripping
- New reason to reconnect — their news or our news
- Simple question to re-open dialogue

### Post-event (met at conference, meetup, community event)
- Reference specific conversation or shared experience
- Value-add: relevant resource, introduction, or insight
- Soft CTA for next conversation

## Follow-up Sequence

For every proposal, also draft:
- **Day 3 follow-up**: Short, new angle or additional value
- **Day 7 follow-up**: Different framing of the mutual value
- **Day 14 break-up**: Final attempt, graceful close

Include these in the JSON response under "follow_up_sequence".

## JSON Extension

Add to the proposal JSON:
- "hook": {"type": "trigger|mutual_connection|content|initiative|role", "detail": "..."}
- "scenario": "cold|warm|re_engagement|post_event"
- "follow_up_sequence": [{"day": 3, "body": "..."}, {"day": 7, "body": "..."}, {"day": 14, "body": "..."}]
```

---

## 3. Monitor-Ecosystem Command

**Purpose:** Ongoing ecosystem intelligence — the researcher currently only maps on demand. This adds a periodic scan for changes in previously researched entities.

### 3.1 New Command: `monitor-ecosystem`

**File:** `backend/agents/blueprints/community/leader/commands/monitor_ecosystem.py`

```python
"""Community leader command: periodic ecosystem monitoring."""

from agents.blueprints.base import command


@command(
    name="monitor-ecosystem",
    description=(
        "Weekly scan for ecosystem changes — new events, leadership changes, "
        "partnership announcements, funding news, or dormancy signals in "
        "previously researched entities. Flags changes and recommends actions: "
        "update research, draft proposal, or deprioritize."
    ),
    schedule="weekly",
    model="claude-sonnet-4-6",
)
def monitor_ecosystem(self, agent) -> dict:
    return {
        "exec_summary": "Scan ecosystem for changes since last research cycle",
        "step_plan": (
            "1. Retrieve previously researched entities from completed ecosystem research tasks\n"
            "2. For each high-potential entity (score 7+), search for recent news and activity\n"
            "3. Flag changes: new events, leadership changes, funding, partnerships, dormancy\n"
            "4. Classify each change as: opportunity (draft proposal), update (revise research), "
            "or deprioritize (lower score)\n"
            "5. Create follow-up tasks: research revision tasks for updated entities, "
            "proposal tasks for new opportunities\n"
            "6. Report ecosystem health: active entities, dormant entities, new opportunities"
        ),
    }
```

### 3.2 Register on Leader

Add to `CommunityLeaderBlueprint`:

```python
from agents.blueprints.community.leader.commands import monitor_ecosystem

# In the class:
monitor_ecosystem = monitor_ecosystem
```

Update `commands/__init__.py` to export `monitor_ecosystem`.

### 3.3 Leader System Prompt Extension

Add to the leader's responsibilities list:

```
6. Monitor ecosystem changes weekly — flag new opportunities, dormant entities, and partnership openings from ongoing intelligence
```

Add a new skill to the leader's `skills` list:

```python
{
    "name": "Ecosystem Intelligence",
    "description": (
        "Ongoing monitoring of researched entities for changes: new events, "
        "leadership moves, funding, partnership announcements, dormancy. "
        "Triggers research updates or new proposals based on signals."
    ),
},
```

---

## 4. Operationalization — First Campaign

Once enrichments are implemented, run the first community campaign:

### 4.1 Prerequisites

- Community department activated on a project
- All 5 agents enabled with auto-approve for scheduled commands
- `plan-community` (weekly) and `check-progress` (daily) and `monitor-ecosystem` (weekly) schedules active

### 4.2 First Run Sequence

1. **Manually trigger `plan-community`** — the leader will identify initial ecosystem categories to research based on the project's goals and industry
2. **Leader creates `map-ecosystem` tasks** for the researcher, one per category
3. **Researcher executes**, returns structured entity maps with qualification signals
4. **Analyst reviews** (auto-routed), scores research quality, flags gaps
5. **Researcher revises** if needed (ping-pong loop)
6. **Leader creates `draft-proposal` tasks** for the writer, targeting entities scored 7+
7. **Writer drafts**, using hook identification and scenario adaptation
8. **Reviewer reviews** (auto-routed), scores against mutual_value, specificity, tone, structure, next_steps
9. **Writer revises** if needed (ping-pong until 9.5/10 or max rounds)
10. **Weekly `monitor-ecosystem`** begins scanning for changes in researched entities

### 4.3 Initial Categories to Research (suggest to leader)

These depend on the project, but typical first-wave categories:

- Local tech communities and meetups
- Industry-specific organizations and associations
- Complementary service providers (non-competitive)
- Event series and conferences in the space
- Influencers and content creators in the niche

---

## Files Changed

| File | Change |
|------|--------|
| `community/workforce/ecosystem_researcher/agent.py` | Extend `skills`, `system_prompt`, `get_task_suffix` |
| `community/workforce/partnership_writer/agent.py` | Extend `skills`, `system_prompt`, `get_task_suffix` |
| `community/leader/agent.py` | Add `monitor_ecosystem` command, extend `skills`, extend `system_prompt` |
| `community/leader/commands/__init__.py` | Export `monitor_ecosystem` |
| `community/leader/commands/monitor_ecosystem.py` | **New file** — scheduled weekly command |

## Files NOT Changed

| File | Reason |
|------|--------|
| `community/workforce/ecosystem_analyst/agent.py` | Already strong reviewer with clear rubric |
| `community/workforce/partnership_reviewer/agent.py` | Already strong reviewer with 9.5/10 threshold |
| All command files except new `monitor_ecosystem.py` | Step plans remain adequate |

---

## Source Attribution

- Ecosystem researcher enrichment adapted from: `knowledge-work-plugins/sales/skills/account-research/SKILL.md` — systematic multi-query research execution, qualification signals framework
- Partnership writer enrichment adapted from: `knowledge-work-plugins/sales/skills/draft-outreach/SKILL.md` — hook prioritization, AIDA structure, anti-patterns, scenario templates, follow-up sequences
