"""Tests for the Output model."""

import pytest
from django.db import IntegrityError

from projects.models import Output


class TestOutputModel:
    def test_output_type_choices(self):
        choices = [c[0] for c in Output.OutputType.choices]
        assert "markdown" in choices
        assert "plaintext" in choices
        assert "link" in choices
        assert "file" in choices

    def test_no_fountain_type(self):
        choices = [c[0] for c in Output.OutputType.choices]
        assert "fountain" not in choices

    def test_no_version_field(self):
        field_names = [f.name for f in Output._meta.get_fields()]
        assert "version" not in field_names
        assert "parent" not in field_names

    def test_no_project_field(self):
        """Project is derived from sprint, not stored directly."""
        field_names = [f.name for f in Output._meta.get_fields()]
        assert "project" not in field_names

    def test_has_sprint_field(self):
        field_names = [f.name for f in Output._meta.get_fields()]
        assert "sprint" in field_names

    def test_has_url_field(self):
        field_names = [f.name for f in Output._meta.get_fields()]
        assert "url" in field_names


class TestOutputConstraints:
    @pytest.mark.django_db
    def test_two_outputs_same_label_rejected(self):
        """Two outputs with the same (sprint, department, label) must fail."""
        from django.contrib.auth import get_user_model
        from projects.models import Department, Project, Sprint

        User = get_user_model()
        user = User.objects.create_user(email="test2@test.com", password="test")
        project = Project.objects.create(name="Test", goal="Test", owner=user)
        dept = Department.objects.create(project=project, department_type="writers_room")
        sprint = Sprint.objects.create(project=project, text="Write a pitch", created_by=user)
        sprint.departments.add(dept)

        Output.objects.create(sprint=sprint, department=dept, title="Expose Deliverable", label="expose:deliverable", output_type="markdown", content="v1")

        with pytest.raises(IntegrityError):
            Output.objects.create(sprint=sprint, department=dept, title="Expose Deliverable", label="expose:deliverable", output_type="markdown", content="v2")

    @pytest.mark.django_db
    def test_three_outputs_different_labels_allowed(self):
        """Three outputs with different labels for same sprint+dept must succeed."""
        from django.contrib.auth import get_user_model
        from projects.models import Department, Project, Sprint

        User = get_user_model()
        user = User.objects.create_user(email="test3@test.com", password="test")
        project = Project.objects.create(name="Test", goal="Test", owner=user)
        dept = Department.objects.create(project=project, department_type="writers_room")
        sprint = Sprint.objects.create(project=project, text="Write a pitch", created_by=user)
        sprint.departments.add(dept)

        Output.objects.create(sprint=sprint, department=dept, title="Expose Deliverable", label="expose:deliverable", output_type="markdown", content="d")
        Output.objects.create(sprint=sprint, department=dept, title="Expose Critique", label="expose:critique", output_type="markdown", content="c")
        Output.objects.create(sprint=sprint, department=dept, title="Expose Research", label="expose:research", output_type="markdown", content="r")

        assert Output.objects.filter(sprint=sprint, department=dept).count() == 3
