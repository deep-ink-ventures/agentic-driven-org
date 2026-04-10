"""Document consolidation tasks.

Three-tier consolidation:
1. Sprint-end: merge all sprint progress docs into one summary per department.
2. Monthly: merge all docs older than 30 days into topic-clustered archives.
3. Volume: emergency consolidation when a department exceeds 500k tokens.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import Sum
from django.db.models.functions import Length
from django.utils import timezone

from agents.ai.claude_client import call_claude, parse_json_response

logger = logging.getLogger(__name__)

# ~500k tokens ≈ ~1.5M characters (rough 1:3 ratio for English text)
VOLUME_THRESHOLD_CHARS = 1_500_000


def _consolidate_documents(documents, department, document_type, title_prefix, instruction):
    """Shared consolidation logic: Claude reads documents, produces a summary, archives originals."""
    if not documents:
        return None

    docs_text = ""
    for doc in documents:
        docs_text += f"\n\n--- [{doc.doc_type}] {doc.title} (created {doc.created_at.date()}) ---\n{doc.content}"

    system_prompt = (
        "You are a knowledge consolidator. Your job is to merge multiple documents into a comprehensive, "
        "well-organized summary. Preserve ALL meaningful detail — findings, decisions, artifacts, outcomes. "
        "Organize by topic. Drop only information that is clearly outdated or superseded by newer content. "
        "Write in markdown. Be thorough — this summary replaces the originals."
    )

    user_message = f"""{instruction}

## Department: {department.name}

## Documents to consolidate:
{docs_text}

Write the consolidated document now."""

    response, _usage = call_claude(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=16384,
    )

    from projects.models import Document

    summary = Document.objects.create(
        title=f"{title_prefix} — {department.name} — {timezone.now().strftime('%Y-%m-%d')}",
        content=response,
        department=department,
        document_type=document_type,
        doc_type=Document.DocType.GENERAL,
    )

    for doc in documents:
        doc.is_archived = True
        doc.consolidated_into = summary
        doc.save(update_fields=["is_archived", "consolidated_into", "updated_at"])

    logger.info(
        "Consolidated %d documents into '%s' for department %s",
        len(documents),
        summary.title,
        department.name,
    )
    return summary


@shared_task
def consolidate_sprint_documents(sprint_id):
    """Merge all sprint progress documents into one summary per department."""
    from projects.models import Document, Sprint

    try:
        sprint = Sprint.objects.get(id=sprint_id)
    except Sprint.DoesNotExist:
        logger.warning("Sprint %s not found — skipping consolidation", sprint_id)
        return

    for department in sprint.departments.all():
        docs = list(
            Document.objects.filter(
                department=department,
                sprint=sprint,
                is_archived=False,
                is_locked=False,
            )
            .exclude(document_type="sprint_summary")
            .order_by("created_at")
        )

        summary = _consolidate_documents(
            documents=docs,
            department=department,
            document_type="sprint_summary",
            title_prefix=f"Sprint Summary: {sprint.text[:50]}",
            instruction=(
                f"Consolidate all progress documents from this sprint into one comprehensive summary.\n"
                f"Sprint instruction: {sprint.text}\n"
                f"Sprint status: {sprint.status}"
            ),
        )

        # Link the summary to the sprint
        if summary:
            summary.sprint = sprint
            summary.save(update_fields=["sprint", "updated_at"])


@shared_task
def consolidate_monthly_documents():
    """Monthly: merge all non-archived documents older than 30 days per department."""
    from projects.models import Department, Document

    cutoff = timezone.now() - timedelta(days=30)

    departments_with_old_docs = (
        Document.objects.filter(
            is_archived=False,
            is_locked=False,
            created_at__lt=cutoff,
        )
        .values_list("department_id", flat=True)
        .distinct()
    )

    for dept_id in departments_with_old_docs:
        department = Department.objects.get(id=dept_id)
        docs = list(
            Document.objects.filter(
                department=department,
                is_archived=False,
                is_locked=False,
                created_at__lt=cutoff,
            ).order_by("created_at")
        )

        _consolidate_documents(
            documents=docs,
            department=department,
            document_type="monthly_archive",
            title_prefix="Monthly Archive",
            instruction=(
                "Consolidate these older documents into a comprehensive archive. "
                "Drop information that is clearly outdated or no longer relevant. "
                "Organize by topic. This archive represents the department's historical knowledge."
            ),
        )


@shared_task
def consolidate_department_documents(department_id):
    """Emergency consolidation when department context exceeds volume threshold."""
    from projects.models import Department, Document

    department = Department.objects.get(id=department_id)

    active_docs = Document.objects.filter(department=department, is_archived=False, is_locked=False)
    total_chars = active_docs.aggregate(total=Sum(Length("content")))["total"] or 0

    if total_chars < VOLUME_THRESHOLD_CHARS:
        return

    logger.warning(
        "VOLUME_THRESHOLD department=%s chars=%d threshold=%d — triggering consolidation",
        department.name,
        total_chars,
        VOLUME_THRESHOLD_CHARS,
    )

    docs = list(active_docs.order_by("created_at"))

    _consolidate_documents(
        documents=docs,
        department=department,
        document_type="monthly_archive",
        title_prefix="Volume Consolidation",
        instruction=(
            "This department's context has grown too large. Consolidate ALL documents into a compact, "
            "topic-organized set. Preserve everything still relevant. Drop only clearly outdated information."
        ),
    )


# ── Agent instructions review ───────────────────────────────────────────────


@shared_task
def review_agent_instructions_after_sprint(sprint_id: str):
    """Review agent instructions across all departments after a sprint completes.

    Three-step process:
    1. Assess which departments are affected by sprint outcomes
    2. For affected departments, assess which agents need instruction updates
    3. For affected agents, propose updated instructions (stored as pending AgentTask)
    """
    from agents.models import AgentTask
    from projects.models import Department, Sprint

    try:
        sprint = Sprint.objects.get(id=sprint_id)
    except Sprint.DoesNotExist:
        logger.warning("Sprint %s not found — skipping instructions review", sprint_id)
        return

    project = sprint.project

    # Gather sprint outcomes
    sprint_tasks = list(
        AgentTask.objects.filter(sprint=sprint, status=AgentTask.Status.DONE)
        .select_related("agent", "agent__department")
        .values_list("agent__department__department_type", "exec_summary", "report")
    )
    if not sprint_tasks:
        return

    outcomes_text = ""
    for dept_type, summary, report in sprint_tasks:
        outcomes_text += f"\n- [{dept_type}] {summary}"
        if report:
            outcomes_text += f"\n  Result: {report[:500]}"

    # Get all departments in the project
    all_departments = list(Department.objects.filter(project=project).values_list("id", "department_type"))

    # Step 1: Which departments are affected?
    dept_list = "\n".join(f"- {dt}" for _, dt in all_departments)
    response, _usage = call_claude(
        system_prompt=(
            "You assess whether sprint outcomes affect other departments' agent instructions. "
            "Respond with JSON only. No markdown fences."
        ),
        user_message=f"""## Project: {project.name}
