"""Factory for constructing the right RetailerScrapeStrategy.

Dispatches by retailer name to the matching concrete strategy class. This
is the only place that needs to know the full set of supported retailers;
adding a new retailer means writing a new strategy module and adding one
elif branch here.
"""
from src.utils.strategies.books_to_scrape_strategy import BooksToScrapeStrategy
from src.utils.strategies.fashionphile_scrape_strategy import FashionphileScrapeStrategy
from src.utils.strategies.scrape_strategy import RetailerScrapeStrategy
from src.utils.strategies.walmart_scrape_strategy import WalmartScrapeStrategy


def build_scrape_strategy(
    retailer: str,
    store_identification: dict,
    fetch_type: str,
    fetch_query: str,
    start_url: str,
    project_config,
    logger,
    singleton: bool = False,
) -> RetailerScrapeStrategy:
    if retailer == "Walmart":
        return WalmartScrapeStrategy(
            store_identification=store_identification,
            fetch_type=fetch_type,
            fetch_query=fetch_query,
            start_url=start_url,
            project_config=project_config,
            logger=logger,
            singleton=singleton,
        )
    elif retailer == "Fashionphile":
        return FashionphileScrapeStrategy(
            store_identification=store_identification,
            fetch_type=fetch_type,
            fetch_query=fetch_query,
            start_url=start_url,
            project_config=project_config,
            logger=logger,
            singleton=singleton,
        )
    elif retailer == "books.toscrape.com":
        return BooksToScrapeStrategy(
            store_identification=store_identification,
            fetch_type=fetch_type,
            fetch_query=fetch_query,
            start_url=start_url,
            project_config=project_config,
            logger=logger,
            singleton=singleton,
        )
    else:
        raise NotImplementedError(f"No scrape strategy defined for retailer: {retailer}")
