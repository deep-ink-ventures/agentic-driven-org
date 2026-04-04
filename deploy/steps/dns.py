"""Step 12: Domain mapping + manual DNS instructions."""

import time

import click
from rich.console import Console
from rich.panel import Panel

from deploy.steps.base import BaseStep

console = Console()


class DNSStep(BaseStep):
    name = "dns"
    description = "Configure domain mapping + DNS"

    def run(self) -> dict:
        project_id = self.config.project_id
        domain = self.config.domain

        # Create Cloud Run domain mapping
        result = self.provider.create_domain_mapping(
            project_id,
            self.config.backend_service_name,
            domain,
        )

        # Show manual DNS instructions
        console.print(Panel(
            f"[bold]Add this DNS record at Gandi for agentdriven.org:[/bold]\n\n"
            f"  Type:  CNAME\n"
            f"  Name:  {self.config.company}.as\n"
            f"  Value: ghs.googlehosted.com.\n\n"
            f"[dim]Log in to Gandi → Domain → agentdriven.org → DNS Records → Add Record[/dim]",
            title="Manual DNS Setup Required",
            border_style="yellow",
        ))

        click.pause("Press Enter when you've added the DNS record...")

        # Poll for SSL certificate
        console.print("\n[dim]Waiting for SSL certificate provisioning...[/dim]")
        for attempt in range(30):
            status = self.provider.check_ssl_status(project_id, domain)
            if status == "True":
                console.print(f"[green]SSL certificate provisioned for {domain}[/green]")
                return {"domain": domain, "ssl_provisioned": True}
            console.print(f"[dim]  Attempt {attempt + 1}/30 — SSL status: {status}[/dim]")
            time.sleep(30)

        console.print("[yellow]SSL not yet provisioned. It may take up to 24h.[/yellow]")
        console.print(f"[dim]Check later: gcloud run domain-mappings describe --domain={domain} --region={self.provider.region} --project={project_id}[/dim]")

        return {"domain": domain, "ssl_provisioned": False}
