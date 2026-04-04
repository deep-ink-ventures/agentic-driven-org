"""Step 1: Create GCP project, link billing, enable APIs."""

import click
from rich.console import Console

from deploy.config import REQUIRED_APIS, TenantConfig
from deploy.steps.base import BaseStep

console = Console()


class ProjectStep(BaseStep):
    name = "project"
    description = "Create GCP project + enable APIs"

    def run(self) -> dict:
        console.print(f"Creating GCP project: [bold]{self.config.project_id}[/bold]")

        # Ask for billing account
        billing_account = click.prompt(
            "Enter your GCP billing account ID (e.g. 012345-6789AB-CDEF01)"
        )

        resources = self.provider.create_project(self.config.project_id, billing_account)

        console.print(f"Enabling {len(REQUIRED_APIS)} APIs...")
        self.provider.enable_apis(self.config.project_id, REQUIRED_APIS)

        resources["billing_account"] = billing_account
        return resources
