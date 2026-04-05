# Deployment Automation — Design Spec

**Date:** 2026-04-04
**Status:** Approved

## Overview

An interactive Python CLI script that provisions a complete isolated tenant stack on Google Cloud. Given a company name and authenticated `gcloud` CLI, it walks the operator through every step — creating infrastructure, configuring secrets, deploying services, and wiring DNS — with interactive pauses for manual steps.

Each tenant gets its own GCP project, isolated resources, and a subdomain at `{name}.as.agentdriven.org`.

## Architecture

### Stack per tenant

| Resource | Service | Spec |
|---|---|---|
| Backend (Django ASGI) | Cloud Run | 1 vCPU, 512MB, scales to zero |
| Frontend (Next.js) | Cloud Run | 1 vCPU, 512MB, scales to zero |
| Celery worker + beat | GCE VM (e2-small) | Runs both worker and beat via `-B` flag |
| PostgreSQL 16 | Cloud SQL | db-f1-micro, 10GB SSD, private IP |
| Redis 7 | Memorystore | Basic, 1GB (M1), on VPC |
| Object storage | GCS | Standard bucket |
| Secrets | Secret Manager | All secrets stored here, never locally |
| Docker images | Artifact Registry | One repo per tenant |
| Domain | Cloud Run domain mapping | `{name}.as.agentdriven.org`, auto SSL |

Region: `europe-west1` (configurable).

Estimated cost per tenant: ~$60–85/mo at low traffic.

### Why Celery on a VM

Cloud Run cannot reliably run Celery workers or beat — instance recycling kills subprocesses and CPU throttling causes missed heartbeats. This was debugged extensively in ScriptPulse. The solution: dedicated GCE VM running both worker and beat in a single container, with Cloud SQL Auth Proxy as a sidecar.

### Secrets management

All secrets go into GCP Secret Manager. The state file and repo never contain secret values. Secrets are referenced by name only. The script generates what it can (Django secret key, DB password) and prompts the operator for external ones (ANTHROPIC_API_KEY, etc.).

## Folder structure

```
deploy/
├── deploy.py              # Entry point — interactive CLI
├── config.py              # Shared config, naming conventions
├── state/                 # Per-tenant state files (gitignored)
│   └── {company}.json
├── providers/
│   ├── base.py            # Abstract provider interface
│   └── gcloud.py          # GCloud implementation
├── steps/                 # Each provisioning step as a module
│   ├── project.py         # Create GCP project, enable APIs
│   ├── networking.py      # VPC, subnet, serverless connector, firewall
│   ├── database.py        # Cloud SQL (Postgres 16)
│   ├── redis.py           # Memorystore (Redis 7)
│   ├── storage.py         # GCS bucket
│   ├── secrets.py         # Secret Manager entries
│   ├── oauth.py           # OAuth consent screen + client
│   ├── registry.py        # Artifact Registry, build + push images
│   ├── backend.py         # Cloud Run — Django backend
│   ├── frontend.py        # Cloud Run — Next.js frontend
│   ├── celery.py          # GCE VM — Celery worker + beat
│   └── dns.py             # Domain mapping + manual DNS instructions
├── templates/             # Config file templates
│   └── celery-vm-startup.sh.tpl
└── requirements.txt       # click, rich
```

## Naming conventions

Given `--company acme`:

| Resource | Name |
|---|---|
| GCP Project | `acme-agentdriven` |
| Cloud SQL instance | `acme-agentdriven-db` |
| Cloud SQL database | `agentdriven` |
| Memorystore Redis | `acme-agentdriven-redis` |
| GCS bucket | `acme-agentdriven-storage` |
| Cloud Run backend | `acme-backend` |
| Cloud Run frontend | `acme-frontend` |
| GCE VM | `acme-celery-vm` |
| VPC | `acme-agentdriven-vpc` |
| Serverless VPC connector | `acme-vpc-connector` |
| Domain | `acme.as.agentdriven.org` |
| Secret prefix | `acme-agentdriven-*` |
| Artifact Registry repo | `acme-agentdriven` |

## Provisioning flow

### Phase 1: Foundation

