from rest_framework import serializers

from agents.models import Agent


class AgentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ["instructions", "config", "auto_approve", "status"]

    def validate_config(self, value):
        agent = self.instance
        if agent:
            bp = agent.get_blueprint()
            errors = bp.validate_config(value)
            if errors:
                raise serializers.ValidationError(errors)
        return value
