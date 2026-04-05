from rest_framework import generics, permissions

from projects.models import Document
from projects.serializers.document_serializer import DocumentSerializer


class DocumentListView(generics.ListAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        department_id = self.kwargs["department_id"]
        qs = Document.objects.filter(department_id=department_id).order_by("-created_at")

        show_archived = self.request.query_params.get("show_archived", "").lower() == "true"
        if not show_archived:
            qs = qs.filter(is_archived=False)

        return qs
