# Sources & Auto-Bootstrap — Design Spec

## Overview

Add source material upload (files, URLs, free text) to projects. When triggered, Claude analyzes all sources against the project goal and proposes a complete setup: departments, agents with pre-filled instructions, and department documents. The proposal is reviewable before being applied.

## Data Models

### projects.Source

Belongs to Project. Stores uploaded files, URLs, or free text with extracted text for Claude analysis.

| Field | Type | Notes |
|-------|------|-------|
| id | UUIDField PK | |
| project | FK → Project | |
| source_type | CharField choices | `file`, `url`, `text` |
| original_filename | CharField max=255, blank | For file sources |
| url | URLField blank | For URL sources |
| file_key | CharField max=512, blank | Storage path — private, never exposed directly |
| content_hash | CharField max=64, blank | SHA-256 dedup per user |
| user | FK → User, null | Uploader |
| raw_content | TextField blank | For text sources; also stores unprocessed extracted text |
| extracted_text | TextField blank | Cleaned text ready for Claude |
| file_format | CharField max=20, blank | pdf, docx, txt, md |
| content_type | CharField max=100, blank | MIME type |
| file_size | PositiveIntegerField null | Bytes |
| word_count | PositiveIntegerField null | |
| created_at | DateTimeField auto_now_add | |

Constraints:
- UniqueConstraint on (user, content_hash) where content_hash is not empty — prevents duplicate file uploads per user.

### projects.BootstrapProposal

Tracks each bootstrap attempt with full status lifecycle for debugging and auditing.

| Field | Type | Notes |
|-------|------|-------|
| id | UUIDField PK | |
| project | FK → Project | |
| status | CharField choices | `pending`, `processing`, `proposed`, `approved`, `failed` |
| proposal | JSONField null, blank | The proposed structure |
| error_message | TextField blank | If failed |
| token_usage | JSONField null, blank | Claude API usage tracking |
| created_at | DateTimeField auto_now_add | |
| updated_at | DateTimeField auto_now | |

#### Proposal JSON Schema

```json
{
  "summary": "Human-readable analysis of what was found in the sources",
  "departments": [
    {
      "name": "Social Media",
      "documents": [
        {
          "title": "Brand Voice Guide",
          "content": "Markdown content extracted and structured from sources...",
          "tags": ["branding", "voice"]
        }
      ],
      "agents": [
        {
          "name": "Twitter Agent",
          "agent_type": "twitter",
          "instructions": "Custom instructions derived from source analysis...",
          "auto_exec_hourly": false
        }
      ]
    }
  ],
  "ignored_content": [
    {
      "source_id": "uuid",
      "source_name": "floor_plan.pdf",
      "reason": "Floor plan image — not relevant for agent setup"
    }
  ]
}
```

The `agent_type` values are strictly limited to registered blueprints (twitter, reddit, campaign). Claude receives the list of available types and their descriptions in the prompt.

## File Structure

All new files in existing apps:

```
projects/
├── models/
│   ├── source.py                     (new)
│   ├── bootstrap_proposal.py         (new)
│   └── __init__.py                   (update — add exports)
├── admin/
│   ├── source_admin.py               (new)
│   ├── bootstrap_proposal_admin.py   (new — approve action)
│   ├── project_admin.py              (update — bootstrap action, source inline)
│   └── __init__.py                   (update)
├── storage.py                        (new — from scriptpulse)
├── extraction.py                     (new — text extractors)
├── prompts.py                        (new — bootstrap system prompt)
├── tasks.py                          (new — bootstrap_project celery task)
└── migrations/
```

## Storage

Lifted from scriptpulse's `projects/storage.py`. Dual-backend abstraction:

- **Local** (dev): files stored in `MEDIA_ROOT/projects/{project_id}/sources/`, served via Django.
- **GCS** (production): private bucket, access only via time-limited signed URLs.

Controlled by `STORAGE_BACKEND` env var (defaults to `local` when `DEBUG=True`, `gcs` otherwise).

Public API:
- `upload_file(content, filename, project_id, subfolder="sources") -> file_key`
- `get_signed_url(file_key) -> url`
- `delete_file(file_key) -> bool`
- `delete_project_files(project_id) -> count`

## Text Extraction

New `projects/extraction.py`. Each extractor takes raw input and returns plain text. All extractors are memory-efficient — process page-at-a-time, stream where possible, close handles promptly.

