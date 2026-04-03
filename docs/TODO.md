# TODO — Future Improvements

## Context Efficiency
- `build_context_message()` dumps up to 3000 chars per department document + 10 recent tasks with 200-char reports. For departments with many docs/tasks, this eats input tokens. Consider summarizing context with a cheaper model (e.g. Haiku) rather than raw-dumping full text.

## Bootstrap Source Handling
- `build_bootstrap_user_message()` sends up to 10K chars per source. Instead of truncating, summarize each source with a cheaper model first, then feed summaries to the bootstrap prompt.

## Multi-tenancy
- Redis is a single instance for broker, cache, and channels. When going multi-tenant, consider separate Redis instances or Redis Cluster. Add this as a requirement when multi-tenancy is designed.

## Agent Config Security
- `agent.config` JSONField stores sensitive data (browser cookies, auth tokens). Currently visible to all admin users. When the frontend API is built, ensure this field is write-only in serializers.

## Prompt Injection Hardening (before multi-tenant / frontend)

Current mitigation: XML tags around user-controlled content in all prompts. Still needed:

- **Source URL content scanning** — `extract_from_url` fetches external HTML that flows into bootstrap. Scan/strip content that looks like prompt injection before storing extracted_text. This is the only vector that exists TODAY (attacker doesn't need an account, just a URL someone pastes as a source).
- **Bootstrap proposal schema validation** — validate Claude's JSON response against a strict schema (only known department_types, only known agent_types per department) before `_apply_proposal` creates objects. Currently validated at the department/agent level but not at the JSON structure level.
- **Rate limiting on Claude calls** — prevent a user from generating unlimited bootstrap proposals or task proposals. Add per-user/per-project rate limits on bootstrap_project and create_next_leader_task.
- **Audit logging** — log every prompt sent to Claude (system + user message) with timestamp, user, agent, and token usage. Searchable for post-incident review.
- **Output validation** — verify Claude's JSON responses match expected structure strictly before acting on them. Reject responses with unexpected keys or values.
- **Task report feedback loop** — Claude's own output (task reports) gets fed back as context for future tasks. A hallucinated instruction in a report could self-reinforce. Consider summarizing/sanitizing reports before including in context, or capping context to most recent N tasks.
- **Agent instructions field** — when frontend ships, either restrict to plain text (no markdown headers, no instruction-like patterns) or make it a structured form instead of free text.
