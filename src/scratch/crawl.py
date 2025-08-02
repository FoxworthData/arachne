import asyncio
import os
import uuid

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.async_configs import BrowserConfig, ProxyConfig
from dotenv import load_dotenv
from fake_useragent import UserAgent

from src.utils.file_storage import FileStorage
from src.utils.setup_config_logging import setup_config_logging



load_dotenv()
app_env = os.getenv("APP_ENV", "development")  # Default to 'development' if not set


def get_proxy(proxy_type: str = 'residential'):
    session_id = str(uuid.uuid4())[:8]

    proxy_user = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_USER")
    proxy_pass = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PASSWORD")
    proxy_port = 33335

    proxy_host = "brd.superproxy.io"
    proxy_server = f"{proxy_host}:{proxy_port}"
    proxy_user_with_session = f"{proxy_user}-session-{session_id}"

    return {
        "server": proxy_server,  # Your residential proxy port
        "username": proxy_user_with_session,  # Bright Data session rotation
        "password": proxy_pass
    }



async def main():
    logger, logger_manager, project_config = setup_config_logging(filename=__name__)
    file_storage = FileStorage('nothing', project_config, logger)

    # user_agent = UserAgent().random
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15'

    proxy_config_data = get_proxy()

    proxy_config = ProxyConfig(
        server=proxy_config_data["server"],
        username=proxy_config_data["username"],
        password=proxy_config_data["password"]
    )

    viewport = {"width": 1920, "height": 1080}

    browser_conf = BrowserConfig(
        headless=True,
        browser_type="Mozilla",
        user_agent=user_agent,
        viewport=viewport,
        proxy_config=proxy_config
    )

    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="domcontentloaded",
    )

    # url='https://example.com'
    url='https://www.walmart.com/store/1253-austin-tx'

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        result = await crawler.arun(
            url=url,
            config=run_conf
        )
        file_storage.save_html("test_before_click.html.gz", result.html)

        # run JS to click 'Make this my store' button if it exists
        js_set_store = """
        const selector = '#maincontent > section:nth-child(2) > div > div > div.w-100.w-third-l.top-0 > div > div > div > div > button';
        const button = document.querySelector(selector);
        if (button) button.click();
        """

        run_conf = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="domcontentloaded",
            js_code=js_set_store,
        )

        result = await crawler.arun(
            url=url,
            config=run_conf
        )

        file_storage.save_html("test_after_click.html.gz", result.html)

if __name__ == "__main__":
    asyncio.run(main())