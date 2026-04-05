"""GitHub Actions workflow templates pushed to target repos during bootstrap."""

CLAUDE_IMPLEMENT_YML = """\
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
          curl -X POST "${{ inputs.webhook_url }}" \\
            -H "Content-Type: application/json" \\
            -H "X-Webhook-Secret: ${{ secrets.WEBHOOK_SECRET }}" \\
            -d '{"workflow":"implement","issue":"${{ inputs.issue_number }}","status":"${{ job.status }}","branch":"${{ inputs.branch_name }}"}'
"""

CLAUDE_REVIEW_YML = """\
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
          curl -X POST "${{ inputs.webhook_url }}" \\
            -H "Content-Type: application/json" \\
            -H "X-Webhook-Secret: ${{ secrets.WEBHOOK_SECRET }}" \\
            -d '{"workflow":"review","pr":"${{ inputs.pr_number }}","status":"${{ job.status }}"}'
"""

CLAUDE_SECURITY_REVIEW_YML = """\
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
          curl -X POST "${{ inputs.webhook_url }}" \\
            -H "Content-Type: application/json" \\
            -H "X-Webhook-Secret: ${{ secrets.WEBHOOK_SECRET }}" \\
            -d '{"workflow":"security","pr":"${{ inputs.pr_number }}","status":"${{ job.status }}"}'
"""

CLAUDE_A11Y_AUDIT_YML = """\
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
          curl -X POST "${{ inputs.webhook_url }}" \\
            -H "Content-Type: application/json" \\
            -H "X-Webhook-Secret: ${{ secrets.WEBHOOK_SECRET }}" \\
            -d '{"workflow":"a11y","pr":"${{ inputs.pr_number }}","status":"${{ job.status }}"}'
"""

# Map of filename -> content for iteration during bootstrap
WORKFLOW_FILES = {
    "claude-implement.yml": CLAUDE_IMPLEMENT_YML,
    "claude-review.yml": CLAUDE_REVIEW_YML,
    "claude-security-review.yml": CLAUDE_SECURITY_REVIEW_YML,
    "claude-a11y-audit.yml": CLAUDE_A11Y_AUDIT_YML,
}
