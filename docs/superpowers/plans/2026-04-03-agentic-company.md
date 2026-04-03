# The Agentic Company Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Django platform where AI agents organized into departments propose, get approval for, and execute tasks autonomously via Claude API and Playwright.

**Architecture:** Django 5.x backend with 4 apps (accounts, projects, agents, integrations). Celery Beat drives two periodic loops: hourly task execution and per-minute approval queue refill. Claude API powers agent reasoning; Playwright handles browser automation for specific agent types. Django Admin is the initial UI.

**Tech Stack:** Django 5.x, DRF, Celery/Beat, Redis, Postgres, Daphne, Django Channels, allauth, Anthropic SDK, Playwright, pytest

**Reference architecture:** `../scriptpulse` — reuse patterns for settings, celery, asgi, auth, docker-compose.

---

## File Structure

```
the-agentic-company/
├── backend/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── celery.py
│   │   ├── asgi.py
│   │   ├── wsgi.py
│   │   ├── urls.py
│   │   └── ws_auth.py
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── allow_list.py
│   │   ├── admin/
│   │   │   ├── __init__.py
│   │   │   ├── user_admin.py
│   │   │   └── allow_list_admin.py
│   │   ├── adapter.py
│   │   ├── management/
│   │   │   ├── __init__.py
│   │   │   └── commands/
│   │   │       ├── __init__.py
│   │   │       └── configure.py
│   │   └── migrations/
│   │       └── __init__.py
│   ├── projects/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── project.py
│   │   │   ├── department.py
│   │   │   ├── document.py
│   │   │   └── tag.py
│   │   ├── admin/
│   │   │   ├── __init__.py
│   │   │   ├── project_admin.py
│   │   │   ├── department_admin.py
│   │   │   └── document_admin.py
│   │   └── migrations/
│   │       └── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   └── agent_task.py
│   │   ├── admin/
│   │   │   ├── __init__.py
│   │   │   ├── agent_admin.py
│   │   │   └── agent_task_admin.py
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   └── claude_client.py
│   │   ├── blueprints/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── twitter/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agent.py
│   │   │   │   └── skills.py
│   │   │   ├── reddit/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agent.py
│   │   │   │   └── skills.py
│   │   │   └── campaign/
│   │   │       ├── __init__.py
│   │   │       ├── agent.py
│   │   │       └── skills.py
│   │   ├── tasks.py
│   │   └── migrations/
│   │       └── __init__.py
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   └── browser.py
│   ├── conftest.py
│   ├── manage.py
│   ├── requirements.txt
│   └── .env
├── docker-compose.dev.yml
├── docker-compose.yml
├── start-dev.sh
├── .gitignore
└── docs/
```

---

### Task 1: Project Scaffolding & Config

**Files:**
- Create: `backend/manage.py`
- Create: `backend/requirements.txt`
- Create: `backend/.env`
- Create: `backend/config/__init__.py`
- Create: `backend/config/settings.py`
- Create: `backend/config/celery.py`
- Create: `backend/config/asgi.py`
- Create: `backend/config/wsgi.py`
- Create: `backend/config/urls.py`
- Create: `backend/config/ws_auth.py`
- Create: `backend/conftest.py`
- Create: `docker-compose.dev.yml`
- Create: `start-dev.sh`
- Create: `.gitignore`

- [ ] **Step 1: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
*.egg
dist/
build/
.eggs/

# Virtual environment
venv/
.venv/

# Environment
.env
*.env

# Django
*.sqlite3
staticfiles/
media/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Node (for future frontend)
node_modules/

# Playwright
.playwright-mcp/

# Test
.pytest_cache/
htmlcov/
.coverage
```

- [ ] **Step 2: Create requirements.txt**

```
django>=5.1,<5.2
djangorestframework>=3.15,<4.0
django-allauth>=65.0,<66.0
django-cors-headers>=4.6,<5.0
channels>=4.2,<5.0
channels-redis>=4.2,<5.0
daphne>=4.1,<5.0
celery>=5.4,<6.0
redis>=5.2,<6.0
psycopg[binary]>=3.2,<4.0
anthropic>=0.42,<1.0
python-dotenv>=1.0,<2.0
whitenoise
pytest>=8.3,<9.0
pytest-django>=4.9,<5.0
pytest-asyncio>=0.24,<1.0
factory-boy>=3.3,<4.0
channels[daphne]>=4.2,<5.0
```

- [ ] **Step 3: Create venv and install dependencies**

Run:
```bash
cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

- [ ] **Step 4: Create backend/.env**

```
DJANGO_SECRET_KEY=dev-insecure-change-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=agentic_company
POSTGRES_USER=agentic_company
POSTGRES_PASSWORD=agentic_company
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
REDIS_URL=redis://localhost:6380/0
ANTHROPIC_API_KEY=
```

- [ ] **Step 5: Create manage.py**

```python
#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Create config/__init__.py**

```python
from .celery import app as celery_app

__all__ = ["celery_app"]
```

- [ ] **Step 7: Create config/settings.py**

```python
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-change-me")

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third party
    "rest_framework",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "channels",
    # Local
    "accounts",
    "projects",
    "agents",
    "integrations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "agentic_company"),
        "USER": os.environ.get("POSTGRES_USER", "agentic_company"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "agentic_company"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Auth
AUTH_USER_MODEL = "accounts.User"
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

# AllowList gating
ONLY_ALLOWLIST_CAN_SIGN_UP = os.environ.get("ONLY_ALLOWLIST_CAN_SIGN_UP", "true").lower() != "false"

# Google OAuth
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "APP": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        },
    },
}
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
ACCOUNT_ADAPTER = "accounts.adapter.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapter.CustomSocialAccountAdapter"
LOGIN_REDIRECT_URL = os.environ.get("LOGIN_REDIRECT_URL", "http://localhost:3000/dashboard")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# CORS
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
).split(",")
CORS_ALLOW_CREDENTIALS = True

# Session
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:3000"
).split(",")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https" if not DEBUG else "http"

# Cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    },
}

# Channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get("REDIS_URL", "redis://localhost:6379/0")],
        },
    },
}

# Celery
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": 1800,
}
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BEAT_SCHEDULE = {
    "refill-approval-queue": {
        "task": "agents.tasks.refill_approval_queue",
        "schedule": 60,
    },
    "execute-hourly-tasks": {
        "task": "agents.tasks.execute_hourly_tasks",
        "schedule": 3600,
    },
}

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "agents": {"handlers": ["console"], "level": "DEBUG"},
        "projects": {"handlers": ["console"], "level": "DEBUG"},
        "accounts": {"handlers": ["console"], "level": "DEBUG"},
        "integrations": {"handlers": ["console"], "level": "DEBUG"},
        "django.request": {"handlers": ["console"], "level": "WARNING"},
    },
}

