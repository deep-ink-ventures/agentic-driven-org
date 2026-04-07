from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("agents", "0016_add_agent_outreach_field"),
    ]

    operations = [
        migrations.AddField(
            model_name="agent",
            name="enabled_commands",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Maps command names to booleans. True = auto-execute, False/absent = needs approval.",
            ),
        ),
    ]
