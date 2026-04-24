import asyncio
import os
import re
import time
from typing import Dict, Any

import requests
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.curlconverter.walmart.walmart_home_page import load_search_by_query
from src.utils.header_builders import WalmartHeaderBuilder
from src.utils.proxy_builder_simple import get_proxies, get_proxy_components
from src.utils.retailer_factory import RetailerBundle
from src.utils.setup_config_logging import setup_config_logging
from src.utils.browser_personas import BrowserPersonaChooser, BrowserPersona
from src.utils.yaml_util import load_store_by_id

load_dotenv()

logger, logger_manager, project_config = setup_config_logging(__name__)

browser_persona_chooser = BrowserPersonaChooser()
# browser_persona = browser_persona_chooser.get_random_persona()
browser_persona = browser_persona_chooser.get_persona(os_name='Windows', browser_name='Chrome')

logger.info(f"Using browser persona: {browser_persona.persona_id}")

cookies = {
    '_pxvid': '5d92bb41-d769-11ef-b5ae-c8c9d555910f',
    'vtc': 'dd9PPd4ei-FkppMZKF3QpI',
    'ACID': 'da6245c7-0a44-41f2-a733-731749b1af0f',
    '_m': '9',
    'hasACID': 'true',
    'io_id': '8c94023f-303d-47be-b9ea-36ee3a7d2a58',
    'abqme': 'true',
    'AID': 'wmlspartner=0:reflectorid=0000000000000000000000:lastupd=1748369091276',
    '_pxhd': 'fc2f1cefdde9edb77d9501997e345c5ba5fd2e221acf617bb6760edfb05b9a18:5d92bb41-d769-11ef-b5ae-c8c9d555910f',
    'pxcts': 'dc3a32e9-577f-11f0-8c7a-dfac7eec1b08',
    'wmlh': '556303ce56b6e07f3d71d778211ead9ca72498a4f197a9ca3b62304bdee2e1cf',
    'isoLoc': 'US_TX_t3',
    '_astc': '73989f425a2b378b108b6e4581a630bc',
    'adblocked': 'false',
    'hasLocData': '1',
    'userAppVersion': 'usweb-1.220.0-ada3f07b1e1f576f89fca794606c73b0cd2ce649-8211424r',
    'assortmentStoreId': '1198',
    'locDataV3': 'eyJpc0RlZmF1bHRlZCI6ZmFsc2UsImluc3RvcmUiOmZhbHNlLCJpbnRlbnQiOiJQSUNLVVAiLCJwaWNrdXAiOlt7Im5vZGVJZCI6IjExOTgiLCJkaXNwbGF5TmFtZSI6IlNhbiBBbnRvbmlvIFN1cGVyY2VudGVyIiwiYWRkcmVzcyI6eyJwb3N0YWxDb2RlIjoiNzgyMzIiLCJhZGRyZXNzTGluZTEiOiIxNTE1IE4gTE9PUCAxNjA0IEUiLCJjaXR5IjoiU2FuIEFudG9uaW8iLCJzdGF0ZSI6IlRYIiwiY291bnRyeSI6IlVTIn0sImdlb1BvaW50Ijp7ImxhdGl0dWRlIjoyOS42MTI0MTEsImxvbmdpdHVkZSI6LTk4LjQ3MDcyMX0sInNjaGVkdWxlZEVuYWJsZWQiOnRydWUsInVuU2NoZWR1bGVkRW5hYmxlZCI6dHJ1ZSwic3RvcmVIcnMiOiIwNjowMC0yMzowMCIsImFsbG93ZWRXSUNBZ2VuY2llcyI6WyJUWCJdLCJzdXBwb3J0ZWRBY2Nlc3NUeXBlcyI6WyJQSUNLVVBfSU5TVE9SRSIsIkFDQ19JTkdST1VORCIsIlBJQ0tVUF9TUEVDSUFMX0VWRU5UIiwiUElDS1VQX0JBS0VSWSIsIlBJQ0tVUF9DVVJCU0lERSIsIkFDQyJdLCJ0aW1lWm9uZSI6IkFtZXJpY2EvQ2hpY2FnbyIsInN0b3JlQnJhbmRGb3JtYXQiOiJXYWxtYXJ0IFN1cGVyY2VudGVyIiwic2VsZWN0aW9uVHlwZSI6IkNVU1RPTUVSX1NFTEVDVEVEIn0seyJub2RlSWQiOiI0MTYyIn0seyJub2RlSWQiOiIxODAzIn0seyJub2RlSWQiOiIyNDA0In0seyJub2RlSWQiOiI3NjUifSx7Im5vZGVJZCI6IjEzNDcifSx7Im5vZGVJZCI6IjI1OTkifSx7Im5vZGVJZCI6IjUxNDUifSx7Im5vZGVJZCI6IjI3NjkifV0sInNoaXBwaW5nQWRkcmVzcyI6eyJsYXRpdHVkZSI6MjkuNTg3OSwibG9uZ2l0dWRlIjotOTguNDcyLCJwb3N0YWxDb2RlIjoiNzgyMzIiLCJjaXR5IjoiU2FuIEFudG9uaW8iLCJzdGF0ZSI6IlRYIiwiY291bnRyeUNvZGUiOiJVU0EiLCJnaWZ0QWRkcmVzcyI6ZmFsc2UsInRpbWVab25lIjoiQW1lcmljYS9DaGljYWdvIiwiYWxsb3dlZFdJQ0FnZW5jaWVzIjpbIlRYIl19LCJhc3NvcnRtZW50Ijp7Im5vZGVJZCI6IjExOTgiLCJkaXNwbGF5TmFtZSI6IlNhbiBBbnRvbmlvIFN1cGVyY2VudGVyIiwiaW50ZW50IjoiUElDS1VQIn0sImlzRXhwbGljaXQiOmZhbHNlLCJkZWxpdmVyeSI6eyJub2RlSWQiOiIxMTk4IiwiZGlzcGxheU5hbWUiOiJTYW4gQW50b25pbyBTdXBlcmNlbnRlciIsImFkZHJlc3MiOnsicG9zdGFsQ29kZSI6Ijc4MjMyIiwiYWRkcmVzc0xpbmUxIjoiMTUxNSBOIExPT1AgMTYwNCBFIiwiY2l0eSI6IlNhbiBBbnRvbmlvIiwic3RhdGUiOiJUWCIsImNvdW50cnkiOiJVUyJ9LCJnZW9Qb2ludCI6eyJsYXRpdHVkZSI6MjkuNjEyNDExLCJsb25naXR1ZGUiOi05OC40NzA3MjF9LCJzY2hlZHVsZWRFbmFibGVkIjpmYWxzZSwidW5TY2hlZHVsZWRFbmFibGVkIjpmYWxzZSwiYWNjZXNzUG9pbnRzIjpbeyJhY2Nlc3NUeXBlIjoiREVMSVZFUllfQUREUkVTUyJ9XSwiaXNFeHByZXNzRGVsaXZlcnlPbmx5IjpmYWxzZSwiYWxsb3dlZFdJQ0FnZW5jaWVzIjpbIlRYIl0sInN1cHBvcnRlZEFjY2Vzc1R5cGVzIjpbIkRFTElWRVJZX0FERFJFU1MiLCJBQ0MiXSwidGltZVpvbmUiOiJBbWVyaWNhL0NoaWNhZ28iLCJzdG9yZUJyYW5kRm9ybWF0IjoiV2FsbWFydCBTdXBlcmNlbnRlciIsInNlbGVjdGlvblR5cGUiOiJMU19TRUxFQ1RFRCJ9LCJyZWZyZXNoQXQiOjE3NTYwOTExODE0ODQsImlzZ2VvSW50bFVzZXIiOmZhbHNlLCJtcERlbFN0b3JlQ291bnQiOjIwLCJtcHMiOlsiMTUyMzcwMiIsIjE1MjM3MDUiLCIxNTIyODE1IiwiMTUyMzY1MyIsIjE1MjIxMDYiLCIxNTI1MTQyIiwiMTUyMzQyMyIsIjE1MjM3MDQiLCIxNTIzNTk1IiwiMTUxOTYxNCIsIjE1MjExODEiLCIxNTIzNjIwIiwiMTUyMzU3MiIsIjE1MjM1NzQiLCIxNTIzNDE5IiwiMTUyMDQzMSIsIjE1MjM4OTQiLCIxNTIyNzY1IiwiMTUyMzY4NyIsIjEwMDAwMDEiLCIxNTI1MjA0IiwiMTUxOTEwMiIsIjE1MjM1NzciLCIxNTIyODcxIiwiMTUyMjAyOCIsIjE1MjMzNDYiLCIxNTIyNjg4IiwiMTUyMzc0MyIsIjE1MjM5OTMiLCIxNTIzOTk0IiwiMTUyMDA5NyIsIjE1MjM1MTEiLCIxNTIwNTA1IiwiMTUyMzU2MCIsIjE1MjA0NjAiLCIxNTIzNTkwIiwiMTUyMDMzMCIsIjE1MjIwMzciLCIxNTIzNjU4IiwiMTUxOTczNSIsIjE1MjM4MDYiLCIxNTI0NDE1IiwiMTUyMzU2OSIsIjE1MjM2ODkiLCIxNTIzNjUyIiwiMTUyMzY0MCIsIjE1MjM2MzQiLCIxNTIzNzc0IiwiMTUyMDYyOSIsIjE1MjM2OTIiXSwibXBVbmlxdWVTZWxsZXJDb3VudCI6MCwic2hvd0xNUEVudHJ5UG9pbnQiOmZhbHNlLCJzaG93TG9jYWxFeHBlcmllbmNlIjpmYWxzZSwidmFsaWRhdGVLZXkiOiJwcm9kOnYyOmRhNjI0NWM3LTBhNDQtNDFmMi1hNzMzLTczMTc0OWIxYWYwZiJ9',
    'locGuestData': 'eyJpbnRlbnQiOiJQSUNLVVAiLCJpc0V4cGxpY2l0IjpmYWxzZSwic3RvcmVJbnRlbnQiOiJQSUNLVVAiLCJtZXJnZUZsYWciOnRydWUsImlzRGVmYXVsdGVkIjpmYWxzZSwicGlja3VwIjp7Im5vZGVJZCI6IjExOTgiLCJ0aW1lc3RhbXAiOjE3Mzc0MDMzMDE5MDEsInNlbGVjdGlvblR5cGUiOiJDVVNUT01FUl9TRUxFQ1RFRCIsInNlbGVjdGlvblNvdXJjZSI6IlBpY2t1cCBTdG9yZSBTZWxlY3RvciJ9LCJzaGlwcGluZ0FkZHJlc3MiOnsidGltZXN0YW1wIjoxNzM3NDAzMzAxOTAxLCJ0eXBlIjoicGFydGlhbC1sb2NhdGlvbiIsImdpZnRBZGRyZXNzIjpmYWxzZSwicG9zdGFsQ29kZSI6Ijc4MjMyIiwiZGVsaXZlcnlTdG9yZUxpc3QiOlt7Im5vZGVJZCI6IjExOTgiLCJ0eXBlIjoiREVMSVZFUlkiLCJ0aW1lc3RhbXAiOjE3NTYwNjk1ODE0NTQsImRlbGl2ZXJ5VGllciI6bnVsbCwic2VsZWN0aW9uVHlwZSI6IkxTX1NFTEVDVEVEIiwic2VsZWN0aW9uU291cmNlIjoiWklQX0NPREVfQllfVVNFUiJ9XSwiY2l0eSI6IlNhbiBBbnRvbmlvIiwic3RhdGUiOiJUWCJ9LCJwb3N0YWxDb2RlIjp7InRpbWVzdGFtcCI6MTczNzQwMzMwMTkwMSwiYmFzZSI6Ijc4MjMyIn0sIm1wIjpbXSwibXNwIjp7Im5vZGVJZHMiOlsiNDE2MiIsIjE4MDMiLCIyNDA0IiwiNzY1IiwiMTM0NyIsIjI1OTkiLCI1MTQ1IiwiMjc2OSJdLCJ0aW1lc3RhbXAiOjE3NTYwNjk1ODE0MzJ9LCJtcHMiOlsiMTUyMzcwMiIsIjE1MjM3MDUiLCIxNTIyODE1IiwiMTUyMzY1MyIsIjE1MjIxMDYiLCIxNTI1MTQyIiwiMTUyMzQyMyIsIjE1MjM3MDQiLCIxNTIzNTk1IiwiMTUxOTYxNCIsIjE1MjExODEiLCIxNTIzNjIwIiwiMTUyMzU3MiIsIjE1MjM1NzQiLCIxNTIzNDE5IiwiMTUyMDQzMSIsIjE1MjM4OTQiLCIxNTIyNzY1IiwiMTUyMzY4NyIsIjEwMDAwMDEiLCIxNTI1MjA0IiwiMTUxOTEwMiIsIjE1MjM1NzciLCIxNTIyODcxIiwiMTUyMjAyOCIsIjE1MjMzNDYiLCIxNTIyNjg4IiwiMTUyMzc0MyIsIjE1MjM5OTMiLCIxNTIzOTk0IiwiMTUyMDA5NyIsIjE1MjM1MTEiLCIxNTIwNTA1IiwiMTUyMzU2MCIsIjE1MjA0NjAiLCIxNTIzNTkwIiwiMTUyMDMzMCIsIjE1MjIwMzciLCIxNTIzNjU4IiwiMTUxOTczNSIsIjE1MjM4MDYiLCIxNTI0NDE1IiwiMTUyMzU2OSIsIjE1MjM2ODkiLCIxNTIzNjUyIiwiMTUyMzY0MCIsIjE1MjM2MzQiLCIxNTIzNzc0IiwiMTUyMDYyOSIsIjE1MjM2OTIiXSwibXBEZWxTdG9yZUNvdW50IjoyMCwic2hvd0xvY2FsRXhwZXJpZW5jZSI6ZmFsc2UsInNob3dMTVBFbnRyeVBvaW50IjpmYWxzZSwibXBVbmlxdWVTZWxsZXJDb3VudCI6MCwidmFsaWRhdGVLZXkiOiJwcm9kOnYyOmRhNjI0NWM3LTBhNDQtNDFmMi1hNzMzLTczMTc0OWIxYWYwZiJ9',
    'akavpau_p1': '1756070181~id=2f148097902b39a967b4b7df0a8172af',
    'xptwj': 'uz:0058fcc3aede5c43559d:o5N5r/KdsUDFSB6Wq+j0heQeY1eB/Yth/+lmlt4qlBWQtgy/NrmaejLuYoWs4zeTr7rkYmoq34ZIkqy1mfYv5rVUlxhXbKq1+C8/yyaRAkn0c4ja/YJBRKKFv7rw41RkDP/16X+d2Z7TcPyBjZAIAOOH8B7kjlWSqV2v2+KBowp1K+oqaTUKy9jVLco7xoftDWfshhIRb/wqDYUJfkdS7EG9',
    'bstc': 'dEpqYBsdQ_iSwusr4ZgaLE',
    '__cf_bm': 'LvM_olOUR6ztJGOcGz1.XVbpX95_Ro1F02P.PxAG8oI-1756138761-1.0.1.1-9cRMlUL9O4SD4LTfN7YzWmTV.0NkizKQXdAckV1x73WtKPiQtwGGy6fIOvV_M7XdCaNpA5IKAlKJkFvgT0DLlckjxBAUCOQPvB3wSsdvIAPX6R6oRHIOCHWN1hMEhJSb',
    'com.wm.reflector': '"reflectorid:0000000000000000000000@lastupd:1756138762000@firstcreate:1738075562989"',
    'xptc': 'assortmentStoreId%2B1198~_m%2B9',
    'xpth': 'x-o-mart%2BB2C~x-o-mverified%2Bfalse',
    'xpa': '086BP|1bezR|3VCVY|5_EoH|8Kkdx|9Yd9_|ArsR1|Avpka|EFPmM|E_gpz|J-MZ4|Mx7J7|O_ewj|QPToB|RuVdg|TKwVE|ToJIM|_wRhm|a43Wd|aYAez|bFvEw|c_oVZ|eOpcH|fXtQf|fdm-7|fkq_L|hsomz|imMMk|jKJLU|jM1ax|kyO7M|lmqpp|mAZQB|mIxD_|pAaPn|rTu67|suTY7|wY6LG|wdV3R|y1Ld_',
    'xpm': '0%2B1756138762%2Bdd9PPd4ei-FkppMZKF3QpI~%2B0',
    'exp-ck': '086BP11bezR19Yd9_2ArsR13Avpka1EFPmM1E_gpz1J-MZ41Mx7J71QPToB1ToJIM1a43Wd1aYAez2c_oVZ1fXtQf1fdm-71fkq_L1hsomztimMMk1kyO7M1lmqpp1mIxD_2rTu675wY6LG2wdV3R1y1Ld_4',
    'xptwg': '3820783523:B7BFE87EB99338:1C164EF:FF323B83:15C752F8:AEADB0F6:',
    'TS01a90220': '018481d4b852bbcb983d9a69c74bd27b1db5754e685c227b4d1e619a216cea3d5b245012957c20a2c9e2cccab116f82cc52ec7eca0',
    'TS012768cf': '016aac771866b58283cf5594bd08f4a635e42046f26bbb042d65f272f4fef449710eaccab9e78b8d02f5a5631bf77e800bb91fde9c',
    'TS2a5e0c5c027': '088fbc6647ab2000cd0962d31c1b0011bea97d2d30e2a0b59471599b9ca76984195ec1c48253c55b08164780c511300066aefd6230e4bb6f409585c9bbf0a0b1303cae1032631eb5ef932d52b17bfd82c3bf8116529ffbbf9aa8d54ef5d1dec6',
    'akavpau_p2': '1756139370~id=ec93559772e2dda422cc8e64405230fe',
    'bm_mi': '905CFCC46B526BE77E101886546F68E2~YAAQ0iXAF9KgAciYAQAAuA8H4hxWZcf1SLAGCOxkjJ0ER45sV7lX/f8+YFKDY2h3p4JZQtnu/2Rlkqo05lpvBkw4Fx50oLOuQtf3f8ja113gDKxcmMY4tBZvbnTAlwi5HYHu7pa0iETmDLrjl97kLvI7DkhCmBkM+W5wFrpvbnJopCIgrfjQwS4/Bs5KSXEqY/4G4zN6pYWv1Q5Fa0WDSTKQOMuCwRGxfeBmSEdsLUoYzALJWr2JFn9dG0jGq3IJHC6/a+m24/wQ8FITHDDzU/8luk5r5ulunhuSGoGYbSlHmbbrQ8W01R8Hr3xXye1lsFdPXis3~1',
    'ak_bmsc': '99F112B27B2585093324CCFCD9595DEE~000000000000000000000000000000~YAAQ0iXAF+WnAciYAQAAzhgH4hzFCtaDx+ydjoxqC/6fwhNN9bNzLswP6X2bYxZrKDZhURzC7NqEXbhGAWJG23gfrIe0z5fJWNynnRyWraq+phqc4ZYDc2HebkkftMRLe0vtqb1xfsnTUv8KNhYzYniEYxzNSJchwyYXxqnsc/fA+WAA1EO8/+ijIF3sGUnwz3vpaD8ctbGE+KXsd6QP++Wtlrc3AsxjJIvRkzlgoif19+k7qaPQLuhP3WTfnpVWK7l55DMcw932X2b0Et7L6PnYC9PCJBvx6X1LUkeUdS2oNMfFL9eK0rLuF8iIEmCRqiGP7I8aCu59FnAgP+7WDHSC0rYMAq/X5flmjUXOvfQ5KpYABtqs7AglOPAT1fpTrd38T8li1AHQmbuDPq2Jwbk/ELOexhjFgFhArtYFQmZGfGWfT5laM9v2OdKQTtki3e7MuPLq3UlQGcYMmxlhEIo/U48zwPrYFFsXBt9Pb9EXck0MPEUg/w==',
    'if_id': 'FMEZARSF3rtaobWC+7qcI29gUrKUShTXbBM/YnedldqDj1V9xjF9yD5nT/xW2sWUIfJoi/2qqg/4rL2XjPDCNa2fZh9MV6XLWkojqUH/KyijKJhkHrT+X92L4kFJ7ljt3tVocX1+YNSZaxMatjUsAoL3zYsclFrWhg2F69mSHBuHDpHnkJuyyUsJPI9TpzMNNF8+Oi0fx81EhP42alf6ry54ooNtrIk0UY5MTH+I/7TvXBGfgi1VKtHVUSZC9iCyxR8TXnNEYJhuKrPYIT+4jNSqKr3KpsphrID4SwCyV6rGqrtz0VUgMmSQ4AZqWP98JSRjh1O+IBNT6ui6w+BicGfE6sYr6A==',
    'TS016ef4c8': '01a45e1c891407286af8e2222d9db70b465503657781480d5be5203417c9fef5336736f5306a5ba22c781077c4357563c0d5b91c0b',
    'TS01f89308': '01a45e1c891407286af8e2222d9db70b465503657781480d5be5203417c9fef5336736f5306a5ba22c781077c4357563c0d5b91c0b',
    'TS8cb5a80e027': '089bdf021fab2000235286022a6b23806696079efcc29bca337bfe2d7943d9abda896905a7b9d72908497247871130009b9b1cd967e44ce5221112a6caf8fa9bd7737624208987cd4ad8601468d33a0eebb02cfc55a84d17eea7db8bd6f55d47',
    'bm_sv': '047529B422E94AFD8B274B8DE8B2D724~YAAQ0iXAFzmuAciYAQAAjSEH4hzC8btSWtTknzzVI9E/fpzg0FLhbQyE6bp8V2ff0jJOUHtt4R2hDsohGCkMYzqirLJR9MPkJORTNKxh6mEWIjU/CRpzt0VfIYCSuz9PlNeyxhPwNY/JNB4CFyJeEO6Js9Gicug3/Eh3GbJQ7Yu3YZt5KKooIbeHfy0pTA329oppZwIl0vCQtBXh1JGtZ11+2Cyk4uKQK55Z6HwEqjUKlRFaCW82y5DNUIwe9G10YA==~1',
    '_px3': 'afe0c7157274adce650b011de8de3646078a36ce70747c10a572fe8a4b7bb449:f7g1MGaZgy1EWQcBa4l4PgfCdQaewxZYK8mGmzIlFI71RA6MFn0CQPqOE98PbZNMRRCLN9s8/niLFh8dOI5++Q==:1000:IdvtbjiljFNFJUxhtTKmWi0+KsbgeaExZKJs2/iDZKDDHSGgKGuIj2MSIlZ33g56qAVq0SV3+fCz0Hlb2GYnfq3gtyMvj7enAjRocT5QnqVQ+gFrHKrAYBFNzj4emUgI1bUTJF8HgvPJS284f1BXwvoYTRHGsC6F5MZtPR+mz2b2I79EV8osxvJKFi5RkT5SzPs0s3PfN9sacN960b8sFtSp4OVZ0a0wD2pyNS7wcD4=',
    '_pxde': '217041e87108d995ef9a1f90264413b2aabf885fd20400f60ae6e7da8e18b3ce:eyJ0aW1lc3RhbXAiOjE3NTYxMzg3ODUwNzh9',
}


