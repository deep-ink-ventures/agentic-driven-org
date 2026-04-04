"""Step 7: OAuth consent screen + client credentials."""

import click
from rich.console import Console

from deploy.steps.base import BaseStep

console = Console()


class OAuthStep(BaseStep):
    name = "oauth"
    description = "Create OAuth consent screen + client"

    def run(self) -> dict:
        domain = self.config.domain
        project_id = self.config.project_id
        prefix = self.config.secret_prefix

        # Create consent screen
        self.provider.create_oauth_consent_screen(
            project_id,
            f"{self.config.company} - AgentDriven",
            domain,
        )

        # Create OAuth client
        redirect_uris = [
            f"https://{domain}/accounts/google/login/callback/",
            "http://localhost:8000/accounts/google/login/callback/",
        ]
        result = self.provider.create_oauth_client(
            project_id,
            f"{self.config.company}-agentdriven",
            redirect_uris,
        )

        client_id = result.get("oauth_client_id", "")
        client_secret = result.get("oauth_client_secret", "")

        # Store in Secret Manager
        if client_id:
            self.provider.set_secret(project_id, f"{prefix}-google-client-id", client_id)
            self.provider.set_secret(project_id, f"{prefix}-google-client-secret", client_secret)
            console.print("[dim]OAuth credentials stored in Secret Manager[/dim]")
        else:
            console.print("[yellow]Could not auto-create OAuth client.[/yellow]")
            console.print("[yellow]This may require manual setup in the Google Cloud Console:[/yellow]")
            console.print(f"  [link]https://console.cloud.google.com/apis/credentials?project={project_id}[/link]")
            client_id = click.prompt("Enter the OAuth Client ID")
            client_secret = click.prompt("Enter the OAuth Client Secret", hide_input=True)
            self.provider.set_secret(project_id, f"{prefix}-google-client-id", client_id)
            self.provider.set_secret(project_id, f"{prefix}-google-client-secret", client_secret)

        # Check if verification is needed
        console.print("\n[bold yellow]⚠ OAuth verification may be required for external users.[/bold yellow]")
        console.print(f"  Check: [link]https://console.cloud.google.com/apis/credentials/consent?project={project_id}[/link]")
        console.print("  If verification is needed, submit the request and continue.")
        click.pause("Press Enter to continue...")

        return {
            "oauth_client_id": client_id,
            "oauth_configured": True,
        }
