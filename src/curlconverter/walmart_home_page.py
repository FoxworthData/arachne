import os
import asyncio
import json
import random
import hashlib
import time
import uuid
import urllib.parse
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

import yaml
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from dotenv import load_dotenv

load_dotenv()
app_env = os.getenv("APP_ENV", "development")  # Default to 'development' if not set



try:
    from src.utils.setup_config_logging import setup_config_logging
    from src.utils.yaml_util import load_store_by_id, load_search_by_query
    from src.utils.file_storage import FileStorage
    from src.utils.file_namer import WalmartNamer
    from src.utils.fetcher_tracking import FetcherSession, FetchedFile
    from src.utils.paginators import WalmartPaginator
    from src.utils.config_loader import ConfigLoader

except ImportError:
    # Fallback for running directly from command line
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.setup_config_logging import setup_config_logging
    from utils.yaml_util import load_store_by_id, load_search_by_query
    from utils.file_storage import FileStorage
    from utils.file_namer import WalmartNamer
    from utils.fetcher_tracking import FetcherSession, FetchedFile
    from utils.paginators import WalmartPaginator
    from utils.config_loader import ConfigLoader

@dataclass
class BrowserPersona:
    """Browser persona with consistent fingerprinting data."""
    user_agent: str
    sec_ch_ua: str
    sec_ch_ua_mobile: str
    sec_ch_ua_platform: str
    device_specs: Dict[str, str]
    persona_id: str
    viewport_width: int
    viewport_height: int
    
    @property
    def viewport(self):
        return {'width': self.viewport_width, 'height': self.viewport_height}
    
    @classmethod
    def generate_persona_id(cls, user_agent: str) -> str:
        """Generate a unique persona ID based on user agent characteristics."""
        ua_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
        
        if "Chrome" in user_agent and "Windows" in user_agent:
            return f"chrome-win-{ua_hash}"
        elif "Chrome" in user_agent and "Macintosh" in user_agent:
            return f"chrome-mac-{ua_hash}"
        elif "Chrome" in user_agent and "Linux" in user_agent:
            return f"chrome-linux-{ua_hash}"
        else:
            return f"chrome-unknown-{ua_hash}"


class BrowserPersonaChooser:
    """
    Browser persona management, contains curated Chrome personas for maximum bot evasion.
    
    Note: Only Chrome personas are used because Playwright only supports Chromium engines.
    Using Safari/Firefox personas with Chromium would create header/runtime mismatches
    that can be detected as bot behavior by anti-bot systems.
    """
    
    def __init__(self):
        # Curated Chrome personas only - compatible with Playwright's Chromium engine
        # Safari personas removed due to header/runtime mismatch causing bot detection
        self._personas_data = [
            # Chrome Windows - High success rate
            {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "sec_ch_ua": '"Google Chrome";v="137", "Chromium";v="137", "Not.A/Brand";v="24"',
                "sec_ch_ua_mobile": "?0",
                "sec_ch_ua_platform": '"Windows"',
                "device_specs": {
                    "downlink": "8.5",
                    "dpr": "1",
                    "rtt": "100",
                    "ect": "4g"
                },
                "viewport_width": 1920,
                "viewport_height": 1080
            },
            # Chrome macOS - High success rate
            {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "sec_ch_ua": '"Google Chrome";v="137", "Chromium";v="137", "Not.A/Brand";v="24"',
                "sec_ch_ua_mobile": "?0", 
                "sec_ch_ua_platform": '"macOS"',
                "device_specs": {
                    "downlink": "10.0",
                    "dpr": "2",
                    "rtt": "50",
                    "ect": "4g"
                },
                "viewport_width": 1440,
                "viewport_height": 900
            },
            # Chrome Linux - Added for additional variety while maintaining Chromium compatibility
            {
                "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "sec_ch_ua": '"Google Chrome";v="137", "Chromium";v="137", "Not.A/Brand";v="24"',
                "sec_ch_ua_mobile": "?0",
                "sec_ch_ua_platform": '"Linux"',
                "device_specs": {
                    "downlink": "9.2",
                    "dpr": "1",
                    "rtt": "75",
                    "ect": "4g"
                },
                "viewport_width": 1920,
                "viewport_height": 1080
            }
        ]
    
    def get_random_persona(self) -> BrowserPersona:
        """Select a random persona from curated list."""
        persona_data = random.choice(self._personas_data)
        persona_id = BrowserPersona.generate_persona_id(persona_data["user_agent"])
        
        return BrowserPersona(
            user_agent=persona_data["user_agent"],
            sec_ch_ua=persona_data["sec_ch_ua"],
            sec_ch_ua_mobile=persona_data["sec_ch_ua_mobile"],
            sec_ch_ua_platform=persona_data["sec_ch_ua_platform"],
            device_specs=persona_data["device_specs"],
            persona_id=persona_id,
            viewport_width=persona_data["viewport_width"],
            viewport_height=persona_data["viewport_height"]
        )


