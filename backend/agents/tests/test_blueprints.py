import pytest

from agents.blueprints import (
    AGENT_TYPE_CHOICES,
    WORKFORCE_TYPE_CHOICES,
    get_blueprint,
)
from agents.blueprints.base import (
    VERDICT_TOOL,
    LeaderBlueprint,
    WorkforceBlueprint,
    command,
)
from agents.models import Agent, AgentTask
from projects.models import Department, Document, Project

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
        status="active",
    )


@pytest.fixture
def twitter_agent(department):
    return Agent.objects.create(
        name="Twitter Guy",
        agent_type="twitter",
        department=department,
        instructions="Be witty",
        status="active",
    )


@pytest.fixture
def reddit_agent(department):
    return Agent.objects.create(
        name="Reddit Poster",
        agent_type="reddit",
        department=department,
        status="active",
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
        # It is concrete (default implementation calls Claude)
        assert not getattr(WorkforceBlueprint.execute_task, "__isabstractmethod__", False)

    def test_leader_has_execute_task(self):
        assert hasattr(LeaderBlueprint, "execute_task")
        # It is concrete (default delegation implementation)
        assert not getattr(LeaderBlueprint.execute_task, "__isabstractmethod__", False)

    def test_leader_has_generate_task_proposal(self):
        assert hasattr(LeaderBlueprint, "generate_task_proposal")
        assert callable(LeaderBlueprint.generate_task_proposal)


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

    def test_get_context_gathers_correct_data(self, twitter_agent, reddit_agent, leader_agent, doc):
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


# ── Blueprint metadata (essential / controls) ────────────────────────────────


@pytest.mark.django_db
class TestBlueprintMetadata:
    def test_base_blueprint_defaults(self):
        from agents.blueprints.marketing.workforce.twitter.agent import TwitterBlueprint

        bp = TwitterBlueprint()
        assert bp.essential is False
        assert bp.controls is None

    def test_essential_field_on_blueprint(self):
        from agents.blueprints.writers_room.workforce.format_analyst.agent import FormatAnalystBlueprint

        bp = FormatAnalystBlueprint()
        assert bp.essential is True

    def test_controls_field_string(self):
        from agents.blueprints.writers_room.workforce.market_analyst.agent import MarketAnalystBlueprint

        bp = MarketAnalystBlueprint()
        assert bp.controls == "story_researcher"

    def test_controls_field_list(self):
        from agents.blueprints.engineering.workforce.review_engineer.agent import ReviewEngineerBlueprint

        bp = ReviewEngineerBlueprint()
        assert bp.controls == ["backend_engineer", "frontend_engineer"]


# ── get_workforce_metadata ───────────────────────────────────────────────────


class TestGetWorkforceMetadata:
    def test_returns_all_agents_with_metadata(self):
        from agents.blueprints import get_workforce_metadata

        metadata = get_workforce_metadata("writers_room")
        slugs = {m["agent_type"] for m in metadata}
        assert "dialog_writer" in slugs
        assert "dialogue_analyst" in slugs
        assert "format_analyst" in slugs

    def test_includes_essential_flag(self):
        from agents.blueprints import get_workforce_metadata

        metadata = get_workforce_metadata("writers_room")
        by_slug = {m["agent_type"]: m for m in metadata}
        assert by_slug["format_analyst"]["essential"] is True
        assert by_slug["dialog_writer"]["essential"] is False

    def test_includes_controls_field(self):
        from agents.blueprints import get_workforce_metadata

        metadata = get_workforce_metadata("writers_room")
        by_slug = {m["agent_type"]: m for m in metadata}
        assert by_slug["market_analyst"]["controls"] == "story_researcher"
        assert by_slug["dialog_writer"]["controls"] is None

    def test_includes_name_and_description(self):
        from agents.blueprints import get_workforce_metadata

        metadata = get_workforce_metadata("writers_room")
        for m in metadata:
            assert "name" in m
            assert "description" in m
            assert len(m["name"]) > 0

    def test_unknown_department_returns_empty(self):
        from agents.blueprints import get_workforce_metadata

        metadata = get_workforce_metadata("nonexistent")
        assert metadata == []


# ── Leader document creation ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestLeaderDocumentCreation:
    def test_leader_writes_progress_doc_before_planning(self, department, user):
        from unittest.mock import patch

        from agents.blueprints.base import LeaderBlueprint
        from agents.models import Agent, AgentTask
        from projects.models import Document, Sprint

        class ConcreteLeaderBlueprint(LeaderBlueprint):
            name = "Test Leader"
            description = "A test leader"
            system_prompt = "You are a test leader."

        sprint = Sprint.objects.create(
            project=department.project,
            text="Write pilot episode",
            created_by=user,
        )
        sprint.departments.add(department)

        leader = Agent.objects.create(
            name="Test Leader",
            agent_type="leader",
            department=department,
            is_leader=True,
            status="active",
        )

        # Add a workforce agent so generate_task_proposal doesn't bail early
        Agent.objects.create(
            name="Twitter Guy",
            agent_type="twitter",
            department=department,
            is_leader=False,
            status="active",
        )

        AgentTask.objects.create(
            agent=leader,
            sprint=sprint,
            status=AgentTask.Status.DONE,
            exec_summary="Analyze characters",
            report="Found three strong protagonist candidates with distinct arcs.",
        )
        AgentTask.objects.create(
            agent=leader,
            sprint=sprint,
            status=AgentTask.Status.DONE,
            exec_summary="Draft outline",
            report="Three-act structure with dual timelines established.",
        )

        with patch("agents.ai.claude_client.call_claude") as mock_claude:
            mock_claude.return_value = (
                '{"sprint_done": false, "exec_summary": "Next task", '
                '"tasks": [{"target_agent_type": "twitter", '
                '"command_name": "post-content", "exec_summary": "Post content", '
                '"step_plan": "Post to Twitter.", "depends_on_previous": false}]}',
                {"input_tokens": 100, "output_tokens": 50},
            )

            blueprint = ConcreteLeaderBlueprint()
            blueprint.generate_task_proposal(leader)

        progress_docs = Document.objects.filter(
            department=department,
            document_type="sprint_progress",
            sprint=sprint,
        )
        assert progress_docs.count() == 1
        doc = progress_docs.first()
        assert "Analyze characters" in doc.content or "protagonist" in doc.content
        assert doc.is_archived is False

    def test_no_progress_doc_when_no_completed_tasks(self, department, user):
        from unittest.mock import patch

        from agents.blueprints.base import LeaderBlueprint
        from agents.models import Agent
        from projects.models import Document, Sprint

        class ConcreteLeaderBlueprint(LeaderBlueprint):
            name = "Test Leader"
            description = "A test leader"
            system_prompt = "You are a test leader."

        sprint = Sprint.objects.create(
            project=department.project,
            text="Fresh sprint",
            created_by=user,
        )
        sprint.departments.add(department)

        leader = Agent.objects.create(
            name="Test Leader",
            agent_type="leader",
            department=department,
            is_leader=True,
            status="active",
        )

        # Add a workforce agent so generate_task_proposal doesn't bail early
        Agent.objects.create(
            name="Twitter Guy",
            agent_type="twitter",
            department=department,
            is_leader=False,
            status="active",
        )

        count_before = Document.objects.filter(department=department).count()

        with patch("agents.ai.claude_client.call_claude") as mock_claude:
            mock_claude.return_value = (
                '{"sprint_done": false, "exec_summary": "First task", '
                '"tasks": [{"target_agent_type": "twitter", '
                '"command_name": "post-content", "exec_summary": "Start writing", '
                '"step_plan": "Begin.", "depends_on_previous": false}]}',
                {"input_tokens": 100, "output_tokens": 50},
            )

            blueprint = ConcreteLeaderBlueprint()
            blueprint.generate_task_proposal(leader)

        assert Document.objects.filter(department=department).count() == count_before


# ── WorkforceBlueprint default execute_task ────────────────────────────────


@pytest.mark.django_db
class TestWorkforceDefaultExecuteTask:
    """Test that WorkforceBlueprint.execute_task provides a working default."""

    def test_default_execute_task_calls_claude(self, twitter_agent):
        """Default execute_task calls call_claude and returns response."""
        from unittest.mock import patch

        with patch(
            "agents.ai.claude_client.call_claude",
            return_value=("Test response from Claude", {"input_tokens": 10, "output_tokens": 20}),
        ) as mock_call:
            bp = get_blueprint("researcher", "sales")
            task = AgentTask.objects.create(
                agent=twitter_agent,
                status=AgentTask.Status.PROCESSING,
                exec_summary="Test task",
                step_plan="Do something",
            )

            result = bp.execute_task(twitter_agent, task)

            assert result == "Test response from Claude"
            assert mock_call.called
            task.refresh_from_db()
            assert task.token_usage == {"input_tokens": 10, "output_tokens": 20}

    def test_get_task_suffix_injected_into_message(self, twitter_agent):
        """Agents with get_task_suffix have their suffix included in the task message."""
        from unittest.mock import patch

        with patch(
            "agents.ai.claude_client.call_claude",
            return_value=("OK", {}),
        ) as mock_call:
            bp = get_blueprint("strategist", "sales")
            task = AgentTask.objects.create(
                agent=twitter_agent,
                status=AgentTask.Status.PROCESSING,
                exec_summary="Draft strategy",
            )

            bp.execute_task(twitter_agent, task)

            user_message = mock_call.call_args.kwargs.get("user_message", "")
            assert "STRATEGY METHODOLOGY" in user_message

    def test_get_max_tokens_passed_to_claude(self, twitter_agent):
        """Agents with get_max_tokens have it passed to call_claude."""
        from unittest.mock import patch

        with patch(
            "agents.ai.claude_client.call_claude",
            return_value=("OK", {}),
        ) as mock_call:
            bp = get_blueprint("market_analyst", "writers_room")
            task = AgentTask.objects.create(
                agent=twitter_agent,
                status=AgentTask.Status.PROCESSING,
                exec_summary="Analyze market",
            )

            bp.execute_task(twitter_agent, task)

            assert mock_call.call_args.kwargs.get("max_tokens") == 12000

    def test_default_max_tokens_not_passed(self, twitter_agent):
        """Agents without get_max_tokens override don't pass max_tokens."""
        from unittest.mock import patch

        with patch(
            "agents.ai.claude_client.call_claude",
            return_value=("OK", {}),
        ) as mock_call:
            bp = get_blueprint("researcher", "sales")
            task = AgentTask.objects.create(
                agent=twitter_agent,
                status=AgentTask.Status.PROCESSING,
                exec_summary="Research",
            )

            bp.execute_task(twitter_agent, task)

            assert "max_tokens" not in mock_call.call_args.kwargs

    def test_default_suffix_is_empty(self):
        """Base WorkforceBlueprint.get_task_suffix returns empty string."""
        from agents.blueprints.marketing.workforce.web_researcher.agent import WebResearcherBlueprint

        bp = WebResearcherBlueprint()
        assert bp.get_task_suffix(None, None) == ""

    def test_agents_without_override_use_default(self):
        """Agents that don't override execute_task should NOT have it on their class."""
        from agents.blueprints.sales.workforce.researcher.agent import ResearcherBlueprint
        from agents.blueprints.sales.workforce.strategist.agent import StrategistBlueprint

        # These classes should NOT define execute_task — they inherit from WorkforceBlueprint
        assert "execute_task" not in ResearcherBlueprint.__dict__
        assert "execute_task" not in StrategistBlueprint.__dict__
        # But they should define get_task_suffix
        assert "get_task_suffix" in ResearcherBlueprint.__dict__
        assert "get_task_suffix" in StrategistBlueprint.__dict__

    def test_agents_with_integrations_still_override(self):
        """Agents with external integrations keep their custom execute_task."""
        from agents.blueprints.marketing.workforce.twitter.agent import TwitterBlueprint

        # Twitter has Playwright integration — it must override execute_task
        assert "execute_task" in TwitterBlueprint.__dict__

    def test_all_workforce_agents_have_execute_task(self):
        """Every workforce blueprint must have an execute_task (inherited or overridden)."""
        from agents.blueprints import DEPARTMENTS

        for dept_slug, dept in DEPARTMENTS.items():
            for agent_slug, bp in dept["workforce"].items():
                assert hasattr(bp, "execute_task"), f"{dept_slug}/{agent_slug} missing execute_task"
                assert callable(bp.execute_task), f"{dept_slug}/{agent_slug}.execute_task not callable"


# ── Review dimensions single source of truth ──────────────────────────────���─


class TestReviewDimensions:
    def test_reviewer_blueprints_have_dimensions(self):
        """Reviewer agents declare review_dimensions on the blueprint."""
        from agents.blueprints import get_blueprint

        cases = {
            ("sales_qa", "sales"): [
                "research_accuracy",
                "strategy_quality",
                "storyline_effectiveness",
                "profile_accuracy",
                "pitch_personalization",
            ],
            ("partnership_reviewer", "community"): ["mutual_value", "specificity", "tone", "structure", "next_steps"],
            ("content_reviewer", "marketing"): [
                "brand_alignment",
                "audience_fit",
                "channel_conventions",
                "messaging_clarity",
                "cta_effectiveness",
            ],
            ("review_engineer", "engineering"): [
                "correctness",
                "test_coverage",
                "security",
                "design_quality",
                "accessibility",
                "code_quality",
            ],
        }
        for (agent_type, dept), expected_dims in cases.items():
            bp = get_blueprint(agent_type, dept)
            assert (
                bp.review_dimensions == expected_dims
            ), f"{dept}/{agent_type} dimensions mismatch: {bp.review_dimensions}"

    def test_non_reviewer_blueprints_have_empty_dimensions(self):
        """Non-reviewer workforce agents have empty review_dimensions by default."""
        from agents.blueprints import get_blueprint

        bp = get_blueprint("twitter", "marketing")
        assert bp.review_dimensions == []

    def test_propose_review_chain_reads_from_blueprint(self, department, leader_agent, twitter_agent):
        """_propose_review_chain reads dimensions from the reviewer blueprint."""
        bp = get_blueprint("leader", "marketing")
        task = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.DONE,
            exec_summary="Tweet draft",
            report="Here is my tweet draft.",
        )
        workforce_types = {"twitter", "content_reviewer"}
        result = bp._propose_review_chain(leader_agent, task, workforce_types)
        assert result is not None
        step_plan = result["tasks"][0]["step_plan"]
        # Dimensions from ContentReviewerBlueprint.review_dimensions
        assert "brand_alignment" in step_plan
        assert "cta_effectiveness" in step_plan


