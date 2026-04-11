from rest_framework import serializers

from projects.models import SprintNote


class SprintNoteSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    source_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        default=list,
    )
    sources = serializers.SerializerMethodField()

    class Meta:
        model = SprintNote
        fields = ["id", "text", "user_email", "source_ids", "sources", "created_at"]
        read_only_fields = ["id", "user_email", "created_at"]

    def get_sources(self, obj):
        return [
            {
                "id": str(s.id),
                "original_filename": s.original_filename,
                "source_type": s.source_type,
            }
            for s in obj.sources.all()
        ]

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Text cannot be empty.")
        return value

    def create(self, validated_data):
        validated_data.pop("source_ids", None)
        return super().create(validated_data)
