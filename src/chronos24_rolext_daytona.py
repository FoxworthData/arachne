import os

import requests

from dotenv import load_dotenv


load_dotenv()

import requests

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
    'userHistory': '31015533|1750874747900|1',
    'cfctGroup': 'AAAESIV00%3D%26TCRTII01%3D%26ABSI01%3D%26CDCO01%3D%26LTRS00%3D%26AAAISIV00%3D',
    'c24-data': 'eyI1Ijp7ImUiOiIxNzUzNDY2NzQ3IiwidiI6IjUifSwiNiI6eyJlIjoiMTc1MzQ2Njc0NyIsInYiOiI1In0sIjI3Ijp7ImUiOiIxNzgyNDA5MTM4IiwidiI6IjEifSwiMzYiOnsiZSI6IjE3ODI0MDkxMzgiLCJ2IjoiMTc1MDg3MzEzODY4OSJ9LCIzNyI6eyJlIjoiMTc4MjQwOTEzOCIsInYiOiIxNzUwODczMTM4Njg5In0sIjM4Ijp7ImUiOiIxNzgyNDA5MTM4IiwidiI6IjE3NDgxOTQ3Mzg2ODkifSwiNDEiOnsiZSI6IjE3ODI0MDkxMzgiLCJ2IjoiMTc1MDg3MzEzODAwMCJ9LCI5OCI6eyJlIjoiMTc4MjQxMDc0NyIsInYiOiI1In0sIjExNSI6eyJ2IjoibGciLCJlIjoiMTc2NjQyNjc0OSJ9LCIyMzIiOnsiZSI6IjE3ODI0MDkxNDEiLCJ2IjoiMTc1MDg3MzEzOTA0OSJ9LCI0NjUiOnsiZSI6IjE4NDU0ODExNDIiLCJ2IjoiMTg0NTQ4MTE0MjkwNyJ9LCI1MTQiOnsiZSI6IjE3ODI0MDkxNzgiLCJ2IjoiIn0sIjUxNSI6eyJlIjoiMTc4MjQwOTE3OCIsInYiOiIxIn19',
    '_ga_B8CPBTKGPW': 'GS2.1.s1750873143$o1$g1$t1750874748$j60$l0$h660537393',
    '__gads': 'ID=ed4a5c6d0e7b335d:T=1750873178:RT=1750874749:S=ALNI_MZqXK9RqmArPVLuI_igEiL787xWbg',
    '__gpi': 'UID=0000104ff3003a52:T=1750873178:RT=1750874749:S=ALNI_MZ_je6CCIvH9wYCF4gBD055ULgJcA',
    '__eoi': 'ID=298c2a40b37a9067:T=1750873178:RT=1750874749:S=AA-AfjY_afimCIoV8P5eQ0AbwBFh',
    'FPGSID': '1.1750873144.1750874749.G-B8CPBTKGPW.nSMyfxMj7o6f6KRwCL-mhA',
    'lastRskxRun': '1750874749468',
}

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    # 'cookie': 'chronosessid=59d050c0-9580-46a2-929b-5b7e8046e34a; filter-combinations=1:Man,0:; csrf-token=1750873138.kjVKxVhnuhzwHM-cJePm0K8uBSc3JdBQDjwjaMTqyU0.AXG1VdibBGy9lHJuvCJVXLZtwhpn; __cflb=0H28vBCZxXf5QcKQeSUz1bT3jumYpMsK3TxtJri7QqA; timezone=America/Chicago; __ssid=6f38d0544dba3ec0a01f68fce9ca2ae; rskxRunCookie=0; rCookie=gueldyqi84kqjxa6ezswbqmcc8ntmy; c24-consent=AAEAJo/nwEhO; catalog-switcher-state=listings; catalog-switcher-hint=catalogSwitchHintDisplayed; _ga=GA1.1.566637698.1750873144; _fbp=fb.1.1750873143634.67016769358054055; _hjSession_72519=eyJpZCI6IjBiZmRlMmE2LTc4MTYtNGI0OC04M2RjLTViYmRiMDhmOTgzYSIsImMiOjE3NTA4NzMxNDQwNDMsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjoxLCJzcCI6MX0=; FPID=FPID2.2.1%2Fw6HbXKORl0iuL085IDbh8P0Qjg%2FR%2FdNd4zVqm5Lf4%3D.1750873144; FPLC=sFPo7pDZXte%2FStls92gTIKN%2B9yHiYYq5SU%2B1Qx1zBsfrsco%2B6TFHCO%2FBszxaDnEmxf8AIz3r6%2FZcOqOd5p8FkCbiItuQmYcabbcGmN%2BGScQJpYBA04rzFTFO8v0Gsg%3D%3D; FPAU=1.2.2109597400.1750873144; last-search-result-ids=41021143.41113958.41135137.41111846.38709578.23988054.40708879.40855418.41000857.40773459.40884461.40723800.38689626.40936019.36091299.40711598.41017358.41012948.40616428.41151461.41002715.30265922.40417083.39035263.35733142.38656635.40586357.30268545.38358648.40080099.40550670.39256789.39315600.40430540.40307752.38105884.40574476.40974957.40855455.40449726.40655680.40324204.40884357.38899267.38986311.40449755.37904140.40840713.38878868.40456611.38804848.40449787.38641810.40555765.40708207.39467129.40360548.17339263.40463035.40835614; _hjSessionUser_72519=eyJpZCI6IjAzYzc3MjlmLTY3NTQtNWVjYS05MTc2LWJlZDFmMjI5YzU5ZSIsImNyZWF0ZWQiOjE3NTA4NzMxNDQwNDIsImV4aXN0aW5nIjp0cnVlfQ==; _hjDonePolls=1565214; userHistory=31015533|1750874747900|1; cfctGroup=AAAESIV00%3D%26TCRTII01%3D%26ABSI01%3D%26CDCO01%3D%26LTRS00%3D%26AAAISIV00%3D; c24-data=eyI1Ijp7ImUiOiIxNzUzNDY2NzQ3IiwidiI6IjUifSwiNiI6eyJlIjoiMTc1MzQ2Njc0NyIsInYiOiI1In0sIjI3Ijp7ImUiOiIxNzgyNDA5MTM4IiwidiI6IjEifSwiMzYiOnsiZSI6IjE3ODI0MDkxMzgiLCJ2IjoiMTc1MDg3MzEzODY4OSJ9LCIzNyI6eyJlIjoiMTc4MjQwOTEzOCIsInYiOiIxNzUwODczMTM4Njg5In0sIjM4Ijp7ImUiOiIxNzgyNDA5MTM4IiwidiI6IjE3NDgxOTQ3Mzg2ODkifSwiNDEiOnsiZSI6IjE3ODI0MDkxMzgiLCJ2IjoiMTc1MDg3MzEzODAwMCJ9LCI5OCI6eyJlIjoiMTc4MjQxMDc0NyIsInYiOiI1In0sIjExNSI6eyJ2IjoibGciLCJlIjoiMTc2NjQyNjc0OSJ9LCIyMzIiOnsiZSI6IjE3ODI0MDkxNDEiLCJ2IjoiMTc1MDg3MzEzOTA0OSJ9LCI0NjUiOnsiZSI6IjE4NDU0ODExNDIiLCJ2IjoiMTg0NTQ4MTE0MjkwNyJ9LCI1MTQiOnsiZSI6IjE3ODI0MDkxNzgiLCJ2IjoiIn0sIjUxNSI6eyJlIjoiMTc4MjQwOTE3OCIsInYiOiIxIn19; _ga_B8CPBTKGPW=GS2.1.s1750873143$o1$g1$t1750874748$j60$l0$h660537393; __gads=ID=ed4a5c6d0e7b335d:T=1750873178:RT=1750874749:S=ALNI_MZqXK9RqmArPVLuI_igEiL787xWbg; __gpi=UID=0000104ff3003a52:T=1750873178:RT=1750874749:S=ALNI_MZ_je6CCIvH9wYCF4gBD055ULgJcA; __eoi=ID=298c2a40b37a9067:T=1750873178:RT=1750874749:S=AA-AfjY_afimCIoV8P5eQ0AbwBFh; FPGSID=1.1750873144.1750874749.G-B8CPBTKGPW.nSMyfxMj7o6f6KRwCL-mhA; lastRskxRun=1750874749468',
}

params = {
    'searchHash': 'c475e71b_WyF3LO',
    'pos': '22',
    'catalogTestBadge': 'TCRT_01_listing_true',
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
    'https://www.chrono24.com/rolex/rolex-daytona---116519ln-meteorite-dial-new-2023--id31015533.htm',
    params=params,
    cookies=cookies,
    headers=headers,
                        proxies=get_proxies(),
                        verify=False
)

# Save response text to a file
with open('rolex_daytona.html', 'w', encoding='utf-8') as file:
    file.write(response.text)