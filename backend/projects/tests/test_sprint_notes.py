"""Tests for Sprint Notes API."""

import pytest

from projects.models import Department, Project, Source, Sprint, SprintNote


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(email="test@test.com", password="pass")


@pytest.fixture
def authed_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def project(user):
    return Project.objects.create(name="Test", goal="Test", owner=user)


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="writers_room", project=project)


@pytest.fixture
def sprint(project, department, user):
    s = Sprint.objects.create(project=project, text="Test sprint", created_by=user, status="running")
    s.departments.add(department)
    return s


@pytest.mark.django_db
class TestSprintNoteAPI:
    def test_create_note(self, authed_client, project, sprint):
        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/{sprint.id}/notes/",
            {"text": "Change the protagonist name to Kaya"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["text"] == "Change the protagonist name to Kaya"
        assert resp.data["user_email"] == "test@test.com"
        assert SprintNote.objects.filter(sprint=sprint).count() == 1

    def test_create_note_with_source_ids(self, authed_client, project, sprint, user):
        source = Source.objects.create(
            project=project,
            source_type="text",
            raw_content="Reference material",
            original_filename="ref.md",
            user=user,
        )
        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/{sprint.id}/notes/",
            {"text": "See attached reference", "source_ids": [str(source.id)]},
            format="json",
        )
        assert resp.status_code == 201
        note = SprintNote.objects.get(id=resp.data["id"])
        assert note.sources.count() == 1
        assert note.sources.first().id == source.id

    def test_list_notes(self, authed_client, project, sprint, user):
        SprintNote.objects.create(sprint=sprint, user=user, text="First note")
        SprintNote.objects.create(sprint=sprint, user=user, text="Second note")
        resp = authed_client.get(
            f"/api/projects/{project.id}/sprints/{sprint.id}/notes/",
        )
        assert resp.status_code == 200
        assert len(resp.data) == 2
        assert resp.data[0]["text"] == "First note"
        assert resp.data[1]["text"] == "Second note"

    def test_list_notes_empty(self, authed_client, project, sprint):
        resp = authed_client.get(
            f"/api/projects/{project.id}/sprints/{sprint.id}/notes/",
        )
        assert resp.status_code == 200
        assert len(resp.data) == 0

    def test_create_note_requires_text(self, authed_client, project, sprint):
        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/{sprint.id}/notes/",
            {"text": ""},
            format="json",
        )
        assert resp.status_code == 400

    def test_create_note_requires_auth(self, client, project, sprint):
        resp = client.post(
            f"/api/projects/{project.id}/sprints/{sprint.id}/notes/",
            {"text": "Anon note"},
            format="json",
        )
        assert resp.status_code in [401, 403]