trimmed_cookies = {
    # '_pxvid': '5d92bb41-d769-11ef-b5ae-c8c9d555910f',
    # 'vtc': 'dd9PPd4ei-FkppMZKF3QpI',

### CRITICAL ###
    'ACID': 'da6245c7-0a44-41f2-a733-731749b1af0f',  ### CRITICAL ###
    # '_m': '9',

### CRITICAL ###
    'hasACID': 'true',  ### CRITICAL ###
### WATCH - linked to _astc and if_id ###
    # 'io_id': '8c94023f-303d-47be-b9ea-36ee3a7d2a58',
    # 'abqme': 'true',
### WATCH linked to com.wm.reflector ###
    # 'AID': 'wmlspartner=0:reflectorid=0000000000000000000000:lastupd=1748369091276',
    # '_pxhd': 'fc2f1cefdde9edb77d9501997e345c5ba5fd2e221acf617bb6760edfb05b9a18:5d92bb41-d769-11ef-b5ae-c8c9d555910f',
    # 'pxcts': 'dc3a32e9-577f-11f0-8c7a-dfac7eec1b08',
    # 'wmlh': '556303ce56b6e07f3d71d778211ead9ca72498a4f197a9ca3b62304bdee2e1cf',
    # 'isoLoc': 'US_TX_t3',
### WATCH - linked to io_id and if_id ###
    # '_astc': '73989f425a2b378b108b6e4581a630bc',
    'adblocked': 'false',

### CRITICAL ###
    'hasLocData': '1',  ### CRITICAL ###
    # 'userAppVersion': 'usweb-1.220.0-ada3f07b1e1f576f89fca794606c73b0cd2ce649-8211424r',

### CRITICAL ###
    'assortmentStoreId': '1198',  ### CRITICAL ###
### CRITICAL ###
    'locDataV3': 'eyJpc0RlZmF1bHRlZCI6ZmFsc2UsImluc3RvcmUiOmZhbHNlLCJpbnRlbnQiOiJQSUNLVVAiLCJwaWNrdXAiOlt7Im5vZGVJZCI6IjExOTgiLCJkaXNwbGF5TmFtZSI6IlNhbiBBbnRvbmlvIFN1cGVyY2VudGVyIiwiYWRkcmVzcyI6eyJwb3N0YWxDb2RlIjoiNzgyMzIiLCJhZGRyZXNzTGluZTEiOiIxNTE1IE4gTE9PUCAxNjA0IEUiLCJjaXR5IjoiU2FuIEFudG9uaW8iLCJzdGF0ZSI6IlRYIiwiY291bnRyeSI6IlVTIn0sImdlb1BvaW50Ijp7ImxhdGl0dWRlIjoyOS42MTI0MTEsImxvbmdpdHVkZSI6LTk4LjQ3MDcyMX0sInNjaGVkdWxlZEVuYWJsZWQiOnRydWUsInVuU2NoZWR1bGVkRW5hYmxlZCI6dHJ1ZSwic3RvcmVIcnMiOiIwNjowMC0yMzowMCIsImFsbG93ZWRXSUNBZ2VuY2llcyI6WyJUWCJdLCJzdXBwb3J0ZWRBY2Nlc3NUeXBlcyI6WyJQSUNLVVBfSU5TVE9SRSIsIkFDQ19JTkdST1VORCIsIlBJQ0tVUF9TUEVDSUFMX0VWRU5UIiwiUElDS1VQX0JBS0VSWSIsIlBJQ0tVUF9DVVJCU0lERSIsIkFDQyJdLCJ0aW1lWm9uZSI6IkFtZXJpY2EvQ2hpY2FnbyIsInN0b3JlQnJhbmRGb3JtYXQiOiJXYWxtYXJ0IFN1cGVyY2VudGVyIiwic2VsZWN0aW9uVHlwZSI6IkNVU1RPTUVSX1NFTEVDVEVEIn0seyJub2RlSWQiOiI0MTYyIn0seyJub2RlSWQiOiIxODAzIn0seyJub2RlSWQiOiIyNDA0In0seyJub2RlSWQiOiI3NjUifSx7Im5vZGVJZCI6IjEzNDcifSx7Im5vZGVJZCI6IjI1OTkifSx7Im5vZGVJZCI6IjUxNDUifSx7Im5vZGVJZCI6IjI3NjkifV0sInNoaXBwaW5nQWRkcmVzcyI6eyJsYXRpdHVkZSI6MjkuNTg3OSwibG9uZ2l0dWRlIjotOTguNDcyLCJwb3N0YWxDb2RlIjoiNzgyMzIiLCJjaXR5IjoiU2FuIEFudG9uaW8iLCJzdGF0ZSI6IlRYIiwiY291bnRyeUNvZGUiOiJVU0EiLCJnaWZ0QWRkcmVzcyI6ZmFsc2UsInRpbWVab25lIjoiQW1lcmljYS9DaGljYWdvIiwiYWxsb3dlZFdJQ0FnZW5jaWVzIjpbIlRYIl19LCJhc3NvcnRtZW50Ijp7Im5vZGVJZCI6IjExOTgiLCJkaXNwbGF5TmFtZSI6IlNhbiBBbnRvbmlvIFN1cGVyY2VudGVyIiwiaW50ZW50IjoiUElDS1VQIn0sImlzRXhwbGljaXQiOmZhbHNlLCJkZWxpdmVyeSI6eyJub2RlSWQiOiIxMTk4IiwiZGlzcGxheU5hbWUiOiJTYW4gQW50b25pbyBTdXBlcmNlbnRlciIsImFkZHJlc3MiOnsicG9zdGFsQ29kZSI6Ijc4MjMyIiwiYWRkcmVzc0xpbmUxIjoiMTUxNSBOIExPT1AgMTYwNCBFIiwiY2l0eSI6IlNhbiBBbnRvbmlvIiwic3RhdGUiOiJUWCIsImNvdW50cnkiOiJVUyJ9LCJnZW9Qb2ludCI6eyJsYXRpdHVkZSI6MjkuNjEyNDExLCJsb25naXR1ZGUiOi05OC40NzA3MjF9LCJzY2hlZHVsZWRFbmFibGVkIjpmYWxzZSwidW5TY2hlZHVsZWRFbmFibGVkIjpmYWxzZSwiYWNjZXNzUG9pbnRzIjpbeyJhY2Nlc3NUeXBlIjoiREVMSVZFUllfQUREUkVTUyJ9XSwiaXNFeHByZXNzRGVsaXZlcnlPbmx5IjpmYWxzZSwiYWxsb3dlZFdJQ0FnZW5jaWVzIjpbIlRYIl0sInN1cHBvcnRlZEFjY2Vzc1R5cGVzIjpbIkRFTElWRVJZX0FERFJFU1MiLCJBQ0MiXSwidGltZVpvbmUiOiJBbWVyaWNhL0NoaWNhZ28iLCJzdG9yZUJyYW5kRm9ybWF0IjoiV2FsbWFydCBTdXBlcmNlbnRlciIsInNlbGVjdGlvblR5cGUiOiJMU19TRUxFQ1RFRCJ9LCJyZWZyZXNoQXQiOjE3NTYwOTExODE0ODQsImlzZ2VvSW50bFVzZXIiOmZhbHNlLCJtcERlbFN0b3JlQ291bnQiOjIwLCJtcHMiOlsiMTUyMzcwMiIsIjE1MjM3MDUiLCIxNTIyODE1IiwiMTUyMzY1MyIsIjE1MjIxMDYiLCIxNTI1MTQyIiwiMTUyMzQyMyIsIjE1MjM3MDQiLCIxNTIzNTk1IiwiMTUxOTYxNCIsIjE1MjExODEiLCIxNTIzNjIwIiwiMTUyMzU3MiIsIjE1MjM1NzQiLCIxNTIzNDE5IiwiMTUyMDQzMSIsIjE1MjM4OTQiLCIxNTIyNzY1IiwiMTUyMzY4NyIsIjEwMDAwMDEiLCIxNTI1MjA0IiwiMTUxOTEwMiIsIjE1MjM1NzciLCIxNTIyODcxIiwiMTUyMjAyOCIsIjE1MjMzNDYiLCIxNTIyNjg4IiwiMTUyMzc0MyIsIjE1MjM5OTMiLCIxNTIzOTk0IiwiMTUyMDA5NyIsIjE1MjM1MTEiLCIxNTIwNTA1IiwiMTUyMzU2MCIsIjE1MjA0NjAiLCIxNTIzNTkwIiwiMTUyMDMzMCIsIjE1MjIwMzciLCIxNTIzNjU4IiwiMTUxOTczNSIsIjE1MjM4MDYiLCIxNTI0NDE1IiwiMTUyMzU2OSIsIjE1MjM2ODkiLCIxNTIzNjUyIiwiMTUyMzY0MCIsIjE1MjM2MzQiLCIxNTIzNzc0IiwiMTUyMDYyOSIsIjE1MjM2OTIiXSwibXBVbmlxdWVTZWxsZXJDb3VudCI6MCwic2hvd0xNUEVudHJ5UG9pbnQiOmZhbHNlLCJzaG93TG9jYWxFeHBlcmllbmNlIjpmYWxzZSwidmFsaWRhdGVLZXkiOiJwcm9kOnYyOmRhNjI0NWM3LTBhNDQtNDFmMi1hNzMzLTczMTc0OWIxYWYwZiJ9',    ### CRITICAL ###
### CRITICAL ###
    'locGuestData': 'eyJpbnRlbnQiOiJQSUNLVVAiLCJpc0V4cGxpY2l0IjpmYWxzZSwic3RvcmVJbnRlbnQiOiJQSUNLVVAiLCJtZXJnZUZsYWciOnRydWUsImlzRGVmYXVsdGVkIjpmYWxzZSwicGlja3VwIjp7Im5vZGVJZCI6IjExOTgiLCJ0aW1lc3RhbXAiOjE3Mzc0MDMzMDE5MDEsInNlbGVjdGlvblR5cGUiOiJDVVNUT01FUl9TRUxFQ1RFRCIsInNlbGVjdGlvblNvdXJjZSI6IlBpY2t1cCBTdG9yZSBTZWxlY3RvciJ9LCJzaGlwcGluZ0FkZHJlc3MiOnsidGltZXN0YW1wIjoxNzM3NDAzMzAxOTAxLCJ0eXBlIjoicGFydGlhbC1sb2NhdGlvbiIsImdpZnRBZGRyZXNzIjpmYWxzZSwicG9zdGFsQ29kZSI6Ijc4MjMyIiwiZGVsaXZlcnlTdG9yZUxpc3QiOlt7Im5vZGVJZCI6IjExOTgiLCJ0eXBlIjoiREVMSVZFUlkiLCJ0aW1lc3RhbXAiOjE3NTYwNjk1ODE0NTQsImRlbGl2ZXJ5VGllciI6bnVsbCwic2VsZWN0aW9uVHlwZSI6IkxTX1NFTEVDVEVEIiwic2VsZWN0aW9uU291cmNlIjoiWklQX0NPREVfQllfVVNFUiJ9XSwiY2l0eSI6IlNhbiBBbnRvbmlvIiwic3RhdGUiOiJUWCJ9LCJwb3N0YWxDb2RlIjp7InRpbWVzdGFtcCI6MTczNzQwMzMwMTkwMSwiYmFzZSI6Ijc4MjMyIn0sIm1wIjpbXSwibXNwIjp7Im5vZGVJZHMiOlsiNDE2MiIsIjE4MDMiLCIyNDA0IiwiNzY1IiwiMTM0NyIsIjI1OTkiLCI1MTQ1IiwiMjc2OSJdLCJ0aW1lc3RhbXAiOjE3NTYwNjk1ODE0MzJ9LCJtcHMiOlsiMTUyMzcwMiIsIjE1MjM3MDUiLCIxNTIyODE1IiwiMTUyMzY1MyIsIjE1MjIxMDYiLCIxNTI1MTQyIiwiMTUyMzQyMyIsIjE1MjM3MDQiLCIxNTIzNTk1IiwiMTUxOTYxNCIsIjE1MjExODEiLCIxNTIzNjIwIiwiMTUyMzU3MiIsIjE1MjM1NzQiLCIxNTIzNDE5IiwiMTUyMDQzMSIsIjE1MjM4OTQiLCIxNTIyNzY1IiwiMTUyMzY4NyIsIjEwMDAwMDEiLCIxNTI1MjA0IiwiMTUxOTEwMiIsIjE1MjM1NzciLCIxNTIyODcxIiwiMTUyMjAyOCIsIjE1MjMzNDYiLCIxNTIyNjg4IiwiMTUyMzc0MyIsIjE1MjM5OTMiLCIxNTIzOTk0IiwiMTUyMDA5NyIsIjE1MjM1MTEiLCIxNTIwNTA1IiwiMTUyMzU2MCIsIjE1MjA0NjAiLCIxNTIzNTkwIiwiMTUyMDMzMCIsIjE1MjIwMzciLCIxNTIzNjU4IiwiMTUxOTczNSIsIjE1MjM4MDYiLCIxNTI0NDE1IiwiMTUyMzU2OSIsIjE1MjM2ODkiLCIxNTIzNjUyIiwiMTUyMzY0MCIsIjE1MjM2MzQiLCIxNTIzNzc0IiwiMTUyMDYyOSIsIjE1MjM2OTIiXSwibXBEZWxTdG9yZUNvdW50IjoyMCwic2hvd0xvY2FsRXhwZXJpZW5jZSI6ZmFsc2UsInNob3dMTVBFbnRyeVBvaW50IjpmYWxzZSwibXBVbmlxdWVTZWxsZXJDb3VudCI6MCwidmFsaWRhdGVLZXkiOiJwcm9kOnYyOmRhNjI0NWM3LTBhNDQtNDFmMi1hNzMzLTczMTc0OWIxYWYwZiJ9',    ### CRITICAL ###
    # 'akavpau_p1': '1756070181~id=2f148097902b39a967b4b7df0a8172af',
    # 'xptwj': 'uz:0058fcc3aede5c43559d:o5N5r/KdsUDFSB6Wq+j0heQeY1eB/Yth/+lmlt4qlBWQtgy/NrmaejLuYoWs4zeTr7rkYmoq34ZIkqy1mfYv5rVUlxhXbKq1+C8/yyaRAkn0c4ja/YJBRKKFv7rw41RkDP/16X+d2Z7TcPyBjZAIAOOH8B7kjlWSqV2v2+KBowp1K+oqaTUKy9jVLco7xoftDWfshhIRb/wqDYUJfkdS7EG9',
    # 'bstc': 'dEpqYBsdQ_iSwusr4ZgaLE',
    # '__cf_bm': 'LvM_olOUR6ztJGOcGz1.XVbpX95_Ro1F02P.PxAG8oI-1756138761-1.0.1.1-9cRMlUL9O4SD4LTfN7YzWmTV.0NkizKQXdAckV1x73WtKPiQtwGGy6fIOvV_M7XdCaNpA5IKAlKJkFvgT0DLlckjxBAUCOQPvB3wSsdvIAPX6R6oRHIOCHWN1hMEhJSb',
### WATCH - linked to AID ###
    # 'com.wm.reflector': '"reflectorid:0000000000000000000000@lastupd:1756138762000@firstcreate:1738075562989"',
    # 'xptc': 'assortmentStoreId%2B1198~_m%2B9',
    # 'xpth': 'x-o-mart%2BB2C~x-o-mverified%2Bfalse',
    # 'xpa': '086BP|1bezR|3VCVY|5_EoH|8Kkdx|9Yd9_|ArsR1|Avpka|EFPmM|E_gpz|J-MZ4|Mx7J7|O_ewj|QPToB|RuVdg|TKwVE|ToJIM|_wRhm|a43Wd|aYAez|bFvEw|c_oVZ|eOpcH|fXtQf|fdm-7|fkq_L|hsomz|imMMk|jKJLU|jM1ax|kyO7M|lmqpp|mAZQB|mIxD_|pAaPn|rTu67|suTY7|wY6LG|wdV3R|y1Ld_',
    # 'xpm': '0%2B1756138762%2Bdd9PPd4ei-FkppMZKF3QpI~%2B0',
    # 'exp-ck': '086BP11bezR19Yd9_2ArsR13Avpka1EFPmM1E_gpz1J-MZ41Mx7J71QPToB1ToJIM1a43Wd1aYAez2c_oVZ1fXtQf1fdm-71fkq_L1hsomztimMMk1kyO7M1lmqpp1mIxD_2rTu675wY6LG2wdV3R1y1Ld_4',
    # 'xptwg': '3820783523:B7BFE87EB99338:1C164EF:FF323B83:15C752F8:AEADB0F6:',
    # 'TS01a90220': '018481d4b852bbcb983d9a69c74bd27b1db5754e685c227b4d1e619a216cea3d5b245012957c20a2c9e2cccab116f82cc52ec7eca0',
    # 'TS012768cf': '016aac771866b58283cf5594bd08f4a635e42046f26bbb042d65f272f4fef449710eaccab9e78b8d02f5a5631bf77e800bb91fde9c',
    # 'TS2a5e0c5c027': '088fbc6647ab2000cd0962d31c1b0011bea97d2d30e2a0b59471599b9ca76984195ec1c48253c55b08164780c511300066aefd6230e4bb6f409585c9bbf0a0b1303cae1032631eb5ef932d52b17bfd82c3bf8116529ffbbf9aa8d54ef5d1dec6',
    # 'akavpau_p2': '1756139370~id=ec93559772e2dda422cc8e64405230fe',
    # 'bm_mi': '905CFCC46B526BE77E101886546F68E2~YAAQ0iXAF9KgAciYAQAAuA8H4hxWZcf1SLAGCOxkjJ0ER45sV7lX/f8+YFKDY2h3p4JZQtnu/2Rlkqo05lpvBkw4Fx50oLOuQtf3f8ja113gDKxcmMY4tBZvbnTAlwi5HYHu7pa0iETmDLrjl97kLvI7DkhCmBkM+W5wFrpvbnJopCIgrfjQwS4/Bs5KSXEqY/4G4zN6pYWv1Q5Fa0WDSTKQOMuCwRGxfeBmSEdsLUoYzALJWr2JFn9dG0jGq3IJHC6/a+m24/wQ8FITHDDzU/8luk5r5ulunhuSGoGYbSlHmbbrQ8W01R8Hr3xXye1lsFdPXis3~1',
    # 'ak_bmsc': '99F112B27B2585093324CCFCD9595DEE~000000000000000000000000000000~YAAQ0iXAF+WnAciYAQAAzhgH4hzFCtaDx+ydjoxqC/6fwhNN9bNzLswP6X2bYxZrKDZhURzC7NqEXbhGAWJG23gfrIe0z5fJWNynnRyWraq+phqc4ZYDc2HebkkftMRLe0vtqb1xfsnTUv8KNhYzYniEYxzNSJchwyYXxqnsc/fA+WAA1EO8/+ijIF3sGUnwz3vpaD8ctbGE+KXsd6QP++Wtlrc3AsxjJIvRkzlgoif19+k7qaPQLuhP3WTfnpVWK7l55DMcw932X2b0Et7L6PnYC9PCJBvx6X1LUkeUdS2oNMfFL9eK0rLuF8iIEmCRqiGP7I8aCu59FnAgP+7WDHSC0rYMAq/X5flmjUXOvfQ5KpYABtqs7AglOPAT1fpTrd38T8li1AHQmbuDPq2Jwbk/ELOexhjFgFhArtYFQmZGfGWfT5laM9v2OdKQTtki3e7MuPLq3UlQGcYMmxlhEIo/U48zwPrYFFsXBt9Pb9EXck0MPEUg/w==',
### WATCH - linked to io_id and _astc ###
    # 'if_id': 'FMEZARSF3rtaobWC+7qcI29gUrKUShTXbBM/YnedldqDj1V9xjF9yD5nT/xW2sWUIfJoi/2qqg/4rL2XjPDCNa2fZh9MV6XLWkojqUH/KyijKJhkHrT+X92L4kFJ7ljt3tVocX1+YNSZaxMatjUsAoL3zYsclFrWhg2F69mSHBuHDpHnkJuyyUsJPI9TpzMNNF8+Oi0fx81EhP42alf6ry54ooNtrIk0UY5MTH+I/7TvXBGfgi1VKtHVUSZC9iCyxR8TXnNEYJhuKrPYIT+4jNSqKr3KpsphrID4SwCyV6rGqrtz0VUgMmSQ4AZqWP98JSRjh1O+IBNT6ui6w+BicGfE6sYr6A==',
    # 'TS016ef4c8': '01a45e1c891407286af8e2222d9db70b465503657781480d5be5203417c9fef5336736f5306a5ba22c781077c4357563c0d5b91c0b',
    # 'TS01f89308': '01a45e1c891407286af8e2222d9db70b465503657781480d5be5203417c9fef5336736f5306a5ba22c781077c4357563c0d5b91c0b',
    # 'TS8cb5a80e027': '089bdf021fab2000235286022a6b23806696079efcc29bca337bfe2d7943d9abda896905a7b9d72908497247871130009b9b1cd967e44ce5221112a6caf8fa9bd7737624208987cd4ad8601468d33a0eebb02cfc55a84d17eea7db8bd6f55d47',
    # 'bm_sv': '047529B422E94AFD8B274B8DE8B2D724~YAAQ0iXAFzmuAciYAQAAjSEH4hzC8btSWtTknzzVI9E/fpzg0FLhbQyE6bp8V2ff0jJOUHtt4R2hDsohGCkMYzqirLJR9MPkJORTNKxh6mEWIjU/CRpzt0VfIYCSuz9PlNeyxhPwNY/JNB4CFyJeEO6Js9Gicug3/Eh3GbJQ7Yu3YZt5KKooIbeHfy0pTA329oppZwIl0vCQtBXh1JGtZ11+2Cyk4uKQK55Z6HwEqjUKlRFaCW82y5DNUIwe9G10YA==~1',
    # '_px3': 'afe0c7157274adce650b011de8de3646078a36ce70747c10a572fe8a4b7bb449:f7g1MGaZgy1EWQcBa4l4PgfCdQaewxZYK8mGmzIlFI71RA6MFn0CQPqOE98PbZNMRRCLN9s8/niLFh8dOI5++Q==:1000:IdvtbjiljFNFJUxhtTKmWi0+KsbgeaExZKJs2/iDZKDDHSGgKGuIj2MSIlZ33g56qAVq0SV3+fCz0Hlb2GYnfq3gtyMvj7enAjRocT5QnqVQ+gFrHKrAYBFNzj4emUgI1bUTJF8HgvPJS284f1BXwvoYTRHGsC6F5MZtPR+mz2b2I79EV8osxvJKFi5RkT5SzPs0s3PfN9sacN960b8sFtSp4OVZ0a0wD2pyNS7wcD4=',
    # '_pxde': '217041e87108d995ef9a1f90264413b2aabf885fd20400f60ae6e7da8e18b3ce:eyJ0aW1lc3RhbXAiOjE3NTYxMzg3ODUwNzh9',
}



