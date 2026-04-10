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

    # Step 2 & 3: For each affected department, review agents
    dept_map = {dt: did for did, dt in all_departments}
    for dept_type in affected_dept_types:
        dept_id = dept_map.get(dept_type)
        if not dept_id:
            continue
        _review_department_agents(dept_id, sprint, outcomes_text)


def _review_department_agents(department_id, sprint, outcomes_text: str):
    """Review and update agent instructions for a single department."""
    from agents.models import Agent, AgentTask
    from projects.models import Department, Document

    department = Department.objects.get(id=department_id)

    agents = list(
        Agent.objects.filter(
            department=department,
            status=Agent.Status.ACTIVE,
        ).values_list("id", "name", "agent_type", "instructions")
    )
    if not agents:
        return

    # Gather current department docs for context
    docs = list(
        Document.objects.filter(department=department, is_archived=False).values_list("title", "doc_type", "content")[
            :10
        ]
    )
    docs_text = ""
    for title, doc_type, content in docs:
        docs_text += f"\n\n--- [{doc_type}] {title} ---\n{content[:1000]}"

    # Build agent descriptions
    agents_text = ""
    for _agent_id, name, agent_type, instructions in agents:
        agents_text += f"\n\n### {name} ({agent_type})\n**Current instructions:**\n{instructions or '(none)'}"

    # Step 2: Which agents are affected?
    response, _usage = call_claude(
        system_prompt=(
            "You review agent instructions after a sprint to check if they are still accurate. "
            "Respond with JSON only. No markdown fences."
        ),
        user_message=f"""## Department: {department.name} ({department.department_type})

## Sprint outcomes that may affect this department:
{outcomes_text}

## Current department documents:
{docs_text}

## Agents and their current instructions:
{agents_text}

For each agent, decide:
- Are their instructions still accurate given the sprint outcomes?
- Do they reference anything that changed?
- Should instructions be updated to reflect new context?

Respond with JSON:
{{
    "agents": [
        {{
            "agent_type": "agent_type",
            "affected": true/false,
            "reason": "why affected or not",
            "updated_instructions": "the full new instructions text (only if affected)"
        }}
    ]
}}

Rules:
- Only flag agents whose instructions genuinely need updating
- Preserve the style and tone of existing instructions
- Add new context, don't rewrite from scratch
- If an agent has no instructions and doesn't need any, mark as not affected""",
        max_tokens=8192,
    )

    result = parse_json_response(response)
    if not result:
        logger.warning(
            "INSTRUCTIONS_REVIEW: failed to parse agent assessment for department %s",
            department.name,
        )
        return

    # Step 3: Create update tasks for affected agents
    agent_map = {at: (aid, name) for aid, name, at, _ in agents}
    leader = Agent.objects.filter(department=department, is_leader=True, status="active").first()

    updated_count = 0
    for agent_data in result.get("agents", []):
        if not agent_data.get("affected"):
            continue

        agent_type = agent_data.get("agent_type")
        if agent_type not in agent_map:
            continue

        agent_id, agent_name = agent_map[agent_type]
        new_instructions = agent_data.get("updated_instructions", "")
        if not new_instructions:
            continue

        # Create an awaiting-approval task on the leader to update this agent's instructions
        AgentTask.objects.create(
            agent_id=leader.id if leader else agent_id,
            created_by_agent=leader,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary=f"Update instructions for {agent_name} after sprint: {sprint.text[:60]}",
            step_plan=(
                f"## Reason\n{agent_data.get('reason', 'Sprint outcomes changed relevant context.')}\n\n"
                f"## Proposed Updated Instructions\n{new_instructions}\n\n"
                f"Approve to apply these updated instructions to {agent_name} ({agent_type})."
            ),
        )
        updated_count += 1

        logger.info(
            "INSTRUCTIONS_REVIEW: proposed update for %s (%s) in %s — %s",
            agent_name,
            agent_type,
            department.name,
            agent_data.get("reason", ""),
        )

    if updated_count:
        logger.info(
            "INSTRUCTIONS_REVIEW: proposed %d instruction updates for department %s",
            updated_count,
            department.name,
        )
    else:
        logger.info(
            "INSTRUCTIONS_REVIEW: no instruction updates needed for department %s",
            department.name,
        )