# ── Quality gate helper ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestApplyQualityGate:
    def test_accepts_excellent_score(self, leader_agent):
        bp = get_blueprint("leader", "marketing")
        accepted, polish_count, round_num = bp._apply_quality_gate(leader_agent, 9.5, "test_key")
        assert accepted is True

    def test_rejects_low_score(self, leader_agent):
        bp = get_blueprint("leader", "marketing")
        accepted, polish_count, round_num = bp._apply_quality_gate(leader_agent, 7.0, "test_key")
        assert accepted is False

    def test_accepts_near_excellence_after_max_polish(self, leader_agent):
        """After MAX_POLISH_ATTEMPTS at >= 9.0, accepts even without reaching 9.5."""
        bp = get_blueprint("leader", "marketing")
        # Seed state with existing polish attempts
        leader_agent.internal_state = {
            "review_rounds": {"test_key": 3},
            "polish_attempts": {"test_key": 2},  # Will be incremented to 3 = MAX
        }
        leader_agent.save(update_fields=["internal_state"])
        accepted, polish_count, round_num = bp._apply_quality_gate(leader_agent, 9.2, "test_key")
        assert accepted is True
        assert polish_count == 3

    def test_clears_tracking_on_acceptance(self, leader_agent):
        bp = get_blueprint("leader", "marketing")
        leader_agent.internal_state = {
            "review_rounds": {"test_key": 1},
            "polish_attempts": {"test_key": 0},
        }
        leader_agent.save(update_fields=["internal_state"])
        bp._apply_quality_gate(leader_agent, 9.5, "test_key")
        leader_agent.refresh_from_db()
        assert "test_key" not in leader_agent.internal_state.get("review_rounds", {})
        assert "test_key" not in leader_agent.internal_state.get("polish_attempts", {})


