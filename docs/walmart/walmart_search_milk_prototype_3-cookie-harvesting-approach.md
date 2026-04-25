# Walmart Search Milk Prototype 3: Cookie Harvesting Approach

## Overview

The `walmart_search_milk_prototype_3.py` script demonstrates an advanced cookie harvesting approach for Walmart web scraping. This system creates authentic browser sessions by harvesting real cookies from www.walmart.com, then uses these seeded values to perform subsequent scrapes with higher success rates and reduced bot detection.

## Architecture Components

### 1. Browser Persona Selection

The script begins by choosing a Chrome/Windows browser persona to establish a consistent browser fingerprint:

```python
browser_persona_chooser = BrowserPersonaChooser()
browser_persona = browser_persona_chooser.get_persona(os_name='Windows', browser_name='Chrome')
```

This persona provides essential browser characteristics including:
- User-Agent string
- Security headers (`sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`)
- Viewport dimensions
- Browser-specific fingerprinting data

### 2. Residential Proxy Configuration

The system configures residential proxies to avoid IP-based blocking:

```python
proxies = get_proxies(proxy_type='residential')
```

These proxies are used throughout the cookie harvesting process to ensure geographic consistency and avoid detection.

### 3. Header Builder: WalmartCookieSeedingHeaderBuilder

The `WalmartCookieSeedingHeaderBuilder` class extends the base `WalmartHeaderBuilder` to create initial headers and cookies needed for cookie seeding.

#### Initialization

The header builder requires:
- `store_identification`: Store-specific data including store ID, location details
- `browser_persona`: Browser fingerprinting data

#### Initial Headers Generation

The builder creates a comprehensive set of initial headers:

```python
self.initial_headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': self.browser_persona.sec_ch_ua,
    'sec-ch-ua-mobile': self.browser_persona.sec_ch_ua_mobile,
    'sec-ch-ua-platform': self.browser_persona.sec_ch_ua_platform,
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': self.browser_persona.user_agent
}
```

#### Location Cookie Generation

The builder executes the `location_cookie()` method to generate store-specific cookies:

```python
generated_location_cookies = self.location_cookie()
```

This creates a semicolon-delimited string of cookies that are parsed into a dictionary for easier access.

#### Initial Cookies Dictionary

The builder creates initial cookies essential for Walmart's location-based services:

```python
self.initial_cookies = {
    'hasACID': 'true',
    'adblocked': 'false',
    'hasLocData': '1',
    'ACID': self.generated_location_cookie_dict['ACID'],
    'locGuestData': self.generated_location_cookie_dict['locGuestData'],
    'locDataV3': self.generated_location_cookie_dict['locDataV3'],
    'assortmentStoreId': self.store_id
}
```

These cookies establish the user's location context and authentication state.

### 4. Cookie Seeder: WalmartCookieSeeder

The `WalmartCookieSeeder` class performs the actual cookie harvesting from www.walmart.com.

#### Initialization Requirements

The cookie seeder requires:
- `retailer_store_id`: Target store ID for validation
- `initial_headers`: Headers from the header builder
- `initial_cookies`: Cookies from the header builder
- `proxies`: Proxy configuration
- `logger`: Logging instance

#### Cache Management

The seeder maintains an in-memory cache with TTL (Time-To-Live) of 3600 seconds (1 hour) to avoid unnecessary harvesting requests.

#### get_seeded_values() Method

This is the main entry point that:
1. Checks the cache for existing valid cookies
2. If cache miss/expired, calls `harvest_walmart_seeded_values()`
3. Returns the final seeded values

#### harvest_walmart_seeded_values() Method

This method implements a retry mechanism using the `tenacity` package:

```python
for attempt in Retrying(
    stop=stop_after_attempt(10),
    retry=retry_if_exception_type((StoreIdMismatchError, StoreIdNotFoundError, NonSuccessStatusError)),
    before_sleep=before_sleep_log(self.logger, logging.INFO),
    reraise=True
):
```

It attempts up to 10 retries for specific exceptions, allowing recovery from temporary failures.

#### _perform_harvest_attempt() Method

This method executes the actual harvesting logic:

##### Proxy Configuration
Converts proxy configuration to aiohttp format and sets up SSL and timeout parameters.

##### aiohttp Session Setup
```python
async with aiohttp.ClientSession(
    connector=connector,
    timeout=timeout,
    cookies=self.initial_cookies
) as session:
```

