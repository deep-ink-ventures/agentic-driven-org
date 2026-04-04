"""Tenant deployment state — tracks provisioned resources for resume."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path(__file__).parent / "state"


def _state_path(company: str) -> Path:
    return STATE_DIR / f"{company}.json"


def load_state(company: str) -> dict:
    """Load existing state or return empty state."""
    path = _state_path(company)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"company": company, "steps": {}, "resources": {}}


def save_state(company: str, state: dict) -> None:
    """Persist state to disk."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = _state_path(company)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def mark_step_complete(state: dict, step_name: str, resources: dict | None = None) -> None:
    """Mark a step as completed and record any resource identifiers."""
    state["steps"][step_name] = {
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if resources:
        state["resources"].update(resources)


def is_step_complete(state: dict, step_name: str) -> bool:
    """Check if a step has already been completed."""
    step = state.get("steps", {}).get(step_name, {})
    return step.get("status") == "completed"
