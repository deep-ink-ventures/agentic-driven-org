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
