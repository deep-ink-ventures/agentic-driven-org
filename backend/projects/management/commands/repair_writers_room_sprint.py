"""
Repair a Writers Room sprint by replaying lead_writer diffs to rebuild deliverables.

Usage:
    python manage.py repair_writers_room_sprint <sprint_id> [--dry-run] [--stage pitch]
"""

import logging

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

# lead_writer command → stage
COMMAND_TO_STAGE = {
    "write_pitch": "pitch",
    "write_expose": "expose",
    "write_treatment": "treatment",
    "write_concept": "treatment",  # series format uses "concept" command for treatment stage
    "write_first_draft": "first_draft",
}

# stage → effective display name (for doc title matching)
STAGE_DISPLAY = {
    "pitch": "Pitch",
    "expose": "Expose",
    "treatment": "Treatment",
    "first_draft": "First Draft",
}


class Command(BaseCommand):
    help = "Replay lead_writer task diffs to rebuild Writers Room deliverables for a sprint."

    def add_arguments(self, parser):
        parser.add_argument("sprint_id", type=str, help="Sprint UUID")
        parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
        parser.add_argument(
            "--stage", type=str, help="Only repair a specific stage (pitch, expose, treatment, first_draft)"
        )

    def handle(self, *args, **options):
        from projects.models import Sprint

        sprint_id = options["sprint_id"]
        dry_run = options["dry_run"]
        stage_filter = options.get("stage")

        try:
            sprint = Sprint.objects.prefetch_related("departments").get(id=sprint_id)
        except Sprint.DoesNotExist as exc:
            raise CommandError(f"Sprint {sprint_id} not found.") from exc

        # Verify it's a writers room department
        departments = list(sprint.departments.all())
        wr_dept = None
        for dept in departments:
            leader = dept.agents.filter(is_leader=True).first()
            if leader:
                bp = leader.get_blueprint()
                from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

                if isinstance(bp, WritersRoomLeaderBlueprint):
                    wr_dept = dept
                    break

        if not wr_dept:
            raise CommandError(
                f"Sprint {sprint_id} has no Writers Room department. " f"Departments: {[d.name for d in departments]}"
            )

        self.stdout.write(f"Sprint: {sprint.text[:80]}")
        self.stdout.write(f"Department: {wr_dept.name}")
        self.stdout.write(f"Status: {sprint.status}")
        self.stdout.write("")

        # Detect format type for concept/treatment disambiguation
        dept_state = sprint.get_department_state(str(wr_dept.id))
        format_type = dept_state.get("format_type", "standalone")
        self.stdout.write(f"Format type: {format_type}")

        # Find all lead_writer done tasks for this sprint, ordered chronologically
        from agents.models import AgentTask

        lead_tasks = list(
            AgentTask.objects.filter(
                sprint=sprint,
                agent__department=wr_dept,
                agent__agent_type="lead_writer",
                status=AgentTask.Status.DONE,
            )
            .order_by("completed_at")
            .select_related("agent")
        )

        if not lead_tasks:
            self.stdout.write(self.style.WARNING("No completed lead_writer tasks found in this sprint."))
            return

        self.stdout.write(f"Found {len(lead_tasks)} lead_writer task(s):\n")

        # Group tasks by stage
        stages_seen = {}
        for task in lead_tasks:
            cmd = task.command_name or ""
            stage = COMMAND_TO_STAGE.get(cmd)
            if not stage:
                self.stdout.write(self.style.WARNING(f"  Skipping unknown command: {cmd}"))
                continue

            # For series format, treatment stage uses "concept" display
            effective_display = STAGE_DISPLAY.get(stage, stage.replace("_", " ").title())
            if stage == "treatment" and format_type == "series":
                effective_display = "Concept"

            if stage not in stages_seen:
                stages_seen[stage] = {
                    "tasks": [],
                    "display": effective_display,
                }
            stages_seen[stage]["tasks"].append(task)

        if stage_filter:
            if stage_filter not in stages_seen:
                raise CommandError(
                    f"Stage '{stage_filter}' not found in sprint. " f"Available: {list(stages_seen.keys())}"
                )
            stages_seen = {stage_filter: stages_seen[stage_filter]}

        # Replay each stage
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()

        for stage, info in stages_seen.items():
            tasks = info["tasks"]
            display = info["display"]

            self.stdout.write(self.style.MIGRATE_HEADING(f"Stage: {stage} ({display})"))
            self.stdout.write(f"  {len(tasks)} lead_writer task(s)")

            deliverable = None

            for i, task in enumerate(tasks):
                report = task.report or ""
                if not report.strip():
                    self.stdout.write(self.style.WARNING(f"  [{i}] Empty report — skipping"))
                    continue

                if deliverable is None:
                    # First task — base deliverable (full text)
                    deliverable = report
                    self.stdout.write(f"  [{i}] Base deliverable ({len(report)} chars)")
                else:
                    # Subsequent tasks — apply section-based updates
                    deliverable = bp._apply_section_updates(deliverable, report)
                    self.stdout.write(
                        self.style.SUCCESS(f"  [{i}] Applied section updates ({len(report)} chars revised output)")
                    )

            if deliverable is None:
                self.stdout.write(self.style.WARNING(f"  No deliverable could be reconstructed for {stage}"))
                continue

            self.stdout.write(f"\n  Final deliverable: {len(deliverable)} chars")
            self.stdout.write(f"  Preview: {deliverable[:120].replace(chr(10), ' ')}")

            if dry_run:
                self.stdout.write(self.style.NOTICE("  [DRY RUN] Would update Document and Output"))
                continue

            # Update the Document
            from projects.models import Document, Output

            existing_doc = Document.objects.filter(
                department=wr_dept,
                doc_type="stage_deliverable",
                is_archived=False,
                title__startswith=f"{display} v",
            ).first()

            if existing_doc:
                old_len = len(existing_doc.content or "")
                existing_doc.content = deliverable
                existing_doc.save(update_fields=["content", "updated_at"])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Updated Document '{existing_doc.title}' ({old_len} -> {len(deliverable)} chars)"
                    )
                )
            else:
                # Determine version from task count
                version = len(tasks)
                title = f"{display} v{version} — Deliverable"
                doc = Document.objects.create(
                    department=wr_dept,
                    doc_type="stage_deliverable",
                    title=title,
                    content=deliverable,
                    sprint=sprint,
                    is_locked=True,
                )
                self.stdout.write(self.style.SUCCESS(f"  Created Document '{doc.title}'"))

            # Determine effective stage label for output
            effective_stage = stage
            if stage == "treatment" and format_type == "series":
                effective_stage = "concept"
            label = f"{effective_stage}:deliverable"

            Output.objects.update_or_create(
                sprint=sprint,
                department=wr_dept,
                label=label,
                defaults={
                    "title": f"{display} Deliverable",
                    "output_type": "markdown",
                    "content": deliverable,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"  Updated Output '{label}'"))

        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.NOTICE("Dry run complete. No changes written."))
        else:
            self.stdout.write(self.style.SUCCESS("Repair complete."))