# Email — console in dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Timezone
TIME_ZONE = "UTC"
USE_TZ = True

# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Anthropic
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
```

- [ ] **Step 8: Create config/celery.py**

```python
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("agentic_company")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

- [ ] **Step 9: Create config/asgi.py**

```python
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

from config.ws_auth import TicketAuthMiddleware

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": TicketAuthMiddleware(
            AuthMiddlewareStack(URLRouter([]))
        ),
    }
)
```

- [ ] **Step 10: Create config/wsgi.py**

```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
```

- [ ] **Step 11: Create config/urls.py**

```python
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("admin/", admin.site.urls),
]
```

- [ ] **Step 12: Create config/ws_auth.py**

```python
"""WebSocket authentication via one-time tickets.

Browsers don't send httponly session cookies on cross-origin WebSocket connections.
Frontend fetches a short-lived ticket via HTTP, then passes it as ?ticket=xxx on the WS URL.
"""

import uuid
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.core.cache import cache

TICKET_PREFIX = "ws_ticket:"
TICKET_TTL = 30


def create_ws_ticket(user_id) -> str:
    ticket = uuid.uuid4().hex
    cache.set(f"{TICKET_PREFIX}{ticket}", str(user_id), timeout=TICKET_TTL)
    return ticket


@database_sync_to_async
def consume_ticket(ticket: str):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    key = f"{TICKET_PREFIX}{ticket}"
    user_id = cache.get(key)
    if user_id is None:
        return None
    cache.delete(key)
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


class TicketAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        ticket = params.get("ticket", [None])[0]
        if ticket:
            user = await consume_ticket(ticket)
            if user:
                scope["user"] = user
        return await super().__call__(scope, receive, send)
```

- [ ] **Step 13: Create conftest.py**

```python
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def use_in_memory_channel_layer(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }
```

- [ ] **Step 14: Create docker-compose.dev.yml**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: agentic_company
      POSTGRES_USER: agentic_company
      POSTGRES_PASSWORD: agentic_company
    ports:
      - "5433:5432"
    volumes:
      - agentic_company_postgres:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"

volumes:
  agentic_company_postgres:
```

- [ ] **Step 15: Create docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: agentic_company
      POSTGRES_USER: agentic_company
      POSTGRES_PASSWORD: agentic_company
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build:
      context: ./backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
    command: >
      sh -c "python manage.py migrate --noinput &&
             daphne -b 0.0.0.0 -p 8000 config.asgi:application"

  celery:
    build:
      context: ./backend
    env_file:
      - ./backend/.env
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
    command: celery -A config worker --loglevel=info

  celery-beat:
    build:
      context: ./backend
    env_file:
      - ./backend/.env
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
    command: celery -A config beat --loglevel=info

volumes:
  postgres_data:
```

- [ ] **Step 16: Create start-dev.sh**

```bash
#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

G='\033[0;32m'
Y='\033[0;33m'
R='\033[0;31m'
NC='\033[0m'

echo -e "${G}Starting Agentic Company dev environment...${NC}"

# 1. Infra
echo -e "${Y}Starting Docker services (Postgres + Redis)...${NC}"
docker compose -f docker-compose.dev.yml up -d

echo -n "Waiting for Postgres..."
until docker compose -f docker-compose.dev.yml exec -T postgres pg_isready -q 2>/dev/null; do
  echo -n "."
  sleep 1
done
echo -e " ${G}ready${NC}"

# 2. Configure
echo -e "${Y}Running configure...${NC}"
cd backend
./venv/bin/python manage.py configure
cd ..

# 3. Backend
echo -e "${Y}Starting Django backend (port 8000)...${NC}"
cd backend
./venv/bin/python manage.py runserver 8000 &
DJANGO_PID=$!
cd ..

# 4. Celery worker
echo -e "${Y}Starting Celery worker...${NC}"
cd backend
./venv/bin/celery -A config worker --loglevel=info &
CELERY_PID=$!
cd ..

# 5. Celery beat
echo -e "${Y}Starting Celery beat...${NC}"
cd backend
./venv/bin/celery -A config beat --loglevel=info &
BEAT_PID=$!
cd ..

echo ""
echo -e "${G}All services running:${NC}"
echo -e "  Backend:   http://localhost:8000"
echo -e "  Admin:     http://localhost:8000/admin/"
echo -e "  Postgres:  localhost:5433"
echo -e "  Redis:     localhost:6380"
echo ""
echo -e "${Y}Press Ctrl+C to stop all services${NC}"

cleanup() {
  echo ""
  echo -e "${R}Stopping all services...${NC}"
  kill $DJANGO_PID $CELERY_PID $BEAT_PID 2>/dev/null
  docker compose -f docker-compose.dev.yml stop
  echo -e "${G}Done.${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM
wait
```

- [ ] **Step 17: Commit**

```bash
git init
git add .gitignore docker-compose.dev.yml docker-compose.yml start-dev.sh backend/manage.py backend/requirements.txt backend/.env backend/config/ backend/conftest.py
git commit -m "feat: project scaffolding — config, celery, asgi, docker-compose, start-dev"
```

---

### Task 2: Accounts App

**Files:**
- Create: `backend/accounts/__init__.py`
- Create: `backend/accounts/apps.py`
- Create: `backend/accounts/models/__init__.py`
- Create: `backend/accounts/models/user.py`
- Create: `backend/accounts/models/allow_list.py`
- Create: `backend/accounts/admin/__init__.py`
- Create: `backend/accounts/admin/user_admin.py`
- Create: `backend/accounts/admin/allow_list_admin.py`
- Create: `backend/accounts/adapter.py`
- Create: `backend/accounts/management/__init__.py`
- Create: `backend/accounts/management/commands/__init__.py`
- Create: `backend/accounts/management/commands/configure.py`
- Create: `backend/accounts/migrations/__init__.py`

- [ ] **Step 1: Create accounts/__init__.py (empty) and apps.py**

`accounts/__init__.py`: empty file

```python
# accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
```

- [ ] **Step 2: Create accounts/models/user.py**

```python
import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
```

- [ ] **Step 3: Create accounts/models/allow_list.py**

```python
from django.db import models


class AllowList(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "allow list entry"
        verbose_name_plural = "allow list entries"

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
```

- [ ] **Step 4: Create accounts/models/__init__.py**

```python
from .user import User
from .allow_list import AllowList

__all__ = ["User", "AllowList"]
```

- [ ] **Step 5: Create accounts/admin/user_admin.py**

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "is_staff", "is_active", "created_at")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email",)
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2"),
        }),
    )
```

- [ ] **Step 6: Create accounts/admin/allow_list_admin.py**

```python
from django.contrib import admin

