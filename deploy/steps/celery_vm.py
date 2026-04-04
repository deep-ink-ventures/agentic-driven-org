"""Step 11: GCE VM for Celery worker + beat."""

from pathlib import Path

from rich.console import Console

from deploy.steps.base import BaseStep

console = Console()

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class CeleryVMStep(BaseStep):
    name = "celery_vm"
    description = "Create GCE VM for Celery worker + beat"

    def run(self) -> dict:
        resources = self.state.get("resources", {})

        # Read and fill startup script template
        template = (TEMPLATE_DIR / "celery-vm-startup.sh.tpl").read_text()
        startup_script = template.format(
            company=self.config.company,
            project_id=self.config.project_id,
            region=self.provider.region,
            registry_url=resources.get("registry_url", ""),
            sql_connection=resources.get("sql_connection_name", ""),
            secret_prefix=self.config.secret_prefix,
            redis_host=resources.get("redis_host", ""),
            sql_database=self.config.sql_database_name,
            sql_user=self.config.sql_user,
            bucket_name=self.config.bucket_name,
            domain=self.config.domain,
        )

        result = self.provider.create_vm(
            self.config.project_id,
            self.config.celery_vm_name,
            self.config.zone,
            startup_script,
        )

        console.print(f"[green]Celery VM created: {self.config.celery_vm_name}[/green]")
        console.print(f"[dim]SSH: gcloud compute ssh {self.config.celery_vm_name} --zone={self.config.zone} --project={self.config.project_id}[/dim]")

        return result