class AdvancedWalmartHeaderBuilder:
    """
    Header builder that implements store-specific location cookies and headers
    """
    
    def __init__(self, store_identification: dict, persona: BrowserPersona, logger=None):
        self.store_identification = store_identification
        self.persona = persona
        self.logger = logger
        
        self._build_location_cookies()
    
    def _build_location_cookies(self):
        """Build store-specific location cookies using store identification data."""
        acid = str(uuid.uuid4())
        address_timestamp = int(time.time() * 1000)
        delivery_timestamp = int(time.time() * 1000)
        refresh_timestamp = int((time.time() + (6 * 60 * 60)) * 1000)  # 6 hours ahead
        
        # Complete location_guest_data matching the prototype exactly
        location_guest_data = {
            'intent': 'PICKUP',
            'isDefaulted': False,
            'isExplicit': False,
            'mergeFlag': True,
            'mp': [],
            'pickup': {
                'nodeId': self.store_identification['store_id'],
                'selectionSource': 'Pickup Store Selector',
                'selectionType': 'CUSTOMER_SELECTED',
                'timestamp': address_timestamp
            },
            'postalCode': {
                'base': self.store_identification['store_zip_code'], 
                'timestamp': address_timestamp
            },
            'shippingAddress': {
                'city': self.store_identification['store_city'],
                'deliveryStoreList': [
                    {
                        'deliveryTier': None,
                        'nodeId': self.store_identification['store_id'],
                        'selectionSource': 'ZIP_CODE_BY_USER',
                        'selectionType': 'LS_SELECTED',
                        'timestamp': delivery_timestamp,
                        'type': 'DELIVERY'
                    }
                ],
                'giftAddress': False,
                'postalCode': self.store_identification['store_zip_code'],
                'state': self.store_identification['store_state'],
                'timestamp': address_timestamp
            }
        }
        
        # Base64 encode the location data
        location_data_json = json.dumps(location_guest_data, separators=(',', ':'))
        location_data_b64 = base64.b64encode(location_data_json.encode()).decode()
        
        # Build location cookies string
        self._base_location_cookies = (
            f"assortmentStoreId={self.store_identification['store_id']}; "
            f"hasACID={acid}; "
            f"locGuestData={location_data_b64}; "
            f"locDataV3=refreshTimestamp%3D{refresh_timestamp}%7CaddressSource%3DPICKUP_STORE_SELECTOR; "
            f"xptc=assortmentStoreId%2B{self.store_identification['store_id']}~_m%2B9"
        )
        
        if self.logger:
            self.logger.info(f"🏗️ [Store Headers] Built location cookies for store {self.store_identification['store_id']}")
    
    def _get_device_performance_headers(self) -> Dict[str, str]:
        """Generate realistic device performance headers with variance."""
        specs = self.persona.device_specs
        
        # Add realistic variance to avoid identical fingerprints
        downlink_base = float(specs.get('downlink', '8.0'))
        downlink_variance = random.uniform(-0.5, 0.5)
        downlink = str(round(downlink_base + downlink_variance, 1))
        
        rtt_base = int(specs.get('rtt', '100'))
        rtt_variance = random.randint(-20, 20)
        rtt = str(max(10, rtt_base + rtt_variance))
        
        return {
            'downlink': downlink,
            'dpr': specs.get('dpr', '1'),
            'rtt': rtt,
            'ect': specs.get('ect', '4g')
        }
    
    def build_advanced_headers(self, target_url: str = "https://www.walmart.com") -> Dict[str, str]:
        """
        Build advanced headers with modern browser fingerprinting and store-specific data.
        """
        if self.logger:
            self.logger.info(f"🏗️ [Advanced Headers] Building for persona: {self.persona.persona_id}")
        
        # Get device performance headers
        device_headers = self._get_device_performance_headers()
        
        # Base headers with modern browser characteristics
        headers = {
            # Core headers (modern browser order)
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            
            # Modern priority header
            "priority": "u=0, i",
            
            # Chrome Client Hints (modern browser fingerprinting)
            "sec-ch-ua": self.persona.sec_ch_ua,
            "sec-ch-ua-mobile": self.persona.sec_ch_ua_mobile,
            "sec-ch-ua-platform": self.persona.sec_ch_ua_platform,
            
            # Fetch Metadata headers (modern security)
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate", 
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            
            # Security headers
            "upgrade-insecure-requests": "1",
            
            # Consistent persona User-Agent
            "user-agent": self.persona.user_agent,
            
            # Store-specific location cookies
            "cookie": self._base_location_cookies
        }
        
        # Add device performance headers
        headers.update(device_headers)
        
        if self.logger:
            self.logger.info(f"🏗️ [Advanced Headers] Built {len(headers)} headers for store {self.store_identification['store_id']}")
        return headers


