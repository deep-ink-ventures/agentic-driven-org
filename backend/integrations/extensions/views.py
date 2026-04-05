"""
Chrome extension endpoints for session cookie sync.

Two endpoints:
1. GenerateExtensionTokenView — authenticated user generates a pairing token for a project
2. SyncSessionView — extension POSTs cookies using the pairing token (no session auth)
"""

import json
import logging

import requests as http_requests
from cryptography.fernet import Fernet
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from projects.models import Project

logger = logging.getLogger(__name__)

# Token prefix for namespacing
TOKEN_SALT = "extension-pairing"
# Tokens valid for 24 hours (was 90 days)
TOKEN_MAX_AGE = 24 * 60 * 60


def _get_fernet() -> Fernet:
    """Get Fernet instance using COOKIE_ENCRYPTION_KEY from settings (or derive from SECRET_KEY)."""
    import base64
    import hashlib

    key = getattr(settings, "COOKIE_ENCRYPTION_KEY", None)
    if not key:
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt_cookies(cookies: dict) -> str:
    """Encrypt cookie dict to a Fernet-encrypted string."""
    f = _get_fernet()
    return f.encrypt(json.dumps(cookies).encode()).decode()


def decrypt_cookies(encrypted: str) -> dict:
    """Decrypt Fernet-encrypted cookie string back to dict."""
    f = _get_fernet()
    return json.loads(f.decrypt(encrypted.encode()).decode())


# Maps platform key → config key on the agent + agent_type hint for auto-discovery
PLATFORM_CONFIG = {
    "twitter": {"config_key": "twitter_session", "agent_types": ["twitter"]},
    "reddit": {"config_key": "reddit_session", "agent_types": ["reddit"]},
    "luma": {"config_key": "luma_session", "agent_types": ["luma_researcher"]},
}


def _fetch_reddit_username(cookies: dict) -> dict:
    """Call Reddit API with session cookies to get the actual username."""
    try:
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        resp = http_requests.get(
            "https://www.reddit.com/api/me.json",
            headers={
                "Cookie": cookie_str,
                "User-Agent": "AgenticCompany/1.0",
            },
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            name = data.get("data", {}).get("name", "")
            if name:
                return {"reddit_username": name}
    except Exception:
        logger.warning("Failed to fetch Reddit username from API")
    return {}


def _fetch_twitter_handle(cookies: dict) -> dict:
    """Extract Twitter handle from the twid cookie (contains user ID)."""
    # twid cookie contains the user ID as u%3D<id>
    # We can't easily get the handle without an API call,
    # and Twitter's API requires OAuth. Skip for now.
    return {}


class GenerateExtensionTokenView(APIView):
    """POST /api/projects/<slug>/extension-token/ — generate a pairing token."""

    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        try:
            project = Project.objects.get(slug=slug, members=request.user)
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        token = signing.dumps(
            {"project_id": str(project.id), "user_id": str(request.user.id)},
            salt=TOKEN_SALT,
        )

        return Response({"token": token, "project": project.name})


class SyncSessionView(APIView):
    """
    POST /api/extensions/sync-session/ — receive cookies from chrome extension.

    Authenticated via X-Extension-Token header (signed pairing token).
    Body: {"platform": "twitter", "cookies": {"auth_token": "...", ...}}
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # Skip session/CSRF auth — uses token

    # Rate limit: 10 requests per hour per token
    RATE_LIMIT_PREFIX = "ext_sync_rate"
    RATE_LIMIT_MAX = 10
    RATE_LIMIT_WINDOW = 3600

    def _check_rate_limit(self, token_hash: str) -> bool:
        cache_key = f"{self.RATE_LIMIT_PREFIX}:{token_hash}"
        count = cache.get(cache_key, 0)
        if count >= self.RATE_LIMIT_MAX:
            return False
        cache.set(cache_key, count + 1, self.RATE_LIMIT_WINDOW)
        return True

    def post(self, request):
        # Validate token
        token = request.headers.get("X-Extension-Token", "")
        if not token:
            return Response(
                {"error": "Missing X-Extension-Token header"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            payload = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
        except signing.BadSignature:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Rate limit per token
        import hashlib

        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        if not self._check_rate_limit(token_hash):
            return Response(
                {"error": "Rate limit exceeded. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        project_id = payload.get("project_id")

        # Validate request body
        platform = request.data.get("platform")
        cookies = request.data.get("cookies")

        if not platform or not cookies:
            return Response(
                {"error": "platform and cookies are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        platform_cfg = PLATFORM_CONFIG.get(platform)
        if not platform_cfg:
            return Response(
                {"error": f"Unknown platform: {platform}. Supported: {', '.join(PLATFORM_CONFIG.keys())}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find the agent(s) in this project that use this platform
        config_key = platform_cfg["config_key"]
        agent_types = platform_cfg["agent_types"]

        agents = Agent.objects.filter(
            department__project_id=project_id,
            agent_type__in=agent_types,
        )

        if not agents.exists():
            return Response(
                {"error": f"No {platform} agent found in this project"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Resolve platform-specific metadata from APIs (not DOM scraping)
        extra_config = {}
        if platform == "reddit":
            extra_config = _fetch_reddit_username(cookies)
        elif platform == "twitter":
            extra_config = _fetch_twitter_handle(cookies)

        # Update config on all matching agents
        updated = []
        for agent in agents:
            config = agent.config or {}
            config[config_key] = encrypt_cookies(cookies)
            config.update(extra_config)

            agent.config = config
            agent.save(update_fields=["config"])
            updated.append(agent.name)
            logger.info(
                "Synced %s session cookies to agent '%s' (project=%s, extra=%s)",
                platform,
                agent.name,
                project_id,
                list(extra_config.keys()),
            )

        return Response(
            {
                "synced": True,
                "platform": platform,
                "agent_name": ", ".join(updated),
                "cookie_count": len(cookies),
            }
        )
