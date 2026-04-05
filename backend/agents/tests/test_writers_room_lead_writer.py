"""Tests for Lead Writer agent and writers room pipeline refactor."""

from projects.models import Document


class TestStageDocTypes:
    def test_stage_deliverable_doc_type_exists(self):
        assert "stage_deliverable" in [c[0] for c in Document.DocType.choices]

    def test_stage_research_doc_type_exists(self):
        assert "stage_research" in [c[0] for c in Document.DocType.choices]

    def test_stage_critique_doc_type_exists(self):
        assert "stage_critique" in [c[0] for c in Document.DocType.choices]
