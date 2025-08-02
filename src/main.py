import asyncio
import os

from dotenv import load_dotenv

from src.utils.retailer_factory import build_retailer_bundle
from src.utils.setup_config_logging import setup_config_logging
from src.utils.yaml_util import load_store_by_id, load_search_by_query, get_random_products, \
    load_store_directories_by_state

load_dotenv()
app_env = os.getenv("APP_ENV", "development")  # Default to 'development' if not set


# retailer = 'books.toscrape.com'
# store_identification = {'store_id': 1198, 'store_zip': 78232}
# fetch_type = 'search'
# query = 'sequential-art_5'
# first_page_search_url = f'https://books.toscrape.com/catalogue/category/books/{query}/index.html'

async def main():

    logger, logger_manager, project_config = setup_config_logging(filename=__name__)
    logger.info("Configuration and logging initialized successfully.")
    logger.info("Hello, world, from arachne!")

    # 1198, 1235, 1253
    # Eggs, tomatoes, avocados, fresh berries, rollbacks - food

    retailer = 'Walmart'
    store_id = '5145'

    # fetch_type = 'search'
    # query = 'tomatoes'

    fetch_type = 'store-directory'
    query = 'la'

    store_identification = load_store_by_id(store_id=store_id)
    logger.info(store_identification)

    if fetch_type == 'search':
        logger.info(f"Retailer: {retailer} Store: {store_id} Fetch Type: {fetch_type} Query: {query}")

        search = load_search_by_query(query=query)
        logger.info(search)

        query = search.get('query')
        first_page_search_url = search.get('search_url')

        bundle = build_retailer_bundle(
            retailer=retailer,
            store_identification=store_identification,
            fetch_type=fetch_type,
            fetch_query=query,
            start_url=first_page_search_url,
            project_config=project_config,
            logger=logger
        )

        results = await bundle.fetcher.fetch_all(first_page_search_url, bundle.handle_result)

    elif fetch_type == 'product':
        query = fetch_type
        logger.info(f"Retailer: {retailer} Store: {store_id} Fetch Type: {fetch_type} Query: {query}")

        random_entries = get_random_products()
        urls = []
        for entry in random_entries:
            urls.append(entry.get('canonical_url'))

        bundle = build_retailer_bundle(
            retailer=retailer,
            store_identification=store_identification,
            fetch_type=fetch_type,
            fetch_query=query,
            start_url=None,
            project_config=project_config,
            logger=logger,
            singleton=True
        )

        results = await bundle.fetcher.fetch_singleton_urls(urls, bundle.handle_result)

    elif fetch_type == 'store-directory':

        logger.info(f"Retailer: {retailer} Store: {store_id} Fetch Type: {fetch_type} Query: {query}")

        url = f"https://www.walmart.com/store-directory/{query.lower()}"

        bundle = build_retailer_bundle(
            retailer=retailer,
            store_identification=store_identification,
            fetch_type=fetch_type,
            fetch_query=query,
            start_url=url,
            project_config=project_config,
            logger=logger,
            singleton=True
        )

        results = await bundle.fetcher.fetch_singleton_urls([url], bundle.handle_result)

    elif fetch_type == 'store-directory-by-state':

        query = 'tx'

        logger.info(f"Retailer: {retailer} Store: {store_id} Fetch Type: {fetch_type} Query: {query}")

        city_urls = load_store_directories_by_state(query)


        for city_url in city_urls:
            city = city_url.get('city')
            city_url_value = city_url.get('url')

            city_query = f"{query} {city}"

            bundle = build_retailer_bundle(
                retailer=retailer,
                store_identification=store_identification,
                fetch_type=fetch_type,
                fetch_query=city_query,
                start_url=city_url_value,
                project_config=project_config,
                logger=logger,
                singleton=True
            )

            results = await bundle.fetcher.fetch_singleton_urls([city_url_value], bundle.handle_result)
            logger.info(bundle.get_session_summary())


    logger.info(bundle.get_session_summary())

if __name__ == "__main__":
    asyncio.run(main())