## Project Goal: {project.goal or "Not set"}

## Sprint that just completed: {sprint.text}

## Sprint outcomes:
{outcomes_text}

## All departments in this project:
{dept_list}

Which departments might have agents whose instructions are now outdated due to these sprint outcomes?

Only flag departments where the sprint outcomes genuinely change the context that agents rely on.
For example:
- A writers room sprint that changes the title/arc affects marketing and sales agents
- A backend security fix does NOT affect sales or writers room agents
- A sales strategy sprint might affect community/partnership agents

Respond with JSON:
{{"affected_departments": ["dept_type1", "dept_type2"], "reasoning": "why"}}

If NO departments are affected, return {{"affected_departments": [], "reasoning": "why not"}}""",
        max_tokens=1024,
    )

    result = parse_json_response(response)
    if not result:
        logger.warning("INSTRUCTIONS_REVIEW: failed to parse department assessment for sprint %s", sprint_id)
        return

    affected_dept_types = result.get("affected_departments", [])
    if not affected_dept_types:
        logger.info(
            "INSTRUCTIONS_REVIEW: no departments affected by sprint %s — %s",
            sprint_id,
            result.get("reasoning", ""),
        )
        return

    logger.info(
        "INSTRUCTIONS_REVIEW: sprint %s affects departments: %s — %s",
        sprint_id,
        affected_dept_types,
        result.get("reasoning", ""),
    )

    # Fan out: one task per agent in affected departments
    from agents.models import Agent

    dept_map = {dt: did for did, dt in all_departments}
    for dept_type in affected_dept_types:
        dept_id = dept_map.get(dept_type)
        if not dept_id:
            continue
        agent_ids = list(
            Agent.objects.filter(
                department_id=dept_id,
                status=Agent.Status.ACTIVE,
            ).values_list("id", flat=True)
        )
        for aid in agent_ids:
            review_single_agent_instructions.delay(str(aid), str(project.id))


@shared_task
def review_agent_instructions_after_goal_change(project_id: str):
    """Fan out one review task per active agent after the project goal changes."""
    from agents.models import Agent
    from projects.models import Project

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist as e:
        raise ValueError(f"Project {project_id} not found") from e

    agent_ids = list(
        Agent.objects.filter(
            department__project=project,
            status=Agent.Status.ACTIVE,
        ).values_list("id", flat=True)
    )
    if not agent_ids:
        return

    # Fan out: each task manages its own provisioning→active lifecycle
    for aid in agent_ids:
        review_single_agent_instructions.delay(str(aid), project_id)


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def review_single_agent_instructions(self, agent_id: str, project_id: str):
    """Review and update a single agent's instructions after a goal change.

    One agent, one Claude call, one structured response.
    Sets agent back to active when done (or on failure).
    """
    from agents.ai.claude_client import call_claude_structured
    from agents.models import Agent, AgentTask

    try:
        agent = Agent.objects.select_related("department", "department__project").get(id=agent_id)
    except Agent.DoesNotExist as e:
        raise ValueError(f"Agent {agent_id} not found") from e

    project = agent.department.project
    department = agent.department

    # Set to provisioning at the start of THIS task
    agent.status = Agent.Status.PROVISIONING
    agent.save(update_fields=["status", "updated_at"])
    _broadcast_agent_status(project_id, department.id, agent_id, "provisioning")

    try:
        bp = agent.get_blueprint()
        locale = agent.get_config_value("locale") or "en"

        review_schema = {
            "type": "object",
            "properties": {
                "affected": {
                    "type": "boolean",
                    "description": "Whether this agent's instructions need updating",
                },
                "reason": {
                    "type": "string",
                    "description": "Why the instructions do or do not need updating",
                },
                "updated_instructions": {
                    "type": "string",
                    "description": "The full updated instructions text (only if affected=true)",
                },
            },
            "required": ["affected", "reason"],
        }

        result, _usage = call_claude_structured(
            system_prompt=(
                "You review an agent's instructions after the project goal changed. "
                "Decide if the instructions need updating to reflect the new goal. "
                "If yes, write the full updated instructions preserving the existing style and tone. "
                "Add project-specific context from the goal, don't rewrite from scratch. "
                f"Write in {locale}."
            ),
            user_message=f"""## Project: {project.name}

