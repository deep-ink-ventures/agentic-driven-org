import contextlib
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


def _context_section(context: str) -> str:
    if not context:
        return ""
    return f"## Additional Context\n{context}"


def _detect_locale_from_text(text: str) -> str | None:
    """Best-effort locale detection from text using character/word heuristics."""
    import re

    if not text:
        return None
    lower = text.lower()
    # German indicators
    if re.search(r"\b(und|oder|ein|eine|das|der|die|ist|schreib|auf deutsch)\b", lower):
        return "de"
    # French indicators
    if re.search(r"\b(le|la|les|des|est|une|dans|pour|avec|écrire|en français)\b", lower):
        return "fr"
    # Spanish indicators
    if re.search(r"\b(el|los|las|una|del|por|con|para|escribir|en español)\b", lower):
        return "es"
    # Italian indicators
    if re.search(r"\b(il|gli|una|della|sono|con|per|scrivi|in italiano)\b", lower):
        return "it"
    return None


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def summarize_source(self, source_id: str):
    """Generate a comprehensive summary of a source document using Claude."""
    from agents.ai.claude_client import call_claude
    from projects.models import Source

    try:
        source = Source.objects.get(id=source_id)
    except Source.DoesNotExist:
        logger.error("Source %s not found", source_id)
        return

    text = source.extracted_text or source.raw_content or ""
    if not text:
        return

    # Short texts don't need summarization — use as-is
    if len(text) < 3000:
        source.summary = text
        source.save(update_fields=["summary"])
        return

    try:
        response, _usage = call_claude(
            system_prompt=(
                "You are a document analyst. Produce a comprehensive summary that preserves ALL key information. "
                "This summary will be used by AI agents as their ONLY access to this document, so nothing important "
                "can be lost. Include: main themes, specific names/places/dates, key arguments, data points, "
                "creative details (characters, settings, plot points), and any instructions or requirements. "
                "Write in the same language as the source. Be thorough — 500-2000 words depending on document length."
            ),
            user_message=f"Summarize this document comprehensively. Preserve all key details.\n\n{text}",
            max_tokens=4096,
        )
        source.summary = response.strip()
        source.save(update_fields=["summary"])
        logger.info(
            "Summarized source %s (%d chars → %d chars)",
            source.original_filename or source.id,
            len(text),
            len(source.summary),
        )
    except Exception as e:
        logger.warning("summarize_source attempt %d failed: %s", self.request.retries + 1, e)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e) from e
        logger.exception("Failed to summarize source %s", source_id)


