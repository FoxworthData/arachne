
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


class FashionphileFileNamer(BaseFileNamer):
    def __init__(self, retailer: str, scrape_type: str, store_id: str, timestamp: Optional[str] = None):
        self.retailer = retailer or "Fashionphile"
        self.scrape_type = scrape_type
        self.store_id = store_id
        self.timestamp = timestamp or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def get_html_filename(self, query: str, page_num: int) -> str:
        # Example: Fashionphile_search_websote_handbags_page_1_20240517T103000Z.html.gz
        safe_query = query.replace("/", "_").replace(" ", "_")
        return f"{self.retailer}_{self.scrape_type}_{self.store_id}_{safe_query}_page_{page_num}_{self.timestamp}.html.gz"


class AldiNamer(BaseFileNamer):
    """File namer for Aldi.

    Aldi runs save one JSON file per run rather than one per page, so the
    `page_num` parameter on get_html_filename is accepted but ignored;
    the strategy uses get_json_filename for its actual file naming.
    """

    def __init__(self, retailer: str, scrape_type: str, store_id: str, timestamp: Optional[str] = None):
        self.retailer = retailer or "Aldi"
        self.scrape_type = scrape_type
        self.store_id = store_id
        self.timestamp = timestamp or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def get_json_filename(self, query: str) -> str:
        # Example: Aldi_search_444-089_milk_20260427T142412Z.json.gz
        safe_query = query.lower().replace("/", "_").replace(" ", "_")[:30]
        return f"{self.retailer}_{self.scrape_type}_{self.store_id}_{safe_query}_{self.timestamp}.json.gz"

    def get_html_filename(self, query: str, page_num: int = 0) -> str:
        # Aldi saves JSON, not HTML. Satisfies the ABC by delegating.
        return self.get_json_filename(query)
