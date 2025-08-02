import os

import requests

from dotenv import load_dotenv


load_dotenv()

cookies = {
    'chronosessid': '59d050c0-9580-46a2-929b-5b7e8046e34a',
    'filter-combinations': '1:Man,0:',
    'csrf-token': '1750873138.kjVKxVhnuhzwHM-cJePm0K8uBSc3JdBQDjwjaMTqyU0.AXG1VdibBGy9lHJuvCJVXLZtwhpn',
    '__cflb': '0H28vBCZxXf5QcKQeSUz1bT3jumYpMsK3TxtJri7QqA',
    'timezone': 'America/Chicago',
    '__ssid': '6f38d0544dba3ec0a01f68fce9ca2ae',
    'rskxRunCookie': '0',
    'rCookie': 'gueldyqi84kqjxa6ezswbqmcc8ntmy',
    'c24-consent': 'AAEAJo/nwEhO',
    'catalog-switcher-state': 'listings',
    'catalog-switcher-hint': 'catalogSwitchHintDisplayed',
    '_ga': 'GA1.1.566637698.1750873144',
    '_fbp': 'fb.1.1750873143634.67016769358054055',
    '_hjSession_72519': 'eyJpZCI6IjBiZmRlMmE2LTc4MTYtNGI0OC04M2RjLTViYmRiMDhmOTgzYSIsImMiOjE3NTA4NzMxNDQwNDMsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjoxLCJzcCI6MX0=',
    'FPID': 'FPID2.2.1%2Fw6HbXKORl0iuL085IDbh8P0Qjg%2FR%2FdNd4zVqm5Lf4%3D.1750873144',
    'FPLC': 'sFPo7pDZXte%2FStls92gTIKN%2B9yHiYYq5SU%2B1Qx1zBsfrsco%2B6TFHCO%2FBszxaDnEmxf8AIz3r6%2FZcOqOd5p8FkCbiItuQmYcabbcGmN%2BGScQJpYBA04rzFTFO8v0Gsg%3D%3D',
    'FPAU': '1.2.2109597400.1750873144',
    'last-search-result-ids': '41021143.41113958.41135137.41111846.38709578.23988054.40708879.40855418.41000857.40773459.40884461.40723800.38689626.40936019.36091299.40711598.41017358.41012948.40616428.41151461.41002715.30265922.40417083.39035263.35733142.38656635.40586357.30268545.38358648.40080099.40550670.39256789.39315600.40430540.40307752.38105884.40574476.40974957.40855455.40449726.40655680.40324204.40884357.38899267.38986311.40449755.37904140.40840713.38878868.40456611.38804848.40449787.38641810.40555765.40708207.39467129.40360548.17339263.40463035.40835614',
    '_hjSessionUser_72519': 'eyJpZCI6IjAzYzc3MjlmLTY3NTQtNWVjYS05MTc2LWJlZDFmMjI5YzU5ZSIsImNyZWF0ZWQiOjE3NTA4NzMxNDQwNDIsImV4aXN0aW5nIjp0cnVlfQ==',
    '_hjDonePolls': '1565214',
    'cfctGroup': 'AAAESIV00%3D%26TCRTII01%3D%26ABSI01%3D%26CDCO01%3D%26LTRS00%3D%26AAAISIV00%3D',
    '__gads': 'ID=ed4a5c6d0e7b335d:T=1750873178:RT=1750874749:S=ALNI_MZqXK9RqmArPVLuI_igEiL787xWbg',
    '__gpi': 'UID=0000104ff3003a52:T=1750873178:RT=1750874749:S=ALNI_MZ_je6CCIvH9wYCF4gBD055ULgJcA',
    '__eoi': 'ID=298c2a40b37a9067:T=1750873178:RT=1750874749:S=AA-AfjY_afimCIoV8P5eQ0AbwBFh',
    'FPGSID': '1.1750873144.1750874749.G-B8CPBTKGPW.nSMyfxMj7o6f6KRwCL-mhA',
    'lastRskxRun': '1750874749468',
    'c24-data': 'eyIzNiI6eyJlIjoiMTc4MjQwOTEzOCIsInYiOiIxNzUwODczMTM4Njg5In0sIjM3Ijp7ImUiOiIxNzgyNDA5MTM4IiwidiI6IjE3NTA4NzMxMzg2ODkifSwiMjciOnsiZSI6IjE3ODI0MDkxMzgiLCJ2IjoiMSJ9LCIzOCI6eyJlIjoiMTc4MjQwOTEzOCIsInYiOiIxNzQ4MTk0NzM4Njg5In0sIjIzMiI6eyJlIjoiMTc4MjQwOTE0MSIsInYiOiIxNzUwODczMTM5MDQ5In0sIjQ2NSI6eyJlIjoiMTg0NTQ4MTE0MiIsInYiOiIxODQ1NDgxMTQyOTA3In0sIjUiOnsiZSI6IjE3NTM0NjY3NTgiLCJ2IjoiNiJ9LCIxMTUiOnsiZSI6IjE3NjY0MjY3NDkiLCJ2IjoibGcifSwiNiI6eyJlIjoiMTc1MzQ2Njc1OCIsInYiOiI2In0sIjUxNCI6eyJlIjoiMTc4MjQwOTE3OCIsInYiOiIifSwiNTE1Ijp7ImUiOiIxNzgyNDA5MTc4IiwidiI6IjEifSwiNDEiOnsiZSI6IjE3ODI0MDkxMzgiLCJ2IjoiMTc1MDg3MzEzODAwMCJ9LCI5OCI6eyJlIjoiMTc4MjQxMDc1OCIsInYiOiI2In19',
    'userHistory': '31015533|1750874758613|2',
    '_ga_B8CPBTKGPW': 'GS2.1.s1750873143$o1$g1$t1750874758$j50$l0$h660537393',
}

headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://www.chrono24.com/rolex/rolex-daytona---116519ln-meteorite-dial-new-2023--id31015533.htm?searchHash=c475e71b_WyF3LO&pos=22&catalogTestBadge=TCRT_01_listing_true',
    'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'x-csrf-token': '1750873138.kjVKxVhnuhzwHM-cJePm0K8uBSc3JdBQDjwjaMTqyU0.AXG1VdibBGy9lHJuvCJVXLZtwhpn',
    # 'cookie': 'chronosessid=59d050c0-9580-46a2-929b-5b7e8046e34a; filter-combinations=1:Man,0:; csrf-token=1750873138.kjVKxVhnuhzwHM-cJePm0K8uBSc3JdBQDjwjaMTqyU0.AXG1VdibBGy9lHJuvCJVXLZtwhpn; __cflb=0H28vBCZxXf5QcKQeSUz1bT3jumYpMsK3TxtJri7QqA; timezone=America/Chicago; __ssid=6f38d0544dba3ec0a01f68fce9ca2ae; rskxRunCookie=0; rCookie=gueldyqi84kqjxa6ezswbqmcc8ntmy; c24-consent=AAEAJo/nwEhO; catalog-switcher-state=listings; catalog-switcher-hint=catalogSwitchHintDisplayed; _ga=GA1.1.566637698.1750873144; _fbp=fb.1.1750873143634.67016769358054055; _hjSession_72519=eyJpZCI6IjBiZmRlMmE2LTc4MTYtNGI0OC04M2RjLTViYmRiMDhmOTgzYSIsImMiOjE3NTA4NzMxNDQwNDMsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjoxLCJzcCI6MX0=; FPID=FPID2.2.1%2Fw6HbXKORl0iuL085IDbh8P0Qjg%2FR%2FdNd4zVqm5Lf4%3D.1750873144; FPLC=sFPo7pDZXte%2FStls92gTIKN%2B9yHiYYq5SU%2B1Qx1zBsfrsco%2B6TFHCO%2FBszxaDnEmxf8AIz3r6%2FZcOqOd5p8FkCbiItuQmYcabbcGmN%2BGScQJpYBA04rzFTFO8v0Gsg%3D%3D; FPAU=1.2.2109597400.1750873144; last-search-result-ids=41021143.41113958.41135137.41111846.38709578.23988054.40708879.40855418.41000857.40773459.40884461.40723800.38689626.40936019.36091299.40711598.41017358.41012948.40616428.41151461.41002715.30265922.40417083.39035263.35733142.38656635.40586357.30268545.38358648.40080099.40550670.39256789.39315600.40430540.40307752.38105884.40574476.40974957.40855455.40449726.40655680.40324204.40884357.38899267.38986311.40449755.37904140.40840713.38878868.40456611.38804848.40449787.38641810.40555765.40708207.39467129.40360548.17339263.40463035.40835614; _hjSessionUser_72519=eyJpZCI6IjAzYzc3MjlmLTY3NTQtNWVjYS05MTc2LWJlZDFmMjI5YzU5ZSIsImNyZWF0ZWQiOjE3NTA4NzMxNDQwNDIsImV4aXN0aW5nIjp0cnVlfQ==; _hjDonePolls=1565214; cfctGroup=AAAESIV00%3D%26TCRTII01%3D%26ABSI01%3D%26CDCO01%3D%26LTRS00%3D%26AAAISIV00%3D; __gads=ID=ed4a5c6d0e7b335d:T=1750873178:RT=1750874749:S=ALNI_MZqXK9RqmArPVLuI_igEiL787xWbg; __gpi=UID=0000104ff3003a52:T=1750873178:RT=1750874749:S=ALNI_MZ_je6CCIvH9wYCF4gBD055ULgJcA; __eoi=ID=298c2a40b37a9067:T=1750873178:RT=1750874749:S=AA-AfjY_afimCIoV8P5eQ0AbwBFh; FPGSID=1.1750873144.1750874749.G-B8CPBTKGPW.nSMyfxMj7o6f6KRwCL-mhA; lastRskxRun=1750874749468; c24-data=eyIzNiI6eyJlIjoiMTc4MjQwOTEzOCIsInYiOiIxNzUwODczMTM4Njg5In0sIjM3Ijp7ImUiOiIxNzgyNDA5MTM4IiwidiI6IjE3NTA4NzMxMzg2ODkifSwiMjciOnsiZSI6IjE3ODI0MDkxMzgiLCJ2IjoiMSJ9LCIzOCI6eyJlIjoiMTc4MjQwOTEzOCIsInYiOiIxNzQ4MTk0NzM4Njg5In0sIjIzMiI6eyJlIjoiMTc4MjQwOTE0MSIsInYiOiIxNzUwODczMTM5MDQ5In0sIjQ2NSI6eyJlIjoiMTg0NTQ4MTE0MiIsInYiOiIxODQ1NDgxMTQyOTA3In0sIjUiOnsiZSI6IjE3NTM0NjY3NTgiLCJ2IjoiNiJ9LCIxMTUiOnsiZSI6IjE3NjY0MjY3NDkiLCJ2IjoibGcifSwiNiI6eyJlIjoiMTc1MzQ2Njc1OCIsInYiOiI2In0sIjUxNCI6eyJlIjoiMTc4MjQwOTE3OCIsInYiOiIifSwiNTE1Ijp7ImUiOiIxNzgyNDA5MTc4IiwidiI6IjEifSwiNDEiOnsiZSI6IjE3ODI0MDkxMzgiLCJ2IjoiMTc1MDg3MzEzODAwMCJ9LCI5OCI6eyJlIjoiMTc4MjQxMDc1OCIsInYiOiI2In19; userHistory=31015533|1750874758613|2; _ga_B8CPBTKGPW=GS2.1.s1750873143$o1$g1$t1750874758$j50$l0$h660537393',
}

params = {
    'dealerId': '23037',
    'size': '5',
    'offset': '0',
    'stars': '0',
    'sorting': 'Relevance',
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


response = requests.get('https://www.chrono24.com/api/merchant/ratings.json',
                        params=params,
                        cookies=cookies,
                        headers=headers,
                        proxies=get_proxies(),
                        verify=False
                        )

print (response.text)
