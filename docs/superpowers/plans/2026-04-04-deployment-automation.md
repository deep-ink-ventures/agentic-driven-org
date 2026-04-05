# Deployment Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive Python CLI that provisions a complete isolated tenant stack on Google Cloud — from GCP project creation through DNS wiring — in one run.

**Architecture:** A `deploy/` folder at monorepo root. Entry point (`deploy.py`) orchestrates sequential steps, each in its own module under `steps/`. Provider abstraction (`providers/base.py` + `providers/gcloud.py`) isolates all `gcloud` CLI calls. State file per tenant enables resume-after-interruption.

**Tech Stack:** Python 3.12, click (CLI), rich (pretty output), subprocess (gcloud CLI)

**Spec:** `docs/superpowers/specs/2026-04-04-deployment-automation-design.md`

---

## File Structure

```
deploy/
├── deploy.py                          # CLI entry point — click app, step orchestrator
├── config.py                          # Naming conventions, region defaults, API list
├── state.py                           # Load/save/update tenant state JSON
├── providers/
│   ├── base.py                        # Abstract CloudProvider interface
│   └── gcloud.py                      # GCloudProvider — all gcloud CLI calls
├── steps/
│   ├── __init__.py                    # Step registry — ordered list of all steps
│   ├── base.py                        # BaseStep — run/skip/state logic
│   ├── project.py                     # Step 1: GCP project + billing + APIs
│   ├── networking.py                  # Step 2: VPC, subnet, VPC connector, firewall
│   ├── database.py                    # Step 3: Cloud SQL Postgres 16
│   ├── redis.py                       # Step 4: Memorystore Redis 7
│   ├── storage.py                     # Step 5: GCS bucket
│   ├── secrets.py                     # Step 6: Secret Manager entries
│   ├── oauth.py                       # Step 7: OAuth consent screen + client
│   ├── registry.py                    # Step 8: Artifact Registry + build/push
│   ├── backend.py                     # Step 9: Cloud Run backend
│   ├── frontend.py                    # Step 10: Cloud Run frontend
│   ├── celery_vm.py                   # Step 11: GCE VM for Celery
│   └── dns.py                         # Step 12: Domain mapping + manual DNS
├── templates/
│   └── celery-vm-startup.sh.tpl       # VM startup script template
├── requirements.txt                   # click, rich
└── .gitignore                         # state/ directory
```

---

## Task 1: Project scaffold + dependencies

**Files:**
- Create: `deploy/requirements.txt`
- Create: `deploy/.gitignore`
- Create: `deploy/deploy.py` (stub)

- [ ] **Step 1: Create requirements.txt**

```
click>=8.1
rich>=13.0
```

- [ ] **Step 2: Create .gitignore**

```
state/
__pycache__/
*.pyc
.venv/
```

- [ ] **Step 3: Create deploy.py stub**

```python
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
```

- [ ] **Step 4: Verify it runs**

Run: `cd /Users/christianpeters/the-agentic-company && pip install click rich && python deploy/deploy.py --company test`
Expected: `Deploying test on gcloud in europe-west1`

- [ ] **Step 5: Commit**

```bash
git add deploy/requirements.txt deploy/.gitignore deploy/deploy.py
git commit -m "feat(deploy): scaffold deployment automation project"
```

---

## Task 2: Config + naming conventions

**Files:**
- Create: `deploy/config.py`

- [ ] **Step 1: Create config.py**

```python
"""Naming conventions and configuration for tenant deployments."""

from dataclasses import dataclass, field


# APIs to enable on every new GCP project
REQUIRED_APIS = [
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "compute.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "vpcaccess.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iamcredentials.googleapis.com",
]

# Secrets that the script generates automatically
AUTO_GENERATED_SECRETS = [
    "django-secret-key",
    "postgres-password",
]

# Secrets the operator must provide
OPERATOR_PROVIDED_SECRETS = [
    "anthropic-api-key",
]

# Base domain for all tenant subdomains
BASE_DOMAIN = "as.agentdriven.org"


@dataclass
class TenantConfig:
    """All derived names for a tenant deployment."""

    company: str
    region: str
    zone: str = ""

    # Derived names — set in __post_init__
    project_id: str = ""
    vpc_name: str = ""
    subnet_name: str = ""
    vpc_connector_name: str = ""
    sql_instance_name: str = ""
    sql_database_name: str = "agentdriven"
    sql_user: str = "agentdriven"
    redis_instance_name: str = ""
    bucket_name: str = ""
    backend_service_name: str = ""
    frontend_service_name: str = ""
    celery_vm_name: str = ""
    registry_name: str = ""
    domain: str = ""
    secret_prefix: str = ""

    def __post_init__(self) -> None:
        if not self.zone:
            self.zone = f"{self.region}-b"

        c = self.company
        self.project_id = f"{c}-agentdriven"
        self.vpc_name = f"{c}-agentdriven-vpc"
        self.subnet_name = f"{c}-agentdriven-subnet"
        self.vpc_connector_name = f"{c}-vpc-connector"
        self.sql_instance_name = f"{c}-agentdriven-db"
        self.redis_instance_name = f"{c}-agentdriven-redis"
        self.bucket_name = f"{c}-agentdriven-storage"
        self.backend_service_name = f"{c}-backend"
        self.frontend_service_name = f"{c}-frontend"
        self.celery_vm_name = f"{c}-celery-vm"
        self.registry_name = f"{c}-agentdriven"
        self.domain = f"{c}.{BASE_DOMAIN}"
        self.secret_prefix = f"{c}-agentdriven"
```

