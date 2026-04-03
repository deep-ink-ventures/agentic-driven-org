# Frontend Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a Next.js frontend with auth flow (login, signup with allowlist, Google OAuth) and empty dashboard, plus the Django API endpoints to support it.

**Architecture:** Next.js 16 App Router with next-intl (en/de), shadcn/tailwind dark theme, cookie-based auth via Django REST. Frontend at `frontend/`, reuses ScriptPulse's design system and patterns. Backend gets auth API endpoints (session, login, signup, logout, Google OAuth) following the `serializers/model_name_serializer.py`, `views/model_name_view.py` pattern.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn (base-nova), next-intl, Django REST Framework

**Reference:** ScriptPulse frontend at `../scriptpulse/frontend/`

---

## Phase 1: Django Auth API

### Task 1: Auth serializers, views, and URLs

**Files:**
- Create: `backend/accounts/serializers/__init__.py`
- Create: `backend/accounts/serializers/auth_serializer.py`
- Create: `backend/accounts/serializers/user_serializer.py`
- Create: `backend/accounts/views/__init__.py`
- Create: `backend/accounts/views/auth_view.py`
- Create: `backend/accounts/urls.py`
- Modify: `backend/config/urls.py`

The auth API mirrors ScriptPulse exactly. Key endpoints:
- `GET /api/auth/session/` — returns current user or null (sets CSRF cookie)
- `POST /api/auth/signup/` — email/password signup with allowlist check, terms_accepted required
- `POST /api/auth/login/` — email/password login
- `POST /api/auth/logout/` — logout
- `GET /api/auth/ws-ticket/` — WebSocket ticket
- Google OAuth via allauth URLs

**Serializers follow the pattern: `serializers/model_name_serializer.py`**

`serializers/auth_serializer.py`:
```python
from rest_framework import serializers
from accounts.models import User


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    terms_accepted = serializers.BooleanField(required=True)
    locale = serializers.ChoiceField(choices=["en", "de"], required=False, default="en")

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate_terms_accepted(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions.")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
```

`serializers/user_serializer.py`:
```python
from rest_framework import serializers
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "is_staff"]
        read_only_fields = fields
```

`serializers/__init__.py`:
```python
from .auth_serializer import SignupSerializer, LoginSerializer
from .user_serializer import UserSerializer

__all__ = ["SignupSerializer", "LoginSerializer", "UserSerializer"]
```

**Views follow the pattern: `views/model_name_view.py`**

`views/auth_view.py` — adapted from ScriptPulse but simplified (no beats, no referral, no newsletter, no email verification):
```python
from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User, AllowList
from accounts.serializers import LoginSerializer, SignupSerializer, UserSerializer


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            return Response({"user": UserSerializer(request.user).data})
        return Response({"user": None})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # AllowList gating
        if django_settings.ONLY_ALLOWLIST_CAN_SIGN_UP:
            email = data["email"]
            allowed = AllowList.objects.filter(email__iexact=email).exists()
            if not allowed:
                return Response(
                    {"error": "This email is not on the allow list."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        user = User.objects.create_user(email=data["email"], password=data["password"])
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["email"].lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out"})


class WsTicketView(APIView):
    def post(self, request):
        from config.ws_auth import create_ws_ticket
        ticket = create_ws_ticket(request.user.id)
        return Response({"ticket": ticket})
```

`views/__init__.py`:
```python
from .auth_view import SessionView, SignupView, LoginView, LogoutView, WsTicketView

__all__ = ["SessionView", "SignupView", "LoginView", "LogoutView", "WsTicketView"]
```

`accounts/urls.py`:
```python
from django.urls import path, include
from accounts import views

urlpatterns = [
    path("session/", views.SessionView.as_view(), name="auth-session"),
    path("signup/", views.SignupView.as_view(), name="auth-signup"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("ws-ticket/", views.WsTicketView.as_view(), name="ws-ticket"),
    # Google OAuth via django-allauth
    path("", include("allauth.socialaccount.providers.google.urls")),
]
```

Update `config/urls.py` — add auth URL include:
```python
path("api/auth/", include("accounts.urls")),
```

Commit after testing: `python manage.py check` passes.

---

