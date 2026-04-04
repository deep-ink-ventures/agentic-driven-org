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
