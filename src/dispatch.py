"""dispatch_fetch_type: route a RunConfig to the right strategy method.

The dispatcher is the only module that knows the mapping from fetch_type
strings to strategy method calls, plus the special case of retailer-specific
operations that aren't on the RetailerScrapeStrategy ABC (Walmart's two
store-directory flows).

Adding a new fetch_type means: add a method to the ABC (or to a specific
strategy if it's retailer-specific), and add one branch here.
"""
from logging import Logger

from src.run_config import RunConfig
from src.utils.strategies.scrape_strategy import RetailerScrapeStrategy
from src.utils.strategies.walmart_scrape_strategy import WalmartScrapeStrategy


async def dispatch_fetch_type(
    strategy: RetailerScrapeStrategy,
    config: RunConfig,
    logger: Logger,
) -> None:
    """Call the strategy method that corresponds to config.fetch_type.

    Raises ValueError for unknown fetch_types and for fetch_types that
    require a retailer-specific operation the strategy doesn't support
    (e.g. asking a non-Walmart strategy for a store-directory crawl).
    """
    fetch_type = config.fetch_type

    if fetch_type == 'search':
        await strategy.run_search(config.query)

    elif fetch_type == 'product':
        await strategy.run_product_lookup()

    elif fetch_type == 'store-directory':
        if not isinstance(strategy, WalmartScrapeStrategy):
            raise ValueError(
                f"fetch_type 'store-directory' is only supported by "
                f"WalmartScrapeStrategy, not {type(strategy).__name__}"
            )
        await strategy.run_store_directory(config.query)

    elif fetch_type == 'store-directory-by-state':
        if not isinstance(strategy, WalmartScrapeStrategy):
            raise ValueError(
                f"fetch_type 'store-directory-by-state' is only supported by "
                f"WalmartScrapeStrategy, not {type(strategy).__name__}"
            )
        await strategy.run_store_directory_by_state(config.query)

    else:
        raise ValueError(f"Unknown fetch_type: {fetch_type!r}")
