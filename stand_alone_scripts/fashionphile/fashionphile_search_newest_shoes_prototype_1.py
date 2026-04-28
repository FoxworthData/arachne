import asyncio
import os
import re
import time
from typing import Dict, Any

import requests
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.curlconverter.walmart.walmart_home_page import load_search_by_query
from src.utils.fashionphile_cookie_seeder import FashionphileCookieSeeder
from src.utils.file_namer import FashionphileFileNamer
from src.utils.header_builders import WalmartHeaderBuilder, FashionphileCookieSeedingHeaderBuilder
from src.utils.paginators import FashionphilePaginator
from src.utils.proxy_builder_simple import get_proxies, get_proxy_components
from src.utils.response_analyzers import fashionphile_response_analyzer
from src.utils.retailer_factory import RetailerBundle
from src.utils.setup_config_logging import setup_config_logging
from src.utils.browser_personas import BrowserPersonaChooser, BrowserPersona
from src.utils.yaml_util import load_store_by_id

load_dotenv()

logger, logger_manager, project_config = setup_config_logging(__name__)


def blend_cookies(initial_cookies, harvested_cookies):
    """Blend initial and harvested cookies for Fashionphile"""
    # Combine initial cookies with harvested cookies
    all_cookies = {**initial_cookies, **harvested_cookies}
    
    # Create cookie string
    cookie_string = "; ".join(f"{key}={value}" for key, value in all_cookies.items())
    
    return cookie_string

class LocalBundle(RetailerBundle):
    headers = {}
    def set_headers(self, headers:dict):
        self.headers = headers

    def build_headers(self):
        return self.headers

    def get_headers(self):
        return self.build_headers()

async def main():
    retailer = 'fashionphile'
    retailer_store_id = 'website'
    fetch_type = 'search'
    query = 'newest louboutin shoes'  # Simple query for testing

    # Load configuration using existing utilities with absolute paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stores_file = os.path.join(project_root, 'data', 'fashionphile_stores.yaml')
    search_file = os.path.join(project_root, 'data', 'fashionphile_fetch_search.yaml')

    store_identification = load_store_by_id(store_id=retailer_store_id, yaml_file=stores_file)
    search_config = load_search_by_query(query=query, yaml_file=search_file)

    query = search_config.get('query')
    first_page_search_url = search_config.get('search_url')

    browser_persona_chooser = BrowserPersonaChooser()
    # browser_persona = browser_persona_chooser.get_random_persona()
    browser_persona = browser_persona_chooser.get_persona(os_name='Windows', browser_name='Chrome')

    logger.info(f"Using browser persona: {browser_persona.persona_id}")

    proxies = get_proxies(proxy_type='residential')

    header_builder = FashionphileCookieSeedingHeaderBuilder(store_identification=store_identification, browser_persona=browser_persona)
    cookie_seeder = FashionphileCookieSeeder(
        retailer_store_id=retailer_store_id,
        initial_headers=header_builder.initial_headers,
        initial_cookies=header_builder.initial_cookies,
        proxies=proxies,
        logger=logger
    )

    harvested_result = await cookie_seeder.get_seeded_cookies(
        browser_persona=browser_persona
    )

    if harvested_result['success']:
        logger.info("Cookie seeding successful")
        blended_cookie_string = blend_cookies(header_builder.initial_cookies, harvested_result['cookies'])

        logger.info(f"blended cookie string: {blended_cookie_string}")

        seeded_headers = harvested_result['headers']
        seeded_headers['cookie'] = blended_cookie_string

        logger.info("[SCRAPING] Starting scraping process...")

        logger.info(f"🎯 [Config] Query: {query}")
        logger.info(f"🎯 [Config] Start URL: {first_page_search_url}")

        bundle = LocalBundle(
            retailer=retailer,
            store_identification=store_identification,
            fetch_type=fetch_type,
            fetch_query=query,
            start_url=first_page_search_url,
            project_config=project_config,
            logger=logger,
        )

        bundle.response_analyzer = fashionphile_response_analyzer
        bundle.file_namer = FashionphileFileNamer(
            retailer="Fashionphile",
            store_id=retailer_store_id,
            scrape_type=fetch_type,
        )
        bundle.paginator = FashionphilePaginator()

        bundle.fetcher.paginator = FashionphilePaginator()
        bundle.fetcher.response_analyzer = fashionphile_response_analyzer

        bundle.set_headers(seeded_headers)



        results = await bundle.fetcher.fetch_all(first_page_search_url, bundle.handle_result)


if __name__ == "__main__":
    asyncio.run(main())