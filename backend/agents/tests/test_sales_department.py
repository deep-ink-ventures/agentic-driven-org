"""Tests for the sales department — blueprint registry, leader state machine, QA cascade, SendGrid outreach."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.blueprints import DEPARTMENTS, get_blueprint
from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.leader.agent import (
    AGENT_FIX_COMMANDS,
    CHAIN_ORDER,
    DIMENSION_TO_AGENT,
    PIPELINE_STEPS,
    STEP_CONTEXT_SOURCES,
    STEP_TO_AGENT,
    STEP_TO_COMMAND,
    SalesLeaderBlueprint,
)
from agents.models import Agent, AgentTask, ClonedAgent
from projects.models import Department, Project, Sprint

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(email="sales@example.com", password="pass")


@pytest.fixture
def project(user):
    return Project.objects.create(name="SaaS Startup", goal="Sell our product to CTOs", owner=user)


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="sales", project=project)


@pytest.fixture
def leader(department):
    return Agent.objects.create(
        name="Head of Sales",
        agent_type="leader",
        department=department,
        is_leader=True,
        status="active",
    )


@pytest.fixture
def sprint(department, user):
    s = Sprint.objects.create(project=department.project, text="Outreach to fintech CTOs", created_by=user)
    s.departments.add(department)
    return s


@pytest.fixture
def workforce(department):
    """Create all workforce agents for the sales department."""
    agents = {}
    for slug in [
        "researcher",
        "strategist",
        "pitch_personalizer",
        "sales_qa",
        "email_outreach",
    ]:
        agents[slug] = Agent.objects.create(
            name=f"Test {slug}",
            agent_type=slug,
            department=department,
            status="active",
            outreach=(slug == "email_outreach"),
        )
    return agents


# ── Blueprint Registry ────────────────────────────────────────────────────────


class TestSalesRegistry:
    def test_sales_department_registered(self):
        assert "sales" in DEPARTMENTS

    def test_sales_has_6_workforce_agents(self):
        dept = DEPARTMENTS["sales"]
        assert len(dept["workforce"]) == 6

    def test_sales_workforce_slugs(self):
        slugs = set(DEPARTMENTS["sales"]["workforce"].keys())
        assert slugs == {
            "researcher",
            "strategist",
            "pitch_personalizer",
            "sales_qa",
            "authenticity_analyst",
            "email_outreach",
        }

    def test_leader_is_head_of_sales(self):
        leader = DEPARTMENTS["sales"]["leader"]
        assert leader.name == "Head of Sales"
        assert isinstance(leader, SalesLeaderBlueprint)

    def test_all_agents_resolve_via_get_blueprint(self):
        for slug in DEPARTMENTS["sales"]["workforce"]:
            bp = get_blueprint(slug, "sales")
            assert bp is not None
            assert hasattr(bp, "system_prompt")


# ── Blueprint Properties ──────────────────────────────────────────────────────


class TestSalesBlueprintProperties:
    def test_researcher_uses_haiku(self):
        bp = get_blueprint("researcher", "sales")
        assert bp.default_model == "claude-haiku-4-5"

    def test_strategist_and_qa_use_opus(self):
        for slug in ["strategist", "sales_qa"]:
            bp = get_blueprint(slug, "sales")
            assert bp.default_model == "claude-opus-4-6", f"{slug} should use opus"

    def test_sales_qa_is_essential(self):
        bp = get_blueprint("sales_qa", "sales")
        assert bp.essential is True

    def test_sales_qa_has_5_review_dimensions(self):
        bp = get_blueprint("sales_qa", "sales")
        assert bp.review_dimensions == [
            "research_accuracy",
            "strategy_quality",
            "storyline_effectiveness",
            "profile_accuracy",
            "pitch_personalization",
        ]

    def test_non_reviewer_agents_have_no_dimensions(self):
        for slug in ["researcher", "strategist", "pitch_personalizer"]:
            bp = get_blueprint(slug, "sales")
            assert bp.review_dimensions == [], f"{slug} should have no review_dimensions"

    def test_each_agent_has_commands(self):
        expected = {
            "researcher": ["research-industry"],
            "strategist": ["draft-strategy", "finalize-outreach", "revise-strategy"],
            "pitch_personalizer": ["personalize-pitches", "revise-pitches"],
            "sales_qa": ["review-pipeline"],
            "email_outreach": ["send-outreach"],
        }
        for slug, expected_cmds in expected.items():
            bp = get_blueprint(slug, "sales")
            cmd_names = sorted([c["name"] for c in bp.get_commands()])
            assert cmd_names == sorted(expected_cmds), f"{slug} commands mismatch"

    def test_each_agent_has_system_prompt(self):
        for slug in DEPARTMENTS["sales"]["workforce"]:
            bp = get_blueprint(slug, "sales")
            prompt = bp.system_prompt
            assert isinstance(prompt, str)
            assert len(prompt) > 50, f"{slug} system prompt is too short"

    def test_each_agent_has_task_suffix(self):
        for slug in [
            "researcher",
            "strategist",
            "pitch_personalizer",
            "sales_qa",
        ]:
            bp = get_blueprint(slug, "sales")
            agent_mock = MagicMock()
            agent_mock.config = {}
            agent_mock.get_config_value.return_value = "en"
            suffix = bp.get_task_suffix(agent_mock, MagicMock())
            assert isinstance(suffix, str)
            assert len(suffix) > 20, f"{slug} task suffix is too short"


# ── Email Outreach Config ─────────────────────────────────────────────────────


class TestEmailOutreachConfig:
    def test_config_schema_has_required_fields(self):
        bp = get_blueprint("email_outreach", "sales")
        required_keys = {"sendgrid_api_key", "from_email", "from_name", "calendly_link", "bcc_email"}
        schema_keys = set(bp.config_schema.keys())
        assert required_keys.issubset(schema_keys)

    def test_has_execute_task_override(self):
        from agents.blueprints.sales.workforce.email_outreach.agent import EmailOutreachBlueprint

        assert "execute_task" in EmailOutreachBlueprint.__dict__


# ── Authenticity Analyst in Sales ─────────────────────────────────────────────


class TestSalesAuthenticityAnalyst:
    def test_inherits_mixin(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin

        bp = get_blueprint("authenticity_analyst", "sales")
        assert isinstance(bp, AuthenticityAnalystMixin)

    def test_inherits_workforce_blueprint(self):
        bp = get_blueprint("authenticity_analyst", "sales")
        assert isinstance(bp, WorkforceBlueprint)

    def test_has_analyze_command(self):
        bp = get_blueprint("authenticity_analyst", "sales")
        cmd_names = [c["name"] for c in bp.get_commands()]
        assert "analyze" in cmd_names


# ── Leader Constants Consistency ──────────────────────────────────────────────


class TestLeaderConstants:
    def test_pipeline_steps(self):
        assert PIPELINE_STEPS == ["research", "strategy", "personalization", "finalize", "qa_review", "dispatch"]

    def test_all_steps_have_agent_mapping(self):
        for step in PIPELINE_STEPS:
            assert step in STEP_TO_AGENT

    def test_all_steps_have_command_mapping(self):
        for step in PIPELINE_STEPS:
            assert step in STEP_TO_COMMAND

    def test_all_steps_have_context_sources(self):
        for step in PIPELINE_STEPS:
            assert step in STEP_CONTEXT_SOURCES

    def test_all_dimensions_map_to_chain_agents(self):
        for dim, agent_type in DIMENSION_TO_AGENT.items():
            assert agent_type in CHAIN_ORDER, f"{dim} maps to {agent_type} not in CHAIN_ORDER"
            assert agent_type in AGENT_FIX_COMMANDS, f"{agent_type} not in AGENT_FIX_COMMANDS"

    def test_chain_order_is_researcher_then_strategist(self):
        assert CHAIN_ORDER == ["researcher", "strategist"]

    def test_personalization_step_maps_to_personalizer(self):
        assert STEP_TO_AGENT["personalization"] == "pitch_personalizer"

    def test_finalize_step_maps_to_strategist(self):
        assert STEP_TO_AGENT["finalize"] == "strategist"

    def test_finalize_command(self):
        assert STEP_TO_COMMAND["finalize"] == "finalize-outreach"


# ── Leader Review Pairs ───────────────────────────────────────────────────────


class TestSalesReviewPairs:
    def test_has_one_review_pair(self):
        bp = SalesLeaderBlueprint()
        assert len(bp.get_review_pairs()) == 1

    def test_creator_is_strategist(self):
        bp = SalesLeaderBlueprint()
        pair = bp.get_review_pairs()[0]
        assert pair["creator"] == "strategist"
        assert pair["creator_fix_command"] == "revise-strategy"

    def test_reviewer_is_sales_qa(self):
        bp = SalesLeaderBlueprint()
        pair = bp.get_review_pairs()[0]
        assert pair["reviewer"] == "sales_qa"
        assert pair["reviewer_command"] == "review-pipeline"

    def test_dimensions_match_sales_qa_blueprint(self):
        bp = SalesLeaderBlueprint()
        pair_dims = bp.get_review_pairs()[0]["dimensions"]
        qa_bp = get_blueprint("sales_qa", "sales")
        assert pair_dims == qa_bp.review_dimensions


# ── Leader State Machine ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLeaderStateMachine:
    def test_starts_at_research(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        result = bp.generate_task_proposal(leader)
        assert result is not None
        assert result["tasks"][0]["target_agent_type"] == "researcher"

    def test_advances_to_strategy(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        AgentTask.objects.create(
            agent=workforce["researcher"],
            sprint=sprint,
            command_name="research-industry",
            status=AgentTask.Status.DONE,
            report="Industry briefing here.",
        )
        leader.internal_state = {"pipeline_steps": {str(sprint.id): "research"}}
        leader.save(update_fields=["internal_state"])
        result = bp.generate_task_proposal(leader)
        assert result is not None
        assert result["tasks"][0]["target_agent_type"] == "strategist"

    def test_strategy_context_includes_research(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        AgentTask.objects.create(
            agent=workforce["researcher"],
            sprint=sprint,
            command_name="research-industry",
            status=AgentTask.Status.DONE,
            report="Fintech is booming.",
        )
        result = bp._propose_step_task(leader, sprint, "strategy")
        assert "Fintech is booming" in result["tasks"][0]["step_plan"]

    def test_returns_none_without_sprints(self, leader, workforce):
        bp = SalesLeaderBlueprint()
        assert bp.generate_task_proposal(leader) is None

    def test_waits_for_active_task(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        AgentTask.objects.create(
            agent=workforce["researcher"],
            sprint=sprint,
            command_name="research-industry",
            status=AgentTask.Status.PROCESSING,
        )
        leader.internal_state = {"pipeline_steps": {str(sprint.id): "research"}}
        leader.save(update_fields=["internal_state"])
        assert bp.generate_task_proposal(leader) is None

    def test_strategy_gets_outreach_channels(self, leader, sprint, workforce):
        """Strategy step includes available outreach agents."""
        bp = SalesLeaderBlueprint()
        result = bp._propose_step_task(leader, sprint, "strategy")
        step_plan = result["tasks"][0]["step_plan"]
        assert "email_outreach" in step_plan

    def test_qa_review_also_dispatches_authenticity_analyst(self, leader, sprint, workforce, department):
        """QA review step dispatches both sales_qa and authenticity_analyst."""
        Agent.objects.create(
            name="Authenticity Analyst",
            agent_type="authenticity_analyst",
            department=department,
            status="active",
        )
        bp = SalesLeaderBlueprint()
        result = bp._propose_step_task(leader, sprint, "qa_review")
        agent_types = [t["target_agent_type"] for t in result["tasks"]]
        assert "sales_qa" in agent_types
        assert "authenticity_analyst" in agent_types

    def test_qa_review_without_authenticity_analyst(self, leader, sprint, workforce):
        """QA review works without authenticity analyst agent."""
        bp = SalesLeaderBlueprint()
        result = bp._propose_step_task(leader, sprint, "qa_review")
        agent_types = [t["target_agent_type"] for t in result["tasks"]]
        assert "sales_qa" in agent_types
        assert "authenticity_analyst" not in agent_types


# ── Fan-Out Personalization ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestFanOutPersonalization:
    def test_creates_clones_after_strategy(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        AgentTask.objects.create(
            agent=workforce["strategist"],
            sprint=sprint,
            command_name="draft-strategy",
            status=AgentTask.Status.DONE,
            report=(
                "### Target Area 1: Fintech CTOs\nDetails here\n\n"
                "### Target Area 2: SaaS Founders\nMore details\n\n"
                "### Target Area 3: DevOps Leads\nEven more\n\n"
                "### Priority Ranking\n1. Fintech\n"
            ),
        )
        leader.internal_state = {"pipeline_steps": {str(sprint.id): "strategy"}}
        leader.save(update_fields=["internal_state"])

        result = bp.generate_task_proposal(leader)
        assert result is not None
        assert len(result["tasks"]) == 3
        assert all(t["target_agent_type"] == "pitch_personalizer" for t in result["tasks"])

        assert ClonedAgent.objects.filter(sprint=sprint).count() == 3

    def test_waits_for_all_clones(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        parent = workforce["pitch_personalizer"]
        clone0 = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        clone1 = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=1)
        AgentTask.objects.create(
            agent=parent,
            sprint=sprint,
            command_name="personalize-pitches",
            status=AgentTask.Status.DONE,
            report="Done",
            cloned_agent=clone0,
        )
        AgentTask.objects.create(
            agent=parent,
            sprint=sprint,
            command_name="personalize-pitches",
            status=AgentTask.Status.PROCESSING,
            cloned_agent=clone1,
        )
        leader.internal_state = {"pipeline_steps": {str(sprint.id): "personalization"}}
        leader.save(update_fields=["internal_state"])
        assert bp.generate_task_proposal(leader) is None

    def test_advances_to_finalize_when_all_done(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        parent = workforce["pitch_personalizer"]
        clone0 = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        clone1 = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=1)
        AgentTask.objects.create(
            agent=parent,
            sprint=sprint,
            command_name="personalize-pitches",
            status=AgentTask.Status.DONE,
            report="Clone 0 output",
            cloned_agent=clone0,
        )
        AgentTask.objects.create(
            agent=parent,
            sprint=sprint,
            command_name="personalize-pitches",
            status=AgentTask.Status.DONE,
            report="Clone 1 output",
            cloned_agent=clone1,
        )
        leader.internal_state = {"pipeline_steps": {str(sprint.id): "personalization"}}
        leader.save(update_fields=["internal_state"])

        result = bp.generate_task_proposal(leader)
        assert result is not None
        assert result["tasks"][0]["target_agent_type"] == "strategist"
        assert result["tasks"][0]["command_name"] == "finalize-outreach"
        assert "Clone 0 output" in result["tasks"][0]["step_plan"]
        assert "Clone 1 output" in result["tasks"][0]["step_plan"]


# ── QA Cascade Fix Routing ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestQACascadeRouting:
    def test_find_earliest_researcher(self, leader):
        bp = SalesLeaderBlueprint()
        report = "research_accuracy: 7.5/10\nstrategy_quality: 9.5/10"
        assert bp._find_earliest_failing_agent(report, 7.5) == "researcher"

    def test_find_earliest_strategist(self, leader):
        bp = SalesLeaderBlueprint()
        report = "research_accuracy: 9.5/10\nstrategy_quality: 7.0/10\nprofile_accuracy: 8.0/10"
        assert bp._find_earliest_failing_agent(report, 7.0) == "strategist"

    def test_all_pass_returns_none(self, leader):
        bp = SalesLeaderBlueprint()
        report = "research_accuracy: 9.5/10\nstrategy_quality: 9.5/10"
        assert bp._find_earliest_failing_agent(report, 9.5) is None

    def test_fix_routes_to_researcher(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        review_task = AgentTask.objects.create(
            agent=workforce["sales_qa"],
            sprint=sprint,
            command_name="review-pipeline",
            status=AgentTask.Status.DONE,
            report="research_accuracy: 7.0/10\nstrategy_quality: 9.5/10",
            review_verdict="CHANGES_REQUESTED",
            review_score=7.0,
        )
        result = bp._propose_fix_task(leader, review_task, 7.0, 1, 0)
        assert result["tasks"][0]["target_agent_type"] == "researcher"

    def test_fallback_to_strategist(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        review_task = AgentTask.objects.create(
            agent=workforce["sales_qa"],
            sprint=sprint,
            command_name="review-pipeline",
            status=AgentTask.Status.DONE,
            report="Needs improvement.",
            review_verdict="CHANGES_REQUESTED",
            review_score=8.0,
        )
        result = bp._propose_fix_task(leader, review_task, 8.0, 1, 0)
        assert result["tasks"][0]["target_agent_type"] == "strategist"
        assert result["tasks"][0]["command_name"] == "revise-strategy"


# ── Document Persistence ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDocumentPersistence:
    def test_research_creates_document(self, leader, sprint, workforce):
        from projects.models import Document

        AgentTask.objects.create(
            agent=workforce["researcher"],
            sprint=sprint,
            command_name="research-industry",
            status=AgentTask.Status.DONE,
            report="Fintech industry briefing content.",
        )

        bp = SalesLeaderBlueprint()
        bp._persist_step_document(leader, sprint, "research")

        doc = Document.objects.get(department=leader.department, doc_type=Document.DocType.RESEARCH, sprint=sprint)
        assert "Fintech industry briefing" in doc.content

    def test_strategy_creates_document(self, leader, sprint, workforce):
        from projects.models import Document

        AgentTask.objects.create(
            agent=workforce["strategist"],
            sprint=sprint,
            command_name="draft-strategy",
            status=AgentTask.Status.DONE,
            report="Target areas: fintech CTOs, Series B.",
        )

        bp = SalesLeaderBlueprint()
        bp._persist_step_document(leader, sprint, "strategy")

        doc = Document.objects.get(department=leader.department, doc_type=Document.DocType.STRATEGY, sprint=sprint)
        assert "fintech CTOs" in doc.content

    def test_other_steps_dont_create_documents(self, leader, sprint, workforce):
        from projects.models import Document

        bp = SalesLeaderBlueprint()
        count_before = Document.objects.count()
        bp._persist_step_document(leader, sprint, "personalization")
        assert Document.objects.count() == count_before

    def test_updates_existing_document(self, leader, sprint, workforce):
        from projects.models import Document

        Document.objects.create(
            title="Old briefing",
            content="Old content",
            department=leader.department,
            doc_type=Document.DocType.RESEARCH,
            sprint=sprint,
        )

        AgentTask.objects.create(
            agent=workforce["researcher"],
            sprint=sprint,
            command_name="research-industry",
            status=AgentTask.Status.DONE,
            report="Updated briefing content.",
        )

        bp = SalesLeaderBlueprint()
        bp._persist_step_document(leader, sprint, "research")

        docs = Document.objects.filter(department=leader.department, doc_type=Document.DocType.RESEARCH, sprint=sprint)
        assert docs.count() == 1
        assert "Updated briefing" in docs.first().content


# ── SendGrid Service ──────────────────────────────────────────────────────────


class TestSendGridService:
    def test_send_email_success(self):
        mock_sg_module = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sg_module.SendGridAPIClient.return_value.send.return_value = mock_response

        with patch.dict("sys.modules", {"sendgrid": mock_sg_module, "sendgrid.helpers.mail": MagicMock()}):
            # Re-import to pick up mocked module
            import importlib

            import integrations.sendgrid.service as svc

            importlib.reload(svc)

            result = svc.send_email(
                api_key="test-key",
                from_email="from@test.com",
                from_name="Sender",
                to_email="to@test.com",
                to_name="Recipient",
                subject="Hello",
                plain_text_body="Test body",
                bcc_email="bcc@test.com",
            )

            assert result["success"] is True
            assert result["status_code"] == 202

    def test_send_email_failure(self):
        mock_sg_module = MagicMock()
        mock_sg_module.SendGridAPIClient.return_value.send.side_effect = Exception("API error")

        with patch.dict("sys.modules", {"sendgrid": mock_sg_module, "sendgrid.helpers.mail": MagicMock()}):
            import importlib

            import integrations.sendgrid.service as svc

            importlib.reload(svc)

            result = svc.send_email(
                api_key="test-key",
                from_email="from@test.com",
                from_name="Sender",
                to_email="to@test.com",
                to_name="Recipient",
                subject="Hello",
                plain_text_body="Test body",
            )

            assert result["success"] is False
            assert "API error" in result["error"]


# ── call_claude_tool_loop ─────────────────────────────────────────────────────


class TestClaudeToolLoop:
    def test_returns_final_text_when_no_tools(self):
        with patch("agents.ai.claude_client._get_client") as mock_client_fn:
            mock_msg = MagicMock()
            mock_msg.content = [MagicMock(type="text", text="Done.")]
            mock_msg.stop_reason = "end_turn"
            mock_msg.usage.input_tokens = 100
            mock_msg.usage.output_tokens = 50
            mock_client_fn.return_value.messages.create.return_value = mock_msg

            from agents.ai.claude_client import call_claude_tool_loop

            text, usage = call_claude_tool_loop(
                system_prompt="sys",
                user_message="msg",
                tools=[],
                handle_tool_call=lambda n, i: "{}",
            )

            assert text == "Done."
            assert usage["input_tokens"] == 100

    def test_handles_tool_calls_and_loops(self):
        with patch("agents.ai.claude_client._get_client") as mock_client_fn:
            # Turn 1: tool call — use spec=None and set name explicitly to avoid MagicMock name conflict
            tool_block = MagicMock(spec=None)
            tool_block.type = "tool_use"
            tool_block.name = "my_tool"
            tool_block.input = {"key": "val"}
            tool_block.id = "tool_1"
            msg1 = MagicMock()
            msg1.content = [tool_block]
            msg1.stop_reason = "tool_use"
            msg1.usage.input_tokens = 100
            msg1.usage.output_tokens = 50

            # Turn 2: final response
            msg2 = MagicMock()
            msg2.content = [MagicMock(type="text", text="All done.")]
            msg2.stop_reason = "end_turn"
            msg2.usage.input_tokens = 150
            msg2.usage.output_tokens = 30

            mock_client_fn.return_value.messages.create.side_effect = [msg1, msg2]

            calls = []

            def handle(name, inp):
                calls.append((name, inp))
                return json.dumps({"result": "ok"})

            from agents.ai.claude_client import call_claude_tool_loop

            text, usage = call_claude_tool_loop(
                system_prompt="sys",
                user_message="msg",
                tools=[{"name": "my_tool"}],
                handle_tool_call=handle,
            )

            assert text == "All done."
            assert len(calls) == 1
            assert calls[0] == ("my_tool", {"key": "val"})
            assert usage["input_tokens"] == 250
            assert usage["output_tokens"] == 80


# ── Email Outreach execute_task ───────────────────────────────────────────────


@pytest.mark.django_db
class TestEmailOutreachExecuteTask:
    def test_returns_error_without_config(self, department):
        from agents.blueprints.sales.workforce.email_outreach.agent import EmailOutreachBlueprint

        agent = Agent.objects.create(
            name="Email Outreach",
            agent_type="email_outreach",
            department=department,
            status="active",
            config={},
        )
        task = AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Send emails",
        )

        bp = EmailOutreachBlueprint()
        result = bp.execute_task(agent, task)
        assert "ERROR" in result

    def test_sends_via_sendgrid_and_produces_report(self, department):
        from agents.blueprints.sales.workforce.email_outreach.agent import EmailOutreachBlueprint

        agent = Agent.objects.create(
            name="Email Outreach",
            agent_type="email_outreach",
            department=department,
            status="active",
            config={
                "sendgrid_api_key": "SG.test",
                "from_email": "outreach@test.com",
                "from_name": "Test Sender",
                "calendly_link": "https://calendly.com/test",
                "bcc_email": "closer@test.com",
                "bcc_name": "The Closer",
                "sender_title": "VP Sales",
            },
        )
        task = AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Send outreach",
            step_plan="Send these pitches.",
        )

        # Mock the tool loop: Claude calls send_email then prospect_briefing then returns
        def mock_tool_loop(system_prompt, user_message, tools, handle_tool_call, model, **kwargs):
            # Simulate Claude calling send_email
            handle_tool_call(
                "send_email",
                {"to_email": "cto@fintech.com", "to_name": "Jane Doe", "subject": "Quick question", "body": "Hi Jane"},
            )
            # Simulate Claude calling prospect_briefing
            handle_tool_call(
                "prospect_briefing",
                {
                    "prospect_name": "Jane Doe",
                    "prospect_company": "Fintech Co",
                    "prospect_role": "CTO",
                    "why_reaching_out": "Series B, scaling eng team",
                    "key_talking_points": ["Infrastructure", "Hiring"],
                    "what_they_care_about": "Engineering velocity",
                    "pitch_angle_used": "Scaling teams",
                },
            )
            return "Sent 1 email.", {"model": "test", "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.01}

        with (
            patch("agents.ai.claude_client.call_claude_tool_loop", side_effect=mock_tool_loop),
            patch.object(
                EmailOutreachBlueprint,
                "_send_via_sendgrid",
                return_value={
                    "success": True,
                    "status_code": 202,
                    "to_email": "cto@fintech.com",
                    "to_name": "Jane Doe",
                    "subject": "Quick question",
                },
            ),
        ):
            bp = EmailOutreachBlueprint()
            result = bp.execute_task(agent, task)

        assert "Delivery Report" in result
        assert "Jane Doe" in result
        assert "sent" in result

        # Check briefing was stored
        agent.refresh_from_db()
        briefings = agent.internal_state.get("briefings", [])
        assert len(briefings) == 1
        assert briefings[0]["prospect_name"] == "Jane Doe"

    def test_signature_includes_calendly(self, department):
        from agents.blueprints.sales.workforce.email_outreach.agent import EmailOutreachBlueprint

        agent = Agent.objects.create(
            name="Email Outreach",
            agent_type="email_outreach",
            department=department,
            status="active",
            config={
                "sendgrid_api_key": "SG.test",
                "from_email": "outreach@test.com",
                "from_name": "Test Sender",
                "calendly_link": "https://calendly.com/test",
                "bcc_email": "closer@test.com",
                "sender_title": "VP Sales",
            },
        )

        bp = EmailOutreachBlueprint()
        suffix = bp.get_task_suffix(agent, MagicMock())
        assert "calendly.com/test" in suffix
        assert "auto-appended" in suffix


# ── Outreach Field on Agent ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestOutreachField:
    def test_default_is_false(self, department):
        agent = Agent.objects.create(
            name="Test Agent",
            agent_type="researcher",
            department=department,
            status="active",
        )
        assert agent.outreach is False

    def test_can_set_to_true(self, department):
        agent = Agent.objects.create(
            name="Email Outreach",
            agent_type="email_outreach",
            department=department,
            status="active",
            outreach=True,
        )
        agent.refresh_from_db()
        assert agent.outreach is True

    def test_outreach_filter_works(self, department, workforce):
        outreach_agents = list(department.agents.filter(outreach=True))
        assert len(outreach_agents) == 1
        assert outreach_agents[0].agent_type == "email_outreach"


# ── ClonedAgent Model ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestClonedAgent:
    def test_create_clone(self, department, workforce, sprint):
        parent = workforce["pitch_personalizer"]
        clone = ClonedAgent.objects.create(
            parent=parent,
            sprint=sprint,
            clone_index=0,
        )
        assert clone.parent == parent
        assert clone.sprint == sprint
        assert clone.clone_index == 0
        assert clone.internal_state == {}

    def test_clone_resolves_parent_blueprint(self, department, workforce, sprint):
        parent = workforce["pitch_personalizer"]
        clone = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        bp = clone.parent.get_blueprint()
        assert bp.slug == "pitch_personalizer"

    def test_clone_destroyed_with_sprint_helper(self, leader, department, workforce, sprint):
        parent = workforce["pitch_personalizer"]
        ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=1)
        assert ClonedAgent.objects.filter(sprint=sprint).count() == 2

        ClonedAgent.objects.filter(sprint=sprint).delete()
        assert ClonedAgent.objects.filter(sprint=sprint).count() == 0

    def test_task_can_reference_clone(self, department, workforce, sprint):
        parent = workforce["pitch_personalizer"]
        clone = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        task = AgentTask.objects.create(
            agent=parent,
            sprint=sprint,
            command_name="personalize-pitches",
            status=AgentTask.Status.QUEUED,
            cloned_agent=clone,
        )
        assert task.cloned_agent == clone
        assert task.cloned_agent.parent == parent

    def test_task_without_clone_is_fine(self, department, workforce, sprint):
        task = AgentTask.objects.create(
            agent=workforce["researcher"],
            sprint=sprint,
            command_name="research-industry",
            status=AgentTask.Status.QUEUED,
        )
        assert task.cloned_agent is None


# ── Leader Clone Helpers ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLeaderCloneHelpers:
    def test_create_clones(self, leader, workforce, sprint):
        bp = SalesLeaderBlueprint()
        parent = workforce["pitch_personalizer"]
        clones = bp.create_clones(parent, 3, sprint)
        assert len(clones) == 3
        assert all(c.parent == parent for c in clones)
        assert [c.clone_index for c in clones] == [0, 1, 2]
        assert all(c.sprint == sprint for c in clones)

    def test_destroy_sprint_clones(self, leader, workforce, sprint):
        bp = SalesLeaderBlueprint()
        parent = workforce["pitch_personalizer"]
        bp.create_clones(parent, 3, sprint)
        assert ClonedAgent.objects.filter(sprint=sprint).count() == 3

        bp.destroy_sprint_clones(sprint)
        assert ClonedAgent.objects.filter(sprint=sprint).count() == 0

    def test_create_clones_with_initial_state(self, leader, workforce, sprint):
        bp = SalesLeaderBlueprint()
        parent = workforce["pitch_personalizer"]
        clones = bp.create_clones(parent, 2, sprint, initial_state={"target_count": 50})
        assert all(c.internal_state == {"target_count": 50} for c in clones)


# ── Strategist Expanded (absorbs pitch_architect) ───────────────────────────


class TestStrategistExpanded:
    def test_system_prompt_includes_narrative_design(self):
        bp = get_blueprint("strategist", "sales")
        prompt = bp.system_prompt
        assert "narrative arc" in prompt.lower() or "aida" in prompt.lower()

    def test_system_prompt_includes_target_areas(self):
        bp = get_blueprint("strategist", "sales")
        prompt = bp.system_prompt
        assert "target area" in prompt.lower()

    def test_has_finalize_outreach_command(self):
        bp = get_blueprint("strategist", "sales")
        cmd_names = [c["name"] for c in bp.get_commands()]
        assert "finalize-outreach" in cmd_names

    def test_finalize_outreach_mentions_csv(self):
        bp = get_blueprint("strategist", "sales")
        for cmd in bp.get_commands():
            if cmd["name"] == "finalize-outreach":
                assert "csv" in cmd["description"].lower() or "CSV" in cmd["description"]
                break


# ── Personalizer Expanded (absorbs profile_selector) ─────────────────────────


class TestPersonalizerExpanded:
    def test_system_prompt_includes_profile_finding(self):
        bp = get_blueprint("pitch_personalizer", "sales")
        prompt = bp.system_prompt
        assert "find" in prompt.lower() or "search" in prompt.lower() or "discover" in prompt.lower()

    def test_uses_web_search(self):
        bp = get_blueprint("pitch_personalizer", "sales")
        assert bp.uses_web_search is True

    def test_uses_haiku_model(self):
        bp = get_blueprint("pitch_personalizer", "sales")
        assert bp.default_model == "claude-haiku-4-5"
