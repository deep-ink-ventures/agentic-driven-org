"""Webhook adapter registry."""

WEBHOOK_ADAPTERS = {}


def register_adapter(adapter_class):
    WEBHOOK_ADAPTERS[adapter_class.slug] = adapter_class()


def get_adapter(slug):
    return WEBHOOK_ADAPTERS.get(slug)


from integrations.webhooks.adapters.github import GitHubWebhookAdapter
register_adapter(GitHubWebhookAdapter)
