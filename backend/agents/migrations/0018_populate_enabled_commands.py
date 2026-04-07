"""Data migration: convert auto_approve=True → enabled_commands with all blueprint commands set True."""

from django.db import migrations


def forwards(apps, schema_editor):
    Agent = apps.get_model("agents", "Agent")

    for agent in Agent.objects.filter(auto_approve=True):
        try:
            from agents.blueprints import get_blueprint

            bp = get_blueprint(agent.agent_type, agent.department.department_type)
            cmds = bp.get_commands()
            agent.enabled_commands = {cmd["name"]: True for cmd in cmds}
        except Exception:
            # If blueprint lookup fails, leave enabled_commands empty
            agent.enabled_commands = {}
        agent.save(update_fields=["enabled_commands"])


def backwards(apps, schema_editor):
    Agent = apps.get_model("agents", "Agent")

    for agent in Agent.objects.all():
        if agent.enabled_commands and all(agent.enabled_commands.values()):
            agent.auto_approve = True
        else:
            agent.auto_approve = False
        agent.save(update_fields=["auto_approve"])


class Migration(migrations.Migration):
    dependencies = [
        ("agents", "0017_add_enabled_commands"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