from accounts.models import AllowList


@admin.register(AllowList)
class AllowListAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at")
    search_fields = ("email",)
    ordering = ("-created_at",)
```

- [ ] **Step 7: Create accounts/admin/__init__.py**

```python
from .user_admin import UserAdmin
from .allow_list_admin import AllowListAdmin

__all__ = ["UserAdmin", "AllowListAdmin"]
```

- [ ] **Step 8: Create accounts/adapter.py**

```python
from django.conf import settings as django_settings
from django.shortcuts import redirect
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import AllowList, User


class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        frontend_url = django_settings.FRONTEND_URL
        return f"{frontend_url}/dashboard"


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def pre_social_login(self, request, sociallogin):
        super().pre_social_login(request, sociallogin)

        if not sociallogin.is_existing:
            email = sociallogin.user.email
            if email:
                try:
                    existing_user = User.objects.get(email__iexact=email)
                    sociallogin.connect(request, existing_user)
                    sociallogin.user = existing_user
                    return
                except User.DoesNotExist:
                    pass

        if not sociallogin.is_existing and django_settings.ONLY_ALLOWLIST_CAN_SIGN_UP:
            email = sociallogin.user.email
            allowed = AllowList.objects.filter(email__iexact=email).exists()
            if not allowed:
                frontend_url = django_settings.FRONTEND_URL
                raise ImmediateHttpResponse(
                    redirect(f"{frontend_url}/login?error=allowlist")
                )