def get_sources_context(project) -> str:
    """Get source context for prompts — uses summaries when available, full text when short."""
    from projects.models import Source

    sources_text = ""
    for s in Source.objects.filter(project=project):
        text = s.summary or s.extracted_text or s.raw_content or ""
        if not text:
            continue
        name = s.original_filename or s.url or "Text input"
        sources_text += f"\n### {name}\n{text}\n"
    return sources_text


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def bootstrap_project(self, proposal_id: str):
    """
    Analyze project sources with Claude and generate a bootstrap proposal.
    """
    import re

    from agents.ai.claude_client import call_claude_structured
    from agents.blueprints import DEPARTMENTS
    from projects.models import BootstrapProposal, Source
    from projects.prompts import BOOTSTRAP_SYSTEM_PROMPT, build_bootstrap_user_message

    try:
        proposal = BootstrapProposal.objects.select_related("project").get(id=proposal_id)
    except BootstrapProposal.DoesNotExist:
        logger.error("BootstrapProposal %s not found", proposal_id)
        return

    project = proposal.project

    proposal.status = BootstrapProposal.Status.PROCESSING
    proposal.save(update_fields=["status", "updated_at"])
    _broadcast_bootstrap(project.id, proposal.id, "processing", phase="Gathering sources")

    try:
        # Gather sources (optional — bootstrap can work with just a goal)
        source_data = []
        for s in Source.objects.filter(project=project):
            text = s.summary or s.extracted_text or s.raw_content or ""
            if not text:
                continue
            name = s.original_filename or s.url or "Text input"
            source_data.append(
                {
                    "id": str(s.id),
                    "name": name,
                    "source_type": s.source_type,
                    "text": text,
                }
            )

        _broadcast_bootstrap(project.id, proposal.id, "processing", phase="Mapping your project")

        # Available departments with their workforce agents
        available_departments = []
        for dept_slug, dept_config in DEPARTMENTS.items():
            workforce = [
                {"slug": slug, "name": bp.name, "description": bp.description}
                for slug, bp in dept_config["workforce"].items()
            ]
            available_departments.append(
                {
                    "slug": dept_slug,
                    "name": dept_config["name"],
                    "description": dept_config["description"],
                    "workforce": workforce,
                }
            )

        # Build prompt
        user_message = build_bootstrap_user_message(
            project_name=project.name,
            project_goal=project.goal,
            sources=source_data,
            available_departments=available_departments,
        )

        _broadcast_bootstrap(project.id, proposal.id, "processing", phase="Analyzing your project")

        # Stream Claude with time-based phases + content detection
        seen_names = set()
        events = []
        max_tokens = 4096
        last_broadcast_len = 0
        import time

        stream_start = time.monotonic()

        # Time-based phases so the user always sees movement
        TIMED_PHASES = [
            (0, "Analyzing sources"),
            (5, "Understanding project goals"),
            (15, "Building department structure"),
            (30, "Selecting agents"),
            (60, "Generating instructions"),
            (90, "Writing initial documents"),
            (120, "Finalizing proposal"),
        ]

        # Detect department types and agent types in streaming JSON
        dept_type_re = re.compile(r'"department_type"\s*:\s*"([^"]+)"')
        agent_type_re = re.compile(r'"agent_type"\s*:\s*"([^"]+)"')

        def on_progress(accumulated: str, tokens_so_far: int):
            nonlocal last_broadcast_len
            if len(accumulated) - last_broadcast_len < 200:
                return
            last_broadcast_len = len(accumulated)

            elapsed = time.monotonic() - stream_start

            # Detect departments and agents by their type slugs (reliable, not name-based)
            for match in dept_type_re.finditer(accumulated):
                slug = match.group(1)
                label = f"{slug.replace('_', ' ').title()} department"
                if label not in seen_names:
                    seen_names.add(label)
                    events.append(label)
            for match in agent_type_re.finditer(accumulated):
                slug = match.group(1)
                label = slug.replace("_", " ").title()
                if label not in seen_names:
                    seen_names.add(label)
                    events.append(label)

            # Phase: use content-detected events if available, otherwise time-based
            if events:
                current_phase = f"Adding {events[-1]}"
            else:
                current_phase = "Analyzing sources"
                for threshold, phase_text in TIMED_PHASES:
                    if elapsed >= threshold:
                        current_phase = phase_text

            _broadcast_bootstrap(
                project.id,
                proposal.id,
                "processing",
                phase=current_phase,
                events=events[:],
            )

        # Use structured output via forced tool call — guarantees valid JSON
        bootstrap_schema = {
            "type": "object",
            "properties": {
                "enriched_goal": {
                    "type": "string",
                    "description": "The user's original goal with misspellings fixed and formatted as clean markdown",
                },
                "summary": {
                    "type": "string",
                    "description": "2-3 sentence analysis of the project",
                },
                "departments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "department_type": {"type": "string"},
                            "agents": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "agent_type": {"type": "string"},
                                        "instructions": {"type": "string"},
                                    },
                                    "required": ["name", "agent_type", "instructions"],
                                },
                            },
                        },
                        "required": ["department_type", "agents"],
                    },
                },
            },
            "required": ["enriched_goal", "summary", "departments"],
        }

        proposal_data, _usage = call_claude_structured(
            system_prompt=BOOTSTRAP_SYSTEM_PROMPT,
            user_message=user_message,
            output_schema=bootstrap_schema,
            tool_name="submit_proposal",
            tool_description="Submit the project bootstrap proposal with departments and agents",
            max_tokens=max_tokens,
            on_progress=on_progress,
        )

        _broadcast_bootstrap(
            project.id, proposal.id, "processing", phase="Validating proposal", progress=98, events=events[:]
        )

        # Ensure ALL workforce agents are included for each department
        # (Claude may cherry-pick despite instructions — enforce in code)
        for dept_data in proposal_data.get("departments", []):
            dept_type = dept_data.get("department_type")
            if dept_type not in DEPARTMENTS:
                continue
            proposed_types = {a["agent_type"] for a in dept_data.get("agents", [])}
            for slug, bp in DEPARTMENTS[dept_type]["workforce"].items():
                if slug not in proposed_types:
                    dept_data["agents"].append(
                        {
                            "name": bp.name,
                            "agent_type": slug,
                            "instructions": "",
                        }
                    )

        # Validate proposal against schema
        proposal.proposal = proposal_data
        validation_errors = proposal.validate_proposal()
        if validation_errors:
            raise ValueError(f"Invalid proposal from Claude: {'; '.join(validation_errors)}")

        _broadcast_bootstrap(project.id, proposal.id, "processing", phase="Finalizing")

        proposal.token_usage = _usage
        proposal.status = BootstrapProposal.Status.PROPOSED
        proposal.save(update_fields=["proposal", "token_usage", "status", "updated_at"])

        logger.info("Bootstrap proposal generated for project %s", project.name)
        _broadcast_bootstrap(project.id, proposal.id, "proposed")

    except Exception as e:
        logger.warning("bootstrap_project attempt %d failed: %s", self.request.retries + 1, e)
        if self.request.retries < self.max_retries:
            proposal.status = BootstrapProposal.Status.PENDING
            proposal.save(update_fields=["status", "updated_at"])
            raise self.retry(exc=e) from e
        logger.exception("Bootstrap failed for project %s after %d retries", project.name, self.max_retries)
        proposal.status = BootstrapProposal.Status.FAILED
        proposal.error_message = str(e)[:1000]
        proposal.save(update_fields=["status", "error_message", "updated_at"])
        _broadcast_bootstrap(project.id, proposal.id, "failed", str(e)[:200])


