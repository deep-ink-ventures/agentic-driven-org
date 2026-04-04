"""Step 13: Create deploy service account for CI/CD."""

import click
from rich.console import Console
from rich.panel import Panel

from deploy.steps.base import BaseStep

console = Console()

DEPLOY_SA_ROLES = [
    "roles/run.admin",
    "roles/artifactregistry.writer",
    "roles/compute.instanceAdmin.v1",
    "roles/secretmanager.secretAccessor",
    "roles/iam.serviceAccountUser",
]


class ServiceAccountStep(BaseStep):
    name = "service_account"
    description = "Create deploy service account for CI/CD"

    def run(self) -> dict:
        project_id = self.config.project_id
        company = self.config.company
        sa_name = f"{company}-deploy"
        sa_email = f"{sa_name}@{project_id}.iam.gserviceaccount.com"

        # Create service account
        self.provider.create_service_account(project_id, sa_name, f"Deploy SA for {company}")

        # Grant roles
        for role in DEPLOY_SA_ROLES:
            self.provider.grant_project_role(project_id, sa_email, role)

        # Create key
        key_path = f"/tmp/{company}-deploy-key.json"
        self.provider.create_sa_key(project_id, sa_email, key_path)

        # Display instructions
        gh_secret_name = f"GCP_SA_KEY_{company.upper()}"
        console.print(Panel(
            f"[bold]Add this service account key to GitHub repo secrets:[/bold]\n\n"
            f"  Secret name: [bold]{gh_secret_name}[/bold]\n"
            f"  Key file: [bold]{key_path}[/bold]\n\n"
            f"  Run: [dim]cat {key_path} | pbcopy[/dim]\n"
            f"  Then paste as the secret value in GitHub → Settings → Secrets\n\n"
            f"[yellow]Delete the key file after adding it to GitHub.[/yellow]",
            title="GitHub Actions Setup",
            border_style="yellow",
        ))

        click.pause("Press Enter after you've added the secret to GitHub...")

        return {
            "deploy_sa_email": sa_email,
            "gh_secret_name": gh_secret_name,
        }
