"""
Blueprint registry.

Departments and their agents are defined by the folder structure:
  blueprints/<department_type>/leader/     — one leader per department
  blueprints/<department_type>/workforce/<agent_type>/  — workforce agents

The registry is the single source of truth for what departments and agent types exist.
"""

from agents.blueprints.social_media.leader import DepartmentLeaderBlueprint as SocialMediaLeader
from agents.blueprints.social_media.workforce.twitter import TwitterBlueprint
from agents.blueprints.social_media.workforce.reddit import RedditBlueprint


# ── Department registry ──────────────────────────────────────────────────────

DEPARTMENTS = {
    "social_media": {
        "name": "Social Media",
        "description": "Manages social media presence across platforms — engagement, content creation, campaigns",
        "leader": SocialMediaLeader(),
        "workforce": {
            "twitter": TwitterBlueprint(),
            "reddit": RedditBlueprint(),
        },
    },
    # "engineering": {
    #     "name": "Engineering",
    #     "description": "Software development and technical operations",
    #     "leader": EngineeringLeader(),
    #     "workforce": {},
    # },
}

# Choices for Department.department_type
DEPARTMENT_TYPE_CHOICES = [
    (slug, dept["name"]) for slug, dept in DEPARTMENTS.items()
]

# Flat agent type choices (for Agent.agent_type) — includes "leader" + all workforce types
AGENT_TYPE_CHOICES = [("leader", "Department Leader")]
for dept in DEPARTMENTS.values():
    for slug, bp in dept["workforce"].items():
        if (slug, bp.name) not in AGENT_TYPE_CHOICES:
            AGENT_TYPE_CHOICES.append((slug, bp.name))

# Workforce types only (excludes leader) — used by bootstrap prompt
WORKFORCE_TYPE_CHOICES = [c for c in AGENT_TYPE_CHOICES if c[0] != "leader"]


def get_department(department_type: str) -> dict:
    """Get department config by type slug."""
    dept = DEPARTMENTS.get(department_type)
    if dept is None:
        raise ValueError(f"Unknown department type: {department_type}")
    return dept


def get_blueprint(agent_type: str, department_type: str | None = None):
    """
    Get blueprint instance by agent_type, optionally scoped to a department.

    For leaders: returns the department-specific leader blueprint.
    For workforce: returns the workforce blueprint (validates it belongs to the department if given).
    """
    if agent_type == "leader":
        if department_type is None:
            raise ValueError("department_type required for leader blueprint lookup")
        dept = get_department(department_type)
        return dept["leader"]

    # Workforce — search all departments or validate against specific one
    if department_type:
        dept = get_department(department_type)
        bp = dept["workforce"].get(agent_type)
        if bp is None:
            raise ValueError(f"Agent type '{agent_type}' not available in department '{department_type}'")
        return bp

    # No department specified — search all (backwards compat)
    for dept in DEPARTMENTS.values():
        bp = dept["workforce"].get(agent_type)
        if bp is not None:
            return bp

    raise ValueError(f"Unknown agent type: {agent_type}")


def get_workforce_for_department(department_type: str) -> dict:
    """Get available workforce blueprints for a department type."""
    dept = get_department(department_type)
    return dept["workforce"]