- [ ] **Step 2: Verify config instantiation**

Run: `python -c "from deploy.config import TenantConfig; c = TenantConfig('acme', 'europe-west1'); print(c.project_id, c.domain, c.celery_vm_name)"`
Expected: `acme-agentdriven acme.as.agentdriven.org acme-celery-vm`

- [ ] **Step 3: Commit**

```bash
git add deploy/config.py
git commit -m "feat(deploy): tenant config with naming conventions"
```

---

## Task 3: State management

**Files:**
- Create: `deploy/state.py`

- [ ] **Step 1: Create state.py**

```python
"""Tenant deployment state — tracks provisioned resources for resume."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path(__file__).parent / "state"


def _state_path(company: str) -> Path:
    return STATE_DIR / f"{company}.json"


def load_state(company: str) -> dict:
    """Load existing state or return empty state."""
    path = _state_path(company)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"company": company, "steps": {}, "resources": {}}


def save_state(company: str, state: dict) -> None:
    """Persist state to disk."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = _state_path(company)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def mark_step_complete(state: dict, step_name: str, resources: dict | None = None) -> None:
    """Mark a step as completed and record any resource identifiers."""
    state["steps"][step_name] = {
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if resources:
        state["resources"].update(resources)


def is_step_complete(state: dict, step_name: str) -> bool:
    """Check if a step has already been completed."""
    step = state.get("steps", {}).get(step_name, {})
    return step.get("status") == "completed"
```

- [ ] **Step 2: Verify state round-trip**

Run:
```bash
python -c "
from deploy.state import load_state, save_state, mark_step_complete, is_step_complete
s = load_state('test')
assert not is_step_complete(s, 'project')
mark_step_complete(s, 'project', {'project_id': 'test-agentdriven'})
save_state('test', s)
s2 = load_state('test')
assert is_step_complete(s2, 'project')
assert s2['resources']['project_id'] == 'test-agentdriven'
print('OK')
import os; os.remove('deploy/state/test.json')
"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add deploy/state.py
git commit -m "feat(deploy): state management for resumable deployments"
```

---

## Task 4: Provider base + GCloud provider

**Files:**
- Create: `deploy/providers/__init__.py`
- Create: `deploy/providers/base.py`
- Create: `deploy/providers/gcloud.py`

- [ ] **Step 1: Create providers/__init__.py**

```python
```

(Empty init file.)

- [ ] **Step 2: Create providers/base.py**

```python
"""Abstract cloud provider interface."""

from abc import ABC, abstractmethod


class CloudProvider(ABC):
    """Interface for cloud infrastructure operations.

    Each method returns a dict of resource identifiers to store in state.
    """

    def __init__(self, region: str) -> None:
        self.region = region

    @abstractmethod
    def create_project(self, project_id: str, billing_account: str) -> dict:
        ...

    @abstractmethod
    def enable_apis(self, project_id: str, apis: list[str]) -> None:
        ...

    @abstractmethod
    def create_vpc(self, project_id: str, vpc_name: str, subnet_name: str) -> dict:
        ...

    @abstractmethod
    def create_vpc_connector(self, project_id: str, connector_name: str, vpc_name: str) -> dict:
        ...

    @abstractmethod
    def create_firewall_rules(self, project_id: str, vpc_name: str) -> None:
        ...

    @abstractmethod
    def create_sql_instance(self, project_id: str, instance_name: str, vpc_name: str) -> dict:
        ...

    @abstractmethod
    def create_sql_database(self, project_id: str, instance_name: str, db_name: str, user: str, password: str) -> dict:
        ...

    @abstractmethod
    def create_redis(self, project_id: str, instance_name: str, vpc_name: str) -> dict:
        ...

    @abstractmethod
    def create_bucket(self, project_id: str, bucket_name: str) -> dict:
        ...

    @abstractmethod
    def set_secret(self, project_id: str, secret_name: str, value: str) -> None:
        ...

    @abstractmethod
    def get_secret(self, project_id: str, secret_name: str) -> str:
        ...

    @abstractmethod
    def create_oauth_consent_screen(self, project_id: str, app_name: str, domain: str) -> dict:
        ...

    @abstractmethod
    def create_oauth_client(self, project_id: str, app_name: str, redirect_uris: list[str]) -> dict:
        ...

    @abstractmethod
    def create_artifact_registry(self, project_id: str, repo_name: str) -> dict:
        ...

    @abstractmethod
    def build_and_push_image(self, project_id: str, repo_name: str, image_name: str, context_dir: str, dockerfile: str) -> str:
        ...

    @abstractmethod
    def deploy_cloud_run(self, project_id: str, service_name: str, image: str, env_vars: dict, vpc_connector: str, extra_args: list[str] | None = None) -> dict:
        ...

    @abstractmethod
    def create_vm(self, project_id: str, vm_name: str, zone: str, startup_script: str, machine_type: str = "e2-small") -> dict:
        ...

    @abstractmethod
    def create_domain_mapping(self, project_id: str, service_name: str, domain: str) -> dict:
        ...

    @abstractmethod
    def check_ssl_status(self, project_id: str, domain: str) -> str:
        ...
```

