"""WalmartScrapeStrategy: scrape strategy for walmart.com.

Includes cookie-seeding integration. On the first fetch call, the strategy
runs a one-time seeding flow against walmart.com to harvest authentic
session cookies (anti-bot tokens, location cookies). All subsequent fetches
in the run use the resulting blended Cookie header. Without seeding, page-2+
requests reliably trip Walmart's bot detection — see
docs/walmart-cookie-seeding-port-plan.md for the diagnostic background.

The seeding is lazy and idempotent: callers don't need to invoke any prep
step explicitly, and concurrent first calls are serialized via an asyncio
lock so the seeding flow runs exactly once per strategy instance.
"""
import asyncio
from typing import List, Optional

from src.utils.browser_personas import BrowserPersona, BrowserPersonaChooser
from src.utils.cookie_utils import blend_cookies
from src.utils.file_namer import WalmartNamer
from src.utils.header_builders import (
    WalmartCookieSeedingHeaderBuilder,
    WalmartHeaderBuilder,
)
from src.utils.paginators import WalmartPaginator
from src.utils.proxy_builder_simple import get_proxies
from src.utils.response_analyzers import walmart_response_analyzer
from src.utils.strategies.aiohttp_scrape_strategy import AiohttpScrapeStrategy
from src.utils.walmart_cookie_seeder import WalmartCookieSeeder
from src.utils.yaml_util import (
    get_random_products,
    load_search_by_query,
    load_store_directories_by_state,
)