```

- [ ] **Step 9: Create management command directories and configure.py**

Create empty `__init__.py` files for `accounts/management/` and `accounts/management/commands/`.

```python
# accounts/management/commands/configure.py
"""
One-shot setup: migrate + collectstatic + ensure superuser. Idempotent.

Usage:
  python manage.py configure
  python manage.py configure --skip-superuser
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

SUPERUSER_EMAIL = "admin@agentic.company"
SUPERUSER_PASSWORD = "change-me"


class Command(BaseCommand):
    help = "Run migrate + collectstatic + ensure superuser. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument("--skip-superuser", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Running migrations..."))
        call_command("migrate", "--noinput", stdout=self.stdout)

        self.stdout.write(self.style.MIGRATE_HEADING("Collecting static files..."))
        call_command("collectstatic", "--noinput", stdout=self.stdout)

        if options["skip_superuser"]:
            self.stdout.write("Skipping superuser.")
            return

        from accounts.models import User
        if User.objects.filter(email=SUPERUSER_EMAIL).exists():
            self.stdout.write(f"Superuser {SUPERUSER_EMAIL} already exists — skipping.")
            return

        User.objects.create_superuser(email=SUPERUSER_EMAIL, password=SUPERUSER_PASSWORD)
        self.stdout.write(self.style.SUCCESS(f"Created superuser: {SUPERUSER_EMAIL}"))
```

- [ ] **Step 10: Create accounts/migrations/__init__.py (empty)**

- [ ] **Step 11: Run makemigrations and migrate**

Run:
```bash
cd backend && source venv/bin/activate && python manage.py makemigrations accounts && python manage.py migrate
```

- [ ] **Step 12: Verify admin loads**

Run:
```bash
python manage.py configure && python manage.py runserver 8000
```

Open http://localhost:8000/admin/ — login with admin@agentic.company / change-me. Verify Users and Allow List entries are visible.

- [ ] **Step 13: Commit**

```bash
git add backend/accounts/
git commit -m "feat: accounts app — User, AllowList, Google OAuth adapter, admin"
```

---

### Task 3: Projects App

**Files:**
- Create: `backend/projects/__init__.py`
- Create: `backend/projects/apps.py`
- Create: `backend/projects/models/__init__.py`
- Create: `backend/projects/models/project.py`
- Create: `backend/projects/models/department.py`
- Create: `backend/projects/models/document.py`
- Create: `backend/projects/models/tag.py`
- Create: `backend/projects/admin/__init__.py`
- Create: `backend/projects/admin/project_admin.py`
- Create: `backend/projects/admin/department_admin.py`
- Create: `backend/projects/admin/document_admin.py`
- Create: `backend/projects/migrations/__init__.py`

- [ ] **Step 1: Create projects/__init__.py (empty) and apps.py**

```python
# projects/apps.py
from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projects"
```

- [ ] **Step 2: Create projects/models/project.py**

```python
import uuid

from django.conf import settings
from django.db import models


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    goal = models.TextField(blank=True, help_text="Project goal in markdown")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
```

- [ ] **Step 3: Create projects/models/department.py**

```python
import uuid

from django.db import models


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="departments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("project", "name")]

    def __str__(self):
        return f"{self.project.name} / {self.name}"
```

- [ ] **Step 4: Create projects/models/tag.py**

```python
import uuid

from django.db import models


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
```

- [ ] **Step 5: Create projects/models/document.py**

```python
import uuid

from django.db import models


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, help_text="Document content in markdown")
    department = models.ForeignKey(
        "projects.Department",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    tags = models.ManyToManyField("projects.Tag", blank=True, related_name="documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
```

- [ ] **Step 6: Create projects/models/__init__.py**

```python
from .project import Project
from .department import Department
from .tag import Tag
from .document import Document

__all__ = ["Project", "Department", "Tag", "Document"]
```

- [ ] **Step 7: Create projects/admin/project_admin.py**

```python
from django.contrib import admin

from projects.models import Project, Department


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 1
    fields = ("name",)
    show_change_link = True


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__email")
    ordering = ("-updated_at",)
    inlines = [DepartmentInline]
```

- [ ] **Step 8: Create projects/admin/department_admin.py**

```python
from django.contrib import admin

from projects.models import Department, Document


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 1
    fields = ("title", "tags")
    show_change_link = True


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "created_at")
    list_filter = ("project",)
    search_fields = ("name", "project__name")
    ordering = ("project__name", "name")
    inlines = [DocumentInline]
```

- [ ] **Step 9: Create projects/admin/document_admin.py**

```python
from django.contrib import admin

from projects.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "created_at")
    list_filter = ("department__project", "department", "tags")
    search_fields = ("title", "content")
    ordering = ("-updated_at",)
    filter_horizontal = ("tags",)
```

- [ ] **Step 10: Create projects/admin/__init__.py**

```python
from .project_admin import ProjectAdmin
from .department_admin import DepartmentAdmin
from .document_admin import DocumentAdmin

__all__ = ["ProjectAdmin", "DepartmentAdmin", "DocumentAdmin"]
```

- [ ] **Step 11: Create projects/migrations/__init__.py (empty), run makemigrations and migrate**

Run:
```bash
cd backend && source venv/bin/activate && python manage.py makemigrations projects && python manage.py migrate
```

- [ ] **Step 12: Verify in admin**

Open http://localhost:8000/admin/ — verify Projects, Departments, Documents, Tags are visible. Create a test project with a department.

- [ ] **Step 13: Commit**

```bash
git add backend/projects/
git commit -m "feat: projects app — Project, Department, Document, Tag models and admin"
```

---

### Task 4: Agents App — Models & Admin

**Files:**
- Create: `backend/agents/__init__.py`
- Create: `backend/agents/apps.py`
- Create: `backend/agents/models/__init__.py`
- Create: `backend/agents/models/agent.py`
- Create: `backend/agents/models/agent_task.py`
- Create: `backend/agents/admin/__init__.py`
- Create: `backend/agents/admin/agent_admin.py`
- Create: `backend/agents/admin/agent_task_admin.py`
- Create: `backend/agents/migrations/__init__.py`

- [ ] **Step 1: Create agents/__init__.py (empty) and apps.py**

```python
# agents/apps.py
from django.apps import AppConfig


class AgentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "agents"
```

- [ ] **Step 2: Create agents/models/agent.py**

```python
import uuid

from django.db import models


def get_agent_type_choices():
    from agents.blueprints import AGENT_TYPE_CHOICES
    return AGENT_TYPE_CHOICES


class Agent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Display name, e.g. 'Our Twitter Guy'")
    agent_type = models.CharField(
        max_length=50,
        help_text="Blueprint type — determines the agent's behavior",
    )
    department = models.ForeignKey(
        "projects.Department",
        on_delete=models.CASCADE,
        related_name="agents",
    )
    superior = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinates",
        help_text="Superior agent that can delegate tasks to this agent",
    )
    instructions = models.TextField(
        blank=True,
        help_text="Custom instructions layered on top of the blueprint prompts",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-agent config (browser cookies, API keys, etc.)",
    )
    auto_exec_hourly = models.BooleanField(
        default=False,
        help_text="Whether this agent auto-executes hourly tasks",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department", "name"]

    def get_blueprint(self):
        from agents.blueprints import get_blueprint
        return get_blueprint(self.agent_type)

    def __str__(self):
        return f"{self.name} ({self.agent_type})"
```

- [ ] **Step 3: Create agents/models/agent_task.py**

```python
import uuid

from django.db import models
from django.utils import timezone


class AgentTask(models.Model):
    class Status(models.TextChoices):
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    created_by_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_tasks",
        help_text="Set when a superior agent delegates this task",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AWAITING_APPROVAL,
        db_index=True,
    )
    auto_execute = models.BooleanField(default=False)
    exec_summary = models.TextField(blank=True, help_text="Short description of what to do")
    step_plan = models.TextField(blank=True, help_text="Detailed step-by-step plan")
    report = models.TextField(blank=True, help_text="What was actually done")
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def approve(self):
        """Move task from awaiting_approval to queued and dispatch."""
        if self.status != self.Status.AWAITING_APPROVAL:
            return False
        self.status = self.Status.QUEUED
        self.save(update_fields=["status", "updated_at"])
        from agents.tasks import execute_agent_task
        execute_agent_task.delay(str(self.id))
        return True

    def __str__(self):
        return f"[{self.get_status_display()}] {self.agent.name}: {self.exec_summary[:60]}"
```

- [ ] **Step 4: Create agents/models/__init__.py**

```python
from .agent import Agent
from .agent_task import AgentTask

__all__ = ["Agent", "AgentTask"]
```

- [ ] **Step 5: Create agents/admin/agent_admin.py**

```python
from django.contrib import admin

from agents.models import Agent, AgentTask


class AgentTaskInline(admin.TabularInline):
    model = AgentTask
    fk_name = "agent"
    extra = 0
    fields = ("status", "exec_summary", "auto_execute", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    show_change_link = True
    max_num = 10


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "agent_type", "department", "superior", "auto_exec_hourly", "is_active")
    list_filter = ("agent_type", "is_active", "auto_exec_hourly", "department__project")
    search_fields = ("name", "department__name")
    ordering = ("department", "name")
    fieldsets = (
        (None, {"fields": ("name", "agent_type", "department", "superior")}),
        ("Configuration", {"fields": ("instructions", "config", "auto_exec_hourly", "is_active")}),
    )
    inlines = [AgentTaskInline]
```

- [ ] **Step 6: Create agents/admin/agent_task_admin.py**

```python
from django.contrib import admin
from django.utils import timezone

from agents.models import AgentTask


@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display = ("short_summary", "agent", "status", "auto_execute", "created_by_agent", "created_at")
    list_filter = ("status", "auto_execute", "agent__agent_type", "agent__department__project")
    search_fields = ("exec_summary", "agent__name")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "started_at", "completed_at")
    fieldsets = (
        (None, {"fields": ("id", "agent", "created_by_agent", "status", "auto_execute")}),
        ("Task Details", {"fields": ("exec_summary", "step_plan")}),
        ("Results", {"fields": ("report", "error_message")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "started_at", "completed_at")}),
    )
    actions = ["approve_tasks", "reject_tasks"]

    @admin.display(description="Summary")
    def short_summary(self, obj):
        return obj.exec_summary[:80] if obj.exec_summary else "—"

    @admin.action(description="Approve selected tasks")
    def approve_tasks(self, request, queryset):
        approved = 0
        for task in queryset.filter(status=AgentTask.Status.AWAITING_APPROVAL):
            task.approve()
            approved += 1
        self.message_user(request, f"{approved} task(s) approved and queued.")

    @admin.action(description="Reject selected tasks")
    def reject_tasks(self, request, queryset):
        count = queryset.filter(status=AgentTask.Status.AWAITING_APPROVAL).update(
            status=AgentTask.Status.FAILED,
            error_message="Rejected by admin",
            completed_at=timezone.now(),
        )
        self.message_user(request, f"{count} task(s) rejected.")
```

- [ ] **Step 7: Create agents/admin/__init__.py**

```python
from .agent_admin import AgentAdmin
from .agent_task_admin import AgentTaskAdmin

__all__ = ["AgentAdmin", "AgentTaskAdmin"]
```

- [ ] **Step 8: Create agents/migrations/__init__.py (empty), run makemigrations and migrate**

Run:
```bash
cd backend && source venv/bin/activate && python manage.py makemigrations agents && python manage.py migrate
```

- [ ] **Step 9: Verify in admin**

Open http://localhost:8000/admin/ — verify Agents and Agent Tasks are visible. Create a test agent linked to a department.

- [ ] **Step 10: Commit**

```bash
git add backend/agents/__init__.py backend/agents/apps.py backend/agents/models/ backend/agents/admin/ backend/agents/migrations/
git commit -m "feat: agents app — Agent, AgentTask models with admin approve/reject actions"
```

---

### Task 5: Integrations App

**Files:**
- Create: `backend/integrations/__init__.py`
- Create: `backend/integrations/apps.py`
- Create: `backend/integrations/browser.py`

- [ ] **Step 1: Create integrations/__init__.py (empty) and apps.py**

```python
# integrations/apps.py
from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "integrations"
```

- [ ] **Step 2: Create integrations/browser.py**

```python
"""
Playwright browser automation for agent actions.

