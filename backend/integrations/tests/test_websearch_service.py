"""Tests for the web search service."""


class TestWebSearch:
    def test_search_returns_list(self):
        """search() returns a list."""
        from integrations.websearch.service import search

        results = search("test query")
        assert isinstance(results, list)

    def test_search_empty_results(self):
        """search() currently returns empty list (stub implementation)."""
        from integrations.websearch.service import search

        results = search("test query")
        assert results == []

    def test_search_accepts_num_results_param(self):
        """search() accepts optional num_results parameter without error."""
        from integrations.websearch.service import search

        results = search("specific search term", num_results=5)
        assert isinstance(results, list)

    def test_search_empty_query(self):
        """search() handles empty query string."""
        from integrations.websearch.service import search

        results = search("")
        assert isinstance(results, list)

    def test_search_default_num_results(self):
        """search() has default num_results of 10."""
        import inspect

        from integrations.websearch.service import search

        sig = inspect.signature(search)
        assert sig.parameters["num_results"].default == 10
