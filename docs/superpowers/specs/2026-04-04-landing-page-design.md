# AgentDriven Landing Page — Design Spec

**Date:** 2026-04-04
**Status:** Approved

## Overview

A single-page marketing landing page for agentdriven.org. Communicates that AgentDriven is a consultancy and product company: we built an agentic AI stack — AI agents that run departments, handle workflows, take autonomous actions — deployable on your own cloud. We consult to deeply integrate it into your business.

Currently invite-only. Waitlist collects emails via SendGrid.

## Stack

- Next.js 15 (app router, TypeScript)
- Tailwind CSS 4
- No UI library — all custom components
- SendGrid Marketing Contacts API for waitlist
- Deployable on Vercel, Cloud Run, or any Node host

## Folder Structure

```
landing-page/
├── app/
│   ├── layout.tsx          # Root layout, fonts, metadata
│   ├── page.tsx            # All sections composed here
│   ├── globals.css         # Tailwind + custom properties
│   └── api/
│       └── waitlist/
│           └── route.ts    # POST → SendGrid Marketing Contacts
├── components/
│   ├── hero.tsx            # Hero with animated gradient
│   ├── value-props.tsx     # Three pillars
│   ├── product.tsx         # The agentic stack
│   ├── consulting.tsx      # Deep integration consulting
│   ├── security.tsx        # BYOC, security, no vendor lock-in
│   ├── quote.tsx           # Client quote — placeholder content
│   ├── waitlist.tsx        # Email capture + invite-only messaging
│   └── footer.tsx          # Minimal footer
├── tailwind.config.ts
├── package.json
├── .env.local.example      # SENDGRID_API_KEY, SENDGRID_LIST_ID
└── next.config.ts
```

## Page Sections (scroll order)

### 1. Hero
Full viewport height. Bold headline communicating the core proposition: an agentic AI stack you deploy on your own cloud, backed by a consultancy that makes it work for your business. One-liner subtitle. CTA button scrolls to waitlist. Background: slow-moving animated CSS mesh gradient (no JS animation library).

### 2. Value Props
Three columns:
- **Agentic AI software** — We built the stack. AI agents that run departments, execute workflows, make decisions. Not chatbots — autonomous agents.
- **Deep integration consulting** — We don't hand you software and walk away. We embed in your org, configure agents for your business, push you to state of the art.
- **Replace legacy, not people** — Kill manual processes, automate workflows, upskill your team. Modernize how your company operates.

### 3. Product
What the agentic stack is. Departments staffed by AI agents. Configurable workflows. Automated actions. Emphasize: runs on YOUR cloud infrastructure. Open, transparent, no black boxes. You own your data and your agents.

### 4. Consulting
What working with AgentDriven looks like. Focused, technical, outcome-driven. Not a 6-month enterprise engagement — we embed, configure, and ship. We make your company agentic-first and then you run it.

### 5. Security & BYOC
Bring your own cloud (GCP, AWS, Azure). Your data never leaves your infrastructure. API keys stay in your Secret Manager. No vendor lock-in. Security-first architecture.

### 6. Quote
Client testimonial section. Placeholder content for now — will be filled with real quotes later. Design: large pull-quote style, attribution below, visually distinct from surrounding sections.

### 7. Waitlist
"Currently invite-only due to high demand." Email input field + submit button. Inline success confirmation (no redirect). Subtle, confident — not desperate.

### 8. Footer
Minimal. AgentDriven wordmark, copyright 2026, contact email.

## Design Direction

### Palette
- Background: Deep navy/near-black (`#0a0e1a`)
- Primary accent: Electric violet/indigo gradient (`#6366f1` → `#8b5cf6`)
- Secondary/CTA: Warm amber (`#f59e0b`)
- Text: White headings, muted silver body (`#94a3b8`)

### Typography
- Headings: Inter or Satoshi — bold, tight letter-spacing, large sizes
- Body: Same family, lighter weight, generous line height

### Visual Treatment
- Hero: slow animated CSS mesh gradient background
- Section transitions: fade-in on scroll via Intersection Observer
- Cards: glass-morphism with subtle backdrop blur over dark background
- Waitlist form: glowing border on focus, satisfying submit state
- No illustrations, no stock photos, no icons. Type, color, and space.
- Generous whitespace throughout — premium, confident feel

### Tone
Mix of premium consultancy confidence (McKinsey Digital) and modern startup energy (Stripe). Bold but not loud. Lean copy — every word earns its place.

## Waitlist API

`POST /api/waitlist` with JSON body `{ "email": "..." }`:
1. Validate email format (server-side)
2. Call SendGrid Marketing Contacts API: `PUT https://api.sendgrid.com/v3/marketing/contacts` with email and list ID
3. Return `{ "success": true }` on success
4. Return `{ "error": "..." }` with appropriate status code on failure

Environment variables:
- `SENDGRID_API_KEY` — SendGrid API key
- `SENDGRID_LIST_ID` — Marketing list ID to add contacts to

## Content Approach

Copy will be drafted via the marketing:draft-content skill. Lean, punchy, no buzzword soup. Make people feel like they're missing out if they don't get on the list. The product is real, the consulting is serious, and the demand is high.

## Out of Scope

- Blog / content pages
- Authentication / login
- Admin panel for waitlist management (use SendGrid dashboard)
- Analytics (add later)
- Multi-language support
