# Engineering Department Design Spec

**Date:** 2026-04-04
**Status:** Proposed
**Depends on:** [Department Config & GitHub Integration](2026-04-04-department-config-github-integration.md)

---

## Goal

Add an Engineering department with 8 agents (1 leader + 7 workforce) that autonomously decompose project goals into GitHub issues, implement code via GitHub Actions (using `claude-code-action`), run tests, review PRs, audit security, and verify accessibility — with human approval gates at key decision points.

## Architecture

**Brain/Hands Model:** Our agents are the brain — they hold context, skills, and judgment. GitHub Actions is the hands — it provides a code execution environment (clone, edit, test, push). The agent crafts a detailed, implementation-ready prompt; the Action executes it.

**Key Principle:** Three focused agents consistently outperform one generalist working three times as long (Osmani's "Code Agent Orchestra" pattern).

---

## Department Overview

**Department type:** `engineering`

| Agent | Blueprint Type | Role | GitHub Interaction |
|-------|---------------|------|-------------------|
| Engineering Leader | `leader` | Decomposes goals, routes tasks, tracks progress | Creates GitHub Projects, reads status |
| Ticket Manager | `ticket_manager` | Creates issues, labels, detects duplicates | Creates/manages GitHub issues |
| Backend Engineer | `backend_engineer` | Implements backend code | Triggers `claude-implement.yml` |
| Frontend Engineer | `frontend_engineer` | Implements frontend code | Triggers `claude-implement.yml` |
| Test Engineer | `test_engineer` | Writes tests, checks coverage | Triggers `claude-implement.yml` |
| Review Engineer | `review_engineer` | Reviews PRs, manages iteration | Triggers `claude-review.yml` |
| Security Auditor | `security_auditor` | Audits PRs for vulnerabilities | Triggers `claude-security-review.yml` |
| Accessibility Engineer | `accessibility_engineer` | Audits frontend PRs for WCAG compliance | Triggers `claude-a11y-audit.yml` |

---

## Task Flow

```
User creates Engineering department
  -> Leader bootstrap: creates GitHub Project board, pushes workflow files to repo
  -> Leader daily: scans project goal + activity -> decomposes into tickets

Leader creates "Implement feature X"
  -> Ticket Manager: creates GitHub issue with labels, acceptance criteria
  -> Leader creates implementation task for correct engineer(s)
     (blocked_by ticket_manager task)

Backend/Frontend Engineer receives task
  -> Builds implementation-ready prompt using skills + codebase context
  -> Triggers workflow dispatch (claude-code-action)
  -> Webhook returns with PR URL on completion

Leader creates follow-up tasks:
  -> Test Engineer task (blocked_by implementation)
  -> After tests pass:
     -> Review Engineer task
     -> Security Auditor task (parallel with review, if flagged paths)
     -> Accessibility Engineer task (parallel with review, if frontend PR)

Review Engineer reviews PR
  -> If changes requested: creates fix task back to original engineer
     (max 5 iterations tracked in internal_state)
  -> If approved + security/a11y pass: reports done

After all gates pass:
  -> If auto_merge_on_approval: merge PR
  -> Otherwise: leader reports completion, human merges
```

### Parallelism Rules

- Backend + Frontend Engineers can work **in parallel** on independent stories
- Security Auditor + Accessibility Engineer + Review Engineer run **in parallel**
- Test Engineer runs **after** implementation, **before** review
- Never assign the same file to two agents simultaneously

### Escalation

- After 5 review iterations on the same PR: stop, create human escalation task
- After 30 minutes without webhook callback: beat task marks run as failed, notifies leader
- Agent failure (Action returns error): leader assesses and re-routes or escalates

---

## Agent Designs

### 1. Engineering Leader

**Type:** `leader`

**Commands:**

| Command | Schedule | Model | Purpose |
|---------|----------|-------|---------|
| `bootstrap` | once | sonnet | Creates GitHub Project board with columns, pushes workflow files + CLAUDE.md to target repo |
| `plan_sprint` | daily | sonnet | Decomposes project goal into epics -> stories -> tasks |
| `check_progress` | hourly | haiku | Reads GitHub Project board status, unblocks stalled work |

**Skills:**

- `decompose_goal` — Breaks goal into Epic -> Story -> Task hierarchy. Each task scoped to 4-8 hours of junior engineer work. Maps dependencies to maximize parallelism.
- `route_task` — Routes tasks to agents based on file paths and issue labels:
  - `.py` in `api/`, `models/`, `services/` -> Backend Engineer
  - `.tsx`, `.css` in `components/`, `app/` -> Frontend Engineer
  - PR touches `auth/`, `crypto/`, API boundaries -> Security Auditor (parallel)
  - PR touches UI components -> Accessibility Engineer (parallel)
  - Any PR -> Review Engineer (after implementation + tests)
- `manage_dependencies` — Creates task chains with `blocked_by`, tracks progress in `internal_state`
- `escalate` — After 5 review iterations or agent failure, escalates to human
- `setup_repo` — Pushes the 4 workflow files to `.github/workflows/` and generates a `CLAUDE.md` for the target repo via GitHub API

**Leader System Prompt Core:**

```
You are the Engineering Leader. You decompose high-level goals into
implementable tickets and orchestrate a team of specialist agents.

DECOMPOSITION PROCESS:
1. Break the goal into 2-5 epics (user-facing capabilities)
2. Each epic -> 3-8 stories with acceptance criteria
3. Each story -> 1-3 tasks, each scoped to 4-8 hours of junior engineer work
4. Map dependencies: which tasks block others? Parallelize the rest.

ROUTING RULES:
- Route by file paths and domain, not by guessing
- Backend + Frontend can run in PARALLEL on independent stories
- Security Auditor + Accessibility Engineer run in PARALLEL with Review
- Test Engineer runs AFTER implementation, BEFORE review
- Never assign the same file to two agents simultaneously

ITERATION TRACKING:
- Track review iterations in internal_state["review_rounds"][pr_number]
- After 5 rounds on the same PR: stop, create a human escalation task

BOOTSTRAP:
On first run, push workflow files and CLAUDE.md to the target repo.
Create a GitHub Project board with columns: Backlog, In Progress, In Review, Done.
```

---

### 2. Ticket Manager

**Type:** `ticket_manager`

**Commands:**

| Command | Schedule | Model | Purpose |
|---------|----------|-------|---------|
| `create_issues` | on-demand | sonnet | Creates GitHub issues from leader's story breakdown |
| `triage_issue` | on-demand | haiku | Auto-labels incoming issues, checks for duplicates |

**Skills:**

- `write_issue` — Structures issues following the template below
- `label_and_prioritize` — Applies labels: type (`feature`, `bug`, `chore`), component (`api`, `frontend`, `auth`), size (`S/M/L`), priority (`P0-P3`)
- `detect_duplicates` — Searches existing issues before creating new ones
- `link_dependencies` — Cross-references related issues, notes blocking relationships

**Issue Template:**

```markdown
## [Verb] [Object] -- [Context]

### Problem Statement
[1-2 sentences: what problem exists and who it affects]

### Acceptance Criteria
GIVEN [precondition]
WHEN [action]
THEN [expected outcome]

### Technical Notes
- Relevant files: [paths]
- Follow pattern in: [reference file]
- Dependencies: [blocking issues]

### Out of Scope
- [Explicitly what this ticket does NOT cover]
```

---

### 3. Backend Engineer

**Type:** `backend_engineer`

**Commands:**

| Command | Schedule | Model | Purpose |
|---------|----------|-------|---------|
| `implement` | on-demand | sonnet | Crafts implementation prompt, triggers workflow dispatch |

**Skills:**

- `build_implementation_prompt` — Constructs a spec-grade prompt with structured sections. References existing file patterns by path. Scoped to 4-8 hours of work.
- `read_codebase_context` — Fetches relevant files via GitHub API to understand existing patterns before crafting the prompt
- `verify_result` — When webhook returns with PR URL, reads the diff and validates it matches requirements

**Prompt Construction Template:**

```
TASK: [One-sentence summary from the ticket]

CONTEXT:
- Repository: {repo}
- Relevant files: {file_paths from ticket}
- Existing patterns to follow: {reference file}
- Tech stack: Python 3.12, Django 5.x, DRF, PostgreSQL, Celery

REQUIREMENTS:
{acceptance criteria from ticket, numbered}

CONSTRAINTS:
- Follow the existing pattern in {reference file}
- Do not modify files outside the scope of this ticket
- All new code must have type hints

TESTS:
- Add tests covering happy path and error cases
- Use AAA pattern (Arrange/Act/Assert)
- Every test MUST have meaningful assertions
- Run: pytest --tb=short to verify

DEFINITION OF DONE:
- [ ] Feature works as described
- [ ] All existing tests pass
- [ ] New tests added and passing
- [ ] No linting errors (ruff check)
```

---

### 4. Frontend Engineer

**Type:** `frontend_engineer`

**Commands:**

| Command | Schedule | Model | Purpose |
|---------|----------|-------|---------|
| `implement` | on-demand | sonnet | Crafts UI implementation prompt, triggers workflow dispatch |

**Skills:**

- `build_ui_prompt` — Like backend but adds design tokens, component states, responsive breakpoints, and mandatory accessibility constraints
- `read_codebase_context` — Same as backend
- `verify_result` — Same as backend

**Additional Prompt Sections (beyond backend template):**

```
DESIGN SPEC:
- Follow existing component patterns in components/ui/
- Use Tailwind CSS 4 with project design tokens
- Implement ALL states: loading (skeleton), empty, error, populated

ACCESSIBILITY (MANDATORY -- non-negotiable):
- Semantic HTML (<nav>, <main>, <article>)
- ARIA labels for all interactive elements
- Keyboard navigation: Tab/Enter/Escape for all actions
- Visible focus ring, logical tab order
- Color contrast >= 4.5:1 for text, 3:1 for large text

RESPONSIVE:
- Mobile-first (< 768px)
- Tablet (768-1024px)
- Desktop (> 1024px)
```

---

### 5. Test Engineer

**Type:** `test_engineer`

**Commands:**

| Command | Schedule | Model | Purpose |
|---------|----------|-------|---------|
| `check_coverage` | on-demand | sonnet | Analyzes PR diff, writes missing tests, triggers workflow dispatch |

**Skills:**

- `analyze_coverage_gaps` — Reads the PR diff, identifies untested branches, edge cases, error paths
- `build_test_prompt` — Constructs test generation prompt with explicit quality rules and anti-patterns
- `verify_coverage` — Validates differential coverage meets threshold (>80% branch coverage on changed lines)

**Quality Enforcement:**

```
ASSERTION QUALITY RULES (ENFORCED):
- Every test MUST have at least one meaningful assertion
- Do NOT just assert "no exception thrown" -- assert actual output
- Assert side effects (DB state, API calls, events emitted)

ANTI-PATTERNS (FORBIDDEN):
- Tests without assertions
- Random/dynamic data that makes tests flaky
- Tests that depend on execution order
- Tests that print output for manual inspection
- Asserting implementation details (private methods, internal state)

TEST STRATEGY:
- Unit tests for pure business logic
- Integration tests for API endpoints / DB interactions
- Use AAA pattern: Arrange, Act, Assert

COVERAGE TARGET:
- Differential branch coverage > 80% (changed lines only)
- Run: pytest --cov --cov-branch
```

---

### 6. Review Engineer

**Type:** `review_engineer`

**Commands:**

| Command | Schedule | Model | Purpose |
|---------|----------|-------|---------|
| `review_pr` | on-demand | sonnet | Reviews PR, posts inline comments with severity levels |

**Skills:**

- `structured_review` — Reviews against team standards with signal/noise filtering. Target: >80% comment acceptance rate.
- `incremental_rereview` — On fix commits, reviews only the new diff. Auto-resolves addressed comments.
- `judge_filter` — Self-filters output before posting: removes style nitpicks, theoretical concerns, comments on unchanged code

**Review Criteria:**

```
WHAT TO CHECK:
- Correctness: Does the code do what the PR description says?
- Tests: Are new behaviors covered?
- Security: No hardcoded credentials, proper input validation
- Breaking changes: API contracts preserved
- Pattern consistency: Follows existing codebase conventions

WHAT NOT TO COMMENT ON:
- Style issues (handled by linter)
- Minor naming preferences
- Theoretical improvements not relevant to this PR
- Unchanged code

SEVERITY LEVELS:
- BLOCKER: Must fix before merge (bugs, security, breaking changes)
- SUGGESTION: Recommended but not blocking
- QUESTION: Seeking clarification
```

**Signal vs Noise:**

| High Signal (keep) | Low Signal (suppress) |
|--------------------|-----------------------|
| Bugs and logic errors | Style nitpicks covered by linters |
| Security vulnerabilities | "Consider renaming this variable" |
| Architectural drift | Theoretical performance concerns |
| Missing tests for new behavior | Comments on unchanged code |
| Breaking API changes | Boilerplate suggestions |

**Iteration Management:**

- `internal_state["review_rounds"][pr_number]` incremented each cycle
- After 5 rounds -> stops reviewing, creates escalation task for leader
- On re-review: only reviews new diff against prior findings

---

### 7. Security Auditor

**Type:** `security_auditor`

**Commands:**

| Command | Schedule | Model | Purpose |
|---------|----------|-------|---------|
| `security_review` | on-demand | sonnet | Triggers `claude-code-security-review` action on PR |

**Skills:**

- `assess_risk` — Reads PR diff, determines if security review is needed based on file paths (auth, crypto, API, dependencies, user input)
- `interpret_findings` — Interprets action results, filters by confidence threshold, posts structured comments

**What It Checks (via `anthropics/claude-code-security-review`):**

| Category | Specific Checks |
|----------|----------------|
| Injection Attacks | SQL, command, LDAP, XPath, NoSQL, XXE |
| Auth & Authorization | Broken auth, privilege escalation, insecure direct object references |
| Data Exposure | Hardcoded secrets, sensitive data logging, PII handling |
| Cryptographic Issues | Weak algorithms, improper key management |
| Business Logic | Race conditions, TOCTOU |
| Supply Chain | Vulnerable dependencies, typosquatting |
| XSS | Reflected, stored, DOM-based |

**What It Explicitly Ignores (noise reduction):**
- DoS / rate limiting
- Memory/CPU exhaustion
- Generic input validation without proven impact
- Open redirects

**Confidence Threshold:** Only reports findings at >= 0.8 confidence.

---

### 8. Accessibility Engineer

**Type:** `accessibility_engineer`

**Commands:**

| Command | Schedule | Model | Purpose |
|---------|----------|-------|---------|
| `a11y_audit` | on-demand | sonnet | Audits frontend PRs for WCAG 2.1 AA compliance |

**Skills:**

- `wcag_checklist` — Full WCAG 2.1 AA audit organized by principle
- `axe_core_analysis` — Triggers axe-core via workflow, interprets results (~57% automated coverage)
- `manual_checks` — Prompts for the remaining ~43%: heading hierarchy, focus management, screen reader announcements, keyboard trap detection

**WCAG 2.1 AA Checklist:**

```
PERCEIVABLE:
- All images have meaningful alt text (1.1.1)
- Color is not the only means of conveying info (1.4.1)
- Contrast >= 4.5:1 for text, 3:1 for large text (1.4.3)
- Text resizable to 200% without loss (1.4.4)
- Content reflows at 320px width (1.4.10)

OPERABLE:
- All functionality available via keyboard (2.1.1)
- No keyboard traps (2.1.2)
- Skip navigation link present (2.4.1)
- Focus order is logical (2.4.3)
- Focus visible on all interactive elements (2.4.7)
- Touch target >= 44x44 CSS pixels (2.5.5)

UNDERSTANDABLE:
- Page language declared (3.1.1)
- Form inputs have visible labels (3.3.2)
- Error messages identify field and describe error (3.3.1)

ROBUST:
- Valid HTML (4.1.1)
- ARIA roles/states/properties correct (4.1.2)
- Status messages use aria-live (4.1.3)
```

---

## GitHub Actions Integration

### Workflow Templates

Four reusable workflow files pushed to the target repo by the leader's `bootstrap` command:

#### 1. `claude-implement.yml`

Used by: Backend Engineer, Frontend Engineer, Test Engineer

```yaml
name: Claude Implement
on:
  workflow_dispatch:
    inputs:
      issue_number:
        description: 'GitHub issue number'
        required: true
      instructions:
        description: 'Implementation instructions from agent'
        required: true
      branch_name:
        description: 'Branch to create'
        required: true
      webhook_url:
        description: 'Callback URL for completion'
        required: true

jobs:
  implement:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          prompt: ${{ inputs.instructions }}
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          branch: ${{ inputs.branch_name }}
          create-pr: true
          pr-title: "#${{ inputs.issue_number }}: Implementation"
      - name: Notify webhook
        if: always()
        run: |
          curl -X POST "${{ inputs.webhook_url }}" \
            -H "Content-Type: application/json" \
            -H "X-Webhook-Secret: ${{ secrets.WEBHOOK_SECRET }}" \
            -d '{"workflow":"implement","issue":"${{ inputs.issue_number }}","status":"${{ job.status }}","branch":"${{ inputs.branch_name }}"}'
```

#### 2. `claude-review.yml`

Used by: Review Engineer

```yaml
name: Claude Review
on:
  workflow_dispatch:
    inputs:
      pr_number:
        description: 'PR number to review'
        required: true
      review_instructions:
        description: 'Review criteria from agent'
        required: true
      webhook_url:
        required: true

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          prompt: ${{ inputs.review_instructions }}
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          allowed-tools: "Read,Bash(gh pr diff:*),Bash(gh pr view:*),Bash(gh pr comment:*)"
      - name: Notify webhook
        if: always()
        run: |
          curl -X POST "${{ inputs.webhook_url }}" \
            -H "Content-Type: application/json" \
            -H "X-Webhook-Secret: ${{ secrets.WEBHOOK_SECRET }}" \
            -d '{"workflow":"review","pr":"${{ inputs.pr_number }}","status":"${{ job.status }}"}'
```

#### 3. `claude-security-review.yml`

Used by: Security Auditor

```yaml
name: Claude Security Review
on:
  workflow_dispatch:
    inputs:
      pr_number:
        required: true
      webhook_url:
        required: true

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-security-review@main
        with:
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          comment-pr: true
      - name: Notify webhook
        if: always()
        run: |
          curl -X POST "${{ inputs.webhook_url }}" \
            -H "Content-Type: application/json" \
            -H "X-Webhook-Secret: ${{ secrets.WEBHOOK_SECRET }}" \
            -d '{"workflow":"security","pr":"${{ inputs.pr_number }}","status":"${{ job.status }}"}'
```

#### 4. `claude-a11y-audit.yml`

Used by: Accessibility Engineer

```yaml
name: Claude A11y Audit
on:
  workflow_dispatch:
    inputs:
      pr_number:
        required: true
      instructions:
        required: true
      webhook_url:
        required: true

jobs:
  accessibility:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - run: npm ci
      - uses: anthropics/claude-code-action@v1
        with:
          prompt: |
            ${{ inputs.instructions }}

            Run axe-core checks:
            npx @axe-core/cli http://localhost:3000 --tags wcag2a,wcag2aa

            Run Lighthouse accessibility audit:
            npx lighthouse http://localhost:3000 --only-categories=accessibility --output=json

            Post findings as PR comments with severity levels.
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          allowed-tools: "Read,Bash(npx:*),Bash(gh pr comment:*),Bash(npm:*)"
      - name: Notify webhook
        if: always()
        run: |
          curl -X POST "${{ inputs.webhook_url }}" \
            -H "Content-Type: application/json" \
            -H "X-Webhook-Secret: ${{ secrets.WEBHOOK_SECRET }}" \
            -d '{"workflow":"a11y","pr":"${{ inputs.pr_number }}","status":"${{ job.status }}"}'
```

### Trigger Flow

```
Agent receives task
  -> Agent skill builds prompt (the brain work)
  -> Agent calls integrations.github_dev.service.trigger_workflow(
        repo, workflow_file, inputs={
          issue_number, instructions, branch_name, webhook_url
        })
  -> Agent sets internal_state["pending_runs"][run_id] = {
        workflow, issue, timestamp
     }
  -> Agent task status -> "processing"

GitHub Actions runs workflow
  -> On completion, POSTs to webhook_url
  -> integrations.webhooks receives it
  -> GitHub adapter verifies signature, routes to correct project
  -> Updates agent's internal_state
  -> Creates follow-up task for leader

Beat task: monitor_pending_webhooks
  -> Checks for runs older than 30 minutes without callback
  -> Marks as failed, notifies leader
```

### Webhook URL

Project-scoped: `/api/webhooks/{project_id}/github/`

Adapter extracts: `workflow`, `issue`/`pr`, `status`, `branch` — matched to agent via `internal_state["pending_runs"]`.

### Target Repo Requirements

For any repo the engineering department works on:

1. Four workflow files in `.github/workflows/` (pushed by leader bootstrap)
2. Two secrets: `CLAUDE_API_KEY` and `WEBHOOK_SECRET`
3. A `CLAUDE.md` describing the project (generated by leader bootstrap)

The leader's `bootstrap` command automates all of this — pushes workflow files and generates `CLAUDE.md` via the GitHub API on first setup.

---

## Department Config Schema

Cascading config: agent -> department -> project.

| Key | Type | Default | Level | Purpose |
|-----|------|---------|-------|---------|
| `github_repo` | string | required | department | Target repo (`owner/repo`) |
| `github_token` | string | required | project | PAT with repo + workflow permissions |
| `webhook_secret` | string | required | project | Shared secret for webhook signature verification |
| `default_branch` | string | `"main"` | department | Branch to target PRs against |
| `max_review_iterations` | integer | `5` | department | Review round cap before escalation |
| `auto_merge_on_approval` | boolean | `false` | department | Auto-merge when all gates pass |
| `require_security_review` | boolean | `true` | department | Security auditor on flagged PRs (auth, crypto, API, deps) |
| `require_a11y_review` | boolean | `true` | department | A11y audit on frontend PRs |
| `claude_model` | string | `"claude-sonnet-4-6"` | project | Model for GitHub Actions |

**Cascading example:**
- Project sets `github_token`, `webhook_secret`, `claude_model` (shared across departments)
- Department sets `github_repo`, `default_branch`, `max_review_iterations` (per-repo)
- Agent can override `claude_model` if needed (e.g., leader uses a more capable model)

---

## Research Sources

Industry-grade skills research informing this design:

- [Claude Code Action Solutions Guide](https://github.com/anthropics/claude-code-action/blob/main/docs/solutions.md)
- [Anthropic Claude Code Security Review](https://github.com/anthropics/claude-code-security-review)
- [Addy Osmani: The Code Agent Orchestra](https://addyosmani.com/blog/code-agent-orchestra/)
- [Augment Code: High-Quality AI Code Review Agent](https://www.augmentcode.com/blog/how-we-built-high-quality-ai-code-review-agent)
- [Devin Agents101](https://devin.ai/agents101)
- [OpenHands SOTA on SWE-bench](https://openhands.dev/blog/sota-on-swe-bench-verified-with-inference-time-scaling-and-critic-model)
- [axe-core Accessibility Engine](https://www.deque.com/axe/axe-core/)
- [OWASP Top 10 2025](https://seccomply.net/resources/blog/owasp-top-10-2025)
- [Graphite: AI Code Review Best Practices](https://graphite.com/guides/ai-code-review-implementation-best-practices)
- [TELPA: Advancing Code Coverage with LLMs](https://conf.researchr.org/details/ase-2025/ase-2025-journal-first-track/41/)

Full research briefings:
- `~/tmp/briefings/2026-04-04-ai-coding-agent-skills-research.md`
- `~/tmp/briefings/ai-marketing-agent-skills-research-2026-04-04.md`
