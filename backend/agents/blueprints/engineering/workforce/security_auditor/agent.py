from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.engineering.workforce.security_auditor.commands import security_review

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.8

# File paths that trigger security review
SECURITY_SENSITIVE_PATHS = [
    "auth/",
    "crypto/",
    "security/",
    "permissions/",
    "api/",
    "views/",
    "endpoints/",
    "middleware/",
    "decorators/",
    "requirements.txt",
    "package.json",
    "Pipfile",
    "poetry.lock",
]

SECURITY_CATEGORIES = """\
WHAT TO CHECK (via anthropics/claude-code-security-review):

| Category | Specific Checks |
|----------|----------------|
| Injection Attacks | SQL, command, LDAP, XPath, NoSQL, XXE |
| Auth & Authorization | Broken auth, privilege escalation, insecure direct object references |
| Data Exposure | Hardcoded secrets, sensitive data logging, PII handling |
| Cryptographic Issues | Weak algorithms, improper key management |
| Business Logic | Race conditions, TOCTOU |
| Supply Chain | Vulnerable dependencies, typosquatting |
| XSS | Reflected, stored, DOM-based |

WHAT TO EXPLICITLY IGNORE (noise reduction):
- DoS / rate limiting
- Memory/CPU exhaustion
- Generic input validation without proven impact
- Open redirects
"""


