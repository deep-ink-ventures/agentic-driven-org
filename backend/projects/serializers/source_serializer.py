from rest_framework import serializers
from projects.models import Source


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ["id", "source_type", "original_filename", "url", "raw_content", "extracted_text", "word_count", "created_at"]
        read_only_fields = ["id", "extracted_text", "word_count", "created_at"]
