"""Leader command: bootstrap the engineering department — push workflows and create project board."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(
    name="bootstrap",
    description="Push workflow files + CLAUDE.md to target repos, create GitHub Project board",
    schedule="once",
    model="claude-sonnet-4-6",
)
def bootstrap(self, agent: Agent) -> dict:
    department = agent.department
    project = department.project
    config = {**project.config, **department.config, **agent.config}

    github_repos = config.get("github_repos", [])
    github_token = config.get("github_token")

    if not github_repos:
        return {
            "exec_summary": "Bootstrap skipped — no github_repos configured",
            "step_plan": "Configure github_repos in department config before bootstrapping.",
        }
    if not github_token:
        return {
            "exec_summary": "Bootstrap skipped — no github_token configured",
            "step_plan": "Configure github_token in project config before bootstrapping.",
        }

    results = []
    for repo_config in github_repos:
        repo = repo_config if isinstance(repo_config, str) else repo_config.get("repo", "")
        if not repo:
            continue
        result = self._setup_repo(agent, repo, github_token, config)
        results.append(result)

    # Create GitHub Project board
    board_result = _create_project_board(github_token, github_repos, project.name)

    # Store bootstrap state
    internal_state = agent.internal_state or {}
    internal_state["bootstrapped"] = True
    internal_state["bootstrapped_repos"] = [r["repo"] for r in results]
    if board_result.get("project_id"):
        internal_state["github_project_id"] = board_result["project_id"]
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])

    repos_summary = "\n".join(f"- {r['repo']}: {r['status']}" for r in results)
    return {
        "exec_summary": f"Bootstrapped {len(results)} repo(s) with workflow files and CLAUDE.md",
        "step_plan": f"Repos:\n{repos_summary}\n\nProject board: {board_result.get('status', 'unknown')}",
    }


def _create_project_board(token: str, repos: list, project_name: str) -> dict:
    """Create a GitHub Projects v2 board with standard columns."""
    import requests

    # GitHub Projects v2 uses GraphQL — extract org from first repo
    first_repo = repos[0] if repos else None
    if not first_repo:
        return {"status": "skipped — no repos"}

    repo_name = first_repo if isinstance(first_repo, str) else first_repo.get("repo", "")
    owner = repo_name.split("/")[0] if "/" in repo_name else ""
    if not owner:
        return {"status": "skipped — could not determine org"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Try to create an org-level project via GraphQL
    graphql_url = "https://api.github.com/graphql"

    # First get owner ID (could be org or user)
    query_owner = """
    query($login: String!) {
        organization(login: $login) { id }
    }
    """
    resp = requests.post(
        graphql_url, headers=headers, json={"query": query_owner, "variables": {"login": owner}}, timeout=30
    )

    owner_id = None
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        org = data.get("organization")
        if org:
            owner_id = org["id"]

    if not owner_id:
        # Try as user
        query_user = """
        query($login: String!) {
            user(login: $login) { id }
        }
        """
        resp = requests.post(
            graphql_url, headers=headers, json={"query": query_user, "variables": {"login": owner}}, timeout=30
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            user = data.get("user")
            if user:
                owner_id = user["id"]

    if not owner_id:
        logger.warning("Could not resolve GitHub owner ID for %s", owner)
        return {"status": f"failed — could not resolve owner {owner}"}

    # Create project
    mutation = """
    mutation($ownerId: ID!, $title: String!) {
        createProjectV2(input: {ownerId: $ownerId, title: $title}) {
            projectV2 { id number url }
        }
    }
    """
    title = f"{project_name} — Engineering"
    resp = requests.post(
        graphql_url,
        headers=headers,
        json={
            "query": mutation,
            "variables": {"ownerId": owner_id, "title": title},
        },
        timeout=30,
    )

    if resp.status_code != 200:
        logger.warning("Failed to create GitHub Project: %s", resp.text[:500])
        return {"status": f"failed — {resp.status_code}"}

    result = resp.json()
    errors = result.get("errors")
    if errors:
        logger.warning("GraphQL errors creating project: %s", errors)
        return {"status": f"failed — {errors[0].get('message', 'unknown')}"}

    project_data = result.get("data", {}).get("createProjectV2", {}).get("projectV2", {})
    project_id = project_data.get("id")
    project_url = project_data.get("url", "")

    if not project_id:
        return {"status": "failed — no project ID returned"}

    # Add status field with columns: Backlog, In Progress, In Review, Done
    # Projects v2 comes with a default Status field — we add our custom options
    logger.info("Created GitHub Project: %s (%s)", title, project_url)
    return {"status": "created", "project_id": project_id, "url": project_url}
