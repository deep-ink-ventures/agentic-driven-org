"""Integration beat tasks."""

import logging
from collections import defaultdict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def monitor_pending_webhooks():
    """Every 5 minutes: check for pending webhook events that may have been missed."""
    from datetime import timedelta

    from django.utils import timezone

    from agents.models import Agent, AgentTask
    from integrations.webhooks import get_adapter

    now = timezone.now()
    stale_cutoff = now - timedelta(hours=2)

    agents = Agent.objects.filter(status="active").exclude(internal_state={})

    for agent in agents:
        pending = agent.internal_state.get("pending_webhook_events", [])
        if not pending:
            continue

        by_integration = defaultdict(list)
        for evt in pending:
            by_integration[evt.get("integration", "")].append(evt)

        updated = False
        remaining = []

        for integration_slug, events in by_integration.items():
            adapter = get_adapter(integration_slug)
            if not adapter:
                remaining.extend(events)
                continue

            config = {}
            for key in ["github_token", "github_repos"]:
                val = agent.get_config_value(key)
                if val:
                    config[key] = val

            completed = adapter.check_pending(events, config)
            completed_ids = {e.get("external_id") for e in completed}

            for evt in events:
                if evt.get("external_id") in completed_ids:
                    task_id = evt.get("task_id")
                    result = next((c for c in completed if c.get("external_id") == evt.get("external_id")), {})
                    if task_id:
                        try:
                            task = AgentTask.objects.get(id=task_id)
                            if result.get("result"):
                                task.report = result["result"]
                                task.save(update_fields=["report", "updated_at"])
                            logger.info("Beat monitor: processed %s event %s", integration_slug, evt.get("external_id"))
                        except AgentTask.DoesNotExist:
                            pass
                    updated = True
                elif evt.get("created_at"):
                    from django.utils.dateparse import parse_datetime

                    created = parse_datetime(evt["created_at"])
                    if created and created < stale_cutoff:
                        logger.warning(
                            "Beat monitor: stale %s event %s — removing", integration_slug, evt.get("external_id")
                        )
                        updated = True
                    else:
                        remaining.append(evt)
                else:
                    remaining.append(evt)

        if updated:
            agent.internal_state["pending_webhook_events"] = remaining
            agent.save(update_fields=["internal_state"])