- [ ] **Step 3: Create providers/gcloud.py**

```python
"""Google Cloud provider — shells out to gcloud CLI."""

import json
import subprocess
import sys

from rich.console import Console

from .base import CloudProvider

console = Console()


class GCloudProvider(CloudProvider):
    """Provision infrastructure via the gcloud CLI."""

    def _run(self, args: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
        """Run a gcloud command."""
        cmd = ["gcloud"] + args + ["--format=json"]
        console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            console.print(f"[red]Command failed:[/red] {result.stderr}")
            sys.exit(1)
        return result

    def _run_json(self, args: list[str]) -> dict | list:
        """Run a gcloud command and parse JSON output."""
        result = self._run(args)
        if not result.stdout.strip():
            return {}
        return json.loads(result.stdout)

    def _project_flag(self, project_id: str) -> list[str]:
        return [f"--project={project_id}"]

    def create_project(self, project_id: str, billing_account: str) -> dict:
        # Check if project already exists
        result = self._run(["projects", "describe", project_id], check=False)
        if result.returncode == 0:
            console.print(f"[yellow]Project {project_id} already exists, skipping creation[/yellow]")
        else:
            self._run(["projects", "create", project_id])
        # Link billing
        subprocess.run(
            ["gcloud", "billing", "projects", "link", project_id,
             f"--billing-account={billing_account}"],
            check=True, text=True,
        )
        return {"project_id": project_id}

    def enable_apis(self, project_id: str, apis: list[str]) -> None:
        self._run(["services", "enable"] + apis + self._project_flag(project_id))

    def create_vpc(self, project_id: str, vpc_name: str, subnet_name: str) -> dict:
        # Create VPC
        self._run([
            "compute", "networks", "create", vpc_name,
            "--subnet-mode=custom",
        ] + self._project_flag(project_id))
        # Create subnet
        self._run([
            "compute", "networks", "subnets", "create", subnet_name,
            f"--network={vpc_name}",
            f"--region={self.region}",
            "--range=10.0.0.0/20",
        ] + self._project_flag(project_id))
        return {"vpc_name": vpc_name, "subnet_name": subnet_name}

    def create_vpc_connector(self, project_id: str, connector_name: str, vpc_name: str) -> dict:
        self._run([
            "compute", "networks", "vpc-access", "connectors", "create", connector_name,
            f"--region={self.region}",
            f"--network={vpc_name}",
            "--range=10.8.0.0/28",
            "--min-instances=2",
            "--max-instances=3",
        ] + self._project_flag(project_id))
        return {"vpc_connector": connector_name}

    def create_firewall_rules(self, project_id: str, vpc_name: str) -> None:
        # Allow internal traffic
        self._run([
            "compute", "firewall-rules", "create", f"{vpc_name}-allow-internal",
            f"--network={vpc_name}",
            "--allow=tcp,udp,icmp",
            "--source-ranges=10.0.0.0/20,10.8.0.0/28",
        ] + self._project_flag(project_id))
        # Allow SSH to Celery VM
        self._run([
            "compute", "firewall-rules", "create", f"{vpc_name}-allow-ssh",
            f"--network={vpc_name}",
            "--allow=tcp:22",
            "--source-ranges=0.0.0.0/0",
            "--target-tags=celery-vm",
        ] + self._project_flag(project_id))

    def create_sql_instance(self, project_id: str, instance_name: str, vpc_name: str) -> dict:
        # Allocate private IP range
        self._run([
            "compute", "addresses", "create", f"{instance_name}-ip-range",
            "--global",
            "--purpose=VPC_PEERING",
            "--prefix-length=16",
            f"--network={vpc_name}",
        ] + self._project_flag(project_id))
        # Create private connection
        self._run([
            "services", "vpc-peerings", "connect",
            "--service=servicenetworking.googleapis.com",
            f"--ranges={instance_name}-ip-range",
            f"--network={vpc_name}",
        ] + self._project_flag(project_id))
        # Create instance
        result = self._run_json([
            "sql", "instances", "create", instance_name,
            "--database-version=POSTGRES_16",
            "--tier=db-f1-micro",
            f"--region={self.region}",
            f"--network=projects/{project_id}/global/networks/{vpc_name}",
            "--no-assign-ip",
            "--storage-size=10GB",
            "--storage-auto-increase",
        ] + self._project_flag(project_id))
        private_ip = ""
        if isinstance(result, dict):
            private_ip = result.get("ipAddresses", [{}])[0].get("ipAddress", "")
        return {"sql_instance": instance_name, "sql_private_ip": private_ip}

    def create_sql_database(self, project_id: str, instance_name: str, db_name: str, user: str, password: str) -> dict:
        self._run([
            "sql", "databases", "create", db_name,
            f"--instance={instance_name}",
        ] + self._project_flag(project_id))
        self._run([
            "sql", "users", "create", user,
            f"--instance={instance_name}",
            f"--password={password}",
        ] + self._project_flag(project_id))
        return {"sql_database": db_name, "sql_user": user}

    def create_redis(self, project_id: str, instance_name: str, vpc_name: str) -> dict:
        result = self._run_json([
            "redis", "instances", "create", instance_name,
            f"--region={self.region}",
            "--size=1",
            "--tier=basic",
            f"--network=projects/{project_id}/global/networks/{vpc_name}",
            "--redis-version=redis_7_0",
        ] + self._project_flag(project_id))
        redis_host = ""
        if isinstance(result, dict):
            redis_host = result.get("host", "")
        return {"redis_instance": instance_name, "redis_host": redis_host}

    def create_bucket(self, project_id: str, bucket_name: str) -> dict:
        self._run([
            "storage", "buckets", "create", f"gs://{bucket_name}",
            f"--location={self.region}",
            "--uniform-bucket-level-access",
        ] + self._project_flag(project_id))
        return {"bucket": bucket_name}

    def set_secret(self, project_id: str, secret_name: str, value: str) -> None:
        # Create secret (ignore if exists)
        self._run([
            "secrets", "create", secret_name,
            "--replication-policy=automatic",
        ] + self._project_flag(project_id), check=False)
        # Add version with value via stdin
        proc = subprocess.run(
            ["gcloud", "secrets", "versions", "add", secret_name,
             "--data-file=-", f"--project={project_id}"],
            input=value, text=True, capture_output=True, check=True,
        )

    def get_secret(self, project_id: str, secret_name: str) -> str:
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "access", "latest",
             f"--secret={secret_name}", f"--project={project_id}"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()

    def create_oauth_consent_screen(self, project_id: str, app_name: str, domain: str) -> dict:
        # OAuth consent screen must be configured via gcloud alpha or the API
        # Using gcloud alpha iap oauth-brands create
        self._run([
            "alpha", "iap", "oauth-brands", "create",
            f"--application_title={app_name}",
            f"--support_email=admin@{domain}",
        ] + self._project_flag(project_id), check=False)
        return {"oauth_consent_configured": True}

    def create_oauth_client(self, project_id: str, app_name: str, redirect_uris: list[str]) -> dict:
        # OAuth client creation via gcloud alpha
        result = self._run_json([
            "alpha", "iap", "oauth-clients", "create",
            f"projects/{project_id}/brands/-",
            f"--display_name={app_name}",
        ])
        client_id = ""
        client_secret = ""
        if isinstance(result, dict):
            client_id = result.get("name", "").split("/")[-1]
            client_secret = result.get("secret", "")
        return {"oauth_client_id": client_id, "oauth_client_secret": client_secret}

    def create_artifact_registry(self, project_id: str, repo_name: str) -> dict:
        self._run([
            "artifacts", "repositories", "create", repo_name,
            f"--location={self.region}",
            "--repository-format=docker",
        ] + self._project_flag(project_id))
        registry_url = f"{self.region}-docker.pkg.dev/{project_id}/{repo_name}"
        return {"registry_url": registry_url}

    def build_and_push_image(self, project_id: str, repo_name: str, image_name: str, context_dir: str, dockerfile: str) -> str:
        registry_url = f"{self.region}-docker.pkg.dev/{project_id}/{repo_name}"
        tag = f"{registry_url}/{image_name}:latest"
        subprocess.run(
            ["docker", "build", "-t", tag, "-f", dockerfile, context_dir],
            check=True, text=True,
        )
        subprocess.run(
            ["docker", "push", tag],
            check=True, text=True,
        )
        return tag

    def deploy_cloud_run(self, project_id: str, service_name: str, image: str, env_vars: dict, vpc_connector: str, extra_args: list[str] | None = None) -> dict:
        env_str = ",".join(f"{k}={v}" for k, v in env_vars.items())
        args = [
            "run", "deploy", service_name,
            f"--image={image}",
            f"--region={self.region}",
            f"--set-env-vars={env_str}",
            f"--vpc-connector={vpc_connector}",
            "--allow-unauthenticated",
            "--memory=1Gi",
            "--cpu=2",
            "--min-instances=0",
            "--max-instances=3",
        ] + self._project_flag(project_id)
        if extra_args:
            args.extend(extra_args)
        result = self._run_json(args)
        url = ""
        if isinstance(result, dict):
            url = result.get("status", {}).get("url", "")
        return {"service_url": url}

    def create_vm(self, project_id: str, vm_name: str, zone: str, startup_script: str, machine_type: str = "e2-small") -> dict:
        self._run([
            "compute", "instances", "create", vm_name,
            f"--zone={zone}",
            f"--machine-type={machine_type}",
            "--image-family=cos-stable",
            "--image-project=cos-cloud",
            "--tags=celery-vm",
            f"--metadata=startup-script={startup_script}",
            "--scopes=cloud-platform",
        ] + self._project_flag(project_id))
        return {"celery_vm": vm_name}

    def create_domain_mapping(self, project_id: str, service_name: str, domain: str) -> dict:
        self._run([
            "run", "domain-mappings", "create",
            f"--service={service_name}",
            f"--domain={domain}",
            f"--region={self.region}",
        ] + self._project_flag(project_id))
        return {"domain": domain}

    def check_ssl_status(self, project_id: str, domain: str) -> str:
        result = self._run_json([
            "run", "domain-mappings", "describe",
            f"--domain={domain}",
            f"--region={self.region}",
        ] + self._project_flag(project_id))
        if isinstance(result, dict):
            for condition in result.get("status", {}).get("conditions", []):
                if condition.get("type") == "CertificateProvisioned":
                    return condition.get("status", "Unknown")
        return "Unknown"
```

