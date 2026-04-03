"""
Bootstrap prompt for Claude to analyze project sources and propose setup.
"""


BOOTSTRAP_SYSTEM_PROMPT = """You are a project setup analyst for an AI agent platform. Your job is to analyze source materials provided by a user and propose the optimal configuration of departments, AI agents, and department documents.

You MUST respond with valid JSON matching the exact schema below. No markdown, no explanation outside the JSON.

## Rules

1. Only propose agent types from the AVAILABLE AGENT TYPES list provided. Do not invent new types.
2. Each department should have at least one agent and at least one document.
3. Agent instructions should be specific and derived from the source material — reference the project's domain, audience, tone, and goals.
4. Documents should extract and structure useful information from the sources — branding guidelines, target audience profiles, content strategies, etc.
5. Explain what you extracted from each source and why. If a source wasn't useful, explain why it was ignored.
6. Keep document content in markdown format, actionable and concise.
7. Set campaign agents as needing auto_exec_hourly=false and subordinate agents (twitter, reddit) as auto_exec_hourly=false initially. The user will enable these manually.

## Response JSON Schema

{
    "summary": "2-3 sentence analysis of the project and what was found in the sources",
    "departments": [
        {
            "name": "Department Name",
            "documents": [
                {
                    "title": "Document Title",
                    "content": "Markdown content...",
                    "tags": ["tag1", "tag2"]
                }
            ],
            "agents": [
                {
                    "name": "Human-friendly Agent Name",
                    "agent_type": "one_of_available_types",
                    "instructions": "Specific instructions for this agent derived from sources...",
                    "auto_exec_hourly": false
                }
            ]
        }
    ],
    "ignored_content": [
        {
            "source_id": "uuid-string",
            "source_name": "filename or description",
            "reason": "Why this source was not useful"
        }
    ]
}"""


def build_bootstrap_user_message(
    project_name: str,
    project_goal: str,
    sources: list[dict],
    available_types: list[dict],
) -> str:
    """
    Build the user message for the bootstrap prompt.

    Args:
        project_name: Name of the project
        project_goal: Project goal in markdown
        sources: List of dicts with keys: id, name, source_type, text
        available_types: List of dicts with keys: slug, name, description
    """
    types_text = "\n".join(
        f"- **{t['slug']}** ({t['name']}): {t['description']}"
        for t in available_types
    )

    sources_text = ""
    for s in sources:
        sources_text += f"\n\n### Source: {s['name']} (type: {s['source_type']}, id: {s['id']})\n"
        text = s["text"]
        if len(text) > 10000:
            text = text[:10000] + "\n\n[... truncated ...]"
        sources_text += text

    return f"""# Project: {project_name}

## Goal
{project_goal}

## Available Agent Types
{types_text}

## Source Materials
{sources_text}

Analyze these sources and propose the optimal project setup. Respond with JSON only."""