#
# headers = {
#     'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
#     'accept-language': 'en-US,en;q=0.9',
#     'cache-control': 'no-cache',
#     'pragma': 'no-cache',
#     'priority': 'u=0, i',
#     'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
#     'sec-ch-ua-mobile': '?0',
#     'sec-ch-ua-platform': '"macOS"',
#     'sec-fetch-dest': 'document',
#     'sec-fetch-mode': 'navigate',
#     'sec-fetch-site': 'none',
#     'sec-fetch-user': '?1',
#     'upgrade-insecure-requests': '1',
#     'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
# }
headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': browser_persona.sec_ch_ua,
    'sec-ch-ua-mobile': browser_persona.sec_ch_ua_mobile,
    'sec-ch-ua-platform': browser_persona.sec_ch_ua_platform,
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': browser_persona.user_agent
}


retailer = 'Walmart'
store_id = '1198'
fetch_type = 'search'
query = 'Milk'  # Simple query for testing

# Load configuration using existing utilities with absolute paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
stores_file = os.path.join(project_root, 'data', 'Walmart_stores.yaml')
search_file = os.path.join(project_root, 'data', 'Walmart_fetch_search.yaml')

store_identification = load_store_by_id(store_id=store_id, yaml_file=stores_file)
search_config = load_search_by_query(query=query, yaml_file=search_file)
header_builder = WalmartHeaderBuilder(store_identification=store_identification)

