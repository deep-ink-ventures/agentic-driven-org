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
