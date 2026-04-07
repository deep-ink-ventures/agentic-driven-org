"""Tests for projects.tasks — bootstrap_project."""

import json
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from projects.models import BootstrapProposal, Project, Source

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="taskuser@example.com", password="pass123")


@pytest.fixture
def project(user):
    return Project.objects.create(name="Task Project", goal="Test goal", owner=user)


@pytest.fixture
def source_with_text(project, user):
    return Source.objects.create(
        project=project,
        source_type="text",
        raw_content="This is project content for analysis.",
        extracted_text="This is project content for analysis.",
        user=user,
    )


@pytest.fixture
def proposal(project):
    return BootstrapProposal.objects.create(project=project)


_VALID_JSON = json.dumps(
    {
        "summary": "A great project setup.",
        "departments": [
            {
                "department_type": "marketing",
                "documents": [{"title": "Brand Guide", "content": "# Brand", "tags": ["branding"]}],
                "agents": [
                    {
                        "name": "Twitter Bot",
                        "agent_type": "twitter",
                        "instructions": "Post tweets about the project.",
                    }
                ],
            }
        ],
        "ignored_content": [],
    }
)

_USAGE = {"model": "claude-opus-4-6", "input_tokens": 500, "output_tokens": 200}

VALID_RESPONSE = (_VALID_JSON, _USAGE)


class TestBootstrapProject:
    @patch("agents.ai.claude_client.stream_claude", return_value=VALID_RESPONSE)
    def test_success(self, mock_stream, proposal, source_with_text):
        from projects.tasks import bootstrap_project

        bootstrap_project(str(proposal.id))

        proposal.refresh_from_db()
        assert proposal.status == "proposed"
        assert proposal.proposal is not None
        assert "departments" in proposal.proposal
        assert proposal.error_message == ""

    @patch("agents.ai.claude_client.stream_claude", return_value=VALID_RESPONSE)
    def test_status_transitions(self, mock_stream, proposal, source_with_text):
        """Verify the proposal goes from pending -> processing -> proposed."""
        from projects.tasks import bootstrap_project

        assert proposal.status == "pending"

        # We can't easily observe the intermediate 'processing' state in a sync test,
        # but we can verify the final state and that stream_claude was called.
        bootstrap_project(str(proposal.id))

        proposal.refresh_from_db()
        assert proposal.status == "proposed"
        mock_stream.assert_called_once()

    @patch("agents.ai.claude_client.stream_claude", return_value=("not valid json {{{", _USAGE))
    def test_bad_json_fails(self, mock_stream, proposal, source_with_text):
        from projects.tasks import bootstrap_project

        # With retries=max_retries, the task skips retrying and goes straight to failure.
        bootstrap_project.apply(args=[str(proposal.id)], retries=bootstrap_project.max_retries)

        proposal.refresh_from_db()
        assert proposal.status == "failed"
        assert proposal.error_message != ""

    @patch("agents.ai.claude_client.stream_claude", return_value=VALID_RESPONSE)
    def test_no_sources_proceeds(self, mock_stream, proposal):
        """No sources — task proceeds without them (sources are optional for bootstrap)."""
        from projects.tasks import bootstrap_project

        bootstrap_project(str(proposal.id))

        proposal.refresh_from_db()
        # Task should succeed even without sources — Claude gets an empty sources list
        assert proposal.status == "proposed"
        mock_stream.assert_called_once()

    @patch("agents.ai.claude_client.stream_claude", return_value=VALID_RESPONSE)
    def test_sources_without_text_proceeds(self, mock_stream, project, user, proposal):
        """Sources exist but none have text — task still proceeds (sources are optional)."""
        Source.objects.create(
            project=project,
            source_type="file",
            user=user,
            extracted_text="",
            raw_content="",
        )
        from projects.tasks import bootstrap_project

        bootstrap_project(str(proposal.id))

        proposal.refresh_from_db()
        # Task should succeed — empty sources are silently skipped
        assert proposal.status == "proposed"
        mock_stream.assert_called_once()

    @pytest.mark.django_db
    def test_nonexistent_proposal(self):
        """Non-existent proposal ID should not raise — just log."""
        from projects.tasks import bootstrap_project

        # Should not raise
        bootstrap_project(str(uuid.uuid4()))

    @patch("agents.ai.claude_client.stream_claude")
    def test_markdown_fenced_json(self, mock_stream, proposal, source_with_text):
        """Claude sometimes wraps JSON in markdown fences."""
        mock_stream.return_value = (f"```json\n{_VALID_JSON}\n```", _USAGE)

        from projects.tasks import bootstrap_project

        bootstrap_project(str(proposal.id))

        proposal.refresh_from_db()
        assert proposal.status == "proposed"
        assert proposal.proposal is not None

    @patch("agents.ai.claude_client.stream_claude", side_effect=Exception("API error"))
    def test_claude_exception_fails(self, mock_stream, proposal, source_with_text):
        from projects.tasks import bootstrap_project

        # With retries=max_retries, the task skips retrying and goes straight to failure.
        bootstrap_project.apply(args=[str(proposal.id)], retries=bootstrap_project.max_retries)

        proposal.refresh_from_db()
        assert proposal.status == "failed"
        assert "API error" in proposal.error_message


