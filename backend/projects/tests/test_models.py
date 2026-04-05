"""Tests for projects app models."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from projects.models import (
    BootstrapProposal,
    Department,
    Document,
    Project,
    ProjectConfig,
    Source,
    Tag,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="test@example.com", password="testpass123")


@pytest.fixture
def user2(db):
    return User.objects.create_user(email="test2@example.com", password="testpass456")


@pytest.fixture
def config(db):
    return ProjectConfig.objects.create(
        name="Test Config",
        config={},
    )


@pytest.fixture
def project(user, config):
    return Project.objects.create(name="My Project", goal="Build something", owner=user, config=config)


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="marketing", project=project)


@pytest.fixture
def tag(db):
    return Tag.objects.create(name="important")


# ── ProjectConfig ──────────────────────────────────────────────────────────────


class TestProjectConfig:
    def test_create(self, config):
        assert config.name == "Test Config"
        assert config.google_email == ""
        assert config.google_credentials == {}
        assert config.pk is not None

    def test_str(self, config):
        assert str(config) == "Test Config"

    def test_update(self, config):
        config.config["google_credentials"] = {"access_token": "abc"}
        config.save()
        config.refresh_from_db()
        assert config.google_credentials == {"access_token": "abc"}

    def test_validate_config_valid(self, config):
        assert config.validate_config() == []

    def test_validate_config_unknown_key(self):
        c = ProjectConfig(name="Bad", config={"unknown_key": "value"})
        errors = c.validate_config()
        assert len(errors) == 1
        assert "unknown_key" in errors[0]

    def test_validate_config_wrong_type(self):
        c = ProjectConfig(name="Bad", config={"any_key": 123})
        errors = c.validate_config()
        assert len(errors) == 1

    def test_get_schema(self):
        schema = ProjectConfig.get_schema()
        assert "type" in schema
        assert "properties" in schema


# ── Project ────────────────────────────────────────────────────────────────────


class TestProject:
    def test_create(self, project):
        assert project.name == "My Project"
        assert project.goal == "Build something"
        assert project.pk is not None

    def test_str(self, project):
        assert str(project) == "My Project"

    def test_owner_cascade(self, project, user):
        user.delete()
        assert not Project.objects.filter(pk=project.pk).exists()

    def test_config_set_null(self, project, config):
        config.delete()
        project.refresh_from_db()
        assert project.config is None

    def test_config_fk_multiple_projects(self, user, config):
        p1 = Project.objects.create(name="P1", owner=user, config=config)
        p2 = Project.objects.create(name="P2", owner=user, config=config)
        assert config.projects.count() == 2
        assert set(config.projects.values_list("pk", flat=True)) == {p1.pk, p2.pk}

    def test_blank_goal(self, user):
        p = Project.objects.create(name="No goal", owner=user)
        assert p.goal == ""


# ── Department ─────────────────────────────────────────────────────────────────


class TestDepartment:
    def test_create(self, department, project):
        assert department.department_type == "marketing"
        assert department.name == "Marketing"  # property from blueprint registry
        assert department.project == project

    def test_str(self, department):
        assert str(department) == "My Project / Marketing"

    def test_unique_per_project(self, project):
        Department.objects.create(department_type="marketing", project=project)
        with pytest.raises(IntegrityError):
            Department.objects.create(department_type="marketing", project=project)

    def test_same_name_different_project(self, user, project):
        p2 = Project.objects.create(name="Other", owner=user)
        Department.objects.create(department_type="marketing", project=project)
        d2 = Department.objects.create(department_type="marketing", project=p2)
        assert d2.pk is not None

    def test_cascade_on_project_delete(self, department, project):
        project.delete()
        assert not Department.objects.filter(pk=department.pk).exists()


# ── Tag ────────────────────────────────────────────────────────────────────────


class TestTag:
    def test_create(self, tag):
        assert tag.name == "important"

    def test_str(self, tag):
        assert str(tag) == "important"

    def test_unique_name(self, tag):
        with pytest.raises(IntegrityError):
            Tag.objects.create(name="important")


# ── Document ───────────────────────────────────────────────────────────────────


class TestDocument:
    def test_create(self, department):
        doc = Document.objects.create(title="Readme", content="# Hello", department=department)
        assert doc.title == "Readme"
        assert doc.content == "# Hello"

    def test_str(self, department):
        doc = Document.objects.create(title="Readme", department=department)
        assert str(doc) == "Readme"

    def test_tags_m2m(self, department, tag):
        doc = Document.objects.create(title="Doc", department=department)
        tag2 = Tag.objects.create(name="urgent")
        doc.tags.add(tag, tag2)
        assert doc.tags.count() == 2
        assert tag in doc.tags.all()

    def test_cascade_on_department_delete(self, department):
        doc = Document.objects.create(title="Gone", department=department)
        department.delete()
        assert not Document.objects.filter(pk=doc.pk).exists()


# ── Source ─────────────────────────────────────────────────────────────────────


class TestSource:
    def test_create_file(self, project, user):
        s = Source.objects.create(
            project=project,
            source_type=Source.SourceType.FILE,
            original_filename="test.pdf",
            file_key="projects/abc/sources/test.pdf",
            content_hash="abc123",
            user=user,
            file_format="pdf",
        )
        assert s.source_type == "file"
        assert s.pk is not None

    def test_create_url(self, project, user):
        s = Source.objects.create(
            project=project,
            source_type=Source.SourceType.URL,
            url="https://example.com/page",
            user=user,
        )
        assert s.source_type == "url"

    def test_create_text(self, project, user):
        s = Source.objects.create(
            project=project,
            source_type=Source.SourceType.TEXT,
            raw_content="Hello world",
            user=user,
        )
        assert s.source_type == "text"

    def test_source_type_choices(self):
        choices = dict(Source.SourceType.choices)
        assert choices == {"file": "File", "url": "URL", "text": "Text"}

    def test_str_file(self, project, user):
        s = Source.objects.create(
            project=project,
            source_type="file",
            original_filename="report.pdf",
            user=user,
        )
        assert str(s) == "report.pdf — My Project"

    def test_str_url(self, project, user):
        s = Source.objects.create(
            project=project,
            source_type="url",
            url="https://example.com/very-long-url-that-should-be-truncated",
            user=user,
        )
        assert "example.com" in str(s)
        assert "My Project" in str(s)

    def test_str_text(self, project, user):
        s = Source.objects.create(
            project=project,
            source_type="text",
            raw_content="Some text",
            user=user,
        )
        assert str(s) == "Text source — My Project"

    def test_unique_content_hash_per_user(self, project, user):
        Source.objects.create(
            project=project,
            source_type="file",
            content_hash="deadbeef",
            user=user,
        )
        with pytest.raises(IntegrityError):
            Source.objects.create(
                project=project,
                source_type="file",
                content_hash="deadbeef",
                user=user,
            )

    def test_same_hash_different_users(self, project, user, user2):
        Source.objects.create(project=project, source_type="file", content_hash="deadbeef", user=user)
        s2 = Source.objects.create(project=project, source_type="file", content_hash="deadbeef", user=user2)
        assert s2.pk is not None

    def test_empty_hash_allowed_duplicates(self, project, user):
        """Empty content_hash should not trigger the unique constraint."""
        Source.objects.create(project=project, source_type="text", content_hash="", user=user)
        s2 = Source.objects.create(project=project, source_type="text", content_hash="", user=user)
        assert s2.pk is not None

    def test_cascade_on_project_delete(self, project, user):
        s = Source.objects.create(project=project, source_type="text", user=user)
        project.delete()
        assert not Source.objects.filter(pk=s.pk).exists()

    def test_ordering(self, project, user):
        s1 = Source.objects.create(project=project, source_type="text", user=user)
        s2 = Source.objects.create(project=project, source_type="text", user=user)
        sources = list(Source.objects.filter(project=project))
        # Newest first
        assert sources[0].pk == s2.pk
        assert sources[1].pk == s1.pk


# ── BootstrapProposal ─────────────────────────────────────────────────────────


class TestBootstrapProposal:
    def test_create(self, project):
        bp = BootstrapProposal.objects.create(project=project)
        assert bp.status == "pending"
        assert bp.proposal is None
        assert bp.error_message == ""

    def test_status_choices(self):
        choices = dict(BootstrapProposal.Status.choices)
        assert set(choices.keys()) == {"pending", "processing", "proposed", "approved", "failed"}

    def test_str(self, project):
        bp = BootstrapProposal.objects.create(project=project)
        assert str(bp) == "[Pending] Bootstrap for My Project"

    def test_str_proposed(self, project):
        bp = BootstrapProposal.objects.create(project=project, status="proposed")
        assert str(bp) == "[Proposed] Bootstrap for My Project"

    def test_proposal_json(self, project):
        data = {"departments": [{"name": "Sales"}]}
        bp = BootstrapProposal.objects.create(project=project, proposal=data)
        bp.refresh_from_db()
        assert bp.proposal == data

    def test_cascade_on_project_delete(self, project):
        bp = BootstrapProposal.objects.create(project=project)
        project.delete()
        assert not BootstrapProposal.objects.filter(pk=bp.pk).exists()

    def test_ordering(self, project):
        BootstrapProposal.objects.create(project=project)
        bp2 = BootstrapProposal.objects.create(project=project)
        proposals = list(BootstrapProposal.objects.filter(project=project))
        assert proposals[0].pk == bp2.pk


# ── DocumentConsolidation ──────────────────────────────────────────────────────


class TestDocumentConsolidation:
    def test_document_has_consolidated_into_field(self, department):
        parent = Document.objects.create(
            title="Original",
            content="old content",
            department=department,
        )
        child = Document.objects.create(
            title="Consolidated",
            content="merged content",
            department=department,
            consolidated_into=parent,
        )
        assert child.consolidated_into == parent
        assert parent.consolidated_from.count() == 1

    def test_document_type_choices(self, department):
        doc = Document.objects.create(
            title="Sprint Progress",
            content="results",
            department=department,
            document_type="sprint_progress",
        )
        assert doc.document_type == "sprint_progress"

    def test_document_sprint_fk(self, user, department):
        from projects.models import Sprint

        sprint = Sprint.objects.create(
            project=department.project,
            text="Write chapter 1",
            created_by=user,
        )
        sprint.departments.add(department)
        doc = Document.objects.create(
            title="Progress",
            content="done",
            department=department,
            sprint=sprint,
        )
        assert doc.sprint == sprint
        assert sprint.documents.count() == 1

    def test_consolidated_into_nullable(self, department):
        doc = Document.objects.create(
            title="Standalone",
            content="content",
            department=department,
        )
        assert doc.consolidated_into is None

    def test_document_type_default(self, department):
        doc = Document.objects.create(
            title="Test",
            content="content",
            department=department,
        )
        assert doc.document_type == "general"
