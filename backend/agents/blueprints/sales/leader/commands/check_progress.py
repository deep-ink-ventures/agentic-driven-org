"""Sales leader command: hourly progress check."""

from agents.blueprints.base import command


@command(
    name="check-progress",
    description=(
        "Hourly health check monitoring stalled review loops, overdue follow-ups, and idle agents. "
        "Detects completed writer tasks that need reviewer assignment, stalled tasks older than 3 hours, "
        "and review loops exceeding 3 rounds. Escalates blockers to the leader for intervention."
    ),
    schedule="hourly",
    model="claude-haiku-4-5",
)
def check_progress(self, agent) -> dict:
    return {
        "exec_summary": "Check pipeline health — stalled tasks, pending reviews, idle agents",
        "step_plan": (
            "1. Find completed writer tasks without reviewer assignment\n"
            "2. Detect stalled tasks (processing > 3h)\n"
            "3. Check review loops exceeding 3 rounds\n"
            "4. Report pipeline counts by stage"
        ),
    }