- [ ] **Step 4: Verify import**

Run: `python -c "from deploy.providers.gcloud import GCloudProvider; p = GCloudProvider('europe-west1'); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add deploy/providers/
git commit -m "feat(deploy): cloud provider abstraction + gcloud implementation"
```

---

## Task 5: Step base class + step registry

**Files:**
- Create: `deploy/steps/__init__.py`
- Create: `deploy/steps/base.py`

- [ ] **Step 1: Create steps/base.py**

```python
"""Base class for provisioning steps."""

from abc import ABC, abstractmethod

from rich.console import Console

from deploy.config import TenantConfig
from deploy.providers.base import CloudProvider
from deploy.state import is_step_complete, mark_step_complete, save_state

console = Console()


class BaseStep(ABC):
    """A single provisioning step."""

    name: str = ""  # Override in subclass
    description: str = ""  # Override in subclass

    def __init__(self, config: TenantConfig, provider: CloudProvider, state: dict) -> None:
        self.config = config
        self.provider = provider
        self.state = state

    def execute(self) -> None:
        """Run the step, skipping if already completed."""
        if is_step_complete(self.state, self.name):
            console.print(f"[green]✓[/green] {self.description} [dim](already done)[/dim]")
            return

        console.print(f"\n[bold blue]→ {self.description}[/bold blue]")
        resources = self.run()
        mark_step_complete(self.state, self.name, resources)
        save_state(self.config.company, self.state)
        console.print(f"[green]✓[/green] {self.description} [green]complete[/green]")

    @abstractmethod
    def run(self) -> dict | None:
        """Execute the step. Return resource identifiers to store in state."""
        ...
```

