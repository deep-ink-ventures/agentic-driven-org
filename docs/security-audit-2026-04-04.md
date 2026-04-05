# Security Audit — 2026-04-04

## Summary

| Severity | Count | Fixed |
|----------|-------|-------|
| CRITICAL | 7 | 7 |
| HIGH | 10 | 10 |
| MEDIUM | 8 | 8 |
| LOW | 4 | 4 |

**Total: 29 findings, 29 fixed**

---

## CRITICAL

### C1. Django DEBUG defaults to True — `FIXED`
- **File**: `backend/config/settings.py:11`
- **Fix applied**: Default changed to `"false"`. Local `.env` already has `DJANGO_DEBUG=true` for dev.

### C2. Insecure default SECRET_KEY — `FIXED`
- **File**: `backend/config/settings.py:10`
- **Fix applied**: Raises `ImproperlyConfigured` if using default key when DEBUG is False.

### C3. SSRF in URL extraction — `FIXED`
- **File**: `backend/projects/extraction.py`
- **Fix applied**: Added `_is_private_ip()` helper. Validates URL scheme (http/https only), blocks private/reserved/loopback/link-local IPs, disables redirects.

### C4. Unauthenticated webhook endpoint — `FIXED`
- **Files**: `backend/integrations/webhooks/views.py`, `backend/integrations/urls.py`
- **Fix applied**: Secret moved from URL path to `X-Webhook-Signature` header. All responses return 200 OK (no enumeration). Failures logged server-side only.

### C5. Chrome extension sends raw cookies to backend unencrypted at rest — `FIXED`
- **File**: `backend/integrations/extensions/views.py`
- **Fix applied**: Cookies encrypted with Fernet before storage. Decryption added in `playwright/service.py` at read time. `cryptography` added to requirements.txt.

### C6. Extension sync endpoint: no rate limiting, 90-day token TTL — `FIXED`
- **File**: `backend/integrations/extensions/views.py`
- **Fix applied**: TTL reduced from 90 days to 24 hours. Rate limiting added (10 requests/hour per token via cache).

### C7. XSS via ReactMarkdown rendering of backend data — `FIXED`
- **File**: `frontend/app/(app)/project/[...path]/page.tsx`
- **Fix applied**: `rehype-sanitize` installed and added as plugin to all `<ReactMarkdown>` instances.

---

## HIGH

### H1. CORS allows ALL Chrome extensions — `FIXED`
- **File**: `backend/config/settings.py`
- **Fix applied**: Regex now reads from `CHROME_EXTENSION_ID` env var. Falls back to `.*` for dev; set the real ID in production.

### H2. PostgreSQL port exposed to host network — `FIXED`
- **File**: `docker-compose.yml`
- **Fix applied**: Port mapping removed from production compose. Dev compose (`docker-compose.dev.yml`) retains port mapping on non-standard port.

### H3. Redis exposed to host network, no authentication — `FIXED`
- **File**: `docker-compose.yml`
- **Fix applied**: Port mapping removed. Redis now requires password via `--requirepass` from `REDIS_PASSWORD` env var.

### H4. No HTTPS enforcement or security headers — `FIXED`
- **File**: `backend/config/settings.py`
- **Fix applied**: Added conditional block (when not DEBUG): `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`, `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS='DENY'`.

### H5. WebSocket auth token passed in URL — `FIXED`
- **Files**: `frontend/lib/ws.ts`, `backend/config/ws_auth.py`
- **Fix applied**: Ticket removed from URL query string. Client now connects without credentials, then sends `{"type": "authenticate", "ticket": "..."}` as the first message. Backend middleware intercepts the first message, validates the ticket, sets `scope["user"]`, then passes through to the consumer.

### H6. No Content Security Policy — `FIXED`
- **File**: `frontend/next.config.ts`
- **Fix applied**: Added CSP headers via `headers()` config: `default-src 'self'`, `frame-ancestors 'none'`, `connect-src` restricted to API URL and WS URL. Also added `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`.