class SecurityAuditorBlueprint(WorkforceBlueprint):
    name = "Security Auditor"
    slug = "security_auditor"
    controls = ["backend_engineer", "frontend_engineer"]
    description = "Audits PRs for security vulnerabilities using claude-code-security-review with confidence filtering"
    tags = ["engineering", "security", "audit", "vulnerabilities"]
    skills = [
        {
            "name": "Assess Risk",
            "description": "Reads PR diff and determines if security review is needed based on file paths (auth, crypto, API, dependencies, user input)",
        },
        {
            "name": "Interpret Findings",
            "description": "Interprets security action results, filters by confidence threshold (>= 0.8), and posts structured comments",
        },
    ]
    config_schema = {
        "github_repos": {
            "type": "list",
            "required": True,
            "label": "GitHub Repos",
            "description": "Target repositories with path mappings (cascades from department)",
        },
    }

    @property
    def system_prompt(self) -> str:
        return f"""You are a Security Auditor agent. You assess PRs for security risks and trigger the claude-code-security-review GitHub Action for in-depth security analysis.

## Your Role
You determine whether a PR warrants security review based on the file paths and changes involved, then trigger the security review workflow. You also interpret findings and filter by confidence threshold.

## Risk Assessment
Trigger security review when PR touches:
- Authentication / authorization code (auth/, permissions/, middleware/)
- Cryptographic operations (crypto/, security/)
- API boundaries (api/, views/, endpoints/)
- Dependency files (requirements.txt, package.json, etc.)
- User input handling

## Security Categories
{SECURITY_CATEGORIES}

## Confidence Threshold
Only report findings with confidence >= {CONFIDENCE_THRESHOLD}. Lower-confidence findings are noise and should be suppressed.

## What to Ignore
- DoS / rate limiting concerns
- Memory/CPU exhaustion
- Generic input validation without proven exploit path
- Open redirects

When executing tasks, respond with a JSON object:
{{
    "risk_assessment": "low|medium|high|critical",
    "security_relevant_paths": ["path/to/sensitive/file.py"],
    "should_review": true,
    "pr_number": 123,
    "target_repo": "org/repo",
    "report": "Risk assessment summary"
}}"""

    # Register commands
    security_review = security_review

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        return self._execute_security_review(agent, task)

    def _get_github_config(self, agent: Agent) -> tuple[str, list[dict]]:
        """Resolve GitHub token and repos from cascading config."""
        token = agent.get_config_value("github_token")
        if not token:
            raise ValueError("github_token not configured. Set it at project or department level.")
        repos = agent.get_config_value("github_repos")
        if not repos:
            raise ValueError("github_repos not configured. Set it at department level.")
        return token, repos

    def _assess_risk(self, file_paths: list[str]) -> tuple[str, list[str]]:
        """Assess security risk based on file paths.

        Returns (risk_level, security_relevant_paths).
        """
        relevant = []
        for fp in file_paths:
            for sensitive in SECURITY_SENSITIVE_PATHS:
                if sensitive in fp:
                    relevant.append(fp)
                    break

        if not relevant:
            return "low", relevant

        # Assess severity
        critical_patterns = ["auth/", "crypto/", "security/", "permissions/"]
        has_critical = any(any(cp in fp for cp in critical_patterns) for fp in relevant)

        if has_critical:
            return "critical" if len(relevant) > 3 else "high", relevant
        return "medium", relevant

    def _interpret_findings(self, findings: list[dict]) -> list[dict]:
        """Filter findings by confidence threshold."""
        return [f for f in findings if f.get("confidence", 0) >= CONFIDENCE_THRESHOLD]

    def _execute_security_review(self, agent: Agent, task: AgentTask) -> str:
        """Assess PR risk and trigger security review workflow."""
        from agents.ai.claude_client import call_claude, parse_json_response
        from integrations.github_dev import service as gh

        token, repos = self._get_github_config(agent)

        # Check if security review is required
        require_security = agent.get_config_value("require_security_review")
        if require_security is False:
            return "Security review is disabled for this department. Skipping."

        suffix = """Analyze this task for security review needs.

Extract from the task:
1. The PR number
2. The target repository
3. File paths changed in the PR
4. Any security-relevant patterns in the changes

Assess the risk level based on:
- Does the PR touch auth, crypto, API boundaries, or dependency files?
- Are there any obvious security-sensitive patterns?

Return JSON:
{
    "risk_assessment": "low|medium|high|critical",
    "security_relevant_paths": ["path/to/sensitive/file.py"],
    "should_review": true,
    "pr_number": 123,
    "target_repo": "org/repo",
    "categories_to_check": ["injection", "auth", "data_exposure"],
    "report": "Risk assessment summary and rationale"
}"""

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
            model=self.get_model(agent, "security-review"),
            max_tokens=8192,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        if not data:
            raise ValueError(f"Failed to parse security review JSON: {response[:200]}")

        pr_number = data.get("pr_number")
        target_repo = data.get("target_repo") or repos[0]["repo"]
        should_review = data.get("should_review", True)
        risk_assessment = data.get("risk_assessment", "medium")

        if not pr_number:
            raise ValueError("No PR number found in task. Cannot perform security review without a PR reference.")

        if not should_review:
            report = data.get("report", "")
            report += f"\n\nRisk level: {risk_assessment}. No security review needed for this PR."
            return report

        # Build webhook URL
        project = agent.department.project
        webhook_url = f"/api/webhooks/{project.id}/github/"

        # Trigger security review workflow
        default_branch = agent.get_config_value("default_branch") or "main"
        gh.dispatch_workflow(
            token=token,
            repo=target_repo,
            workflow_file="claude-security-review.yml",
            ref=default_branch,
            inputs={
                "pr_number": str(pr_number),
                "webhook_url": webhook_url,
            },
        )

        # Store pending run in internal_state
        state = agent.internal_state or {}
        if "pending_runs" not in state:
            state["pending_runs"] = {}
        run_key = f"security-pr-{pr_number}"
        state["pending_runs"][run_key] = {
            "workflow": "claude-security-review.yml",
            "pr": str(pr_number),
            "risk_assessment": risk_assessment,
            "repo": target_repo,
            "timestamp": datetime.now(UTC).isoformat(),
            "task_id": str(task.id),
        }
        agent.internal_state = state
        agent.save(update_fields=["internal_state"])

        report = data.get("report", "")
        report += f"\n\nRisk level: {risk_assessment}."
        report += f"\nSecurity review workflow dispatched to {target_repo} for PR #{pr_number}."
        report += f"\nConfidence threshold: {CONFIDENCE_THRESHOLD} (findings below this will be filtered)."
        report += f"\nPending run tracked as '{run_key}' in internal_state."
        return report
