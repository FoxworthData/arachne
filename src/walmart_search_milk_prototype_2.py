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
from src.utils.header_builders import WalmartHeaderBuilder
from src.utils.proxy_builder_simple import get_proxies, get_proxy_components
from src.utils.retailer_factory import RetailerBundle
from src.utils.setup_config_logging import setup_config_logging
from src.utils.browser_personas import BrowserPersonaChooser, BrowserPersona
from src.utils.yaml_util import load_store_by_id

load_dotenv()

logger, logger_manager, project_config = setup_config_logging(__name__)

browser_persona_chooser = BrowserPersonaChooser()
# browser_persona = browser_persona_chooser.get_random_persona()
browser_persona = browser_persona_chooser.get_persona(os_name='Windows', browser_name='Chrome')

logger.info(f"Using browser persona: {browser_persona.persona_id}")

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': browser_persona.sec_ch_ua,
    'sec-ch-ua-mobile': browser_persona.sec_ch_ua_mobile,
    'sec-ch-ua-platform': browser_persona.sec_ch_ua_platform,
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': browser_persona.user_agent
}


async def get_walmart_home_page_with_requests(store_id:str, headers:dict, cookies:dict):
    proxies = get_proxies(proxy_type='residential')

    logger.info("[COOKIE SEEDING] Starting cookie seeding process...")

    max_attempts = 10
    attempt = 1
    while attempt <= max_attempts:
        logger.info(f"[COOKIE SEEDING] Attempt {attempt} of {max_attempts}...")
        response = requests.get(
            'https://www.walmart.com',
            cookies=cookies,
            proxies=proxies,
            headers=headers,
            verify=False
        )

        logger.info(f'[COOKIE SEEDING] https://www.walmart.com response code: {response.status_code}')
        logger.info(f'[COOKIE SEEDING] https://www.walmart.com response reason: {response.reason}')

        if (response.status_code == 200):
            # Save response text to a file
            with open('walmart_home_page_output.html', 'w', encoding='utf-8') as file:
                file_text = response.text

                logger.info(f"[COOKIE SEEDING] Searching response text for storeId:{store_id}...")
                match = re.search(r'"storeId":"(\d+)"', file_text)
                if match:
                    file.write(file_text)
                    found_id = match.group(1)  # Extracts the number from the pattern
                    logger.info(f"[COOKIE SEEDING] ******* Found store ID '{found_id}'.")
                    if found_id == store_id:
                        logger.info(f"[COOKIE SEEDING] Store ID '{found_id}' matches the specified retailer_store_id '{store_id}'.")
                        for cookie in response.cookies:
                            logger.info(f"Cookie: {cookie.name}={cookie.value}")

                        harvested_cookies = await harvest_cookies(response.cookies.get_dict())

                        success_result = {
                                    "success": True,
                                    "cookies": harvested_cookies,
                                    "headers": headers
                                }

                        return success_result
                    else:
                        logger.warning(f"[COOKIE SEEDING] Found Store ID '{found_id}' does not match the specified retailer_store_id '{store_id}'.")
                else:
                    logger.warning("[COOKIE SEEDING] No 'storeId' pattern found in the HTML response.")
        else:
            logger.warning(f"[COOKIE SEEDING] Attempt {attempt} failed. Status code: {response.status_code}. Reason: {response.reason}")

        attempt += 1

    return {
                "success": False,
                "cookies": cookies,
                "headers": headers
            }


async def harvest_cookies(all_context_cookies):
    harvested_cookies = {}
    cookies_to_harvest = ['_pxvid', 'vtc', '_m', 'io_id', 'abqme',
                          'AID', '_pxhd', 'pxcts', 'wmlh', '_astc',
                          'userAppVersion', 'akavpau_p1', 'bstc', '__cf_bm', 'com.wm.reflector',
                          'akavpau_p2', 'bm_mi', 'ak_bmsc', 'if_id', 'bm_sv', '_px3',
                          '_pxde', ]
    for cookie in all_context_cookies:
        if cookie in cookies_to_harvest:
            harvested_cookies[cookie] =  all_context_cookies[cookie]
    return harvested_cookies


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

async def main():
    retailer = 'Walmart'
    store_id = '1198'
    fetch_type = 'search'
    query = 'Milk'  # Simple query for testing

    # Load configuration using existing utilities with absolute paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stores_file = os.path.join(project_root, 'data', 'Walmart_stores.yaml')
    search_file = os.path.join(project_root, 'data', 'Walmart_fetch_search.yaml')

    store_identification = load_store_by_id(store_id=store_id, yaml_file=stores_file)
    search_config = load_search_by_query(query=query, yaml_file=search_file)
    header_builder = WalmartHeaderBuilder(store_identification=store_identification)

    query = search_config.get('query')
    first_page_search_url = search_config.get('search_url')

    generated_location_cookies = header_builder.location_cookie()
    generated_location_cookie_dict = {}
    for pair in generated_location_cookies.split('; '):
        if '=' in pair:
            name, value = pair.split('=', 1)
            generated_location_cookie_dict[name] = value
            logger.info(f"Generated cookie: {name}={value}")

    trimmed_cookies = {
        'hasACID': 'true',
        'adblocked': 'false',
        'hasLocData': '1',
        'ACID': generated_location_cookie_dict['ACID'],
        'locGuestData': generated_location_cookie_dict['locGuestData'],
        'locDataV3': generated_location_cookie_dict['locDataV3'],
        'assortmentStoreId': store_id
    }

    logger.info(f"🎯 [Config] Retailer: {retailer}")
    logger.info(f"🎯 [Config] Store: {store_id} ({store_identification.get('store_display_name', 'Unknown')})")

    harvested_result = await get_walmart_home_page_with_requests(
        store_id=store_id,
        headers=headers,
        cookies=trimmed_cookies
    )

    blended_cookie_string = blend_cookies(trimmed_cookies, harvested_result['cookies'])

    logger.info(f"blended cookie string: {blended_cookie_string}")

    headers['cookie'] = blended_cookie_string

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

    bundle.set_headers(headers)

    results = await bundle.fetcher.fetch_all(first_page_search_url, bundle.handle_result)


if __name__ == "__main__":
    asyncio.run(main())