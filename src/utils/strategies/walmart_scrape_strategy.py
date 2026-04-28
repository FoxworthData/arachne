"""WalmartScrapeStrategy: scrape strategy for walmart.com."""
from src.utils.file_namer import WalmartNamer
from src.utils.header_builders import WalmartHeaderBuilder
from src.utils.paginators import WalmartPaginator
from src.utils.proxy_builder_simple import get_proxies
from src.utils.response_analyzers import walmart_response_analyzer
from src.utils.strategies.aiohttp_scrape_strategy import AiohttpScrapeStrategy


class WalmartScrapeStrategy(AiohttpScrapeStrategy):
    def __init__(self, store_identification, fetch_type, fetch_query, start_url,
                 project_config, logger, singleton=False):
        super().__init__(
            retailer="Walmart",
            store_identification=store_identification,
            fetch_type=fetch_type,
            fetch_query=fetch_query,
            start_url=start_url,
            project_config=project_config,
            logger=logger,
            singleton=singleton,
        )

    def _build_paginator(self):
        return WalmartPaginator()

    def _build_file_namer(self):
        return WalmartNamer(self.retailer, self.fetch_type,
                            self.store_identification['store_id'])

    def _build_response_analyzer(self):
        return walmart_response_analyzer

    def get_headers(self) -> dict:
        return WalmartHeaderBuilder(
            store_identification=self.store_identification
        ).build_headers()

    def get_proxy(self) -> str:
        return get_proxies(proxy_type='residential').get('http', '')
