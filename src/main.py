"""Application entrypoint for the arachne web scraping orchestrator.

Composes a single scrape run from the moving parts:
  1. Load configuration and logging
  2. Build a RunConfig from the defaults below (edit them to test different
     retailer / store / fetch_type / query combinations)
  3. Resolve the store_identification record from store_id
  4. Construct a RetailerScrapeStrategy via build_scrape_strategy
  5. Dispatch the fetch_type to the matching strategy method
  6. Log the session summary

Most of the moving parts live elsewhere: target resolution and session
seeding are inside the strategies; the fetch_type-to-method mapping is
in src/dispatch.py. main.py is intentionally thin so a developer reading
the codebase can scan it once and know where to look for everything else.
"""
import asyncio
import os
from typing import Final

from dotenv import load_dotenv

from src.dispatch import dispatch_fetch_type
from src.run_config import RunConfig
from src.utils.aldi_store_util import load_aldi_store_by_location_code
from src.utils.retailer_factory import build_scrape_strategy
from src.utils.setup_config_logging import setup_config_logging
from src.utils.yaml_util import load_store_by_id

load_dotenv()
app_env = os.getenv("APP_ENV", "development")

# ── Defaults — edit for testing different runs ───────────────────────────────
#
# retailer = Walmart
#   store_id: 1198 (San Antonio Supercenter), 1235, 1253
#   search queries: Eggs, Tomatoes, Avocados, Milk, Cookies
#   fetch_types: search, product, store-directory, store-directory-by-state
#
# Personae can be customized to simulate different browser environments;
# the strategy's session seeding pins to whatever is configured here.

# DEFAULT_RETAILER: Final[str] = "Walmart"
# DEFAULT_STORE_ID: Final[str] = "1198"
# DEFAULT_FETCH_TYPE: Final[str] = "search"
# DEFAULT_QUERY: Final[str] = "milk"

DEFAULT_RETAILER: Final[str] = "Aldi"
DEFAULT_STORE_ID: Final[str] = "444-089"
DEFAULT_FETCH_TYPE: Final[str] = "product"
DEFAULT_QUERY: Final[str] = "milk"

DEFAULT_PERSONA_OS_NAME: Final[str] = "Windows"
DEFAULT_PERSONA_BROWSER_NAME: Final[str] = "Chrome"


def _resolve_store_identification(config: RunConfig) -> dict:
    """Pick the right store loader for the configured retailer.

    The orchestration layer has to do this *before* the strategy exists,
    because the strategy constructor takes store_identification. This is
    the only retailer-aware branch in main.py.
    """
    if config.retailer == "Aldi":
        return load_aldi_store_by_location_code(location_code=config.store_id)
    return load_store_by_id(store_id=config.store_id)


async def main() -> None:
    logger, _logger_manager, project_config = setup_config_logging(filename=__name__)
    logger.info("Configuration and logging initialized successfully.")
    logger.info("Hello, world, from arachne!")

    config = RunConfig(
        retailer=DEFAULT_RETAILER,
        store_id=DEFAULT_STORE_ID,
        fetch_type=DEFAULT_FETCH_TYPE,
        query=DEFAULT_QUERY,
        persona_os_name=DEFAULT_PERSONA_OS_NAME,
        persona_browser_name=DEFAULT_PERSONA_BROWSER_NAME,
    )

    store_identification = _resolve_store_identification(config)
    logger.info(store_identification)

    # singleton=True for fetch types that don't paginate; the dispatcher's
    # contract is "call the right run_* method," but the underlying strategy
    # still needs to know whether to wire up a paginator at construction time.
    singleton = config.fetch_type != 'search'

    strategy = build_scrape_strategy(
        retailer=config.retailer,
        store_identification=store_identification,
        fetch_type=config.fetch_type,
        fetch_query=config.query,
        start_url=None,
        project_config=project_config,
        logger=logger,
        singleton=singleton,
        persona_os_name=config.persona_os_name,
        persona_browser_name=config.persona_browser_name,
    )

    await dispatch_fetch_type(strategy, config, logger)
    logger.info(strategy.get_session_summary())


if __name__ == "__main__":
    asyncio.run(main())