# ── Consolidation task fixtures ────────────────────────────────────────────────


@pytest.fixture
def consolidation_user(db):
    return User.objects.create_user(email="consolidation-user@example.com", password="pass123")


@pytest.fixture
def consolidation_project(consolidation_user):
    from projects.models import Project

    p = Project.objects.create(name="Consolidation Project", goal="Test consolidation", owner=consolidation_user)
    p.members.add(consolidation_user)
    return p


@pytest.fixture
def consolidation_department(consolidation_project):
    from projects.models import Department

    return Department.objects.create(department_type="engineering", project=consolidation_project)


class TestConsolidateSprintDocuments:
    def test_merges_sprint_docs_into_summary(self, consolidation_user, consolidation_department):
        from projects.models import Document, Sprint
        from projects.tasks_consolidation import consolidate_sprint_documents

        sprint = Sprint.objects.create(
            project=consolidation_department.project,
            text="Write pilot",
            created_by=consolidation_user,
        )
        sprint.departments.add(consolidation_department)

        doc1 = Document.objects.create(
            title="Sprint Progress — Write pilot — Batch 1",
            content="Character analysis completed. Found three viable protagonists.",
            department=consolidation_department,
            document_type="sprint_progress",
            sprint=sprint,
        )
        doc2 = Document.objects.create(
            title="Sprint Progress — Write pilot — Batch 2",
            content="Story outline drafted. Three-act structure with B-plot.",
            department=consolidation_department,
            document_type="sprint_progress",
            sprint=sprint,
        )

        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            mock_claude.return_value = (
                "# Sprint Summary: Write pilot\n\nCharacter analysis identified three protagonists. "
                "Story outline uses three-act structure with B-plot.",
                {"input_tokens": 100, "output_tokens": 50},
            )
            consolidate_sprint_documents(str(sprint.id))

        doc1.refresh_from_db()
        doc2.refresh_from_db()
        assert doc1.is_archived is True
        assert doc2.is_archived is True

        summary = Document.objects.filter(
            department=consolidation_department,
            document_type="sprint_summary",
            sprint=sprint,
            is_archived=False,
        ).first()
        assert summary is not None
        assert "Sprint Summary" in summary.title
        assert doc1.consolidated_into == summary
        assert doc2.consolidated_into == summary

    def test_no_docs_does_nothing(self, consolidation_user, consolidation_department):
        from projects.models import Sprint
        from projects.tasks_consolidation import consolidate_sprint_documents

        sprint = Sprint.objects.create(
            project=consolidation_department.project,
            text="Empty sprint",
            created_by=consolidation_user,
        )
        sprint.departments.add(consolidation_department)

        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            consolidate_sprint_documents(str(sprint.id))
            mock_claude.assert_not_called()


class TestConsolidateMonthlyDocuments:
    def test_merges_old_docs_per_department(self, consolidation_user, consolidation_department):
        from datetime import timedelta

        from django.utils import timezone

        from projects.models import Document
        from projects.tasks_consolidation import consolidate_monthly_documents

        old_date = timezone.now() - timedelta(days=35)

        doc1 = Document.objects.create(
            title="Old research",
            content="Market analysis from last month.",
            department=consolidation_department,
            document_type="sprint_summary",
        )
        Document.objects.filter(id=doc1.id).update(created_at=old_date)

        doc2 = Document.objects.create(
            title="Old findings",
            content="Competitor review from last month.",
            department=consolidation_department,
            document_type="sprint_summary",
        )
        Document.objects.filter(id=doc2.id).update(created_at=old_date)

        recent = Document.objects.create(
            title="Fresh doc",
            content="Just created.",
            department=consolidation_department,
            document_type="sprint_progress",
        )

        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            mock_claude.return_value = (
                "# Monthly Archive\n\nMarket analysis and competitor review consolidated.",
                {"input_tokens": 100, "output_tokens": 50},
            )
            consolidate_monthly_documents()

        doc1.refresh_from_db()
        doc2.refresh_from_db()
        recent.refresh_from_db()
        assert doc1.is_archived is True
        assert doc2.is_archived is True
        assert recent.is_archived is False

        archive = Document.objects.filter(
            department=consolidation_department,
            document_type="monthly_archive",
            is_archived=False,
        ).first()
        assert archive is not None


class TestConsolidateDepartmentDocuments:
    def test_triggers_when_over_threshold(self, consolidation_department):
        from projects.models import Document
        from projects.tasks_consolidation import consolidate_department_documents

        big_content = "word " * 200000
        Document.objects.create(title="Huge doc 1", content=big_content, department=consolidation_department)
        Document.objects.create(title="Huge doc 2", content=big_content, department=consolidation_department)

        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            mock_claude.return_value = (
                "# Consolidated\n\nMerged content.",
                {"input_tokens": 100, "output_tokens": 50},
            )
            consolidate_department_documents(str(consolidation_department.id))

        assert Document.objects.filter(department=consolidation_department, is_archived=True).count() == 2

    def test_skips_when_under_threshold(self, consolidation_department):
        from projects.models import Document
        from projects.tasks_consolidation import consolidate_department_documents

        Document.objects.create(title="Small doc", content="Just a few words.", department=consolidation_department)

        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            consolidate_department_documents(str(consolidation_department.id))
            mock_claude.assert_not_called()
