from rest_framework import serializers

from agents.models import Agent
from projects.models import Department, Project


def _mask_value(val):
    """Mask sensitive config values, showing only a prefix."""
    if isinstance(val, str) and len(val) > 8:
        return val[:4] + "********"
    if isinstance(val, dict):
        return {k: _mask_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_mask_value(v) for v in val]
    return val


def _mask_config(config: dict) -> dict:
    """Mask all values in a config dict for safe API exposure."""
    if not config:
        return {}
    return {k: _mask_value(v) for k, v in config.items()}


class AgentSummarySerializer(serializers.ModelSerializer):
    pending_task_count = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    config = serializers.SerializerMethodField()
    effective_config = serializers.SerializerMethodField()
    config_source = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            "id",
            "name",
            "agent_type",
            "is_leader",
            "status",
            "instructions",
            "config",
            "enabled_commands",
            "internal_state",
            "pending_task_count",
            "tags",
            "effective_config",
            "config_source",
            "created_at",
        ]
        read_only_fields = fields

    def get_config(self, obj):
        return _mask_config(obj.config)

    def get_pending_task_count(self, obj):
        return obj.tasks.filter(status="awaiting_approval").count()

    def get_tags(self, obj):
        try:
            bp = obj.get_blueprint()
            return bp.tags
        except Exception:
            return []

    def get_effective_config(self, obj):
        merged = {}
        pc = obj.department.project.config
        if pc and pc.config:
            merged.update(pc.config)
        if obj.department.config:
            merged.update(obj.department.config)
        merged.update(obj.config)
        return _mask_config(merged)

    def get_config_source(self, obj):
        sources = {}
        pc = obj.department.project.config
        if pc and pc.config:
            for k in pc.config:
                sources[k] = "project"
        if obj.department.config:
            for k in obj.department.config:
                sources[k] = "department"
        for k in obj.config:
            sources[k] = "agent"
        return sources


class DepartmentDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="department_type", read_only=True)
    display_name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    agents = AgentSummarySerializer(many=True, read_only=True)
    config = serializers.JSONField(read_only=True)
    config_schema = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            "id",
            "department_type",
            "name",
            "display_name",
            "description",
            "agents",
            "config",
            "config_schema",
            "created_at",
        ]
        read_only_fields = fields

    def get_display_name(self, obj):
        return obj.name

    def get_description(self, obj):
        from agents.blueprints import DEPARTMENTS

        dept = DEPARTMENTS.get(obj.department_type)
        return dept["description"] if dept else ""

    def get_config_schema(self, obj):
        from agents.blueprints import get_department_config_schema

        return get_department_config_schema(obj.department_type)


class ProjectDetailSerializer(serializers.ModelSerializer):
    departments = DepartmentDetailSerializer(many=True, read_only=True)
    owner_email = serializers.CharField(source="owner.email", read_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "slug", "goal", "status", "owner_email", "departments", "created_at", "updated_at"]
        read_only_fields = fields
