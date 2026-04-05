"""Tests for projects.prompts module."""

from projects.prompts import BOOTSTRAP_SYSTEM_PROMPT, build_bootstrap_user_message


class TestBuildBootstrapUserMessage:
    def _make_sources(self, texts=None):
        if texts is None:
            texts = ["Source text content"]
        return [
            {
                "id": f"src-{i}",
                "name": f"source_{i}.txt",
                "source_type": "file",
                "text": t,
            }
            for i, t in enumerate(texts)
        ]

    def _make_departments(self):
        return [
            {
                "slug": "marketing",
                "name": "Marketing",
                "description": "Marketing management",
                "workforce": [
                    {"slug": "twitter", "name": "Twitter Agent", "description": "Posts tweets"},
                    {"slug": "reddit", "name": "Reddit Agent", "description": "Posts on Reddit"},
                ],
            },
        ]

    def test_includes_project_name(self):
        msg = build_bootstrap_user_message("My Project", "Some goal", self._make_sources(), self._make_departments())
        assert "# Project: My Project" in msg

    def test_includes_goal(self):
        msg = build_bootstrap_user_message("P", "Build a product", self._make_sources(), self._make_departments())
        assert "<project_goal>" in msg
        assert "Build a product" in msg

    def test_includes_sources(self):
        sources = self._make_sources(["Content A", "Content B"])
        msg = build_bootstrap_user_message("P", "G", sources, self._make_departments())
        assert "Content A" in msg
        assert "Content B" in msg
        assert "source_0.txt" in msg
        assert "source_1.txt" in msg

    def test_includes_available_departments(self):
        msg = build_bootstrap_user_message("P", "G", self._make_sources(), self._make_departments())
        assert "## Available Departments" in msg
        assert "marketing" in msg
        assert "**twitter**" in msg
        assert "Posts tweets" in msg
        assert "**reddit**" in msg

    def test_long_text_not_truncated(self):
        long_text = "x" * 15000
        sources = self._make_sources([long_text])
        msg = build_bootstrap_user_message("P", "G", sources, self._make_departments())
        assert "[... truncated ...]" not in msg
        assert "x" * 15000 in msg

    def test_short_text_not_truncated(self):
        sources = self._make_sources(["short text"])
        msg = build_bootstrap_user_message("P", "G", sources, self._make_departments())
        assert "[... truncated ...]" not in msg
        assert "short text" in msg

    def test_all_sections_present(self):
        msg = build_bootstrap_user_message("P", "G", self._make_sources(), self._make_departments())
        assert "# Project:" in msg
        assert "<project_goal>" in msg
        assert "## Available Departments" in msg
        assert "## Source Materials" in msg
        assert "Respond with JSON only." in msg

    def test_source_metadata_in_header(self):
        sources = self._make_sources(["text"])
        msg = build_bootstrap_user_message("P", "G", sources, self._make_departments())
        assert 'type="file"' in msg
        assert 'id="src-0"' in msg


class TestBootstrapSystemPrompt:
    def test_is_nonempty_string(self):
        assert isinstance(BOOTSTRAP_SYSTEM_PROMPT, str)
        assert len(BOOTSTRAP_SYSTEM_PROMPT) > 100

    def test_mentions_json(self):
        assert "JSON" in BOOTSTRAP_SYSTEM_PROMPT

    def test_mentions_departments(self):
        assert "departments" in BOOTSTRAP_SYSTEM_PROMPT

    def test_mentions_department_type(self):
        assert "department_type" in BOOTSTRAP_SYSTEM_PROMPT
