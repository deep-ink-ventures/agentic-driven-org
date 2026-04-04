from rest_framework import serializers
from agents.models import AgentTask


class AgentTaskSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.name", read_only=True)
    agent_type = serializers.CharField(source="agent.agent_type", read_only=True)
    created_by_agent_name = serializers.SerializerMethodField()
    blocked_by_summary = serializers.SerializerMethodField()

    class Meta:
        model = AgentTask
        fields = [
            "id", "agent", "agent_name", "agent_type",
            "created_by_agent", "created_by_agent_name",
            "status", "auto_execute", "command_name",
            "blocked_by", "blocked_by_summary",
            "exec_summary", "step_plan", "report", "error_message",
            "proposed_exec_at", "scheduled_at", "started_at", "completed_at",
            "token_usage", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_created_by_agent_name(self, obj):
        return obj.created_by_agent.name if obj.created_by_agent else None

    def get_blocked_by_summary(self, obj):
        if obj.blocked_by:
            return obj.blocked_by.exec_summary[:100]
        return None
