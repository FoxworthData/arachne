import aiohttp
import asyncio
import random
import time

from logging import Logger

from tqdm.asyncio import tqdm
from typing import Any, Dict, List, Optional, Callable, Tuple

from src.utils.config_loader import ConfigLoader

class AiohttpFetcher:
    def __init__(
        self,
        store_identification,
        paginator,
        timeout: int = 30,
        max_retries: int = 1,
        max_concurrent_requests: int = 5,
        project_config: ConfigLoader = None,
        logger: Logger = None,
        get_headers: Optional[Callable[[], Dict[str, str]]] = None,
        get_proxy: Optional[Callable[[], Optional[str]]] = None,
        response_analyzer: Optional[
            Callable[[aiohttp.ClientResponse, str, Dict[str, str], Logger, dict, Any], Any]
        ] = None,
        check_store_identification: bool = True,
    ):
        self.store_identification = store_identification
        self.paginator = paginator
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_concurrent_requests = max_concurrent_requests
        self.project_config = project_config or ConfigLoader()
        self.logger = logger  # get module-specific logger
        self.get_headers = get_headers
        self.get_proxy = get_proxy
        self.response_analyzer = response_analyzer
        self.check_store_identification = check_store_identification

    async def fetch_page(
            self,
            session: aiohttp.ClientSession,
            url: str
    ) -> Optional[Dict[str, str]]:
        retries = 0
        last_error = None
        last_status_code = None
        headers = self.get_headers() if self.get_headers else {}
        proxy = self.get_proxy() if self.get_proxy else None

        while retries < self.max_retries:
            try:
                async with session.get(
                    url,
                    headers=headers,
                    proxy=proxy,
                    ssl=False,
                    timeout=self.timeout,
                    raise_for_status=True
                ) as response:

                    html = await response.text()

                    # Analyze the response if analyzer is provided
                    if self.response_analyzer:
                        is_valid = await self.response_analyzer(
                            response,
                            url,
                            headers,
                            self.logger,
                            self.store_identification,
                            self.check_store_identification
                        )
                        if not is_valid:
                            raise ValueError("Response failed analysis")

                    self.logger.debug(f"Fetched: {url}")
                    return {
                        'url': url,
                        'html': html,
                        'status_code': response.status,
                        'error': None
                    }
            except aiohttp.ClientResponseError as e:
                last_status_code = e.status
                last_error = str(e)
                self.logger.warning(f"Retry {retries}/{self.max_retries} for {url} due to {last_error}")
                await asyncio.sleep(2 ** retries)  # Exponential backoff
                retries += 1
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
                last_error = str(e)
                self.logger.warning(f"Retry {retries}/{self.max_retries} for {url} due to {last_error}")
                await asyncio.sleep(2 ** retries)  # Exponential backoff
                retries += 1

        self.logger.error(f"❌ Failed to fetch {url} after {self.max_retries} retries.")
        return {
            'url': url,
            'html': '',
            'status_code': last_status_code,
            'error': last_error
        }

    async def fetch_with_semaphore(
            self,
            semaphore: asyncio.Semaphore,
            session: aiohttp.ClientSession,
            url: str
    ) -> Optional[Dict[str, str]]:
        async with semaphore:
            return await self.fetch_page(session, url)

    async def fetch_all(
            self,
            url: str,
            on_result: Optional[Callable[[Dict[str, str], int], None]] = None,
            batch_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        results: List[Dict[str, Any]] = []

        config = self.project_config.get('fetcher', {})
        batch_size = batch_size or config.get('batch_size', 5)
        min_delay = config.get('delay_min_seconds', 1.5)
        max_delay = config.get('delay_max_seconds', 3.0)

        start_time = time.time()
        total_retries = 0

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10)) as session:
            async with semaphore:
                try:
                    first_page = await self.fetch_page(session, url)
                except Exception as e:
                    self.logger.error(f"❌ Failed to fetch first page: {e}")
                    error_result = {
                        "url": url,
                        "html": "",
                        "status_code": None,
                        "error": str(e)
                    }
                    if on_result:
                        on_result(error_result, 1)
                    else:
                        results.append(error_result)
                    return results if not on_result else []

            if not first_page:
                self.logger.error("Failed to fetch the first page.")
                return []

            if on_result:
                on_result(first_page, 1)
            else:
                results.append(first_page)

            urls = self.paginator.get_page_urls(first_page_url=url, html=first_page['html'])

            for i in range(1, len(urls), batch_size):
                batch_urls = urls[i:i + batch_size]
                tasks = [
                    asyncio.wait_for(self.fetch_with_semaphore(semaphore, session, u), timeout=60)
                    for u in batch_urls
                ]
                fetched = await tqdm.gather(*tasks, desc="Fetching pages", unit="page", initial=i + 1, total=len(urls))

                for j, result in enumerate(fetched):
                    if result:
                        if on_result:
                            on_result(result, i + j + 1)
                        else:
                            results.append(result)
                    else:
                        total_retries += 1

                if i + batch_size < len(urls):
                    delay = random.uniform(min_delay, max_delay)
                    self.logger.debug(f"Sleeping for {delay:.2f} seconds before next batch...")
                    await asyncio.sleep(delay)

        elapsed = time.time() - start_time
        self.logger.info(f"✅ Fetch complete in {elapsed:.2f} seconds. Total retries: {total_retries}")

        return results if not on_result else []

    async def fetch_singleton_urls(
            self,
            urls: List[str],
            on_result: Optional[Callable[[Dict[str, str], int], None]] = None
    ) -> List[Dict[str, Any]]:
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        results: List[Dict[str, Any]] = []
        start_time = time.time()

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10)) as session:
            tasks = []
            for index, url in enumerate(urls, start=1):
                async def fetch_single(url=url, index=index):
                    async with semaphore:
                        try:
                            result = await self.fetch_page(session, url)
                            if on_result:
                                on_result(result, index)
                            else:
                                results.append(result)
                        except Exception as e:
                            self.logger.error(f"❌ Failed to fetch {url}: {e}")
                            error_result = {
                                "url": url,
                                "html": "",
                                "status_code": None,
                                "error": str(e)
                            }
                            if on_result:
                                on_result(error_result, index)
                            else:
                                results.append(error_result)

                tasks.append(fetch_single())

            await asyncio.gather(*tasks)

        elapsed = time.time() - start_time
        self.logger.info(f"✅ Singleton fetch complete in {elapsed:.2f} seconds.")

        return results if not on_result else []

    #
    # async def retry_failed(self, urls: List[str]) -> List[Tuple[str, Any]]:
    #     if not urls:
    #         self.logger.info("No URLs to retry.")
    #         return []
    #
    #     sem = asyncio.Semaphore(self.max_concurrent_requests)
    #     results = []
    #
    #     async def fetch_with_retry(url):
    #         async with sem:
    #             try:
    #                 headers = self.get_headers() if self.get_headers else {}
    #                 proxy = self.get_proxy() if self.get_proxy else None
    #                 async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as client:
    #                     async with client.get(url, headers=headers, proxy=proxy) as response:
    #                         text = await response.text()
    #                         result = self.response_analyzer(
    #                             response, url, headers, self.logger, {}
    #                         ) if self.response_analyzer else {
    #                             "url": url,
    #                             "html": text,
    #                             "status_code": response.status,
    #                             "error": None
    #                         }
    #                         results.append((url, result))
    #             except Exception as e:
    #                 self.logger.warning(f"Retry failed for {url}: {e}")
    #                 results.append((url, {
    #                     "url": url,
    #                     "html": "",
    #                     "status_code": None,
    #                     "error": str(e)
    #                 }))
    #
    #     await asyncio.gather(*[fetch_with_retry(url) for url in urls])
    #     return results