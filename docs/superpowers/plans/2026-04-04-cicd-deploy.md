# CI/CD Multi-Client Deployment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitHub Actions workflow that builds Docker images on push to main and deploys to all clients in parallel via matrix strategy.

**Architecture:** Single workflow reads `deploy/tenants.json` for client list. Backend image built once; frontend built per client (needs per-client `NEXT_PUBLIC_API_URL`). Each client deploys to its own GCP project using a per-client service account key stored as a GitHub secret.

**Tech Stack:** GitHub Actions, Docker, gcloud CLI, bash

**Spec:** `docs/superpowers/specs/2026-04-04-cicd-deploy-design.md`

---

## File Structure

```
backend/Dockerfile                    # Backend Docker image
frontend/Dockerfile                   # Frontend Docker image (accepts build args)
deploy/tenants.json                   # Client list + region config
deploy/scripts/deploy-celery-vm.sh    # Celery VM rolling deploy (standalone bash)
deploy/steps/service_account.py       # New provisioning step: create deploy SA + key
deploy/steps/__init__.py              # Modified: add ServiceAccountStep to registry
.github/workflows/deploy.yml         # The CI/CD workflow
```

---

### Task 1: Backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: Create backend/Dockerfile**

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
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
```

- [ ] **Step 2: Verify Docker build**

Run:
```bash
cd /Users/christianpeters/the-agentic-company
docker build -t agentdriven-backend:test backend/
```
Expected: Build succeeds (may warn about missing DB for collectstatic — that's fine, it uses the placeholder key).

- [ ] **Step 3: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat(deploy): backend Dockerfile"
```

---

### Task 2: Frontend Dockerfile

**Files:**
- Create: `frontend/Dockerfile`

- [ ] **Step 1: Create frontend/Dockerfile**

The frontend needs `NEXT_PUBLIC_API_URL` at build time. This is passed as a Docker build arg.

```dockerfile
FROM node:22-alpine AS builder

ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_PROJECT_NAME=Frontier

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_PROJECT_NAME=${NEXT_PUBLIC_PROJECT_NAME}

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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/Dockerfile
git commit -m "feat(deploy): frontend Dockerfile with build args"
```

---

### Task 3: tenants.json

**Files:**
- Create: `deploy/tenants.json`

- [ ] **Step 1: Create deploy/tenants.json**

```json
{
  "clients": [],
  "region": "europe-west1"
}
```

Empty client list — clients are added after provisioning.

- [ ] **Step 2: Commit**

```bash
git add deploy/tenants.json
git commit -m "feat(deploy): tenants.json client registry"
```

---

### Task 4: Celery VM deploy script

**Files:**
- Create: `deploy/scripts/deploy-celery-vm.sh`

This is a standalone bash script (not a Python format template). It reads all config from environment variables set by the caller (GitHub Actions or manual invocation).

- [ ] **Step 1: Create deploy/scripts/deploy-celery-vm.sh**

