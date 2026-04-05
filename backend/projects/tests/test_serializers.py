"""Tests for project serializers."""

import pytest

from projects.serializers.bootstrap_proposal_serializer import BootstrapProposalSerializer
from projects.serializers.project_detail_serializer import (
    ProjectDetailSerializer,
    _mask_config,
    _mask_value,
)
from projects.serializers.project_serializer import ProjectSerializer
from projects.serializers.source_serializer import SourceSerializer


@pytest.mark.django_db
class TestProjectSerializer:
    def _create_project(self):
        from accounts.models import User
        from projects.models import Project

        user = User.objects.create_user(email="proj@test.com", password="pass")
        project = Project.objects.create(name="Test Project", goal="Build something", owner=user)
        project.members.add(user)
        return project

    def test_serializes_project_fields(self):
        project = self._create_project()
        data = ProjectSerializer(project).data
        assert data["name"] == "Test Project"
        assert data["goal"] == "Build something"
        assert data["slug"] == "test-project"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_department_count(self):
        from projects.models import Department

        project = self._create_project()
        Department.objects.create(project=project, department_type="marketing")
        data = ProjectSerializer(project).data
        assert data["department_count"] == 1

    def test_agent_count(self):
        from agents.models import Agent
        from projects.models import Department

        project = self._create_project()
        dept = Department.objects.create(project=project, department_type="marketing")
        Agent.objects.create(name="Agent 1", agent_type="twitter", department=dept)
        Agent.objects.create(name="Agent 2", agent_type="reddit", department=dept)
        data = ProjectSerializer(project).data
        assert data["agent_count"] == 2

    def test_source_count(self):
        from projects.models import Source

        project = self._create_project()
        Source.objects.create(project=project, source_type="text", raw_content="hello")
        data = ProjectSerializer(project).data
        assert data["source_count"] == 1

    def test_bootstrap_status_none_when_no_proposals(self):
        project = self._create_project()
        data = ProjectSerializer(project).data
        assert data["bootstrap_status"] is None

    def test_bootstrap_status_from_proposal(self):
        from projects.models import BootstrapProposal

        project = self._create_project()
        BootstrapProposal.objects.create(project=project, status="proposed")
        data = ProjectSerializer(project).data
        assert data["bootstrap_status"] == "proposed"

    def test_sources_nested(self):
        from projects.models import Source

        project = self._create_project()
        Source.objects.create(project=project, source_type="url", url="https://example.com")
        data = ProjectSerializer(project).data
        assert len(data["sources"]) == 1
        assert data["sources"][0]["url"] == "https://example.com"


@pytest.mark.django_db
class TestProjectDetailSerializer:
    def _create_full_project(self):
        from accounts.models import User
        from agents.models import Agent
        from projects.models import Department, Project, ProjectConfig

        user = User.objects.create_user(email="detail@test.com", password="pass")
        pc = ProjectConfig.objects.create(name="Test Config", config={"api_key": "secret123456"})
        project = Project.objects.create(name="Detail Project", owner=user, config=pc)
        project.members.add(user)
        dept = Department.objects.create(project=project, department_type="marketing")
        Agent.objects.create(
            name="Twitter Bot",
            agent_type="twitter",
            department=dept,
            config={"twitter_session": "longvalue12345678"},
        )
        return project

    def test_includes_departments(self):
        project = self._create_full_project()
        data = ProjectDetailSerializer(project).data
        assert len(data["departments"]) == 1
        assert data["departments"][0]["department_type"] == "marketing"

    def test_includes_agents_in_departments(self):
        project = self._create_full_project()
        data = ProjectDetailSerializer(project).data
        agents = data["departments"][0]["agents"]
        assert len(agents) == 1
        assert agents[0]["name"] == "Twitter Bot"

    def test_owner_email(self):
        project = self._create_full_project()
        data = ProjectDetailSerializer(project).data
        assert data["owner_email"] == "detail@test.com"


class TestMaskValue:
    def test_short_string_not_masked(self):
        assert _mask_value("short") == "short"

    def test_long_string_masked(self):
        result = _mask_value("super_secret_long_value")
        assert result == "supe********"

    def test_dict_values_masked(self):
        result = _mask_value({"key": "long_value_here_123"})
        assert result["key"] == "long********"

    def test_list_values_masked(self):
        result = _mask_value(["short", "long_value_here_123"])
        assert result[0] == "short"
        assert result[1] == "long********"

    def test_non_string_passthrough(self):
        assert _mask_value(42) == 42
        assert _mask_value(True) is True
        assert _mask_value(None) is None


class TestMaskConfig:
    def test_empty_config(self):
        assert _mask_config({}) == {}
        assert _mask_config(None) == {}

    def test_masks_all_values(self):
        result = _mask_config({"token": "abcdefghijklmnop"})
        assert result["token"] == "abcd********"


@pytest.mark.django_db
class TestSourceSerializer:
    def _create_source(self, **kwargs):
        from accounts.models import User
        from projects.models import Project, Source

        user = User.objects.create_user(email=f"src{id(kwargs)}@test.com", password="pass")
        project = Project.objects.create(name=f"Src Project {id(kwargs)}", owner=user)
        project.members.add(user)
        return Source.objects.create(project=project, **kwargs)

    def test_serializes_text_source(self):
        source = self._create_source(source_type="text", raw_content="Hello world")
        data = SourceSerializer(source).data
        assert data["source_type"] == "text"
        assert data["raw_content"] == "Hello world"
        assert "id" in data
        assert "created_at" in data

    def test_serializes_url_source(self):
        source = self._create_source(source_type="url", url="https://example.com")
        data = SourceSerializer(source).data
        assert data["source_type"] == "url"
        assert data["url"] == "https://example.com"

    def test_serializes_file_source(self):
        source = self._create_source(source_type="file", original_filename="doc.pdf")
        data = SourceSerializer(source).data
        assert data["source_type"] == "file"
        assert data["original_filename"] == "doc.pdf"

    def test_read_only_fields(self):
        serializer = SourceSerializer()
        for field_name in ["id", "extracted_text", "word_count", "created_at"]:
            assert field_name in serializer.Meta.read_only_fields


@pytest.mark.django_db
class TestBootstrapProposalSerializer:
    def test_serializes_proposal(self):
        from accounts.models import User
        from projects.models import BootstrapProposal, Project

        user = User.objects.create_user(email="boot@test.com", password="pass")
        project = Project.objects.create(name="Boot Project", owner=user)
        project.members.add(user)
        proposal = BootstrapProposal.objects.create(
            project=project,
            status="proposed",
            proposal={"summary": "Test", "departments": []},
            token_usage={"input_tokens": 100, "output_tokens": 50},
        )
        data = BootstrapProposalSerializer(proposal).data
        assert data["status"] == "proposed"
        assert data["proposal"]["summary"] == "Test"
        assert data["token_usage"]["input_tokens"] == 100
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_all_fields_read_only(self):
        serializer = BootstrapProposalSerializer()
        for field_name in serializer.Meta.fields:
            assert field_name in serializer.Meta.read_only_fields
