import os
import requests
from dotenv import load_dotenv

load_dotenv()

headers = {
    'accept': 'application/json; charset=utf-8',
    'origin': 'https://shop.rebag.com',
    'referer': 'https://shop.rebag.com/',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
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

# response = requests.get('https://psaqr.rebag.com/init?...&pf_v_designers=Chanel', headers=headers)


response = requests.get('https://psaqr.rebag.com/init?...&pf_v_designers=Chanel',
                        headers=headers,
                        proxies=get_proxies(),
                        verify=False
                        )


# Save response text to a file
with open('rebag_api_test_1.txt', 'w', encoding='utf-8') as file:
    file.write(response.text)