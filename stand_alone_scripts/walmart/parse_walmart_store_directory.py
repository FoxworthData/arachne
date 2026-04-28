import asyncio
import json
import os
import traceback
from logging import Logger

import re
from pathlib import Path
from urllib.parse import urljoin, quote

import yaml
from parsel import Selector


from dotenv import load_dotenv


from src.utils.config_loader import ConfigLoader
from src.utils.file_storage import FileStorage
from src.utils.setup_config_logging import setup_config_logging

load_dotenv()  # Load environment variables from .env file

app_env = os.getenv("APP_ENV", "development")  # Default to 'development' if not set
print(f"Running in {app_env} environment.")


class WalmartStoreDirectoryParser:
    def __init__(
        self,
        project_config: ConfigLoader = None,
        logger: Logger = None,
    ):
        self.project_config = project_config
        self.logger = logger
        self.file_storage = FileStorage(
            retailer='Walmart',
            project_config=self.project_config,
            logger=self.logger
        )

        self.retailer = 'Walmart'
        self.app_environment = os.environ.get("APP_ENV", "development")  # Default to 'development'
        self.fetch_type = 'store-directory'
        self.fetched_save_location = str(Path(os.environ.get("SAVE_LOCATION"), self.retailer, self.fetch_type))
        self.parsed_save_location = str(Path(os.environ.get("PARSED_SAVE_LOCATION"), self.retailer, self.fetch_type))

    def extract_search_next_data(self, html_content):
        """Extracts JSON data from the <script id="__NEXT_DATA__"> tag using XPath."""
        sel = Selector(text=html_content)
        data = sel.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        return json.loads(data) if data else None

    def parse(self, fetched):
        # Load the JSON data

        # fetched = "Walmart_store-directory_1253_tx_page_1_20250527T152521Z.html.gz"
        source_full_path = str(Path(self.fetched_save_location, fetched))

        html_content = self.file_storage.get_html_content(source_full_path)
        next_data_json = self.extract_search_next_data(html_content)

        # next_data_json = json.loads(next_data_content)

        # Recursive function to find the "StorePagesStoreDirectory" module
        def find_store_pages_directory(data):
            if isinstance(data, dict):
                if data.get('type') == 'StorePagesStoreDirectory':
                    return data
                for key, value in data.items():
                    result = find_store_pages_directory(value)
                    if result:
                        return result
            elif isinstance(data, list):
                for item in data:
                    result = find_store_pages_directory(item)
                    if result:
                        return result
            return None

        # Find the configs dictionary containing the state -> cities mapping
        store_pages_directory_data = find_store_pages_directory(next_data_json)
        configs_data = store_pages_directory_data.get('configs')
        store_directory_json_str = store_pages_directory_data['configs']['storeDirectory'][0]['text']
        # Parse the city data as JSON
        store_directory_data = json.loads(store_directory_json_str)

        # Build the YAML data structure
        states_cities_data = []

        for state_code, cities in store_directory_data.items():
            state_entry = {
                'state': state_code,
                'cities': []
            }
            base_url = "https://www.walmart.com/store-directory/"

            for city in cities:
                if isinstance(city, str):
                    # Remove the count in parentheses, e.g., "Austin (7)" -> "Austin"
                    cleaned_city = re.sub(r'\s*\(\d+\)', '', city).strip()
                    # Encode the city slug
                    city_slug = quote(cleaned_city.lower())
                    # Build the full URL using urljoin
                    path = f"{state_code}/{city_slug}"
                    url = urljoin(base_url, path)
                    state_entry['cities'].append({
                        'city': cleaned_city,
                        'url': url
                    })
            states_cities_data.append(state_entry)

        # Convert to YAML format
        yaml_content = yaml.dump(states_cities_data, sort_keys=False, allow_unicode=True)

        # Save to a YAML file
        with open('walmart_store_directories_by_state.yaml', 'w') as f:
            f.write(yaml_content)

        print("YAML file has been created: walmart_stores_by_state.yaml")

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
    fetch_type = 'store-directory'

    logger.info(f"Retailer: {retailer} Fetch Type: {fetch_type}")

    try:
        parser = WalmartStoreDirectoryParser(project_config=project_config, logger=logger)
        parser.parse(fetched="Walmart_store-directory_1253_tx_page_1_20250527T152521Z.html.gz")

    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        logger.error(f"{traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(main())