- [ ] **Step 2: Create steps/__init__.py**

```python
"""Step registry — ordered list of all provisioning steps."""


def get_steps(config, provider, state) -> list:
    """Return all steps in execution order."""
    from .project import ProjectStep
    from .networking import NetworkingStep
    from .database import DatabaseStep
    from .redis import RedisStep
    from .storage import StorageStep
    from .secrets import SecretsStep
    from .oauth import OAuthStep
    from .registry import RegistryStep
    from .backend import BackendStep
    from .frontend import FrontendStep
    from .celery_vm import CeleryVMStep
    from .dns import DNSStep

    step_classes = [
        ProjectStep,
        NetworkingStep,
        DatabaseStep,
        RedisStep,
        StorageStep,
        SecretsStep,
        OAuthStep,
        RegistryStep,
        BackendStep,
        FrontendStep,
        CeleryVMStep,
        DNSStep,
    ]
    return [cls(config, provider, state) for cls in step_classes]
```

- [ ] **Step 3: Commit**

```bash
git add deploy/steps/__init__.py deploy/steps/base.py
git commit -m "feat(deploy): step base class and registry"
```

---

## Task 6: Step 1 — Project creation

**Files:**
- Create: `deploy/steps/project.py`

- [ ] **Step 1: Create steps/project.py**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add deploy/steps/project.py
git commit -m "feat(deploy): step 1 — GCP project creation"
```

---

## Task 7: Step 2 — Networking

**Files:**
- Create: `deploy/steps/networking.py`

- [ ] **Step 1: Create steps/networking.py**

```python
"""Step 2: VPC, subnet, serverless VPC connector, firewall rules."""

from deploy.steps.base import BaseStep


class NetworkingStep(BaseStep):
    name = "networking"
    description = "Create VPC, subnet, VPC connector, firewall rules"

    def run(self) -> dict:
        resources = self.provider.create_vpc(
            self.config.project_id,
            self.config.vpc_name,
            self.config.subnet_name,
        )

        connector = self.provider.create_vpc_connector(
            self.config.project_id,
            self.config.vpc_connector_name,
            self.config.vpc_name,
        )
        resources.update(connector)

        self.provider.create_firewall_rules(
            self.config.project_id,
            self.config.vpc_name,
        )

        return resources
```

- [ ] **Step 2: Commit**

```bash
git add deploy/steps/networking.py
git commit -m "feat(deploy): step 2 — VPC networking"
```

---

## Task 8: Step 3 — Database

**Files:**
- Create: `deploy/steps/database.py`

- [ ] **Step 1: Create steps/database.py**

```python
"""Step 3: Cloud SQL Postgres 16 — instance, database, user."""

import secrets

from rich.console import Console

from deploy.steps.base import BaseStep

console = Console()


class DatabaseStep(BaseStep):
    name = "database"
    description = "Provision Cloud SQL Postgres 16"

    def run(self) -> dict:
        # Create instance with private IP
        resources = self.provider.create_sql_instance(
            self.config.project_id,
            self.config.sql_instance_name,
            self.config.vpc_name,
        )

        # Generate a secure password
        db_password = secrets.token_urlsafe(32)

        # Create database and user
        db_resources = self.provider.create_sql_database(
            self.config.project_id,
            self.config.sql_instance_name,
            self.config.sql_database_name,
            self.config.sql_user,
            db_password,
        )
        resources.update(db_resources)

        # Store password in Secret Manager
        self.provider.set_secret(
            self.config.project_id,
            f"{self.config.secret_prefix}-postgres-password",
            db_password,
        )
        console.print("[dim]Database password stored in Secret Manager[/dim]")

        # Store the Cloud SQL connection name for proxy
        connection_name = f"{self.config.project_id}:{self.provider.region}:{self.config.sql_instance_name}"
        resources["sql_connection_name"] = connection_name

        return resources
