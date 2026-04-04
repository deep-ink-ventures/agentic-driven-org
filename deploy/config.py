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
