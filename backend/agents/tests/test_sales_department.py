"""Tests for the sales department — blueprint registry, leader state machine, fan-out, SendGrid outreach."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.blueprints import DEPARTMENTS, get_blueprint
from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.leader.agent import (
    DEFAULT_PROSPECTS_PER_AREA,
    FAN_OUT_STEPS,
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
        "authenticity_analyst",
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
    def test_researcher_uses_sonnet(self):
        bp = get_blueprint("researcher", "sales")
        assert bp.default_model == "claude-sonnet-4-6"

    def test_identify_targets_uses_sonnet(self):
        """identify-targets uses sonnet for speed — it is a targeting step, not creative writing."""
        bp = get_blueprint("strategist", "sales")
        cmds = {c["name"]: c for c in bp.get_commands()}
        assert cmds["identify-targets"]["model"] == "claude-sonnet-4-6"

    def test_sales_qa_is_essential(self):
        bp = get_blueprint("sales_qa", "sales")
        assert bp.essential is True

    def test_sales_qa_has_4_review_dimensions(self):
        bp = get_blueprint("sales_qa", "sales")
        assert bp.review_dimensions == [
            "multiplier_strategy",
            "prospect_verification",
            "pitch_quality",
            "pipeline_coherence",
        ]

    def test_non_reviewer_agents_have_no_dimensions(self):
        for slug in ["researcher", "strategist", "pitch_personalizer"]:
            bp = get_blueprint(slug, "sales")
            assert bp.review_dimensions == [], f"{slug} should have no review_dimensions"

    def test_each_agent_has_commands(self):
        expected = {
            "researcher": ["discover-prospects"],
            "strategist": ["identify-targets"],
            "pitch_personalizer": ["write-pitches"],
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

    def test_has_verify_prospects_command(self):
        bp = get_blueprint("authenticity_analyst", "sales")
        cmd_names = [c["name"] for c in bp.get_commands()]
        assert "verify-prospects" in cmd_names

    def test_has_verify_pitches_command(self):
        bp = get_blueprint("authenticity_analyst", "sales")
        cmd_names = [c["name"] for c in bp.get_commands()]
        assert "verify-pitches" in cmd_names


# ── Leader Constants Consistency ──────────────────────────────────────────────


class TestLeaderConstants:
    def test_pipeline_steps(self):
        assert PIPELINE_STEPS == [
            "ideation",
            "discovery",
            "prospect_gate",
            "copywriting",
            "copy_gate",
            "qa_review",
            "dispatch",
        ]

    def test_pipeline_has_7_steps(self):
        assert len(PIPELINE_STEPS) == 7

    def test_pipeline_starts_with_ideation(self):
        assert PIPELINE_STEPS[0] == "ideation"

    def test_all_steps_have_agent_mapping(self):
        for step in PIPELINE_STEPS:
            assert step in STEP_TO_AGENT

    def test_all_steps_have_command_mapping(self):
        for step in PIPELINE_STEPS:
            assert step in STEP_TO_COMMAND

    def test_all_steps_have_context_sources(self):
        for step in PIPELINE_STEPS:
            assert step in STEP_CONTEXT_SOURCES

    def test_fan_out_steps(self):
        assert set(FAN_OUT_STEPS.keys()) == {"discovery", "copywriting"}

    def test_fan_out_discovery_config(self):
        assert FAN_OUT_STEPS["discovery"]["agent_type"] == "researcher"
        assert FAN_OUT_STEPS["discovery"]["command"] == "discover-prospects"
        assert FAN_OUT_STEPS["discovery"]["source_step"] == "ideation"

    def test_fan_out_copywriting_config(self):
        assert FAN_OUT_STEPS["copywriting"]["agent_type"] == "pitch_personalizer"
        assert FAN_OUT_STEPS["copywriting"]["command"] == "write-pitches"

    def test_default_prospects_per_area(self):
        assert DEFAULT_PROSPECTS_PER_AREA == 10

    def test_discovery_step_maps_to_researcher(self):
        assert STEP_TO_AGENT["discovery"] == "researcher"

    def test_copywriting_step_maps_to_personalizer(self):
        assert STEP_TO_AGENT["copywriting"] == "pitch_personalizer"

    def test_prospect_gate_maps_to_authenticity_analyst(self):
        assert STEP_TO_AGENT["prospect_gate"] == "authenticity_analyst"

    def test_copy_gate_maps_to_authenticity_analyst(self):
        assert STEP_TO_AGENT["copy_gate"] == "authenticity_analyst"

    def test_ideation_maps_to_strategist(self):
        assert STEP_TO_AGENT["ideation"] == "strategist"

    def test_ideation_command(self):
        assert STEP_TO_COMMAND["ideation"] == "identify-targets"

    def test_discovery_command(self):
        assert STEP_TO_COMMAND["discovery"] == "discover-prospects"


# ── Leader State Machine ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLeaderStateMachine:
    def test_starts_at_ideation(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        result = bp.generate_task_proposal(leader)
        assert result is not None
        assert result["tasks"][0]["target_agent_type"] == "strategist"
        assert result["tasks"][0]["command_name"] == "identify-targets"

    def test_advances_to_discovery_after_ideation(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        AgentTask.objects.create(
            agent=workforce["strategist"],
            sprint=sprint,
            command_name="identify-targets",
            status=AgentTask.Status.DONE,
            report=(
                "### Target Area 1: Fintech CTOs\nDetails\n\n"
                "### Target Area 2: SaaS Founders\nMore details\n\n"
                "### Priority Ranking\n1. Fintech\n"
            ),
        )
        sprint.set_department_state(str(leader.department_id), {"pipeline_step": "ideation"})
        result = bp.generate_task_proposal(leader)
        # After ideation completes, next step is discovery (a fan-out step)
        # which creates clones — so the result should contain clone tasks
        assert result is not None

    def test_ideation_context_is_empty(self, leader, sprint, workforce):
        """Ideation is the first step — no prior context to inject."""
        bp = SalesLeaderBlueprint()
        result = bp._propose_step_task(leader, sprint, "ideation")
        assert "No prior step output" in result["tasks"][0]["step_plan"]

    def test_returns_none_without_sprints(self, leader, workforce):
        bp = SalesLeaderBlueprint()
        assert bp.generate_task_proposal(leader) is None

    def test_waits_for_active_task(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        AgentTask.objects.create(
            agent=workforce["strategist"],
            sprint=sprint,
            command_name="identify-targets",
            status=AgentTask.Status.PROCESSING,
        )
        sprint.set_department_state(str(leader.department_id), {"pipeline_step": "ideation"})
        assert bp.generate_task_proposal(leader) is None


# ── Fan-Out ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFanOut:
    def test_discovery_creates_researcher_clones(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        AgentTask.objects.create(
            agent=workforce["strategist"],
            sprint=sprint,
            command_name="identify-targets",
            status=AgentTask.Status.DONE,
            report=(
                "### Target Area 1: Fintech CTOs\nDetails here\n\n"
                "### Target Area 2: SaaS Founders\nMore details\n\n"
                "### Target Area 3: DevOps Leads\nEven more\n\n"
                "### Priority Ranking\n1. Fintech\n"
            ),
        )
        sprint.set_department_state(str(leader.department_id), {"pipeline_step": "discovery"})

        result = bp.generate_task_proposal(leader)
        assert result is not None
        assert len(result["tasks"]) == 3
        assert all(t["target_agent_type"] == "researcher" for t in result["tasks"])
        assert all(t["command_name"] == "discover-prospects" for t in result["tasks"])

        assert ClonedAgent.objects.filter(sprint=sprint, parent=workforce["researcher"]).count() == 3

    def test_waits_for_all_discovery_clones(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        parent = workforce["researcher"]
        clone0 = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        clone1 = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=1)
        AgentTask.objects.create(
            agent=parent,
            sprint=sprint,
            command_name="discover-prospects",
            status=AgentTask.Status.DONE,
            report="Done",
            cloned_agent=clone0,
        )
        AgentTask.objects.create(
            agent=parent,
            sprint=sprint,
            command_name="discover-prospects",
            status=AgentTask.Status.PROCESSING,
            cloned_agent=clone1,
        )
        sprint.set_department_state(str(leader.department_id), {"pipeline_step": "discovery"})
        assert bp.generate_task_proposal(leader) is None

    def test_advances_to_prospect_gate_when_discovery_done(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        parent = workforce["researcher"]
        clone0 = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        clone1 = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=1)
        AgentTask.objects.create(
            agent=parent,
            sprint=sprint,
            command_name="discover-prospects",
            status=AgentTask.Status.DONE,
            report="Clone 0 prospects",
            cloned_agent=clone0,
        )
        AgentTask.objects.create(
            agent=parent,
            sprint=sprint,
            command_name="discover-prospects",
            status=AgentTask.Status.DONE,
            report="Clone 1 prospects",
            cloned_agent=clone1,
        )
        sprint.set_department_state(str(leader.department_id), {"pipeline_step": "discovery"})

        result = bp.generate_task_proposal(leader)
        assert result is not None
        assert result["tasks"][0]["target_agent_type"] == "authenticity_analyst"
        assert result["tasks"][0]["command_name"] == "verify-prospects"

    def test_copywriting_creates_personalizer_clones(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        AgentTask.objects.create(
            agent=workforce["strategist"],
            sprint=sprint,
            command_name="identify-targets",
            status=AgentTask.Status.DONE,
            report=(
                "### Target Area 1: Fintech CTOs\nDetails\n\n"
                "### Target Area 2: SaaS Founders\nMore details\n\n"
                "### Priority Ranking\n1. Fintech\n"
            ),
        )
        sprint.set_department_state(str(leader.department_id), {"pipeline_step": "copywriting"})

        result = bp.generate_task_proposal(leader)
        assert result is not None
        assert len(result["tasks"]) == 2
        assert all(t["target_agent_type"] == "pitch_personalizer" for t in result["tasks"])
        assert all(t["command_name"] == "write-pitches" for t in result["tasks"])

        assert ClonedAgent.objects.filter(sprint=sprint, parent=workforce["pitch_personalizer"]).count() == 2


# ── Document Persistence ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDocumentPersistence:
    def test_ideation_creates_document(self, leader, sprint, workforce):
        from projects.models import Document

        AgentTask.objects.create(
            agent=workforce["strategist"],
            sprint=sprint,
            command_name="identify-targets",
            status=AgentTask.Status.DONE,
            report="Multiplier target areas: fintech CTOs, Series B.",
        )

        bp = SalesLeaderBlueprint()
        bp._persist_step_document(leader, sprint, "ideation")

        doc = Document.objects.get(department=leader.department, doc_type=Document.DocType.STRATEGY, sprint=sprint)
        assert "fintech CTOs" in doc.content

    def test_other_steps_dont_create_documents(self, leader, sprint, workforce):
        from projects.models import Document

        bp = SalesLeaderBlueprint()
        count_before = Document.objects.count()
        bp._persist_step_document(leader, sprint, "discovery")
        bp._persist_step_document(leader, sprint, "copywriting")
        assert Document.objects.count() == count_before

    def test_updates_existing_document(self, leader, sprint, workforce):
        from projects.models import Document

        Document.objects.create(
            title="Old strategy",
            content="Old content",
            department=leader.department,
            doc_type=Document.DocType.STRATEGY,
            sprint=sprint,
        )

        AgentTask.objects.create(
            agent=workforce["strategist"],
            sprint=sprint,
            command_name="identify-targets",
            status=AgentTask.Status.DONE,
            report="Updated target areas content.",
        )

        bp = SalesLeaderBlueprint()
        bp._persist_step_document(leader, sprint, "ideation")

        docs = Document.objects.filter(department=leader.department, doc_type=Document.DocType.STRATEGY, sprint=sprint)
        assert docs.count() == 1
        assert "Updated target areas" in docs.first().content


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
            command_name="write-pitches",
            status=AgentTask.Status.QUEUED,
            cloned_agent=clone,
        )
        assert task.cloned_agent == clone
        assert task.cloned_agent.parent == parent

    def test_task_without_clone_is_fine(self, department, workforce, sprint):
        task = AgentTask.objects.create(
            agent=workforce["researcher"],
            sprint=sprint,
            command_name="discover-prospects",
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


# ── Strategist ───────────────────────────────────────────────────────────────


class TestStrategist:
    def test_system_prompt_includes_multiplier(self):
        bp = get_blueprint("strategist", "sales")
        prompt = bp.system_prompt
        assert "multiplier" in prompt.lower()

    def test_system_prompt_includes_target_areas(self):
        bp = get_blueprint("strategist", "sales")
        prompt = bp.system_prompt
        assert "target area" in prompt.lower()

    def test_has_identify_targets_command(self):
        bp = get_blueprint("strategist", "sales")
        cmd_names = [c["name"] for c in bp.get_commands()]
        assert "identify-targets" in cmd_names


# ── Personalizer ─────────────────────────────────────────────────────────────


class TestPersonalizer:
    def test_system_prompt_includes_b2b_partnership(self):
        bp = get_blueprint("pitch_personalizer", "sales")
        prompt = bp.system_prompt
        assert "b2b" in prompt.lower() or "partnership" in prompt.lower()

    def test_does_not_use_web_search(self):
        bp = get_blueprint("pitch_personalizer", "sales")
        assert bp.uses_web_search is False

    def test_uses_sonnet_model(self):
        bp = get_blueprint("pitch_personalizer", "sales")
        assert bp.default_model == "claude-sonnet-4-6"


# ── Target Area Parsing ─────────────────────────────────────────────────────


class TestTargetAreaParsing:
    def test_parse_3_target_areas(self):
        bp = SalesLeaderBlueprint()
        report = (
            "## Strategic Thesis\nSome thesis here.\n\n"
            "### Target Area 1: Fintech CTOs\nScope: CFOs at fintech...\nRationale: Growing market...\n\n"
            "### Target Area 2: SaaS Founders\nScope: Series A founders...\nRationale: Scaling needs...\n\n"
            "### Target Area 3: DevOps Leads\nScope: Platform engineering...\nRationale: Cloud migration...\n\n"
            "### Priority Ranking\n1. Fintech CTOs\n2. SaaS Founders\n3. DevOps Leads\n"
        )
        areas = bp._parse_target_areas(report)
        assert len(areas) == 3
        assert "Fintech CTOs" in areas[0][0]
        assert "SaaS Founders" in areas[1][0]
        assert "DevOps Leads" in areas[2][0]
        assert "Growing market" in areas[0][1]

    def test_parse_empty_report(self):
        bp = SalesLeaderBlueprint()
        assert bp._parse_target_areas("") == []

    def test_parse_no_target_areas(self):
        bp = SalesLeaderBlueprint()
        assert bp._parse_target_areas("Just some text without target areas.") == []

    def test_parse_areas_with_risks_section(self):
        bp = SalesLeaderBlueprint()
        report = "### Target Area 1: Enterprise\nDetails\n\n" "### Risks & Assumptions\nSome risks\n"
        areas = bp._parse_target_areas(report)
        assert len(areas) == 1
        assert "Enterprise" in areas[0][0]


# ── Sprint Department State ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestSprintDepartmentState:
    def test_default_empty(self, sprint):
        assert sprint.department_state == {}

    def test_get_department_state_empty(self, sprint, department):
        state = sprint.get_department_state(department.id)
        assert state == {}

    def test_set_and_get_department_state(self, sprint, department):
        sprint.set_department_state(department.id, {"pipeline_step": "ideation"})
        sprint.refresh_from_db()
        state = sprint.get_department_state(department.id)
        assert state == {"pipeline_step": "ideation"}

    def test_multiple_departments(self, sprint, department, project):
        from projects.models import Department

        dept2 = Department.objects.create(department_type="writers_room", project=project)
        sprint.departments.add(dept2)

        sprint.set_department_state(department.id, {"pipeline_step": "ideation"})
        sprint.set_department_state(dept2.id, {"current_stage": "concept"})
        sprint.refresh_from_db()

        assert sprint.get_department_state(department.id)["pipeline_step"] == "ideation"
        assert sprint.get_department_state(dept2.id)["current_stage"] == "concept"
