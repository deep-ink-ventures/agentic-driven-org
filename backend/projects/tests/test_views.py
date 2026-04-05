from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from agents.models import Agent
from projects.models import BootstrapProposal, Department, Project, ProjectConfig, Source

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="project-tester@example.com", password="pass1234")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="outsider@example.com", password="pass1234")


@pytest.fixture
def project(user):
    p = Project.objects.create(name="My Project", goal="Build something", owner=user)
    p.members.add(user)
    return p


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="marketing", project=project)


@pytest.fixture
def authed_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


# ── ProjectListView ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProjectListView:
    def test_lists_user_projects(self, authed_client, project):
        resp = authed_client.get("/api/projects/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["name"] == "My Project"

    def test_does_not_list_non_member_projects(self, api_client, other_user, project):
        api_client.force_authenticate(user=other_user)
        resp = api_client.get("/api/projects/")
        assert resp.status_code == 200
        assert len(resp.data) == 0

    def test_create_project(self, authed_client, user):
        resp = authed_client.post("/api/projects/", {"name": "New Project", "goal": "Ship it"}, format="json")
        assert resp.status_code == 201
        assert resp.data["name"] == "New Project"
        p = Project.objects.get(id=resp.data["id"])
        assert user in p.members.all()
        assert p.owner == user

    def test_requires_auth(self, api_client):
        resp = api_client.get("/api/projects/")
        assert resp.status_code in (401, 403)


# ── ProjectDetailView ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProjectDetailView:
    def test_returns_detail_with_departments(self, authed_client, project, department):
        Agent.objects.create(
            name="Bot",
            agent_type="twitter",
            department=department,
            status="active",
        )
        resp = authed_client.get(f"/api/projects/{project.slug}/detail/")
        assert resp.status_code == 200
        assert resp.data["name"] == "My Project"
        assert len(resp.data["departments"]) == 1
        assert len(resp.data["departments"][0]["agents"]) == 1

    def test_non_member_gets_404(self, api_client, other_user, project):
        api_client.force_authenticate(user=other_user)
        resp = api_client.get(f"/api/projects/{project.slug}/detail/")
        assert resp.status_code == 404


# ── BootstrapTriggerView ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestBootstrapTriggerView:
    @patch("projects.tasks.bootstrap_project")
    def test_triggers_bootstrap(self, mock_task, authed_client, project, user):
        Source.objects.create(project=project, source_type="text", raw_content="content", user=user)
        resp = authed_client.post(f"/api/projects/{project.id}/bootstrap/")
        assert resp.status_code == 202
        assert resp.data["status"] == "pending"
        mock_task.delay.assert_called_once()

    def test_requires_goal(self, authed_client, user):
        p = Project.objects.create(name="No Goal", goal="", owner=user)
        p.members.add(user)
        Source.objects.create(project=p, source_type="text", raw_content="x", user=user)
        resp = authed_client.post(f"/api/projects/{p.id}/bootstrap/")
        assert resp.status_code == 400
        assert "goal" in resp.data["error"].lower()

    @patch("projects.tasks.bootstrap_project")
    def test_triggers_without_sources(self, mock_task, authed_client, project):
        """Bootstrap can be triggered without sources — the task handles empty sources gracefully."""
        resp = authed_client.post(f"/api/projects/{project.id}/bootstrap/")
        assert resp.status_code == 202
        assert resp.data["status"] == "pending"
        mock_task.delay.assert_called_once()


# ── BootstrapLatestView ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestBootstrapLatestView:
    def test_returns_latest_proposal(self, authed_client, project):
        proposal = BootstrapProposal.objects.create(
            project=project,
            status=BootstrapProposal.Status.PROPOSED,
            proposal={"summary": "test", "departments": []},
        )
        resp = authed_client.get(f"/api/projects/{project.id}/bootstrap/latest/")
        assert resp.status_code == 200
        assert resp.data["id"] == str(proposal.id)

    def test_returns_null_when_none(self, authed_client, project):
        resp = authed_client.get(f"/api/projects/{project.id}/bootstrap/latest/")
        assert resp.status_code == 200
        assert resp.data["proposal"] is None


# ── BootstrapApproveView ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestBootstrapApproveView:
    def _make_proposal(self, project):
        return BootstrapProposal.objects.create(
            project=project,
            status=BootstrapProposal.Status.PROPOSED,
            proposal={
                "summary": "A great project about marketing",
                "departments": [
                    {
                        "department_type": "marketing",
                        "documents": [{"title": "Brand Guide", "content": "Be bold", "tags": ["brand"]}],
                        "agents": [{"name": "Twitter Bot", "agent_type": "twitter", "instructions": "Post tweets"}],
                    }
                ],
            },
        )

    def test_applies_proposal(self, authed_client, project):
        proposal = self._make_proposal(project)
        resp = authed_client.post(f"/api/projects/{project.id}/bootstrap/{proposal.id}/approve/")
        assert resp.status_code == 200
        proposal.refresh_from_db()
        assert proposal.status == "approved"
        project.refresh_from_db()
        assert project.status == "active"
        # Departments and agents were created
        assert project.departments.count() >= 1
        dept = project.departments.first()
        assert dept.agents.exists()

    def test_rejects_non_proposed(self, authed_client, project):
        proposal = BootstrapProposal.objects.create(
            project=project,
            status=BootstrapProposal.Status.PENDING,
        )
        resp = authed_client.post(f"/api/projects/{project.id}/bootstrap/{proposal.id}/approve/")
        assert resp.status_code == 400


# ── ProjectSourceListView ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProjectSourceListView:
    def test_list_sources(self, authed_client, project, user):
        Source.objects.create(project=project, source_type="text", raw_content="hello", user=user)
        resp = authed_client.get(f"/api/projects/{project.id}/sources/")
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_create_text_source(self, authed_client, project):
        resp = authed_client.post(
            f"/api/projects/{project.id}/sources/",
            {"source_type": "text", "raw_content": "Some text"},
            format="json",
        )
        assert resp.status_code == 201
        assert Source.objects.filter(project=project).count() == 1
        src = Source.objects.get(id=resp.data["id"])
        assert src.extracted_text == "Some text"

    def test_create_url_source(self, authed_client, project):
        with patch("projects.views.source_view.extract_text", return_value="extracted"):
            resp = authed_client.post(
                f"/api/projects/{project.id}/sources/",
                {"source_type": "url", "url": "https://example.com"},
                format="json",
            )
        assert resp.status_code == 201

    @patch("projects.views.source_view.upload_file", return_value="files/test.txt")
    @patch("projects.views.source_view.extract_text", return_value="file content")
    def test_file_upload(self, mock_extract, mock_upload, authed_client, project):
        f = SimpleUploadedFile("test.txt", b"Hello world", content_type="text/plain")
        resp = authed_client.post(
            f"/api/projects/{project.id}/sources/",
            {"file": f, "source_type": "file"},
            format="multipart",
        )
        assert resp.status_code == 201
        src = Source.objects.get(id=resp.data["id"])
        assert src.source_type == "file"
        assert src.original_filename == "test.txt"

    @patch("projects.views.source_view.upload_file", return_value="files/evil.exe")
    def test_file_upload_accepts_any_extension(self, mock_upload, authed_client, project):
        """Source view does not restrict file extensions — all file types are accepted."""
        f = SimpleUploadedFile("evil.exe", b"payload", content_type="application/octet-stream")
        resp = authed_client.post(
            f"/api/projects/{project.id}/sources/",
            {"file": f, "source_type": "file"},
            format="multipart",
        )
        assert resp.status_code == 201

    @patch("projects.views.source_view.upload_file", return_value="files/big.pdf")
    def test_file_upload_accepts_large_files(self, mock_upload, authed_client, project):
        """Source view does not enforce a file size limit — large files are accepted."""
        big_content = b"x" * (50 * 1024 * 1024 + 1)
        f = SimpleUploadedFile("big.pdf", big_content, content_type="application/pdf")
        resp = authed_client.post(
            f"/api/projects/{project.id}/sources/",
            {"file": f, "source_type": "file"},
            format="multipart",
        )
        assert resp.status_code == 201

    @patch("projects.views.source_view.upload_file", return_value="files/test.txt")
    @patch("projects.views.source_view.extract_text", return_value="content")
    def test_file_upload_strips_path_from_filename(self, mock_extract, mock_upload, authed_client, project):
        f = SimpleUploadedFile("/etc/passwd/../test.txt", b"Hello", content_type="text/plain")
        resp = authed_client.post(
            f"/api/projects/{project.id}/sources/",
            {"file": f, "source_type": "file"},
            format="multipart",
        )
        assert resp.status_code == 201
        src = Source.objects.get(id=resp.data["id"])
        assert "/" not in src.original_filename
        assert src.original_filename == "test.txt"


# ── ProjectConfigView ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProjectConfigView:
    def test_get_config_empty(self, authed_client, project):
        resp = authed_client.get(f"/api/projects/{project.slug}/config/")
        assert resp.status_code == 200
        assert resp.data["config"] == {}
        assert "schema" in resp.data

    def test_get_config_with_values(self, authed_client, project):
        pc = ProjectConfig.objects.create(name="Test Config", config={"google_email": "a@b.com"})
        project.config = pc
        project.save(update_fields=["config"])
        resp = authed_client.get(f"/api/projects/{project.slug}/config/")
        assert resp.status_code == 200
        assert resp.data["config"]["google_email"] == "a@b.com"

    def test_patch_creates_config_if_missing(self, authed_client, project):
        resp = authed_client.patch(
            f"/api/projects/{project.slug}/config/",
            {"config": {"google_email": "new@test.com"}},
            format="json",
        )
        assert resp.status_code == 200
        project.refresh_from_db()
        assert project.config is not None
        assert project.config.config["google_email"] == "new@test.com"

    def test_patch_merges_config(self, authed_client, project):
        pc = ProjectConfig.objects.create(name="Config", config={"google_email": "old@test.com"})
        project.config = pc
        project.save(update_fields=["config"])
        resp = authed_client.patch(
            f"/api/projects/{project.slug}/config/",
            {"config": {"google_email": "updated@test.com"}},
            format="json",
        )
        assert resp.status_code == 200
        pc.refresh_from_db()
        assert pc.config["google_email"] == "updated@test.com"

    def test_non_member_gets_404(self, api_client, other_user, project):
        api_client.force_authenticate(user=other_user)
        resp = api_client.get(f"/api/projects/{project.slug}/config/")
        assert resp.status_code == 404


# ── AvailableDepartmentsView ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestAvailableDepartmentsView:
    def test_returns_departments_with_recommendations(self, authed_client, project):
        mock_response = {
            "departments": ["marketing"],
            "agents": {"marketing": ["twitter", "web_researcher"]},
        }
        with patch("projects.views.add_department_view._get_recommendations") as mock_rec:
            mock_rec.return_value = mock_response
            resp = authed_client.get(f"/api/projects/{project.id}/departments/available/")
        assert resp.status_code == 200
        data = resp.data
        assert "departments" in data
        assert len(data["departments"]) > 0
        dept = data["departments"][0]
        assert "recommended" in dept
        assert "workforce" in dept
        agent = dept["workforce"][0]
        assert "recommended" in agent
        assert "essential" in agent
        assert "controls" in agent

    def test_graceful_fallback_on_recommendation_failure(self, authed_client, project):
        with patch("projects.views.add_department_view._get_recommendations") as mock_rec:
            mock_rec.side_effect = Exception("Claude unavailable")
            resp = authed_client.get(f"/api/projects/{project.id}/departments/available/")
        assert resp.status_code == 200
        # Should still return departments, just without recommendations
        assert len(resp.data["departments"]) > 0


# ── AddDepartmentView ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAddDepartmentView:
    @patch("projects.views.add_department_view.configure_new_department")
    def test_add_department_with_agent_selection(self, mock_configure, authed_client, project):
        resp = authed_client.post(
            f"/api/projects/{project.id}/departments/add/",
            {
                "departments": [
                    {"department_type": "marketing", "agents": ["twitter", "web_researcher"]},
                ],
                "context": "Test context",
            },
            format="json",
        )
        assert resp.status_code == 202
        assert len(resp.data["departments"]) == 1
        mock_configure.delay.assert_called_once()
        args = mock_configure.delay.call_args[0]
        # args are (department_id, context) — agents are created directly, not passed to configure
        assert args[1] == "Test context"

    @patch("projects.views.add_department_view.configure_new_department")
    def test_rejects_unknown_department(self, mock_configure, authed_client, project):
        resp = authed_client.post(
            f"/api/projects/{project.id}/departments/add/",
            {"departments": [{"department_type": "nonexistent", "agents": []}]},
            format="json",
        )
        assert resp.status_code == 400

    @patch("projects.views.add_department_view.configure_new_department")
    def test_rejects_empty_departments(self, mock_configure, authed_client, project):
        resp = authed_client.post(
            f"/api/projects/{project.id}/departments/add/",
            {"departments": []},
            format="json",
        )
        assert resp.status_code == 400


# ── TestBootstrapEssentialAgents ─────────────────────────────────────────────


@pytest.mark.django_db
class TestBootstrapEssentialAgents:
    def test_apply_proposal_includes_essential_agents(self, user):
        """Bootstrap should add essential agents even if Claude's proposal omits them."""
        from projects.models import BootstrapProposal, Department, Project

        project = Project.objects.create(name="Test", goal="Test goal", owner=user)
        project.members.add(user)
        proposal = BootstrapProposal.objects.create(
            project=project,
            status=BootstrapProposal.Status.PROPOSED,
            proposal={
                "summary": "Test",
                "departments": [
                    {
                        "department_type": "engineering",
                        "documents": [],
                        "agents": [
                            {"agent_type": "backend_engineer", "name": "Backend Dev", "instructions": "Build stuff"},
                        ],
                    }
                ],
            },
        )

        from projects.views.bootstrap_view import BootstrapApproveView

        view = BootstrapApproveView()
        view._apply_proposal(proposal)

        dept = Department.objects.get(project=project, department_type="engineering")
        agent_types = set(dept.agents.values_list("agent_type", flat=True))

        # ticket_manager is essential — should be included
        assert "ticket_manager" in agent_types
        # review_engineer controls backend_engineer — should be included
        assert "review_engineer" in agent_types
        # test_engineer controls backend_engineer — should be included
        assert "test_engineer" in agent_types
        # security_auditor controls backend_engineer — should be included
        assert "security_auditor" in agent_types

    def test_apply_proposal_does_not_duplicate_agents(self, user):
        """If Claude already recommended an essential agent, don't create it twice."""
        from projects.models import BootstrapProposal, Department, Project

        project = Project.objects.create(name="Test2", goal="Test goal", owner=user)
        project.members.add(user)
        proposal = BootstrapProposal.objects.create(
            project=project,
            status=BootstrapProposal.Status.PROPOSED,
            proposal={
                "summary": "Test",
                "departments": [
                    {
                        "department_type": "engineering",
                        "documents": [],
                        "agents": [
                            {"agent_type": "backend_engineer", "name": "Backend Dev", "instructions": "Build"},
                            {"agent_type": "ticket_manager", "name": "Ticket Mgr", "instructions": "Manage"},
                        ],
                    }
                ],
            },
        )

        from projects.views.bootstrap_view import BootstrapApproveView

        view = BootstrapApproveView()
        view._apply_proposal(proposal)

        dept = Department.objects.get(project=project, department_type="engineering")
        # ticket_manager should exist exactly once (not duplicated)
        assert dept.agents.filter(agent_type="ticket_manager").count() == 1
