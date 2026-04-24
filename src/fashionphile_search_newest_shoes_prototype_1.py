import asyncio
import os
import re
import time
from typing import Dict, Any

import requests
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.curlconverter.walmart_home_page import load_search_by_query
from src.utils.header_builders import WalmartHeaderBuilder
from src.utils.proxy_builder_simple import get_proxies, get_proxy_components
from src.utils.retailer_factory import RetailerBundle
from src.utils.setup_config_logging import setup_config_logging
from src.utils.browser_personas import BrowserPersonaChooser, BrowserPersona
from src.utils.walmart_cookie_seeder import WalmartCookieSeeder
from src.utils.yaml_util import load_store_by_id

load_dotenv()

logger, logger_manager, project_config = setup_config_logging(__name__)


def blend_cookies(location_cookies, harvested_cookies):

    cookie_string = f"hasLocData={location_cookies['hasLocData']}; ACID={location_cookies['ACID']}; locGuestData={location_cookies['locGuestData']}; assortmentStoreId={location_cookies['assortmentStoreId']}; hasACID=true; locDataV3={location_cookies['locDataV3']}; "

    harvested_cookie_string = "; ".join(f"{key}={value}" for key, value in harvested_cookies.items())

    cookie_string += f"{harvested_cookie_string};"

    return cookie_string

class LocalBundle(RetailerBundle):
    headers = {}
    def set_headers(self, headers:dict):
        self.headers = headers

    def build_headers(self):
        return self.headers

    def get_headers(self):
        return self.build_headers()

class WalmartCookieSeedingHeaderBuilder(WalmartHeaderBuilder):
    def __init__(self, store_identification:dict, browser_persona:BrowserPersona):
        super().__init__(store_identification=store_identification)
        self.browser_persona = browser_persona

        self.initial_headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'priority': 'u=0, i',
                'sec-ch-ua': self.browser_persona.sec_ch_ua,
                'sec-ch-ua-mobile': self.browser_persona.sec_ch_ua_mobile,
                'sec-ch-ua-platform': self.browser_persona.sec_ch_ua_platform,
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': self.browser_persona.user_agent
            }

        generated_location_cookies = self.location_cookie()
        self.generated_location_cookie_dict = {}
        for pair in generated_location_cookies.split('; '):
            if '=' in pair:
                name, value = pair.split('=', 1)
                self.generated_location_cookie_dict[name] = value
                logger.info(f"Generated cookie: {name}={value}")

        self.initial_cookies = {
            'hasACID': 'true',
            'adblocked': 'false',
            'hasLocData': '1',
            'ACID': self.generated_location_cookie_dict['ACID'],
            'locGuestData': self.generated_location_cookie_dict['locGuestData'],
            'locDataV3': self.generated_location_cookie_dict['locDataV3'],
            'assortmentStoreId': self.store_id
        }


async def main():
    retailer = 'Walmart'
    retailer_store_id = '1198'
    fetch_type = 'search'
    query = 'Milk'  # Simple query for testing

    # Load configuration using existing utilities with absolute paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stores_file = os.path.join(project_root, 'data', 'Walmart_stores.yaml')
    search_file = os.path.join(project_root, 'data', 'Walmart_fetch_search.yaml')

    store_identification = load_store_by_id(store_id=retailer_store_id, yaml_file=stores_file)
    search_config = load_search_by_query(query=query, yaml_file=search_file)

    query = search_config.get('query')
    first_page_search_url = search_config.get('search_url')

    browser_persona_chooser = BrowserPersonaChooser()
    # browser_persona = browser_persona_chooser.get_random_persona()
    browser_persona = browser_persona_chooser.get_persona(os_name='Windows', browser_name='Chrome')

    logger.info(f"Using browser persona: {browser_persona.persona_id}")

    proxies = get_proxies(proxy_type='residential')

    header_builder = WalmartCookieSeedingHeaderBuilder(store_identification=store_identification, browser_persona=browser_persona)
    cookie_seeder = WalmartCookieSeeder(
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

        bundle.set_headers(seeded_headers)

        results = await bundle.fetcher.fetch_all(first_page_search_url, bundle.handle_result)


if __name__ == "__main__":
    asyncio.run(main())