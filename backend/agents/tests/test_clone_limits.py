import pytest

from agents.blueprints.base import LeaderBlueprint
from agents.models import Agent, ClonedAgent
from projects.models import Department, Project, Sprint


class _StubLeader(LeaderBlueprint):
    """Minimal concrete subclass for testing create_clones."""

    def system_prompt(self, agent, task):
        return "stub"


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(email="test@test.com", password="pass")


@pytest.fixture
def project(user):
    return Project.objects.create(name="Clone Test Project", goal="Test clones", owner=user)


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="marketing", project=project)


@pytest.fixture
def sprint(department, user):
    s = Sprint.objects.create(project=department.project, text="Clone test sprint", created_by=user)
    s.departments.add(department)
    return s


@pytest.fixture
def parent_agent(department):
    return Agent.objects.create(
        name="Clone Parent",
        agent_type="leader",
        department=department,
        is_leader=True,
        status="active",
    )


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_create_clones_within_limit(settings, parent_agent, sprint):
    settings.AGENT_MAX_CLONES_PER_SPRINT = 10
    bp = _StubLeader()
    clones = bp.create_clones(parent_agent, count=5, sprint=sprint)
    assert len(clones) == 5
    assert ClonedAgent.objects.filter(sprint=sprint).count() == 5


@pytest.mark.django_db
def test_create_clones_at_limit(settings, parent_agent, sprint):
    settings.AGENT_MAX_CLONES_PER_SPRINT = 10
    bp = _StubLeader()
    clones = bp.create_clones(parent_agent, count=10, sprint=sprint)
    assert len(clones) == 10
    assert ClonedAgent.objects.filter(sprint=sprint).count() == 10


@pytest.mark.django_db
def test_create_clones_over_limit_raises(settings, parent_agent, sprint):
    settings.AGENT_MAX_CLONES_PER_SPRINT = 10
    bp = _StubLeader()
    with pytest.raises(ValueError, match="exceeds max"):
        bp.create_clones(parent_agent, count=11, sprint=sprint)


@pytest.mark.django_db
def test_create_clones_way_over_limit_raises(settings, parent_agent, sprint):
    settings.AGENT_MAX_CLONES_PER_SPRINT = 10
    bp = _StubLeader()
    with pytest.raises(ValueError, match="exceeds max"):
        bp.create_clones(parent_agent, count=500, sprint=sprint)


@pytest.mark.django_db
def test_no_clones_created_on_rejection(settings, parent_agent, sprint):
    settings.AGENT_MAX_CLONES_PER_SPRINT = 10
    bp = _StubLeader()
    with pytest.raises(ValueError):
        bp.create_clones(parent_agent, count=50, sprint=sprint)
    assert ClonedAgent.objects.filter(sprint=sprint).count() == 0
