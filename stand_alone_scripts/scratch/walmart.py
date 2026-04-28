import asyncio
import aiohttp
import base64
from dotenv import load_dotenv
from fake_useragent import UserAgent
import json
import os
import time
import uuid


load_dotenv()


api_key = os.getenv('ALPHAVANTAGE_API_KEY')
url = 'https://www.alphavantage.co/query?function=OVERVIEW&symbol={}&apikey={}'
symbols = ['AAPL', 'GOOG', 'TSLA', 'MSFT', 'PEP']
results = []

# url = 'https://www.walmart.com/search?q=Eggs'
store_id = 1198
store_zip = 78232


def location_cookie():
    "Builds a cookie string for the specified store ID and zip code."
    timestamp = int(time.time())
    acid = str(uuid.uuid4())

    # Simplify the location_guest_data
    location_guest_data = {
        "intent": "SHIPPING",
        "storeIntent": "PICKUP",
        "pickup": {
            "nodeId": store_id,
            "timestamp": timestamp
        },
        "postalCode": {
            "base": store_zip,
            "timestamp": timestamp
        },
        "validateKey": f"prod:v2:{acid}"
    }

    # Encode the simplified data
    encoded_location_data = base64.urlsafe_b64encode(json.dumps(location_guest_data).encode()).decode()

    # Return a smaller cookie string
    return f"ACID={acid}; hasACID=true; hasLocData=1; assortmentStoreId={store_id}; locGuestData={encoded_location_data}"


def get_random_user_agent():
    # Instantiate the UserAgent class with a browser list
    user_agents = UserAgent(browsers=['safari', 'chrome'])
    user_agent = user_agents.random
    return user_agent


def get_headers():
    ac = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
    headers = {
        "Cookie": location_cookie(),
        "Referer": "https://www.google.com",
        "Connection": "Keep-Alive",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": ac,
        "User-Agent": get_random_user_agent(),
    }
    return headers

def get_tasks(session):
    tasks = []
    proxy_url = get_proxies()['http']
    for symbol in symbols:
        tasks.append(asyncio.create_task(session.get(url.format(symbol,api_key), ssl=False, proxy=proxy_url)))
    return tasks

async def get_symbols():
    async with aiohttp.ClientSession() as session:
        tasks = get_tasks(session)
        responses = await asyncio.gather(*tasks)
    
    return responses

def get_proxies(proxy_type: str = 'residential'):
    proxy_user = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_USER")
    proxy_pass = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PASSWORD")
    proxy_host = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_HOST")
    proxy_port = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PORT")

    proxies = {'http': f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
                'https': f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}'}
    return proxies

async def print_results(responses):
    for result in responses:
        print(await result.text())

async def fetch_page():
    url = 'https://www.walmart.com/search?q=Eggs'
    proxy_url = get_proxies()['http']
    headers = get_headers()
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url=url,
            ssl=False,
            proxy=proxy_url,
            headers=headers
        ) as response:
            data = await response.text()
            # print(await response.status)

    return data

# async def fetch_page(session, url):
#     try:
#         async with session.get(
#             url=url,
#             ssl=False,
#         ) as response:
#             data = await response.text()
#             print(response.status)
#
#         return data
#     except Exception as e:
#         print(str(e))


async def main():

    start = time.time()

    # category = 'sequential-art_5'
    # search_url = 'https://books.toscrape.com/catalogue/category/books/sequential-art_5/index.html'

    # async with aiohttp.ClientSession() as session:
    #     first_page_html = await fetch_page(session=session,url=search_url)

    first_page_html = await fetch_page()

    filename = "search_results_page_1.html"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(first_page_html)


    # responses = await get_symbols()

    # page = await fetch_page()

    end = time.time()
    total_time = end - start

    # print(f"It took {total_time} seconds to make {len(responses)} API calls")
    # await print_results(responses)

    # print(get_headers())
    # print(get_random_user_agent())

if __name__ == "__main__":
    asyncio.run(main())

