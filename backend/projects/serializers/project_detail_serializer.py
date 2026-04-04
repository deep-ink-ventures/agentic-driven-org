from rest_framework import serializers
from projects.models import Project, Department
from agents.models import Agent


class AgentSummarySerializer(serializers.ModelSerializer):
    pending_task_count = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = ["id", "name", "agent_type", "is_leader", "is_active", "instructions", "config", "auto_actions", "internal_state", "pending_task_count", "created_at"]
        read_only_fields = fields

    def get_pending_task_count(self, obj):
        return obj.tasks.filter(status="awaiting_approval").count()


class DepartmentDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="department_type", read_only=True)
    display_name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    agents = AgentSummarySerializer(many=True, read_only=True)

    class Meta:
        model = Department
        fields = ["id", "department_type", "name", "display_name", "description", "agents", "created_at"]
        read_only_fields = fields

    def get_display_name(self, obj):
        return obj.name

    def get_description(self, obj):
        from agents.blueprints import DEPARTMENTS
        dept = DEPARTMENTS.get(obj.department_type)
        return dept["description"] if dept else ""


class ProjectDetailSerializer(serializers.ModelSerializer):
    departments = DepartmentDetailSerializer(many=True, read_only=True)
    owner_email = serializers.CharField(source="owner.email", read_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "goal", "status", "owner_email", "departments", "created_at", "updated_at"]
        read_only_fields = fields
