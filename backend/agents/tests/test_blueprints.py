import pytest
from unittest.mock import patch, MagicMock

from agents.blueprints.base import (
    BaseBlueprint,
    WorkforceBlueprint,
    LeaderBlueprint,
    command,
)
from agents.blueprints import (
    get_blueprint,
    AGENT_TYPE_CHOICES,
    WORKFORCE_TYPE_CHOICES,
)
from agents.models import Agent, AgentTask
from projects.models import Project, Department, Document


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(email="test@example.com", password="pass")


@pytest.fixture
def project(user):
    return Project.objects.create(name="Acme Corp", goal="World domination", owner=user)


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="marketing", project=project)


@pytest.fixture
def leader_agent(department):
    return Agent.objects.create(
        name="Growth Leader",
        agent_type="leader",
        department=department,
        is_leader=True,
        instructions="Focus on crypto audience",
        is_active=True,
    )


@pytest.fixture
def twitter_agent(department):
    return Agent.objects.create(
        name="Twitter Guy",
        agent_type="twitter",
        department=department,
        instructions="Be witty",
        is_active=True,
    )


@pytest.fixture
def reddit_agent(department):
    return Agent.objects.create(
        name="Reddit Poster",
        agent_type="reddit",
        department=department,
        is_active=True,
    )


@pytest.fixture
def doc(department):
    return Document.objects.create(
        title="Brand Guidelines",
        content="Use friendly tone. Avoid jargon.",
        department=department,
    )


# ── Command decorator ───────────────────────────────────────────────────────


class TestCommandDecorator:
    def test_registers_metadata(self):
        @command(name="test-cmd", description="A test command", schedule="hourly")
        def my_func(self, agent):
            pass

        assert my_func._command_meta == {
            "name": "test-cmd",
            "description": "A test command",
            "schedule": "hourly",
            "model": None,
            "max_tokens": None,
        }

    def test_no_schedule(self):
        @command(name="on-demand", description="On demand only")
        def my_func(self, agent):
            pass

        assert my_func._command_meta["schedule"] is None


# ── BaseBlueprint ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestBaseBlueprint:
    def test_get_commands(self):
        bp = get_blueprint("twitter")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "place-content" in names
        assert "post-content" in names
        assert "search-trends" in names

    def test_get_scheduled_commands_hourly(self):
        bp = get_blueprint("twitter")
        hourly = bp.get_scheduled_commands("hourly")
        names = {c["name"] for c in hourly}
        assert "place-content" in names
        assert "post-content" not in names  # daily

    def test_get_scheduled_commands_daily(self):
        bp = get_blueprint("twitter")
        daily = bp.get_scheduled_commands("daily")
        names = {c["name"] for c in daily}
        assert "post-content" in names

    def test_run_command_dispatches(self, twitter_agent):
        bp = get_blueprint("twitter")
        result = bp.run_command("place-content", twitter_agent)
        assert "exec_summary" in result

    def test_run_command_unknown_raises(self, twitter_agent):
        bp = get_blueprint("twitter")
        with pytest.raises(ValueError, match="Unknown command"):
            bp.run_command("nonexistent", twitter_agent)


# ── Blueprint registry ──────────────────────────────────────────────────────