```bash
#!/bin/bash
# Celery VM rolling deploy — called via SSH from GitHub Actions or manually.
# All config via environment variables:
#   CLIENT, PROJECT, REGION, REGISTRY_URL, SQL_CONNECTION,
#   SECRET_PREFIX, REDIS_HOST, SQL_DATABASE, SQL_USER, BUCKET_NAME, DOMAIN

set -euo pipefail

echo "=== Celery deploy for ${CLIENT} ==="

# Authenticate Docker with Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Fetch secrets from Secret Manager
DJANGO_SK=$(gcloud secrets versions access latest --secret="${SECRET_PREFIX}-django-secret-key" --project=${PROJECT})
PG_PASS=$(gcloud secrets versions access latest --secret="${SECRET_PREFIX}-postgres-password" --project=${PROJECT})
ANTHROPIC_KEY=$(gcloud secrets versions access latest --secret="${SECRET_PREFIX}-anthropic-api-key" --project=${PROJECT})
GOOGLE_CID=$(gcloud secrets versions access latest --secret="${SECRET_PREFIX}-google-client-id" --project=${PROJECT})
GOOGLE_CSECRET=$(gcloud secrets versions access latest --secret="${SECRET_PREFIX}-google-client-secret" --project=${PROJECT})

IMAGE="${REGISTRY_URL}/backend:latest"

# Pull latest image
echo "Pulling ${IMAGE}..."
docker pull ${IMAGE}

# Start Cloud SQL Auth Proxy (if not running)
if ! docker ps --format '{{.Names}}' | grep -q cloud-sql-proxy; then
    echo "Starting Cloud SQL Auth Proxy..."
    docker run -d \
        --name cloud-sql-proxy \
        --restart=always \
        --network=host \
        gcr.io/cloud-sql-connectors/cloud-sql-proxy:2 \
        --address 0.0.0.0 \
        --port 5432 \
        ${SQL_CONNECTION}
fi

# Build env file
cat > /tmp/celery.env << ENVEOF
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=${DJANGO_SK}
ANTHROPIC_API_KEY=${ANTHROPIC_KEY}
POSTGRES_DB=${SQL_DATABASE}
POSTGRES_USER=${SQL_USER}
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_PASSWORD=${PG_PASS}
REDIS_URL=redis://${REDIS_HOST}:6379/0
GOOGLE_CLIENT_ID=${GOOGLE_CID}
GOOGLE_CLIENT_SECRET=${GOOGLE_CSECRET}
STORAGE_BACKEND=gcs
GCS_BUCKET=${BUCKET_NAME}
GCP_PROJECT_ID=${PROJECT}
FRONTEND_URL=https://${DOMAIN}
ONLY_ALLOWLIST_CAN_SIGN_UP=true
ENVEOF

# Rolling restart: start new, wait, stop old
echo "Starting new celery worker..."
docker run -d \
    --name celery-worker-new \
    --restart=always \
    --network=host \
    --env-file /tmp/celery.env \
    ${IMAGE} \
    celery -A config worker -B --loglevel=info --concurrency=2 --schedule=/tmp/celerybeat-schedule

echo "Waiting 20s for new worker to stabilize..."
sleep 20

# Gracefully stop old worker if exists
if docker ps --format '{{.Names}}' | grep -q '^celery-worker$'; then
    echo "Stopping old worker (600s drain timeout)..."
    docker stop --time=600 celery-worker || true
    docker rm celery-worker || true
fi

# Rename new to active
docker rename celery-worker-new celery-worker

# Cleanup
rm -f /tmp/celery.env
docker image prune -f

echo "=== Celery deploy complete for ${CLIENT} ==="
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x /Users/christianpeters/the-agentic-company/deploy/scripts/deploy-celery-vm.sh`

- [ ] **Step 3: Commit**

```bash
git add deploy/scripts/deploy-celery-vm.sh
git commit -m "feat(deploy): celery VM rolling deploy script"
```

---

### Task 5: Deploy service account provisioning step

**Files:**
- Create: `deploy/steps/service_account.py`
- Modify: `deploy/steps/__init__.py`

- [ ] **Step 1: Create deploy/steps/service_account.py**

