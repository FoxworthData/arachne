import os
import time
from typing import List, Tuple

from src.utils.fetchers import AiohttpFetcher
from src.utils.paginators import BooksToScrapePaginator, WalmartPaginator
from src.utils.fetcher_tracking import FetcherSession, FetchedFile
from src.utils.file_namer import BooksToScrapeNamer, WalmartNamer
from src.utils.file_storage import FileStorage
from src.utils.header_builders import WalmartHeaderBuilder
from src.utils.response_analyzers import walmart_response_analyzer


def get_proxies():
    proxy_user = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_USER")
    proxy_pass = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PASSWORD")
    proxy_host = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_HOST")
    proxy_port = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PORT")

    proxies = {'http': f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
                'https': f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}'}
    return proxies

def get_proxy(proxy_type: str = 'http'):
    proxies = get_proxies()
    return proxies.get(proxy_type, proxies[proxy_type])


class RetailerBundle:
    def __init__(self, retailer, store_identification, fetch_type, fetch_query, start_url, project_config, logger, singleton=False):
        self.retailer = retailer
        self.store_identification = store_identification
        self.fetch_type = fetch_type
        self.fetch_query = fetch_query
        self.start_url = start_url
        self.project_config = project_config
        self.logger = logger
        self.file_storage = FileStorage(retailer, project_config, logger)
        self.singleton = singleton

        if not self.singleton:
            if retailer == "Walmart":
                self.paginator = WalmartPaginator()
            else:
                self.paginator = BooksToScrapePaginator()

        if retailer == "Walmart":
            self.file_namer = WalmartNamer(retailer, fetch_type, store_identification['store_id'])
        else:
            self.file_namer = BooksToScrapeNamer(retailer, fetch_type, store_identification['store_id'])

        self.fetcher = AiohttpFetcher(
            store_identification=store_identification,
            paginator=self.paginator if not self.singleton else None,
            project_config=project_config,
            logger=logger,
            get_headers=self.get_headers,
            get_proxy=self.get_proxy,
            response_analyzer=walmart_response_analyzer,
            check_store_identification=fetch_type not in ['store-directory', 'store-directory-by-state'],
            max_retries=5
        )

        self.session = FetcherSession(
            retailer=retailer,
            store_id=store_identification['store_id'],
            fetch_type=fetch_type,
            fetch_query=fetch_query,
            url=start_url
        )

    def get_headers(self) -> dict:
        if self.retailer == "Walmart":
            header_builder = WalmartHeaderBuilder(
                store_identification=self.store_identification
            )
            return header_builder.build_headers()
        return {}

    def get_proxy(self) -> str:
        if self.retailer == "Walmart":
            return get_proxy()
        return ""

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
            message=result.get("error")
        )

        if is_retry:
            fetched_file.retry_of_url = result["url"]

        self.session.add_fetched_file(fetched_file)

    def handle_retry_results(self, retry_results: List[Tuple[str, dict]]):
        for url, result in retry_results:
            self.handle_result(result, page_num=-1, is_retry=True)

    def get_session_summary(self) -> str:
        self.session.close()
        return self.session.to_string()

    async def fetch_singleton_urls(self, urls: List[str]):
        self.logger.info(f"Fetching {len(urls)} singleton URLs...")
        await self.fetcher.fetch_singleton_urls(urls, self.handle_result)


def build_retailer_bundle(retailer: str, store_identification: dict, fetch_type: str, fetch_query: str, start_url: str, project_config, logger, singleton: bool = False):
    if retailer == "books.toscrape.com" or retailer == "Walmart":
        return RetailerBundle(
            retailer=retailer,
            store_identification=store_identification,
            fetch_type=fetch_type,
            fetch_query=fetch_query,
            start_url=start_url,
            project_config=project_config,
            logger=logger,
            singleton=singleton
        )
    else:
        raise NotImplementedError(f"No bundle defined for retailer: {retailer}")