query = search_config.get('query')
first_page_search_url = search_config.get('search_url')


generated_location_cookies = header_builder.location_cookie()

generated_location_cookie_dict = {}
for pair in generated_location_cookies.split('; '):
    if '=' in pair:
        name, value = pair.split('=', 1)
        generated_location_cookie_dict[name] = value
        logger.info(f"Generated cookie: {name}={value}")

trimmed_cookies['ACID'] = generated_location_cookie_dict['ACID']
trimmed_cookies['locGuestData'] = generated_location_cookie_dict['locGuestData']
trimmed_cookies['locDataV3'] = generated_location_cookie_dict['locDataV3']




async def get_walmart_home_page_with_requests(headers:dict, cookies:dict):
    proxies = get_proxies(proxy_type='residential')

    logger.info(proxies)

    max_attempts = 10
    attempt = 1
    while attempt <= max_attempts:
        logger.info(f"Attempt {attempt} of {max_attempts}...")
        response = requests.get(
            'https://www.walmart.com',
            cookies=cookies,
            proxies=proxies,
            headers=headers,
            verify=False
        )

        logger.info(f'https://www.walmart.com response code: {response.status_code}')
        logger.info(f'https://www.walmart.com response reason: {response.reason}')

        if (response.status_code == 200):
            # Save response text to a file
            with open('walmart_home_page_output.html', 'w', encoding='utf-8') as file:
                file_text = response.text

                logger.info(f"Searching response text for storeId:{store_id}...")
                match = re.search(r'"storeId":"(\d+)"', file_text)
                if match:
                    file.write(file_text)
                    found_id = match.group(1)  # Extracts the number from the pattern
                    logger.info(f"******* Found store ID '{found_id}'.")
                    if found_id == store_id:
                        logger.info(f"Store ID '{found_id}' matches the specified retailer_store_id '{store_id}'.")
                        for cookie in response.cookies:
                            logger.info(f"Cookie: {cookie.name}={cookie.value}")

                        harvested_cookies = await harvest_cookies(response.cookies.get_dict())

                        success_result = {
                                    "success": True,
                                    "cookies": harvested_cookies,
                                    "headers": headers
                                }

                    return success_result
                else:
                    logger.warning("No 'storeId' pattern found in the HTML response.")
        else:
            logger.warning(f"Attempt {attempt} failed. Status code: {response.status_code}. Reason: {response.reason}")

        attempt += 1

    return {
                "success": False,
                "cookies": cookies,
                "headers": headers
            }