# ── Output declarations ────────────────────────────────────────────────────


class TestOutputDeclarations:
    def test_outputs_set_on_expected_agents(self):
        """Agents that produce persistent artifacts declare their outputs."""
        cases = {
            ("web_researcher", "marketing"): ["document"],
            ("story_researcher", "writers_room"): ["document"],
            ("ticket_manager", "engineering"): ["github_issue"],
        }
        for (agent_type, dept), expected in cases.items():
            bp = get_blueprint(agent_type, dept)
            assert bp.outputs == expected, f"{dept}/{agent_type} outputs mismatch: {bp.outputs}"

    def test_default_outputs_empty(self):
        """Agents without artifact production have empty outputs."""
        bp = get_blueprint("twitter", "marketing")
        assert bp.outputs == []

    def test_outputs_field_exists_on_base(self):
        """The outputs field is defined on BaseBlueprint."""
        from agents.blueprints.base import BaseBlueprint

        assert hasattr(BaseBlueprint, "outputs")
        assert BaseBlueprint.outputs == []


# ── Verdict tool injection ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestVerdictToolInjection:
    """Test that reviewer agents get VERDICT_TOOL injected in execute_task."""

    def test_reviewer_gets_verdict_tool(self, department):
        """Reviewer agents use call_claude_with_tools and get VERDICT_TOOL."""
        from unittest.mock import patch

        from agents.blueprints.marketing.workforce.content_reviewer.agent import ContentReviewerBlueprint

        agent = Agent.objects.create(
            name="Content Reviewer",
            agent_type="content_reviewer",
            department=department,
            status="active",
        )
        task = AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Review tweet draft",
            step_plan="Review the content",
        )

        tool_input = {"verdict": "APPROVED", "score": 9.6}
        with patch(
            "agents.ai.claude_client.call_claude_with_tools",
            return_value=("Great content!", tool_input, {"input_tokens": 100, "output_tokens": 200}),
        ) as mock_call:
            bp = ContentReviewerBlueprint()
            result = bp.execute_task(agent, task)

            assert mock_call.called
            # Verify tools kwarg contains VERDICT_TOOL
            call_kwargs = mock_call.call_args.kwargs
            assert VERDICT_TOOL in call_kwargs["tools"]
            # Verify task fields are set from tool response
            task.refresh_from_db()
            assert task.review_verdict == "APPROVED"
            assert task.review_score == 9.6
            assert result == "Great content!"

    def test_non_reviewer_uses_regular_call(self, twitter_agent):
        """Non-reviewer agents use regular call_claude without tools."""
        from unittest.mock import patch

        task = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Research prospects",
            step_plan="Find leads",
        )

        with patch(
            "agents.ai.claude_client.call_claude",
            return_value=("Here are some leads!", {"input_tokens": 50, "output_tokens": 100}),
        ) as mock_call:
            bp = get_blueprint("researcher", "sales")
            result = bp.execute_task(twitter_agent, task)

            assert mock_call.called
            task.refresh_from_db()
            assert task.review_verdict == ""
            assert task.review_score is None
            assert result == "Here are some leads!"

    def test_fallback_when_tool_not_called(self, department):
        """When Claude doesn't call the tool, fallback parsing sets verdict fields."""
        from unittest.mock import patch

        from agents.blueprints.marketing.workforce.content_reviewer.agent import ContentReviewerBlueprint

        agent = Agent.objects.create(
            name="Content Reviewer",
            agent_type="content_reviewer",
            department=department,
            status="active",
        )
        task = AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Review tweet draft",
            step_plan="Review the content",
        )

        # tool_input is None — Claude didn't call the tool, but text has VERDICT line
        response_text = "Good content.\nVERDICT: APPROVED (score: 9.5/10)"
        with patch(
            "agents.ai.claude_client.call_claude_with_tools",
            return_value=(response_text, None, {"input_tokens": 100, "output_tokens": 200}),
        ):
            bp = ContentReviewerBlueprint()
            result = bp.execute_task(agent, task)

            task.refresh_from_db()
            assert task.review_verdict == "APPROVED"
            assert task.review_score == 9.5
            assert result == response_text


