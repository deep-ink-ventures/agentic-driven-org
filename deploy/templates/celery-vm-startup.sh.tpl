#!/bin/bash
# Celery VM startup script for {company}
# Pulls backend image, runs Cloud SQL Auth Proxy, starts celery worker+beat

set -euo pipefail

PROJECT="{project_id}"
REGION="{region}"
REGISTRY="{registry_url}"
SQL_CONNECTION="{sql_connection}"
SECRET_PREFIX="{secret_prefix}"
REDIS_HOST="{redis_host}"

# Authenticate Docker with Artifact Registry
gcloud auth configure-docker ${{REGION}}-docker.pkg.dev --quiet

# Fetch secrets from Secret Manager
DJANGO_SK=$(gcloud secrets versions access latest --secret="${{SECRET_PREFIX}}-django-secret-key" --project=${{PROJECT}})
PG_PASS=$(gcloud secrets versions access latest --secret="${{SECRET_PREFIX}}-postgres-password" --project=${{PROJECT}})
ANTHROPIC_KEY=$(gcloud secrets versions access latest --secret="${{SECRET_PREFIX}}-anthropic-api-key" --project=${{PROJECT}})
GOOGLE_CID=$(gcloud secrets versions access latest --secret="${{SECRET_PREFIX}}-google-client-id" --project=${{PROJECT}})
GOOGLE_CSECRET=$(gcloud secrets versions access latest --secret="${{SECRET_PREFIX}}-google-client-secret" --project=${{PROJECT}})

IMAGE="${{REGISTRY}}/backend:latest"

# Pull latest image
docker pull ${{IMAGE}}

# Start Cloud SQL Auth Proxy (if not running)
if ! docker ps --format '{{{{.Names}}}}' | grep -q cloud-sql-proxy; then
    docker run -d \
        --name cloud-sql-proxy \
        --restart=always \
        --network=host \
        gcr.io/cloud-sql-connectors/cloud-sql-proxy:2 \
        --address 0.0.0.0 \
        --port 5432 \
        ${{SQL_CONNECTION}}
fi

# Build env file
cat > /tmp/celery.env << ENVEOF
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=${{DJANGO_SK}}
ANTHROPIC_API_KEY=${{ANTHROPIC_KEY}}
POSTGRES_DB={sql_database}
POSTGRES_USER={sql_user}
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_PASSWORD=${{PG_PASS}}
REDIS_URL=redis://${{REDIS_HOST}}:6379/0
GOOGLE_CLIENT_ID=${{GOOGLE_CID}}
GOOGLE_CLIENT_SECRET=${{GOOGLE_CSECRET}}
STORAGE_BACKEND=gcs
GCS_BUCKET={bucket_name}
GCP_PROJECT_ID=${{PROJECT}}
FRONTEND_URL=https://{domain}
ONLY_ALLOWLIST_CAN_SIGN_UP=true
ENVEOF

# Rolling restart: start new worker, wait, drain old worker, then restart beat
docker run -d \
    --name celery-worker-new \
    --restart=always \
    --network=host \
    --env-file /tmp/celery.env \
    -e REMAP_SIGTERM=SIGQUIT \
    ${{IMAGE}} \
    celery -A config worker --loglevel=info --concurrency=2 --without-heartbeat

echo "Waiting 20s for new worker to stabilize..."
sleep 20

# Gracefully stop old worker if exists
if docker ps --format '{{{{.Names}}}}' | grep -q '^celery-worker$'; then
    echo "Stopping old worker (600s drain timeout)..."
    docker stop --time=600 celery-worker || true
    docker rm celery-worker || true
fi

# Rename new to active
docker rename celery-worker-new celery-worker

# Restart beat separately
if docker ps --format '{{{{.Names}}}}' | grep -q '^celery-beat$'; then
    docker stop --time=10 celery-beat || true
    docker rm celery-beat || true
fi

docker run -d \
    --name celery-beat \
    --restart=always \
    --network=host \
    --env-file /tmp/celery.env \
    ${{IMAGE}} \
    celery -A config beat --loglevel=info --schedule=/tmp/celerybeat-schedule

# Cleanup
rm -f /tmp/celery.env
docker image prune -f

echo "Celery deployment complete."
