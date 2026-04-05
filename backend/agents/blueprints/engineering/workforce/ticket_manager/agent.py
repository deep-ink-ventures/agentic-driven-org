from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.engineering.workforce.ticket_manager.commands import create_issues, triage_issue
from agents.blueprints.engineering.workforce.ticket_manager.skills import format_skills

logger = logging.getLogger(__name__)

ISSUE_TEMPLATE = """\
## [Verb] [Object] -- [Context]

### Problem Statement
[1-2 sentences: what problem exists and who it affects]

### Acceptance Criteria
GIVEN [precondition]
WHEN [action]
THEN [expected outcome]

### Technical Notes
- Relevant files: [paths]
- Follow pattern in: [reference file]
- Dependencies: [blocking issues]

### Out of Scope
- [Explicitly what this ticket does NOT cover]
"""

LABELING_RULES = """\
TYPE labels (exactly one):
- `feature` — new user-facing capability
- `bug` — defect in existing behavior
- `chore` — refactoring, tooling, CI, docs

COMPONENT labels (one or more):
- `api` — backend API endpoints, serializers
- `frontend` — UI components, pages, styles
- `auth` — authentication, authorization, permissions
- `data` — models, migrations, database
- `infra` — CI/CD, deployment, Docker

SIZE labels (exactly one):
- `S` — < 2 hours of work
- `M` — 2-6 hours of work
- `L` — 6-16 hours of work

PRIORITY labels (exactly one):
- `P0` — critical, blocks release
- `P1` — important, do this sprint
- `P2` — normal, schedule soon
- `P3` — low priority, backlog
"""