Agents that need browser interaction (twitter, reddit) call these functions
from their blueprint's execute_task method. Playwright runs headless on the worker VM.
"""

import json
import logging
import subprocess

logger = logging.getLogger(__name__)


def run_browser_action(action_type: str, params: dict, agent_config: dict) -> dict:
    """
    Execute a browser action via Playwright CLI.

    Args:
        action_type: The type of action (e.g. "navigate", "click", "type", "screenshot")
        params: Action-specific parameters
        agent_config: Agent's config JSON (may contain cookies, session data)

    Returns:
        dict with "success" bool and "result" or "error"
    """
    logger.info("Browser action: %s params=%s", action_type, json.dumps(params)[:200])

    try:
        # Placeholder: actual Playwright integration will use the Playwright Python API
        # For now, log the action and return a stub result
        logger.info("Would execute browser action: %s", action_type)
        return {
            "success": True,
            "result": f"Executed {action_type}",
            "action_type": action_type,
        }
    except Exception as e:
        logger.exception("Browser action failed: %s", action_type)
        return {
            "success": False,
            "error": str(e),
        }
```

- [ ] **Step 3: Commit**

```bash
git add backend/integrations/
git commit -m "feat: integrations app — browser automation stub for Playwright"
```

---

### Task 6: Agent Blueprints

**Files:**
- Create: `backend/agents/blueprints/__init__.py`
- Create: `backend/agents/blueprints/base.py`
- Create: `backend/agents/blueprints/twitter/__init__.py`
- Create: `backend/agents/blueprints/twitter/agent.py`
- Create: `backend/agents/blueprints/twitter/skills.py`
- Create: `backend/agents/blueprints/reddit/__init__.py`
- Create: `backend/agents/blueprints/reddit/agent.py`
- Create: `backend/agents/blueprints/reddit/skills.py`
- Create: `backend/agents/blueprints/campaign/__init__.py`
- Create: `backend/agents/blueprints/campaign/agent.py`
- Create: `backend/agents/blueprints/campaign/skills.py`

- [ ] **Step 1: Create agents/blueprints/base.py**

```python
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

logger = logging.getLogger(__name__)


class BaseBlueprint(ABC):
    """Abstract base class for all agent blueprints."""

    name: str = ""
    slug: str = ""
    description: str = ""

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The agent's persona, role, and capabilities."""

    @property
    @abstractmethod
    def hourly_prompt(self) -> str:
        """What to do on the hourly beat."""

    @property
    @abstractmethod
    def task_generation_prompt(self) -> str:
        """How to propose new tasks for the approval queue."""

    @property
    @abstractmethod
    def skills_description(self) -> str:
        """Formatted skills text injected into system prompt."""

    def get_context(self, agent: Agent) -> dict:
        """Gather context: project goal, department docs, sibling activity."""
        department = agent.department
        project = department.project

        # Department documents
        docs = list(
            department.documents.values_list("title", "content")
        )
        docs_text = ""
        for title, content in docs:
            docs_text += f"\n\n--- {title} ---\n{content[:3000]}"

        # Sibling agents and their recent tasks
        siblings = list(
            department.agents.exclude(id=agent.id)
            .filter(is_active=True)
            .values_list("name", "agent_type")
        )
        sibling_text = ""
        for sib_name, sib_type in siblings:
            from agents.models import AgentTask
            recent = list(
                AgentTask.objects.filter(
                    agent__name=sib_name,
                    agent__department=department,
                )
                .order_by("-created_at")[:5]
                .values_list("exec_summary", "status")
            )
            if recent:
                task_lines = "\n".join(f"  - [{s}] {e[:100]}" for e, s in recent)
                sibling_text += f"\n\n{sib_name} ({sib_type}) recent tasks:\n{task_lines}"

        # This agent's recent tasks
        own_recent = list(
            agent.tasks.order_by("-created_at")[:10]
            .values_list("exec_summary", "status", "report")
        )
        own_text = ""
        for es, st, rp in own_recent:
            own_text += f"\n  - [{st}] {es[:100]}"
            if rp:
                own_text += f"\n    Report: {rp[:200]}"

        return {
            "project_name": project.name,
            "project_goal": project.goal,
            "department_name": department.name,
            "department_documents": docs_text,
            "sibling_agents": sibling_text,
            "own_recent_tasks": own_text,
            "agent_instructions": agent.instructions,
        }

    def build_system_prompt(self, agent: Agent) -> str:
        """Assemble the full system prompt with blueprint + user instructions."""
        parts = [self.system_prompt]
        parts.append(f"\n\n## Your Skills\n{self.skills_description}")
        if agent.instructions:
            parts.append(f"\n\n## Additional Instructions\n{agent.instructions}")
        return "".join(parts)

    def build_context_message(self, agent: Agent) -> str:
        """Build user message with full context."""
        ctx = self.get_context(agent)
        return f"""# Context

## Project: {ctx['project_name']}
**Goal:** {ctx['project_goal']}

## Department: {ctx['department_name']}

### Department Documents
{ctx['department_documents'] or 'No documents yet.'}

### Other Agents in Department
{ctx['sibling_agents'] or 'No other agents.'}

### Your Recent Tasks
{ctx['own_recent_tasks'] or 'No tasks yet.'}"""

    @abstractmethod
    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        """Execute a task. Returns the report text."""

    @abstractmethod
    def generate_task_proposal(self, agent: Agent) -> dict:
        """Propose the next highest-value task. Returns {exec_summary, step_plan}."""
```

- [ ] **Step 2: Create agents/blueprints/twitter/skills.py**

```python
SKILLS = [
    {
        "name": "Search Trending Topics",
        "description": "Search Twitter/X for trending topics and hashtags relevant to the project's domain",
    },
    {
        "name": "Find High-Impact Tweets",
        "description": "Identify tweets with high engagement in the project's niche to engage with",
    },
    {
        "name": "Engage with Tweets",
        "description": "Like, reply to, and retweet relevant high-impact tweets to build presence",
    },
    {
        "name": "Post Tweet",
        "description": "Compose and post an original tweet aligned with project goals and branding",
    },
    {
        "name": "Post Thread",
        "description": "Compose and post a multi-tweet thread for in-depth content",
    },
]


