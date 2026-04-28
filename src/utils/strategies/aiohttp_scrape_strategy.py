"""AiohttpScrapeStrategy: shared base for retailers using the AiohttpFetcher.

Several retailers (Walmart, Fashionphile, books.toscrape.com) share the same
high-level shape: HTML pages fetched via aiohttp, paginated, response-analyzed,
saved as gzipped HTML, with per-fetch tracking. This base class implements
that common flow as a Template Method, with retailer-specific decisions
exposed as overridable hooks.

Retailers that diverge from this shape (e.g. Aldi, which uses curl_cffi for
GraphQL) subclass RetailerScrapeStrategy directly and do not inherit from
this class.
"""
import time
from typing import List, Tuple

from src.utils.fetchers import AiohttpFetcher
from src.utils.fetcher_tracking import FetcherSession, FetchedFile
from src.utils.file_storage import FileStorage
from src.utils.strategies.scrape_strategy import RetailerScrapeStrategy


class AiohttpScrapeStrategy(RetailerScrapeStrategy):
    """Template Method base for aiohttp-based HTML retailer strategies.

    Subclasses must define the retailer's name, header builder, paginator,
    file namer, response analyzer, and proxy resolution by overriding the
    abstract hook methods below. The shared lifecycle (fetcher construction,
    result handling, session bookkeeping) lives here.
    """

    def __init__(
        self,
        retailer: str,
        store_identification: dict,
        fetch_type: str,
        fetch_query: str,
        start_url: str,
        project_config,
        logger,
        singleton: bool = False,
    ):
        self.retailer = retailer
        self.store_identification = store_identification
        self.fetch_type = fetch_type
        self.fetch_query = fetch_query
        self.start_url = start_url
        self.project_config = project_config
        self.logger = logger
        self.singleton = singleton

        self.file_storage = FileStorage(retailer, project_config, logger)
        self.paginator = None if singleton else self._build_paginator()
        self.file_namer = self._build_file_namer()
        self.response_analyzer = self._build_response_analyzer()

        self.fetcher = AiohttpFetcher(
            store_identification=store_identification,
            paginator=self.paginator,
            project_config=project_config,
            logger=logger,
            get_headers=self.get_headers,
            get_proxy=self.get_proxy,
            response_analyzer=self.response_analyzer,
            check_store_identification=fetch_type not in [
                'store-directory', 'store-directory-by-state'
            ],
            max_retries=5,
        )

        self.session = FetcherSession(
            retailer=retailer,
            store_id=store_identification['store_id'],
            fetch_type=fetch_type,
            fetch_query=fetch_query,
            url=start_url,
        )

    # ── Hooks subclasses must implement ──────────────────────────────────────

    def _build_paginator(self):
        """Return the paginator instance for this retailer."""
        raise NotImplementedError

    def _build_file_namer(self):
        """Return the file namer instance for this retailer."""
        raise NotImplementedError

    def _build_response_analyzer(self):
        """Return the async response analyzer callable, or None if unused."""
        return None

    def get_headers(self) -> dict:
        """Return the headers to use for the next fetch."""
        raise NotImplementedError

    def get_proxy(self) -> str:
        """Return the proxy URL, or empty string if no proxy."""
        return ""

    # ── Shared implementation ─────────────────────────────────────────────────

    def handle_result(self, result: dict, page_num: int, is_retry: bool = False):
        filename = None
        if not result['error']:
            filename = self.file_namer.get_html_filename(self.fetch_query, page_num=page_num)
            self.file_storage.save_html(filename, result["html"], fetch_type=self.fetch_type)

        fetched_file = FetchedFile(
            retailer=self.retailer,
            store_id=self.store_identification['store_id'],
            fetch_type=self.fetch_type,
            fetch_query=self.fetch_query,
            url=result["url"],
            filename=filename,
            size=len(result["html"]),
            page_number=page_num,
            fetched_time=time.time(),
            response_status_code=result.get("status_code"),
            blocked=False,
            success=result.get("status_code") == 200,
            message=result.get("error"),
        )

        if is_retry:
            fetched_file.retry_of_url = result["url"]

        self.session.add_fetched_file(fetched_file)

    def handle_retry_results(self, retry_results: List[Tuple[str, dict]]):
        for url, result in retry_results:
            self.handle_result(result, page_num=-1, is_retry=True)

    # ── RetailerScrapeStrategy interface ─────────────────────────────────────

    async def fetch_all(self, start_url: str) -> None:
        self.logger.info(f"Fetching paginated results from start URL: {start_url}")
        await self.fetcher.fetch_all(start_url, self.handle_result)

    async def fetch_singleton_urls(self, urls: List[str]) -> None:
        self.logger.info(f"Fetching {len(urls)} singleton URLs...")
        await self.fetcher.fetch_singleton_urls(urls, self.handle_result)

    def get_session_summary(self) -> str:
        self.session.close()
        return self.session.to_string()
