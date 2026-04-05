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

_USAGE = {"model": "claude-sonnet-4-6", "input_tokens": 500, "output_tokens": 200}

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
