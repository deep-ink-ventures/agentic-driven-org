from rest_framework import serializers

from projects.models import Output


class OutputListSerializer(serializers.ModelSerializer):
    """List view -- truncated content for performance."""

    created_by_task_summary = serializers.SerializerMethodField()

    class Meta:
        model = Output
        fields = [
            "id",
            "project",
            "department",
            "title",
            "label",
            "output_type",
            "content",
            "file_key",
            "original_filename",
            "file_size",
            "content_type",
            "version",
            "parent",
            "word_count",
            "created_by_task",
            "created_by_task_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_created_by_task_summary(self, obj) -> dict | None:
        if not obj.created_by_task_id:
            return None
        return {
            "id": str(obj.created_by_task_id),
            "exec_summary": obj.created_by_task.exec_summary if obj.created_by_task else "",
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Truncate content in list view to 500 chars
        if data.get("content") and len(data["content"]) > 500:
            data["content"] = data["content"][:500] + "..."
        # Never expose file_key directly
        data.pop("file_key", None)
        return data


class OutputDetailSerializer(OutputListSerializer):
    """Detail view -- full content, no truncation."""

    def to_representation(self, instance):
        # Skip the list serializer's truncation by calling ModelSerializer directly
        data = serializers.ModelSerializer.to_representation(self, instance)
        # Add created_by_task_summary
        data["created_by_task_summary"] = self.get_created_by_task_summary(instance)
        # Never expose file_key directly
        data.pop("file_key", None)
        return data
