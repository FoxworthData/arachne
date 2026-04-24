import os
import requests
from dotenv import load_dotenv

load_dotenv()

cookies = {
    'identityId': '9c326047-1719-4a34-9023-e1dc559d3a0e',
    'ajs_anonymous_id': '9c326047-1719-4a34-9023-e1dc559d3a0e',
    'fpCookieAccept': 'true',
    '_tt_enable_cookie': '1',
    '_ttp': '01JZ1CWHWCB9V1FRQ6055K831Q_.tt.1',
    '_gcl_au': '1.1.834779743.1751319989',
    '_ga': 'GA1.1.1587555537.1751319990',
    '_fbp': 'fb.1.1751319990114.737220091802244154',
    '_axwrt': '5d17cb32-2f42-4997-b985-095b9f7cfaf5',
    '_pin_unauth': 'dWlkPU9HUTFOakptWmpFdFpqWXpNUzAwTVdJM0xXSXhPV1F0TkRBMVltSmhOVEpoWWpJdw',
    '__stripe_mid': '50080c79-16f4-48f1-b9ed-66bd261ae2c649b9b0',
    'email_popup_counter': '12',
    'viewed_products': '%5B1660080%5D',
    'redirect_url': 'https%3A%2F%2Fwww.fashionphile.com%2Fshop%2Fcategories%2Fshoes',
    'cf_clearance': 'RxBxmUb732m5Ki.xPyycNyYm2oKoO8KtQwGbNwM2Es4-1755107532-1.2.1.1-UtCAakEjAqsNm6x2mrmsEwYXvY.yQr_R2WaqqKffnfH_aoySx_BNGP8VdoldozzcD_IoEmI3xCEK53l5kuby7_DxKYDi8Mjpd8lAF_7zMn5IQWOQvi01JiOV5TgNQAKim1LMhkYn0b59yVQ73_y5doJUW_.ZH5tHTd5s_e_gEI.GH.qiXUWnqPg6.CxJw0E6GY_XJatkVru4zYYHvOe7mQ_rjmtvc5P9s.sla18l.ws',
    'cartData': '%7B%22cartItems%22%3A%5B%5D%2C%22productsInCart%22%3A0%2C%22total%22%3A0%2C%22revalidate%22%3Afalse%7D',
    'ttcsid': '1755107534180::c_mBYeWa5ydtn1NAkaLg.3.1755107534180',
    'ttcsid_CKEPVNRC77UFTHK77PHG': '1755107534179::IU8Pgj5_G9BsxuakjnQA.3.1755107534403',
    '_uetsid': '3edd98e0786e11f0992ec9559900e906',
    '_uetvid': 'af5f315055fb11f098b32fcdbfb39c18',
    '_ga_DJV8VFWG4V': 'GS2.1.s1755107534$o3$g0$t1755107534$j60$l0$h884582033',
    '__rtbh.lid': '%7B%22eventType%22%3A%22lid%22%2C%22id%22%3A%227sGlGM8m9zbtv2gj7OLr%22%2C%22expiryDate%22%3A%222026-08-13T17%3A52%3A14.908Z%22%7D',
    'lantern': 'e3fb2e56-ace1-420f-baf0-b5d59b6d3657',
    '_clck': '1ct09u%7C2%7Cfyf%7C0%7C2007',
    '_clsk': 'jlfduu%7C1755107535789%7C1%7C1%7Co.clarity.ms%2Fcollect',
    '__stripe_sid': 'c5c0b1bf-17c6-41fc-ae92-5bbe9173d239651458',
    'inside-us': '799349202-64bc88b45bb7802cdc4ad3e47b0cb3ebae14849169d38440134b792bed03af3d-0-0',
    'ax_visitor': '%7B%22firstVisitTs%22%3A1751319990367%2C%22lastVisitTs%22%3A1751480460348%2C%22currentVisitStartTs%22%3A1755107534712%2C%22ts%22%3A1755107570426%2C%22visitCount%22%3A3%7D',
    '_dd_s': 'rum=2&id=f818b3dc-6bd7-431c-bd33-9d93f2bdb598&created=1755107531896&expire=1755108450503',
}

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
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
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


response = requests.get(
    'https://www.fashionphile.com/p/chanel-lambskin-booties-39-black-navy-1665116',
    cookies=cookies,
    headers=headers,
    proxies=get_proxies(),
    verify=False
)

# Save response text to a file
with open('fashionphile_product_response_output.html', 'w', encoding='utf-8') as file:
    file.write(response.text)