```python
"""Step 13: Create deploy service account for CI/CD."""

import click
from rich.console import Console
from rich.panel import Panel

from deploy.steps.base import BaseStep

console = Console()

DEPLOY_SA_ROLES = [
    "roles/run.admin",
    "roles/artifactregistry.writer",
    "roles/compute.instanceAdmin.v1",
    "roles/secretmanager.secretAccessor",
    "roles/iam.serviceAccountUser",
]


class ServiceAccountStep(BaseStep):
    name = "service_account"
    description = "Create deploy service account for CI/CD"

    def run(self) -> dict:
        project_id = self.config.project_id
        company = self.config.company
        sa_name = f"{company}-deploy"
        sa_email = f"{sa_name}@{project_id}.iam.gserviceaccount.com"

        # Create service account
        self.provider.create_service_account(project_id, sa_name, f"Deploy SA for {company}")

        # Grant roles
        for role in DEPLOY_SA_ROLES:
            self.provider.grant_project_role(project_id, sa_email, role)

        # Create key
        key_path = f"/tmp/{company}-deploy-key.json"
        self.provider.create_sa_key(project_id, sa_email, key_path)

        # Display instructions
        gh_secret_name = f"GCP_SA_KEY_{company.upper()}"
        console.print(Panel(
            f"[bold]Add this service account key to GitHub repo secrets:[/bold]\n\n"
            f"  Secret name: [bold]{gh_secret_name}[/bold]\n"
            f"  Key file: [bold]{key_path}[/bold]\n\n"
            f"  Run: [dim]cat {key_path} | pbcopy[/dim]\n"
            f"  Then paste as the secret value in GitHub → Settings → Secrets\n\n"
            f"[yellow]Delete the key file after adding it to GitHub.[/yellow]",
            title="GitHub Actions Setup",
            border_style="yellow",
        ))

        click.pause("Press Enter after you've added the secret to GitHub...")

        return {
            "deploy_sa_email": sa_email,
            "gh_secret_name": gh_secret_name,
        }
```

- [ ] **Step 2: Add provider methods**

Add these three methods to `deploy/providers/base.py` (append before the closing of the class):

```python
    @abstractmethod
    def create_service_account(self, project_id: str, name: str, display_name: str) -> dict:
        ...

    @abstractmethod
    def grant_project_role(self, project_id: str, member_email: str, role: str) -> None:
        ...

    @abstractmethod
    def create_sa_key(self, project_id: str, sa_email: str, output_path: str) -> None:
        ...
```

Add these implementations to `deploy/providers/gcloud.py` (append before the closing of the class):

```python
    def create_service_account(self, project_id: str, name: str, display_name: str) -> dict:
        self._run([
            "iam", "service-accounts", "create", name,
            f"--display-name={display_name}",
        ] + self._project_flag(project_id), check=False)
        return {"service_account": f"{name}@{project_id}.iam.gserviceaccount.com"}

    def grant_project_role(self, project_id: str, member_email: str, role: str) -> None:
        subprocess.run(
            ["gcloud", "projects", "add-iam-policy-binding", project_id,
             f"--member=serviceAccount:{member_email}",
             f"--role={role}",
             "--condition=None",
             "--quiet"],
            check=True, text=True, capture_output=True,
        )

    def create_sa_key(self, project_id: str, sa_email: str, output_path: str) -> None:
        subprocess.run(
            ["gcloud", "iam", "service-accounts", "keys", "create", output_path,
             f"--iam-account={sa_email}",
             f"--project={project_id}"],
            check=True, text=True, capture_output=True,
        )
```

- [ ] **Step 3: Add ServiceAccountStep to the step registry**

In `deploy/steps/__init__.py`, add the import and class to the list. The full file should be:

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
    from .service_account import ServiceAccountStep

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
        ServiceAccountStep,
    ]
    return [cls(config, provider, state) for cls in step_classes]
```

- [ ] **Step 4: Verify imports**

Run:
```bash
cd /Users/christianpeters/the-agentic-company
python -c "from deploy.steps.service_account import ServiceAccountStep; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add deploy/steps/service_account.py deploy/steps/__init__.py deploy/providers/base.py deploy/providers/gcloud.py
git commit -m "feat(deploy): service account provisioning step for CI/CD"
```

---

### Task 6: GitHub Actions deploy workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: Create .github/workflows/deploy.yml**

```yaml
name: Deploy to clients

on:
  push:
    branches: [main]
    paths-ignore:
      - 'docs/**'
      - 'deploy/**'
      - 'landing-page/**'
      - '*.md'
  workflow_dispatch:
    inputs:
      client:
        description: 'Deploy to a specific client (leave empty for all)'
        required: false
        default: ''

