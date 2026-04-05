# CI/CD Multi-Client Deployment — Design Spec

**Date:** 2026-04-04
**Status:** Approved

## Overview

GitHub Actions workflow that deploys the application to all clients on push to `main`. Uses a matrix strategy to deploy to each client in parallel. Each client has its own GCP project (provisioned by `deploy/deploy.py`), its own service account key as a GitHub secret, and its own Cloud Run services + Celery VM.

## How It Fits Together

- **`deploy/deploy.py`** — provisions infrastructure once per client (GCP project, VPC, Cloud SQL, Redis, Cloud Run, Celery VM). Also creates a deploy service account + key for CI/CD.
- **GitHub Actions** — continuous deployment. Builds images once, deploys to all clients in parallel.
- **`deploy/tenants.json`** — explicit list of clients that receive deploys.

## Files

```
.github/workflows/deploy.yml         # Main deploy workflow
deploy/tenants.json                   # Client list + shared config
deploy/scripts/deploy-celery-vm.sh    # Celery VM rolling deploy script
```

Modifications to existing:
- `deploy/steps/` — new step for creating deploy service account + key during provisioning

## Trigger

- **Push to `main`** — deploy to all clients
- **`workflow_dispatch`** — manual trigger with optional `client` input (deploy one client, or all if empty)

## tenants.json

```json
{
  "clients": ["acme"],
  "region": "europe-west1"
}
```

Adding a new client:
1. Run `deploy/deploy.py --company newclient` (provisions infra + creates deploy SA key)
2. Add `GCP_SA_KEY_NEWCLIENT` to GitHub repo secrets
3. Add `"newclient"` to `deploy/tenants.json`
4. Push to `main`

## Workflow Structure

### Job 1: build

Runs once. Builds the backend Docker image tagged with the commit SHA. Saves it as a workflow artifact (via `docker save`) so deploy jobs can load it. The frontend is NOT built here — it needs per-client build args (`NEXT_PUBLIC_API_URL`), so it's built in each deploy job.

Steps:
1. Checkout code
2. Set up Docker Buildx
3. Build `backend:${{ github.sha }}` from `backend/Dockerfile`
4. Save backend image as tar artifact

### Job 2: deploy (matrix)

Runs in parallel for each client. Depends on `build`.

**Matrix source:** Reads `deploy/tenants.json` to get client list.

**GitHub secrets convention:** `GCP_SA_KEY_{CLIENT_UPPER}` — e.g., `GCP_SA_KEY_ACME` for client `acme`. The job derives the secret name by uppercasing the client name.

Steps per client:
1. Checkout code
2. Download backend image artifact from build job
3. Load backend Docker image (`docker load`)
4. Authenticate to GCP using `google-github-actions/auth` with the client's SA key
5. Configure Docker for the client's Artifact Registry
6. Build frontend image with `--build-arg NEXT_PUBLIC_API_URL=https://{client}.as.agentdriven.org`
7. Tag backend + frontend images for the client's registry: `{region}-docker.pkg.dev/{client}-agentdriven/{client}-agentdriven/{image}:{sha}` and `:latest`
8. Push both images to the client's Artifact Registry
9. **Deploy backend to Cloud Run:** `gcloud run deploy {client}-backend` with env vars fetched from the client's Secret Manager, Cloud SQL proxy attached, VPC connector
10. **Deploy frontend to Cloud Run:** `gcloud run deploy {client}-frontend`
11. **Deploy Celery VM:** SSH into `{client}-celery-vm`, run `deploy/scripts/deploy-celery-vm.sh` which performs a rolling restart (pull new image, start new container, wait 20s, drain old container with 600s timeout)

## Naming Conventions

All derived from client name, matching `deploy/config.py`:

| Resource | Pattern |
|---|---|
| GCP Project | `{client}-agentdriven` |
| Artifact Registry | `{region}-docker.pkg.dev/{client}-agentdriven/{client}-agentdriven` |
| Cloud Run backend | `{client}-backend` |
| Cloud Run frontend | `{client}-frontend` |
| Celery VM | `{client}-celery-vm` |
| Secret prefix | `{client}-agentdriven-*` |
| GH Secret | `GCP_SA_KEY_{CLIENT_UPPER}` |
| Deploy SA | `{client}-deploy@{client}-agentdriven.iam.gserviceaccount.com` |

## Deploy Service Account (new provisioning step)

Added to `deploy/deploy.py` as a new step after the Celery VM step. Creates a GCP service account for CI/CD with the minimum required roles:

- `roles/run.admin` — deploy to Cloud Run
- `roles/artifactregistry.writer` — push Docker images
- `roles/compute.instanceAdmin.v1` — SSH into Celery VM
- `roles/secretmanager.secretAccessor` — read secrets for env vars
- `roles/iam.serviceAccountUser` — act as the Cloud Run service agent

Steps:
1. Create service account `{client}-deploy`
2. Grant the 5 roles above on the project
3. Create a JSON key
4. Print instructions: "Add the contents of this key as `GCP_SA_KEY_{CLIENT_UPPER}` in your GitHub repo secrets"
5. Delete the local key file after displaying

## Celery VM Deploy Script

`deploy/scripts/deploy-celery-vm.sh` — standalone bash script called by GitHub Actions via SSH. Parameterized by env vars set before invocation:

```
CLIENT, PROJECT, REGION, REGISTRY_URL, SQL_CONNECTION, SECRET_PREFIX, REDIS_HOST
```

Pattern (same as ScriptPulse):
1. Authenticate Docker with Artifact Registry
2. Pull latest backend image
3. Fetch secrets from Secret Manager
4. Build env file
5. Start new celery-worker container (`celery -A config worker -B --concurrency=2`)
6. Wait 20s for stabilization
7. Gracefully stop old container (600s drain timeout)
8. Rename new → active
9. Clean up env file + old images

## Cloud Run Backend Env Vars

Set during deploy, fetched from the client's Secret Manager:

```
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS={client}.as.agentdriven.org
DJANGO_SECRET_KEY=<from secret manager>
POSTGRES_DB=agentdriven
POSTGRES_USER=agentdriven
POSTGRES_PASSWORD=<from secret manager>
POSTGRES_HOST=/cloudsql/{connection_name}
POSTGRES_PORT=5432
REDIS_URL=redis://{redis_host}:6379/0
GOOGLE_CLIENT_ID=<from secret manager>
GOOGLE_CLIENT_SECRET=<from secret manager>
ANTHROPIC_API_KEY=<from secret manager>
STORAGE_BACKEND=gcs
GCS_BUCKET={client}-agentdriven-storage
GCP_PROJECT_ID={client}-agentdriven
FRONTEND_URL=https://{client}.as.agentdriven.org
CORS_ALLOWED_ORIGINS=https://{client}.as.agentdriven.org
CSRF_TRUSTED_ORIGINS=https://{client}.as.agentdriven.org
ONLY_ALLOWLIST_CAN_SIGN_UP=true
```

## Cloud Run Frontend Env Vars

```
NEXT_PUBLIC_API_URL=https://{client}.as.agentdriven.org
NEXT_PUBLIC_PROJECT_NAME=Frontier
```

Note: `NEXT_PUBLIC_*` vars are baked at build time in Next.js. The frontend is rebuilt per client in the deploy matrix with `--build-arg NEXT_PUBLIC_API_URL=https://{client}.as.agentdriven.org` passed to `docker build`. This means the build job only builds the backend image; the frontend is built per client in the deploy job.

## Out of Scope

- Rollback automation (manual via `gcloud run deploy --image=previous-tag`)
- Canary/blue-green deployments
- Slack/email notifications on deploy
- Per-client feature flags
- Landing page deployment (separate, not per-client)
