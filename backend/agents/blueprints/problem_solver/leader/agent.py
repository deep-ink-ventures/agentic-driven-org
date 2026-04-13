from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import django.utils.timezone

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.problem_solver.leader.commands import decompose_problem

logger = logging.getLogger(__name__)

MAX_ROUNDS = 10
PLAYGROUND_SCORE_THRESHOLD = 8


class ProblemSolverLeaderBlueprint(LeaderBlueprint):
    name = "First Principle Thinker"
    slug = "leader"
    description = (
        "First-principles decomposition leader — breaks problems into fundamental building blocks, "
        "defines falsifiable definitions of done, and orchestrates a multi-round pipeline of "
        "cross-domain exploration, synthesis, and review."
    )
    tags = ["leadership", "first-principles", "decomposition", "orchestration"]
    skills = [
        {
            "name": "First-Principles Decomposition",
            "description": "Strip a problem to its fundamental truths by listing and challenging every assumption — keep only physical laws, mathematical truths, and verified data.",
        },
        {
            "name": "Assumption Challenging",
            "description": "Classify each assumption as physical law, mathematical truth, convention, or unknown — discard conventions and reconstruct from what remains.",
        },
        {
            "name": "Definition of Done",
            "description": "Craft a falsifiable, measurable definition of done for any problem — reject problems that cannot have one.",
        },
        {
            "name": "Problem Rejection",
            "description": "Identify and reject ill-posed problems that lack a clear, testable success criterion.",
        },
    ]
    config_schema = {
        "github_playground_repo": {
            "type": "str",
            "required": True,
            "description": "Full URL of the GitHub playground repository for PoC validation",
        },
        "github_token": {
            "type": "str",
            "required": True,
            "description": "GitHub Personal Access Token with repo scope",
        },
    }

    # Register commands
    decompose_problem = decompose_problem

    @property
    def system_prompt(self) -> str:
        return """You are the First Principle Thinker — the leader of the Problem Solver department. You decompose problems into their fundamental building blocks and orchestrate a multi-round pipeline to find novel solutions.

## First-Principles Methodology

For every problem:
1. List ALL assumptions explicitly — nothing is taken for granted
2. Challenge each assumption: Is it a physical law? A mathematical truth? A convention? An unknown?
3. Discard conventions. Keep only laws and verified data.
4. Reconstruct the problem from these fundamentals
5. Identify core actors, dynamics, and variants

## Definition of Done (DoD)

Every problem MUST have a falsifiable, measurable definition of done:
- It must be testable — you can run an experiment or computation that proves success or failure
- It must be measurable — numeric thresholds, boolean conditions, or reproducible outcomes
- If no clear DoD is possible, REJECT the problem as invalid — do not waste rounds on ill-posed questions

## Mathematical and Computational Bias

Prefer solutions that can be:
- Expressed as equations, algorithms, or formal proofs
- Validated computationally (code that runs, tests that pass)
- Reproduced independently

## Pipeline Orchestration

You orchestrate a multi-round pipeline:
1. Decompose the problem (you do this yourself via decompose-problem)
2. Dispatch the Out-of-Box Thinker to propose 5 cross-domain fields
3. Dispatch 5 Playground agents in parallel (one per field) to explore structural analogies
4. Filter for scores 8+ — dispatch Synthesizer to build PoCs from high-scoring hypotheses
5. Reviewer validates each PoC against the DoD
6. If accepted (score >= 9.0), write Output and mark solved
7. If rejected or no high scorers, loop to a new round (up to 10 rounds)

## Review Chain (AUTOMATIC — do not manually manage reviews)

When a synthesizer task completes, the system automatically:
1. Routes the PoC to the reviewer for validation
2. If score < threshold → fix task auto-created for the synthesizer with feedback
3. After fix → reviewer runs again (ping-pong until approved or max rounds)
Do NOT manually create review tasks — the system handles the loop."""

    def execute_task(self, agent: Agent, task) -> str:
        """Override to persist decomposition state when decompose-problem completes."""
        from agents.ai.claude_client import call_claude

        if task.command_name == "decompose-problem":
            # Run the LLM directly with decomposition-specific instructions (no delegation suffix)
            cache_context, task_msg = self.build_task_message(agent, task)
            model = self.get_model(agent, task.command_name)
            max_tokens = self.get_max_tokens(agent, task)

            kwargs = {
                "system_prompt": self.build_system_prompt(agent),
                "user_message": task_msg,
                "model": model,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            response, usage = call_claude(**kwargs)
            task.token_usage = usage
            task.save(update_fields=["token_usage"])

            # Parse and persist decomposition into sprint department state
            try:
                parsed = json.loads(response) if response.strip().startswith("{") else None
                if parsed and parsed.get("decomposition"):
                    from projects.models import Sprint

                    sprint = task.sprint
                    if sprint:
                        dept_id = str(agent.department_id)
                        dept_state = sprint.get_department_state(dept_id)
                        dept_state["decomposition"] = parsed["decomposition"]
                        dept_state["status"] = parsed.get("status", "running")
                        sprint.set_department_state(dept_id, dept_state)

                        if dept_state["status"] == "invalid_problem":
                            sprint.status = Sprint.Status.DONE
                            sprint.completion_summary = (
                                f"Problem rejected: {parsed.get('rejection_reason', 'No clear DoD')}"
                            )
                            sprint.completed_at = django.utils.timezone.now()
                            sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])
            except (json.JSONDecodeError, AttributeError, KeyError):
                logger.warning("Failed to parse decomposition from leader response for task %s", task.id)

            # Return full response as the report (preserves the decomposition JSON)
            return response

        # All other commands use standard leader delegation flow
        return super().execute_task(agent, task)

    def generate_task_proposal(self, agent: Agent) -> dict | None:
        # 2. Get sprint and department state
        from projects.models import Sprint

        department = agent.department
        running_sprints = list(
            Sprint.objects.filter(departments=department, status=Sprint.Status.RUNNING).order_by("updated_at")
        )
        if not running_sprints:
            return None
        sprint = running_sprints[0]
        dept_id = str(department.id)
        dept_state = sprint.get_department_state(dept_id)

        status = dept_state.get("status", "new")
        current_round = dept_state.get("round", 0)

        # 3. Check termination
        if status in ("solved", "invalid_problem", "exhausted"):
            return None
        if current_round >= MAX_ROUNDS:
            dept_state["status"] = "exhausted"
            sprint.set_department_state(dept_id, dept_state)
            sprint.status = Sprint.Status.DONE
            sprint.completion_summary = (
                f"Exhausted {MAX_ROUNDS} rounds without reaching quality threshold. "
                f"See solution_round_* outputs for best attempts."
            )
            sprint.completed_at = django.utils.timezone.now()
            sprint.save(
                update_fields=[
                    "status",
                    "completion_summary",
                    "completed_at",
                    "updated_at",
                ]
            )
            return None

        # 4. Get recent completed tasks
        from agents.models import AgentTask

        recent_tasks = list(
            AgentTask.objects.filter(
                sprint=sprint,
                agent__department=department,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .select_related("agent")[:20]
        )
        last_type = recent_tasks[0].agent.agent_type if recent_tasks else None

        # Stage 1: No decomposition yet -> try to extract from completed leader task, or propose one
        if not dept_state.get("decomposition"):
            # Check if a decompose task already completed — extract and persist its result
            leader_tasks = [t for t in recent_tasks if t.agent.agent_type == "leader"]
            for lt in leader_tasks:
                if lt.report:
                    try:
                        parsed = json.loads(lt.report) if lt.report.strip().startswith("{") else None
                        if parsed and parsed.get("decomposition"):
                            dept_state["decomposition"] = parsed["decomposition"]
                            dept_state["status"] = parsed.get("status", "running")
                            sprint.set_department_state(dept_id, dept_state)
                            if dept_state["status"] == "invalid_problem":
                                sprint.status = Sprint.Status.DONE
                                sprint.completion_summary = (
                                    f"Problem rejected: {parsed.get('rejection_reason', 'No clear DoD')}"
                                )
                                sprint.completed_at = django.utils.timezone.now()
                                sprint.save(
                                    update_fields=["status", "completion_summary", "completed_at", "updated_at"]
                                )
                                return None
                            break
                    except (json.JSONDecodeError, AttributeError):
                        pass

            # If we successfully extracted decomposition, fall through to Stage 2
            # Otherwise, propose the decompose task (only if none completed yet)
            if not dept_state.get("decomposition"):
                if leader_tasks:
                    # Leader task completed but report wasn't parseable — don't re-queue infinitely
                    return None
                return {
                    "_sprint_id": str(sprint.id),
                    "exec_summary": "Decompose problem into first principles",
                    "tasks": [
                        {
                            "target_agent_type": "leader",
                            "command_name": "decompose-problem",
                            "exec_summary": f"First-principles decomposition of: {sprint.text[:100]}",
                            "step_plan": (
                                f"Problem statement: {sprint.text}\n\n"
                                "Apply first-principles methodology:\n"
                                "1. List all assumptions\n"
                                "2. Challenge each\n"
                                "3. Identify actors, dynamics, variants\n"
                                "4. Define a falsifiable, measurable definition of done\n"
                                "5. If no clear DoD possible, declare invalid_problem\n\n"
                                "Respond with JSON:\n"
                                '{"decomposition": {"actors": [...], "dynamics": [...], "variants": [...], '
                                '"assumptions_challenged": [...], "definition_of_done": "...", "math_bias": "..."}, '
                                '"status": "running" or "invalid_problem", '
                                '"rejection_reason": "..." (if invalid), "report": "..."}'
                            ),
                            "depends_on_previous": False,
                        }
                    ],
                }

        # Stage 2: Decomposition done -> dispatch Out-of-Box Thinker
        if last_type == "leader" or (
            dept_state.get("decomposition") and not self._has_pending_work(sprint, department)
        ):
            current_round = dept_state.get("round", 0) + 1
            dept_state["round"] = current_round
            sprint.set_department_state(dept_id, dept_state)

            round_history = dept_state.get("round_history", [])
            history_text = json.dumps(round_history, indent=2) if round_history else "No prior rounds."

            return {
                "_sprint_id": str(sprint.id),
                "exec_summary": f"Round {current_round}: propose 5 cross-domain fields",
                "tasks": [
                    {
                        "target_agent_type": "out_of_box_thinker",
                        "command_name": "propose-fields",
                        "exec_summary": f"Round {current_round}: propose 5 cross-domain fields for exploration",
                        "step_plan": (
                            f"## Problem Decomposition\n{json.dumps(dept_state.get('decomposition', {}), indent=2)}\n\n"
                            f"## Definition of Done\n{dept_state.get('decomposition', {}).get('definition_of_done', 'Not defined')}\n\n"
                            f"## Prior Round History\n{history_text}\n\n"
                            "Propose 5 NEW fields (never repeat prior round fields):\n"
                            "- 2 same-domain\n"
                            "- 2 associated-domain\n"
                            "- 1 random-associative"
                        ),
                        "depends_on_previous": False,
                    }
                ],
            }

        # Stage 3: Fields proposed -> dispatch 5 Playground agents in parallel
        if last_type == "out_of_box_thinker":
            last_report = recent_tasks[0].report or ""
            try:
                fields_data = json.loads(last_report)
                fields = fields_data.get("fields", [])
            except (json.JSONDecodeError, AttributeError):
                fields = []

            if not fields:
                return None

            decomposition = json.dumps(dept_state.get("decomposition", {}), indent=2)
            dod = dept_state.get("decomposition", {}).get("definition_of_done", "Not defined")

            tasks = []
            for i, field in enumerate(fields[:5]):
                field_name = field.get("name", f"Field {i + 1}")
                tasks.append(
                    {
                        "target_agent_type": "playground",
                        "command_name": "explore-field",
                        "exec_summary": f"Explore field: {field_name}",
                        "step_plan": (
                            f"## Assigned Field\n{json.dumps(field, indent=2)}\n\n"
                            f"## Problem Decomposition\n{decomposition}\n\n"
                            f"## Definition of Done\n{dod}\n\n"
                            "Explore this field for structural analogies. "
                            "Produce hypothesis + pseudocode sketch. Score 1-10."
                        ),
                        "depends_on_previous": False,
                    }
                )

            return {
                "_sprint_id": str(sprint.id),
                "exec_summary": f"Round {current_round}: explore 5 fields in parallel",
                "tasks": tasks,
            }

        # Stage 4: Playground agents done -> filter for 8+ scores -> dispatch Synthesizer
        playground_tasks = [t for t in recent_tasks if t.agent.agent_type == "playground"]
        if playground_tasks and last_type == "playground":
            high_scorers = []
            for pt in playground_tasks:
                try:
                    report = json.loads(pt.report or "{}")
                    score = report.get("score", 0)
                    if score >= PLAYGROUND_SCORE_THRESHOLD:
                        high_scorers.append((pt, report, score))
                except (json.JSONDecodeError, AttributeError):
                    pass

            if not high_scorers:
                # No hypotheses scored 8+ -- record round and loop
                round_entry = {
                    "round": current_round,
                    "fields_proposed": [
                        json.loads(pt.report or "{}").get("field", "unknown") for pt in playground_tasks
                    ],
                    "playground_scores": {
                        json.loads(pt.report or "{}").get("field", "unknown"): json.loads(pt.report or "{}").get(
                            "score", 0
                        )
                        for pt in playground_tasks
                    },
                    "synthesizer_invoked_for": [],
                    "feedback": "No hypotheses scored 8+. All fields were dead ends this round.",
                }
                history = dept_state.get("round_history", [])
                history.append(round_entry)
                dept_state["round_history"] = history
                sprint.set_department_state(dept_id, dept_state)
                return self.generate_task_proposal(agent)  # Recurse to propose new fields

            dod = dept_state.get("decomposition", {}).get("definition_of_done", "Not defined")
            tasks = []
            for _pt, report, score in high_scorers:
                tasks.append(
                    {
                        "target_agent_type": "synthesizer",
                        "command_name": "build-poc",
                        "exec_summary": f"Build PoC for: {report.get('field', 'unknown')} (score {score})",
                        "step_plan": (
                            f"## Hypothesis (scored {score}/10)\n"
                            f"Field: {report.get('field', 'unknown')}\n"
                            f"Hypothesis: {report.get('hypothesis', 'N/A')}\n\n"
                            f"## Pseudocode\n{report.get('pseudocode', 'N/A')}\n\n"
                            f"## Structural Mapping\n{report.get('structural_mapping', 'N/A')}\n\n"
                            f"## Definition of Done\n{dod}\n\n"
                            "Build a working PoC, push to playground repo, trigger GitHub Action, validate against DoD."
                        ),
                        "depends_on_previous": False,
                    }
                )

            return {
                "_sprint_id": str(sprint.id),
                "exec_summary": f"Round {current_round}: synthesize {len(tasks)} high-scoring hypotheses",
                "tasks": tasks,
            }

        # Stage 5: Reviewer accepted -> write Output, mark solved
        if last_type == "reviewer":
            reviewer_tasks = [t for t in recent_tasks if t.agent.agent_type == "reviewer"]
            for rt in reviewer_tasks:
                if rt.review_verdict == "APPROVED" and rt.review_score and rt.review_score >= 9.0:
                    synth_tasks = [t for t in recent_tasks if t.agent.agent_type == "synthesizer"]
                    best_report = synth_tasks[0].report if synth_tasks else "No synthesizer report."

                    from projects.models import Output

                    Output.objects.create(
                        sprint=sprint,
                        department=department,
                        title=f"Solution Round {current_round}",
                        label=f"solution_round_{current_round}",
                        output_type=Output.OutputType.MARKDOWN,
                        content=best_report,
                    )
                    Output.objects.create(
                        sprint=sprint,
                        department=department,
                        title=f"Solution — {sprint.text[:80]}",
                        label="solution",
                        output_type=Output.OutputType.MARKDOWN,
                        content=best_report,
                    )

                    dept_state["status"] = "solved"
                    sprint.set_department_state(dept_id, dept_state)
                    sprint.status = Sprint.Status.DONE
                    sprint.completion_summary = f"Solved in round {current_round} with score {rt.review_score}/10."
                    sprint.completed_at = django.utils.timezone.now()
                    sprint.save(
                        update_fields=[
                            "status",
                            "completion_summary",
                            "completed_at",
                            "updated_at",
                        ]
                    )
                    return None

        # Default: fall back to base class
        return super().generate_task_proposal(agent)

    def _has_pending_work(self, sprint, department) -> bool:
        """Check if any task in the department is still queued or processing."""
        from agents.models import AgentTask

        pending_statuses = (
            AgentTask.Status.QUEUED,
            AgentTask.Status.PROCESSING,
            AgentTask.Status.AWAITING_APPROVAL,
        )
        return AgentTask.objects.filter(
            sprint=sprint,
            agent__department=department,
            status__in=pending_statuses,
        ).exists()
