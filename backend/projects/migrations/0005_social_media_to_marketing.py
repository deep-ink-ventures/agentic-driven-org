"""Rename department_type social_media -> marketing."""

from django.db import migrations


def forwards(apps, schema_editor):
    Department = apps.get_model("projects", "Department")
    Department.objects.filter(department_type="social_media").update(department_type="marketing")


def backwards(apps, schema_editor):
    Department = apps.get_model("projects", "Department")
    Department.objects.filter(department_type="marketing").update(department_type="social_media")


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0004_department_type"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
