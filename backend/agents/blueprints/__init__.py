"""
Blueprint registry.

Departments and their agents are defined by the folder structure:
  blueprints/<department_type>/leader/
  blueprints/<department_type>/workforce/<agent_type>/
"""

from agents.blueprints.engineering.leader import EngineeringLeaderBlueprint
from agents.blueprints.marketing.leader import MarketingLeaderBlueprint
from agents.blueprints.marketing.workforce.content_reviewer import ContentReviewerBlueprint
from agents.blueprints.marketing.workforce.email_marketing import EmailMarketingBlueprint
from agents.blueprints.marketing.workforce.luma_researcher import LumaResearcherBlueprint
from agents.blueprints.marketing.workforce.reddit import RedditBlueprint
from agents.blueprints.marketing.workforce.twitter import TwitterBlueprint
from agents.blueprints.marketing.workforce.web_researcher import WebResearcherBlueprint

# Workforce blueprints — imported individually so partially-implemented departments still load
_engineering_workforce = {}
_workforce_imports = {
    "ticket_manager": ("agents.blueprints.engineering.workforce.ticket_manager", "TicketManagerBlueprint"),
    "backend_engineer": ("agents.blueprints.engineering.workforce.backend_engineer", "BackendEngineerBlueprint"),
    "frontend_engineer": ("agents.blueprints.engineering.workforce.frontend_engineer", "FrontendEngineerBlueprint"),
    "test_engineer": ("agents.blueprints.engineering.workforce.test_engineer", "TestEngineerBlueprint"),
    "review_engineer": ("agents.blueprints.engineering.workforce.review_engineer", "ReviewEngineerBlueprint"),
    "security_auditor": ("agents.blueprints.engineering.workforce.security_auditor", "SecurityAuditorBlueprint"),
    "accessibility_engineer": (
        "agents.blueprints.engineering.workforce.accessibility_engineer",
        "AccessibilityEngineerBlueprint",
    ),
    "ux_designer": (
        "agents.blueprints.engineering.workforce.ux_designer",
        "UxDesignerBlueprint",
    ),
    "design_qa": (
        "agents.blueprints.engineering.workforce.design_qa",
        "DesignQaBlueprint",
    ),
}
for _slug, (_mod_path, _cls_name) in _workforce_imports.items():
    try:
        import importlib

        _mod = importlib.import_module(_mod_path)
        _engineering_workforce[_slug] = getattr(_mod, _cls_name)()
    except (ImportError, AttributeError):
        pass

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
            "content_reviewer": ContentReviewerBlueprint(),
        },
        "config_schema": {},
    },
}

# ── Writers Room ─────────────────────────────────────────────────────────────

try:
    from agents.blueprints.writers_room.leader import WritersRoomLeaderBlueprint
except ImportError:
    WritersRoomLeaderBlueprint = None

_writers_room_workforce = {}
_writers_room_imports = {
    "story_researcher": ("agents.blueprints.writers_room.workforce.story_researcher", "StoryResearcherBlueprint"),
    "story_architect": ("agents.blueprints.writers_room.workforce.story_architect", "StoryArchitectBlueprint"),
    "character_designer": ("agents.blueprints.writers_room.workforce.character_designer", "CharacterDesignerBlueprint"),
    "dialog_writer": ("agents.blueprints.writers_room.workforce.dialog_writer", "DialogWriterBlueprint"),
    "market_analyst": ("agents.blueprints.writers_room.workforce.market_analyst", "MarketAnalystBlueprint"),
    "structure_analyst": ("agents.blueprints.writers_room.workforce.structure_analyst", "StructureAnalystBlueprint"),
    "character_analyst": ("agents.blueprints.writers_room.workforce.character_analyst", "CharacterAnalystBlueprint"),
    "dialogue_analyst": ("agents.blueprints.writers_room.workforce.dialogue_analyst", "DialogueAnalystBlueprint"),
    "format_analyst": ("agents.blueprints.writers_room.workforce.format_analyst", "FormatAnalystBlueprint"),
    "production_analyst": ("agents.blueprints.writers_room.workforce.production_analyst", "ProductionAnalystBlueprint"),
    "creative_reviewer": ("agents.blueprints.writers_room.workforce.creative_reviewer", "CreativeReviewerBlueprint"),
    "authenticity_analyst": (
        "agents.blueprints.writers_room.workforce.authenticity_analyst.agent",
        "AuthenticityAnalystBlueprint",
    ),
    "lead_writer": ("agents.blueprints.writers_room.workforce.lead_writer", "LeadWriterBlueprint"),
}
for _slug, (_mod_path, _cls_name) in _writers_room_imports.items():
    try:
        _mod = importlib.import_module(_mod_path)
        _writers_room_workforce[_slug] = getattr(_mod, _cls_name)()
    except (ImportError, AttributeError):
        pass

