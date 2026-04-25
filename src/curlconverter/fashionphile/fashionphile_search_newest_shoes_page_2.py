import os
import requests
from dotenv import load_dotenv

load_dotenv()

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
}

params = {
    'page': '2',
}


def get_proxies():
    proxy_user = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_USER")
    proxy_pass = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PASSWORD")

    # proxy_user = os.getenv("BRIGHTDATA_DATACENTER_PROXY_USER")
    # proxy_pass = os.getenv("BRIGHTDATA_DATACENTER_PROXY_PASSWORD")

    proxy_host = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_HOST")
    proxy_port = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PORT")

    proxies = {'http': f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
                'https': f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}'}
    return proxies

def get_proxy(proxy_type: str = 'http'):
    proxies = get_proxies()
    return proxies.get(proxy_type, proxies[proxy_type])

response = requests.get('https://www.fashionphile.com/shop/categories/shoes',
                        params=params,
                        headers=headers,
                        proxies=get_proxies(),
                        verify=False
                        )


# Save response text to a file
with open('fashionphile_response_output_page_2.html', 'w', encoding='utf-8') as file:
    file.write(response.text)