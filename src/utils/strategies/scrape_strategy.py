"""RetailerScrapeStrategy: ABC for retailer-specific scrape execution.

Implements the GoF Strategy pattern. Each concrete subclass encapsulates
the full set of behavior needed to scrape one retailer (header building,
proxy selection, pagination, response analysis, file naming, persistence,
session tracking, and target resolution) behind a uniform interface.

The orchestration layer (currently main.py via src/dispatch.py) holds a
RetailerScrapeStrategy reference and calls run_search / run_product_lookup
without knowing which retailer it's talking to. Each strategy owns its
own knowledge of how to translate a query into URLs, how to load
candidate product targets, and how to drive the underlying fetcher.

Retailer-specific operations that don't generalize across retailers
(e.g. Walmart's store-directory crawls) live as additional methods on
the relevant concrete subclass and are not part of this base contract.
The dispatcher checks for those methods explicitly via hasattr/isinstance
when needed.

The lower-level fetch_all and fetch_singleton_urls methods remain on the
ABC for the run_* methods to use internally and for advanced callers
that want to drive the fetcher directly with a specific URL list.
"""
from abc import ABC, abstractmethod
from typing import List


class RetailerScrapeStrategy(ABC):
    """Defines the operations every retailer scrape strategy must support."""

    # ── High-level entry points (recommended public surface) ─────────────────

    @abstractmethod
    async def run_search(self, query: str) -> None:
        """Resolve query into a search URL (or set of URLs) and fetch results.

        The strategy is responsible for translating query into whatever
        retailer-specific target representation it needs and then driving
        the underlying fetcher.
        """

    @abstractmethod
    async def run_product_lookup(self) -> None:
        """Resolve a list of product detail targets and fetch them.

        How targets are sourced is retailer-specific (a YAML file of
        canonical URLs, the output of a prior search run, an internal
        registry, etc.). The strategy owns that decision.
        """

    # ── Low-level fetch primitives (used internally and for advanced cases) ─

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
