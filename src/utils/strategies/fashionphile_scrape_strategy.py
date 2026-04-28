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
