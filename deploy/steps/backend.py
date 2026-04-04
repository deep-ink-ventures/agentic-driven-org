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
