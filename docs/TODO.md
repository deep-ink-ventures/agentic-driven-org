# TODO — Future Improvements

## Context Efficiency
- `build_context_message()` dumps up to 3000 chars per department document + 10 recent tasks with 200-char reports. For departments with many docs/tasks, this eats input tokens. Consider summarizing context with a cheaper model (e.g. Haiku) rather than raw-dumping full text.

## Bootstrap Source Handling
- `build_bootstrap_user_message()` sends up to 10K chars per source. Instead of truncating, summarize each source with a cheaper model first, then feed summaries to the bootstrap prompt.

## Multi-tenancy
- Redis is a single instance for broker, cache, and channels. When going multi-tenant, consider separate Redis instances or Redis Cluster. Add this as a requirement when multi-tenancy is designed.

## Agent Config Security
- `agent.config` JSONField stores sensitive data (browser cookies, auth tokens). Currently visible to all admin users. When the frontend API is built, ensure this field is write-only in serializers.