class TestBlueprintRegistry:
    def test_get_blueprint_twitter(self):
        from agents.blueprints.marketing.workforce.twitter.agent import TwitterBlueprint
        assert isinstance(get_blueprint("twitter", "marketing"), TwitterBlueprint)

    def test_get_blueprint_reddit(self):
        from agents.blueprints.marketing.workforce.reddit.agent import RedditBlueprint
        assert isinstance(get_blueprint("reddit", "marketing"), RedditBlueprint)

    def test_get_blueprint_leader(self):
        from agents.blueprints.marketing.leader.agent import MarketingLeaderBlueprint
        assert isinstance(get_blueprint("leader", "marketing"), MarketingLeaderBlueprint)

    def test_get_blueprint_leader_requires_department(self):
        with pytest.raises(ValueError, match="department_type required"):
            get_blueprint("leader")

    def test_get_blueprint_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown agent type"):
            get_blueprint("unknown_type")

    def test_agent_type_choices_contains_expected(self):
        slugs = {slug for slug, _ in AGENT_TYPE_CHOICES}
        assert slugs >= {"leader", "twitter", "reddit", "web_researcher", "luma_researcher", "email_marketing"}

    def test_workforce_type_choices_excludes_leader(self):
        slugs = {slug for slug, _ in WORKFORCE_TYPE_CHOICES}
        assert "leader" not in slugs
        assert "twitter" in slugs
        assert "reddit" in slugs
        assert "web_researcher" in slugs
        assert "luma_researcher" in slugs
        assert "email_marketing" in slugs


# ── Abstract contract checks ────────────────────────────────────────────────


class TestBlueprintAbstracts:
    def test_workforce_has_execute_task(self):
        assert hasattr(WorkforceBlueprint, "execute_task")
        # It is abstract
        assert getattr(WorkforceBlueprint.execute_task, "__isabstractmethod__", False)

    def test_leader_has_execute_task(self):
        assert hasattr(LeaderBlueprint, "execute_task")
        assert getattr(LeaderBlueprint.execute_task, "__isabstractmethod__", False)

    def test_leader_has_generate_task_proposal(self):
        assert hasattr(LeaderBlueprint, "generate_task_proposal")
        assert getattr(
            LeaderBlueprint.generate_task_proposal, "__isabstractmethod__", False
        )


# ── build_system_prompt / build_context_message / get_context ────────────────


@pytest.mark.django_db
class TestBlueprintPrompts:
    def test_build_system_prompt_includes_skills(self, twitter_agent):
        bp = get_blueprint("twitter")
        prompt = bp.build_system_prompt(twitter_agent)
        assert "Your Skills" in prompt
        assert "Twitter" in prompt or "tweet" in prompt.lower()

    def test_build_system_prompt_includes_instructions(self, twitter_agent):
        bp = get_blueprint("twitter")
        prompt = bp.build_system_prompt(twitter_agent)
        assert "Be witty" in prompt
        assert "Additional Instructions" in prompt

    def test_build_system_prompt_no_instructions_section_when_empty(self, reddit_agent):
        bp = get_blueprint("reddit")
        prompt = bp.build_system_prompt(reddit_agent)
        assert "Additional Instructions" not in prompt

    def test_build_context_message_includes_project_and_dept(self, twitter_agent):
        bp = get_blueprint("twitter")
        msg = bp.build_context_message(twitter_agent)
        assert "Acme Corp" in msg
        assert "World domination" in msg
        assert "Marketing" in msg

    def test_get_context_gathers_correct_data(
        self, twitter_agent, reddit_agent, leader_agent, doc
    ):
        # Create a task for a sibling agent
        AgentTask.objects.create(
            agent=reddit_agent,
            status=AgentTask.Status.DONE,
            exec_summary="Posted on r/crypto",
        )
        # Create a task for the agent itself
        AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.DONE,
            exec_summary="Tweeted about launch",
            report="Got 50 likes",
        )

        bp = get_blueprint("twitter")
        ctx = bp.get_context(twitter_agent)

        assert ctx["project_name"] == "Acme Corp"
        assert ctx["project_goal"] == "World domination"
        assert ctx["department_name"] == "Marketing"
        assert "Brand Guidelines" in ctx["department_documents"]
        assert "Reddit Poster" in ctx["sibling_agents"]
        assert "Posted on r/crypto" in ctx["sibling_agents"]
        assert "Tweeted about launch" in ctx["own_recent_tasks"]
        assert "Got 50 likes" in ctx["own_recent_tasks"]
        assert ctx["agent_instructions"] == "Be witty"