class WalmartScrapeStrategy(AiohttpScrapeStrategy):
    def __init__(
        self,
        store_identification,
        fetch_type,
        fetch_query,
        start_url,
        project_config,
        logger,
        singleton=False,
        browser_persona: Optional[BrowserPersona] = None,
    ):
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
        # Pin to a known-good Windows/Chrome persona unless the caller supplies
        # one explicitly. Persona-rotation policy is a future concern; matching
        # the prototype's known-working config is the priority for now.
        self._persona = browser_persona or BrowserPersonaChooser().get_persona(
            os_name='Windows', browser_name='Chrome'
        )
        self._seeded_headers: Optional[dict] = None
        self._seeding_lock = asyncio.Lock()

    def _build_paginator(self):
        return WalmartPaginator()

    def _build_file_namer(self):
        return WalmartNamer(self.retailer, self.fetch_type,
                            self.store_identification['store_id'])

    def _build_response_analyzer(self):
        return walmart_response_analyzer

    def get_headers(self) -> dict:
        # After successful seeding, every fetch uses the blended seeded headers.
        # Before seeding (and on un-seeded code paths, if any are added later),
        # fall back to the location-cookie-only header set.
        if self._seeded_headers is not None:
            return self._seeded_headers
        return WalmartHeaderBuilder(
            store_identification=self.store_identification
        ).build_headers()

    def get_proxy(self) -> str:
        return get_proxies(proxy_type='residential').get('http', '')

    # ── Cookie seeding ────────────────────────────────────────────────────────

    async def _ensure_seeded(self) -> None:
        """Run the cookie-seeding flow exactly once per strategy instance.

        Idempotent and concurrency-safe: a second caller that arrives while
        seeding is in progress will await the lock, then see _seeded_headers
        already set and return immediately.

        Raises RuntimeError if seeding fails. The strategy never silently
        falls back to un-seeded fetches — pages 2+ would just fail bot
        detection a few seconds later anyway.
        """
        if self._seeded_headers is not None:
            return

        async with self._seeding_lock:
            if self._seeded_headers is not None:
                return

            self.logger.info(
                f"[SEEDING] Starting Walmart cookie seeding "
                f"(persona: {self._persona.persona_id})"
            )

            header_builder = WalmartCookieSeedingHeaderBuilder(
                store_identification=self.store_identification,
                browser_persona=self._persona,
            )
            seeder = WalmartCookieSeeder(
                retailer_store_id=self.store_identification['store_id'],
                initial_headers=header_builder.initial_headers,
                initial_cookies=header_builder.initial_cookies,
                proxies=get_proxies(proxy_type='residential'),
                logger=self.logger,
            )

            harvested = await seeder.get_seeded_cookies(browser_persona=self._persona)

            if not harvested.get('success'):
                raise RuntimeError(
                    f"Walmart cookie seeding failed; aborting scrape. "
                    f"Result: {harvested}"
                )

            blended_cookie = blend_cookies(
                header_builder.initial_cookies, harvested['cookies']
            )
            seeded_headers = harvested['headers']
            seeded_headers['cookie'] = blended_cookie

            self._seeded_headers = seeded_headers
            self.logger.info("[SEEDING] Walmart cookie seeding complete.")

    # ── RetailerScrapeStrategy interface (override for lazy seeding) ─────────

    async def fetch_all(self, start_url: str) -> None:
        await self._ensure_seeded()
        await super().fetch_all(start_url)

    async def fetch_singleton_urls(self, urls: List[str]) -> None:
        await self._ensure_seeded()
        await super().fetch_singleton_urls(urls)

    # ── High-level run_* entry points ────────────────────────────────────────

    async def run_search(self, query: str) -> None:
        """Resolve query against the Walmart search YAML, then drive fetch_all.

        The YAML stores canonical search URLs by query name. After resolving,
        this method updates the strategy's bookkeeping fields (fetch_query,
        start_url) so the FetcherSession summary reflects what actually ran.
        """
        search_config = load_search_by_query(query=query)
        self.logger.info(search_config)

        resolved_query = search_config.get('query')
        first_page_search_url = search_config.get('search_url')

        # Update bookkeeping so session summary reflects the resolved targets.
        self.fetch_query = resolved_query
        self.start_url = first_page_search_url
        self.session.fetch_query = resolved_query
        self.session.url = first_page_search_url

        self.logger.info(
            f"Retailer: {self.retailer} Store: {self.store_identification['store_id']} "
            f"Fetch Type: {self.fetch_type} Query: {resolved_query}"
        )
        await self.fetch_all(first_page_search_url)

    async def run_product_lookup(self) -> None:
        """Pick a random sample of canonical product URLs and fetch them.

        Targets come from the Walmart_products.yaml fixture. Sampling rather
        than walking the full list keeps demo runs short.
        """
        random_entries = get_random_products(n=100)
        urls = [entry.get('canonical_url') for entry in random_entries]

        self.logger.info(
            f"Retailer: {self.retailer} Store: {self.store_identification['store_id']} "
            f"Fetch Type: {self.fetch_type} Sample size: {len(urls)}"
        )
        await self.fetch_singleton_urls(urls)

    async def run_store_directory(self, query: str) -> None:
        """Fetch a single Walmart store-directory page for query (a state code)."""
        url = f"https://www.walmart.com/store-directory/{query.lower()}"

        self.fetch_query = query
        self.start_url = url
        self.session.fetch_query = query
        self.session.url = url

        self.logger.info(
            f"Retailer: {self.retailer} Store: {self.store_identification['store_id']} "
            f"Fetch Type: {self.fetch_type} Query: {query}"
        )
        await self.fetch_singleton_urls([url])

    async def run_store_directory_by_state(self, state_code: str) -> None:
        """Fetch every per-city store directory for the given state code.

        The YAML lookup returns a list of city dicts with `url` fields; this
        method collapses them into a single fetch_singleton_urls call so the
        strategy seeds cookies once and shares the session across all cities.
        """
        city_entries = load_store_directories_by_state(state_code)
        city_urls = [entry.get('url') for entry in city_entries if entry.get('url')]

        self.fetch_query = state_code
        self.start_url = None
        self.session.fetch_query = state_code

        self.logger.info(
            f"Retailer: {self.retailer} Store: {self.store_identification['store_id']} "
            f"Fetch Type: {self.fetch_type} State: {state_code} "
            f"Cities: {len(city_urls)}"
        )
        await self.fetch_singleton_urls(city_urls)
