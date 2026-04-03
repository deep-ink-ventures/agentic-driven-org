from rest_framework import serializers
from projects.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    department_count = serializers.SerializerMethodField()
    agent_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ["id", "name", "goal", "department_count", "agent_count", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_department_count(self, obj):
        return obj.departments.count()

    def get_agent_count(self, obj):
        from agents.models import Agent
        return Agent.objects.filter(department__project=obj).count()
