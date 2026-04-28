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
from playwright.async_api import async_playwright


def get_store_state(store_id: str) -> str:
    """Get the state for a given Walmart store ID to enable geographic targeting."""
    # Common Walmart store ID to state mapping
    store_state_map = {
        '1198': 'TX',  # San Antonio Supercenter
        '5055': 'NY',  # New York area
        # Add more as needed
    }
    return store_state_map.get(store_id, 'TX')  # Default to TX


def get_proxies(store_id: str = '1198'):
    proxy_user = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_USER")
    proxy_pass = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PASSWORD")
    proxy_host = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_HOST")
    proxy_port = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PORT")

    # Add geographic targeting based on store location
    # This prevents STORE_ID_MISMATCH errors due to geographic IP inconsistency
    target_state = get_store_state(store_id)
    proxy_user_with_targeting = f"{proxy_user}-country-US-state-{target_state}"
    
    proxies = {'http': f'http://{proxy_user_with_targeting}:{proxy_pass}@{proxy_host}:{proxy_port}',
                'https': f'http://{proxy_user_with_targeting}:{proxy_pass}@{proxy_host}:{proxy_port}'}
    return proxies

def get_proxy(proxy_type: str = 'http', store_id: str = '1198'):
    proxies = get_proxies(store_id)
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
        elif "Chrome" in user_agent and "Linux" in user_agent:
            return f"chrome-linux-{ua_hash}"
        else:
            return f"unknown-{ua_hash}"


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


