from rest_framework import serializers

from projects.models import Briefing


class BriefingAttachmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    original_filename = serializers.CharField()
    file_format = serializers.CharField()
    file_size = serializers.IntegerField()
    word_count = serializers.IntegerField()


class BriefingSerializer(serializers.ModelSerializer):
    attachments = BriefingAttachmentSerializer(many=True, read_only=True)
    task_count = serializers.IntegerField(read_only=True, default=0)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Briefing
        fields = [
            "id",
            "project",
            "department",
            "title",
            "content",
            "status",
            "attachments",
            "task_count",
            "created_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "project", "created_at", "updated_at"]
