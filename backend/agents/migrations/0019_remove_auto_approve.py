from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("agents", "0018_populate_enabled_commands"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="agent",
            name="auto_approve",
        ),
    ]
