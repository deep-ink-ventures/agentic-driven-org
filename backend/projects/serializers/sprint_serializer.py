from rest_framework import serializers

from projects.models import Sprint


class SprintSerializer(serializers.ModelSerializer):
    department_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
    )
    source_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        default=list,
    )
    progress_from_sprint_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        default=list,
    )
    departments = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()
    outputs = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Sprint
        fields = [
            "id",
            "project",
            "text",
            "status",
            "completion_summary",
            "departments",
            "department_ids",
            "source_ids",
            "progress_from_sprint_ids",
            "task_count",
            "outputs",
            "created_by_email",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "status",
            "completion_summary",
            "created_by_email",
            "created_at",
            "updated_at",
            "completed_at",
        ]

    def create(self, validated_data):
        validated_data.pop("department_ids", None)
        validated_data.pop("source_ids", None)
        validated_data.pop("progress_from_sprint_ids", None)
        return super().create(validated_data)

    def get_departments(self, obj):
        return [
            {"id": str(d.id), "department_type": d.department_type, "display_name": d.display_name}
            for d in obj.departments.all()
        ]

    def get_task_count(self, obj):
        return obj.tasks.count()

    def get_outputs(self, obj):
        return [
            {
                "id": str(o.id),
                "department": str(o.department_id),
                "title": o.title,
                "label": o.label,
                "output_type": o.output_type,
                "content": o.content,
                "url": o.url,
                "original_filename": o.original_filename,
                "file_size": o.file_size,
                "updated_at": o.updated_at.isoformat() if o.updated_at else None,
            }
            for o in obj.outputs.all()
        ]