class RealCookieSeeder:
    """
    Real cookie seeding system that harvests authentic cookies from actual Walmart sessions.
    Uses PLAYWRIGHT for cookie harvesting to capture JavaScript-generated cookies,
    then provides those cookies to aiohttp for actual search requests.
    
    This hybrid approach solves STORE_ID_MISMATCH errors by:
    - Using Playwright to wait for JavaScript execution and harvest dynamic cookies
    - Using aiohttp for fast, efficient search request execution with harvested cookies
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.session_cache = {}  # In production, this would be Redis/database
        self.cache_ttl = 3600  # 1 hour TTL for harvested cookies
    
    async def harvest_walmart_session(self, persona: BrowserPersona, store_identification: dict = None) -> Dict[str, Any]:
        """
        Harvest real cookies by using Playwright to wait for JavaScript execution.
        This captures JavaScript-generated store location cookies that aiohttp cannot get.
        """
        self.logger.info(f"🌾 [Playwright Harvest] Harvesting authentic cookies for {persona.persona_id}")
        
        # Initialize Playwright with proper resource management
        try:
            async with async_playwright() as playwright:
                # Launch browser
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
                
                # Build realistic headers for Playwright context
                extra_headers = {
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'accept-language': 'en-US,en;q=0.9',
                    'cache-control': 'no-cache',
                    'sec-fetch-dest': 'document',
                    'sec-fetch-mode': 'navigate',
                    'sec-fetch-site': 'none',
                    'sec-fetch-user': '?1',
                    'upgrade-insecure-requests': '1'
                }
                
                # Configure proxy if available
                proxy_config = None
                try:
                    proxy_user = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_USER")
                    proxy_pass = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PASSWORD")
                    proxy_host = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_HOST")
                    proxy_port = os.getenv("BRIGHTDATA_RESIDENTIAL_PROXY_PORT")
                    
                    if proxy_user and proxy_host:
                        # Add geographic targeting based on store location
                        # This prevents STORE_ID_MISMATCH errors due to geographic IP inconsistency
                        store_id = store_identification.get('store_id', '1198') if store_identification else '1198'
                        target_state = get_store_state(store_id)
                        proxy_user_with_targeting = f"{proxy_user}-country-US-state-{target_state}"
                        proxy_config = {
                            'server': f'http://{proxy_host}:{proxy_port}',
                            'username': proxy_user_with_targeting,
                            'password': proxy_pass
                        }
                        self.logger.info(f"🌐 [Playwright] Using {target_state}-targeted proxy for store {store_id}: {proxy_host}:{proxy_port}")
                except Exception as e:
                    self.logger.warning(f"⚠️ [Playwright] Proxy config failed: {e}")
                
                # Create browser context with persona configuration
                context = await playwright_engine.new_context(
                    user_agent=persona.user_agent,
                    viewport={'width': persona.viewport_width, 'height': persona.viewport_height},
                    extra_http_headers=extra_headers,
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
                        self.logger.debug(f"🌐 [Response] {response.url}: {response.status}")
                
                page.on('response', handle_response)
                
                # Navigate to Walmart homepage and wait for JavaScript execution
                self.logger.info("🌐 [Playwright] Navigating to Walmart.com...")
                try:
                    response = await page.goto(
                        "https://www.walmart.com",
                        wait_until='networkidle',
                        timeout=60000  # 60 second timeout
                    )
                    
                    if response:
                        response_status = response.status
                        self.logger.info(f"📄 [Playwright] Page loaded: HTTP {response_status}")
                        
                        # Check for successful page load
                        if response_status == 200:
                            # Wait a bit more for dynamic content
                            await page.wait_for_timeout(3000)
                            
                            # Get page title to verify success
                            title = await page.title()
                            self.logger.info(f"📄 [Playwright] Page title: {title}")
                            
                            # Extract all cookies from browser context
                            playwright_cookies = await context.cookies()
                            harvested_cookies = {}
                            
                            for cookie in playwright_cookies:
                                harvested_cookies[cookie['name']] = cookie['value']
                            
                            self.logger.info(f"✅ [Playwright Harvest] Successfully harvested {len(harvested_cookies)} cookies with JavaScript")
                            self.logger.debug(f"🍪 [Playwright Harvest] Cookie names: {list(harvested_cookies.keys())}")
                            
                            # Cache the harvested cookies with TTL
                            cache_key = f"walmart_{persona.persona_id}_{int(time.time() / self.cache_ttl)}"
                            self.session_cache[cache_key] = {
                                "cookies": harvested_cookies,
                                "harvested_at": time.time(),
                                "persona_id": persona.persona_id
                            }
                            
                            self.logger.info(f"🎯 [Cookie Cache] Cached {len(harvested_cookies)} cookies with key: {cache_key}")
                            
                            # Create the success result BEFORE attempting cleanup
                            success_result = {
                                "success": True,
                                "cookies": harvested_cookies,
                                "headers": {
                                    "x-session-harvested": "playwright",
                                    "x-harvest-time": str(int(time.time())),
                                    "x-persona-id": persona.persona_id,
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
                                self.logger.debug("🧹 [Cleanup] Successfully closed all Playwright resources")
                            except Exception as cleanup_error:
                                self.logger.warning(f"⚠️ [Cleanup] Resource cleanup failed (non-critical): {cleanup_error}")
                                self.logger.info("✅ [Success] Cookie harvesting succeeded despite cleanup issues")
                            
                            return success_result
                        else:
                            self.logger.error(f"❌ [Playwright Navigation] Page load failed with HTTP {response_status}")
                            self.logger.error("🔍 [Troubleshooting] This could indicate: proxy issues, bot detection, or network problems")
                    else:
                        self.logger.error(f"❌ [Playwright Navigation] No HTTP response received from Walmart.com")
                        self.logger.error("🔍 [Troubleshooting] This could indicate: network connectivity issues or proxy blocking")
                        
                except Exception as nav_error:
                    self.logger.error(f"❌ [Playwright Navigation] Failed to navigate to Walmart.com: {nav_error}")
                    self.logger.error("🔍 [Troubleshooting] This could indicate: proxy configuration errors, browser launch issues, or network problems")
                    
                # Resources automatically closed by async with context manager
                
        except Exception as e:
            self.logger.error(f"❌ [Playwright Browser] Failed to launch or configure browser: {e}")
            self.logger.error("🔍 [Troubleshooting] This could indicate: Chrome/Chromium not installed, permission issues, or proxy configuration problems")
        
        # Return failure result with helpful error context
        self.logger.error("🚫 [Cookie Harvest Failed] Unable to harvest JavaScript cookies - STORE_ID_MISMATCH errors likely")
        return {"success": False, "cookies": {}, "headers": {}}
    
    async def get_seeded_cookies(self, target_url: str, persona: BrowserPersona, store_identification: dict = None) -> Dict[str, Any]:
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
        return await self.harvest_walmart_session(persona, store_identification)


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
        Build simplified headers that preserve store cookies while reducing bot detection.
        """
        self.logger.info(f"🏗️ [Simplified Headers] Building for persona: {self.persona.persona_id}")
        
        # Simplified essential headers (remove bot-like perfection)
        headers = {
            # Essential browser headers only
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.5",
            "accept-encoding": "gzip, deflate, br",
            "connection": "keep-alive",
            "referer": "https://www.walmart.com/",
            "upgrade-insecure-requests": "1",
            "user-agent": self.persona.user_agent,
            
            # Start with base location cookies
            "cookie": self._base_location_cookies
        }
        
        # CRITICAL FIX: Use cached seeded data to preserve store location cookies
        try:
            if hasattr(self, 'cached_seeded_data') and self.cached_seeded_data:
                seeded_data = self.cached_seeded_data
                if seeded_data.get('success'):
                    headers = self._merge_cookies_and_headers_simplified(headers, seeded_data)
                    self.logger.debug(f"🔄 [Simplified Headers] Preserved {len(seeded_data.get('cookies', {}))} store location cookies")
                else:
                    self.logger.info(f"🏗️ [Simplified Headers] Using foundation cookies only (no cached data)")
            else:
                # Fallback to live harvesting if no cached data (shouldn't happen in normal operation)
                self.logger.warning(f"⚠️ [Headers] No cached seeded data - falling back to live harvesting")
                seeded_data = await self.cookie_seeder.get_seeded_cookies(target_url, self.persona, self.store_identification)
                if seeded_data.get('success'):
                    headers = self._merge_cookies_and_headers_simplified(headers, seeded_data)
                    self.logger.info(f"✅ [Simplified Headers] Enhanced with {len(seeded_data.get('cookies', {}))} store cookies")
                else:
                    self.logger.info(f"🏗️ [Simplified Headers] Using foundation cookies only")
        except Exception as e:
            self.logger.warning(f"⚠️ [Simplified Headers] Cookie processing failed: {e}")
        
        self.logger.debug(f"🏗️ [Simplified Headers] Built {len(headers)} essential headers for {self.persona.persona_id}")
        return headers
    
    def _merge_cookies_and_headers_simplified(self, base_headers: Dict[str, str], seeded_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Merge foundation location cookies with harvested store cookies (simplified approach).
        Preserves all store location cookies while avoiding bot-like header patterns.
        """
        enhanced_headers = base_headers.copy()
        
        # Merge all cookies into a single cookie string (preserves store targeting)
        seeded_cookies = seeded_data.get('cookies', {})
        if seeded_cookies:
            # Parse existing base cookies
            existing_cookie_dict = {}
            if enhanced_headers.get('cookie'):
                for cookie_pair in enhanced_headers['cookie'].split('; '):
                    if '=' in cookie_pair:
                        name, value = cookie_pair.split('=', 1)
                        existing_cookie_dict[name.strip()] = value.strip()
            
            # Add/override with harvested cookies (including critical store cookies)
            existing_cookie_dict.update(seeded_cookies)
            
            # Build final cookie string
            cookie_parts = [f"{name}={value}" for name, value in existing_cookie_dict.items()]
            enhanced_headers['cookie'] = '; '.join(cookie_parts)
            
            self.logger.debug(f"🍪 [Simplified Merge] Preserved {len(existing_cookie_dict)} total cookies including store location data")
        
        # DO NOT add tracking headers - keep minimal to avoid bot detection
        # Remove any bot-like headers that might have been added
        bot_like_headers = [
            'x-session-harvested', 'x-harvest-time', 'x-persona-id', 'x-page-title',
            'sec-ch-ua', 'sec-ch-ua-mobile', 'sec-ch-ua-platform',
            'sec-fetch-dest', 'sec-fetch-mode', 'sec-fetch-site', 'sec-fetch-user',
            'cache-control', 'pragma', 'priority', 'downlink', 'dpr', 'rtt', 'ect'
        ]
        
        for header_name in bot_like_headers:
            enhanced_headers.pop(header_name, None)
            enhanced_headers.pop(header_name.lower(), None)
        
        return enhanced_headers
    
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
    Uses AIOHTTP for actual search requests with Playwright-harvested cookies.
    
    This hybrid approach provides:
    - Fast aiohttp performance for search requests
    - JavaScript-generated cookies from Playwright seeding
    - Consistent persona fingerprinting across all requests
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
        """Fetch single page with simplified headers to avoid bot detection."""
        retries = 0
        last_error = None
        
        # Add small human-like delay before each request
        if retries == 0:  # Only on first attempt, not retries
            pre_request_delay = random.uniform(0.5, 2.0)
            await asyncio.sleep(pre_request_delay)
        
        while retries <= self.max_retries:
            try:
                # Build simplified headers for this request (preserve store cookies, reduce bot detection)
                headers = await self.header_builder.build_advanced_headers(url)
                proxy = self.get_proxy() if self.get_proxy else None
                
                self.logger.debug(f"🌐 [Fetch] Attempt {retries + 1}/{self.max_retries + 1} for {url}")
                self.logger.debug(f"🎭 [Fetch] Using persona: {self.persona.persona_id}")

                self.logger.info("--- HEADERS AIOHTTP IS SENDING ---")
                for key, value in headers.items():
                    self.logger.info(f"  {key}: {value}")
                self.logger.info("-------------------------------------")

                # Use aiohttp for fast search requests with Playwright-harvested cookies
                async with session.get(
                    url,
                    headers=headers,  # Contains Playwright-harvested cookies merged with base headers
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
                    # Add human-like delay between retries (instead of just exponential backoff)
                    base_delay = 2 ** retries
                    human_delay = base_delay + random.uniform(1.0, 3.0)  # Add 1-3s randomness
                    await asyncio.sleep(human_delay)
        
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
        
        self.logger.info(f"🚀 [Hybrid Fetch] Starting aiohttp requests with persona: {self.persona.persona_id}")
        self.logger.info(f"🚀 [Hybrid Fetch] Using Playwright-harvested cookies + aiohttp requests")
        self.logger.info(f"🚀 [Hybrid Fetch] Target: {start_url}")
        
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
        
        # CRITICAL FIX: Harvest cookies ONCE during initialization, not per-request
        self.seeded_data = None  # Will be populated by harvest_initial_cookies()
        
        self.header_builder = AdvancedWalmartHeaderBuilder(
            store_identification, self.session_persona, self.cookie_seeder, logger
        )
        # Create a store-specific proxy getter for geographic targeting
        store_id = store_identification['store_id']
        store_proxy_getter = lambda: get_proxy(store_id=store_id)
        
        self.fetcher = AdvancedAiohttpFetcher(
            store_identification=store_identification,
            paginator=self.paginator,
            persona=self.session_persona,
            header_builder=self.header_builder,
            get_proxy=store_proxy_getter,
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
    
    async def harvest_initial_cookies(self):
        """
        Harvest cookies ONCE during initialization, then reuse for all requests.
        This is the proper implementation of the caching strategy.
        """
        self.logger.info("🌾 [Initial Harvest] Harvesting cookies ONCE for entire session...")
        
        try:
            # Harvest cookies using Playwright - this should only happen once
            self.seeded_data = await self.cookie_seeder.get_seeded_cookies(
                "https://www.walmart.com", 
                self.session_persona,
                self.store_identification
            )
            
            if self.seeded_data.get('success'):
                cookie_count = len(self.seeded_data.get('cookies', {}))
                self.logger.info(f"✅ [Initial Harvest] Successfully harvested {cookie_count} cookies for session")
                self.logger.info(f"🔄 [Initial Harvest] These cookies will be reused for ALL search requests")
                
                # Inject the cached seeded data into header builder to avoid re-harvesting
                self.header_builder.cached_seeded_data = self.seeded_data
                
            else:
                self.logger.error("❌ [Initial Harvest] Failed to harvest initial cookies")
                raise RuntimeError("Cookie seeding failed - cannot proceed with STORE_ID_MISMATCH errors")
                
        except Exception as e:
            self.logger.error(f"❌ [Initial Harvest] Critical error during cookie harvesting: {e}")
            self.logger.error("🔍 [Troubleshooting] Common causes:")
            self.logger.error("   • Browser/Chrome not properly installed")
            self.logger.error("   • Proxy configuration issues (check BRIGHTDATA_* environment variables)")
            self.logger.error("   • Network connectivity problems")
            self.logger.error("   • Bot detection blocking browser automation")
            self.logger.error("   • Resource cleanup conflicts (if using async context managers)")
            raise RuntimeError(f"Cookie seeding failed - detailed error: {e}")
            
        return self.seeded_data
    
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
        advanced_summary += f"  Cookie Seeding: Enabled (Playwright - JavaScript cookies from walmart.com)\n"
        advanced_summary += f"  Request Engine: aiohttp (fast requests with Playwright-harvested cookies)\n"
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
    logger.info(f"🎭 [Fingerprinting] Features: Session consistency, Modern headers, Hybrid cookie seeding, Device simulation")
    logger.info(f"🎭 [Hybrid Approach] Playwright for cookie seeding + aiohttp for search requests")
    
    # CRITICAL FIX: Harvest cookies ONCE before starting any searches
    try:
        logger.info("🌾 [Cookie Seeding] Harvesting cookies ONCE for entire session...")
        seeded_data = await bundle.harvest_initial_cookies()
        
        if seeded_data and seeded_data.get('success'):
            cookie_count = len(seeded_data.get('cookies', {}))
            logger.info(f"✅ [Cookie Seeding] Successfully harvested {cookie_count} cookies")
            logger.info(f"🔄 [Cookie Seeding] These cookies will be reused for ALL search requests")
            
            # Add human-like delay after cookie harvesting to avoid bot detection
            delay_seconds = random.uniform(3.0, 6.0)
            logger.info(f"⏱️ [Human Behavior] Waiting {delay_seconds:.1f}s before search requests (mimics human browsing pattern)")
            await asyncio.sleep(delay_seconds)
        else:
            logger.error("❌ [Cookie Seeding] Initial cookie harvest failed - cannot proceed")
            return
            
    except Exception as e:
        logger.error(f"❌ [Cookie Seeding] Critical error during initial cookie harvest: {e}")
        logger.error("Cannot proceed without cookies - STORE_ID_MISMATCH errors will occur")
        
        # Check if this was actually a successful harvest with cleanup failure
        if "cookies ONCE for entire session" in str(e) or "Target page, context or browser has been closed" in str(e):
            logger.warning("⚠️ [Analysis] Error occurred during cleanup phase, not during cookie harvesting")
            logger.warning("⚠️ [Analysis] Cookie harvesting may have succeeded but cleanup failed")
            logger.info("🔧 [Recommendation] Check logs for '✅ [Playwright Harvest] Successfully harvested' message")
            logger.info("🔧 [Recommendation] If cookies were harvested, this is a non-critical cleanup issue")
        
        return
    
    # Execute advanced fetch with sophisticated fingerprinting (using cached cookies)
    try:
        logger.info("🚀 [Execution] Starting advanced fingerprinting fetch with cached cookies...")
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