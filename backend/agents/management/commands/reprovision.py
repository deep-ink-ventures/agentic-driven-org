"""Reprovision agents: re-generate instructions via Claude.

Usage:
    # Reprovision a single agent by ID
    python manage.py reprovision <agent-id>

    # Reprovision all workforce agents in a department
    python manage.py reprovision --department <department-id>

    # Reprovision all agents in a project (leaders + workforce)
    python manage.py reprovision --project <project-id>

    # Also reprovision leaders (default: workforce only)
    python manage.py reprovision --department <id> --include-leaders

    # Synchronous mode (wait for completion, useful for debugging)
    python manage.py reprovision <agent-id> --sync
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Re-provision agents by re-generating their instructions via Claude."

    def add_arguments(self, parser):
        parser.add_argument("agent_id", nargs="?", help="UUID of a single agent to reprovision")
        parser.add_argument("--department", help="UUID of department — reprovision all its workforce agents")
        parser.add_argument("--project", help="UUID of project — reprovision all agents across all departments")
        parser.add_argument(
            "--include-leaders", action="store_true", help="Also reprovision leader agents (default: workforce only)"
        )
        parser.add_argument(
            "--sync", action="store_true", help="Run provisioning synchronously instead of dispatching Celery tasks"
        )

    def handle(self, *args, **options):
        from agents.models import Agent

        agents = self._resolve_agents(options)

        if not agents:
            raise CommandError("No agents found matching the given criteria.")

        self.stdout.write(f"Reprovisioning {len(agents)} agent(s)...\n")

        for agent in agents:
            dept_name = agent.department.name if agent.department else "—"
            self.stdout.write(f"  {agent.id}  {agent.agent_type:<25} {dept_name}")

            agent.status = Agent.Status.PROVISIONING
            agent.save(update_fields=["status"])

            if options["sync"]:
                self._provision_sync(agent)
            else:
                self._provision_async(agent)

        if not options["sync"]:
            self.stdout.write(self.style.SUCCESS(f"\nDispatched {len(agents)} provisioning task(s) to Celery."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nDone. {len(agents)} agent(s) reprovisioned."))

    def _resolve_agents(self, options):
        from agents.models import Agent

        if options["agent_id"]:
            try:
                return [Agent.objects.select_related("department__project").get(id=options["agent_id"])]
            except Agent.DoesNotExist as exc:
                raise CommandError(f"Agent {options['agent_id']} not found.") from exc

        qs = Agent.objects.select_related("department__project")

        if options["department"]:
            qs = qs.filter(department_id=options["department"])
        elif options["project"]:
            qs = qs.filter(department__project_id=options["project"])
        else:
            raise CommandError("Provide an agent_id, --department, or --project.")

        if not options["include_leaders"]:
            qs = qs.filter(is_leader=False)

        return list(qs.order_by("department__name", "agent_type"))

    def _provision_async(self, agent):
        if agent.is_leader:
            from projects.tasks import configure_new_department

            configure_new_department.delay(str(agent.department_id))
        else:
            from projects.tasks import provision_single_agent

            provision_single_agent.delay(str(agent.id))

    def _provision_sync(self, agent):
        if agent.is_leader:
            from projects.tasks import configure_new_department

            configure_new_department(str(agent.department_id))
        else:
            from projects.tasks import provision_single_agent

            provision_single_agent(str(agent.id))
