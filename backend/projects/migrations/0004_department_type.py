"""Rename Department.name to department_type with new unique constraint."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0003_projectconfig_project_config"),
    ]

    operations = [
        # 1. Drop old unique_together
        migrations.AlterUniqueTogether(
            name="department",
            unique_together=set(),
        ),
        # 2. Rename field
        migrations.RenameField(
            model_name="department",
            old_name="name",
            new_name="department_type",
        ),
        # 3. Update field definition
        migrations.AlterField(
            model_name="department",
            name="department_type",
            field=models.CharField(
                default="social_media",
                help_text="Department type — must match a blueprint folder (e.g. social_media, engineering)",
                max_length=50,
            ),
        ),
        # 4. New unique_together
        migrations.AlterUniqueTogether(
            name="department",
            unique_together={("project", "department_type")},
        ),
    ]