@shared_task
def recover_stuck_proposals():
    """
    Self-healing: find proposals stuck in pending/processing and retry them.
    - pending for >30s: dispatch bootstrap_project
    - processing for >5min: reset to pending and dispatch (task likely crashed)
    """
    from datetime import timedelta

    from django.utils import timezone

    from projects.models import BootstrapProposal

    now = timezone.now()

    # Pending proposals that were never picked up (>30s old)
    pending = BootstrapProposal.objects.filter(
        status=BootstrapProposal.Status.PENDING,
        updated_at__lt=now - timedelta(seconds=30),
    )
    for p in pending:
        logger.info("Recovering pending proposal %s for project %s", p.id, p.project.name)
        bootstrap_project.delay(str(p.id))

    # Processing proposals stuck for >5min (task crashed)
    stuck = BootstrapProposal.objects.filter(
        status=BootstrapProposal.Status.PROCESSING,
        updated_at__lt=now - timedelta(minutes=5),
    )
    for p in stuck:
        logger.warning("Recovering stuck proposal %s for project %s", p.id, p.project.name)
        p.status = BootstrapProposal.Status.PENDING
        p.error_message = "Auto-recovered from stuck processing state"
        p.save(update_fields=["status", "error_message", "updated_at"])
        bootstrap_project.delay(str(p.id))


@shared_task
def archive_stale_documents():
    """Daily: archive research documents older than 30 days."""
    from datetime import timedelta

    from django.utils import timezone

    from projects.models import Document

    cutoff = timezone.now() - timedelta(days=30)
    count = Document.objects.filter(
        doc_type=Document.DocType.RESEARCH,
        is_archived=False,
        created_at__lt=cutoff,
    ).update(is_archived=True)

    if count:
        logger.info("Archived %d stale research documents", count)


def _broadcast_bootstrap(
    project_id, proposal_id, bootstrap_status, error_message="", phase="", progress=0, events=None
):
    """Send bootstrap status update via WebSocket."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"bootstrap_{project_id}",
            {
                "type": "bootstrap.status",
                "status": bootstrap_status,
                "proposal_id": str(proposal_id),
                "error_message": error_message,
                "phase": phase,
                "progress": progress,
                "events": events or [],
            },
        )
    except Exception:
        logger.exception("Failed to broadcast bootstrap status")


CONFIGURE_LEADER_SYSTEM_PROMPT = """You are a senior project strategist writing the operating manual for a department leader AI agent.

Respond with valid JSON only. No markdown fences, no explanation.

## What leader instructions must contain

The leader reads these instructions before every decision — proposing tasks, reviewing output, delegating work. They must be rich enough to run the department autonomously:

1. **Project context**: What is this project about? What are the key themes, characters, goals, constraints? Reference specific details from the sources — not generic descriptions.
2. **Department mission**: What does this department own? What does success look like?
3. **Quality bar**: What separates good output from bad in this project? What tone, style, and standards apply?
4. **Strategic priorities**: What should the department focus on first? What's the roadmap?
5. **Workforce overview**: How should the leader use each agent? What's the workflow?
6. **Output language**: All work must be in the detected language.

Write 4-6 substantial paragraphs. Think of this as a creative brief + operating manual combined.

## Rules

1. Write in the project's language (detect from goal and sources).
2. Detect the locale using ISO codes (e.g. "de", "en", "fr").
3. Reference specific details from the source materials — generic instructions will be rejected.

You MUST call the submit_config tool with your results."""

CONFIGURE_LEADER_TOOL = {
    "name": "submit_config",
    "description": "Submit the leader instructions and detected locale.",
    "input_schema": {
        "type": "object",
        "properties": {
            "leader_instructions": {
                "type": "string",
                "description": "4-6 paragraphs of detailed, project-specific leader instructions.",
            },
            "locale": {
                "type": "string",
                "description": "ISO 639-1 locale code detected from the project goal and sources (e.g. 'de', 'en', 'fr').",
            },
        },
        "required": ["leader_instructions", "locale"],
    },
}


GENERATE_DOCUMENTS_SYSTEM_PROMPT = """You are a senior project strategist creating foundational documents for a department in an AI agent platform. These documents are the department's knowledge base — agents read them to understand the project and do their work.

Respond with valid JSON only. No markdown fences, no explanation.

## Rules

1. Each document must be rich, thorough, and grounded in the project's actual source materials.
2. Reference specific details from the sources — characters, themes, settings, market data, goals, constraints.
3. Documents should be substantial (1000-3000 words each) — not bullet-point summaries but real working documents.
4. Write in the project's language (specified in the prompt).
5. Generate 2-4 documents appropriate for the department's function.
6. Avoid overlap with other departments' responsibilities.
7. Use markdown formatting with clear structure, headers, and sections.

## Document Quality Bar

Bad: "This document outlines the marketing strategy for the project."
Good: A 2000-word strategy document with specific competitive analysis, target audience segments, positioning, and actionable recommendations grounded in the source material.

## Response JSON Schema

{
    "documents": [
        {
            "title": "Document Title",
            "content": "Thorough markdown content grounded in project sources...",
            "tags": ["tag1", "tag2"]
        }
    ]
}"""


RECOMMEND_DEPARTMENTS_SYSTEM_PROMPT = """You are a project setup analyst for an AI agent platform. Given a project's context, recommend which departments and agents would be most valuable.

You MUST respond with valid JSON. No markdown, no explanation outside the JSON.

## Rules

1. Only recommend department types and agent types from the AVAILABLE list provided.
2. Consider the project's domain, goals, and existing setup.
3. Focus on creative/production agents — essential and controller agents are auto-included by the system.
4. Leaders are auto-created — do NOT include leaders.

## Response JSON Schema

{
    "departments": ["department_type_slug", ...],
    "agents": {
        "department_type_slug": ["agent_type_slug", ...],
        ...
    }
}"""


def get_department_recommendations(project) -> dict:
    """Return all departments and all agents as recommended.

    Departments are granular enough that all agents should be provisioned.
    """
    from agents.blueprints import DEPARTMENTS, get_workforce_metadata

    installed = set(project.departments.values_list("department_type", flat=True))

    departments = []
    agents = {}
    for slug, _dept in DEPARTMENTS.items():
        if slug in installed:
            continue
        departments.append(slug)
        metadata = get_workforce_metadata(slug)
        agents[slug] = [m["agent_type"] for m in metadata]

    return {"departments": departments, "agents": agents}


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def configure_new_department(self, department_id: str, context: str = ""):
    """Configure a department: leader instructions via Claude, then fan out agent + document tasks."""
    from agents.blueprints import DEPARTMENTS
    from agents.models import Agent
    from projects.models import Department

    try:
        department = Department.objects.select_related("project").get(id=department_id)
    except Department.DoesNotExist:
        logger.error("Department %s not found", department_id)
        return

    project = department.project
    department_type = department.department_type

    if department_type not in DEPARTMENTS:
        logger.error("Unknown department type: %s", department_type)
        return

    dept_config = DEPARTMENTS[department_type]
    _broadcast_department(project.id, department_id, "configuring", phase="Generating leader instructions")

    try:
        # 1. Build rich context for leader instructions
        sources_summary = get_sources_context(project)

        # Get the leader blueprint's built-in system prompt
        leader_bp = dept_config["leader"]
        leader_system_prompt = ""
        with contextlib.suppress(Exception):
            leader_system_prompt = leader_bp.system_prompt if hasattr(leader_bp, "system_prompt") else ""

        # Get workforce agent descriptions
        from agents.blueprints import get_workforce_for_department

        workforce = get_workforce_for_department(department_type)
        workforce_text = ""
        for slug, bp in workforce.items():
            cmds = bp.get_commands() if bp else []
            cmd_names = ", ".join(c["name"] for c in cmds) if cmds else "none"
            workforce_text += f"- **{slug}** ({bp.name}): {bp.description}. Commands: {cmd_names}\n"

        user_message = f"""# Project: {project.name}

