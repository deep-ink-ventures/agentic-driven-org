from rest_framework import serializers

from projects.models import Output


class OutputListSerializer(serializers.ModelSerializer):
    created_by_task_summary = serializers.SerializerMethodField()

    class Meta:
        model = Output
        fields = [
            "id",
            "sprint",
            "department",
            "title",
            "label",
            "output_type",
            "url",
            "original_filename",
            "file_size",
            "content_type",
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


class OutputDetailSerializer(OutputListSerializer):
    """Detail view — includes full content."""

    class Meta(OutputListSerializer.Meta):
        fields = [*OutputListSerializer.Meta.fields, "content"]
