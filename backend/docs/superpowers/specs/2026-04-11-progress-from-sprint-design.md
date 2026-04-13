# Progress from Sprint — Design Spec

## Summary

Allow users to carry forward deliverables from completed sprints as source material for new sprints. When creating a sprint, the user can select one or more done sprints; their outputs become Source objects attached to the new sprint, automatically visible to agents via the existing context injection.

## Backend

### Sprint Creation (SprintListCreateView.perform_create)

Add optional `progress_from_sprint_ids` to the sprint creation payload. After the sprint is created and departments/sources are attached:

1. Fetch all `Output` objects from the referenced sprints
2. For each output with content (markdown/plaintext), create a `Source`:
   - `project` = current project
   - `source_type = "text"`
   - `raw_content = output.content`
   - `extracted_text = output.content` (already clean text, no extraction needed)
   - `original_filename = f"{output.title}.md"`
   - `user = request.user`
   - `sprint = new_sprint` (attach to new sprint)
   - `word_count = len(output.content.split())`
3. Skip outputs with empty content, link outputs, and file outputs (link/file outputs have no inline content to carry forward)

### SprintSerializer

Add `progress_from_sprint_ids` as a write-only list field (optional, default empty):

```python
progress_from_sprint_ids = serializers.ListField(
    child=serializers.UUIDField(),
    write_only=True,
    required=False,
    default=list,
)
```

Pop it in `create()` like `department_ids` and `source_ids`. The view's `perform_create` handles the logic.

### Validation

- Referenced sprints must exist and belong to the same project
- Referenced sprints must have status "done"
- If validation fails, 400 with clear error message

### No other backend changes

Sources created this way are identical to file-uploaded sources. The leader context injection at `base.py:1134` reads `sprint.sources.all()` — these new sources appear automatically. No agent pipeline changes needed.

## Frontend

### SprintInput Component

#### New State

```typescript
const [selectedSprints, setSelectedSprints] = useState<Sprint[]>([]);
const [showSprintPicker, setShowSprintPicker] = useState(false);
```

#### "Progress from sprint" Button

In the footer bar (between department pills and Start Sprint button), add a button:
- Icon: `GitBranch` or `History` from lucide
- Text: "Progress from sprint" (or just the icon on small screens)
- Clicking toggles `showSprintPicker`

#### Sprint Chips

Below the file chips area, show selected sprint chips:
- Each chip: sprint text (truncated ~40 chars) + department badge + X to remove
- Same visual style as file chips but with a distinct icon (History)

#### Submit

Extend `handleSubmit` to include `progress_from_sprint_ids`:

```typescript
await api.createSprint(projectId, {
  text: text.trim(),
  department_ids: Array.from(selectedDeptIds),
  source_ids: sourceIds,
  progress_from_sprint_ids: selectedSprints.map(s => s.id),
});
```

### SprintPickerDialog (new component)

A dialog/modal that lists done sprints for selection.

#### Props

```typescript
interface SprintPickerDialogProps {
  open: boolean;
  onClose: () => void;
  onSelect: (sprints: Sprint[]) => void;
  projectId: string;
  departmentId?: string;       // set at dept level, undefined at project level
  selectedIds: Set<string>;    // already selected sprint IDs
}
```

#### Behavior

- Fetches done sprints: `api.listSprints(projectId, { status: "done", department: departmentId })`
- At department level: only sprints for that department (pre-filtered by API)
- At project level: all done sprints, grouped by department display_name
- Search input at top filters by sprint text (client-side)
- Each row shows:
  - Sprint text (truncated)
  - Department badge (at project level)
  - Date (relative: "3 days ago")
  - Output count badge (e.g., "2 outputs")
  - Checkbox for selection
- "Done" button at bottom confirms selection
- Already-selected sprints shown checked

#### Layout

- Fixed-height scrollable list (max ~400px)
- Grouped by department at project level with sticky headers
- Empty state: "No completed sprints yet"

### API Client

Extend `createSprint` type:

```typescript
createSprint: (projectId: string, data: {
  text: string;
  department_ids: string[];
  source_ids?: string[];
  progress_from_sprint_ids?: string[];
}) => ...
```

No new endpoints needed — uses existing `listSprints` with `status=done` filter.

## Data Flow

```
User selects done sprint(s) in picker dialog
  → Sprint IDs stored in component state
  → On submit: IDs sent as progress_from_sprint_ids
  → Backend fetches Output objects from those sprints
  → Creates Source objects (type=text, raw_content=output.content)
  → Attaches Sources to new sprint
  → Leader context injection picks up sources automatically
  → Agents see prior deliverables as source material
```

## Edge Cases

- Sprint with no outputs: selectable but produces no sources (harmless)
- Very large output content: stored as-is in Source.raw_content (TextField, no size limit). The leader context injection at base.py:1134 uses `src.summary or src.extracted_text or src.raw_content` — for large sources, the summarization pipeline can be triggered separately if needed, but raw_content works for now.
- Same sprint selected twice: deduplicated by the frontend (Set-based selection)
- Sprint from different project: rejected by backend validation