```

- [ ] **Step 2: Commit**

```bash
git add deploy/steps/database.py
git commit -m "feat(deploy): step 3 — Cloud SQL Postgres"
```

---

## Task 9: Step 4 — Redis

**Files:**
- Create: `deploy/steps/redis.py`

- [ ] **Step 1: Create steps/redis.py**

```python
"""Step 4: Memorystore Redis 7."""

from deploy.steps.base import BaseStep


class RedisStep(BaseStep):
    name = "redis"
    description = "Provision Memorystore Redis 7"

    def run(self) -> dict:
        return self.provider.create_redis(
            self.config.project_id,
            self.config.redis_instance_name,
            self.config.vpc_name,
        )
```

- [ ] **Step 2: Commit**

```bash
git add deploy/steps/redis.py
git commit -m "feat(deploy): step 4 — Memorystore Redis"
```

---

## Task 10: Step 5 — Storage

**Files:**
- Create: `deploy/steps/storage.py`

- [ ] **Step 1: Create steps/storage.py**

```python
"""Step 5: GCS bucket for file storage."""

from deploy.steps.base import BaseStep


class StorageStep(BaseStep):
    name = "storage"
    description = "Create GCS storage bucket"

    def run(self) -> dict:
        return self.provider.create_bucket(
            self.config.project_id,
            self.config.bucket_name,
        )
```

- [ ] **Step 2: Commit**

```bash
git add deploy/steps/storage.py
git commit -m "feat(deploy): step 5 — GCS bucket"
```

---

## Task 11: Step 6 — Secrets

**Files:**
- Create: `deploy/steps/secrets.py`

- [ ] **Step 1: Create steps/secrets.py**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add deploy/steps/secrets.py
git commit -m "feat(deploy): step 6 — Secret Manager configuration"
```

---

## Task 12: Step 7 — OAuth

**Files:**
- Create: `deploy/steps/oauth.py`

- [ ] **Step 1: Create steps/oauth.py**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add deploy/steps/oauth.py
git commit -m "feat(deploy): step 7 — OAuth consent screen + client"
```

---

## Task 13: Step 8 — Artifact Registry + Docker images

**Files:**
- Create: `deploy/steps/registry.py`

This step needs Dockerfiles. The monorepo doesn't have them yet, so the step creates them if missing.

- [ ] **Step 1: Create steps/registry.py**

```python
"""Step 8: Artifact Registry — create repo, build + push backend and frontend images."""

import os
from pathlib import Path

from rich.console import Console

from deploy.steps.base import BaseStep

console = Console()

MONOREPO_ROOT = Path(__file__).parent.parent.parent

BACKEND_DOCKERFILE = """\
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \\
    libpq-dev gcc && \\
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN DJANGO_SECRET_KEY=build-placeholder python manage.py collectstatic --noinput

RUN useradd -r -s /bin/false appuser
USER appuser

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
"""

FRONTEND_DOCKERFILE = """\
FROM node:22-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
"""


class RegistryStep(BaseStep):
    name = "registry"
    description = "Create Artifact Registry + build/push Docker images"

    def _ensure_dockerfile(self, path: Path, content: str, name: str) -> None:
        if not path.exists():
            console.print(f"[yellow]Creating {name} Dockerfile at {path}[/yellow]")
            path.write_text(content)
        else:
            console.print(f"[dim]{name} Dockerfile already exists[/dim]")

    def run(self) -> dict:
        project_id = self.config.project_id
        repo_name = self.config.registry_name

        # Create registry
        resources = self.provider.create_artifact_registry(project_id, repo_name)

        # Configure docker auth for the registry
        os.system(f"gcloud auth configure-docker {self.provider.region}-docker.pkg.dev --quiet")

        # Ensure Dockerfiles exist
        backend_dir = MONOREPO_ROOT / "backend"
        frontend_dir = MONOREPO_ROOT / "frontend"
        self._ensure_dockerfile(backend_dir / "Dockerfile", BACKEND_DOCKERFILE, "Backend")
        self._ensure_dockerfile(frontend_dir / "Dockerfile", FRONTEND_DOCKERFILE, "Frontend")

        # Build and push backend
        console.print("\n[bold]Building backend image...[/bold]")
        backend_tag = self.provider.build_and_push_image(
            project_id, repo_name, "backend",
            str(backend_dir), str(backend_dir / "Dockerfile"),
        )
        resources["backend_image"] = backend_tag

        # Build and push frontend
        console.print("\n[bold]Building frontend image...[/bold]")
        frontend_tag = self.provider.build_and_push_image(
            project_id, repo_name, "frontend",
            str(frontend_dir), str(frontend_dir / "Dockerfile"),
        )
        resources["frontend_image"] = frontend_tag

        return resources