async def harvest_walmart_session(headers: dict, cookies: dict, browser_persona: BrowserPersona) -> Dict[str, Any]:
    """
    Harvest real cookies by using Playwright to wait for JavaScript execution.
    This captures JavaScript-generated store location cookies that aiohttp cannot get.
    """

    session_cache = {}  # In production, this would be Redis/database
    cache_ttl = 3600

    logger.info(f"🌾 [Playwright Harvest] Harvesting authentic cookies for {browser_persona.persona_id}")

    # Initialize Playwright with proper resource management
    try:
        # async with async_playwright() as playwright:
        async with Stealth().use_async(async_playwright()) as playwright:
            # Launch browser
            logger.info(f"Launching Playwright browser with {browser_persona.persona_id}...")
            playwright_engine = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-extensions',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-features=TranslateUI,VizDisplayCompositor',
                    '--disable-ipc-flooding-protection'
                ],
                channel='chrome'
            )

            proxy_components = get_proxy_components(proxy_type='residential')

            # Configure proxy if available
            proxy_config =  {
                        'server': f'http://{proxy_components['proxy_host']}:{proxy_components['proxy_port']}',
                        'username': proxy_components['proxy_user'],
                        'password': proxy_components['proxy_pass']
                    }

            cookie_string = f"hasLocData={cookies['hasLocData']}; ACID={cookies['ACID']}; locGuestData={cookies['locGuestData']}; assortmentStoreId={cookies['assortmentStoreId']}; hasACID=true; locDataV3={cookies['locDataV3']}; "

            headers['cookie'] = cookie_string

            # Navigate to Walmart homepage and wait for JavaScript execution
            max_attempts = 20
            attempt = 1
            while attempt <= max_attempts:
                # Create browser context with persona configuration
                context = await playwright_engine.new_context(
                    user_agent=browser_persona.user_agent,
                    viewport={'width': browser_persona.viewport_width, 'height': browser_persona.viewport_height},
                    extra_http_headers=headers,
                    locale='en-US',
                    timezone_id='America/Chicago',
                    proxy=proxy_config,
                    ignore_https_errors=True  # For proxy compatibility
                )

                # Inject stealth scripts to avoid bot detection
                await context.add_init_script("""
                    // Remove webdriver property
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
    
                    // Mock Chrome runtime
                    window.chrome = {
                        runtime: {}
                    };
    
                    // Mock permissions API
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => {
                        return parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters);
                    };
    
                    // Override plugins length
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                """)

                # Create new page
                page = await context.new_page()

                # Track network responses for debugging
                response_data = {'status': None, 'redirects': []}

                async def handle_response(response):
                    if 'walmart.com' in response.url:
                        response_data['status'] = response.status
                        if response.status in [301, 302, 307, 308]:
                            response_data['redirects'].append({
                                'from': response.url,
                                'status': response.status
                            })
                        logger.debug(f"🌐 [Response] {response.url}: {response.status}")

                page.on('response', handle_response)

                logger.info(f"Attempt {attempt} of {max_attempts}...")
                try:

                    try:
                        logger.info("🌐 [Playwright] Navigating to Walmart.com...")

                        response = await page.goto(
                            "https://www.walmart.com",
                            wait_until='commit',  # Just wait for navigation to start
                            timeout=60000
                        )
                        # Then wait for the page to settle
                        await page.wait_for_load_state('networkidle')
                    except Exception as e:
                        logger.warning(f"Navigation interrupted, but continuing: {e}")
                        # Page might still be usable

                    if response:
                        response_status = response.status
                        logger.info(f"📄 [Playwright] Page loaded: HTTP {response_status}")

                        # Check for successful page load
                        if response_status == 200:
                            # Wait a bit more for dynamic content
                            await page.wait_for_timeout(3000)

                            # Get page title to verify success
                            title = await page.title()
                            logger.info(f"📄 [Playwright] Page title: {title}")

                            if title == 'Robot or human?':
                                logger.error("BOT DETECTED!!!")
                                break


                            file_text = await response.text()
                            logger.info(f"Searching response text for storeId:{store_id}...")
                            match = re.search(r'"storeId":"(\d+)"', file_text)
                            if match:
                                found_id = match.group(1)
                                logger.info(f"******* Found store ID '{found_id}'.")
                                # if found_id != store_id:
                                #     logger.info(f"Store ID '{found_id}' does not match the specified store_id '{store_id}'.")
                                #     attempt += 1
                                #     continue

                            # Extract all cookies from browser context
                            all_context_cookies = await context.cookies()
                            harvested_cookies = await harvest_cookies(all_context_cookies)

                            logger.info(
                                f"✅ [Playwright Harvest] Successfully harvested {len(harvested_cookies)} cookies with JavaScript")
                            logger.debug(f"🍪 [Playwright Harvest] Cookie names: {list(harvested_cookies.keys())}")

                            # Cache the harvested cookies with TTL
                            cache_key = f"walmart_{browser_persona.persona_id}_{int(time.time() / cache_ttl)}"
                            session_cache[cache_key] = {
                                "cookies": harvested_cookies,
                                "harvested_at": time.time(),
                                "persona_id": browser_persona.persona_id
                            }

                            logger.info(
                                f"🎯 [Cookie Cache] Cached {len(harvested_cookies)} cookies with key: {cache_key}")

                            # Create the success result BEFORE attempting cleanup
                            success_result = {
                                "success": True,
                                "cookies": harvested_cookies,
                                "headers": {
                                    "x-session-harvested": "playwright",
                                    "x-harvest-time": str(int(time.time())),
                                    "x-persona-id": browser_persona.persona_id,
                                    "x-page-title": title
                                },
                                "harvested_at": time.time(),
                                "cache_key": cache_key
                            }

                            # Attempt cleanup but don't let cleanup failures affect success
                            try:
                                await page.close()
                                await context.close()
                                await playwright_engine.close()
                                logger.debug("🧹 [Cleanup] Successfully closed all Playwright resources")
                            except Exception as cleanup_error:
                                logger.warning(f"⚠️ [Cleanup] Resource cleanup failed (non-critical): {cleanup_error}")
                                logger.info("✅ [Success] Cookie harvesting succeeded despite cleanup issues")

                            return success_result
                        else:
                            logger.error(f"❌ [Playwright Navigation] Page load failed with HTTP {response_status}")
                            logger.error(
                                "🔍 [Troubleshooting] This could indicate: proxy issues, bot detection, or network problems")
                    else:
                        logger.error(f"❌ [Playwright Navigation] No HTTP response received from Walmart.com")
                        logger.error(
                            "🔍 [Troubleshooting] This could indicate: network connectivity issues or proxy blocking")

                except Exception as nav_error:
                    logger.error(f"❌ [Playwright Navigation] Failed to navigate to Walmart.com: {nav_error}")
                    logger.error(
                        "🔍 [Troubleshooting] This could indicate: proxy configuration errors, browser launch issues, or network problems")
                attempt += 1
            # Resources automatically closed by async with context manager

    except Exception as e:
        logger.error(f"❌ [Playwright Browser] Failed to launch or configure browser: {e}")
        logger.error(
            "🔍 [Troubleshooting] This could indicate: Chrome/Chromium not installed, permission issues, or proxy configuration problems")

    # Return failure result with helpful error context
    logger.error(
        "🚫 [Cookie Harvest Failed] Unable to harvest JavaScript cookies - STORE_ID_MISMATCH errors likely")
    return {"success": False, "cookies": {}, "headers": {}}


