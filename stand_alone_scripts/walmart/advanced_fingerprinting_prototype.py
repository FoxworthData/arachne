"""
Advanced Browser Fingerprinting Prototype

This script demonstrates how we could implement more sophisticated browser fingerprinting.

Features demonstrated:
- Session-consistent browser personas
- Modern Chrome Client Hints headers
- Device performance simulation
- Cookie seeding simulation
- Fetch Metadata headers
- Advanced bot evasion techniques

This is a standalone prototype that uses existing utilities where possible
but implements advanced features without modifying the core codebase.
"""

import asyncio
import json
import os
import random
import time
import hashlib
import base64
import uuid
from datetime import datetime, timedelta
from logging import Logger
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

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

import aiohttp


def get_proxies():
    proxy_user = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_USER")
    proxy_pass = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PASSWORD")
    proxy_host = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_HOST")
    proxy_port = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PORT")

    proxies = {'http': f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
                'https': f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}'}
    return proxies

def get_proxy(proxy_type: str = 'http'):
    proxies = get_proxies()
    return proxies.get(proxy_type, proxies[proxy_type])


@dataclass
class BrowserPersona:
    """
    Browser persona with consistent fingerprinting data.
    """
    user_agent: str
    sec_ch_ua: str
    sec_ch_ua_mobile: str
    sec_ch_ua_platform: str
    device_specs: Dict[str, str]
    persona_id: str
    viewport_width: int
    viewport_height: int
    
    @classmethod
    def generate_persona_id(cls, user_agent: str) -> str:
        """Generate a unique persona ID based on user agent characteristics."""
        ua_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
        
        if "Chrome" in user_agent and "Windows" in user_agent:
            return f"chrome-win-{ua_hash}"
        elif "Chrome" in user_agent and "Macintosh" in user_agent:
            return f"chrome-mac-{ua_hash}"
        elif "Safari" in user_agent and "Macintosh" in user_agent:
            return f"safari-mac-{ua_hash}"
        else:
            return f"unknown-{ua_hash}"


