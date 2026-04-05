import uuid

from django.db import models
from jsonschema import ValidationError as JsonSchemaError
from jsonschema import validate


def get_proposal_json_schema() -> dict:
    """
    Generate a JSON Schema for bootstrap proposals based on the current
    blueprint registry. Valid department_types and agent_types come directly
    from the registered blueprints.
    """
    from agents.blueprints import DEPARTMENTS

    department_types = list(DEPARTMENTS.keys())

    # Build per-department agent type enums
    all_agent_types = set()
    for dept in DEPARTMENTS.values():
        all_agent_types.update(dept["workforce"].keys())

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["summary", "departments"],
        "properties": {
            "enriched_goal": {
                "type": "string",
                "description": "The user's original goal with misspellings fixed and formatted as clean markdown — same content, no additions, no removals",
            },
            "summary": {
                "type": "string",
                "minLength": 10,
                "description": "2-3 sentence analysis of the project for display purposes",
            },
            "departments": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["department_type", "agents"],
                    "properties": {
                        "department_type": {
                            "type": "string",
                            "enum": department_types,
                        },
                        "documents": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["title", "content"],
                                "properties": {
                                    "title": {"type": "string", "minLength": 1},
                                    "content": {"type": "string", "minLength": 1},
                                    "tags": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "default": [],
                                    },
                                },
                            },
                            "default": [],
                        },
                        "agents": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": ["name", "agent_type"],
                                "properties": {
                                    "name": {"type": "string", "minLength": 1},
                                    "agent_type": {
                                        "type": "string",
                                        "enum": sorted(all_agent_types),
                                    },
                                    "instructions": {"type": "string", "default": ""},
                                },
                            },
                        },
                    },
                },
            },
            "ignored_content": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_id": {"type": "string"},
                        "source_name": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                },
                "default": [],
            },
        },
    }


class BootstrapProposal(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="bootstrap_proposals",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    proposal = models.JSONField(
        null=True,
        blank=True,
        help_text="The proposed departments, agents, and documents — validated against get_proposal_json_schema().",
    )
    error_message = models.TextField(blank=True)
    token_usage = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def validate_proposal(self) -> list[str]:
        """Validate proposal JSON against the schema. Returns list of error strings."""
        if not self.proposal:
            return ["Proposal is empty"]
        schema = get_proposal_json_schema()
        try:
            validate(instance=self.proposal, schema=schema)
        except JsonSchemaError as e:
            return [f"{e.json_path}: {e.message}"]

        # Cross-validate: agent_types must be valid for their department
        from agents.blueprints import DEPARTMENTS

        errors = []
        for dept_data in self.proposal.get("departments", []):
            dept_type = dept_data.get("department_type")
            dept_config = DEPARTMENTS.get(dept_type)
            if not dept_config:
                continue
            valid_types = set(dept_config["workforce"].keys())
            for agent_data in dept_data.get("agents", []):
                if agent_data["agent_type"] not in valid_types:
                    errors.append(
                        f"Agent type '{agent_data['agent_type']}' is not available "
                        f"in department '{dept_type}'. Valid: {sorted(valid_types)}"
                    )
        return errors

    @classmethod
    def get_schema(cls) -> dict:
        """Return the JSON Schema for frontend rendering."""
        return get_proposal_json_schema()

    def __str__(self):
        return f"[{self.get_status_display()}] Bootstrap for {self.project.name}"
