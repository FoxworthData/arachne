import asyncio
import os
import re
import time
from typing import Dict, Any, List

import requests
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.curlconverter.walmart.walmart_home_page import load_search_by_query
from src.utils.file_namer import FashionphileFileNamer
from src.utils.file_storage import FileStorage
from src.utils.paginators import FashionphilePaginator
from src.utils.proxy_builder_simple import get_proxies, get_proxy_components
from src.utils.response_analyzers import fashionphile_response_analyzer
from src.utils.setup_config_logging import setup_config_logging
from src.utils.browser_personas import BrowserPersonaChooser, BrowserPersona
from src.utils.yaml_util import load_store_by_id

load_dotenv()

logger, logger_manager, project_config = setup_config_logging(__name__)


async def scrape_fashionphile_with_playwright():
    """Playwright-based scraper for Fashionphile search results using Arachne infrastructure"""
    retailer = 'fashionphile'
    retailer_store_id = 'website'
    fetch_type = 'search'
    query = 'newest shoes'

    # Load configuration using existing utilities
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stores_file = os.path.join(project_root, 'data', 'fashionphile_stores.yaml')
    search_file = os.path.join(project_root, 'data', 'fashionphile_fetch_search.yaml')

    store_identification = load_store_by_id(store_id=retailer_store_id, yaml_file=stores_file)
    search_config = load_search_by_query(query=query, yaml_file=search_file)

    query = search_config.get('query')
    first_page_search_url = search_config.get('search_url')

    # Initialize Arachne components
    browser_persona_chooser = BrowserPersonaChooser()
    browser_persona = browser_persona_chooser.get_persona(os_name='Windows', browser_name='Chrome')
    
    file_storage = FileStorage(retailer=retailer, project_config=project_config, logger=logger)
    file_namer = FashionphileFileNamer(retailer="Fashionphile", store_id=retailer_store_id, scrape_type=fetch_type)
    paginator = FashionphilePaginator()

    logger.info(f"Using browser persona: {browser_persona.persona_id}")
    logger.info(f"🎯 [Config] Query: {query}")
    logger.info(f"🎯 [Config] Start URL: {first_page_search_url}")

    # Setup proxy configuration
    proxies = get_proxies(proxy_type='residential')
    proxy_components = get_proxy_components('residential')
    proxy_host = proxy_components['proxy_host']
    proxy_port = proxy_components['proxy_port'] 
    proxy_user = proxy_components['proxy_user']
    proxy_pass = proxy_components['proxy_pass']
    
    logger.info(f"🌐 [Proxy] Host: {proxy_host}:{proxy_port}")
    logger.info(f"🌐 [Proxy] User: {proxy_user[:10]}..." if proxy_user else "🌐 [Proxy] User: None")
    logger.info(f"🌐 [Proxy] Pass: {'*' * len(proxy_pass) if proxy_pass else 'None'}")
    
    # Validate proxy credentials are loaded
    if not all([proxy_host, proxy_port, proxy_user, proxy_pass]):
        logger.error("❌ [Proxy] Missing proxy credentials. Check environment variables:")
        logger.error("   - BRIGHTDATA_RESIDENTIAL_PROXY_HOST")
        logger.error("   - BRIGHTDATA_RESIDENTIAL_PROXY_PORT") 
        logger.error("   - BRIGHTDATA_RESIDENTIAL_PROXY_USER")
        logger.error("   - BRIGHTDATA_RESIDENTIAL_PROXY_PASSWORD")
        raise ValueError("Proxy configuration incomplete - script cannot run without proxies")

    # async with async_playwright() as p:
    async with Stealth().use_async(async_playwright()) as p:
        logger.info("[PLAYWRIGHT] Launching browser with stealth...")
        
        # Launch browser with stealth arguments like Walmart prototype
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-features=TranslateUI,VizDisplayCompositor',
                '--disable-ipc-flooding-protection'
            ],
            channel='chrome'
        )

        # Configure proxy like Walmart prototype
        proxy_config = {
            'server': f'http://{proxy_host}:{proxy_port}',
            'username': proxy_user,
            'password': proxy_pass
        }

        # Create context with browser persona and proxy
        context = await browser.new_context(
            user_agent=browser_persona.user_agent,
            viewport={'width': browser_persona.viewport_width, 'height': browser_persona.viewport_height},
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': browser_persona.sec_ch_ua,
                'Sec-Ch-Ua-Mobile': browser_persona.sec_ch_ua_mobile,
                'Sec-Ch-Ua-Platform': browser_persona.sec_ch_ua_platform,
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            },
            locale='en-US',
            timezone_id='America/Chicago',
            proxy=proxy_config,
            ignore_https_errors=True
        )

        # Inject anti-detection scripts like Walmart prototype
        await context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            // Mock Chrome runtime
            window.chrome = {
                runtime: {}
            };

            // Mock permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => {
                return parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters);
            };

            // Override plugins length
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)

        page = await context.new_page()

        try:
            logger.info("[PLAYWRIGHT] Navigating to first page...")
            try:
                response = await page.goto(first_page_search_url, wait_until='domcontentloaded', timeout=30000)
                logger.info(f"📄 [Navigation] Page loaded with status: {response.status}")
            except Exception as e:
                logger.warning(f"⚠️ [Navigation] Timeout during initial load, but continuing: {e}")
                response = None

            # Wait for the page to settle with additional timeout
            logger.info("[PLAYWRIGHT] Waiting for page to fully load...")
            await page.wait_for_timeout(8000)
            
            # Wait specifically for __NEXT_DATA__ script to be present
            try:
                await page.wait_for_selector('script[id="__NEXT_DATA__"]', timeout=15000)
                logger.info("✅ [JavaScript] __NEXT_DATA__ script found - page fully loaded")
            except Exception as e:
                logger.warning(f"⚠️ [JavaScript] __NEXT_DATA__ script not found, proceeding anyway: {e}")

            # Check response status if we have it
            if response and response.status != 200:
                logger.error(f"Failed to load page: {response.status}")
                return

            # Get page content
            html_content = await page.content()
            
            # Check for bot detection patterns in HTML content
            if "Robot or human" in html_content:
                logger.error("❌ [Bot Detection] Fashionphile detected bot behavior!")
                return
            elif "Sorry, fashionphile site doesn't work with your browser." in html_content:
                logger.error("❌ [Browser Rejection] Fashionphile rejected browser!")
                return
            else:
                logger.info("✅ [Response Analysis] Page loaded successfully, no bot detection")
            
            # Save using Arachne FileStorage
            filename = file_namer.get_html_filename(query, 1)
            file_storage.save_html(filename, html_content, fetch_type)

            # Get pagination info using existing paginator
            total_pages = paginator.get_total_pages(html_content)
            logger.info(f"📊 Total pages to scrape: {total_pages}")

            # Get first page product IDs to compare against
            first_page_product_ids = set()
            try:
                import re
                first_page_matches = re.findall(r'"objectID":"([^"]*)"', html_content)
                first_page_product_ids = set(first_page_matches[:10])  # First 10 products
                logger.info(f"🔍 [Page 1] Found {len(first_page_product_ids)} product IDs for comparison")
            except Exception as e:
                logger.warning(f"⚠️ [Page 1] Could not extract product IDs: {e}")

            # Scrape additional pages by clicking Next button repeatedly
            for page_num in range(2, min(total_pages + 1, 6)):  # Limit to first 5 pages for testing
                try:
                    logger.info(f"[PLAYWRIGHT] Clicking Next button to navigate to page {page_num}")
                    
                    # Always try to click Next button instead of looking for specific page numbers
                    clicked = False
                    
                    # Strategy 1: Use specific Fashionphile Next button selectors
                    logger.info(f"🔍 [Pagination] Looking for Next button to navigate to page {page_num}...")
                    next_selectors = [
                        'li.paginationWrapper.rightArrowButton a',  # Specific to Fashionphile's structure
                        '[aria-label="Next page"]',  # Based on your HTML
                        'a[rel="next"]',  # Standard next page link
                        'button:has-text("Next")',
                        'a:has-text("Next")', 
                        'button:has-text(">")',
                        'a:has-text(">")',
                        '[aria-label*="next"]',
                        '[aria-label*="Next"]'
                    ]
                    
                    for selector in next_selectors:
                        try:
                            if await page.locator(selector).count() > 0:
                                logger.info(f"🖱️ [Pagination] Found Next button with selector: {selector}")
                                await page.click(selector)
                                clicked = True
                                break
                        except Exception as e:
                            logger.debug(f"⚠️ [Pagination] Next selector {selector} failed: {e}")
                    
                    # Strategy 2: If still no luck, try to scroll down and look for pagination
                    if not clicked:
                        logger.info(f"🔍 [Pagination] Scrolling to find Next button for page {page_num}...")
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(2000)  # Wait for any lazy-loaded elements
                        
                        # Try the Next button selectors again after scrolling
                        for selector in next_selectors:
                            try:
                                if await page.locator(selector).count() > 0:
                                    logger.info(f"🖱️ [Pagination] Found Next button after scrolling: {selector}")
                                    await page.click(selector)
                                    clicked = True
                                    break
                            except Exception as e:
                                continue
                    
                    if not clicked:
                        logger.error(f"❌ [Pagination] Could not find any pagination button for page {page_num}")
                        continue

                    # Wait for content to actually change after button click
                    logger.info(f"⏳ [Page {page_num}] Waiting for new product data to load after button click...")
                    content_changed = False
                    max_attempts = 15  # 15 seconds max wait
                    
                    for attempt in range(max_attempts):
                        await page.wait_for_timeout(1000)  # Wait 1 second
                        current_html = await page.content()
                        
                        # Extract current page product IDs
                        try:
                            current_matches = re.findall(r'"objectID":"([^"]*)"', current_html)
                            current_product_ids = set(current_matches[:10])
                            
                            # Check if products are different from page 1
                            if current_product_ids and current_product_ids != first_page_product_ids:
                                logger.info(f"✅ [Page {page_num}] New product data loaded after button click in {attempt + 1} seconds")
                                html_content = current_html
                                content_changed = True
                                break
                            elif attempt == max_attempts - 1:
                                logger.warning(f"⚠️ [Page {page_num}] Content may not have changed after button click")
                                html_content = current_html
                                content_changed = True
                        except Exception as e:
                            if attempt == max_attempts - 1:
                                logger.warning(f"⚠️ [Page {page_num}] Could not verify content change: {e}")
                                html_content = current_html
                                content_changed = True
                    
                    if not content_changed:
                        logger.warning(f"⚠️ [Page {page_num}] Using content without verification")
                        html_content = await page.content()
                    
                    # Check for bot detection patterns in HTML content
                    if "Robot or human" in html_content:
                        logger.error(f"❌ [Bot Detection] Page {page_num} - Fashionphile detected bot behavior!")
                        continue
                    elif "Sorry, fashionphile site doesn't work with your browser." in html_content:
                        logger.error(f"❌ [Browser Rejection] Page {page_num} - Fashionphile rejected browser!")
                        continue
                    else:
                        logger.info(f"✅ [Response Analysis] Page {page_num} loaded successfully, no bot detection")
                    filename = file_namer.get_html_filename(query, page_num)
                    file_storage.save_html(filename, html_content, fetch_type)

                    # Brief delay between requests
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"Error scraping page {page_num}: {e}")
                    continue

            logger.info("🎉 Scraping completed successfully!")

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        finally:
            await browser.close()

async def main():
    await scrape_fashionphile_with_playwright()


if __name__ == "__main__":
    asyncio.run(main())