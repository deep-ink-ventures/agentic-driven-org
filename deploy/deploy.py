#!/usr/bin/env python3
"""Deployment automation for the-agentic-company."""

import click


@click.command()
@click.option("--company", required=True, help="Company name (e.g. 'acme')")
@click.option("--provider", default="gcloud", type=click.Choice(["gcloud"]), help="Cloud provider")
@click.option("--region", default="europe-west1", help="Cloud region")
def deploy(company: str, provider: str, region: str) -> None:
    """Provision a complete tenant stack."""
    click.echo(f"Deploying {company} on {provider} in {region}")


if __name__ == "__main__":
    deploy()