<project_goal>
{project.goal or "No goal set."}
</project_goal>

## Sources
<sources>
{sources_summary or "No sources available."}
</sources>

## Department: {dept_config['name']}
{dept_config['description']}

## Leader's Built-in System Prompt (for context)
<leader_prompt>
{leader_system_prompt or "Not available."}
</leader_prompt>

## Workforce Agents this Leader Manages
{workforce_text or "No workforce agents."}

{_context_section(context)}

Write comprehensive leader instructions for this department. The leader uses these instructions to decide what tasks to create and how to coordinate the workforce."""

        # 2. Claude call for leader instructions (forced tool guarantees schema)
        from agents.ai.claude_client import call_claude_with_tools

        _response, result, _usage = call_claude_with_tools(
            system_prompt=CONFIGURE_LEADER_SYSTEM_PROMPT,
            user_message=user_message,
            tools=[CONFIGURE_LEADER_TOOL],
            force_tool="submit_config",
            max_tokens=4096,
        )

        leader_instructions = result.get("leader_instructions", "") if result else ""

        # 3. Set department-level locale from detected language
        locale = result.get("locale") if result else None
        if not locale:
            # Last-resort fallback: heuristic from project goal text
            locale = _detect_locale_from_text(project.goal or "")
        if locale:
            model_config = department.config or {}
            model_config["locale"] = locale
            department.config = model_config
            department.save(update_fields=["config"])

        # 4. Update or create leader
        leader = department.agents.filter(is_leader=True).first()
        if leader:
            if leader_instructions:
                leader.instructions = leader_instructions
            leader.status = Agent.Status.ACTIVE
            leader.save(update_fields=["instructions", "status", "updated_at"])
            _broadcast_agent(project.id, department.id, leader.id, leader.status)
        else:
            leader = Agent.objects.create(
                name=f"Head of {department.name}",
                agent_type="leader",
                department=department,
                is_leader=True,
                status=Agent.Status.ACTIVE,
                instructions=leader_instructions
                or f"Lead the {department.name} department for project: {project.name}.",
            )
            _broadcast_agent(project.id, department.id, leader.id, leader.status)

        # 4. Fan out per-agent provisioning tasks (includes ACTIVE agents needing instructions)
        provisioning_agents = department.agents.filter(is_leader=False).exclude(status=Agent.Status.FAILED)
        for agent in provisioning_agents:
            provision_single_agent.delay(str(agent.id))

        # 5. Fan out document generation
        generate_department_documents.delay(str(department.id), context)

        _broadcast_department(project.id, department_id, "configured")
        logger.info("Department %s configured, %d agents queued", department.name, provisioning_agents.count())

    except Exception as e:
        logger.warning("configure_new_department attempt %d failed: %s", self.request.retries + 1, e)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e) from e
        # Final failure — mark leader as failed, leave agents as provisioning
        # Do NOT fan out agents here — locale may not be set, they'd get wrong language
        logger.exception("Failed to configure department %s after %d retries", department_id, self.max_retries)
        leader = department.agents.filter(is_leader=True, status=Agent.Status.PROVISIONING).first()
        if leader:
            leader.status = Agent.Status.FAILED
            leader.save(update_fields=["status"])
            _broadcast_agent(project.id, department.id, leader.id, "failed", str(e)[:200])
        _broadcast_department(project.id, department_id, "failed", error_message=str(e)[:200])


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def generate_department_documents(self, department_id: str, context: str = ""):
    """Generate initial documents for a department via Claude."""
    from agents.ai.claude_client import call_claude, parse_json_response
    from agents.blueprints import DEPARTMENTS
    from projects.models import Department, Document, Tag

    try:
        department = Department.objects.select_related("project").get(id=department_id)
    except Department.DoesNotExist:
        logger.error("Department %s not found", department_id)
        return

    project = department.project
    department_type = department.department_type

    if department_type not in DEPARTMENTS:
        return

    dept_config = DEPARTMENTS[department_type]

    try:
        sources_summary = get_sources_context(project)

        existing_departments = []
        for dept in project.departments.exclude(id=department.id).prefetch_related("agents"):
            agents = [{"name": a.name, "agent_type": a.agent_type} for a in dept.agents.all()]
            existing_departments.append({"name": dept.name, "agents": agents})

        existing_text = ""
        for ed in existing_departments:
            existing_text += f"\n### {ed['name']}\n"
            for a in ed["agents"]:
                existing_text += f"- {a['name']} ({a['agent_type']})\n"

        # Get locale from department config (set by configure_new_department)
        locale = (department.config or {}).get("locale", "en")

        # Get list of agents in this department for context
        dept_agents = [
            {
                "name": a.name,
                "type": a.agent_type,
                "description": a.get_blueprint().description if a.get_blueprint() else "",
            }
            for a in department.agents.filter(is_leader=False)
        ]
        agents_text = "\n".join(f"- {a['name']} ({a['type']}): {a['description']}" for a in dept_agents)

        user_message = f"""# Project: {project.name}

