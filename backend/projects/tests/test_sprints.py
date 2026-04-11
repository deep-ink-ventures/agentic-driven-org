"""Tests for Sprint model and API endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from agents.models import Agent, AgentTask
from projects.models import Department, Output, Project, Sprint

User = get_user_model()


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(email="sprint-tester@example.com", password="testpass123")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="outsider@example.com", password="testpass123")


@pytest.fixture
def project(user):
    p = Project.objects.create(name="Sprint Project", goal="Ship features", owner=user)
    p.members.add(user)
    return p


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="engineering", project=project)


@pytest.fixture
def sprint(project, department, user):
    s = Sprint.objects.create(
        project=project,
        text="Build the login page",
        created_by=user,
    )
    s.departments.add(department)
    return s


@pytest.fixture
def authed_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


# ── Sprint Model ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSprintModel:
    def test_create_with_required_fields(self, project, user):
        s = Sprint.objects.create(
            project=project,
            text="Do the work",
            created_by=user,
        )
        assert s.pk is not None
        assert s.status == Sprint.Status.RUNNING
        assert s.completed_at is None
        assert s.completion_summary == ""

    def test_str(self, sprint):
        result = str(sprint)
        assert "[running]" in result.lower()
        assert "Build the login page" in result
        assert "Sprint Project" in result

    def test_default_status_is_running(self, project, user):
        s = Sprint.objects.create(project=project, text="Go", created_by=user)
        assert s.status == "running"

    def test_status_transition_running_to_paused(self, sprint):
        sprint.status = Sprint.Status.PAUSED
        sprint.save()
        sprint.refresh_from_db()
        assert sprint.status == "paused"

    def test_status_transition_paused_to_running(self, sprint):
        sprint.status = Sprint.Status.PAUSED
        sprint.save()
        sprint.status = Sprint.Status.RUNNING
        sprint.save()
        sprint.refresh_from_db()
        assert sprint.status == "running"

    def test_status_transition_to_done_sets_completed_at(self, sprint):
        assert sprint.completed_at is None
        sprint.status = Sprint.Status.DONE
        sprint.completed_at = timezone.now()
        sprint.save()
        sprint.refresh_from_db()
        assert sprint.status == "done"
        assert sprint.completed_at is not None

    def test_completed_at_not_set_automatically_on_save(self, sprint):
        """completed_at is not auto-set by the model; the view sets it."""
        sprint.status = Sprint.Status.DONE
        sprint.save()
        sprint.refresh_from_db()
        assert sprint.completed_at is None

    def test_departments_m2m(self, project, user):
        dept1 = Department.objects.create(department_type="marketing", project=project)
        dept2 = Department.objects.create(department_type="engineering", project=project)
        s = Sprint.objects.create(project=project, text="Cross-dept sprint", created_by=user)
        s.departments.add(dept1, dept2)
        assert s.departments.count() == 2
        assert dept1 in s.departments.all()
        assert dept2 in s.departments.all()

    def test_cascade_on_project_delete(self, sprint, project):
        sprint_pk = sprint.pk
        project.delete()
        assert not Sprint.objects.filter(pk=sprint_pk).exists()

    def test_ordering_newest_first(self, project, user):
        s1 = Sprint.objects.create(project=project, text="First", created_by=user)
        s2 = Sprint.objects.create(project=project, text="Second", created_by=user)
        sprints = list(Sprint.objects.filter(project=project))
        assert sprints[0].pk == s2.pk
        assert sprints[1].pk == s1.pk

    def test_status_choices(self):
        choices = dict(Sprint.Status.choices)
        assert set(choices.keys()) == {"running", "paused", "done"}

    def test_department_display_name_property(self, department):
        """Department.display_name is a required property used by sprint serializer."""
        assert hasattr(department, "display_name")
        assert department.display_name == department.name


# ── Sprint API: Create & List ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestSprintListCreateView:
    @patch("agents.tasks.create_next_leader_task")
    def test_create_sprint(self, mock_task, authed_client, project, department):
        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/",
            {
                "text": "Build the dashboard",
                "department_ids": [str(department.id)],
                "source_ids": [],
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["text"] == "Build the dashboard"
        assert resp.data["status"] == "running"
        assert Sprint.objects.filter(project=project).count() == 1

    @patch("agents.tasks.create_next_leader_task")
    def test_create_sprint_sets_departments(self, mock_task, authed_client, project, department):
        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/",
            {
                "text": "Cross-dept work",
                "department_ids": [str(department.id)],
            },
            format="json",
        )
        assert resp.status_code == 201
        sprint = Sprint.objects.get(id=resp.data["id"])
        assert sprint.departments.filter(id=department.id).exists()

    @patch("agents.tasks.create_next_leader_task")
    def test_create_sprint_returns_departments_list(self, mock_task, authed_client, project, department):
        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/",
            {"text": "Build feature", "department_ids": [str(department.id)]},
            format="json",
        )
        assert resp.status_code == 201
        depts = resp.data["departments"]
        assert isinstance(depts, list)
        assert len(depts) == 1
        assert depts[0]["department_type"] == "engineering"
        assert "display_name" in depts[0]

    def test_list_sprints(self, authed_client, project, sprint):
        resp = authed_client.get(f"/api/projects/{project.id}/sprints/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["id"] == str(sprint.id)

    def test_list_sprints_filter_by_status(self, authed_client, project, user):
        Sprint.objects.create(project=project, text="Running sprint", created_by=user, status="running")
        Sprint.objects.create(project=project, text="Paused sprint", created_by=user, status="paused")
        resp = authed_client.get(f"/api/projects/{project.id}/sprints/?status=running")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["status"] == "running"

    def test_list_sprints_filter_multiple_statuses(self, authed_client, project, user):
        Sprint.objects.create(project=project, text="Running sprint", created_by=user, status="running")
        Sprint.objects.create(project=project, text="Paused sprint", created_by=user, status="paused")
        Sprint.objects.create(project=project, text="Done sprint", created_by=user, status="done")
        resp = authed_client.get(f"/api/projects/{project.id}/sprints/?status=running,paused")
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_list_empty_for_other_project(self, authed_client, project, sprint, user):
        other = Project.objects.create(name="Other", owner=user)
        other.members.add(user)
        resp = authed_client.get(f"/api/projects/{other.id}/sprints/")
        assert resp.status_code == 200
        assert len(resp.data) == 0

    def test_create_requires_auth(self, api_client, project, department):
        resp = api_client.post(
            f"/api/projects/{project.id}/sprints/",
            {"text": "Unauthenticated", "department_ids": [str(department.id)]},
            format="json",
        )
        assert resp.status_code in (401, 403)

    def test_list_requires_auth(self, api_client, project):
        resp = api_client.get(f"/api/projects/{project.id}/sprints/")
        assert resp.status_code in (401, 403)

    @patch("agents.tasks.create_next_leader_task")
    def test_create_sprint_with_progress_from_sprint(self, mock_task, authed_client, project, department, user):
        """Outputs from a done sprint become Sources on the new sprint."""
        old_sprint = Sprint.objects.create(project=project, text="Old work", created_by=user, status="done")
        old_sprint.departments.add(department)
        Output.objects.create(
            sprint=old_sprint,
            department=department,
            title="Pitch Deliverable",
            label="pitch:deliverable",
            output_type="markdown",
            content="# The Pitch\n\nThis is the pitch content.",
        )
        Output.objects.create(
            sprint=old_sprint,
            department=department,
            title="Research Notes",
            label="pitch:research",
            output_type="markdown",
            content="## Research\n\nMarket analysis here.",
        )

        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/",
            {
                "text": "Continue the work",
                "department_ids": [str(department.id)],
                "progress_from_sprint_ids": [str(old_sprint.id)],
            },
            format="json",
        )
        assert resp.status_code == 201
        new_sprint = Sprint.objects.get(id=resp.data["id"])

        sources = list(new_sprint.sources.all())
        assert len(sources) == 2
        titles = {s.original_filename for s in sources}
        assert "Pitch Deliverable.md" in titles
        assert "Research Notes.md" in titles

        pitch_src = next(s for s in sources if "Pitch" in s.original_filename)
        assert pitch_src.source_type == "text"
        assert pitch_src.raw_content == "# The Pitch\n\nThis is the pitch content."
        assert pitch_src.extracted_text == pitch_src.raw_content
        assert pitch_src.project == project
        assert pitch_src.user == user

    @patch("agents.tasks.create_next_leader_task")
    def test_progress_from_sprint_skips_empty_outputs(self, mock_task, authed_client, project, department, user):
        """Outputs with no content or link/file type are skipped."""
        old_sprint = Sprint.objects.create(project=project, text="Old", created_by=user, status="done")
        old_sprint.departments.add(department)
        Output.objects.create(
            sprint=old_sprint,
            department=department,
            title="Empty",
            label="empty",
            output_type="markdown",
            content="",
        )
        Output.objects.create(
            sprint=old_sprint,
            department=department,
            title="A Link",
            label="link",
            output_type="link",
            url="https://example.com",
        )

        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/",
            {
                "text": "New sprint",
                "department_ids": [str(department.id)],
                "progress_from_sprint_ids": [str(old_sprint.id)],
            },
            format="json",
        )
        assert resp.status_code == 201
        new_sprint = Sprint.objects.get(id=resp.data["id"])
        assert new_sprint.sources.count() == 0

    @patch("agents.tasks.create_next_leader_task")
    def test_progress_from_sprint_validates_project(self, mock_task, authed_client, project, department, user):
        """Sprints from other projects are rejected."""
        other_project = Project.objects.create(name="Other", goal="Other", owner=user)
        other_sprint = Sprint.objects.create(project=other_project, text="Other", created_by=user, status="done")

        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/",
            {
                "text": "New sprint",
                "department_ids": [str(department.id)],
                "progress_from_sprint_ids": [str(other_sprint.id)],
            },
            format="json",
        )
        assert resp.status_code == 400

    @patch("agents.tasks.create_next_leader_task")
    def test_progress_from_sprint_validates_done_status(self, mock_task, authed_client, project, department, user):
        """Only done sprints can be referenced."""
        running_sprint = Sprint.objects.create(project=project, text="Still running", created_by=user, status="running")
        running_sprint.departments.add(department)

        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/",
            {
                "text": "New sprint",
                "department_ids": [str(department.id)],
                "progress_from_sprint_ids": [str(running_sprint.id)],
            },
            format="json",
        )
        assert resp.status_code == 400


# ── Sprint API: Update ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSprintDetailView:
    def test_patch_status_to_paused(self, authed_client, project, sprint):
        resp = authed_client.patch(
            f"/api/projects/{project.id}/sprints/{sprint.id}/",
            {"status": "paused"},
            format="json",
        )
        assert resp.status_code == 200
        sprint.refresh_from_db()
        assert sprint.status == "paused"

    @patch("agents.tasks.create_next_leader_task")
    def test_patch_status_to_done_sets_completed_at(self, mock_task, authed_client, project, sprint):
        resp = authed_client.patch(
            f"/api/projects/{project.id}/sprints/{sprint.id}/",
            {"status": "done"},
            format="json",
        )
        assert resp.status_code == 200
        sprint.refresh_from_db()
        assert sprint.status == "done"
        assert sprint.completed_at is not None

    @patch("agents.tasks.create_next_leader_task")
    def test_patch_status_to_done_sets_completion_summary(self, mock_task, authed_client, project, sprint):
        resp = authed_client.patch(
            f"/api/projects/{project.id}/sprints/{sprint.id}/",
            {"status": "done", "completion_summary": "We shipped the feature!"},
            format="json",
        )
        assert resp.status_code == 200
        sprint.refresh_from_db()
        assert sprint.completion_summary == "We shipped the feature!"

    @patch("agents.tasks.create_next_leader_task")
    def test_patch_paused_to_running_retriggers_leader(self, mock_task, authed_client, project, department, user):
        leader = Agent.objects.create(
            name="Lead Engineer",
            agent_type="engineering_lead",
            department=department,
            is_leader=True,
            status=Agent.Status.ACTIVE,
        )
        sprint = Sprint.objects.create(project=project, text="Resume work", created_by=user, status="paused")
        sprint.departments.add(department)

        resp = authed_client.patch(
            f"/api/projects/{project.id}/sprints/{sprint.id}/",
            {"status": "running"},
            format="json",
        )
        assert resp.status_code == 200
        mock_task.delay.assert_called_once_with(str(leader.id))

    def test_patch_requires_auth(self, api_client, project, sprint):
        resp = api_client.patch(
            f"/api/projects/{project.id}/sprints/{sprint.id}/",
            {"status": "paused"},
            format="json",
        )
        assert resp.status_code in (401, 403)

    def test_get_sprint_detail(self, authed_client, project, sprint):
        resp = authed_client.get(f"/api/projects/{project.id}/sprints/{sprint.id}/")
        assert resp.status_code == 200
        assert resp.data["id"] == str(sprint.id)
        assert resp.data["text"] == "Build the login page"


# ── Sprint-Task Relationship ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestSprintTaskRelationship:
    def test_agent_task_sprint_fk(self, project, department, sprint, user):
        agent = Agent.objects.create(
            name="Backend Dev",
            agent_type="backend_engineer",
            department=department,
            status=Agent.Status.ACTIVE,
        )
        task = AgentTask.objects.create(
            agent=agent,
            sprint=sprint,
            exec_summary="Implement login endpoint",
        )
        assert task.sprint == sprint
        assert sprint.tasks.count() == 1
        assert sprint.tasks.first() == task

    def test_task_count_on_serializer(self, authed_client, project, department, sprint, user):
        agent = Agent.objects.create(
            name="Backend Dev",
            agent_type="backend_engineer",
            department=department,
            status=Agent.Status.ACTIVE,
        )
        AgentTask.objects.create(agent=agent, sprint=sprint, exec_summary="Task 1")
        AgentTask.objects.create(agent=agent, sprint=sprint, exec_summary="Task 2")

        resp = authed_client.get(f"/api/projects/{project.id}/sprints/{sprint.id}/")
        assert resp.status_code == 200
        assert resp.data["task_count"] == 2

    def test_task_count_zero_by_default(self, authed_client, project, sprint):
        resp = authed_client.get(f"/api/projects/{project.id}/sprints/{sprint.id}/")
        assert resp.status_code == 200
        assert resp.data["task_count"] == 0

    def test_task_sprint_null_on_sprint_delete(self, project, department, sprint, user):
        agent = Agent.objects.create(
            name="Dev",
            agent_type="backend_engineer",
            department=department,
            status=Agent.Status.ACTIVE,
        )
        task = AgentTask.objects.create(agent=agent, sprint=sprint, exec_summary="Some task")
        sprint.delete()
        task.refresh_from_db()
        assert task.sprint is None


# ── Sprint Consolidation Signal ───────────────────────────────────────────────


@pytest.mark.django_db
class TestSprintConsolidationSignal:
    def test_sprint_done_triggers_consolidation(self, user, department):
        from projects.models import Sprint

        sprint = Sprint.objects.create(
            project=department.project,
            text="Test sprint",
            created_by=user,
        )
        sprint.departments.add(department)

        with patch("projects.signals.consolidate_sprint_documents") as mock_task:
            mock_task.delay = MagicMock()
            sprint.status = Sprint.Status.DONE
            sprint.save(update_fields=["status", "updated_at"])
            mock_task.delay.assert_called_once_with(str(sprint.id))

    def test_sprint_paused_triggers_consolidation(self, user, department):
        from projects.models import Sprint

        sprint = Sprint.objects.create(
            project=department.project,
            text="Test sprint",
            created_by=user,
        )
        sprint.departments.add(department)

        with patch("projects.signals.consolidate_sprint_documents") as mock_task:
            mock_task.delay = MagicMock()
            sprint.status = Sprint.Status.PAUSED
            sprint.save(update_fields=["status", "updated_at"])
            mock_task.delay.assert_called_once_with(str(sprint.id))

    def test_sprint_running_does_not_trigger(self, user, department):
        from projects.models import Sprint

        sprint = Sprint.objects.create(
            project=department.project,
            text="Test sprint",
            status=Sprint.Status.PAUSED,
            created_by=user,
        )
        sprint.departments.add(department)

        with patch("projects.signals.consolidate_sprint_documents") as mock_task:
            mock_task.delay = MagicMock()
            sprint.status = Sprint.Status.RUNNING
            sprint.save(update_fields=["status", "updated_at"])
            mock_task.delay.assert_not_called()

    def test_sprint_create_does_not_trigger(self, user, department):
        from projects.models import Sprint

        with patch("projects.signals.consolidate_sprint_documents") as mock_task:
            mock_task.delay = MagicMock()
            Sprint.objects.create(
                project=department.project,
                text="New sprint",
                created_by=user,
            )
            mock_task.delay.assert_not_called()
