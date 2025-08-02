import json
import math
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse, urljoin


from parsel import Selector

class BasePaginator(ABC):
    @abstractmethod
    def get_total_pages(self, html: str) -> int:
        """Extract total number of pages from HTML."""
        pass

    @abstractmethod
    def get_page_urls(self, first_page_url: str, html: str) -> List[str]:
        """Generate list of paginated URLs."""
        pass


class BooksToScrapePaginator(BasePaginator):
    # Paginator for books.toscrape.com

    def __init__(self, results_selector: str = 'form.form-horizontal strong::text', per_page: int = 20):
        self.results_selector = results_selector
        self.per_page = per_page

    def build_page_url(self, base_url: str, page: int) -> str:
        # Replace "index.html" with f"page-{page}.html"
        return base_url.replace("index.html", f"page-{page}.html")

    def get_total_pages(self, html: str) -> int:
        selector = Selector(text=html)
        results_text = selector.css(self.results_selector).get()
        if results_text:
            try:
                total_results = int(results_text)
                return (total_results + self.per_page - 1) // self.per_page
            except ValueError:
                pass
        return 0

    def get_page_urls(self, first_page_url: str, html: str) -> List[str]:
        total_pages = self.get_total_pages(html)
        if total_pages <= 1:
            return [first_page_url]

        urls = [first_page_url]
        for page in range(2, total_pages + 1):
            page_url = self.build_page_url(first_page_url, page)
            urls.append(page_url)
        return urls


class WalmartPaginator(BasePaginator):
    # Paginator for Walmart

    def __init__(self, results_selector: str = '//script[@id="__NEXT_DATA__"]/text()', per_page: int = 40):
        self.results_selector = results_selector
        self.per_page = per_page

    def build_page_url(self, base_url, page) -> str:
        """Generates a URL for a specific page in search results."""
        parsed_url = urlparse(base_url)
        query_params = parse_qs(parsed_url.query)
        query_params["page"] = [str(page)]
        query_params["affinityOverride"] = ["store_led"]
        return urlunparse(parsed_url._replace(query=urlencode(query_params, doseq=True)))

    def get_total_pages(self, html: str) -> int:
        """Extracts the total number of pages from search results."""
        total_results = self.parse_search(html)["total_results"]
        # self.logger.info(f"Total items in search results: {total_results}")
        return min(math.ceil(total_results / self.per_page), 25)  # Walmart limits search to 25 pages

    def parse_search(self, html: str) -> Dict[str, Any]:
        """Parses Walmart's search result page using the supplied HTML."""
        selector = Selector(text=html)
        script_data = selector.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        if not script_data:
            raise ValueError("Failed to extract JSON data from the response.")

        data = json.loads(script_data)

        return {
            "results": data["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"][0]["items"],
            "total_results": data["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"][0]["count"]
        }

    def get_page_urls(self, first_page_url: str, html: str) -> List[str]:
        total_pages = self.get_total_pages(html)
        if total_pages <= 1:
            return [first_page_url]

        urls = [first_page_url]
        for page in range(2, total_pages + 1):
            page_url = self.build_page_url(first_page_url, page)
            urls.append(page_url)
        return urls