async def harvest_cookies(all_context_cookies):
    harvested_cookies = {}
    cookies_to_harvest = ['_pxvid', 'vtc', '_m', 'io_id', 'abqme',
                          'AID', '_pxhd', 'pxcts', 'wmlh', '_astc',
                          'userAppVersion', 'akavpau_p1', 'bstc', '__cf_bm', 'com.wm.reflector',
                          'akavpau_p2', 'bm_mi', 'ak_bmsc', 'if_id', 'bm_sv', '_px3',
                          '_pxde', ]
    for cookie in all_context_cookies:
        if cookie in cookies_to_harvest:
            harvested_cookies[cookie] =  all_context_cookies[cookie]
    return harvested_cookies


# get_walmart_home_page_with_requests()

def blend_cookies(location_cookies, harvested_cookies):

    cookie_string = f"hasLocData={location_cookies['hasLocData']}; ACID={location_cookies['ACID']}; locGuestData={location_cookies['locGuestData']}; assortmentStoreId={location_cookies['assortmentStoreId']}; hasACID=true; locDataV3={location_cookies['locDataV3']}; "

    harvested_cookie_string = "; ".join(f"{key}={value}" for key, value in harvested_cookies.items())

    cookie_string += f"{harvested_cookie_string};"

    return cookie_string

