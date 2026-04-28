"""RetailerScrapeStrategy: ABC for retailer-specific scrape execution.

Implements the GoF Strategy pattern. Each concrete subclass encapsulates
the full set of behavior needed to scrape one retailer (header building,
proxy selection, pagination, response analysis, file naming, persistence,
and session tracking) behind a uniform interface.

The orchestration layer (currently main.py) holds a RetailerScrapeStrategy
reference and calls fetch_all / fetch_singleton_urls / get_session_summary
without knowing which retailer it's talking to.

Retailer-specific operations that don't generalize across retailers
(e.g. Walmart's store-directory crawl) live as additional methods on the
relevant concrete subclass and are not part of this base contract.
"""
from abc import ABC, abstractmethod
from typing import List


class RetailerScrapeStrategy(ABC):
    """Defines the operations every retailer scrape strategy must support."""

    @abstractmethod
    async def fetch_all(self, start_url: str) -> None:
        """Execute the primary paginated scrape starting from start_url.

        Used for search-style flows where pages are walked in sequence.
        """

    @abstractmethod
    async def fetch_singleton_urls(self, urls: List[str]) -> None:
        """Fetch a list of independent target URLs without pagination.

        Used for product-detail flows and other one-shot fetches.
        """

    @abstractmethod
    def get_session_summary(self) -> str:
        """Return a human-readable summary of the completed scrape session."""
