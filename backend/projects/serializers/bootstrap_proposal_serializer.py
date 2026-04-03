from rest_framework import serializers
from projects.models import BootstrapProposal


class BootstrapProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = BootstrapProposal
        fields = ["id", "status", "proposal", "error_message", "token_usage", "created_at", "updated_at"]
        read_only_fields = fields