jobs:
  # Read client list and set up matrix
  prepare:
    runs-on: ubuntu-latest
    outputs:
      clients: ${{ steps.set-matrix.outputs.clients }}
      region: ${{ steps.set-matrix.outputs.region }}
    steps:
      - uses: actions/checkout@v4

      - id: set-matrix
        run: |
          if [ -n "${{ github.event.inputs.client }}" ]; then
            echo "clients=[\"${{ github.event.inputs.client }}\"]" >> $GITHUB_OUTPUT
          else
            echo "clients=$(jq -c '.clients' deploy/tenants.json)" >> $GITHUB_OUTPUT
          fi
          echo "region=$(jq -r '.region' deploy/tenants.json)" >> $GITHUB_OUTPUT

  # Build backend image once
  build-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build backend image
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          file: ./backend/Dockerfile
          tags: agentdriven-backend:${{ github.sha }}
          outputs: type=docker,dest=/tmp/backend.tar

      - name: Upload backend image
        uses: actions/upload-artifact@v4
        with:
          name: backend-image
          path: /tmp/backend.tar
          retention-days: 1

  # Deploy to each client in parallel
  deploy:
    needs: [prepare, build-backend]
    if: ${{ fromJson(needs.prepare.outputs.clients)[0] != null }}
    runs-on: ubuntu-latest
    strategy:
      matrix:
        client: ${{ fromJson(needs.prepare.outputs.clients) }}
      fail-fast: false
    env:
      REGION: ${{ needs.prepare.outputs.region }}
      CLIENT: ${{ matrix.client }}
    steps:
      - uses: actions/checkout@v4

      - name: Derive resource names
        id: names
        run: |
          CLIENT="${{ matrix.client }}"
          CLIENT_UPPER=$(echo "${CLIENT}" | tr '[:lower:]' '[:upper:]')
          echo "project=${CLIENT}-agentdriven" >> $GITHUB_OUTPUT
          echo "client_upper=${CLIENT_UPPER}" >> $GITHUB_OUTPUT
          echo "registry=${REGION}-docker.pkg.dev/${CLIENT}-agentdriven/${CLIENT}-agentdriven" >> $GITHUB_OUTPUT
          echo "backend_service=${CLIENT}-backend" >> $GITHUB_OUTPUT
          echo "frontend_service=${CLIENT}-frontend" >> $GITHUB_OUTPUT
          echo "celery_vm=${CLIENT}-celery-vm" >> $GITHUB_OUTPUT
          echo "domain=${CLIENT}.as.agentdriven.org" >> $GITHUB_OUTPUT
          echo "secret_prefix=${CLIENT}-agentdriven" >> $GITHUB_OUTPUT
          echo "vpc_connector=${CLIENT}-vpc-connector" >> $GITHUB_OUTPUT
          echo "sql_connection=${CLIENT}-agentdriven:${REGION}:${CLIENT}-agentdriven-db" >> $GITHUB_OUTPUT
          echo "bucket=${CLIENT}-agentdriven-storage" >> $GITHUB_OUTPUT
          echo "zone=${REGION}-b" >> $GITHUB_OUTPUT

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets[format('GCP_SA_KEY_{0}', steps.names.outputs.client_upper)] }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

      - name: Download backend image
        uses: actions/download-artifact@v4
        with:
          name: backend-image
          path: /tmp

      - name: Load and push backend image
        run: |
          docker load -i /tmp/backend.tar
          docker tag agentdriven-backend:${{ github.sha }} ${{ steps.names.outputs.registry }}/backend:${{ github.sha }}
          docker tag agentdriven-backend:${{ github.sha }} ${{ steps.names.outputs.registry }}/backend:latest
          docker push ${{ steps.names.outputs.registry }}/backend:${{ github.sha }}
          docker push ${{ steps.names.outputs.registry }}/backend:latest

      - name: Build and push frontend image
        run: |
          docker build \
            --build-arg NEXT_PUBLIC_API_URL=https://${{ steps.names.outputs.domain }} \
            --build-arg NEXT_PUBLIC_PROJECT_NAME=Frontier \
            -t ${{ steps.names.outputs.registry }}/frontend:${{ github.sha }} \
            -t ${{ steps.names.outputs.registry }}/frontend:latest \
            frontend/
          docker push ${{ steps.names.outputs.registry }}/frontend:${{ github.sha }}
          docker push ${{ steps.names.outputs.registry }}/frontend:latest

      - name: Fetch secrets for Cloud Run env vars
        id: secrets
        run: |
          PREFIX="${{ steps.names.outputs.secret_prefix }}"
          PROJECT="${{ steps.names.outputs.project }}"
          echo "django_sk=$(gcloud secrets versions access latest --secret=${PREFIX}-django-secret-key --project=${PROJECT})" >> $GITHUB_OUTPUT
          echo "pg_pass=$(gcloud secrets versions access latest --secret=${PREFIX}-postgres-password --project=${PROJECT})" >> $GITHUB_OUTPUT
          echo "anthropic_key=$(gcloud secrets versions access latest --secret=${PREFIX}-anthropic-api-key --project=${PROJECT})" >> $GITHUB_OUTPUT
          echo "google_cid=$(gcloud secrets versions access latest --secret=${PREFIX}-google-client-id --project=${PROJECT})" >> $GITHUB_OUTPUT
          echo "google_csecret=$(gcloud secrets versions access latest --secret=${PREFIX}-google-client-secret --project=${PROJECT})" >> $GITHUB_OUTPUT
          echo "redis_host=$(gcloud redis instances describe ${CLIENT}-agentdriven-redis --region=${REGION} --project=${PROJECT} --format='value(host)')" >> $GITHUB_OUTPUT

      - name: Deploy backend to Cloud Run
        run: |
          gcloud run deploy ${{ steps.names.outputs.backend_service }} \
            --image=${{ steps.names.outputs.registry }}/backend:${{ github.sha }} \
            --region=${REGION} \
            --project=${{ steps.names.outputs.project }} \
            --vpc-connector=${{ steps.names.outputs.vpc_connector }} \
            --add-cloudsql-instances=${{ steps.names.outputs.sql_connection }} \
            --allow-unauthenticated \
            --memory=1Gi \
            --cpu=2 \
            --min-instances=0 \
            --max-instances=3 \
            --port=8000 \
            --set-env-vars="\
          DJANGO_SETTINGS_MODULE=config.settings,\
          DJANGO_DEBUG=false,\
          DJANGO_ALLOWED_HOSTS=${{ steps.names.outputs.domain }},\
          DJANGO_SECRET_KEY=${{ steps.secrets.outputs.django_sk }},\
          POSTGRES_DB=agentdriven,\
          POSTGRES_USER=agentdriven,\
          POSTGRES_PASSWORD=${{ steps.secrets.outputs.pg_pass }},\
          POSTGRES_HOST=/cloudsql/${{ steps.names.outputs.sql_connection }},\
          POSTGRES_PORT=5432,\
          REDIS_URL=redis://${{ steps.secrets.outputs.redis_host }}:6379/0,\
          GOOGLE_CLIENT_ID=${{ steps.secrets.outputs.google_cid }},\
          GOOGLE_CLIENT_SECRET=${{ steps.secrets.outputs.google_csecret }},\
          ANTHROPIC_API_KEY=${{ steps.secrets.outputs.anthropic_key }},\
          STORAGE_BACKEND=gcs,\
          GCS_BUCKET=${{ steps.names.outputs.bucket }},\
          GCP_PROJECT_ID=${{ steps.names.outputs.project }},\
          FRONTEND_URL=https://${{ steps.names.outputs.domain }},\
          CORS_ALLOWED_ORIGINS=https://${{ steps.names.outputs.domain }},\
          CSRF_TRUSTED_ORIGINS=https://${{ steps.names.outputs.domain }},\
          ONLY_ALLOWLIST_CAN_SIGN_UP=true"

      - name: Deploy frontend to Cloud Run
        run: |
          gcloud run deploy ${{ steps.names.outputs.frontend_service }} \
            --image=${{ steps.names.outputs.registry }}/frontend:${{ github.sha }} \
            --region=${REGION} \
            --project=${{ steps.names.outputs.project }} \
            --vpc-connector=${{ steps.names.outputs.vpc_connector }} \
            --allow-unauthenticated \
            --memory=512Mi \
            --cpu=1 \
            --min-instances=0 \
            --max-instances=3 \
            --port=3000

      - name: Deploy Celery VM
        run: |
          gcloud compute ssh ${{ steps.names.outputs.celery_vm }} \
            --zone=${{ steps.names.outputs.zone }} \
            --project=${{ steps.names.outputs.project }} \
            --command="
              export CLIENT=${{ matrix.client }}
              export PROJECT=${{ steps.names.outputs.project }}
              export REGION=${REGION}
              export REGISTRY_URL=${{ steps.names.outputs.registry }}
              export SQL_CONNECTION=${{ steps.names.outputs.sql_connection }}
              export SECRET_PREFIX=${{ steps.names.outputs.secret_prefix }}
              export REDIS_HOST=${{ steps.secrets.outputs.redis_host }}
              export SQL_DATABASE=agentdriven
              export SQL_USER=agentdriven
              export BUCKET_NAME=${{ steps.names.outputs.bucket }}
              export DOMAIN=${{ steps.names.outputs.domain }}
              bash -s
            " < deploy/scripts/deploy-celery-vm.sh