<project_goal>
{project.goal or "No goal set."}
</project_goal>

## Sources
<sources>
{sources_summary or "No sources available."}
</sources>

## Department: {dept_config['name']}
{dept_config['description']}

## Agents in this Department
{agents_text or "No agents yet."}

## Existing Departments
{existing_text or "None"}

{_context_section(context)}

## Output Language: {locale}

Generate foundational documents for this department. These documents will be read by the agents listed above to inform their work. They must be written in {locale} and reference specific details from the project sources — not generic templates.

For a writers room: think series bible, character profiles, world-building guide, thematic framework.
For engineering: think architecture decisions, coding standards, API contracts.
For marketing: think brand guidelines, audience profiles, channel strategy."""

        response, _usage = call_claude(
            system_prompt=GENERATE_DOCUMENTS_SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=16384,
        )

        result = parse_json_response(response)
        if not result:
            logger.warning("Failed to parse documents response for department %s", department_id)
            return

        for doc_data in result.get("documents", []):
            doc = Document.objects.create(
                title=doc_data.get("title", "Untitled"),
                content=doc_data.get("content", ""),
                department=department,
            )
            for tag_name in doc_data.get("tags", []):
                tag, _ = Tag.objects.get_or_create(name=tag_name.lower())
                doc.tags.add(tag)

        logger.info("Generated %d documents for department %s", len(result.get("documents", [])), department.name)

    except Exception as e:
        logger.warning("generate_department_documents attempt %d failed: %s", self.request.retries + 1, e)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e) from e
        logger.exception(
            "Failed to generate documents for department %s after %d retries", department_id, self.max_retries
        )


def _broadcast_agent(project_id, department_id, agent_id, agent_status, error_message=""):
    """Send agent provisioning status update via WebSocket."""
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
                "status": agent_status,
                "error_message": error_message,
            },
        )
    except Exception:
        logger.exception("Failed to broadcast agent status")


def _broadcast_department(project_id, department_id, dept_status, error_message="", phase=""):
    """Send department configuration status update via WebSocket."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"project_{project_id}",
            {
                "type": "department.status",
                "department_id": str(department_id),
                "status": dept_status,
                "error_message": error_message,
                "phase": phase,
            },
        )
    except Exception:
        logger.exception("Failed to broadcast department status")


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def provision_single_agent(self, agent_id: str):
    """Generate tailored instructions for a single agent using Claude."""
    from agents.ai.claude_client import call_claude, parse_json_response
    from agents.models import Agent

    try:
        agent = Agent.objects.select_related("department__project").get(id=agent_id)
    except Agent.DoesNotExist:
        logger.error("Agent %s not found", agent_id)
        return

    department = agent.department
    project = department.project
    bp = agent.get_blueprint()

    _broadcast_agent(project.id, department.id, agent_id, "provisioning")

    try:
        sources_summary = get_sources_context(project)

        # Get the agent's locale from department config cascade
        locale = agent.get_config_value("locale") or "en"

        # Get the blueprint's actual system prompt for context
        bp_system_prompt = ""
        with contextlib.suppress(Exception):
            bp_system_prompt = bp.system_prompt if hasattr(bp, "system_prompt") else ""

        user_message = f"""# Project: {project.name}

<project_goal>
{project.goal or "No goal set."}
</project_goal>

## Sources
<sources>
{sources_summary or "No sources available."}
</sources>

## Department: {department.name}
Locale: {locale}

## Agent to Configure
- Type: {agent.agent_type}
- Name: {bp.name}
- Description: {bp.description}

## Agent's Built-in System Prompt (for context — this is what the agent sees when executing tasks):
<system_prompt>
{bp_system_prompt or "Not available."}
</system_prompt>

## Your Task

Write the agent's project-specific instructions. These instructions are prepended to every task the agent executes. They must:

1. Ground the agent in THIS project — reference specific characters, settings, themes, plot arcs, tone references from the sources
2. Define what this specific agent owns and delivers (not generic role descriptions)
3. Set the quality bar — what "good" looks like for this agent's output in this project
4. Specify the output language as {locale}
5. Be written in {locale}

Bad example: "Du recherchierst marktrelevante Grundlagen für die Serie."
Good example: "Du recherchierst den Berliner Immobilienmarkt als Serienkulisse — insbesondere die Verflechtung von Politik, Bankenwesen und Familienimperien. Deine Kernaufgabe ist..."

Write 3-5 substantial paragraphs. Also suggest a display name in {locale}.

Respond with JSON only, no markdown fences:
{{"instructions": "detailed project-specific instructions in {locale}...", "name": "Display Name in {locale}"}}"""

        response, _usage = call_claude(
            system_prompt=(
                "You are a senior creative writing consultant configuring AI agents for a writers room. "
                "Your job: write project-specific instructions that make each agent deeply knowledgeable about "
                "THIS project's world, characters, themes, and goals. Generic role descriptions are unacceptable — "
                "every instruction must reference concrete details from the source materials. "
                "Write in the project's language. Respond with valid JSON only, no markdown fences."
            ),
            user_message=user_message,
            max_tokens=4096,
        )

        result = parse_json_response(response)
        if result:
            if result.get("instructions"):
                agent.instructions = result["instructions"]
            if result.get("name"):
                agent.name = result["name"]

        agent.status = Agent.Status.ACTIVE
        agent.save(update_fields=["instructions", "name", "status", "updated_at"])

        _broadcast_agent(project.id, department.id, agent_id, agent.status)
        logger.info("Agent %s provisioned and activated for department %s", agent.name, department.name)

    except Exception as e:
        logger.warning("provision_single_agent attempt %d failed for %s: %s", self.request.retries + 1, agent_id, e)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e) from e
        logger.exception("Failed to provision agent %s after %d retries", agent_id, self.max_retries)
        # Only mark FAILED if agent was PROVISIONING (has required config).
        # Agents already ACTIVE stay active — instruction generation is best-effort.
        if agent.status == Agent.Status.PROVISIONING:
            agent.status = Agent.Status.FAILED
            agent.save(update_fields=["status", "updated_at"])
            _broadcast_agent(project.id, department.id, agent_id, "failed", str(e)[:200])


@shared_task
def recover_stuck_provisioning():
    """
    Self-healing: re-dispatch agents stuck in provisioning for >15 minutes.
    Runs every 15 minutes via celery beat.
    """
    from datetime import timedelta

    from django.utils import timezone

    from agents.models import Agent

    cutoff = timezone.now() - timedelta(minutes=15)
    stuck = Agent.objects.filter(
        status=Agent.Status.PROVISIONING,
        updated_at__lt=cutoff,
    ).select_related("department")

    for agent in stuck:
        logger.warning(
            "Recovering stuck provisioning for agent %s (%s) in %s",
            agent.name,
            agent.agent_type,
            agent.department.name,
        )
        provision_single_agent.delay(str(agent.id))