def format_skills() -> str:
    lines = []
    for skill in SKILLS:
        lines.append(f"- **{skill['name']}**: {skill['description']}")
    return "\n".join(lines)
```

- [ ] **Step 3: Create agents/blueprints/twitter/agent.py**

```python
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import BaseBlueprint
from agents.blueprints.twitter.skills import format_skills

logger = logging.getLogger(__name__)


class TwitterBlueprint(BaseBlueprint):
    name = "Twitter Agent"
    slug = "twitter"
    description = "Manages Twitter/X presence — engagement, posting, trend monitoring"

    @property
    def system_prompt(self) -> str:
        return """You are a Twitter/X social media agent. Your role is to grow the project's presence on Twitter/X through strategic engagement and content creation.

You operate within a department and are aware of your project's goals, branding guidelines, and what other agents in your department are doing. You coordinate with the campaign agent when campaigns are active.

When executing tasks, respond with a JSON object containing your actions:
{
    "actions": [
        {"type": "tweet", "content": "...", "hashtags": ["..."]},
        {"type": "reply", "target_url": "...", "content": "..."},
        {"type": "retweet", "target_url": "..."},
        {"type": "like", "target_url": "..."},
        {"type": "search", "query": "..."}
    ],
    "report": "Summary of what was done and why"
}

Always align your content with the project's branding guidelines and voice."""

    @property
    def hourly_prompt(self) -> str:
        return """Perform your hourly engagement routine:
1. Search for 10 relevant high-impact tweets in the project's domain
2. Engage authentically with the best ones (like, reply, retweet)
3. If appropriate, post one original tweet that adds value

Focus on building genuine connections, not spam. Quality over quantity."""

    @property
    def task_generation_prompt(self) -> str:
        return """Based on the current project context, department activity, and your recent work, propose the single highest-value task you could do next on Twitter/X.

Consider:
- What content gaps exist?
- Are there trending topics to capitalize on?
- Is there engagement to follow up on?
- Are there campaign tasks that need Twitter support?

Respond with JSON:
{
    "exec_summary": "One-line description of the task",
    "step_plan": "Detailed step-by-step plan of what you will do"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        context_msg = self.build_context_message(agent)
        task_msg = f"""{context_msg}

# Task to Execute
**Summary:** {task.exec_summary}
**Plan:** {task.step_plan}

Execute this task now. Respond with your actions JSON and report."""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
        )

        # Parse response — try to extract actions for browser execution
        try:
            data = json.loads(response)
            actions = data.get("actions", [])
            report = data.get("report", response)

            for action in actions:
                from integrations.browser import run_browser_action
                run_browser_action(
                    action_type=action.get("type", "unknown"),
                    params=action,
                    agent_config=agent.config,
                )

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict:
        from agents.ai.claude_client import call_claude

        context_msg = self.build_context_message(agent)
        msg = f"""{context_msg}

# Task Proposal Request
{self.task_generation_prompt}"""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=msg,
        )

        try:
            data = json.loads(response)
            return {
                "exec_summary": data.get("exec_summary", "Twitter engagement task"),
                "step_plan": data.get("step_plan", response),
            }
        except (json.JSONDecodeError, KeyError):
            return {
                "exec_summary": "Twitter engagement task",
                "step_plan": response,
            }
```

- [ ] **Step 4: Create agents/blueprints/twitter/__init__.py**

```python
from .agent import TwitterBlueprint

__all__ = ["TwitterBlueprint"]
```

- [ ] **Step 5: Create agents/blueprints/reddit/skills.py**

```python
SKILLS = [
    {
        "name": "Browse Subreddits",
        "description": "Browse relevant subreddits to find discussions related to the project's domain",
    },
    {
        "name": "Post to Subreddit",
        "description": "Create a new post in a relevant subreddit with valuable content",
    },
    {
        "name": "Comment on Thread",
        "description": "Add a thoughtful, helpful comment to an existing Reddit discussion",
    },
    {
        "name": "Monitor Mentions",
        "description": "Search Reddit for mentions of the project, brand, or relevant keywords",
    },
]


def format_skills() -> str:
    lines = []
    for skill in SKILLS:
        lines.append(f"- **{skill['name']}**: {skill['description']}")
    return "\n".join(lines)
```

- [ ] **Step 6: Create agents/blueprints/reddit/agent.py**

```python
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import BaseBlueprint
from agents.blueprints.reddit.skills import format_skills

logger = logging.getLogger(__name__)


class RedditBlueprint(BaseBlueprint):
    name = "Reddit Agent"
    slug = "reddit"
    description = "Manages Reddit presence — posting, commenting, community engagement"

    @property
    def system_prompt(self) -> str:
        return """You are a Reddit social media agent. Your role is to build the project's presence on Reddit through valuable contributions to relevant communities.

You operate within a department and are aware of your project's goals, branding guidelines, and what other agents in your department are doing. You coordinate with the campaign agent when campaigns are active.

Reddit values authenticity and hates spam. Your contributions must be genuinely helpful and add value to discussions. Never be overtly promotional.

When executing tasks, respond with a JSON object containing your actions:
{
    "actions": [
        {"type": "post", "subreddit": "...", "title": "...", "content": "..."},
        {"type": "comment", "target_url": "...", "content": "..."},
        {"type": "search", "query": "...", "subreddit": "..."}
    ],
    "report": "Summary of what was done and why"
}

Always align your content with subreddit rules and the project's voice."""

    @property
    def hourly_prompt(self) -> str:
        return """Perform your hourly Reddit engagement routine:
1. Browse 3-5 relevant subreddits for discussions where you can add value
2. Leave 2-3 thoughtful, helpful comments on active threads
3. If there's a good opportunity, create one valuable post

Focus on being a genuine community member. Provide value first, brand visibility follows naturally."""

    @property
    def task_generation_prompt(self) -> str:
        return """Based on the current project context, department activity, and your recent work, propose the single highest-value task you could do next on Reddit.

Consider:
- Which subreddits have active discussions you can contribute to?
- Is there original content worth sharing?
- Are there questions in the community you can answer with expertise?
- Are there campaign tasks that need Reddit support?

Respond with JSON:
{
    "exec_summary": "One-line description of the task",
    "step_plan": "Detailed step-by-step plan of what you will do"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        context_msg = self.build_context_message(agent)
        task_msg = f"""{context_msg}

# Task to Execute
**Summary:** {task.exec_summary}
**Plan:** {task.step_plan}

Execute this task now. Respond with your actions JSON and report."""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
        )

        try:
            data = json.loads(response)
            actions = data.get("actions", [])
            report = data.get("report", response)

            for action in actions:
                from integrations.browser import run_browser_action
                run_browser_action(
                    action_type=action.get("type", "unknown"),
                    params=action,
                    agent_config=agent.config,
                )

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict:
        from agents.ai.claude_client import call_claude

        context_msg = self.build_context_message(agent)
        msg = f"""{context_msg}

