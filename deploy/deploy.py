#!/usr/bin/env python3
"""Deployment automation for the-agentic-company.

Provisions a complete isolated tenant stack on Google Cloud.

Usage:
    python deploy/deploy.py --company acme --provider gcloud
"""

import click
from rich.console import Console
from rich.panel import Panel

from deploy.config import TenantConfig
from deploy.providers.gcloud import GCloudProvider
from deploy.state import load_state
from deploy.steps import get_steps

console = Console()

PROVIDERS = {
    "gcloud": GCloudProvider,
}


@click.command()
@click.option("--company", required=True, help="Company name (e.g. 'acme')")
@click.option("--provider", default="gcloud", type=click.Choice(["gcloud"]), help="Cloud provider")
@click.option("--region", default="europe-west1", help="Cloud region")
def deploy(company: str, provider: str, region: str) -> None:
    """Provision a complete tenant stack."""
    config = TenantConfig(company=company, region=region)
    cloud = PROVIDERS[provider](region=region)
    state = load_state(company)

    console.print(Panel(
        f"[bold]Company:[/bold] {company}\n"
        f"[bold]Provider:[/bold] {provider}\n"
        f"[bold]Region:[/bold] {region}\n"
        f"[bold]Project:[/bold] {config.project_id}\n"
        f"[bold]Domain:[/bold] {config.domain}",
        title="Deployment Configuration",
        border_style="blue",
    ))

    click.confirm("Proceed with deployment?", abort=True)

    steps = get_steps(config, cloud, state)
    total = len(steps)

    for i, step in enumerate(steps, 1):
        console.print(f"\n[bold]Step {i}/{total}[/bold]")
        step.execute()

    console.print(Panel(
        f"[bold green]Deployment complete![/bold green]\n\n"
        f"[bold]Backend:[/bold] https://{config.domain}\n"
        f"[bold]Frontend:[/bold] https://{config.domain}\n"
        f"[bold]Celery VM:[/bold] {config.celery_vm_name}\n\n"
        f"[dim]State saved to deploy/state/{company}.json[/dim]",
        title="Done",
        border_style="green",
    ))


if __name__ == "__main__":
    deploy()