<project_goal>
{project.goal or "(empty)"}
</project_goal>

## Agent: {agent.name} ({agent.agent_type})
Role: {bp.description}

## Current Instructions
{agent.instructions or "(none)"}

## Task
Compare the current instructions against the project goal above.
Are these instructions still accurate? Do they need updating to reflect the goal?

If the goal mentions tone, style, themes, characters, or constraints that this agent's
instructions don't cover — they need updating.""",
            output_schema=review_schema,
            tool_name="submit_review",
            tool_description="Submit the instruction review result for this agent",
            max_tokens=4096,
        )

        if result.get("affected") and result.get("updated_instructions", "").strip():
            new_instructions = result["updated_instructions"].strip()
            reason = result.get("reason", "Project goal changed.")

            # Find leader for the task, or fall back to this agent
            leader = Agent.objects.filter(
                department=department, is_leader=True, status__in=["active", "provisioning"]
            ).first()

            AgentTask.objects.create(
                agent_id=leader.id if leader else agent.id,
                created_by_agent=leader,
                status=AgentTask.Status.AWAITING_APPROVAL,
                exec_summary=f"Update instructions for {agent.name} after project goal change",
                step_plan=(
                    f"## Reason\n{reason}\n\n"
                    f"## Proposed Updated Instructions\n{new_instructions}\n\n"
                    f"Approve to apply these updated instructions to {agent.name} ({agent.agent_type})."
                ),
            )
            logger.info(
                "INSTRUCTIONS_REVIEW: proposed update for %s (%s) — %s",
                agent.name,
                agent.agent_type,
                reason[:100],
            )
        else:
            logger.info(
                "INSTRUCTIONS_REVIEW: no update needed for %s (%s) — %s",
                agent.name,
                agent.agent_type,
                result.get("reason", "")[:100],
            )

    except Exception as e:
        logger.warning(
            "review_single_agent_instructions attempt %d failed for %s: %s",
            self.request.retries + 1,
            agent.name,
            e,
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e) from e
        logger.exception(
            "INSTRUCTIONS_REVIEW: failed for %s after %d retries",
            agent.name,
            self.max_retries,
        )

    finally:
        # Always restore to active + broadcast
        agent.status = Agent.Status.ACTIVE
        agent.save(update_fields=["status", "updated_at"])
        _broadcast_agent_status(project_id, department.id, agent_id, "active")


def _broadcast_agent_status(project_id, department_id, agent_id, status):
    """Send agent status update via WebSocket."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"project_{project_id}",
            {
                "type": "agent.status",
                "agent_id": str(agent_id),
                "department_id": str(department_id),
                "status": status,
                "error_message": "",
            },
        )
    except Exception:
        logger.exception("Failed to broadcast agent status")
