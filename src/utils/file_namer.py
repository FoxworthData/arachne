
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class BaseFileNamer(ABC):
    @abstractmethod
    def get_html_filename(self, query: str, page_num: int) -> str:
        """Return the relative path/filename for saving a scraped HTML page."""
        pass


class BooksToScrapeNamer(BaseFileNamer):
    def __init__(self, retailer: str, scrape_type: str, store_id: int, timestamp: Optional[str] = None):
        self.retailer = retailer or "books.toscrape.com"
        self.scrape_type = scrape_type
        self.store_id = store_id
        self.timestamp = timestamp or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def get_html_filename(self, query: str, page_num: int) -> str:
        # Example: books.toscrape.com_search_1198_sequential-art_5_page_1_20240517T103000Z.html.gz
        safe_category = query.replace("/", "_").replace(" ", "_")
        return f"{self.retailer}_{self.scrape_type}_{self.store_id}_{safe_category}_page_{page_num}_{self.timestamp}.html.gz"



class WalmartNamer(BaseFileNamer):
    def __init__(self, retailer: str, scrape_type: str, store_id: int, timestamp: Optional[str] = None):
        self.retailer = retailer or "Walmart"
        self.scrape_type = scrape_type
        self.store_id = store_id
        self.timestamp = timestamp or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def get_html_filename(self, query: str, page_num: int) -> str:
        # Example: Walmart_search_1198_Eggs_page_1_20240517T103000Z.html.gz
        safe_query = query.replace("/", "_").replace(" ", "_")
        return f"{self.retailer}_{self.scrape_type}_{self.store_id}_{safe_query}_page_{page_num}_{self.timestamp}.html.gz"
