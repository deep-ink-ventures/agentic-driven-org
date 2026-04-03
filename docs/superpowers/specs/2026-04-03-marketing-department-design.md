# Marketing Department — Design Spec

## Overview

Replace the `social_media` department with a comprehensive `marketing` department. Five workforce agents + one leader that orchestrates multi-channel campaigns, schedules follow-ups, and coordinates across research, social, and email channels.

## Integration Services Layer

Agents never interact with APIs or secrets directly. Each external system has its own service in `integrations/` with a clean interface.

```
integrations/
├── playwright/service.py    # Browser automation — Twitter, Reddit, Lu.ma
├── websearch/service.py     # Wraps web search for consistency
├── sendgrid/service.py      # Email campaigns, mailing lists
├── gmail/service.py         # Google Workspace Gmail API
├── gdrive/service.py        # Google Drive API
└── luma/service.py          # Lu.ma calendar queries (via Playwright internally)
```

### Service interfaces

**websearch/service.py**
- `search(query, num_results=10) -> list[dict]` — returns `[{title, url, snippet}]`

**luma/service.py** (uses Playwright internally)
- `query_events(calendar_urls, days_ahead=30) -> list[dict]` — returns `[{title, url, date, description, speakers}]`
- `get_event_details(event_url) -> dict`

**playwright/service.py** (generic browser automation)
- `run_action(action_type, params, agent_config) -> dict`

**sendgrid/service.py**
- `send_campaign(api_key, from_email, to_list_id, subject, html_body) -> dict`
- `get_campaign_stats(api_key, campaign_id) -> dict`
- `list_contacts(api_key, list_id) -> dict`

**gmail/service.py** (existing, update interface)
- `send_email(project, to, subject, body) -> dict`
- `read_emails(project, query, max_results) -> dict`

**gdrive/service.py** (existing, update interface)
- `list_files(project, folder_id, max_results) -> dict`

Secrets are read from `ProjectConfig.google_credentials` (for Gmail/Drive), `agent.config` (for per-agent credentials like Reddit sessions, SendGrid keys, Lu.ma calendar URLs).

## Blueprint Structure

```
blueprints/
├── __init__.py
├── base.py
└── marketing/
    ├── __init__.py
    ├── leader/
    │   ├── __init__.py
    │   ├── agent.py
    │   ├── skills/
    │   │   ├── __init__.py
    │   │   ├── analyze_performance.py
    │   │   ├── design_campaigns.py
    │   │   ├── content_calendar.py
    │   │   └── prioritize_tasks.py
    │   └── commands/
    │       ├── __init__.py
    │       ├── create_priority_task.py
    │       ├── create_campaign.py
    │       ├── create_content_calendar.py
    │       └── analyze_performance.py
    └── workforce/
        ├── web_researcher/
        │   ├── __init__.py
        │   ├── agent.py
        │   ├── skills/
        │   │   ├── __init__.py
        │   │   ├── search_trends.py
        │   │   ├── research_competitors.py
        │   │   └── find_opportunities.py
        │   └── commands/
        │       ├── __init__.py
        │       ├── research_trends.py
        │       ├── research_competitors.py
        │       └── find_content_opportunities.py
        ├── luma_researcher/
        │   ├── __init__.py
        │   ├── agent.py
        │   ├── skills/
        │   │   ├── __init__.py
        │   │   ├── query_calendars.py
        │   │   ├── extract_event_details.py
        │   │   └── identify_opportunities.py
        │   └── commands/
        │       ├── __init__.py
        │       ├── scan_events.py
        │       └── find_opportunities.py
        ├── reddit/
        │   ├── __init__.py
        │   ├── agent.py
        │   ├── skills/
        │   │   ├── __init__.py
        │   │   ├── find_trending_posts.py
        │   │   ├── strategic_placement.py
        │   │   └── monitor_mentions.py
        │   └── commands/
        │       ├── __init__.py
        │       ├── place_content.py
        │       ├── post_content.py
        │       └── monitor_mentions.py
        ├── twitter/
        │   ├── __init__.py
        │   ├── agent.py
        │   ├── skills/
        │   │   ├── __init__.py
        │   │   ├── find_trending_tweets.py
        │   │   ├── strategic_placement.py
        │   │   └── post_content.py
        │   └── commands/
        │       ├── __init__.py
        │       ├── place_content.py
        │       ├── post_content.py
        │       └── search_trends.py
        └── email_marketing/
            ├── __init__.py
            ├── agent.py
            ├── skills/
            │   ├── __init__.py
            │   ├── design_campaigns.py
            │   ├── segment_audience.py
            │   ├── schedule_sends.py
            │   └── analyze_performance.py
            └── commands/
                ├── __init__.py
                ├── check_campaign_performance.py
                ├── draft_campaign.py
                └── send_campaign.py
```

## Workforce Agents

### 1. Web Researcher (`web_researcher`)

**Tags:** `research`, `intelligence`, `trends`
**Integration:** `websearch` service
**Config:** none

