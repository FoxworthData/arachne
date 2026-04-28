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
from timezonefinder import TimezoneFinder

from src.utils.config_loader import ConfigLoader
from src.utils.file_storage import FileStorage
from src.utils.setup_config_logging import setup_config_logging

load_dotenv()  # Load environment variables from .env file

app_env = os.getenv("APP_ENV", "development")  # Default to 'development' if not set
print(f"Running in {app_env} environment.")


class WalmartStoreDirectoryByStateParser:
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
        self.fetch_type = 'store-directory-by-state'
        self.fetched_save_location = str(Path(os.environ.get("SAVE_LOCATION"), self.retailer, self.fetch_type))
        self.parsed_save_location = str(Path(os.environ.get("PARSED_SAVE_LOCATION"), self.retailer, self.fetch_type))
        self.country_code = 'USA'

        self.yaml_file = None

    def extract_search_next_data(self, html_content):
        """Extracts JSON data from the <script id="__NEXT_DATA__"> tag using XPath."""
        sel = Selector(text=html_content)
        data = sel.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        return json.loads(data) if data else None

    def build_store_url(self, store_id, city, state):
        city_slug = re.sub(r'\s+', '-', city.lower())
        state_slug = state.lower()
        return f"https://www.walmart.com/store/{store_id}-{city_slug}-{state_slug}"

    def build_store_entry(self, store, timezone):
        store_id = store.get('id')
        city = store.get('address', {}).get('city', '')
        state = store.get('address', {}).get('state', '')

        store_url = self.build_store_url(store_id, city, state) if store_id and city and state else None

        return {
            'store_id': store_id,
            'store_address': store.get('address', {}).get('addressLineOne'),
            'store_address_line_two': store.get('address', {}).get('addressLineTwo'),
            'store_city': city,
            'store_state': state,
            'store_zip_code': store.get('address', {}).get('postalCode'),
            'store_country': store.get('address', {}).get('country'),
            'store_country_code': self.country_code,
            'store_display_name': store.get('displayName', store.get('name')),
            'store_brand_format': store.get('name'),
            'store_time_zone': timezone,
            'store_latitude': store.get('geoPoint', {}).get('latitude'),
            'store_longitude': store.get('geoPoint', {}).get('longitude'),
            'store_is_open_24h': store.get('open24Hours'),
            'store_services': [svc.get('displayName') for svc in (store.get('services') or [])],
            'store_capabilities': [cap.get('accessPointType') for cap in (store.get('capabilities') or [])],
            'store_operational_hours': store.get('operationalHours'),
            'store_is_glass_eligible': store.get('isGlassEligible'),
            'store_url': store_url
        }

    def enrich_stores_with_timezone(self, stores_data):
        tf = TimezoneFinder()
        enriched_stores = []

        for store in stores_data:
            latitude = store.get('geoPoint', {}).get('latitude')
            longitude = store.get('geoPoint', {}).get('longitude')
            timezone = tf.timezone_at(lat=latitude, lng=longitude) if latitude and longitude else None

            store_entry = self.build_store_entry(store, timezone)
            enriched_stores.append(store_entry)

        return enriched_stores

    def load_existing_yaml(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return yaml.safe_load(f) or []
        return []

    def update_or_add_stores(self, existing_stores, new_stores):
        # Convert to dict for easy lookup
        existing_dict = {store['store_id']: store for store in existing_stores}

        for store in new_stores:
            existing_dict[store['store_id']] = store

        return list(existing_dict.values())

    def save_yaml(self, data, file_path):
        with open(file_path, 'w') as f:
            yaml.dump(data, f, sort_keys=False)

    def parse(self, fetched):
        # Load the JSON data

        source_full_path = str(Path(self.fetched_save_location, fetched))

        html_content = self.file_storage.get_html_content(source_full_path)
        next_data_json = self.extract_search_next_data(html_content)

        if not next_data_json:
            self.logger.error("Error: Could not find __NEXT_DATA__ script tag.")
            return

        stores_data = next_data_json['props']['pageProps']['initialData']['initialDataNearbyNodes']['data']['nearByNodes']['nodes']

        self.logger.info("Enriching store data with timezone info...")
        enriched_stores = self.enrich_stores_with_timezone(stores_data)

        self.logger.info("Loading existing YAML file (if exists)...")
        existing_stores = self.load_existing_yaml(self.yaml_file)

        self.logger.info("Updating or adding stores...")
        updated_stores = self.update_or_add_stores(existing_stores, enriched_stores)

        self.logger.info(f"Saving updated YAML file to: {self.yaml_file}")
        self.save_yaml(updated_stores, self.yaml_file)

        self.logger.info(f"✅ Done! Updated YAML with {len(updated_stores)} stores.")

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
    fetch_type = 'store-directory-by-state'

    logger.info(f"Retailer: {retailer} Fetch Type: {fetch_type}")


    try:
        parser = WalmartStoreDirectoryByStateParser(project_config=project_config, logger=logger)
        parser.yaml_file = "/Users/dalesmith/Projects/arachne/data/Walmart_stores_NEW.yaml"

        fetches = parser.file_storage.list_saved_files(fetch_type=fetch_type)

        sorted_fetches = sorted(fetches)

        total_fetches = len(sorted_fetches)

        for i, fetch in enumerate(sorted_fetches):
            if fetch == ".DS_Store":
                logger.info(f"Skipping {fetch} due to .DS_Store file")
                continue
            if i < 250:
                continue
            logger.info(f"parsing {i} of {total_fetches}:  {fetch}")
            parser.parse(fetch)

    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        logger.error(f"{traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(main())