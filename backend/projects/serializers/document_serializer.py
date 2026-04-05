from rest_framework import serializers

from projects.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    consolidated_into = serializers.UUIDField(source="consolidated_into_id", read_only=True, allow_null=True)
    consolidated_from_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "content",
            "department",
            "doc_type",
            "document_type",
            "is_archived",
            "consolidated_into",
            "consolidated_from_count",
            "sprint",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_consolidated_from_count(self, obj) -> int:
        return obj.consolidated_from.count()