class TicketManagerBlueprint(WorkforceBlueprint):
    name = "Ticket Manager"
    slug = "ticket_manager"
    essential = True
    description = "Creates GitHub issues, applies labels, detects duplicates, and links dependencies"
    tags = ["engineering", "tickets", "github", "triage"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return f"""You are a Ticket Manager agent. You create well-structured GitHub issues from engineering plans, triage incoming issues, detect duplicates, and manage cross-references.

## Issue Template
Use this template for every issue you create:

{ISSUE_TEMPLATE}

## Labeling Rules
{LABELING_RULES}

## Duplicate Detection
Before creating any issue:
1. Search existing open issues by title keywords and component
2. If a >80% match is found, note it as a potential duplicate rather than creating a new issue
3. If a related (but not duplicate) issue exists, cross-reference it in Technical Notes

## Dependency Linking
- Note blocking relationships in issue body: "Blocked by #X"
- Note related issues: "Related to #X"
- The leader uses these references to set up task chains

When executing tasks, respond with a JSON object:
{{
    "issues": [
        {{"title": "...", "body": "...", "labels": [...], "duplicates": [...], "dependencies": [...]}}
    ],
    "report": "Summary of issues created"
}}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands
    create_issues = create_issues
    triage_issue = triage_issue

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        if task.command_name == "triage-issue":
            return self._execute_triage(agent, task)
        return self._execute_create_issues(agent, task)

    def _get_github_config(self, agent: Agent) -> tuple[str, list[dict]]:
        """Resolve GitHub token and repos from cascading config."""
        token = agent.get_config_value("github_token")
        if not token:
            raise ValueError("github_token not configured. Set it at project or department level.")
        repos = agent.get_config_value("github_repos")
        if not repos:
            raise ValueError("github_repos not configured. Set it at department level.")
        return token, repos

    def _detect_duplicates(self, token: str, repo: str, title: str) -> list[dict]:
        """Search existing issues for potential duplicates."""
        from integrations.github_dev import service as gh

        # Search using key terms from the title
        search_query = " ".join(title.split()[:5])
        try:
            import requests

            resp = requests.get(
                "https://api.github.com/search/issues",
                headers=gh._headers(token),
                params={"q": f"repo:{repo} is:issue is:open {search_query}", "per_page": 5},
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json().get("items", [])
            return [{"number": r["number"], "title": r["title"], "url": r["html_url"]} for r in results]
        except Exception as e:
            logger.warning("Duplicate search failed for repo %s: %s", repo, e)
            return []

    def _write_issue(self, issue_data: dict) -> tuple[str, str, list[str]]:
        """Format an issue dict into (title, body, labels)."""
        title = issue_data.get("title", "Untitled Issue")
        body = issue_data.get("body", "")
        labels = issue_data.get("labels", [])
        dependencies = issue_data.get("dependencies", [])

        if dependencies:
            dep_lines = "\n".join(f"- Blocked by #{d}" for d in dependencies)
            body += f"\n\n### Dependencies\n{dep_lines}"

        return title, body, labels

    def _link_dependencies(self, issue_data: dict, created_issues: dict[str, int]) -> str:
        """Add cross-reference comments for dependencies."""
        deps = issue_data.get("dependencies", [])
        refs = []
        for dep in deps:
            if dep in created_issues:
                refs.append(f"Depends on #{created_issues[dep]}")
        return "\n".join(refs) if refs else ""

    def _execute_create_issues(self, agent: Agent, task: AgentTask) -> str:
        """Create GitHub issues from the leader's story breakdown."""
        from agents.ai.claude_client import call_claude, parse_json_response
        from integrations.github_dev import service as gh

        token, repos = self._get_github_config(agent)
        # Default to first repo if no specific repo in task
        default_repo = repos[0]["repo"] if repos else None
        if not default_repo:
            raise ValueError("No repos configured in github_repos")

        suffix = f"""Review the task plan and create structured GitHub issues.

Target repository: {default_repo}

For each story/task in the plan, produce a well-structured issue using the template.
Search for duplicates before creating. Apply appropriate labels.

Return JSON:
{{
    "issues": [
        {{
            "title": "[Verb] [Object] -- [Context]",
            "body": "Full issue body using template",
            "labels": ["feature", "api", "M", "P1"],
            "duplicates": [],
            "dependencies": []
        }}
    ],
    "report": "Summary of what was created"
}}"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "create-issues"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        if not data:
            raise ValueError(f"Failed to parse issues JSON from Claude response: {response[:200]}")

        issues = data.get("issues", [])
        report_lines = []
        created_issues: dict[str, int] = {}

        for issue_data in issues:
            title, body, labels = self._write_issue(issue_data)

            # Check for duplicates
            duplicates = self._detect_duplicates(token, default_repo, title)
            if duplicates:
                dup_note = "\n\n### Potential Duplicates\n"
                dup_note += "\n".join(f"- #{d['number']}: {d['title']}" for d in duplicates)
                body += dup_note

            # Add dependency links for issues created in this batch
            dep_links = self._link_dependencies(issue_data, created_issues)
            if dep_links:
                body += f"\n\n### Cross-References\n{dep_links}"

            try:
                result = gh.create_issue(token, default_repo, title, body, labels)
                created_issues[title] = result["number"]
                report_lines.append(f"Created #{result['number']}: {title} ({result['url']})")
                logger.info("Created issue #%d in %s: %s", result["number"], default_repo, title)
            except Exception as e:
                report_lines.append(f"FAILED to create issue '{title}': {e}")
                logger.error("Failed to create issue in %s: %s", default_repo, e)

        report = data.get("report", "")
        report += "\n\n## Created Issues\n" + "\n".join(report_lines)
        return report

    def _execute_triage(self, agent: Agent, task: AgentTask) -> str:
        """Triage an incoming issue: auto-label, check duplicates, prioritize."""
        from agents.ai.claude_client import call_claude, parse_json_response

        token, repos = self._get_github_config(agent)

        suffix = """Triage the described issue. Analyze its content and determine:
1. Type: feature, bug, or chore
2. Component(s): api, frontend, auth, data, infra
3. Size: S, M, or L
4. Priority: P0, P1, P2, or P3
5. Check for duplicate or related issues

Return JSON:
{
    "labels": ["type-label", "component-label", "size-label", "priority-label"],
    "duplicates": [{"number": 123, "similarity": "high|medium"}],
    "triage_comment": "Brief triage assessment",
    "report": "Summary of triage decision"
}"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "triage-issue"),
            max_tokens=4096,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        report = data.get("report", response) if data else response
        return report