@shared_task
def review_agent_instructions_after_goal_change(project_id: str):
    """Review agent instructions across all departments after the project goal changes.

    Sets all active agents to provisioning while reviewing, then restores them
    to active once their department's review is complete.
    """
    from agents.models import Agent
    from projects.models import Department, Project

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        logger.warning("Project %s not found — skipping instructions review", project_id)
        return

    all_departments = list(
        Department.objects.filter(project=project).prefetch_related("agents").values_list("id", "department_type")
    )
    if not all_departments:
        return

    # Set all active agents to provisioning and broadcast
    active_agents = list(
        Agent.objects.filter(
            department__project=project,
            status=Agent.Status.ACTIVE,
        ).values_list("id", "department_id")
    )
    if active_agents:
        Agent.objects.filter(id__in=[a[0] for a in active_agents]).update(status=Agent.Status.PROVISIONING)
        for agent_id, dept_id in active_agents:
            _broadcast_agent_status(project_id, dept_id, agent_id, "provisioning")

    change_context = f"The project goal has been updated.\n\n## Current Project Goal\n{project.goal or '(empty)'}"

    for dept_id, _dept_type in all_departments:
        try:
            _review_department_agents_for_change(dept_id, project, change_context)
        finally:
            # Restore this department's agents to active regardless of success/failure
            dept_agents = [a for a in active_agents if str(a[1]) == str(dept_id)]
            if dept_agents:
                Agent.objects.filter(id__in=[a[0] for a in dept_agents]).update(status=Agent.Status.ACTIVE)
                for agent_id, d_id in dept_agents:
                    _broadcast_agent_status(project_id, d_id, agent_id, "active")


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


def _review_department_agents_for_change(department_id, project, change_context: str):
    """Review and update agent instructions for a single department after a project change."""
    from agents.models import Agent, AgentTask
    from projects.models import Department, Document

    department = Department.objects.get(id=department_id)

    # Query agents that are active or provisioning (we set them to provisioning at the start)
    agents = list(
        Agent.objects.filter(
            department=department,
            status__in=[Agent.Status.ACTIVE, Agent.Status.PROVISIONING],
        ).values_list("id", "name", "agent_type", "instructions")
    )
    if not agents:
        return

    docs = list(
        Document.objects.filter(department=department, is_archived=False).values_list("title", "doc_type", "content")[
            :10
        ]
    )
    docs_text = ""
    for title, doc_type, content in docs:
        docs_text += f"\n\n--- [{doc_type}] {title} ---\n{content[:1000]}"

    agents_text = ""
    for _agent_id, name, agent_type, instructions in agents:
        agents_text += f"\n\n### {name} ({agent_type})\n**Current instructions:**\n{instructions or '(none)'}"

    response, _usage = call_claude(
        system_prompt=(
            "You review agent instructions after a project goal change to check if they are still accurate. "
            "Respond with JSON only. No markdown fences."
        ),
        user_message=f"""## Project: {project.name}

## Change context:
{change_context}

## Department: {department.name} ({department.department_type})

## Current department documents:
{docs_text}

## Agents and their current instructions:
{agents_text}

For each agent, decide:
- Are their instructions still accurate given the updated project goal?
- Do they reference anything that changed?
- Should instructions be updated to reflect the new goal?

Respond with JSON:
{{
    "agents": [
        {{
            "agent_type": "agent_type",
            "affected": true/false,
            "reason": "why affected or not",
            "updated_instructions": "the full new instructions text (only if affected)"
        }}
    ]
}}

Rules:
- Only flag agents whose instructions genuinely need updating
- Preserve the style and tone of existing instructions
- Add new context from the goal, don't rewrite from scratch
- If an agent has no instructions and doesn't need any, mark as not affected""",
        max_tokens=8192,
    )

    result = parse_json_response(response)
    if not result:
        logger.warning(
            "INSTRUCTIONS_REVIEW: failed to parse agent assessment for department %s",
            department.name,
        )
        return

    agent_map = {at: (aid, name) for aid, name, at, _ in agents}
    leader = Agent.objects.filter(department=department, is_leader=True, status__in=["active", "provisioning"]).first()

    updated_count = 0
    for agent_data in result.get("agents", []):
        if not agent_data.get("affected"):
            continue

        agent_type = agent_data.get("agent_type")
        if agent_type not in agent_map:
            continue

        agent_id, agent_name = agent_map[agent_type]
        new_instructions = agent_data.get("updated_instructions", "")
        if not new_instructions:
            continue

        AgentTask.objects.create(
            agent_id=leader.id if leader else agent_id,
            created_by_agent=leader,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary=f"Update instructions for {agent_name} after project goal change",
            step_plan=(
                f"## Reason\n{agent_data.get('reason', 'Project goal changed.')}\n\n"
                f"## Proposed Updated Instructions\n{new_instructions}\n\n"
                f"Approve to apply these updated instructions to {agent_name} ({agent_type})."
            ),
        )
        updated_count += 1

        logger.info(
            "INSTRUCTIONS_REVIEW: proposed update for %s (%s) in %s — %s",
            agent_name,
            agent_type,
            department.name,
            agent_data.get("reason", ""),
        )

    if updated_count:
        logger.info(
            "INSTRUCTIONS_REVIEW: proposed %d instruction updates for department %s after goal change",
            updated_count,
            department.name,
        )
    else:
        logger.info(
            "INSTRUCTIONS_REVIEW: no instruction updates needed for department %s after goal change",
            department.name,
        )
