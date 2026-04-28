"""FashionphileScrapeStrategy: scrape strategy for fashionphile.com."""
from src.utils.file_namer import FashionphileFileNamer
from src.utils.header_builders import FashionphileHeaderBuilder
from src.utils.paginators import BooksToScrapePaginator
from src.utils.proxy_builder_simple import get_proxies
from src.utils.response_analyzers import fashionphile_response_analyzer
from src.utils.strategies.aiohttp_scrape_strategy import AiohttpScrapeStrategy


class FashionphileScrapeStrategy(AiohttpScrapeStrategy):
    def __init__(self, store_identification, fetch_type, fetch_query, start_url,
                 project_config, logger, singleton=False):
        super().__init__(
            retailer="Fashionphile",
            store_identification=store_identification,
            fetch_type=fetch_type,
            fetch_query=fetch_query,
            start_url=start_url,
            project_config=project_config,
            logger=logger,
            singleton=singleton,
        )

    def _build_paginator(self):
        # Fashionphile reuses the BooksToScrape paginator pattern; replace if a
        # Fashionphile-specific paginator is introduced.
        return BooksToScrapePaginator()

    def _build_file_namer(self):
        return FashionphileFileNamer(self.retailer, self.fetch_type,
                                     self.store_identification['store_id'])

    def _build_response_analyzer(self):
        return fashionphile_response_analyzer

    def get_headers(self) -> dict:
        return FashionphileHeaderBuilder(
            store_identification=self.store_identification
        ).build_headers()

    def get_proxy(self) -> str:
        return get_proxies(proxy_type='residential').get('http', '')

    # ── High-level run_* entry points (aspirational stubs) ────────────────────────
    #
    # FashionphileScrapeStrategy was promoted into the strategy hierarchy as
    # part of the RetailerBundle refactor, but its full search/product flow
    # has never been wired through main.py. The header builder, namer, and
    # response analyzer all exist; what's missing is the target-resolution
    # logic (where do canonical search URLs come from? where does the
    # product list come from?). Wire those in when Fashionphile becomes a
    # real driving target on this branch.

    async def run_search(self, query: str) -> None:
        raise NotImplementedError(
            "FashionphileScrapeStrategy.run_search is not yet implemented. "
            "Define how a query name resolves to a Fashionphile search URL "
            "(see WalmartScrapeStrategy.run_search for the pattern)."
        )

    async def run_product_lookup(self) -> None:
        raise NotImplementedError(
            "FashionphileScrapeStrategy.run_product_lookup is not yet implemented. "
            "Define where the candidate product URL list comes from "
            "(see WalmartScrapeStrategy.run_product_lookup for the pattern)."
        )
