import os

import requests

from dotenv import load_dotenv


load_dotenv()

import utils.proxy_builder_simple as proxy_builder

import requests

headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'origin': 'https://www.chrono24.com',
    'pragma': 'no-cache',
    'referer': 'https://www.chrono24.com/',
    'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'script',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
}

url = 'https://static.chrono24.com/lib/generated/vite_en/assets/api-config-Crn_A11v.js'


proxies = proxy_builder.get_proxies()
response = requests.get(
    url=url,
    headers=headers,
    proxies=proxies,
    verify=False
)

print (response.text)