```

- [ ] **Step 2: Verify YAML syntax**

Run:
```bash
cd /Users/christianpeters/the-agentic-company
python -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml')); print('Valid YAML')"
```

If `yaml` isn't installed: `pip install pyyaml` first.

Expected: `Valid YAML`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "feat(deploy): GitHub Actions multi-client deploy workflow"
```

---

### Task 7: Verify full integration

- [ ] **Step 1: Verify all deploy files exist**

Run:
```bash
cd /Users/christianpeters/the-agentic-company
ls -la backend/Dockerfile frontend/Dockerfile deploy/tenants.json deploy/scripts/deploy-celery-vm.sh deploy/steps/service_account.py .github/workflows/deploy.yml
```
Expected: All 6 files listed.

- [ ] **Step 2: Verify deploy.py still loads all steps including new ServiceAccountStep**

Run:
```bash
cd /Users/christianpeters/the-agentic-company
python -c "
from deploy.config import TenantConfig
from deploy.providers.gcloud import GCloudProvider
from deploy.state import load_state
from deploy.steps import get_steps
config = TenantConfig('test', 'europe-west1')
provider = GCloudProvider('europe-west1')
state = load_state('test')
steps = get_steps(config, provider, state)
print(f'{len(steps)} steps:')
for s in steps:
    print(f'  {s.name}')
"
```
Expected: 13 steps listed, ending with `service_account`.

- [ ] **Step 3: Verify workflow references match config.py naming**

Manually check that the naming in the workflow's `Derive resource names` step matches `deploy/config.py`:
- `project=${CLIENT}-agentdriven` matches `TenantConfig.project_id`
- `backend_service=${CLIENT}-backend` matches `TenantConfig.backend_service_name`
- `frontend_service=${CLIENT}-frontend` matches `TenantConfig.frontend_service_name`
- `celery_vm=${CLIENT}-celery-vm` matches `TenantConfig.celery_vm_name`
- `domain=${CLIENT}.as.agentdriven.org` matches `TenantConfig.domain`
- `secret_prefix=${CLIENT}-agentdriven` matches `TenantConfig.secret_prefix`
- `vpc_connector=${CLIENT}-vpc-connector` matches `TenantConfig.vpc_connector_name`
- `bucket=${CLIENT}-agentdriven-storage` matches `TenantConfig.bucket_name`

All match.

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix(deploy): integration fixes" || echo "Nothing to fix"
```