if WritersRoomLeaderBlueprint is not None:
    _writers_room_leader = WritersRoomLeaderBlueprint()
    DEPARTMENTS["writers_room"] = {
        "name": "Writers Room",
        "description": "AI-powered writers room — creative writing and professional coverage analysis for screenplays, novels, theatre, series, and any narrative format",
        "leader": _writers_room_leader,
        "workforce": _writers_room_workforce,
        "config_schema": _writers_room_leader.config_schema,
    }

# ── Engineering ──────────────────────────────────────────────────────────────

_engineering_leader = EngineeringLeaderBlueprint()
DEPARTMENTS["engineering"] = {
    "name": "Engineering",
    "description": "Autonomous software engineering — goal decomposition, implementation, testing, code review, security audits, and accessibility checks",
    "leader": _engineering_leader,
    "workforce": _engineering_workforce,
    "config_schema": _engineering_leader.config_schema,
}

# ── Sales ───────────────────────────────────────────────────────────────────

try:
    from agents.blueprints.sales.leader import SalesLeaderBlueprint
except ImportError:
    SalesLeaderBlueprint = None

_sales_workforce = {}
_sales_imports = {
    "researcher": ("agents.blueprints.sales.workforce.researcher", "ResearcherBlueprint"),
    "strategist": ("agents.blueprints.sales.workforce.strategist", "StrategistBlueprint"),
    "pitch_personalizer": ("agents.blueprints.sales.workforce.pitch_personalizer", "PitchPersonalizerBlueprint"),
    "sales_qa": ("agents.blueprints.sales.workforce.sales_qa", "SalesQaBlueprint"),
    "authenticity_analyst": (
        "agents.blueprints.sales.workforce.authenticity_analyst",
        "AuthenticityAnalystBlueprint",
    ),
    "email_outreach": ("agents.blueprints.sales.workforce.email_outreach", "EmailOutreachBlueprint"),
}
for _slug, (_mod_path, _cls_name) in _sales_imports.items():
    try:
        _mod = importlib.import_module(_mod_path)
        _sales_workforce[_slug] = getattr(_mod, _cls_name)()
    except (ImportError, AttributeError):
        pass

if SalesLeaderBlueprint is not None:
    _sales_leader = SalesLeaderBlueprint()
    DEPARTMENTS["sales"] = {
        "name": "Sales",
        "description": (
            "Outbound sales pipeline — industry research, target strategy with narrative design, "
            "parallel personalization via cloned agents, QA review loops, CSV-driven dispatch"
        ),
        "leader": _sales_leader,
        "workforce": _sales_workforce,
        "config_schema": _sales_leader.config_schema,
    }

# ── Community & Partnerships ────────────────────────────────────────────────

try:
    from agents.blueprints.community.leader import CommunityLeaderBlueprint
except ImportError:
    CommunityLeaderBlueprint = None