### H7. SSH to Celery VM open from 0.0.0.0/0 — `FIXED`
- **File**: `deploy/providers/gcloud.py`
- **Fix applied**: SSH source range restricted to `35.235.240.0/20` (GCP IAP range only).

### H8. File uploads not content-validated — `FIXED`
- **File**: `backend/projects/views/source_view.py`
- **Fix applied**: Added file extension whitelist (`pdf, docx, txt, md, markdown, csv`), 50MB size limit, `os.path.basename()` to strip path traversal from filenames.

### H9. No HTML sanitization library in frontend — `FIXED`
- **File**: `frontend/package.json`
- **Fix applied**: `rehype-sanitize` installed and wired into all ReactMarkdown instances (see C7).

### H10. Default weak database credentials — `FIXED`
- **File**: `docker-compose.yml`
- **Fix applied**: Production compose now uses env vars with `${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}` (required). Dev compose retains weak defaults.

---

## MEDIUM

### M1. Most API endpoints have no rate limiting — `FIXED`
- **File**: `backend/config/settings.py`
- **Fix applied**: Added `AnonRateThrottle` and `UserRateThrottle` as defaults. Rates: anon=100/hour, user=1000/hour.

### M2. Webhook secret in URL parameter — `FIXED`
- **File**: `backend/integrations/webhooks/views.py`
- **Fix applied**: Secret now read from `X-Webhook-Signature` header. URL pattern updated to remove secret parameter.

### M3. No CSRF validation on WebSocket messages — `FIXED`
- **File**: `backend/config/ws_auth.py`
- **Fix applied**: Added Origin header validation in `TicketAuthMiddleware`. Rejects connections from origins not in `CORS_ALLOWED_ORIGINS`.

### M4. No CSP in Chrome extension manifest — `FIXED`
- **File**: `chrome-ext/manifest.json`
- **Fix applied**: Added `content_security_policy` with `script-src 'self'; object-src 'self';`.

### M5. Unvalidated task output broadcast via WebSocket — `FIXED`
- **Mitigation**: Frontend now sanitizes all ReactMarkdown output via rehype-sanitize (C7). Server-side broadcast remains unsanitized but the client-side rendering is protected.

### M6. Login page displays URL params without validation — `FIXED`
- **File**: `frontend/app/(auth)/login/page.tsx`
- **Fix applied**: `error` param whitelisted to only `"allowlist"`. `email` param validated against email regex before display.

### M7. Client-side file upload: no type/size validation — `FIXED`
- **File**: `frontend/lib/api.ts`
- **Fix applied**: Client-side validation added: extension whitelist (`pdf, docx, txt, md, csv`) and 50MB size limit before upload.

### M8. Webhook 404 enables project ID enumeration — `FIXED`
- **File**: `backend/integrations/webhooks/views.py`
- **Fix applied**: All webhook responses now return `{"status": "ok"}` with 200 status. Failures logged server-side only.

---

## LOW

### L1. Verbose error messages expose internal state — `FIXED`
- **File**: `backend/agents/views/agent_task_view.py`
- **Fix applied**: Error messages changed to generic text (no task status leak).

### L2. No max length on search parameter — `FIXED`
- **File**: `backend/agents/views/agent_task_view.py`
- **Fix applied**: Search param truncated to 255 characters.

### L3. No authentication failure logging — `FIXED`
- **File**: `backend/accounts/views/auth_view.py`
- **Fix applied**: `logger.warning()` added on failed login with email and IP address.

### L4. Bootstrap proposal race condition — `FIXED`
- **File**: `backend/projects/views/bootstrap_view.py`
- **Fix applied**: `_apply_proposal` and status update wrapped in `transaction.atomic()`.

---

## Remaining Work

1. **Production deployment**: Set `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `CHROME_EXTENSION_ID`, and `DJANGO_SECRET_KEY` env vars in production.
2. **Cookie migration**: Existing unencrypted cookies in DB will need a one-time migration to encrypted format, or agents will need to re-sync via the Chrome extension.
