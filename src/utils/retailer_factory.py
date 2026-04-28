"""Factory for constructing the right RetailerScrapeStrategy.

Dispatches by retailer name to the matching concrete strategy class. This
is the only place that needs to know the full set of supported retailers;
adding a new retailer means writing a new strategy module and adding one
elif branch here.
"""
from typing import Optional

from src.utils.browser_personas import BrowserPersona, BrowserPersonaChooser
from src.utils.strategies.aldi_scrape_strategy import AldiScrapeStrategy
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
    persona_os_name: Optional[str] = None,
    persona_browser_name: Optional[str] = None,
) -> RetailerScrapeStrategy:
    """Construct the strategy for retailer.

    persona_os_name / persona_browser_name are passed only to strategies that
    support persona pinning (currently Walmart). For strategies that don't
    use a persona, both args are ignored.
    """
    if retailer == "Walmart":
        browser_persona: Optional[BrowserPersona] = None
        if persona_os_name and persona_browser_name:
            browser_persona = BrowserPersonaChooser().get_persona(
                os_name=persona_os_name, browser_name=persona_browser_name
            )
        return WalmartScrapeStrategy(
            store_identification=store_identification,
            fetch_type=fetch_type,
            fetch_query=fetch_query,
            start_url=start_url,
            project_config=project_config,
            logger=logger,
            singleton=singleton,
            browser_persona=browser_persona,
        )
    elif retailer == "Aldi":
        return AldiScrapeStrategy(
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
