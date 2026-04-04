from rest_framework import serializers
from agents.models import Agent


class AgentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ["instructions", "config", "auto_actions", "is_active"]

    def validate_config(self, value):
        agent = self.instance
        if agent:
            bp = agent.get_blueprint()
            errors = bp.validate_config(value)
            if errors:
                raise serializers.ValidationError(errors)
        return value

    def validate_auto_actions(self, value):
        agent = self.instance
        if agent:
            bp = agent.get_blueprint()
            errors = bp.validate_auto_actions(value)
            if errors:
                raise serializers.ValidationError(errors)
        return value
