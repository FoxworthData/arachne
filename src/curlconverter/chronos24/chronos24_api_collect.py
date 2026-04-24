import os

import requests

from dotenv import load_dotenv


load_dotenv()

cookies = {
    '__ssid': '6f38d0544dba3ec0a01f68fce9ca2ae',
    'rskxRunCookie': '0',
    'rCookie': 'gueldyqi84kqjxa6ezswbqmcc8ntmy',
    '_ga': 'GA1.1.566637698.1750873144',
    '_fbp': 'fb.1.1750873143634.67016769358054055',
    '_hjSession_72519': 'eyJpZCI6IjBiZmRlMmE2LTc4MTYtNGI0OC04M2RjLTViYmRiMDhmOTgzYSIsImMiOjE3NTA4NzMxNDQwNDMsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjoxLCJzcCI6MX0=',
    'FPID': 'FPID2.2.1%2Fw6HbXKORl0iuL085IDbh8P0Qjg%2FR%2FdNd4zVqm5Lf4%3D.1750873144',
    'FPLC': 'sFPo7pDZXte%2FStls92gTIKN%2B9yHiYYq5SU%2B1Qx1zBsfrsco%2B6TFHCO%2FBszxaDnEmxf8AIz3r6%2FZcOqOd5p8FkCbiItuQmYcabbcGmN%2BGScQJpYBA04rzFTFO8v0Gsg%3D%3D',
    'FPAU': '1.2.2109597400.1750873144',
    '_hjSessionUser_72519': 'eyJpZCI6IjAzYzc3MjlmLTY3NTQtNWVjYS05MTc2LWJlZDFmMjI5YzU5ZSIsImNyZWF0ZWQiOjE3NTA4NzMxNDQwNDIsImV4aXN0aW5nIjp0cnVlfQ==',
    '_hjDonePolls': '1565214',
    '__gads': 'ID=ed4a5c6d0e7b335d:T=1750873178:RT=1750874749:S=ALNI_MZqXK9RqmArPVLuI_igEiL787xWbg',
    '__gpi': 'UID=0000104ff3003a52:T=1750873178:RT=1750874749:S=ALNI_MZ_je6CCIvH9wYCF4gBD055ULgJcA',
    '__eoi': 'ID=298c2a40b37a9067:T=1750873178:RT=1750874749:S=AA-AfjY_afimCIoV8P5eQ0AbwBFh',
    'FPGSID': '1.1750873144.1750874749.G-B8CPBTKGPW.nSMyfxMj7o6f6KRwCL-mhA',
    'lastRskxRun': '1750874749468',
    '_ga_B8CPBTKGPW': 'GS2.1.s1750873143$o1$g1$t1750874759$j49$l0$h660537393',
}

headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'content-type': 'text/plain;charset=UTF-8',
    'origin': 'https://www.chrono24.com',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://www.chrono24.com/',
    'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    # 'cookie': '__ssid=6f38d0544dba3ec0a01f68fce9ca2ae; rskxRunCookie=0; rCookie=gueldyqi84kqjxa6ezswbqmcc8ntmy; _ga=GA1.1.566637698.1750873144; _fbp=fb.1.1750873143634.67016769358054055; _hjSession_72519=eyJpZCI6IjBiZmRlMmE2LTc4MTYtNGI0OC04M2RjLTViYmRiMDhmOTgzYSIsImMiOjE3NTA4NzMxNDQwNDMsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjoxLCJzcCI6MX0=; FPID=FPID2.2.1%2Fw6HbXKORl0iuL085IDbh8P0Qjg%2FR%2FdNd4zVqm5Lf4%3D.1750873144; FPLC=sFPo7pDZXte%2FStls92gTIKN%2B9yHiYYq5SU%2B1Qx1zBsfrsco%2B6TFHCO%2FBszxaDnEmxf8AIz3r6%2FZcOqOd5p8FkCbiItuQmYcabbcGmN%2BGScQJpYBA04rzFTFO8v0Gsg%3D%3D; FPAU=1.2.2109597400.1750873144; _hjSessionUser_72519=eyJpZCI6IjAzYzc3MjlmLTY3NTQtNWVjYS05MTc2LWJlZDFmMjI5YzU5ZSIsImNyZWF0ZWQiOjE3NTA4NzMxNDQwNDIsImV4aXN0aW5nIjp0cnVlfQ==; _hjDonePolls=1565214; __gads=ID=ed4a5c6d0e7b335d:T=1750873178:RT=1750874749:S=ALNI_MZqXK9RqmArPVLuI_igEiL787xWbg; __gpi=UID=0000104ff3003a52:T=1750873178:RT=1750874749:S=ALNI_MZ_je6CCIvH9wYCF4gBD055ULgJcA; __eoi=ID=298c2a40b37a9067:T=1750873178:RT=1750874749:S=AA-AfjY_afimCIoV8P5eQ0AbwBFh; FPGSID=1.1750873144.1750874749.G-B8CPBTKGPW.nSMyfxMj7o6f6KRwCL-mhA; lastRskxRun=1750874749468; _ga_B8CPBTKGPW=GS2.1.s1750873143$o1$g1$t1750874759$j49$l0$h660537393',
}

