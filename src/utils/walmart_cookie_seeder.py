import logging
import re
import copy

import aiohttp
import time
from typing import Dict, Any

from tenacity import retry, stop_after_attempt, retry_if_exception_type, before_sleep_log, Retrying, RetryError

from src.utils.browser_personas import BrowserPersona


class StoreIdMismatchError(Exception):
    """Custom exception for when store ID doesn't match"""
    pass


class StoreIdNotFoundError(Exception):
    """Custom exception for when store ID pattern is not found"""
    pass


class NonSuccessStatusError(Exception):
    """Custom exception for non-200 status codes"""
    pass


class WalmartCookieSeeder:
    """
    Real cookie seeding system that harvests authentic cookies from actual Walmart sessions.
    This demonstrates how to properly seed browser fingerprints with genuine session data.
    """

    def __init__(self, retailer_store_id: str, initial_headers: dict, initial_cookies: dict, proxies, logger):
        self.retailer_store_id = retailer_store_id
        self.initial_headers = initial_headers
        self.initial_cookies = initial_cookies
        self.proxies = proxies
        self.logger = logger
        self.session_cache = {}  # In production, this would be Redis/database
        self.cache_ttl = 3600  # 1 hour TTL for harvested cookies

    async def harvest_walmart_seeded_values(self, browser_persona: BrowserPersona):
        """Harvest Walmart seeded values with retry logic using instance logger"""

        try:
            # Use Retrying context manager to access self.logger
            for attempt in Retrying(
                    stop=stop_after_attempt(10),
                    retry=retry_if_exception_type((StoreIdMismatchError, StoreIdNotFoundError, NonSuccessStatusError)),
                    before_sleep=before_sleep_log(self.logger, logging.INFO),
                    reraise=True
            ):
                with attempt:
                    return await self._perform_harvest_attempt(browser_persona)

        except RetryError as e:
            self.logger.error(
                f"❌ [Harvest] Cookie harvesting failed after all retry attempts: {e.last_attempt.exception()}")
            return {"success": False, "cookies": {}, "headers": {}}
        except Exception as e:
            # Catch any other unexpected exceptions
            self.logger.error(f"❌ [Harvest] Unexpected error during cookie harvesting: {e}")
            return {"success": False, "cookies": {}, "headers": {}}

    async def _perform_harvest_attempt(self, browser_persona: BrowserPersona):

        self.logger.info("[COOKIE SEEDING] Starting cookie seeding attempt...")

        # Prepare proxy configuration for aiohttp (convert from requests format if needed)
        proxy_url = None
        if self.proxies:
            # Handle different proxy formats
            if isinstance(self.proxies, dict):
                # requests format: {'http': 'http://proxy:port', 'https': 'https://proxy:port'}
                proxy_url = self.proxies.get('https') or self.proxies.get('http')
            elif isinstance(self.proxies, str):
                # Direct URL format
                proxy_url = self.proxies

        # Create aiohttp ClientSession with appropriate configuration
        connector = aiohttp.TCPConnector(ssl=False)  # Equivalent to verify=False
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                cookies=self.initial_cookies  # aiohttp handles cookies dict directly
        ) as session:

            # Make initial request to Walmart homepage to harvest session cookies
            self.logger.info("--- HEADERS AIOHTTP IS SENDING to www.walmart.com for seeding ---")
            for key, value in self.initial_headers.items():
                self.logger.info(f"  {key}: {value}")
            self.logger.info("-------------------------------------")

            async with session.get(
                    "https://www.walmart.com",
                    headers=self.initial_headers,
                    proxy=proxy_url  # aiohttp uses single proxy parameter
            ) as response:

                self.logger.info(f'[COOKIE SEEDING] https://www.walmart.com response code: {response.status}')
                self.logger.info(f'[COOKIE SEEDING] https://www.walmart.com response reason: {response.reason}')

                if response.status != 200:
                    self.logger.warning(
                        f"[COOKIE SEEDING] Failed with status code: {response.status}. Reason: {response.reason}")
                    raise NonSuccessStatusError(f"Status code: {response.status}, Reason: {response.reason}")

                # Get response text (aiohttp requires await)
                file_text = await response.text()

                self.logger.info(f"[COOKIE SEEDING] Searching response text for storeId:{self.retailer_store_id}...")
                match = re.search(r'"storeId":"(\d+)"', file_text)

                if not match:
                    self.logger.warning("[COOKIE SEEDING] No 'storeId' pattern found in the HTML response.")
                    raise StoreIdNotFoundError("No 'storeId' pattern found in the HTML response")

                found_id = match.group(1)  # Extracts the number from the pattern
                self.logger.info(f"[COOKIE SEEDING] ******* Found store ID '{found_id}'.")

                if found_id != self.retailer_store_id:
                    self.logger.warning(
                        f"[COOKIE SEEDING] Found Store ID '{found_id}' does not match the specified retailer_store_id '{self.retailer_store_id}'.")
                    raise StoreIdMismatchError(
                        f"Found Store ID '{found_id}' does not match specified '{self.retailer_store_id}'")

                self.logger.info(
                    f"[COOKIE SEEDING] Store ID '{found_id}' matches the specified retailer_store_id '{self.retailer_store_id}'.")

                # Convert aiohttp cookies to dict format for harvesting
                response_cookies = {}
                for cookie in session.cookie_jar:
                    response_cookies[cookie.key] = cookie.value

                harvested_cookies = await self.harvest_cookies(response_cookies)

                # Create properly seeded headers (deep copy to avoid mutating original)
                seeded_headers = copy.deepcopy(self.initial_headers)
                seeded_headers['x-session-harvested'] = 'true'
                seeded_headers['x-harvest-time'] = str(int(time.time()))
                seeded_headers['x-persona-id'] = browser_persona.persona_id

                # Cache the harvested cookies AND headers with TTL
                cache_key = f"walmart_{browser_persona.persona_id}_{int(time.time() / self.cache_ttl)}"
                self.session_cache[cache_key] = {
                    "cookies": harvested_cookies,
                    "headers": seeded_headers,  # Cache the seeded headers
                    "harvested_at": time.time(),
                    "persona_id": browser_persona.persona_id
                }

                return {
                    "success": True,
                    "cookies": harvested_cookies,
                    "headers": seeded_headers,
                    "harvested_at": time.time(),
                    "cache_key": cache_key
                }

    async def harvest_cookies(self, all_context_cookies):
        harvested_cookies = {}
        cookies_to_harvest = ['_pxvid', 'vtc', '_m', 'io_id', 'abqme',
                              'AID', '_pxhd', 'pxcts', 'wmlh', '_astc',
                              'userAppVersion', 'akavpau_p1', 'bstc', '__cf_bm', 'com.wm.reflector',
                              'akavpau_p2', 'bm_mi', 'ak_bmsc', 'if_id', 'bm_sv', '_px3',
                              '_pxde', ]
        for cookie in all_context_cookies:
            if cookie in cookies_to_harvest:
                harvested_cookies[cookie] = all_context_cookies[cookie]
        return harvested_cookies

    async def get_seeded_cookies(self, browser_persona: BrowserPersona) -> Dict[str, Any]:
        """
        Get authentic seeded cookies, either from cache or by harvesting fresh ones.
        """
        # Check cache first
        cache_key = f"walmart_{browser_persona.persona_id}_{int(time.time() / self.cache_ttl)}"

        if cache_key in self.session_cache:
            cached_data = self.session_cache[cache_key]
            age = time.time() - cached_data["harvested_at"]
            if age < self.cache_ttl:
                self.logger.info(f"🎯 [Cache Hit] Using cached cookies (age: {age:.0f}s)")

                # Return cached headers with additional cache metadata
                cached_headers = copy.deepcopy(cached_data["headers"])
                cached_headers['x-session-cached'] = 'true'
                cached_headers['x-cache-age'] = str(int(age))

                return {
                    "success": True,
                    "cookies": cached_data["cookies"],
                    "headers": cached_headers,
                    "harvested_at": cached_data["harvested_at"],
                    "cache_key": cache_key
                }

        # Cache miss or expired - harvest fresh cookies
        return await self.harvest_walmart_seeded_values(browser_persona)