**Skills:**
- Search Google for industry trends
- Research competitors
- Find relevant news and articles
- Analyze search results for opportunities

**Commands:**
- `research-trends` (hourly) — scan for trending topics in the project's domain. Returns top findings with URLs and relevance assessment.
- `research-competitors` (daily) — check competitor activity and recent developments.
- `find-content-opportunities` (on-demand) — deep-dive research for content ideas, angles, and hooks.

**System prompt emphasis:** Return structured findings with URLs, relevance scores, and suggested angles. Always connect findings back to the project goal.

### 2. Lu.ma Researcher (`luma_researcher`)

**Tags:** `research`, `events`, `networking`
**Integration:** `luma` service
**Config:** `{"calendar_urls": ["https://lu.ma/calendar/...", ...]}`

**Skills:**
- Query Lu.ma calendars for upcoming events
- Extract event details (speakers, topics, dates)
- Identify networking and speaking opportunities
- Track industry event landscape

**Commands:**
- `scan-events` (daily) — check configured calendars for new/upcoming events. Flag events relevant to the project.
- `find-opportunities` (on-demand) — deep search for events matching project goals (speaking, sponsoring, attending).

**System prompt emphasis:** Focus on events where the project can gain visibility. Report event timing, audience, and relevance to the project goal.

### 3. Reddit Specialist (`reddit`)

**Tags:** `social-media`, `reddit`, `placement`, `brand-visibility`
**Integration:** `playwright` service
**Config:** `{"reddit_username": "...", "reddit_session": "..."}`

**Skills:**
- Find high-performing posts in relevant subreddits
- Place strategic content on trending posts — one well-crafted comment that angles toward the project (drives traffic, recommends an event, shares a relevant link)
- Post valuable original content in appropriate subreddits
- Monitor brand/keyword mentions

**Commands:**
- `place-content` (hourly) — find the single highest-performing post in the project's niche. Add one post with a strategic angle that drives value toward the project. No discussions, no replies to replies, no debates. One placement, then move on.
- `post-content` (daily) — share one valuable piece of content in an appropriate subreddit. Aligned with current campaign messaging.
- `monitor-mentions` (on-demand) — scan for brand/project mentions.

**Key behavioral rules (baked into system prompt):**
- NEVER engage in discussions or answer questions
- NEVER reply to replies on your own posts
- ONE post per high-performing thread, then move on
- Content must provide genuine value while angling toward the project
- Track `last_post_at` per subreddit in `internal_state` — minimum 4 hours between posts in same subreddit
- Aware of current campaigns — placement should align with campaign messaging

### 4. Twitter Specialist (`twitter`)

**Tags:** `social-media`, `twitter`, `placement`, `content-creation`
**Integration:** `playwright` service
**Config:** `{"twitter_session": "..."}`

**Skills:**
- Find high-performing tweets in the project's domain
- Place strategic content — one reply or quote tweet on trending content that angles toward the project
- Post original tweets aligned with project voice
- Post threads for in-depth content

**Commands:**
- `place-content` (hourly) — find trending tweet in the niche. Add one strategic reply or quote tweet with a hook that drives to the project. No conversations, no back-and-forth.
- `post-content` (daily) — post one original tweet. Optimized for best posting time (stored in `internal_state`).
- `search-trends` (on-demand) — research trending hashtags and topics for opportunities.

**Key behavioral rules (baked into system prompt):**
- NEVER engage in conversations or reply chains
- ONE placement per trending tweet, then move on
- Content must add value — not just "great post!" or generic replies
- Track `last_tweet_at`, `tweets_today` in `internal_state`
- Know optimal posting times for the project's audience
- Aware of current campaigns — all posts should be on-message

### 5. Email Marketing Specialist (`email_marketing`)

**Tags:** `email`, `campaigns`, `outreach`, `nurture`
**Integration:** `sendgrid` service
**Config:** `{"sendgrid_api_key": "...", "default_from_email": "...", "mailing_lists": {"newsletter": "list-id-1", "leads": "list-id-2"}}`

**Skills:**
- Design email campaigns (subject lines with A/B options, body, CTA)
- Target the right mailing list for each campaign
- Schedule sends for optimal delivery times
- Create email sequences (onboarding, nurture, product launch, event)
- Analyze campaign performance (opens, clicks, unsubscribes)

**Commands:**
- `check-campaign-performance` (daily) — review recent campaign metrics. Report opens/clicks/unsubscribes. Flag issues.
- `draft-campaign` (on-demand) — create a full campaign draft: subject (with 2-3 A/B options), body HTML, CTA, target list, suggested send time. Created as a task awaiting approval — NEVER auto-sent.
- `send-campaign` (on-demand) — execute an approved campaign via SendGrid. Only runs after explicit approval.