class TestWritersRoomReviewPairs:
    def test_get_review_pairs_defined(self):
        from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX, WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        pairs = bp.get_review_pairs()
        assert len(pairs) > 0
        reviewer_types = {p["reviewer"] for p in pairs}
        assert reviewer_types == {"creative_reviewer"}
        all_creators = set()
        for agents_list in CREATIVE_MATRIX.values():
            all_creators.update(agents_list)
        pair_creators = {p["creator"] for p in pairs}
        assert all_creators == pair_creators

    def test_propose_review_chain_returns_none(self):
        """Writers room overrides _propose_review_chain to return None."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        assert bp._propose_review_chain(None, None, set()) is None


# ── Volume safety net ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestVolumeThresholdCheck:
    def test_triggers_consolidation_when_over_threshold(self, db, department):
        from unittest.mock import MagicMock, patch

        from agents.models import Agent

        # Create docs totaling over 1.5M chars
        big_content = "word " * 400000  # ~2M chars
        Document.objects.create(
            title="Huge doc",
            content=big_content,
            department=department,
        )

        agent = Agent.objects.create(
            name="Test Agent",
            agent_type="twitter",
            department=department,
            status="active",
        )

        with patch("agents.blueprints.base.consolidate_department_documents") as mock_task:
            mock_task.delay = MagicMock()
            blueprint = agent.get_blueprint()
            blueprint.get_context(agent)
            mock_task.delay.assert_called_once_with(str(department.id))

    def test_does_not_trigger_consolidation_when_under_threshold(self, db, department):
        from unittest.mock import MagicMock, patch

        from agents.models import Agent

        # Small content, well under threshold
        Document.objects.create(
            title="Small doc",
            content="Just a short document.",
            department=department,
        )

        agent = Agent.objects.create(
            name="Test Agent",
            agent_type="twitter",
            department=department,
            status="active",
        )

        with patch("agents.blueprints.base.consolidate_department_documents") as mock_task:
            mock_task.delay = MagicMock()
            blueprint = agent.get_blueprint()
            blueprint.get_context(agent)
            mock_task.delay.assert_not_called()


# ── No truncation guarantees ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestNoTruncation:
    def test_document_content_not_truncated(self, db, department):
        from agents.models import Agent

        long_content = "A" * 5000
        Document.objects.create(title="Long doc", content=long_content, department=department)

        agent = Agent.objects.create(
            name="Test Agent",
            agent_type="twitter",
            department=department,
            status="active",
        )

        blueprint = agent.get_blueprint()
        ctx = blueprint.get_context(agent)
        assert long_content in ctx["department_documents"]

    def test_report_not_truncated(self, db, department):
        from agents.models import Agent, AgentTask

        agent = Agent.objects.create(
            name="Test Agent",
            agent_type="twitter",
            department=department,
            status="active",
        )

        long_report = "B" * 5000
        AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.DONE,
            exec_summary="Test task with long report",
            report=long_report,
        )

        blueprint = agent.get_blueprint()
        ctx = blueprint.get_context(agent)
        assert long_report in ctx["own_recent_tasks"]

    def test_exec_summary_not_truncated(self, db, department):
        from agents.models import Agent, AgentTask

        agent = Agent.objects.create(
            name="Test Agent",
            agent_type="twitter",
            department=department,
            status="active",
        )

        long_summary = "C" * 200
        AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.DONE,
            exec_summary=long_summary,
            report="Short report",
        )

        blueprint = agent.get_blueprint()
        ctx = blueprint.get_context(agent)
        assert long_summary in ctx["own_recent_tasks"]