# Task Proposal Request
{self.task_generation_prompt}"""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=msg,
        )

        try:
            data = json.loads(response)
            return {
                "exec_summary": data.get("exec_summary", "Reddit engagement task"),
                "step_plan": data.get("step_plan", response),
            }
        except (json.JSONDecodeError, KeyError):
            return {
                "exec_summary": "Reddit engagement task",
                "step_plan": response,
            }
```

- [ ] **Step 7: Create agents/blueprints/reddit/__init__.py**

```python
from .agent import RedditBlueprint

__all__ = ["RedditBlueprint"]
```

- [ ] **Step 8: Create agents/blueprints/campaign/skills.py**

```python
SKILLS = [
    {
        "name": "Create Campaign",
        "description": "Design a cross-platform campaign with goals, messaging, and timeline",
    },
    {
        "name": "Delegate to Subordinates",
        "description": "Create tasks for Twitter and Reddit agents to execute campaign components",
    },
    {
        "name": "Monitor Campaign Progress",
        "description": "Review subordinate agents' task reports to track campaign execution",
    },
    {
        "name": "Adjust Campaign Strategy",
        "description": "Modify campaign direction based on performance and feedback",
    },
]


def format_skills() -> str:
    lines = []
    for skill in SKILLS:
        lines.append(f"- **{skill['name']}**: {skill['description']}")
    return "\n".join(lines)
```

- [ ] **Step 9: Create agents/blueprints/campaign/agent.py**

```python
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import BaseBlueprint
from agents.blueprints.campaign.skills import format_skills

logger = logging.getLogger(__name__)


class CampaignBlueprint(BaseBlueprint):
    name = "Campaign Agent"
    slug = "campaign"
    description = "Orchestrates cross-platform campaigns and delegates to subordinate agents"

    @property
    def system_prompt(self) -> str:
        return """You are a campaign orchestration agent. Your role is to design and coordinate cross-platform social media campaigns, delegating execution to your subordinate agents (Twitter, Reddit, etc.).

You operate within a department and have a high-level view of the project's goals, branding, and all agent activity. You are the superior agent — you create and delegate tasks to subordinate agents.

When executing tasks, respond with a JSON object:
{
    "delegated_tasks": [
        {
            "target_agent_type": "twitter",
            "exec_summary": "What the Twitter agent should do",
            "step_plan": "Detailed steps for the Twitter agent"
        },
        {
            "target_agent_type": "reddit",
            "exec_summary": "What the Reddit agent should do",
            "step_plan": "Detailed steps for the Reddit agent"
        }
    ],
    "report": "Campaign strategy summary and delegation rationale"
}

Focus on strategic coordination. You don't post directly — you orchestrate."""

    @property
    def hourly_prompt(self) -> str:
        return """Review the current state of all active campaigns and subordinate agent activity:
1. Check recent task reports from subordinate agents
2. Identify any gaps in campaign execution
3. Delegate any needed follow-up tasks to subordinates
4. Assess if campaign strategy needs adjustment"""

    @property
    def task_generation_prompt(self) -> str:
        return """Based on the current project context, department activity, and campaign status, propose the single highest-value campaign action you could take.

Consider:
- Is there an opportunity for a new campaign?
- Do existing campaigns need adjustment?
- Are subordinate agents aligned and productive?
- Is there a time-sensitive opportunity to capitalize on?

Respond with JSON:
{
    "exec_summary": "One-line description of the campaign action",
    "step_plan": "Detailed step-by-step plan"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        context_msg = self.build_context_message(agent)
        task_msg = f"""{context_msg}

# Task to Execute
**Summary:** {task.exec_summary}
**Plan:** {task.step_plan}

Execute this task now. If you need to delegate to subordinate agents, include delegated_tasks in your response."""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
        )

        try:
            data = json.loads(response)
            delegated = data.get("delegated_tasks", [])
            report = data.get("report", response)

            # Delegate tasks to subordinate agents
            if delegated:
                from agents.models import Agent as AgentModel, AgentTask as TaskModel
                subordinates = AgentModel.objects.filter(
                    superior=agent,
                    is_active=True,
                )
                sub_by_type = {s.agent_type: s for s in subordinates}

                for dt in delegated:
                    target_type = dt.get("target_agent_type")
                    target_agent = sub_by_type.get(target_type)
                    if not target_agent:
                        logger.warning("No active subordinate of type %s for agent %s", target_type, agent.name)
                        continue

                    sub_task = TaskModel.objects.create(
                        agent=target_agent,
                        created_by_agent=agent,
                        status=TaskModel.Status.QUEUED,
                        auto_execute=True,
                        exec_summary=dt.get("exec_summary", "Delegated task"),
                        step_plan=dt.get("step_plan", ""),
                    )
                    from agents.tasks import execute_agent_task
                    execute_agent_task.delay(str(sub_task.id))
                    logger.info("Delegated task %s to %s", sub_task.id, target_agent.name)

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict:
        from agents.ai.claude_client import call_claude

        context_msg = self.build_context_message(agent)
        msg = f"""{context_msg}

# Task Proposal Request
{self.task_generation_prompt}"""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=msg,
        )

        try:
            data = json.loads(response)
            return {
                "exec_summary": data.get("exec_summary", "Campaign coordination task"),
                "step_plan": data.get("step_plan", response),
            }
        except (json.JSONDecodeError, KeyError):
            return {
                "exec_summary": "Campaign coordination task",
                "step_plan": response,
            }
```

- [ ] **Step 10: Create agents/blueprints/campaign/__init__.py**

```python
from .agent import CampaignBlueprint

__all__ = ["CampaignBlueprint"]
```

- [ ] **Step 11: Create agents/blueprints/__init__.py (registry)**

```python
"""
Blueprint registry.

Scans blueprint packages and builds the AGENT_TYPE_CHOICES for the Agent model.
"""

from agents.blueprints.twitter import TwitterBlueprint
from agents.blueprints.reddit import RedditBlueprint
from agents.blueprints.campaign import CampaignBlueprint

_REGISTRY = {
    "twitter": TwitterBlueprint(),
    "reddit": RedditBlueprint(),
    "campaign": CampaignBlueprint(),
}

AGENT_TYPE_CHOICES = [(slug, bp.name) for slug, bp in _REGISTRY.items()]


def get_blueprint(agent_type: str):
    """Get blueprint instance by agent_type slug."""
    bp = _REGISTRY.get(agent_type)
    if bp is None:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return bp
```

- [ ] **Step 12: Commit**

```bash
git add backend/agents/blueprints/
git commit -m "feat: agent blueprints — base ABC, twitter, reddit, campaign with skills"
```

---

### Task 7: Claude AI Client

**Files:**
- Create: `backend/agents/ai/__init__.py`
- Create: `backend/agents/ai/claude_client.py`

- [ ] **Step 1: Create agents/ai/__init__.py (empty)**

- [ ] **Step 2: Create agents/ai/claude_client.py**

```python
"""
Claude API client for agent reasoning.