**Key behavioral rules (baked into system prompt):**
- NEVER send emails without approval. Draft commands always create tasks in `awaiting_approval`.
- Track `last_campaign_sent_at`, `emails_sent_this_week` in `internal_state`
- Minimum 3 days between campaigns to the same list
- Include unsubscribe link in all campaigns
- Subject lines must include A/B options
- Aware of best send times (data suggests Tuesday/Thursday 10am local)

## Leader Agent

**Marketing Leader** (`leader`)
**Tags:** `leadership`, `strategy`, `campaigns`, `coordination`
**Integration:** none (delegates to workforce)

**Skills:**
- Analyze department activity and performance
- Gather intelligence from research agents (Web, Lu.ma)
- Design multi-channel campaigns with consistent branding and timing
- Create content calendars
- Prioritize tasks based on ROI and project goal
- Schedule future follow-up tasks for campaign continuity

**Commands:**

- `create-priority-task` (hourly) — analyze all workforce activity. Consider recent research findings, event calendar, campaign status, and engagement metrics. Propose the single highest-value next action for any workforce agent. Include clear branding and tone instructions in the task.

- `create-campaign` (on-demand) — design a multi-channel campaign. This is the core orchestration flow:
  1. Create research tasks for Web Researcher and Lu.ma Researcher (auto-execute)
  2. Synthesize research findings
  3. Create coordinated execution tasks for Reddit, Twitter, Email with:
     - Consistent messaging and branding across all channels
     - Channel-appropriate tone (professional for email, casual for Twitter, value-add for Reddit)
     - Specific timing for each channel (not all at once — staggered for maximum impact)
     - Clear instructions about what angle to take and what to link to
  4. Schedule a follow-up task for the leader itself (e.g. "Revisit rooftop campaign in 30 days" using `proposed_exec_at`) to assess performance and adjust

- `create-content-calendar` (on-demand) — plan a week of coordinated content across all channels. Output: day-by-day schedule with specific content briefs for each agent.

- `analyze-performance` (on-demand) — compile reports from all agents' recent task reports, identify what's working, flag underperformers, suggest strategy adjustments.

**Campaign lifecycle** (all within a single project):
1. Exec gives leader a task: "Promote the new rooftop bar"
2. Leader designs campaign within the existing project context (project goal: "increase bookings")
3. Leader creates phased tasks with scheduled execution dates
4. Leader schedules a self-reminder to revisit in 30 days
5. When the 30-day task fires, leader reviews what happened and creates follow-up tasks
6. No new project needed — campaigns are task chains within the project

## Proposed Improvements & Additional Agents (Future)

### Additional agents to consider:

- **LinkedIn Specialist** — B2B engagement, professional content. Same pattern as Twitter/Reddit: strategic placement, not conversation. Uses Playwright.
- **SEO Analyst** — keyword research, content gap analysis, on-page optimization recommendations. Uses `websearch` service. Could suggest blog post topics to the Content Writer.
- **Content Writer** — long-form content (blog posts, case studies, landing pages). Different from social agents that do short-form. Creates drafts for approval.
- **Analytics Reporter** — pulls data from connected platforms (SendGrid stats, Google Analytics if connected), generates performance dashboards. Feeds data back to the leader.
- **Community Manager** — monitors all channels for brand mentions, compiles daily digest. Unlike the engagement agents, this one IS allowed to respond to direct questions/complaints (with approval).

### Flow improvements to consider:

- **Campaign templates** — leader can reference past successful campaigns as templates for new ones. Store completed campaign structures in documents.
- **A/B testing coordination** — leader creates variant tasks ("post A on Tuesday, post B on Thursday") and tracks which performs better.
- **Cross-department intelligence** — if an Engineering department exists, its agents could feed product updates to the Marketing leader for campaign material.
- **Approval delegation** — trusted commands (like research tasks) could auto-approve while risky ones (email blasts, social posts) always require human approval. Already partially supported via `auto_actions`.
- **Performance-driven scheduling** — agents learn optimal posting times from their `internal_state` rather than using hardcoded defaults.

## Migration from social_media

1. Delete `blueprints/social_media/` entirely
2. Create `blueprints/marketing/` with new structure
3. Update `DEPARTMENTS` registry in `blueprints/__init__.py`
4. Migration: rename `department_type='social_media'` to `'marketing'` in existing departments
5. Migration: map existing agents (`twitter` stays, `reddit` stays, remove agents with unknown types)
6. Update bootstrap prompt and tests
7. Create all new integration services
8. Update existing `integrations/browser.py` → `integrations/playwright/service.py`
9. Split existing `integrations/google.py` → `integrations/gmail/service.py` + `integrations/gdrive/service.py`

## Scope

**In scope:**
- Full marketing department blueprint (leader + 5 workforce agents)
- All skills and commands for each agent
- Integration services: websearch, luma, playwright, sendgrid, gmail, gdrive
- Migration from social_media → marketing
- Updated registry and bootstrap prompt

**Out of scope:**
- LinkedIn, SEO, Content Writer, Analytics agents (future)
- Campaign templates system
- A/B testing coordination
- Cross-department intelligence
- Frontend UI for campaign management