## Phase 2: Frontend Scaffold

### Task 2: Next.js project initialization

Create the `frontend/` directory with Next.js, TypeScript, Tailwind, shadcn.

- [ ] **Step 1: Initialize Next.js project**

```bash
cd /Users/christianpeters/the-agentic-company
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --turbopack
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install next-intl @base-ui/react clsx tailwind-merge class-variance-authority lucide-react tw-animate-css
npm install -D @tailwindcss/postcss @tailwindcss/typography
```

- [ ] **Step 3: Initialize shadcn**

```bash
npx shadcn@latest init --style base-nova
npx shadcn@latest add button input label card separator
```

- [ ] **Step 4: Create config files**

Copy from ScriptPulse and adapt:
- `postcss.config.mjs` — same as ScriptPulse
- `tsconfig.json` — same as ScriptPulse
- `components.json` — same as ScriptPulse
- `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000`

- [ ] **Step 5: Create next.config.ts**

```typescript
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin();

const nextConfig: NextConfig = {
  output: "standalone",
};

export default withNextIntl(nextConfig);
```

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: initialize Next.js frontend with shadcn, tailwind, next-intl"
```

---

### Task 3: i18n setup, globals.css, types, API client

**Files:**
- Create: `frontend/i18n/routing.ts`
- Create: `frontend/i18n/navigation.ts`
- Create: `frontend/i18n/request.ts`
- Create: `frontend/messages/en.json`
- Create: `frontend/messages/de.json`
- Create: `frontend/app/globals.css`
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/utils.ts`
- Create: `frontend/proxy.ts`

**i18n files** — identical pattern to ScriptPulse.

**globals.css** — same dark theme as ScriptPulse but branded for AgentDriven:
```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-bg-primary: #111110;
  --color-bg-surface: #1C1B18;
  --color-bg-surface-hover: #272520;
  --color-bg-input: #181714;

  --color-accent-gold: #E8B84B;
  --color-accent-gold-hover: #F0C85C;
  --color-accent-gold-muted: oklch(0.78 0.12 85 / 0.15);

  --color-text-primary: #F0ECE2;
  --color-text-secondary: #A8A290;
  --color-text-heading: #FDFAF0;

  --color-border: #332F28;

  --color-flag-critical: #E5503E;
  --color-flag-major: #E8B84B;
  --color-flag-minor: #D4C068;
  --color-flag-strength: #52C48C;

  --font-serif: "Source Serif 4", Georgia, serif;
  --font-sans: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", monospace;
}

body {
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}

h1, h2, h3 {
  font-family: var(--font-serif);
  color: var(--color-text-heading);
}

@layer base {
  a, button, [role="button"] {
    cursor: pointer;
  }
}
```

**types.ts** — minimal for auth:
```typescript
export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
}
```

**api.ts** — fetch wrapper from ScriptPulse, simplified to auth-only endpoints:
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : null;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}${path}`;
  const headers: Record<string, string> = { ...options.headers as Record<string, string> };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const method = (options.method || "GET").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  }

  const doFetch = () => fetch(url, { ...options, credentials: "include", headers });

  let res: Response;
  try {
    res = await doFetch();
  } catch {
    await new Promise((r) => setTimeout(r, 2000));
    res = await doFetch();
  }

  if (res.status === 503) {
    await new Promise((r) => setTimeout(r, 2000));
    res = await doFetch();
  }

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  getSession: () => request<{ user: import("./types").User | null }>("/api/auth/session/"),
  login: (email: string, password: string) =>
    request<{ user: import("./types").User }>("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  signup: (email: string, password: string, termsAccepted: boolean, locale?: string) =>
    request<{ user: import("./types").User }>("/api/auth/signup/", {
      method: "POST",
      body: JSON.stringify({ email, password, terms_accepted: termsAccepted, locale }),
    }),
  logout: () => request<void>("/api/auth/logout/", { method: "POST" }),
};
```