class LocalBundle(RetailerBundle):
    headers = {}
    def set_headers(self, headers:dict):
        self.headers = headers

    def build_headers(self):
        return self.headers

    def get_headers(self):
        return self.build_headers()

async def main():
    logger.info(f"🎯 [Config] Retailer: {retailer}")
    logger.info(f"🎯 [Config] Store: {store_id} ({store_identification.get('store_display_name', 'Unknown')})")
    logger.info(f"🎯 [Config] Query: {query}")
    logger.info(f"🎯 [Config] Start URL: {first_page_search_url}")

    cookies_to_try = trimmed_cookies

    # harvested_result = await harvest_walmart_session(headers=headers, cookies=cookies, browser_persona=browser_persona)
    harvested_result = await get_walmart_home_page_with_requests(headers=headers, cookies=cookies)

    blended_cookie_string = blend_cookies(cookies_to_try, harvested_result['cookies'])

    logger.info(blended_cookie_string)

    headers['cookie'] = blended_cookie_string

    bundle = LocalBundle(
        retailer=retailer,
        store_identification=store_identification,
        fetch_type=fetch_type,
        fetch_query=query,
        start_url=first_page_search_url,
        project_config=project_config,
        logger=logger,
    )

    bundle.set_headers(headers)

    results = await bundle.fetcher.fetch_all(first_page_search_url, bundle.handle_result)


if __name__ == "__main__":
    asyncio.run(main())