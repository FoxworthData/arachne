import os
import requests
from dotenv import load_dotenv

load_dotenv()

cookies = {
    'identityId': 'cdbb66a4-c95b-433a-824b-b503eaba4338',
    'ajs_anonymous_id': 'cdbb66a4-c95b-433a-824b-b503eaba4338',
    'cartData': '%7B%22cartItems%22%3A%5B%5D%2C%22productsInCart%22%3A0%2C%22total%22%3A0%2C%22revalidate%22%3Afalse%7D',
    '_tt_enable_cookie': '1',
    '_ttp': '01K43NT8H2SXSMZQRTHKVETAW4_.tt.1',
    '_gcl_au': '1.1.1154394410.1756765168',
    '_pin_unauth': 'dWlkPU9USXdaalk0TlRrdE9HTTNZUzAwTW1SaExUZzFaR0l0WTJNMFlXRXdaakJrWXpReQ',
    '_ga': 'GA1.1.1667127612.1756765169',
    '_fbp': 'fb.1.1756765169413.366835779638321189',
    '_axwrt': '5265b52a-6f9a-4648-8fb1-d5f0fe645ebc',
    '_clck': '1gganh9%5E2%5Efyy%5E0%5E2070',
    'fpCookieAccept': 'true',
    '__stripe_mid': '62a7d330-c672-4f0f-b3b0-1501c4b1f24b3f5958',
    '__cf_bm': 'AFOfT_9fGKes_16L.FHnOwFeY2vpbspqH0VI96unZoo-1756767295-1.0.1.1-xyWpZ7AD7EaahMpUh2590gnkEljCH_85_CKwROLyGPSckAzVZnbo3Zvgqkii3RJAk7hf0IK2k6Eha2x8HnAcWQliY0HNxsB2yatbM7hSAvM',
    'redirect_url': 'https%3A%2F%2Fwww.fashionphile.com%2Fshop%2Fcategories%2Fshoes%3Fbrands%3Dlouboutin',
    'cf_clearance': 'l1T5IbM31QqZKUbVX.x6cqTn1s8z4EpY1MhJX_JcqPM-1756767295-1.2.1.1-0dAq8j.ZKVNB4yT3oQ_FhbCxSDegI14o6neEKsUxb1HFwDh5XM1q8K4l4P15mrOx_l3QXSIkHFf_3UKM7ObLvogHGl0qpguphxJFeGedG.z_8tMfVdeid7UBlJMx5Z0I40fVK7ezEjN6kVdzhEZUjITrYqHy5XDqy8nvzMhG4RW2xVDg9eqbwdLmP35hgKoYuZHkdk6kIhGnCds0QnblmouMb3tMP1Y2NfWlDC4vwK4',
    'ttcsid': '1756767296749::9TJgfyk0Mcw6wVfbcbfI.2.1756767296749',
    '_uetsid': 'ba43ef70878111f0af50ed3c20d00612',
    '_uetvid': 'ba43f120878111f0a9c08d643a1f830d',
    '_ga_DJV8VFWG4V': 'GS2.1.s1756765169$o1$g1$t1756767296$j59$l0$h219891370',
    '__rtbh.lid': '%7B%22eventType%22%3A%22lid%22%2C%22id%22%3A%22GhofV5lnEhXrt3QcXOuq%22%2C%22expiryDate%22%3A%222026-09-01T22%3A54%3A56.884Z%22%7D',
    'ttcsid_CKEPVNRC77UFTHK77PHG': '1756767296749::AgoTqlT1-9KwQh99E74I.2.1756767296977',
    '_clsk': 's7rjn8%5E1756767297866%5E1%5E1%5Eo.clarity.ms%2Fcollect',
    '__stripe_sid': 'd6bea739-2067-4720-b26e-8d163e25797e7f68ef',
    'inside-us': '811792388-d7f55cd3ca6e05fc35222e58c56ef65c35f59da3d97136f42e24e2a43b3b49d4-0-0',
    '_dd_s': 'rum=0&expire=1756768195450',
    'ax_visitor': '%7B%22firstVisitTs%22%3A1756765169466%2C%22lastVisitTs%22%3Anull%2C%22currentVisitStartTs%22%3A1756765169466%2C%22ts%22%3A1756767317231%2C%22visitCount%22%3A1%7D',
}

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'max-age=0',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    # 'cookie': 'identityId=cdbb66a4-c95b-433a-824b-b503eaba4338; ajs_anonymous_id=cdbb66a4-c95b-433a-824b-b503eaba4338; cartData=%7B%22cartItems%22%3A%5B%5D%2C%22productsInCart%22%3A0%2C%22total%22%3A0%2C%22revalidate%22%3Afalse%7D; _tt_enable_cookie=1; _ttp=01K43NT8H2SXSMZQRTHKVETAW4_.tt.1; _gcl_au=1.1.1154394410.1756765168; _pin_unauth=dWlkPU9USXdaalk0TlRrdE9HTTNZUzAwTW1SaExUZzFaR0l0WTJNMFlXRXdaakJrWXpReQ; _ga=GA1.1.1667127612.1756765169; _fbp=fb.1.1756765169413.366835779638321189; _axwrt=5265b52a-6f9a-4648-8fb1-d5f0fe645ebc; _clck=1gganh9%5E2%5Efyy%5E0%5E2070; fpCookieAccept=true; __stripe_mid=62a7d330-c672-4f0f-b3b0-1501c4b1f24b3f5958; __cf_bm=AFOfT_9fGKes_16L.FHnOwFeY2vpbspqH0VI96unZoo-1756767295-1.0.1.1-xyWpZ7AD7EaahMpUh2590gnkEljCH_85_CKwROLyGPSckAzVZnbo3Zvgqkii3RJAk7hf0IK2k6Eha2x8HnAcWQliY0HNxsB2yatbM7hSAvM; redirect_url=https%3A%2F%2Fwww.fashionphile.com%2Fshop%2Fcategories%2Fshoes%3Fbrands%3Dlouboutin; cf_clearance=l1T5IbM31QqZKUbVX.x6cqTn1s8z4EpY1MhJX_JcqPM-1756767295-1.2.1.1-0dAq8j.ZKVNB4yT3oQ_FhbCxSDegI14o6neEKsUxb1HFwDh5XM1q8K4l4P15mrOx_l3QXSIkHFf_3UKM7ObLvogHGl0qpguphxJFeGedG.z_8tMfVdeid7UBlJMx5Z0I40fVK7ezEjN6kVdzhEZUjITrYqHy5XDqy8nvzMhG4RW2xVDg9eqbwdLmP35hgKoYuZHkdk6kIhGnCds0QnblmouMb3tMP1Y2NfWlDC4vwK4; ttcsid=1756767296749::9TJgfyk0Mcw6wVfbcbfI.2.1756767296749; _uetsid=ba43ef70878111f0af50ed3c20d00612; _uetvid=ba43f120878111f0a9c08d643a1f830d; _ga_DJV8VFWG4V=GS2.1.s1756765169$o1$g1$t1756767296$j59$l0$h219891370; __rtbh.lid=%7B%22eventType%22%3A%22lid%22%2C%22id%22%3A%22GhofV5lnEhXrt3QcXOuq%22%2C%22expiryDate%22%3A%222026-09-01T22%3A54%3A56.884Z%22%7D; ttcsid_CKEPVNRC77UFTHK77PHG=1756767296749::AgoTqlT1-9KwQh99E74I.2.1756767296977; _clsk=s7rjn8%5E1756767297866%5E1%5E1%5Eo.clarity.ms%2Fcollect; __stripe_sid=d6bea739-2067-4720-b26e-8d163e25797e7f68ef; inside-us=811792388-d7f55cd3ca6e05fc35222e58c56ef65c35f59da3d97136f42e24e2a43b3b49d4-0-0; _dd_s=rum=0&expire=1756768195450; ax_visitor=%7B%22firstVisitTs%22%3A1756765169466%2C%22lastVisitTs%22%3Anull%2C%22currentVisitStartTs%22%3A1756765169466%2C%22ts%22%3A1756767317231%2C%22visitCount%22%3A1%7D',
}

params = {
    'brands': 'louboutin',
}

# response = requests.get('https://www.fashionphile.com/shop/categories/shoes', params=params, cookies=cookies, headers=headers)


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
with open('fashionphile_newest_louboutin_shoes.html', 'w', encoding='utf-8') as file:
    file.write(response.text)