##### Request Execution
Makes a GET request to "https://www.walmart.com" using the initial headers and cookies.

##### Response Validation
1. **Status Code Check**: Throws `NonSuccessStatusError` if status ≠ 200
2. **Store ID Validation**: Searches response text for `"storeId":"(\d+)"` pattern
3. **Store ID Matching**: Throws `StoreIdMismatchError` if found ID doesn't match expected

##### Cookie Harvesting
If validation passes, calls `harvest_cookies(response_cookies)` to filter and collect specific cookies.

#### harvest_cookies() Method

Filters response cookies to collect only valuable anti-bot detection cookies:

```python
cookies_to_harvest = ['_pxvid', 'vtc', '_m', 'io_id', 'abqme',
                      'AID', '_pxhd', 'pxcts', 'wmlh', '_astc',
                      'userAppVersion', 'akavpau_p1', 'bstc', '__cf_bm', 
                      'com.wm.reflector', 'akavpau_p2', 'bm_mi', 'ak_bmsc', 
                      'if_id', 'bm_sv', '_px3', '_pxde']
```

These include:
- **Cloudflare cookies** (`__cf_bm`, `bm_*`): Bot management
- **Akamai cookies** (`aka*`): Content delivery network authentication
- **PerimeterX cookies** (`_px*`): Bot detection evasion
- **Walmart-specific cookies**: Session and tracking cookies

#### Return Values

On success, returns a comprehensive dictionary:

```python
return {
    "success": True,
    "cookies": harvested_cookies,
    "headers": seeded_headers,
    "harvested_at": time.time(),
    "cache_key": cache_key
}
```

### 5. Cookie Blending and Subsequent Scraping

#### blend_cookies() Function

Combines original location cookies with harvested cookies into a properly formatted cookie string:

```python
def blend_cookies(location_cookies, harvested_cookies):
    cookie_string = f"hasLocData={location_cookies['hasLocData']}; ACID={location_cookies['ACID']}; locGuestData={location_cookies['locGuestData']}; assortmentStoreId={location_cookies['assortmentStoreId']}; hasACID=true; locDataV3={location_cookies['locDataV3']}; "
    
    harvested_cookie_string = "; ".join(f"{key}={value}" for key, value in harvested_cookies.items())
    cookie_string += f"{harvested_cookie_string};"
    
    return cookie_string
```

This ensures location cookies take precedence while adding the harvested anti-bot cookies.

#### LocalBundle Implementation

The `LocalBundle` class extends `RetailerBundle` to override header generation:

```python
class LocalBundle(RetailerBundle):
    headers = {}
    
    def set_headers(self, headers: dict):
        self.headers = headers
    
    def build_headers(self):
        return self.headers
    
    def get_headers(self):
        return self.build_headers()
```

This allows injection of the seeded headers and cookies into the existing scraping infrastructure.

#### Final Scraping Execution

The main script:
1. Blends the cookies using `blend_cookies()`
2. Updates headers with the blended cookie string
3. Creates a `LocalBundle` with seeded headers
4. Executes `bundle.fetcher.fetch_all()` to perform the actual scraping

## Error Handling and Retry Logic

The system implements robust error handling:

- **StoreIdMismatchError**: When harvested store ID doesn't match expected
- **StoreIdNotFoundError**: When store ID pattern isn't found in response  
- **NonSuccessStatusError**: For HTTP status codes other than 200
- **Tenacity retry logic**: Up to 10 attempts with exponential backoff
- **Cache management**: Prevents excessive harvesting requests

## Benefits of This Approach

1. **Authentic Sessions**: Uses real cookies from actual Walmart sessions
2. **Bot Detection Evasion**: Harvests anti-bot cookies (Cloudflare, Akamai, PerimeterX)
3. **Geographic Consistency**: Maintains store location context
4. **Caching Efficiency**: Reduces harvesting overhead with TTL cache
5. **Error Recovery**: Robust retry logic handles temporary failures
6. **Modularity**: Separates concerns between harvesting and scraping

## Technical Dependencies

- **aiohttp**: Asynchronous HTTP client for harvesting
- **tenacity**: Retry logic implementation  
- **Browser personas**: Consistent browser fingerprinting
- **Residential proxies**: IP rotation and geographic targeting
- **Store identification**: Location-based cookie generation

This approach significantly improves scraping success rates by establishing authentic browser sessions before performing actual data collection operations.