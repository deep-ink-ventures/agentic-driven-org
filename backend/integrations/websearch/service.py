"""
Web search service. Wraps web search for consistency.
"""

import logging

logger = logging.getLogger(__name__)


def search(query: str, num_results: int = 10) -> list[dict]:
    logger.info("Web search: query='%s', num_results=%d", query, num_results)
    return []
