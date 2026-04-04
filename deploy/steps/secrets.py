"""Step 6: Populate Secret Manager — generate auto secrets, prompt for manual ones."""

import secrets

import click
from rich.console import Console

from deploy.config import AUTO_GENERATED_SECRETS, OPERATOR_PROVIDED_SECRETS
from deploy.steps.base import BaseStep

console = Console()


class SecretsStep(BaseStep):
    name = "secrets"
    description = "Configure secrets in Secret Manager"

    def run(self) -> dict:
        prefix = self.config.secret_prefix

        # Auto-generate secrets
        for secret_name in AUTO_GENERATED_SECRETS:
            full_name = f"{prefix}-{secret_name}"
            # django-secret-key and postgres-password
            # postgres-password was already set in database step
            if secret_name == "postgres-password":
                console.print(f"[dim]{full_name} already set in database step[/dim]")
                continue

            value = secrets.token_urlsafe(50)
            self.provider.set_secret(self.config.project_id, full_name, value)
            console.print(f"[dim]Generated {full_name}[/dim]")

        # Prompt for operator-provided secrets
        for secret_name in OPERATOR_PROVIDED_SECRETS:
            full_name = f"{prefix}-{secret_name}"
            console.print(f"\n[bold]Secret required: {secret_name}[/bold]")
            value = click.prompt(f"Enter value for {secret_name}", hide_input=True)
            self.provider.set_secret(self.config.project_id, full_name, value)
            console.print(f"[dim]Stored {full_name}[/dim]")

        return {"secrets_configured": True}
