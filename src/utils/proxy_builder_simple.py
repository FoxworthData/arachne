import os
import requests
def get_proxies(proxy_type='datacenter'):

    proxy_components = get_proxy_components(proxy_type)

    proxy_user = proxy_components['proxy_user']
    proxy_pass = proxy_components['proxy_pass']

    proxy_host = proxy_components['proxy_host']
    proxy_port = proxy_components['proxy_port']

    proxies = {'http': f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
                'https': f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}'}
    return proxies

def get_proxy(proxy_type: str = 'http'):
    proxies = get_proxies()
    return proxies.get(proxy_type, proxies[proxy_type])

def get_proxy_components(proxy_type='datacenter'):

    proxy_user = os.getenv("BRIGHTDATA_DATACENTER_PROXY_USER")
    proxy_pass = os.getenv("BRIGHTDATA_DATACENTER_PROXY_PASSWORD")

    if proxy_type == 'residential':
        proxy_user = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_USER")
        proxy_pass = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PASSWORD")

    proxy_host = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_HOST")
    proxy_port = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PORT")

    return {'proxy_user': proxy_user, 'proxy_pass': proxy_pass, 'proxy_host': proxy_host, 'proxy_port': proxy_port}