```

- [ ] **Step 2: Commit**

```bash
git add deploy/steps/registry.py
git commit -m "feat(deploy): step 8 — Artifact Registry + Docker builds"
```

---

## Task 14: Step 9 — Backend Cloud Run

**Files:**
- Create: `deploy/steps/backend.py`

- [ ] **Step 1: Create steps/backend.py**

```python
"""Step 9: Deploy Django backend to Cloud Run."""

from rich.console import Console

from deploy.steps.base import BaseStep

console = Console()


class BackendStep(BaseStep):
    name = "backend"
    description = "Deploy Django backend to Cloud Run"

    def run(self) -> dict:
        project_id = self.config.project_id
        prefix = self.config.secret_prefix
        resources = self.state.get("resources", {})

        redis_host = resources.get("redis_host", "")
        sql_connection = resources.get("sql_connection_name", "")
        backend_image = resources.get("backend_image", "")

        # Fetch secrets from Secret Manager for env vars
        django_sk = self.provider.get_secret(project_id, f"{prefix}-django-secret-key")
        pg_pass = self.provider.get_secret(project_id, f"{prefix}-postgres-password")
        anthropic_key = self.provider.get_secret(project_id, f"{prefix}-anthropic-api-key")
        google_cid = self.provider.get_secret(project_id, f"{prefix}-google-client-id")
        google_csecret = self.provider.get_secret(project_id, f"{prefix}-google-client-secret")

        env_vars = {
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJANGO_DEBUG": "false",
            "DJANGO_ALLOWED_HOSTS": f"{self.config.domain},localhost",
            "DJANGO_SECRET_KEY": django_sk,
            "POSTGRES_DB": self.config.sql_database_name,
            "POSTGRES_USER": self.config.sql_user,
            "POSTGRES_PASSWORD": pg_pass,
            "POSTGRES_HOST": "/cloudsql/" + sql_connection,
            "POSTGRES_PORT": "5432",
            "REDIS_URL": f"redis://{redis_host}:6379/0",
            "GOOGLE_CLIENT_ID": google_cid,
            "GOOGLE_CLIENT_SECRET": google_csecret,
            "ANTHROPIC_API_KEY": anthropic_key,
            "STORAGE_BACKEND": "gcs",
            "GCS_BUCKET": self.config.bucket_name,
            "GCP_PROJECT_ID": project_id,
            "FRONTEND_URL": f"https://{self.config.domain}",
            "CORS_ALLOWED_ORIGINS": f"https://{self.config.domain}",
            "CSRF_TRUSTED_ORIGINS": f"https://{self.config.domain}",
            "ONLY_ALLOWLIST_CAN_SIGN_UP": "true",
        }

        extra_args = [
            f"--add-cloudsql-instances={sql_connection}",
            "--port=8000",
        ]

        result = self.provider.deploy_cloud_run(
            project_id,
            self.config.backend_service_name,
            backend_image,
            env_vars,
            self.config.vpc_connector_name,
            extra_args,
        )

        backend_url = result.get("service_url", "")
        console.print(f"[green]Backend deployed at {backend_url}[/green]")

        return {"backend_url": backend_url}
```

- [ ] **Step 2: Commit**

```bash
git add deploy/steps/backend.py
git commit -m "feat(deploy): step 9 — Cloud Run backend deployment"
```

---

## Task 15: Step 10 — Frontend Cloud Run

**Files:**
- Create: `deploy/steps/frontend.py`

- [ ] **Step 1: Create steps/frontend.py**

```python
"""Step 10: Deploy Next.js frontend to Cloud Run."""

from rich.console import Console

from deploy.steps.base import BaseStep

console = Console()


class FrontendStep(BaseStep):
    name = "frontend"
    description = "Deploy Next.js frontend to Cloud Run"

    def run(self) -> dict:
        project_id = self.config.project_id
        resources = self.state.get("resources", {})

        backend_url = resources.get("backend_url", "")
        frontend_image = resources.get("frontend_image", "")

        env_vars = {
            "NEXT_PUBLIC_API_URL": backend_url,
            "NEXT_PUBLIC_PROJECT_NAME": "Frontier",
        }

        extra_args = [
            "--port=3000",
        ]

        result = self.provider.deploy_cloud_run(
            project_id,
            self.config.frontend_service_name,
            frontend_image,
            env_vars,
            self.config.vpc_connector_name,
            extra_args,
        )

        frontend_url = result.get("service_url", "")
        console.print(f"[green]Frontend deployed at {frontend_url}[/green]")

        return {"frontend_url": frontend_url}
```

- [ ] **Step 2: Commit**

```bash
git add deploy/steps/frontend.py
git commit -m "feat(deploy): step 10 — Cloud Run frontend deployment"
```

---

## Task 16: Step 11 — Celery VM

**Files:**
- Create: `deploy/steps/celery_vm.py`
- Create: `deploy/templates/celery-vm-startup.sh.tpl`

- [ ] **Step 1: Create templates/celery-vm-startup.sh.tpl**

```bash
#!/bin/bash
# Celery VM startup script for {company}
# Pulls backend image, runs Cloud SQL Auth Proxy, starts celery worker+beat

set -euo pipefail

PROJECT="{project_id}"
REGION="{region}"
REGISTRY="{registry_url}"
SQL_CONNECTION="{sql_connection}"
SECRET_PREFIX="{secret_prefix}"
REDIS_HOST="{redis_host}"

