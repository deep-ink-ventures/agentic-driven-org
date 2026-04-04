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

    @abstractmethod
    def create_service_account(self, project_id: str, name: str, display_name: str) -> dict:
        ...

    @abstractmethod
    def grant_project_role(self, project_id: str, member_email: str, role: str) -> None:
        ...

    @abstractmethod
    def create_sa_key(self, project_id: str, sa_email: str, output_path: str) -> None:
        ...
