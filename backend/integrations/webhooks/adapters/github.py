"""GitHub webhook adapter."""

import logging

from integrations.github_dev import service as github_service
from integrations.webhooks.base import BaseWebhookAdapter

logger = logging.getLogger(__name__)


class GitHubWebhookAdapter(BaseWebhookAdapter):
    slug = "github"

    def verify(self, request, webhook_secret: str) -> bool:
        signature = request.headers.get("X-Hub-Signature-256", "")
        return github_service.verify_webhook_signature(request.body, signature, webhook_secret)

    def parse_event(self, request) -> dict:
        event_type = request.headers.get("X-GitHub-Event", "")
        action = request.data.get("action", "")
        return {
            "event_type": f"{event_type}.{action}" if action else event_type,
            "data": request.data,
        }

    def handle_event(self, project, event: dict) -> None:
        from agents.models import Agent, AgentTask

        event_type = event["event_type"]
        data = event["data"]

        if event_type == "workflow_run.completed":
            run_id = data.get("workflow_run", {}).get("id")
            if not run_id:
                return

            for agent in Agent.objects.filter(department__project=project, status="active"):
                pending = agent.internal_state.get("pending_webhook_events", [])
                matched = [
                    e for e in pending if e.get("external_id") == str(run_id) and e.get("integration") == "github"
                ]
                if not matched:
                    continue

                for evt in matched:
                    task_id = evt.get("task_id")
                    if task_id:
                        try:
                            task = AgentTask.objects.get(id=task_id)
                            token = agent.get_config_value("github_token")
                            repo = evt.get("repo", "")
                            if token and repo:
                                logs = github_service.get_workflow_logs(token, repo, int(run_id))
                                task.report = logs
                                task.save(update_fields=["report", "updated_at"])
                            logger.info("GitHub webhook: processed run %s for task %s", run_id, task_id)
                        except AgentTask.DoesNotExist:
                            logger.warning("GitHub webhook: task %s not found", task_id)

                remaining = [e for e in pending if e.get("external_id") != str(run_id)]
                agent.internal_state["pending_webhook_events"] = remaining
                agent.save(update_fields=["internal_state"])

    def check_pending(self, events: list[dict], config: dict) -> list[dict]:
        token = config.get("github_token")
        if not token:
            return []
        completed = []
        for evt in events:
            repo = evt.get("repo", "")
            run_id = evt.get("external_id")
            if not repo or not run_id:
                continue
            try:
                run = github_service.get_workflow_run(token, repo, int(run_id))
                if run["status"] == "completed":
                    logs = github_service.get_workflow_logs(token, repo, int(run_id))
                    completed.append({**evt, "result": logs, "conclusion": run["conclusion"]})
            except Exception:
                logger.exception("Failed to check GitHub run %s", run_id)
        return completed