_community_workforce = {}
_community_imports = {
    "ecosystem_researcher": (
        "agents.blueprints.community.workforce.ecosystem_researcher",
        "EcosystemResearcherBlueprint",
    ),
    "ecosystem_analyst": ("agents.blueprints.community.workforce.ecosystem_analyst", "EcosystemAnalystBlueprint"),
    "partnership_writer": ("agents.blueprints.community.workforce.partnership_writer", "PartnershipWriterBlueprint"),
    "partnership_reviewer": (
        "agents.blueprints.community.workforce.partnership_reviewer",
        "PartnershipReviewerBlueprint",
    ),
}
for _slug, (_mod_path, _cls_name) in _community_imports.items():
    try:
        _mod = importlib.import_module(_mod_path)
        _community_workforce[_slug] = getattr(_mod, _cls_name)()
    except (ImportError, AttributeError):
        pass

if CommunityLeaderBlueprint is not None:
    _community_leader = CommunityLeaderBlueprint()
    DEPARTMENTS["community"] = {
        "name": "Community & Partnerships",
        "description": "Ecosystem mapping and partnership development — research communities, propose collaborations, build relationships with quality review loops",
        "leader": _community_leader,
        "workforce": _community_workforce,
        "config_schema": _community_leader.config_schema,
    }

# ── Problem Solver ─────────────────────────────────────────────────────────

try:
    from agents.blueprints.problem_solver.leader import ProblemSolverLeaderBlueprint
except ImportError:
    ProblemSolverLeaderBlueprint = None

_problem_solver_workforce = {}
_problem_solver_imports = {
    "out_of_box_thinker": (
        "agents.blueprints.problem_solver.workforce.out_of_box_thinker",
        "OutOfBoxThinkerBlueprint",
    ),
    "playground": ("agents.blueprints.problem_solver.workforce.playground", "PlaygroundBlueprint"),
    "synthesizer": ("agents.blueprints.problem_solver.workforce.synthesizer", "SynthesizerBlueprint"),
    "reviewer": ("agents.blueprints.problem_solver.workforce.reviewer", "ReviewerBlueprint"),
}
for _slug, (_mod_path, _cls_name) in _problem_solver_imports.items():
    try:
        _mod = importlib.import_module(_mod_path)
        _problem_solver_workforce[_slug] = getattr(_mod, _cls_name)()
    except (ImportError, AttributeError):
        pass

if ProblemSolverLeaderBlueprint is not None:
    _problem_solver_leader = ProblemSolverLeaderBlueprint()
    DEPARTMENTS["problem_solver"] = {
        "name": "Problem Solver",
        "description": (
            "First-principles problem decomposition, cross-domain ideation, "
            "parallel hypothesis testing, and validated proof-of-concept synthesis"
        ),
        "leader": _problem_solver_leader,
        "workforce": _problem_solver_workforce,
        "config_schema": _problem_solver_leader.config_schema,
    }

DEPARTMENT_TYPE_CHOICES = [(slug, dept["name"]) for slug, dept in DEPARTMENTS.items()]

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


def get_workforce_metadata(department_type: str) -> list[dict]:
    """Return all workforce agents for a department with essential/controls metadata."""
    try:
        workforce = get_workforce_for_department(department_type)
    except ValueError:
        return []
    if not workforce:
        return []
    return [
        {
            "agent_type": slug,
            "name": bp.name,
            "description": bp.description,
            "essential": bp.essential,
            "controls": bp.controls,
        }
        for slug, bp in workforce.items()
    ]


def get_department_config_schema(department_type: str) -> dict:
    """Get the config JSON Schema for a department type.

    Uses the leader blueprint's get_config_json_schema() to avoid duplicating
    type conversion logic (email, bool, etc.).
    """
    dept = DEPARTMENTS.get(department_type)
    if not dept:
        return {"type": "object", "properties": {}, "additionalProperties": False}
    leader = dept.get("leader")
    if leader and leader.config_schema:
        return leader.get_config_json_schema()
    return {"type": "object", "properties": {}, "additionalProperties": False}
