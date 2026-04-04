"""
Blueprint registry.

Departments and their agents are defined by the folder structure:
  blueprints/<department_type>/leader/
  blueprints/<department_type>/workforce/<agent_type>/
"""

from agents.blueprints.marketing.leader import MarketingLeaderBlueprint
from agents.blueprints.marketing.workforce.web_researcher import WebResearcherBlueprint
from agents.blueprints.marketing.workforce.luma_researcher import LumaResearcherBlueprint
from agents.blueprints.marketing.workforce.reddit import RedditBlueprint
from agents.blueprints.marketing.workforce.twitter import TwitterBlueprint
from agents.blueprints.marketing.workforce.email_marketing import EmailMarketingBlueprint

DEPARTMENTS = {
    "marketing": {
        "name": "Marketing",
        "description": "Full-stack marketing — research, social media, email campaigns, content coordination",
        "leader": MarketingLeaderBlueprint(),
        "workforce": {
            "web_researcher": WebResearcherBlueprint(),
            "luma_researcher": LumaResearcherBlueprint(),
            "reddit": RedditBlueprint(),
            "twitter": TwitterBlueprint(),
            "email_marketing": EmailMarketingBlueprint(),
        },
        "config_schema": {},
    },
}

DEPARTMENT_TYPE_CHOICES = [
    (slug, dept["name"]) for slug, dept in DEPARTMENTS.items()
]

AGENT_TYPE_CHOICES = [("leader", "Department Leader")]
for dept in DEPARTMENTS.values():
    for slug, bp in dept["workforce"].items():
        if (slug, bp.name) not in AGENT_TYPE_CHOICES:
            AGENT_TYPE_CHOICES.append((slug, bp.name))

WORKFORCE_TYPE_CHOICES = [c for c in AGENT_TYPE_CHOICES if c[0] != "leader"]


def get_department(department_type: str) -> dict:
    dept = DEPARTMENTS.get(department_type)
    if dept is None:
        raise ValueError(f"Unknown department type: {department_type}")
    return dept


def get_blueprint(agent_type: str, department_type: str | None = None):
    if agent_type == "leader":
        if department_type is None:
            raise ValueError("department_type required for leader blueprint lookup")
        dept = get_department(department_type)
        return dept["leader"]

    if department_type:
        dept = get_department(department_type)
        bp = dept["workforce"].get(agent_type)
        if bp is None:
            raise ValueError(f"Agent type '{agent_type}' not available in department '{department_type}'")
        return bp

    for dept in DEPARTMENTS.values():
        bp = dept["workforce"].get(agent_type)
        if bp is not None:
            return bp

    raise ValueError(f"Unknown agent type: {agent_type}")


def get_workforce_for_department(department_type: str) -> dict:
    dept = get_department(department_type)
    return dept["workforce"]


def get_department_config_schema(department_type: str) -> dict:
    """Get the config JSON Schema for a department type."""
    dept = DEPARTMENTS.get(department_type)
    if not dept:
        return {"type": "object", "properties": {}, "additionalProperties": False}
    schema_def = dept.get("config_schema", {})
    if not schema_def:
        return {"type": "object", "properties": {}, "additionalProperties": False}
    properties = {}
    required = []
    for key, spec in schema_def.items():
        prop = {"description": spec.get("description", ""), "title": spec.get("label", key)}
        t = spec.get("type", "str")
        if t == "str":
            prop["type"] = "string"
        elif t == "list":
            prop["type"] = "array"
        elif t == "dict":
            prop["type"] = "object"
        properties[key] = prop
        if spec.get("required"):
            required.append(key)
    result = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        result["required"] = required
    return result
