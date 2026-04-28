"""BooksToScrapeStrategy: scrape strategy for books.toscrape.com.

books.toscrape.com is a public scraping-practice sandbox. No headers, no
proxy, no response analysis are required, which makes this concrete strategy
the smallest example of the pattern in the codebase and a useful starting
point for understanding how the abstractions fit together.
"""
from src.utils.file_namer import BooksToScrapeNamer
from src.utils.paginators import BooksToScrapePaginator
from src.utils.strategies.aiohttp_scrape_strategy import AiohttpScrapeStrategy


class BooksToScrapeStrategy(AiohttpScrapeStrategy):
    def __init__(self, store_identification, fetch_type, fetch_query, start_url,
                 project_config, logger, singleton=False):
        super().__init__(
            retailer="books.toscrape.com",
            store_identification=store_identification,
            fetch_type=fetch_type,
            fetch_query=fetch_query,
            start_url=start_url,
            project_config=project_config,
            logger=logger,
            singleton=singleton,
        )

    def _build_paginator(self):
        return BooksToScrapePaginator()

    def _build_file_namer(self):
        return BooksToScrapeNamer(self.retailer, self.fetch_type,
                                  self.store_identification['store_id'])

    def get_headers(self) -> dict:
        return {}

    def get_proxy(self) -> str:
        return ""

    # ── High-level run_* entry points (aspirational stubs) ────────────────────────
    #
    # books.toscrape.com is the smallest example in the codebase and a
    # natural place to demonstrate run_search / run_product_lookup once
    # someone wires up category lookups against the site's URL scheme.
    # The pattern to follow is in WalmartScrapeStrategy.

    async def run_search(self, query: str) -> None:
        raise NotImplementedError(
            "BooksToScrapeStrategy.run_search is not yet implemented. "
            "Define how a category name resolves to a books.toscrape.com URL "
            "(see WalmartScrapeStrategy.run_search for the pattern)."
        )

    async def run_product_lookup(self) -> None:
        raise NotImplementedError(
            "BooksToScrapeStrategy.run_product_lookup is not yet implemented. "
            "Define where the candidate product URL list comes from "
            "(see WalmartScrapeStrategy.run_product_lookup for the pattern)."
        )