class BrowserPersonaChooser:
    """
    Browser persona management, contains curated, tested browser personas for maximum bot evasion.
    """
    
    def __init__(self):
        # Curated personas based on successful bot evasion testing
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
            # Safari macOS - High success rate
            {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
                "sec_ch_ua": '"Safari";v="17", "Not.A/Brand";v="24"',
                "sec_ch_ua_mobile": "?0",
                "sec_ch_ua_platform": '"macOS"',
                "device_specs": {
                    "downlink": "9.8",
                    "dpr": "2", 
                    "rtt": "45",
                    "ect": "4g"
                },
                "viewport_width": 1440,
                "viewport_height": 900
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


class RealCookieSeeder:
    """
    Real cookie seeding system that harvests authentic cookies from actual Walmart sessions.
    This demonstrates how to properly seed browser fingerprints with genuine session data.
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.session_cache = {}  # In production, this would be Redis/database
        self.cache_ttl = 3600  # 1 hour TTL for harvested cookies
    
    async def harvest_walmart_session(self, persona: BrowserPersona) -> Dict[str, Any]:
        """
        Harvest real cookies by making an actual request to Walmart homepage.
        This gets us authentic session cookies that won't trigger bot detection.
        """
        self.logger.info(f"🌾 [Real Harvest] Harvesting authentic cookies for {persona.persona_id}")
        
        # Create a clean session for harvesting
        async with aiohttp.ClientSession() as session:
            # Build realistic headers for initial harvest request
            harvest_headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "sec-ch-ua": persona.sec_ch_ua,
                "sec-ch-ua-mobile": persona.sec_ch_ua_mobile,
                "sec-ch-ua-platform": persona.sec_ch_ua_platform,
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate", 
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
                "user-agent": persona.user_agent
            }
            
            try:
                # Make initial request to Walmart homepage to harvest session cookies
                self.logger.info("--- HEADERS AIOHTTP IS SENDING to www.walmart.com for seeding ---")
                for key, value in harvest_headers.items():
                    self.logger.info(f"  {key}: {value}")
                self.logger.info("-------------------------------------")

                async with session.get(
                    "https://www.walmart.com",
                    headers=harvest_headers,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        self.logger.error(f"❌ [Harvest] Failed to harvest cookies: HTTP {response.status}")
                        return {"success": False, "cookies": {}, "headers": {}}
                    
                    # Extract all cookies set by Walmart
                    harvested_cookies = {}
                    if hasattr(response, 'cookies') and response.cookies:
                        for cookie_name, cookie in response.cookies.items():
                            if hasattr(cookie, 'value'):
                                # SimpleCookie object
                                harvested_cookies[cookie_name] = cookie.value
                            else:
                                # Direct cookie value
                                harvested_cookies[cookie_name] = str(cookie)
                    
                    self.logger.info(f"✅ [Harvest] Successfully harvested {len(harvested_cookies)} authentic cookies")
                    self.logger.debug(f"🍪 [Harvest] Cookie names: {list(harvested_cookies.keys())}")
                    
                    # Cache the harvested cookies with TTL
                    cache_key = f"walmart_{persona.persona_id}_{int(time.time() / self.cache_ttl)}"
                    self.session_cache[cache_key] = {
                        "cookies": harvested_cookies,
                        "harvested_at": time.time(),
                        "persona_id": persona.persona_id
                    }
                    
                    return {
                        "success": True,
                        "cookies": harvested_cookies,
                        "headers": {
                            "x-session-harvested": "true",
                            "x-harvest-time": str(int(time.time())),
                            "x-persona-id": persona.persona_id
                        },
                        "harvested_at": time.time(),
                        "cache_key": cache_key
                    }
                    
            except Exception as e:
                self.logger.error(f"❌ [Harvest] Cookie harvesting failed: {e}")
                return {"success": False, "cookies": {}, "headers": {}}
    
    async def get_seeded_cookies(self, target_url: str, persona: BrowserPersona) -> Dict[str, Any]:
        """
        Get authentic seeded cookies, either from cache or by harvesting fresh ones.
        """
        # Check cache first
        cache_key = f"walmart_{persona.persona_id}_{int(time.time() / self.cache_ttl)}"
        
        if cache_key in self.session_cache:
            cached_data = self.session_cache[cache_key]
            age = time.time() - cached_data["harvested_at"]
            if age < self.cache_ttl:
                self.logger.info(f"🎯 [Cache Hit] Using cached cookies (age: {age:.0f}s)")
                return {
                    "success": True,
                    "cookies": cached_data["cookies"],
                    "headers": {
                        "x-session-cached": "true",
                        "x-cache-age": str(int(age))
                    },
                    "harvested_at": cached_data["harvested_at"],
                    "cache_key": cache_key
                }
        
        # Cache miss or expired - harvest fresh cookies
        return await self.harvest_walmart_session(persona)


class AdvancedWalmartHeaderBuilder:
    """
    Header builder that implements more sophisticated fingerprinting techniques
    """
    
    def __init__(self, store_identification: dict, persona: BrowserPersona, cookie_seeder: RealCookieSeeder, logger):
        self.store_identification = store_identification
        self.persona = persona
        self.cookie_seeder = cookie_seeder
        self.logger = logger
        
        self._build_location_cookies()
    
    def _build_location_cookies(self):
        import urllib.parse
        
        acid = str(uuid.uuid4())
        address_timestamp = int(time.time() * 1000)
        delivery_timestamp = int(time.time() * 1000)
        refresh_timestamp = int((time.time() + (6 * 60 * 60)) * 1000)  # 6 hours ahead
        
        # Complete location_guest_data matching Reaper exactly
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
                'timestamp': address_timestamp,
                'type': 'partial-location'
            },
            'showLMPEntryPoint': False,
            'showLocalExperience': False,
            'storeIntent': 'PICKUP',
            'validateKey': f'prod:v2:{acid}'
        }
        
        # Complete locDataV3 matching Reaper exactly
        locDataV3 = {
            'assortment': {
                'intent': 'PICKUP',
                'nodeId': self.store_identification['store_id']
            },
            'delivery': {
                'accessPoints': [{'accessType': 'DELIVERY_ADDRESS'}],
                'address': {
                    'addressLine1': self.store_identification['store_address'],
                    'city': self.store_identification['store_city'],
                    'country': self.store_identification['store_country'],
                    'postalCode': self.store_identification['store_zip_code'],
                    'state': self.store_identification['store_state']
                },
                'allowedWICAgencies': [self.store_identification['store_state']],
                'isExpressDeliveryOnly': False,
                'nodeId': self.store_identification['store_id'],
                'scheduledEnabled': False,
                'selectionType': 'LS_SELECTED',
                'supportedAccessTypes': ['DELIVERY_ADDRESS', 'ACC'],
                'timeZone': self.store_identification.get('store_time_zone', 'America/Chicago'),
                'unScheduledEnabled': False
            },
            'instore': False,
            'isDefaulted': False,
            'isExplicit': False,
            'isgeoIntlUser': False,
            'pickup': [
                {
                    'address': {
                        'addressLine1': self.store_identification['store_address'],
                        'city': self.store_identification['store_city'],
                        'country': self.store_identification['store_country'],
                        'postalCode': self.store_identification['store_zip_code'],
                        'state': self.store_identification['store_state']
                    },
                    'allowedWICAgencies': [self.store_identification['store_state']],
                    'nodeId': self.store_identification['store_id'],
                    'scheduledEnabled': True,
                    'selectionType': 'CUSTOMER_SELECTED',
                    'timeZone': self.store_identification.get('store_time_zone', 'America/Chicago'),
                    'unScheduledEnabled': True
                }
            ],
            'refreshAt': refresh_timestamp,
            'shippingAddress': {
                'allowedWICAgencies': [self.store_identification['store_state']],
                'city': self.store_identification['store_city'],
                'countryCode': 'USA',
                'giftAddress': False,
                'postalCode': self.store_identification['store_zip_code'],
                'state': self.store_identification['store_state'],
                'timeZone': self.store_identification.get('store_time_zone', 'America/Chicago')
            },
            'validateKey': f'prod:v2:{acid}',
            'pref': 'PICKUP'
        }
        
        # Encode location data - standard base64 for locGuestData
        encoded_location_guest_data = base64.urlsafe_b64encode(json.dumps(location_guest_data).encode()).decode()
        
        # Double encoding for locDataV3 (JSON → base64 → URL encode) like Reaper
        json_str = json.dumps(locDataV3, separators=(',', ':'))  # Compact JSON
        base64_bytes = base64.urlsafe_b64encode(json_str.encode('utf-8'))
        base64_str = base64_bytes.decode('utf-8')
        encoded_locDataV3 = urllib.parse.quote(base64_str)  # URL encode the base64
        
        # Cookie string format matching Reaper exactly
        self._base_location_cookies = (
            f"hasACID=true; "
            f"ACID={acid}; "
            f"assortmentStoreId={self.store_identification['store_id']}; "
            f"hasLocData=1; "
            f"locGuestData={encoded_location_guest_data}; "
            f"locDataV3={encoded_locDataV3}"
        )
    
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
    
    async def build_advanced_headers(self, target_url: str) -> Dict[str, str]:
        """
        Build advanced headers with modern browser fingerprinting.
        """
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
            
            "cookie": self._base_location_cookies
        }
        
        # Add device performance headers
        headers.update(device_headers)
        
        # Enhance with cookie seeding
        try:
            seeded_data = await self.cookie_seeder.get_seeded_cookies(target_url, self.persona)
            if seeded_data.get('success'):
                headers = self._merge_cookies_and_headers(headers, seeded_data)
                self.logger.info(f"✅ [Advanced Headers] Enhanced with {len(seeded_data.get('cookies', {}))} seeded cookies")
            else:
                self.logger.info(f"🏗️ [Advanced Headers] Using foundation cookies only")
        except Exception as e:
            self.logger.warning(f"⚠️ [Advanced Headers] Cookie seeding failed: {e}")
        
        self.logger.info(f"🏗️ [Advanced Headers] Built {len(headers)} headers for {self.persona.persona_id}")
        return headers
    
    def _merge_cookies_and_headers(self, base_headers: Dict[str, str], seeded_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Merge foundation location cookies with harvested authentic cookies.
        Real cookies take precedence for session authenticity.
        """
        enhanced_headers = base_headers.copy()
        
        # Add seeded headers (tracking/session info)
        seeded_headers = seeded_data.get('headers', {})
        for header_name, header_value in seeded_headers.items():
            if header_name.lower() not in [h.lower() for h in enhanced_headers.keys()]:
                enhanced_headers[header_name] = header_value
        
        # Merge cookies with priority: real harvested cookies + location cookies
        seeded_cookies = seeded_data.get('cookies', {})
        if seeded_cookies:
            base_cookie = enhanced_headers.get('cookie', '')
            
            # Start with harvested cookies (authentic session data)
            cookie_parts = []
            for cookie_name, cookie_value in seeded_cookies.items():
                cookie_parts.append(f"{cookie_name}={cookie_value}")
            
            # Add location cookies (but avoid duplicates)
            if base_cookie:
                for cookie_part in base_cookie.split('; '):
                    if '=' in cookie_part:
                        cookie_name = cookie_part.split('=')[0]
                        # Only add if not already present from harvested cookies
                        if cookie_name not in seeded_cookies:
                            cookie_parts.append(cookie_part)
                    else:
                        cookie_parts.append(cookie_part)
            
            enhanced_headers['cookie'] = "; ".join(cookie_parts)
        
        return enhanced_headers


class AdvancedAiohttpFetcher:
    """
    Enhanced fetcher that maintains session-consistent persona across all requests.
    """
    
    def __init__(
            self,
            store_identification: dict,
            paginator: WalmartPaginator,
            persona: BrowserPersona,
            header_builder: AdvancedWalmartHeaderBuilder,
            get_proxy: Optional[Callable[[], Optional[str]]] = None,
            project_config: ConfigLoader = None,
            logger: Logger = None,
            max_concurrent_requests: int = 3
    ):
        self.store_identification = store_identification
        self.paginator = paginator
        self.persona = persona
        self.header_builder = header_builder
        self.get_proxy = get_proxy
        self.project_config = project_config
        self.logger = logger
        self.max_concurrent_requests = max_concurrent_requests
        
        # Performance configuration
        config = self.project_config.get('fetcher', {})
        self.timeout = config.get('timeout_seconds', 30)
        self.max_retries = config.get('max_retries', 2)
    
    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
        """Fetch single page with advanced fingerprinting."""
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            try:
                # Build advanced headers for this request (consistent persona)
                headers = await self.header_builder.build_advanced_headers(url)
                proxy = self.get_proxy() if self.get_proxy else None
                
                self.logger.debug(f"🌐 [Fetch] Attempt {retries + 1}/{self.max_retries + 1} for {url}")
                self.logger.debug(f"🎭 [Fetch] Using persona: {self.persona.persona_id}")

                self.logger.info("--- HEADERS AIOHTTP IS SENDING ---")
                for key, value in headers.items():
                    self.logger.info(f"  {key}: {value}")
                self.logger.info("-------------------------------------")

                async with session.get(
                    url,
                    headers=headers,
                    proxy=proxy,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    raise_for_status=True
                ) as response:
                    html = await response.text()
                    
                    if await self._validate_response(html, url):
                        return {
                            'url': url,
                            'html': html,
                            'status_code': response.status,
                            'error': None,
                            'persona_id': self.persona.persona_id,
                            'headers_count': len(headers)
                        }
                    else:
                        raise ValueError("Response validation failed")
                        
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"⚠️ [Fetch] Retry {retries}/{self.max_retries} for {url}: {last_error}")
                retries += 1
                
                if retries <= self.max_retries:
                    await asyncio.sleep(2 ** retries)  # Exponential backoff
        
        self.logger.error(f"❌ [Fetch] Failed to fetch {url} after {self.max_retries + 1} attempts")
        return {
            'url': url,
            'html': '',
            'status_code': None,
            'error': last_error,
            'persona_id': self.persona.persona_id,
            'headers_count': 0
        }
    
    async def _validate_response(self, html: str, url: str) -> bool:
        # Check for bot detection
        if "Robot or human" in html:
            self.logger.error(f"❌ [Validation] Bot detected for {url}")
            return False
        
        # Check for browser rejection
        if "Sorry, Walmart site doesn't work with your browser" in html:
            self.logger.error(f"❌ [Validation] Browser rejected for {url}")
            return False
        
        # Check for store ID (critical validation)
        store_id = self.store_identification['store_id']
        if f'"storeId":"{store_id}"' not in html:
            # Find what store ID Walmart actually returned
            import re
            match = re.search(r'"storeId":"(\d+)"', html)
            found_store_id = match.group(1) if match else "unknown"
            
            self.logger.error(f"❌ [Location Targeting Failed] Expected store {store_id}, got store {found_store_id}")
            self.logger.error(f"❌ [Geographic Issue] Your IP location doesn't match store {store_id} location")
            self.logger.error(f"❌ [Solution Required] Use a proxy in {self.store_identification.get('store_state', 'unknown')} state")
            
            # For prototype, continue but mark as failed
            return False
        
        self.logger.info(f"✅ [Validation] Response passed validation for {url}")
        return True
    
    async def fetch_all_with_advanced_fingerprinting(
        self, 
        start_url: str, 
        handle_result_callback
    ) -> List[Dict[str, Any]]:
        """
        Fetch all pages using advanced fingerprinting with session-consistent persona.
        """
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        config = self.project_config.get('fetcher', {})
        batch_size = config.get('batch_size', 3)  # Smaller batches for advanced mode
        min_delay = config.get('delay_min_seconds', 2.0)  # Longer delays for stealth
        max_delay = config.get('delay_max_seconds', 4.0)
        
        start_time = time.time()
        
        self.logger.info(f"🚀 [Advanced Fetch] Starting with persona: {self.persona.persona_id}")
        self.logger.info(f"🚀 [Advanced Fetch] Target: {start_url}")
        
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
        ) as session:
            # Fetch first page
            async with semaphore:
                first_page = await self.fetch_page(session, start_url)
            
            if not first_page or first_page.get('error'):
                self.logger.error(f"❌ [Advanced Fetch] Failed to fetch first page")
                if handle_result_callback:
                    handle_result_callback(first_page, 1)
                return []
            
            # Process first page
            if handle_result_callback:
                handle_result_callback(first_page, 1)
            
            # Get additional page URLs
            try:
                page_urls = self.paginator.get_page_urls(start_url, first_page['html'])
                self.logger.info(f"📄 [Advanced Fetch] Found {len(page_urls)} total pages")
            except Exception as e:
                self.logger.error(f"❌ [Advanced Fetch] Pagination failed: {e}")
                return []
            
            # Fetch remaining pages in batches
            for i in range(1, len(page_urls), batch_size):
                batch_urls = page_urls[i:i + batch_size]
                self.logger.info(f"📦 [Advanced Fetch] Processing batch {i//batch_size + 1}: {len(batch_urls)} pages")
                
                tasks = [
                    asyncio.wait_for(
                        self._fetch_with_semaphore(semaphore, session, url), 
                        timeout=self.timeout + 30
                    ) for url in batch_urls
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process batch results
                for j, result in enumerate(batch_results):
                    page_num = i + j + 1
                    if isinstance(result, Exception):
                        self.logger.error(f"❌ [Advanced Fetch] Page {page_num} failed: {result}")
                        error_result = {
                            "url": batch_urls[j],
                            "html": "",
                            "status_code": None,
                            "error": str(result),
                            "persona_id": self.persona.persona_id
                        }
                        if handle_result_callback:
                            handle_result_callback(error_result, page_num)
                    else:
                        if handle_result_callback:
                            handle_result_callback(result, page_num)
                
                # Delay between batches for stealth
                if i + batch_size < len(page_urls):
                    delay = random.uniform(min_delay, max_delay)
                    self.logger.info(f"⏱️ [Advanced Fetch] Waiting {delay:.2f}s before next batch...")
                    await asyncio.sleep(delay)
        
        elapsed = time.time() - start_time
        self.logger.info(f"✅ [Advanced Fetch] Complete in {elapsed:.2f}s using persona {self.persona.persona_id}")
        return []
    
    async def _fetch_with_semaphore(self, semaphore: asyncio.Semaphore, session: aiohttp.ClientSession, url: str):
        """Fetch with semaphore control."""
        async with semaphore:
            return await self.fetch_page(session, url)


class AdvancedFingerprintingBundle:
    """
    Advanced bundle that orchestrates sophisticated browser fingerprinting.
    """
    
    def __init__(self, retailer: str, store_identification: dict, fetch_type: str, 
                 fetch_query: str, start_url: str, project_config, logger):
        self.retailer = retailer
        self.store_identification = store_identification
        self.fetch_type = fetch_type
        self.fetch_query = fetch_query
        self.start_url = start_url
        self.project_config = project_config
        self.logger = logger
        
        self.file_storage = FileStorage(retailer, project_config, logger)
        self.file_namer = WalmartNamer(retailer, fetch_type, store_identification['store_id'])
        self.paginator = WalmartPaginator()
        
        # Initialize advanced fingerprinting components
        self.persona_chooser = BrowserPersonaChooser()
        self.session_persona = self.persona_chooser.get_random_persona()
        self.cookie_seeder = RealCookieSeeder(logger)
        self.header_builder = AdvancedWalmartHeaderBuilder(
            store_identification, self.session_persona, self.cookie_seeder, logger
        )
        self.fetcher = AdvancedAiohttpFetcher(
            store_identification=store_identification,
            paginator=self.paginator,
            persona=self.session_persona,
            header_builder=self.header_builder,
            get_proxy=get_proxy,
            project_config=project_config,
            logger=logger
        )
        
        self.session = FetcherSession(
            retailer=retailer,
            store_id=store_identification['store_id'],
            fetch_type=fetch_type,
            fetch_query=fetch_query,
            url=start_url
        )
        
        logger.info(f"🎭 [Bundle] Initialized with session persona: {self.session_persona.persona_id}")
        logger.info(f"🎭 [Bundle] Persona details: {self.session_persona.user_agent[:50]}...")
    
    def handle_result(self, result: Dict[str, Any], page_num: int, is_retry: bool = False):
        """Handle fetch results with advanced observability."""
        filename = None
        if not result.get('error'):
            filename = self.file_namer.get_html_filename(self.fetch_query, page_num=page_num)
            self.file_storage.save_html(filename, result["html"], fetch_type=self.fetch_type)
        
        # Create FetchedFile with additional observability data
        fetched_file = FetchedFile(
            retailer=self.retailer,
            store_id=self.store_identification['store_id'],
            fetch_type=self.fetch_type,
            fetch_query=self.fetch_query,
            url=result["url"],
            filename=filename,
            size=len(result.get("html", "")),
            page_number=page_num,
            fetched_time=time.time(),
            response_status_code=result.get("status_code"),
            blocked="Robot or human" in result.get("html", ""),
            success=not result.get("error"),
            message=result.get("error")
        )
        
        # Add advanced tracking data as message suffix
        if result.get('persona_id'):
            advanced_info = f"[Persona: {result['persona_id']}, Headers: {result.get('headers_count', 0)}]"
            if fetched_file.message:
                fetched_file.message += f" {advanced_info}"
            else:
                fetched_file.message = advanced_info
        
        if is_retry:
            fetched_file.retry_of_url = result["url"]
        
        self.session.add_fetched_file(fetched_file)
        
        # Log advanced fingerprinting metrics
        self.logger.info(f"📊 [Result] Page {page_num}: {result.get('status_code', 'ERROR')}, "
                        f"Persona: {result.get('persona_id', 'unknown')}, "
                        f"Size: {len(result.get('html', ''))}, "
                        f"Success: {not result.get('error')}")
    
    def get_session_summary(self) -> str:
        """Get session summary with advanced fingerprinting details."""
        self.session.close()
        base_summary = self.session.to_string()
        
        # Add advanced fingerprinting summary
        advanced_summary = f"\n[Advanced Fingerprinting Summary]\n"
        advanced_summary += f"  Session Persona: {self.session_persona.persona_id}\n"
        advanced_summary += f"  User Agent: {self.session_persona.user_agent}\n"
        advanced_summary += f"  Device Specs: {self.session_persona.device_specs}\n"
        advanced_summary += f"  Viewport: {self.session_persona.viewport_width}x{self.session_persona.viewport_height}\n"
        advanced_summary += f"  Cookie Seeding: Enabled (Real - Harvested from walmart.com)\n"
        advanced_summary += f"  Modern Headers: Chrome Client Hints, Fetch Metadata, Device Performance\n"
        
        return base_summary + advanced_summary


def setup_minimal_config():
    """Setup minimal configuration for standalone execution."""
    import logging
    
    # Simple logger setup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Minimal project config
    project_config = {
        'fetcher': {
            'timeout_seconds': 30,
            'max_retries': 2,
            'batch_size': 3,
            'delay_min_seconds': 2.0,
            'delay_max_seconds': 4.0
        }
    }
    
    return logger, None, project_config


async def main():
    """
    Main function demonstrating advanced browser fingerprinting.
    """
    try:
        logger, logger_manager, project_config = setup_config_logging(__name__)
    except:
        # Fallback to minimal config for standalone execution
        logger, logger_manager, project_config = setup_minimal_config()
    
    logger.info("🚀 Advanced Browser Fingerprinting Prototype")
    logger.info("=" * 60)

    # Configuration (similar to main.py)
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
    
    query = search_config.get('query')
    first_page_search_url = search_config.get('search_url')
    
    logger.info(f"🎯 [Config] Retailer: {retailer}")
    logger.info(f"🎯 [Config] Store: {store_id} ({store_identification.get('store_display_name', 'Unknown')})")
    logger.info(f"🎯 [Config] Query: {query}")
    logger.info(f"🎯 [Config] Start URL: {first_page_search_url}")
    
    # Create advanced fingerprinting bundle
    bundle = AdvancedFingerprintingBundle(
        retailer=retailer,
        store_identification=store_identification,
        fetch_type=fetch_type,
        fetch_query=query,
        start_url=first_page_search_url,
        project_config=project_config,
        logger=logger
    )
    
    logger.info("🎭 [Fingerprinting] Advanced browser persona initialized")
    logger.info(f"🎭 [Fingerprinting] Session persona: {bundle.session_persona.persona_id}")
    logger.info(f"🎭 [Fingerprinting] Features: Session consistency, Modern headers, Cookie seeding, Device simulation")
    
    # Execute advanced fetch with sophisticated fingerprinting
    try:
        logger.info("🚀 [Execution] Starting advanced fingerprinting fetch...")
        results = await bundle.fetcher.fetch_all_with_advanced_fingerprinting(
            first_page_search_url, 
            bundle.handle_result
        )
        
        logger.info("✅ [Execution] Advanced fingerprinting fetch complete")
        
    except Exception as e:
        logger.error(f"❌ [Execution] Advanced fetch failed: {e}", exc_info=True)
    
    # Display comprehensive session summary
    logger.info("📊 [Summary] Session Results:")
    print("\n" + "=" * 80)
    print(bundle.get_session_summary())
    print("=" * 80)
    
    logger.info("🎉 Advanced Browser Fingerprinting Prototype Complete!")
    logger.info("   This prototype demonstrates how we could implement more sophisticated bot evasion techniques")


if __name__ == "__main__":
    asyncio.run(main())