# Authenticate Docker with Artifact Registry
gcloud auth configure-docker ${{REGION}}-docker.pkg.dev --quiet

# Fetch secrets from Secret Manager
DJANGO_SK=$(gcloud secrets versions access latest --secret="${{SECRET_PREFIX}}-django-secret-key" --project=${{PROJECT}})
PG_PASS=$(gcloud secrets versions access latest --secret="${{SECRET_PREFIX}}-postgres-password" --project=${{PROJECT}})
ANTHROPIC_KEY=$(gcloud secrets versions access latest --secret="${{SECRET_PREFIX}}-anthropic-api-key" --project=${{PROJECT}})
GOOGLE_CID=$(gcloud secrets versions access latest --secret="${{SECRET_PREFIX}}-google-client-id" --project=${{PROJECT}})
GOOGLE_CSECRET=$(gcloud secrets versions access latest --secret="${{SECRET_PREFIX}}-google-client-secret" --project=${{PROJECT}})

IMAGE="${{REGISTRY}}/backend:latest"

# Pull latest image
docker pull ${{IMAGE}}

# Start Cloud SQL Auth Proxy (if not running)
if ! docker ps --format '{{{{.Names}}}}' | grep -q cloud-sql-proxy; then
    docker run -d \
        --name cloud-sql-proxy \
        --restart=always \
        --network=host \
        gcr.io/cloud-sql-connectors/cloud-sql-proxy:2 \
        --address 0.0.0.0 \
        --port 5432 \
        ${{SQL_CONNECTION}}
fi

# Build env file
cat > /tmp/celery.env << ENVEOF
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=${{DJANGO_SK}}
ANTHROPIC_API_KEY=${{ANTHROPIC_KEY}}
POSTGRES_DB={sql_database}
POSTGRES_USER={sql_user}
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_PASSWORD=${{PG_PASS}}
REDIS_URL=redis://${{REDIS_HOST}}:6379/0
GOOGLE_CLIENT_ID=${{GOOGLE_CID}}
GOOGLE_CLIENT_SECRET=${{GOOGLE_CSECRET}}
STORAGE_BACKEND=gcs
GCS_BUCKET={bucket_name}
GCP_PROJECT_ID=${{PROJECT}}
FRONTEND_URL=https://{domain}
ONLY_ALLOWLIST_CAN_SIGN_UP=true
ENVEOF

# Rolling restart: start new, wait, stop old
docker run -d \
    --name celery-worker-new \
    --restart=always \
    --network=host \
    --env-file /tmp/celery.env \
    ${{IMAGE}} \
    celery -A config worker -B --loglevel=info --concurrency=2 --schedule=/tmp/celerybeat-schedule

echo "Waiting 20s for new worker to stabilize..."
sleep 20

# Gracefully stop old worker if exists
if docker ps --format '{{{{.Names}}}}' | grep -q '^celery-worker$'; then
    echo "Stopping old worker (600s drain timeout)..."
    docker stop --time=600 celery-worker || true
    docker rm celery-worker || true
fi

# Rename new to active
docker rename celery-worker-new celery-worker

# Cleanup
rm -f /tmp/celery.env
docker image prune -f

echo "Celery deployment complete."
```

- [ ] **Step 2: Create steps/celery_vm.py**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add deploy/steps/celery_vm.py deploy/templates/celery-vm-startup.sh.tpl
git commit -m "feat(deploy): step 11 — GCE Celery VM with rolling deploy"
```

---

## Task 17: Step 12 — DNS

**Files:**
- Create: `deploy/steps/dns.py`

- [ ] **Step 1: Create steps/dns.py**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add deploy/steps/dns.py
git commit -m "feat(deploy): step 12 — domain mapping + manual DNS"
```

---

## Task 18: Wire everything into deploy.py

**Files:**
- Modify: `deploy/deploy.py`

- [ ] **Step 1: Update deploy.py with full orchestration**

Replace the full contents of `deploy/deploy.py` with:

```python
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
```

- [ ] **Step 2: Verify import chain**

Run: `python -c "from deploy.config import TenantConfig; from deploy.providers.gcloud import GCloudProvider; from deploy.state import load_state; from deploy.steps import get_steps; print('All imports OK')"`
Expected: `All imports OK`

- [ ] **Step 3: Commit**

```bash
git add deploy/deploy.py
git commit -m "feat(deploy): wire full orchestration into deploy.py"
```

---

## Task 19: Run a dry walkthrough

- [ ] **Step 1: Verify CLI help**

Run: `python deploy/deploy.py --help`
Expected: Shows help with `--company`, `--provider`, `--region` options.

- [ ] **Step 2: Verify state file not tracked**

Run: `cd /Users/christianpeters/the-agentic-company && echo "test" > deploy/state/test.txt && git status deploy/state/`
Expected: `deploy/state/` should not show as untracked (covered by `.gitignore`).

- [ ] **Step 3: Clean up**

Run: `rm -f deploy/state/test.txt`

- [ ] **Step 4: Final commit with all files**

Run: `git status` — verify all deploy/ files are committed. If any stragglers:

```bash
git add deploy/
git commit -m "feat(deploy): complete deployment automation CLI"
```