1. **Project** — Create GCP project, link billing account, enable APIs (Cloud Run, Cloud SQL, Compute Engine, Memorystore, Secret Manager, Artifact Registry, IAM, Serverless VPC Access)
2. **Networking** — Create VPC, subnet in `europe-west1`, Serverless VPC Connector (for Cloud Run → Cloud SQL/Memorystore), firewall rules (allow internal, allow SSH to Celery VM)
3. **Database** — Provision Cloud SQL Postgres 16, private IP on VPC, create database `agentdriven` + service user, store password in Secret Manager
4. **Redis** — Provision Memorystore Redis 7 on VPC, 1GB basic tier
5. **Storage** — Create GCS bucket, configure CORS if needed

### Phase 2: Application

6. **Secrets** — Generate Django secret key; prompt operator for: `ANTHROPIC_API_KEY`, any other external API keys. Store all in Secret Manager.
7. **OAuth** — Create OAuth consent screen (external), create OAuth client credentials, store in Secret Manager. **Pause with instructions if Google verification review is needed.**
8. **Artifact Registry** — Create Docker repo, build and push backend + frontend images
9. **Backend** — Deploy to Cloud Run, wire environment variables from Secret Manager, connect to VPC via connector, configure Cloud SQL connection
10. **Frontend** — Deploy to Cloud Run, set `NEXT_PUBLIC_API_URL` to backend URL
11. **Celery VM** — Create GCE e2-small instance with startup script that: pulls backend image, starts Cloud SQL Auth Proxy sidecar, runs celery worker+beat (`-B`), configures late acking + prefetch=1. Redeployments use rolling restart (start new container → wait for stabilization → SIGTERM old container with drain timeout for in-flight tasks).

### Phase 3: Routing

12. **DNS** — Create Cloud Run domain mapping for `{name}.as.agentdriven.org`. **Pause with instructions:**
    > Add this DNS record at your domain provider (Gandi) for `agentdriven.org`:
    > ```
    > acme.as.agentdriven.org  CNAME  ghs.googlehosted.com.
    > ```
    > Press Enter when done.

    Then poll until SSL certificate is provisioned.

### Interactive pauses

- Step 6: "Enter your ANTHROPIC_API_KEY:"
- Step 7: "OAuth app needs verification. Go to [console URL] and submit for review. Press Enter when done."
- Step 12: "Add DNS record at Gandi (instructions above). Press Enter when done."

## State management

Each tenant gets a JSON state file at `deploy/state/{company}.json` (gitignored). Tracks:

- Which steps have completed
- Resource IDs/names created
- Timestamps

The script reads state on startup and skips completed steps. This makes it safe to re-run after interruption. No secrets are stored in state — only resource identifiers.

## Provider abstraction

```python
class CloudProvider(ABC):
    def create_project(self, name, billing_account) -> dict
    def enable_apis(self, project, apis) -> None
    def create_vpc(self, project, name, region) -> dict
    def create_database(self, project, name, region, vpc) -> dict
    def create_redis(self, project, name, region, vpc) -> dict
    def create_bucket(self, project, name, region) -> dict
    def set_secret(self, project, name, value) -> None
    def get_secret(self, project, name) -> str
    def create_oauth_client(self, project, name, redirect_uris) -> dict
    def deploy_container(self, project, name, image, env, vpc) -> dict
    def create_vm(self, project, name, region, startup_script) -> dict
    def create_domain_mapping(self, project, service, domain) -> dict
```

`GCloudProvider` implements this by shelling out to `gcloud` CLI. A future `AWSProvider` would use `aws` CLI with equivalent managed services (RDS, ElastiCache, ECS/EC2, etc.).

The `steps/` modules call the provider interface only — they contain no provider-specific logic. Step logic (ordering, prompts, state tracking) is shared across providers.

## Usage

```bash
cd deploy
pip install -r requirements.txt
python deploy.py --company acme --provider gcloud
```

Prerequisites:
- `gcloud` CLI installed and authenticated with sufficient permissions
- GCP billing account available
- Docker installed (for building images)

## Out of scope (for now)

- Automated DNS via Gandi API
- AWS / Azure providers
- CI/CD pipeline generation
- Monitoring / alerting setup
- Automated teardown / deprovisioning
- Multi-region deployments