**messages/en.json**:
```json
{
  "common": {
    "appName": "AgentDriven",
    "login": "Log In",
    "signup": "Sign Up",
    "logout": "Log Out",
    "loading": "Loading...",
    "error": "Something went wrong. Please try again.",
    "back": "Back"
  },
  "auth": {
    "loginTitle": "Welcome back",
    "loginSubtitle": "Sign in to your account",
    "signupTitle": "Create your account",
    "emailLabel": "Email",
    "passwordLabel": "Password",
    "invalidCredentials": "Invalid email or password.",
    "notOnAllowList": "This email is not on the early access list.",
    "noAccount": "Don't have an account?",
    "hasAccount": "Already have an account?",
    "continueWithGoogle": "Continue with Google",
    "termsLabel": "I agree to the Terms of Service and Privacy Policy"
  },
  "navbar": {
    "signedInAs": "Signed in as",
    "dashboard": "Dashboard",
    "settings": "Settings",
    "logout": "Log out"
  },
  "dashboard": {
    "title": "Dashboard",
    "welcome": "Welcome to AgentDriven",
    "empty": "Your dashboard is empty. Projects will appear here."
  }
}
```

**messages/de.json** — German translations of the above.

**proxy.ts** (middleware):
```typescript
import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

const intlMiddleware = createMiddleware(routing);

export function proxy(request: import("next/server").NextRequest) {
  return intlMiddleware(request);
}

export const config = {
  matcher: ["/((?!api|_next|_vercel|monitoring|.*\\..*).*)"],
};
```

---

### Task 4: Auth provider, useAuth hook, root layout

**Files:**
- Create: `frontend/components/auth-provider.tsx`
- Create: `frontend/hooks/use-auth.ts`
- Create: `frontend/app/[locale]/layout.tsx`

Copy patterns directly from ScriptPulse. Adapt:
- App name: "AgentDriven"
- No beats, no subscription tier, no role selection
- Signup takes `termsAccepted` instead of `newsletterOptIn`

---

### Task 5: Login page, Signup page, Dashboard page

**Files:**
- Create: `frontend/app/[locale]/(auth)/login/page.tsx`
- Create: `frontend/app/[locale]/(auth)/signup/page.tsx`
- Create: `frontend/app/[locale]/(app)/layout.tsx`
- Create: `frontend/app/[locale]/(app)/dashboard/page.tsx`
- Create: `frontend/components/nav-bar.tsx`
- Create: `frontend/app/[locale]/page.tsx` (root redirect to login/dashboard)

**Login page** — adapted from ScriptPulse:
- Google OAuth button
- Email/password form
- Allowlist error handling
- Redirect to `/dashboard` on success

**Signup page** — adapted from ScriptPulse:
- Google OAuth button (requires terms accepted)
- Email/password form
- Terms and conditions checkbox (required, no newsletter)
- Allowlist error handling
- Redirect to `/dashboard` on success

**(app)/layout.tsx** — protected route layout:
- Checks `useAuth()` — redirects to `/login` if not authenticated
- Shows NavBar + main content

**Dashboard page** — empty for now:
```tsx
"use client";

import { useTranslations } from "next-intl";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-semibold mb-4">{t("title")}</h1>
      <p className="text-text-secondary">{t("empty")}</p>
    </div>
  );
}
```

**NavBar** — simplified from ScriptPulse:
- Logo + "AgentDriven" text
- User dropdown: email, dashboard link, logout
- No beats, no subscription

**Root page** (`app/[locale]/page.tsx`) — redirects:
```tsx
import { redirect } from "@/i18n/navigation";
export default function Home() {
  redirect("/login");
}
```

---

### Task 6: Update start-dev.sh, verify full stack

- Add frontend to `start-dev.sh`
- Verify: `npm run dev` starts on port 3000
- Verify: login flow works end-to-end (allowlist user, session cookie, dashboard redirect)
- Commit

---

## Summary

| Task | Scope | Dependencies |
|------|-------|-------------|
| 1 | Django auth API (serializers, views, urls) | None |
| 2 | Next.js scaffold (create-next-app, shadcn, deps) | None |
| 3 | i18n, globals.css, types, API client, middleware | Task 2 |
| 4 | Auth provider, useAuth hook, root layout | Task 3 |
| 5 | Login, Signup, Dashboard pages, NavBar | Task 4 |
| 6 | Wire up start-dev.sh, full stack verify | Tasks 1+5 |