class PlaywrightCookieHarvester:
    """
    Advanced Playwright-based cookie harvester using stealth techniques
    to dynamically collect cookies and headers from walmart.com.
    """
    
    def __init__(self, store_identification: Optional[dict] = None, logger=None):
        persona_chooser = BrowserPersonaChooser()
        self.persona = persona_chooser.get_random_persona()  # Random selection
        self.logger = logger
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        # ISOLATION FIX: Always use the proven working approach regardless of store_identification
        # Store identification will be added later for reporting/analysis only
        self.header_builder = None
        self.original_cookies = self._get_original_cookies()
        self.original_headers = self._get_original_headers()
        print(f"🎭 Selected random persona: {self.persona.persona_id}")
        
        # Show mode for debugging
        if store_identification:
            print(f"🔧 [ISOLATION MODE] Using proven base approach with store data for analysis only: {store_identification.get('store_display_name', 'Unknown Store')}")
        else:
            print("🔧 [BASE MODE] Using proven base approach")
    
    def _get_original_cookies(self) -> List[Dict[str, Any]]:
        """Get the original cookies from the requests.get() version."""
        cookie_dict = {
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
            'bstc': 'eSAzsefr4lQaJl6vBOk1J4',
            'xpth': 'x-o-mart%2BB2C~x-o-mverified%2Bfalse',
            'xpa': '086BP|1bezR|3VCVY|5_EoH|8Kkdx|9Yd9_|ArsR1|Avpka|EFPmM|E_gpz|J-MZ4|O_ewj|QPToB|RuVdg|TKwVE|ToJIM|_wRhm|a43Wd|aYAez|bFvEw|c_oVZ|eOpcH|fXtQf|fdm-7|fkq_L|hsomz|imMMk|jKJLU|jM1ax|kcy7R|kyO7M|lmqpp|mAZQB|mIxD_|pAaPn|rTu67|suTY7|wY6LG|wdV3R|y1Ld_',
            'exp-ck': '086BP11bezR19Yd9_2ArsR13Avpka1EFPmM1E_gpz1J-MZ41QPToB1ToJIM1a43Wd1aYAez2c_oVZ1fXtQf1fdm-71fkq_L1hsomztimMMk1kcy7R2kyO7M1lmqpp1mIxD_2rTu675wY6LG2wdV3R1y1Ld_4',
            'assortmentStoreId': '1198',
            'locDataV3': 'eyJpc0RlZmF1bHRlZCI6ZmFsc2UsImluc3RvcmUiOmZhbHNlLCJpbnRlbnQiOiJQSUNLVVAiLCJwaWNrdXAiOlt7Im5vZGVJZCI6IjExOTgiLCJkaXNwbGF5TmFtZSI6IlNhbiBBbnRvbmlvIFN1cGVyY2VudGVyIiwiYWRkcmVzcyI6eyJwb3N0YWxDb2RlIjoiNzgyMzIiLCJhZGRyZXNzTGluZTEiOiIxNTE1IE4gTE9PUCAxNjA0IEUiLCJjaXR5IjoiU2FuIEFudG9uaW8iLCJzdGF0ZSI6IlRYIiwiY291bnRyeSI6IlVTIn0sImdlb1BvaW50Ijp7ImxhdGl0dWRlIjoyOS42MTI0MTEsImxvbmdpdHVkZSI6LTk4LjQ3MDcyMX0sInNjaGVkdWxlZEVuYWJsZWQiOnRydWUsInVuU2NoZWR1bGVkRW5hYmxlZCI6dHJ1ZSwic3RvcmVIcnMiOiIwNjowMC0yMzowMCIsImFsbG93ZWRXSUNBZ2VuY2llcyI6WyJUWCJdLCJzdXBwb3J0ZWRBY2Nlc3NUeXBlcyI6WyJQSUNLVVBfSU5TVE9SRSIsIkFDQ19JTkdST1VORCIsIlBJQ0tVUF9TUEVDSUFMX0VWRU5UIiwiUElDS1VQX0JBS0VSWSIsIlBJQ0tVUF9DVVJCU0lERSIsIkFDQyJdLCJ0aW1lWm9uZSI6IkFtZXJpY2EvQ2hpY2FnbyIsInN0b3JlQnJhbmRGb3JtYXQiOiJXYWxtYXJ0IFN1cGVyY2VudGVyIiwic2VsZWN0aW9uVHlwZSI6IkNVU1RPTUVSX1NFTEVDVEVEIn0seyJub2RlSWQiOiI0MTYyIn0seyJub2RlSWQiOiIxODAzIn0seyJub2RlSWQiOiIyNDA0In0seyJub2RlSWQiOiI3NjUifSx7Im5vZGVJZCI6IjEzNDcifSx7Im5vZGVJZCI6IjI1OTkifSx7Im5vZGVJZCI6IjUxNDUifSx7Im5vZGVJZCI6IjI3NjkifV0sInNoaXBwaW5nQWRkcmVzcyI6eyJsYXRpdHVkZSI6MjkuNTg3OSwibG9uZ2l0dWRlIjotOTguNDcyLCJwb3N0YWxDb2RlIjoiNzgyMzIiLCJjaXR5IjoiU2FuIEFudG9uaW8iLCJzdGF0ZSI6IlRYIiwiY291bnRyeUNvZGUiOiJVU0EiLCJnaWZ0QWRkcmVzcyI6ZmFsc2UsInRpbWVab25lIjoiQW1lcmljYS9DaGljYWdvIiwiYWxsb3dlZFdJQ0FnZW5jaWVzIjpbIlRYIl19LCJhc3NvcnRtZW50Ijp7Im5vZGVJZCI6IjExOTgiLCJkaXNwbGF5TmFtZSI6IlNhbiBBbnRvbmlvIFN1cGVyY2VudGVyIiwiaW50ZW50IjoiUElDS1VQIn0sImlzRXhwbGljaXQiOmZhbHNlLCJkZWxpdmVyeSI6eyJub2RlSWQiOiIxMTk4IiwiZGlzcGxheU5hbWUiOiJTYW4gQW50b25pbyBTdXBlcmNlbnRlciIsImFkZHJlc3MiOnsicG9zdGFsQ29kZSI6Ijc4MjMyIiwiYWRkcmVzc0xpbmUxIjoiMTUxNSBOIExPT1AgMTYwNCBFIiwiY2l0eSI6IlNhbiBBbnRvbmlvIiwic3RhdGUiOiJUWCIsImNvdW50cnkiOiJVUyJ9LCJnZW9Qb2ludCI6eyJsYXRpdHVkZSI6MjkuNjEyNDExLCJsb25naXR1ZGUiOi05OC40NzA3MjF9LCJzY2hlZHVsZWRFbmFibGVkIjpmYWxzZSwidW5TY2hlZHVsZWRFbmFibGVkIjpmYWxzZSwiYWNjZXNzUG9pbnRzIjpbeyJhY2Nlc3NUeXBlIjoiREVMSVZFUllfQUREUkVTUyJ9XSwiaXNFeHByZXNzRGVsaXZlcnlPbmx5IjpmYWxzZSwiYWxsb3dlZFdJQ0FnZW5jaWVzIjpbIlRYIl0sInN1cHBvcnRlZEFjY2Vzc1R5cGVzIjpbIkRFTElWRVJZX0FERFJFU1MiLCJBQ0MiXSwidGltZVpvbmUiOiJBbWVyaWNhL0NoaWNhZ28iLCJzdG9yZUJyYW5kRm9ybWF0IjoiV2FsbWFydCBTdXBlcmNlbnRlciIsInNlbGVjdGlvblR5cGUiOiJMU19TRUxFQ1RFRCJ9LCJyZWZyZXNoQXQiOjE3NTYwOTExODE0ODQsImlzZ2VvSW50bFVzZXIiOmZhbHNlLCJtcERlbFN0b3JlQ291bnQiOjIwLCJtcHMiOlsiMTUyMzcwMiIsIjE1MjM3MDUiLCIxNTIyODE1IiwiMTUyMzY1MyIsIjE1MjIxMDYiLCIxNTI1MTQyIiwiMTUyMzQyMyIsIjE1MjM3MDQiLCIxNTIzNTk1IiwiMTUxOTYxNCIsIjE1MjExODEiLCIxNTIzNjIwIiwiMTUyMzU3MiIsIjE1MjM1NzQiLCIxNTIzNDE5IiwiMTUyMDQzMSIsIjE1MjM4OTQiLCIxNTIyNzY1IiwiMTUyMzY4NyIsIjEwMDAwMDEiLCIxNTI1MjA0IiwiMTUxOTEwMiIsIjE1MjM1NzciLCIxNTIyODcxIiwiMTUyMjAyOCIsIjE1MjMzNDYiLCIxNTIyNjg4IiwiMTUyMzc0MyIsIjE1MjM5OTMiLCIxNTIzOTk0IiwiMTUyMDA5NyIsIjE1MjM1MTEiLCIxNTIwNTA1IiwiMTUyMzU2MCIsIjE1MjA0NjAiLCIxNTIzNTkwIiwiMTUyMDMzMCIsIjE1MjIwMzciLCIxNTIzNjU4IiwiMTUxOTczNSIsIjE1MjM4MDYiLCIxNTI0NDE1IiwiMTUyMzU2OSIsIjE1MjM2ODkiLCIxNTIzNjUyIiwiMTUyMzY0MCIsIjE1MjM2MzQiLCIxNTIzNzc0IiwiMTUyMDYyOSIsIjE1MjM2OTIiXSwibXBVbmlxdWVTZWxsZXJDb3VudCI6MCwic2hvd0xNUEVudHJ5UG9pbnQiOmZhbHNlLCJzaG93TG9jYWxFeHBlcmllbmNlIjpmYWxzZSwidmFsaWRhdGVLZXkiOiJwcm9kOnYyOmRhNjI0NWM3LTBhNDQtNDFmMi1hNzMzLTczMTc0OWIxYWYwZiJ9',
            'locGuestData': 'eyJpbnRlbnQiOiJQSUNLVVAiLCJpc0V4cGxpY2l0IjpmYWxzZSwic3RvcmVJbnRlbnQiOiJQSUNLVVAiLCJtZXJnZUZsYWciOnRydWUsImlzRGVmYXVsdGVkIjpmYWxzZSwicGlja3VwIjp7Im5vZGVJZCI6IjExOTgiLCJ0aW1lc3RhbXAiOjE3Mzc0MDMzMDE5MDEsInNlbGVjdGlvblR5cGUiOiJDVVNUT01FUl9TRUxFQ1RFRCIsInNlbGVjdGlvblNvdXJjZSI6IlBpY2t1cCBTdG9yZSBTZWxlY3RvciJ9LCJzaGlwcGluZ0FkZHJlc3MiOnsidGltZXN0YW1wIjoxNzM3NDAzMzAxOTAxLCJ0eXBlIjoicGFydGlhbC1sb2NhdGlvbiIsImdpZnRBZGRyZXNzIjpmYWxzZSwicG9zdGFsQ29kZSI6Ijc4MjMyIiwiZGVsaXZlcnlTdG9yZUxpc3QiOlt7Im5vZGVJZCI6IjExOTgiLCJ0eXBlIjoiREVMSVZFUlkiLCJ0aW1lc3RhbXAiOjE3NTYwNjk1ODE0NTQsImRlbGl2ZXJ5VGllciI6bnVsbCwic2VsZWN0aW9uVHlwZSI6IkxTX1NFTEVDVEVEIiwic2VsZWN0aW9uU291cmNlIjoiWklQX0NPREVfQllfVVNFUiJ9XSwiY2l0eSI6IlNhbiBBbnRvbmlvIiwic3RhdGUiOiJUWCJ9LCJwb3N0YWxDb2RlIjp7InRpbWVzdGFtcCI6MTczNzQwMzMwMTkwMSwiYmFzZSI6Ijc4MjMyIn0sIm1wIjpbXSwibXNwIjp7Im5vZGVJZHMiOlsiNDE2MiIsIjE4MDMiLCIyNDA0IiwiNzY1IiwiMTM0NyIsIjI1OTkiLCI1MTQ1IiwiMjc2OSJdLCJ0aW1lc3RhbXAiOjE3NTYwNjk1ODE0MzJ9LCJtcHMiOlsiMTUyMzcwMiIsIjE1MjM3MDUiLCIxNTIyODE1IiwiMTUyMzY1MyIsIjE1MjIxMDYiLCIxNTI1MTQyIiwiMTUyMzQyMyIsIjE1MjM3MDQiLCIxNTIzNTk1IiwiMTUxOTYxNCIsIjE1MjExODEiLCIxNTIzNjIwIiwiMTUyMzU3MiIsIjE1MjM1NzQiLCIxNTIzNDE5IiwiMTUyMDQzMSIsIjE1MjM4OTQiLCIxNTIyNzY1IiwiMTUyMzY4NyIsIjEwMDAwMDEiLCIxNTI1MjA0IiwiMTUxOTEwMiIsIjE1MjM1NzciLCIxNTIyODcxIiwiMTUyMjAyOCIsIjE1MjMzNDYiLCIxNTIyNjg4IiwiMTUyMzc0MyIsIjE1MjM5OTMiLCIxNTIzOTk0IiwiMTUyMDA5NyIsIjE1MjM1MTEiLCIxNTIwNTA1IiwiMTUyMzU2MCIsIjE1MjA0NjAiLCIxNTIzNTkwIiwiMTUyMDMzMCIsIjE1MjIwMzciLCIxNTIzNjU4IiwiMTUxOTczNSIsIjE1MjM4MDYiLCIxNTI0NDE1IiwiMTUyMzU2OSIsIjE1MjM2ODkiLCIxNTIzNjUyIiwiMTUyMzY0MCIsIjE1MjM2MzQiLCIxNTIzNzc0IiwiMTUyMDYyOSIsIjE1MjM2OTIiXSwibXBEZWxTdG9yZUNvdW50IjoyMCwic2hvd0xvY2FsRXhwZXJpZW5jZSI6ZmFsc2UsInNob3dMTVBFbnRyeVBvaW50IjpmYWxzZSwibXBVbmlxdWVTZWxsZXJDb3VudCI6MCwidmFsaWRhdGVLZXkiOiJwcm9kOnYyOmRhNjI0NWM3LTBhNDQtNDFmMi1hNzMzLTczMTc0OWIxYWYwZiJ9',
            'akavpau_p1': '1756070181~id=2f148097902b39a967b4b7df0a8172af',
            'ak_bmsc': '4EBD0DAD891A63AC706779095285DA5B~000000000000000000000000000000~YAAQySXAF9yKIdmYAQAAcs4Z3hxaiOtgbg5Qzzo4ISHfOeNmlDFM4ieMxWkt+V8pni5Vj+5vWvjH2FkDdgzTgx2waHn2n+T3tgXOwNHHio0b5mDnXV7R1to02/RjFf6NBiAsy7haTnsIBuah2HkPHNxX3DPH5t/VHX2Dqs8Fu5NuLKBu+d2eandj2pfAotrVPUPsu1hDl2LY3JYmCBuHyip6/4nT/BuI9jSvqmkgKFEm93vppKPbj8m+YGcCY1ZLf4x0xHovz9w29eEWi4V//uFu90uV3CBpRk7MLTFXdyIqbv0YE/bsTmwkJ62hXdPk55+vv1xXMmvmWRT/J+KoQgkcp6kM4ujzPzRgOBsIVyRzcW1xad/wRaejMRjPGB2Q3HazKDFPdX2ifVQ7',
            'xpm': '1%2B1756073190%2Bdd9PPd4ei-FkppMZKF3QpI~%2B0',
            '_intlbu': 'false',
            '_shcc': 'US',
            '__cf_bm': 'YU9cyMeyKHv_2jMOccacAMd_JFxKINZeqBxJFjL1I4E-1756075581-1.0.1.1-GDu8EIcD5Cecb4b5MwZxvWxAguX3mh.GtfoO1VGGtVIwZ69QAa29LbEoHUSovsQYQE8qqgQlUXMRsnM_Yozc7Ry92C9vsXCbRz7zLh.69etXyDfJZWfJKmQkXKNDRxCk',
            '_px3': '11f8a7c69072b9cdb43d66ff2f8f7edb0d77beedcb958a24b8eb88f1922b03d2:DkvvbUU3UW26QHDPsx5qE373n2AAY6SCJpxA6JIyS7B5IVVLOHo8AUkoJy35mVjhzWBH/tIs89EB6UFyw/UpKA==:1000:mmdhvA4+qmmgi6nRtGKNa6L0lXSsV9JUcU1FTtRFkEdeFBp9SDFuL3S8dFnKRlgN8Yvs5CJvg/zB46DTOCcc1EXWxJ7tRBrGYrH3sjwCsmbDsuz8sLaqCLr1ZUCec83r8FAZBZvGROE5vxGQnc2Nems99jqGpy+j3bx5mTqJvCjz8hw/nQvhhsNOU43rZYTBiJmPpdMLLWkX/DRUd+71jTcmwahyGhVhJMIG2slYDvk=',
            'if_id': 'FMEZARSFJ2ISavH849T5oWnq6PzII4lKCCvouzJyF827Xh25nuaceoyRSSvfoydxTupl17S1P4piua7BGorAJSZyv+y9eBumLesvndO7MhikN2+sEFqkfmbS/teXZ90lomWFjJPCam9HmglinPY4V/bPYZ+hoRktl2YhU8EogZOdrEICdtwBpOPPDUQAvcFmcSXyuHwBJaWoqMWX0fX8U0sC6KF9j14lsjr+wYZ88+Qg1uA3YaZMvX3J/egdbcKIxzpUrRvprOvGEu1/lGlUMV6MKDcEZIQIke3csxh75OpC9o7UoEVaOMCy4yGy4u4kwd0MrytyQEsrrUxaXEmZs88rw2FH',
            'TS016ef4c8': '015b0313ae7227e55528d0dc6a46323445be5e3eaec3010ac138ec2c053172e08b828c97fd88608f20054306160eb433580de6a917',
            'TS01f89308': '015b0313ae7227e55528d0dc6a46323445be5e3eaec3010ac138ec2c053172e08b828c97fd88608f20054306160eb433580de6a917',
            'TS8cb5a80e027': '08aa63561aab2000ccbef9915b6891a638e9f0248da8060ad76e98f85756f6f0eae72e917da4f37a08a47e84b5113000ccf54c6242170792aeb71df8c8725fbb80bbf1a46ee421ab38b2d35a472b602136cfdcd565fe7745f3eb0d7c10771558',
            '_pxde': '9b75b22ab77248b7c73be0a8aba4afc61e95d8a362c894bd6c3216e6b51227c1:eyJ0aW1lc3RhbXAiOjE3NTYwNzU2NTEzNDB9',
            'com.wm.reflector': 'reflectorid:0000000000000000000000@lastupd:1756075668315@firstcreate:1738075562989',
            'xptc': '_m%2B9~assortmentStoreId%2B1198',
            'xptwg': '2498219387:1FF73ED4EBAE5E0:4E2E622:A1E3E9B7:B9B0EC4C:A98007D6:',
            'xptwj': 'uz:44c6aec69a7b2ff43043:rhez+3PqadFOTrNfLtlJvAWUUrJYr5kUve9nvdZq8Gt451T1G0Lh6w160z59bLGp/IyOB2WOKv0UQXDajvWbTO/q0XQO9Fp3cJk4tVQc7D7kLar1Hc3CSo8fZIQtBHXudfe7/OT9E48NN2Ig5aaXiTPBFMHaqS+C0zl/pF1vUHoM9TcnDjAzgspsUcNJbyHcNhZfoaOQ83sWWctoJBzY5C4g',
            'TS012768cf': '01d8831d2567b6853a73e8786ed7b975d2e6150b5b57a54138eb34c95673b0bde1c8e4cb84d97486446215f67c0fe0662af90b9582',
            'TS01a90220': '01d8831d2567b6853a73e8786ed7b975d2e6150b5b57a54138eb34c95673b0bde1c8e4cb84d97486446215f67c0fe0662af90b9582',
            'TS2a5e0c5c027': '0891aa67d0ab2000db6b42689507680428bee381aeacede5d8c461bb0a9226d99faa7364e0e7fbce08a9f33fed1130001af748986f3332fb377d7b71de71e5da26e8951e7069a5cd73df67cdf00370883e63abb8fbc68e3e5a707a7bde0d2a80',
            'akavpau_p2': '1756076269~id=430aaf3abeabd272cffb14801a484236',
            'bm_mi': 'EF6C6D756DD5D4666FBBEC28298EFA8D~YAAQ0iXAF0cdNsaYAQAAnjdE3hyzd+WZa3cYJVE2tXFStBbKwM9nQ6GEY6MIqeNNwSiZ7gPiHEkRIop2IebBszYhoyr6E6juS1s1Rq4FlvIQtywBPklw9CT0keHaGMIUJ0IAuXNIPFCYf2AOkCyDZA7Uci6UZV2a7tYGCpl6yBAl2SeEEVOuWivb1EyknHwJiaSR5wsY75SsKJeyf94NCVHGid9TPiQso7h9xsVcewh8jMILM1DqfJ2aKoUhIWWjcx5zNKRJ++EC8oUUyHiNwoUEpzY3Af/89yFED0j+jhC6rDdo8Sa6YQssd1Xx0SA=~1',
            'bm_sv': '620BD55B6CC07F8CBC3176DC46B5EA71~YAAQ0iXAF0gdNsaYAQAAnjdE3hyZk8Yh+naGdfrkB3W2AkIY8KLeHQ4MvGnnrxfWtLO6ihpCjZpaBVCxi3m+bOgkGCoawwNFjjnAkc2W/hxgR4Zev0xwuO0QR882P8/gMNjA4frOvSPlDoJMJx8I3ogB4GZHzW4ucbYmW0xkF6LPGK8NTUVfJ3kf/OKEbow2UFh4CSx33SHBKzxUXVij87wg9awvi/tVPIUX9K1XleqF3/qawgtTmnXbuRGYE9Ah9KQ=~1',
        }
        
        # Convert to Playwright cookie format
        cookies = []
        for name, value in cookie_dict.items():
            cookies.append({
                'name': name,
                'value': value,
                'domain': '.walmart.com',
                'path': '/',
                'httpOnly': False,
                'secure': True,
                'sameSite': 'Lax'
            })
        
        return cookies
    
    def _get_original_headers(self) -> Dict[str, str]:
        """Get headers using the selected browser persona. If header_builder is available, use its advanced headers."""
        # If we have a header builder (with store identification), use its advanced headers
        if self.header_builder:
            return self.header_builder.build_advanced_headers()
        
        # Fallback to persona-based headers for backward compatibility
        return {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'downlink': self.persona.device_specs.get('downlink', '10'),
            'dpr': self.persona.device_specs.get('dpr', '1'),
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'sec-ch-ua': self.persona.sec_ch_ua,
            'sec-ch-ua-mobile': self.persona.sec_ch_ua_mobile,
            'sec-ch-ua-platform': self.persona.sec_ch_ua_platform,
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.persona.user_agent,
        }
    
    def _build_original_cookies_from_header_builder(self) -> List[Dict[str, Any]]:
        """Convert header builder cookie string to Playwright cookie list format."""
        if not self.header_builder or not hasattr(self.header_builder, '_base_location_cookies'):
            return []
        
        cookies = []
        cookie_string = self.header_builder._base_location_cookies
        
        # Parse the cookie string (format: "name1=value1; name2=value2; ...")
        cookie_pairs = [pair.strip() for pair in cookie_string.split(';') if pair.strip()]
        
        for pair in cookie_pairs:
            if '=' in pair:
                name, value = pair.split('=', 1)  # Split only on first '=' to handle values with '='
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.walmart.com',
                    'path': '/',
                    'httpOnly': False,
                    'secure': True,
                    'sameSite': 'Lax'
                })
        
        return cookies
    
    def _build_enhanced_cookies_with_store_data(self) -> List[Dict[str, Any]]:
        """Combine base cookies with store-specific data using conservative approach."""
        # Start with the proven working base cookies
        base_cookies = self._get_original_cookies()
        
        if not self.header_builder or not hasattr(self.header_builder, '_base_location_cookies'):
            if self.logger:
                self.logger.info(f"🍪 [Enhanced Cookies] Using base cookies only -> {len(base_cookies)} total cookies")
            return base_cookies
        
        # Parse store-specific cookies from header builder
        store_cookie_string = self.header_builder._base_location_cookies
        cookie_pairs = [pair.strip() for pair in store_cookie_string.split(';') if pair.strip()]
        
        # Create a dict of base cookies for easy lookup/replacement
        base_cookie_dict = {cookie['name']: cookie for cookie in base_cookies}
        
        # Only update specific store location cookies that might need YAML store data
        # Be very conservative - only touch cookies that are definitely store-related
        store_specific_cookies = ['assortmentStoreId', 'locGuestData', 'locDataV3', 'xptc']
        changes_made = 0
        
        for pair in cookie_pairs:
            if '=' in pair:
                name, value = pair.split('=', 1)
                name = name.strip()
                value = value.strip()
                
                # Only update if it's a store-specific cookie AND the value is different
                if name in store_specific_cookies:
                    if name not in base_cookie_dict or base_cookie_dict[name]['value'] != value:
                        base_cookie_dict[name] = {
                            'name': name,
                            'value': value,
                            'domain': '.walmart.com',
                            'path': '/',
                            'httpOnly': False,
                            'secure': True,
                            'sameSite': 'Lax'
                        }
                        changes_made += 1
                        if self.logger:
                            self.logger.info(f"🔄 [Enhanced Cookies] Updated store cookie: {name}")
        
        # Convert back to list
        enhanced_cookies = list(base_cookie_dict.values())
        
        if self.logger:
            self.logger.info(f"🍪 [Enhanced Cookies] Base: {len(base_cookies)}, Changes: {changes_made}, Total: {len(enhanced_cookies)}")
        
        return enhanced_cookies
        
    async def setup_browser(self) -> None:
        """Initialize Playwright browser with stealth configurations."""
        print("🚀 Setting up Playwright stealth browser...")
        
        playwright = await async_playwright().start()
        
        # Launch with stealth-optimized settings
        self.browser = await playwright.chromium.launch(
            headless=True,  # Run in headless mode for stealth
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-features=TranslateUI,VizDisplayCompositor',
                '--disable-ipc-flooding-protection',
                '--renderer-process-limit=1',
                '--max_old_space_size=4096'
            ],
            channel='chrome'  # Use system Chrome if available
        )
        
        # Get proxy settings for context creation
        proxy_settings = self._get_proxy_settings()
        
        # Prepare context options using persona data to maintain consistency
        context_options = {
            'user_agent': self.persona.user_agent,
            'viewport': self.persona.viewport,
            'extra_http_headers': self._build_base_headers(),
            'locale': 'en-US',  # Consistent with all Chrome personas
            'timezone_id': 'America/Chicago',  # Texas timezone for geographic consistency
            'color_scheme': 'light',
            'reduced_motion': 'no-preference'
        }
        
        # Add proxy if available
        if proxy_settings:
            context_options['proxy'] = proxy_settings
            print(f"🌐 Configuring proxy: {proxy_settings['server']}")
        else:
            print("⚠️  No proxy configured - using direct connection")
        
        # Create context with proxy support and SSL certificate handling
        self.context = await self.browser.new_context(
            **context_options,
            ignore_https_errors=True  # Ignore SSL certificate errors for proxies
        )
        
        # Set the original cookies before navigation
        print("🍪 Setting original cookies from requests.get() version...")
        await self.context.add_cookies(self.original_cookies)
        print(f"✅ Set {len(self.original_cookies)} original cookies")
        
        # Add stealth scripts to avoid detection
        await self.context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock Chrome runtime for extension compatibility
            window.chrome = {
                runtime: {},
            };
            
            // Mock permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)

    def _build_base_headers(self) -> Dict[str, str]:
        """Build base headers for Playwright requests using persona data."""
        # Use the persona-based headers
        headers = self.original_headers.copy()
        
        # Add device performance headers from persona
        headers.update({
            'rtt': self.persona.device_specs.get('rtt', '50'),
            'ect': self.persona.device_specs.get('ect', '4g')
        })
        
        return headers
        
    def _get_proxy_settings(self) -> Optional[Dict[str, str]]:
        """Get BrightData proxy configuration."""
        proxy_user = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_USER")
        proxy_pass = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PASSWORD")
        proxy_host = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_HOST")
        proxy_port = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PORT")
        
        if all([proxy_user, proxy_pass, proxy_host, proxy_port]):
            return {
                'server': f'http://{proxy_host}:{proxy_port}',
                'username': proxy_user,
                'password': proxy_pass
            }
        return None

    async def harvest_walmart_cookies(self, target_url: str = "https://www.walmart.com") -> Dict[str, Any]:
        """
        Navigate to Walmart and harvest cookies and headers dynamically.
        
        Args:
            target_url: URL to harvest cookies from
            
        Returns:
            Dictionary containing cookies, headers, response status, and metadata
        """
        print(f"🌾 Starting cookie harvest from {target_url}")
        
        # Get proxy settings for use throughout this method
        proxy_settings = self._get_proxy_settings()
        
        if not self.context:
            await self.setup_browser()
            
        page = await self.context.new_page()
        
        # Track network responses to capture actual HTTP status codes
        network_responses = []
        
        async def handle_response(response):
            network_responses.append({
                'url': response.url,
                'status': response.status,
                'status_text': response.status_text,
                'headers': dict(response.headers)
            })
            if response.url == target_url or response.url.startswith(target_url):
                print(f"🌐 Network Response: {response.status} {response.status_text} for {response.url}")
        
        page.on('response', handle_response)
        
        try:
            # Navigate to target URL and wait for full load
            print(f"🔍 Navigating to {target_url}...")
            if proxy_settings:
                print(f"🌐 Using proxy: {proxy_settings['server']} with user: {proxy_settings['username']}")
            
            response = await page.goto(
                target_url,
                wait_until='domcontentloaded',  # Less strict than networkidle
                timeout=60000  # Increased timeout to 60 seconds
            )
            
            if response:
                status_code = response.status
                print(f"📡 Response status: {status_code}")
                if status_code >= 400:
                    print(f"🚨 HTTP Error {status_code}: {response.status_text}")
                    print(f"🔍 Response URL: {response.url}")
                    # Try to get response headers for debugging
                    response_headers = response.headers
                    print(f"🔍 Response headers: {dict(response_headers)}")
            else:
                status_code = None
                print("⚠️  No response received")
            
            # Wait a moment for dynamic content and cookies to be set
            await page.wait_for_timeout(2000)
            
            # Harvest cookies from the browser context
            print("🍪 Harvesting cookies from browser context after navigation...")
            all_cookies = await self.context.cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in all_cookies}
            
            # Separate original vs new cookies for analysis
            original_cookie_names = {cookie['name'] for cookie in self.original_cookies}
            new_cookies = {name: value for name, value in cookie_dict.items() if name not in original_cookie_names}
            preserved_cookies = {name: value for name, value in cookie_dict.items() if name in original_cookie_names}
            
            print(f"✅ Total cookies after navigation: {len(cookie_dict)}")
            print(f"   📤 Original cookies preserved: {len(preserved_cookies)}")
            print(f"   🆕 New cookies from Walmart: {len(new_cookies)}")
            
            if new_cookies:
                print(f"   📋 New cookies: {', '.join(new_cookies.keys())}")
            
            # Get the final request headers from the page
            print("📋 Extracting request headers...")
            
            # Use page evaluation to get runtime browser properties for verification
            browser_properties = await page.evaluate("""
                () => {
                    return {
                        'runtime-user-agent': navigator.userAgent,
                        'runtime-language': navigator.language,
                        'runtime-platform': navigator.platform,
                        'runtime-vendor': navigator.vendor,
                        'cookie-enabled': navigator.cookieEnabled
                    };
                }
            """)
            
            # Use the original headers as the primary headers sent
            all_headers = self.original_headers.copy()
            
            # Add runtime properties for verification
            all_headers.update({f"runtime-{k}": v for k, v in browser_properties.items()})
            
            print("✅ Using original headers from requests.get() version")
            print(f"   📤 User-Agent: {all_headers.get('user-agent', 'Not set')[:80]}...")
            print(f"   📤 Platform: {all_headers.get('sec-ch-ua-platform', 'Not set')}")
            
            # Get some page metadata for validation
            page_title = await page.title()
            current_url = page.url
            
            harvest_result = {
                'status_code': status_code,
                'url': current_url,
                'page_title': page_title,
                'cookies': cookie_dict,
                'headers': all_headers,
                'cookie_count': len(cookie_dict),
                'original_cookies_sent': len(self.original_cookies),
                'new_cookies_received': len(new_cookies),
                'preserved_cookies': len(preserved_cookies),
                'harvest_timestamp': datetime.now().isoformat(),
                'persona_id': self.persona.persona_id,
                'proxy_used': proxy_settings is not None,
                'store_identification': getattr(self, 'store_identification', None),
                'network_responses': network_responses
            }
            
            print(f"🎯 Cookie harvest complete: {len(cookie_dict)} cookies, {len(all_headers)} headers")
            return harvest_result
            
        except Exception as e:
            print(f"❌ Error during harvest: {str(e)}")
            
            # Show network responses that were captured before the error
            if network_responses:
                print(f"🌐 Captured {len(network_responses)} network responses before error:")
                for resp in network_responses[-3:]:  # Show last 3 responses
                    print(f"   📡 {resp['status']} {resp['status_text']} - {resp['url']}")
                    if resp['status'] >= 400:
                        print(f"      🚨 Error Response Headers: {resp['headers']}")
            else:
                print("🌐 No network responses captured (connection failed at network level)")
            
            return {
                'status_code': None,
                'url': target_url,
                'page_title': None,
                'cookies': {},
                'headers': {},
                'cookie_count': 0,
                'error': str(e),
                'network_responses': network_responses,
                'harvest_timestamp': datetime.now().isoformat(),
                'persona_id': self.persona.persona_id,
                'proxy_used': proxy_settings is not None
            }
        finally:
            await page.close()
    
    async def close(self):
        """Clean up browser resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

def format_cookies_for_requests(cookies: Dict[str, str]) -> str:
    """Format cookies dictionary as a string for requests library."""
    return '; '.join([f"{name}={value}" for name, value in cookies.items()])

def print_harvest_results(result: Dict[str, Any]) -> None:
    """Pretty print the harvest results."""
    print("\n" + "="*80)
    print("🏪 WALMART COOKIE HARVEST RESULTS (Using Original requests.get() Cookies/Headers)")
    print("="*80)
    
    print(f"📊 Status: {result['status_code']}")
    print(f"🌐 URL: {result['url']}")
    print(f"📄 Page Title: {result['page_title']}")
    print(f"🕒 Timestamp: {result['harvest_timestamp']}")
    print(f"🎭 Persona: {result['persona_id']}")
    print(f"🌐 Proxy Used: {result['proxy_used']}")
    
    # Show store information if available (for analysis)
    if result.get('store_identification'):
        store_info = result['store_identification']
        print(f"🏪 Store Analysis: {store_info.get('retailer_store_id', 'Unknown')} ({store_info.get('store_display_name', 'Unknown')})")
        print(f"   📍 Location: {store_info.get('store_city', 'Unknown')}, {store_info.get('store_state', 'Unknown')} {store_info.get('store_zip_code', 'Unknown')}")
    
    # Show cookie statistics
    if 'original_cookies_sent' in result:
        print(f"📤 Original cookies SENT: {result['original_cookies_sent']}")
        print(f"📥 New cookies RECEIVED: {result.get('new_cookies_received', 0)}")
        print(f"🔄 Original cookies PRESERVED: {result.get('preserved_cookies', 0)}")
    
    # Show network response information for debugging
    if 'network_responses' in result and result['network_responses']:
        print(f"🌐 Network Activity: {len(result['network_responses'])} responses captured")
        # Show the main page response and any error responses
        main_responses = [r for r in result['network_responses'] if result['url'] in r['url']]
        error_responses = [r for r in result['network_responses'] if r['status'] >= 400]
        
        if main_responses:
            main_resp = main_responses[0]
            print(f"   📡 Main Response: {main_resp['status']} {main_resp['status_text']}")
        
        if error_responses:
            print(f"   🚨 Found {len(error_responses)} error responses:")
            for resp in error_responses[:3]:  # Show first 3 error responses
                print(f"      📡 {resp['status']} {resp['status_text']} - {resp['url']}")
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"\n🍪 COOKIES HARVESTED ({result['cookie_count']} total):")
    print("-" * 60)
    for name, value in result['cookies'].items():
        # Truncate long values for readability
        display_value = value[:50] + "..." if len(value) > 50 else value
        print(f"  {name} = {display_value}")
    
    print(f"\n📋 HEADERS ({len(result['headers'])} total):")
    print("-" * 60)
    for name, value in result['headers'].items():
        # Truncate long values for readability
        display_value = str(value)[:80] + "..." if len(str(value)) > 80 else str(value)
        print(f"  {name}: {display_value}")
    
    print(f"\n🔧 COOKIE STRING FOR REQUESTS:")
    print("-" * 60)
    cookie_string = format_cookies_for_requests(result['cookies'])
    # Print cookie string in chunks for readability
    chunk_size = 100
    for i in range(0, len(cookie_string), chunk_size):
        chunk = cookie_string[i:i+chunk_size]
        print(f"  {chunk}")
    
    # Identify critical Walmart cookies
    critical_cookies = [
        'assortmentStoreId', 'locDataV3', 'locGuestData', 'xptc', 
        'isoLoc', '_astc', 'hasACID', 'ACID', '_m'
    ]
    
    found_critical = [cookie for cookie in critical_cookies if cookie in result['cookies']]
    missing_critical = [cookie for cookie in critical_cookies if cookie not in result['cookies']]
    
    print(f"\n🎯 CRITICAL WALMART COOKIES ANALYSIS:")
    print("-" * 60)
    print(f"✅ Found ({len(found_critical)}): {', '.join(found_critical)}")
    if missing_critical:
        print(f"❌ Missing ({len(missing_critical)}): {', '.join(missing_critical)}")
    
    print("\n" + "="*80)


def load_store_by_id(store_id: str, yaml_file: str = '../data/Walmart_stores.yaml') -> dict:
    with open(yaml_file, 'r') as file:
        stores = yaml.safe_load(file)

    for store in stores:
        if store.get('store_id') == store_id:
            return store

    raise ValueError(f"Store with store_id {store_id} not found.")


def load_search_by_query(query: str, yaml_file: str = '../data/Walmart_fetch_search.yaml') -> dict:
    query_lower = query.lower()

    with open(yaml_file, 'r') as file:
        saved_queries = yaml.safe_load(file)

    for saved_query in saved_queries:
        if saved_query.get('query', '').lower() == query_lower:
            return saved_query

    raise ValueError(f"Search with query '{query}' not found.")


async def main():
    """Main execution function."""
    logger, logger_manager, project_config = setup_config_logging(__name__)

    # Configuration (similar to main.py)
    retailer = 'Walmart'
    store_id = '1198'
    fetch_type = 'search'
    query = 'Milk'  # Simple query for testing

    # Load configuration using existing utilities with absolute paths
    project_root = os.path.dirname("/Users/dalesmith/Projects/arachne/")
    stores_file = os.path.join(project_root, 'data', 'Walmart_stores.yaml')
    search_file = os.path.join(project_root, 'data', 'Walmart_fetch_search.yaml')

    store_identification = load_store_by_id(store_id=store_id, yaml_file=stores_file)
    search_config = load_search_by_query(query=query, yaml_file=search_file)

    query = search_config.get('query')
    first_page_search_url = search_config.get('search_url')

    logger.info(f"🎯 [Config] Retailer: {retailer}")
    logger.info(f"🎯 [Config] Store: {store_id} ({store_identification.get('store_display_name', 'Unknown')})")

    # Create harvester WITHOUT store identification to avoid HTTP errors
    # Store identification will be used for reporting only
    print("🔧 [ISOLATION FIX] Creating harvester with proven working approach...")
    harvester = PlaywrightCookieHarvester(logger=logger)
    
    # Store the identification data for analysis/reporting only
    harvester.store_identification = store_identification

    try:
        # Harvest cookies and headers from Walmart homepage
        result = await harvester.harvest_walmart_cookies("https://www.walmart.com")
        
        # Print detailed results
        print_harvest_results(result)
        
        # Save response to file for comparison
        if result['status_code'] and result['status_code'] == 200:
            print(f"\n💾 Saving HTML content to walmart_home_page_output.html")
            # We would need to get the page content separately if needed
            print("Note: Use page.content() during harvest if HTML content is needed")
        
    finally:
        await harvester.close()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())