All agent blueprint code calls this module to interact with Claude.
"""

import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def call_claude(
    system_prompt: str,
    user_message: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 4096,
) -> str:
    """
    Call Claude API and return the text response.

    Args:
        system_prompt: The system prompt for Claude
        user_message: The user message
        model: Claude model to use
        max_tokens: Max tokens in response

    Returns:
        The text content of Claude's response
    """
    client = _get_client()

    logger.info("Calling Claude: model=%s, system_len=%d, msg_len=%d", model, len(system_prompt), len(user_message))

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = ""
    for block in message.content:
        if block.type == "text":
            response_text += block.text

    logger.info(
        "Claude response: input_tokens=%d, output_tokens=%d",
        message.usage.input_tokens,
        message.usage.output_tokens,
    )

    return response_text
```

- [ ] **Step 3: Commit**

```bash
git add backend/agents/ai/
git commit -m "feat: Claude AI client for agent reasoning"
```

---

### Task 8: Celery Tasks — Beat Schedule & Execution

**Files:**
- Create: `backend/agents/tasks.py`

- [ ] **Step 1: Create agents/tasks.py**

```python
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def refill_approval_queue():
    """
    Every minute: for each active agent, if fewer than 5 tasks awaiting approval,
    ask Claude to propose the next highest-value task.
    """
    from agents.models import Agent, AgentTask

    agents = Agent.objects.filter(is_active=True).select_related("department__project")

    for agent in agents:
        awaiting_count = AgentTask.objects.filter(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
        ).count()

        if awaiting_count >= 5:
            continue

        try:
            blueprint = agent.get_blueprint()
            proposal = blueprint.generate_task_proposal(agent)

            AgentTask.objects.create(
                agent=agent,
                status=AgentTask.Status.AWAITING_APPROVAL,
                auto_execute=False,
                exec_summary=proposal.get("exec_summary", "Proposed task"),
                step_plan=proposal.get("step_plan", ""),
            )
            logger.info("Proposed task for %s: %s", agent.name, proposal.get("exec_summary", "")[:80])

        except Exception as e:
            logger.exception("Failed to generate task proposal for %s: %s", agent.name, e)


@shared_task
def execute_hourly_tasks():
    """
    Every hour: for each active agent with auto_exec_hourly=True,
    create and execute a task from the hourly prompt.
    """
    from agents.models import Agent, AgentTask

    agents = Agent.objects.filter(is_active=True, auto_exec_hourly=True).select_related("department__project")

    for agent in agents:
        try:
            blueprint = agent.get_blueprint()
            task = AgentTask.objects.create(
                agent=agent,
                status=AgentTask.Status.QUEUED,
                auto_execute=True,
                exec_summary=f"Hourly task: {blueprint.hourly_prompt[:100]}",
                step_plan=blueprint.hourly_prompt,
            )
            execute_agent_task.delay(str(task.id))
            logger.info("Created hourly task for %s: %s", agent.name, task.id)

        except Exception as e:
            logger.exception("Failed to create hourly task for %s: %s", agent.name, e)


@shared_task(bind=True, max_retries=0)
def execute_agent_task(self, task_id: str):
    """
    Execute a single agent task. Called when tasks are approved or auto-dispatched.
    Uses atomic guard to prevent double execution.
    """
    from agents.models import AgentTask

    # Atomic guard: only one worker can transition queued → processing
    updated = AgentTask.objects.filter(
        id=task_id,
        status=AgentTask.Status.QUEUED,
    ).update(
        status=AgentTask.Status.PROCESSING,
        started_at=timezone.now(),
    )

    if updated == 0:
        current = AgentTask.objects.filter(id=task_id).values_list("status", flat=True).first()
        logger.warning("Task %s not queued (status=%s) — skipping", task_id, current)
        return

    task = AgentTask.objects.select_related(
        "agent__department__project",
    ).get(id=task_id)

    try:
        blueprint = task.agent.get_blueprint()
        report = blueprint.execute_task(task.agent, task)

        task.status = AgentTask.Status.DONE
        task.report = report
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "report", "completed_at", "updated_at"])

        logger.info("Task %s completed: %s", task_id, task.exec_summary[:80])

    except Exception as e:
        logger.exception("Task %s failed: %s", task_id, e)
        task.status = AgentTask.Status.FAILED
        task.error_message = str(e)[:500]
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/tasks.py
git commit -m "feat: Celery tasks — refill_approval_queue, execute_hourly_tasks, execute_agent_task"
```

---

### Task 9: Smoke Test — Full Stack Verification

- [ ] **Step 1: Start infrastructure**

Run:
```bash
cd /Users/christianpeters/the-agentic-company
chmod +x start-dev.sh
docker compose -f docker-compose.dev.yml up -d
```

- [ ] **Step 2: Run configure**

Run:
```bash
cd backend && source venv/bin/activate && python manage.py configure
```

Expected: Migrations run, static files collected, superuser created.

- [ ] **Step 3: Verify admin**

Run:
```bash
python manage.py runserver 8000
```

Open http://localhost:8000/admin/ — login with admin@agentic.company / change-me.

Verify all models are visible:
- Users, Allow List Entries
- Projects, Departments, Documents, Tags
- Agents, Agent Tasks

- [ ] **Step 4: Create test data via admin**

1. Create a Project: name="Hotel Bookings Growth", goal="Increase hotel bookings by 30% through social media"
2. Create Department: name="Social Media", project=Hotel Bookings Growth
3. Create a Document in Social Media dept: title="Brand Voice Guide", content="Professional but friendly tone..."
4. Create Campaign Agent: name="Campaign Manager", type=campaign, department=Social Media
5. Create Twitter Agent: name="Twitter Agent", type=twitter, department=Social Media, superior=Campaign Manager
6. Create Reddit Agent: name="Reddit Agent", type=reddit, department=Social Media, superior=Campaign Manager

- [ ] **Step 5: Test Celery worker**

In a separate terminal:
```bash
cd backend && source venv/bin/activate && celery -A config worker --loglevel=info
```

Verify it starts without errors and discovers the tasks.

- [ ] **Step 6: Commit final state**

```bash
git add -A
git commit -m "feat: complete initial build — all apps, blueprints, celery tasks, admin"
```
