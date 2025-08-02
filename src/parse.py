import asyncio
import os
import traceback

from dotenv import load_dotenv

from src.utils.setup_config_logging import setup_config_logging
from src.utils.walmart_parsers import WalmartSearchParser, WalmartProductParser

load_dotenv()  # Load environment variables from .env file

app_env = os.getenv("APP_ENV", "development")  # Default to 'development' if not set
print(f"Running in {app_env} environment.")


async def main():
    """
    Main entry point of the application.

    This function initializes the configuration, sets up logging,
    and runs the core asynchronous logic.
    """
    # args = parse_arguments()
    logger, logger_manager, project_config = setup_config_logging(__name__)

    logger.info("Configuration and logging initialized successfully.")
    logger.info("Hello, world, from arachne parser!")

    retailer = 'Walmart'
    fetch_type = 'search'

    logger.info(f"Retailer: {retailer} Fetch Type: {fetch_type}")

    try:
        if fetch_type == "search":
            parser = WalmartSearchParser(project_config=project_config, logger=logger)
        elif fetch_type == "product":
            parser = WalmartProductParser(project_config=project_config, logger=logger)

        parser.parse_all()

    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        logger.error(f"{traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(main())
