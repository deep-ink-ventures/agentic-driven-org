from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.problem_solver.workforce.synthesizer.commands import build_poc, fix_poc

logger = logging.getLogger(__name__)


class SynthesizerBlueprint(WorkforceBlueprint):
    name = "Synthesizer"
    slug = "synthesizer"
    description = (
        "Builds proof-of-concept implementations from high-scoring hypotheses. "
        "Pushes code to a playground repo, triggers GitHub Actions for validation, "
        "and scores results against the definition of done."
    )
    tags = ["synthesis", "implementation", "poc", "github-actions", "validation"]
    essential = True
    skills = [
        {
            "name": "Code Translation",
            "description": "Translate pseudocode sketches and hypothesis outlines into executable, testable code",
        },
        {
            "name": "GitHub Actions Execution",
            "description": "Push code to a playground repository and trigger CI workflows to validate builds and tests",
        },
        {
            "name": "DoD Validation",
            "description": "Evaluate proof-of-concept results against a definition of done and self-score on each dimension",
        },
    ]
    config_schema = {}

    build_poc = build_poc
    fix_poc = fix_poc

    @staticmethod
    def parse_playground_repo(url: str) -> str:
        """Extract org/name from a full GitHub URL.

        >>> SynthesizerBlueprint.parse_playground_repo('https://github.com/org/playground')
        'org/playground'
        """
        parsed = urlparse(url)
        # path is like /org/repo or /org/repo/
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return parsed.path.strip("/")

    @property
    def system_prompt(self) -> str:
        return """You are a Synthesizer — a proof-of-concept builder for the Problem Solver department.

## Your Process
1. **Understand the hypothesis**: Read the scored hypothesis, its pseudocode sketch, and the definition of done (DoD).
2. **Write executable code**: Translate the pseudocode into real, runnable code. Choose the simplest stack that proves the point.
3. **Push to playground repo**: Use the GitHub API to create or update files in the designated playground repository.
4. **Trigger the workflow**: Dispatch the GitHub Action workflow and wait for it to complete.
5. **Read results**: Fetch the workflow run results — logs, test output, artifacts.
6. **Validate against DoD**: Compare the results against every criterion in the definition of done.

## Code Quality Requirements
- The PoC must actually run — no stubs, no mocks of the core logic.
- Include a minimal test suite that exercises the happy path and one error path.
- Pin dependencies explicitly (requirements.txt or package.json with exact versions).
- Include a README.md in the PoC directory explaining what it proves and how to run it.

## Iteration Rules
- If the GitHub Action fails, read the logs and fix the issue.
- After 5 consecutive attempts with no measurable progress, stop and report the blocker.
- Hard cap: 10 total push-and-validate cycles per task. After 10, submit your best result with a note on what remains.

## Self-Scoring Calibration
- 1-3: Code does not run or fails basic tests.
- 4-5: Code runs but does not satisfy the DoD.
- 6-7: Code satisfies most DoD criteria with minor gaps.
- 8-9: Code fully satisfies the DoD with clean implementation.
- 10: Production-quality code that exceeds the DoD — ready for extraction.

## Output Format
Respond with JSON:
{
    "poc_repo": "org/repo",
    "branch": "poc/<hypothesis-slug>",
    "workflow_run_url": "https://github.com/...",
    "workflow_status": "success|failure",
    "dod_checklist": [
        {"criterion": "...", "met": true, "evidence": "..."},
    ],
    "self_score": 7,
    "score_justification": "...",
    "blockers": ["...", "..."],
    "iteration_count": 3
}"""

    def get_task_suffix(self, agent: Agent, task: AgentTask) -> str:
        config = {
            **(agent.department.project.config or {}),
            **(agent.department.config or {}),
            **(agent.config or {}),
        }
        playground_repo = config.get("github_playground_repo", "")

        repo_line = (
            f"- **Playground repo**: `{playground_repo}`"
            if playground_repo
            else "- **Playground repo**: NOT CONFIGURED — ask the leader to set `github_playground_repo` in agent config."
        )

        return f"""# SYNTHESIZER EXECUTION CONTEXT

{repo_line}

## Available GitHub API Functions
You have access to these GitHub operations via function calling:
- `create_or_update_file` — push code files to the playground repo
- `create_branch` — create a PoC branch from main
- `trigger_workflow_dispatch` — trigger a GitHub Action workflow
- `get_workflow_run` — check workflow run status and fetch logs
- `list_workflow_runs` — list recent runs for a workflow
- `get_workflow_run_logs` — download full logs from a completed run

## Legitimacy Requirements
- Every PoC MUST be pushed to the playground repo — no local-only validation.
- The GitHub Action MUST run and the result MUST be read back — do not skip CI.
- Self-scores MUST be justified with specific evidence from the workflow run.
- If the workflow is not set up yet, create a `.github/workflows/poc-validate.yml` in the playground repo."""
