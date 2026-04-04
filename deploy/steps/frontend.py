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