data = 'en=page_view&ep.anonymize_ip=true&ep.pageType=search.detail.details&epn.adid=31015533&ep.full_page_path=%2Frolex%2Frolex-daytona---116519ln-meteorite-dial-new-2023--id31015533.htm%3FsearchHash%3Dc475e71b_WyF3LO%26pos%3D22%26catalogTestBadge%3DTCRT_01_listing_true&ep.login_status=not-logged-in&ep.manufacturer=Rolex&ep.model=Daytona&ep.product=116519&ep.page_grouping=search%2Fdetail%2Fdetails&ep.pageId=search.detail.details-viewDetail&ep.test=TCRTII01%7CAAAESIV00%7CABSI01%7CCDCO01%7CLTRS00%7CAAAISIV00&ep.userAgent=Mozilla%2F5.0%20(Macintosh%3B%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F137.0.0.0%20Safari%2F537.36&epn.watchPrice=94844&ep.websiteType=desktop&ep.merchantCountry=UnitedStates&ep.availableInUserCountry=true&ep.ctaButtons=Buy-BuyItNowRequest%7CPriceNegotiation-PriceNegotiationRequest%7CContactSeller%7CPCA&ep.current_referrer=Direct&ep.marketingType=OfferDetails&ep.customized_page_location=https%3A%2F%2Fwww.chrono24.com%2Frolex%2Frolex-daytona---116519ln-meteorite-dial-new-2023--id31015533.htm%3FsearchHash%3Dc475e71b_WyF3LO%26pos%3D22%26catalogTestBadge%3DTCRT_01_listing_true&ep.certification_status=Basic&ep.productType=Watch_Wristwatch&ep.bS=99&ep.test_badge=TCRT_01_listing_true%7CLANDII00_false&ep.app_preheader=true&ep.blockGoogleAds=false&ep.blockFacebook=false&ep.blockBing=false&ep.blockLinkedIn=false&ep.isOfficeRequest=false&_et=3&up.c24sid=DGhu6AigkStE3QY6IwhVMjZZAndBnX3CuYzg&up.bTM=not%20set&up.languageSettings=en&up.isUnsupportedBrowser=0&up.user_city=Austin&up.user_country=UnitedStates&up.user_region=Texas'

def get_proxies():
    # proxy_user = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_USER")
    # proxy_pass = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PASSWORD")

    proxy_user = os.getenv("BRIGHTDATA_DATACENTER_PROXY_USER")
    proxy_pass = os.getenv("BRIGHTDATA_DATACENTER_PROXY_PASSWORD")

    proxy_host = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_HOST")
    proxy_port = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PORT")

    proxies = {'http': f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
                'https': f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}'}
    return proxies

def get_proxy(proxy_type: str = 'http'):
    proxies = get_proxies()
    return proxies.get(proxy_type, proxies[proxy_type])

response = requests.post(
    'https://tsd2.chrono24.com/g/collect?v=2&tid=G-B8CPBTKGPW&gtm=45je56o0v9116619163z86698340za200zb6698340&_p=1750874759184&gcd=13l3l3l3l1l1&npa=0&dma=0&tag_exp=101509157~103116026~103200004~103233427~103351869~103351871~104684208~104684211~104718208~104784387~104784389&cid=566637698.1750873144&ecid=660537393&ul=en-us&sr=1920x1080&ir=1&ur=US-TX&uaa=arm&uab=64&uafvl=Google%2520Chrome%3B137.0.7151.105%7CChromium%3B137.0.7151.105%7CNot%252FA)Brand%3B24.0.0.0&uamb=0&uam=&uap=macOS&uapv=15.5.0&uaw=0&are=1&frm=0&pscdl=noapi&_eu=EAAAAAQ&sst.tft=1750874759184&sst.lpc=39383665&sst.navt=r&sst.ude=0&sst.sw_exp=1&_s=1&sid=1750873143&sct=1&seg=1&dl=https%3A%2F%2Fwww.chrono24.com%2Frolex%2Frolex-daytona---116519ln-meteorite-dial-new-2023--id31015533.htm%3FsearchHash%3Dc475e71b_WyF3LO%26pos%3D22%26catalogTestBadge%3DTCRT_01_listing_true&dt=Rolex%20Daytona%20-%20116519LN%20Meteorite%20Dial%20NEW%202023%20for%20%24110%2C000%20for%20sale%20from%20a%20Trusted%20Seller%20on%20Chrono24&_tu=BA&tfd=1308&richsstsse',
    cookies=cookies,
    headers=headers,
    data=data,
                        proxies=get_proxies(),
                        verify=False
)



print (response.text)