**Supported formats:**
- **PDF**: PyMuPDF (`fitz`) — iterate pages, extract text per page, close document immediately. Memory efficient for large PDFs.
- **DOCX**: `python-docx` — extract paragraph text.
- **TXT/Markdown**: read directly, no processing needed.
- **URL**: `requests` (with timeout + size limit) + `BeautifulSoup` with `lxml` parser — fetch page, extract main content area, strip nav/header/footer/script tags.
- **Free text**: pass through as-is (source_type=text, raw_content stored directly).

Public API:
- `extract_text(source) -> str` — dispatches to the right extractor based on source_type/file_format.

Extraction runs synchronously when a source is created via admin (it's fast — seconds). The expensive Claude analysis only happens during the bootstrap task.

## Bootstrap Flow

### Trigger: Admin Action on Project

"Bootstrap Project" action on ProjectAdmin:
1. Validates project has a goal and at least one source
2. Creates BootstrapProposal with status=`pending`
3. Dispatches `bootstrap_project.delay(proposal_id)`
4. Shows success message with link to the proposal

### Celery Task: `bootstrap_project(proposal_id)`

1. Load proposal, set status → `processing`
2. Gather all sources' extracted_text for the project
3. Build the bootstrap prompt:
   - Project name and goal
   - All source texts (truncated if needed to fit context)
   - Available blueprint types with their names and descriptions
   - Strict JSON output schema
4. Call Claude (via `agents.ai.claude_client.call_claude`)
5. Parse response JSON
6. Store proposal JSON and token_usage, set status → `proposed`
7. On failure: status → `failed`, store error_message

### Bootstrap Prompt

Lives in `projects/prompts.py`. Structured as:

**System prompt**: You are a project setup analyst. Given source materials and a project goal, propose the optimal department and agent configuration. You must only propose agent types from the provided list. Structure extracted knowledge into department documents. Explain what you used and what you ignored.

**User message**: Project name, goal, source texts, available agent types with descriptions.

**Response format**: Strict JSON matching the proposal schema above.

### Approve: Admin Action on BootstrapProposal

"Approve & Apply" action on BootstrapProposalAdmin:
1. Validates status is `proposed`
2. Iterates `proposal.departments`:
   - Creates Department
   - Creates Documents with Tags (creates Tags if they don't exist)
   - Creates Agents with instructions, sets agent_type, auto_exec_hourly
3. Sets superior relationships: for each department, if a campaign agent exists, sets it as superior to twitter/reddit agents
4. Sets proposal status → `approved`
5. Shows success message with count of created objects

### Reject

"Reject" action sets status → `failed` with a note. User can re-trigger bootstrap to get a new proposal.

## Admin UI

### SourceAdmin
- list_display: source_type, original_filename/url, file_format, file_size, word_count, project, created_at
- list_filter: source_type, file_format, project
- readonly_fields: id, file_key, content_hash, extracted_text, word_count, created_at

### BootstrapProposalAdmin
- list_display: project, status, created_at, updated_at
- list_filter: status
- readonly_fields: id, proposal (formatted), token_usage, error_message, created_at, updated_at
- actions: approve_and_apply, reject

### ProjectAdmin updates
- Add SourceInline (TabularInline) — add sources directly from project page
- Add "Bootstrap Project" action

## Dependencies

Add to `requirements.txt`:
- `pymupdf>=1.25,<2.0` — PDF text extraction
- `python-docx>=1.1,<2.0` — DOCX text extraction
- `beautifulsoup4>=4.12,<5.0` — HTML parsing for URL sources
- `lxml>=5.0,<6.0` — fast HTML parser backend

## Scope

**In scope:**
- Source model (file, url, text types)
- Storage abstraction (local + GCS)
- Text extraction (PDF, DOCX, TXT, URL, free text)
- BootstrapProposal model with status lifecycle
- Bootstrap Celery task calling Claude
- Bootstrap prompt in projects/prompts.py
- Approve action creating departments/agents/documents
- Admin UI for all of the above
- Source inline on ProjectAdmin

**Out of scope:**
- Frontend wizard (future — will replace admin actions)
- Image/OCR extraction
- Video/audio transcription
- Incremental re-bootstrap (add more sources, re-analyze)
- WebSocket progress updates for bootstrap
