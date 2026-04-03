from rest_framework import serializers
from projects.models import Project
from projects.serializers.source_serializer import SourceSerializer


class ProjectSerializer(serializers.ModelSerializer):
    department_count = serializers.SerializerMethodField()
    agent_count = serializers.SerializerMethodField()
    source_count = serializers.SerializerMethodField()
    bootstrap_status = serializers.SerializerMethodField()
    sources = SourceSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "name", "goal", "status",
            "department_count", "agent_count", "source_count", "bootstrap_status",
            "sources",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def get_department_count(self, obj):
        return obj.departments.count()

    def get_agent_count(self, obj):
        from agents.models import Agent
        return Agent.objects.filter(department__project=obj).count()

    def get_source_count(self, obj):
        return obj.sources.count()

    def get_bootstrap_status(self, obj):
        """Latest bootstrap proposal status, or null if none."""
        proposal = obj.bootstrap_proposals.first()
        return proposal.status if proposal else None
