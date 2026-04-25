# Porting the Walmart cookie-seeding approach into the `main.py` path

## Why this document exists

`src/main.py`'s Walmart `search` flow can fetch page 1 of a search, but every
subsequent page gets bot-detected. The working reference is
`src/walmart_search_milk_prototype_3.py`, which successfully scrapes *all* pages
for the same `cookies` query. This doc enumerates exactly what is different and
what to change in the `main.py` path to match.

Read order:
1. `src/main.py` (search branch)
2. `src/utils/retailer_factory.py` — `RetailerBundle`
3. `src/utils/header_builders.py` — `WalmartHeaderBuilder`
4. `src/utils/fetchers.py` — `AiohttpFetcher`
5. `src/walmart_search_milk_prototype_3.py` (the working path)
6. `src/utils/walmart_cookie_seeder.py`
7. `src/utils/browser_personas.py`

---

## Root cause (why page 1 works and page 2+ fails)

Walmart's PerimeterX/Akamai stack tolerates an unknown first-touch visitor on
page 1 — it issues challenge/session cookies (`_px3`, `_pxvid`, `ak_bmsc`,
`bm_sv`, `bm_mi`, `__cf_bm`, `_pxde`, `akavpau_p1`, `akavpau_p2`, etc.) in the
`Set-Cookie` response. Page 2+ is evaluated against the presence and
consistency of those cookies plus a stable browser identity.

The `main.py` path fails page 2+ because, on *every* request, it:

1. Rebuilds the `Cookie:` header from scratch, so challenge cookies set by
   Walmart on page 1 are **discarded** before page 2 is sent.
2. Generates a **new `ACID` UUID** (so the session identifier flips).
3. Generates a **new random User-Agent** via `fake_useragent` (so the browser
   identity flips, and may rotate between Chrome and Safari mid-session).
4. Sends **no Client Hints** (`sec-ch-ua*`) and **no Fetch Metadata**
   (`sec-fetch-*`) headers — the modern Chrome set Walmart expects.
5. Never performs a homepage pre-flight, so there is no validated session
   state before the search traffic starts.

prototype_3 fixes all five: one persona, one ACID, one cookie jar, full Chrome
header set, and a validated homepage GET before scraping.

---

## The changes, in order

The sections below are ordered so each step is self-contained. Do them in
order; after step 4 you should already be able to scrape past page 1.

### 1. Use `WalmartCookieSeedingHeaderBuilder` + `BrowserPersona` instead of `WalmartHeaderBuilder`

**Files:** `src/utils/header_builders.py`, `src/utils/retailer_factory.py`, `src/main.py`

**Current `main.py` path** (`header_builders.py:144`):

```python
def build_headers(self):
    ac = "text/html,..."
    headers = {
        "Accept": ac,
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Cookie": self.location_cookie(),       # new UUID, new timestamps every call
        "Referer": "https://www.google.com",
        "Connection": "Keep-Alive",
        "User-Agent": self.get_random_user_agent(),  # random Safari-or-Chrome, rotates
    }
    return headers
```

Problems: no Client Hints, no Fetch Metadata, no `priority`, random UA per
call, and location cookie rebuilt per call.

**Working path** (`walmart_search_milk_prototype_3.py:47-85` — the inline
`WalmartCookieSeedingHeaderBuilder` subclass):

- Takes a `BrowserPersona` (from `src/utils/browser_personas.py`) so the UA,
  `sec-ch-ua`, `sec-ch-ua-mobile`, and `sec-ch-ua-platform` are all internally
  consistent.
- Builds `initial_headers` with the full modern Chrome set:
  `accept`, `accept-language`, `cache-control`, `pragma`, `priority`,
  `sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`, `sec-fetch-dest`,
  `sec-fetch-mode`, `sec-fetch-site`, `sec-fetch-user`,
  `upgrade-insecure-requests`, `user-agent`.
- Calls `self.location_cookie()` *once* and splits the result into
  `initial_cookies` (a dict, not a `Cookie:` string) for the seeder to use.

**Action:**

1. Move `WalmartCookieSeedingHeaderBuilder` out of the prototype file and into
   `src/utils/header_builders.py` (promote it to a first-class builder).
2. Pick a persona at the start of the `search` branch in `main.py`:

   ```python
   from src.utils.browser_personas import BrowserPersonaChooser
   persona = BrowserPersonaChooser().get_persona(os_name='Windows', browser_name='Chrome')
   ```

3. Construct `WalmartCookieSeedingHeaderBuilder(store_identification, persona)`
   once, before building the bundle. Do **not** let `RetailerBundle.get_headers`
   build a new one per request.

Note: on the work machine, verify `src/utils/browser_personas.py` exists and
matches this machine's copy. If not, copy the `BrowserPersona` dataclass and
`BrowserPersonaChooser` class over from `walmart_home_page.py:45-150` as a
starting point.

---

### 2. Add the `WalmartCookieSeeder` pre-flight

**File:** `src/utils/walmart_cookie_seeder.py` (already exists on this machine;
copy to the work machine if missing).

The seeder lives at `src/utils/walmart_cookie_seeder.py`. Key contract:

- Constructor takes `retailer_store_id`, `initial_headers`, `initial_cookies`,
  `proxies`, `logger`.
- `await seeder.get_seeded_cookies(browser_persona)` returns:

  ```python
  {
      "success": True,
      "cookies": {...},    # the harvested anti-bot cookies only
      "headers": {...},    # initial_headers + x-session-harvested / x-harvest-time / x-persona-id
      "harvested_at": <ts>,
      "cache_key": "...",
  }
  ```

- Under the hood it opens an `aiohttp.ClientSession(cookies=initial_cookies)`,
  GETs `https://www.walmart.com` through the proxy, and uses `tenacity` to
  retry up to 10 times on `NonSuccessStatusError`, `StoreIdNotFoundError`, or
  `StoreIdMismatchError` until the response body contains
  `"storeId":"<retailer_store_id>"`. Only then does it return the cookies and
  headers.
- `harvest_cookies` (line 164) filters the session jar down to the anti-bot
  set: `_pxvid, vtc, _m, io_id, abqme, AID, _pxhd, pxcts, wmlh, _astc,
  userAppVersion, akavpau_p1, bstc, __cf_bm, com.wm.reflector, akavpau_p2,
  bm_mi, ak_bmsc, if_id, bm_sv, _px3, _pxde`.

**Action:** In the `search` branch of `main.py`, after building the header
builder and before creating the bundle:

```python
from src.utils.walmart_cookie_seeder import WalmartCookieSeeder
from src.utils.proxy_builder_simple import get_proxies

proxies = get_proxies(proxy_type='residential')

seeder = WalmartCookieSeeder(
    retailer_store_id=store_id,
    initial_headers=header_builder.initial_headers,
    initial_cookies=header_builder.initial_cookies,
    proxies=proxies,
    logger=logger,
)

harvested = await seeder.get_seeded_cookies(browser_persona=persona)
if not harvested['success']:
    raise RuntimeError("Cookie seeding failed; aborting scrape")
```

If `proxy_builder_simple.get_proxies` does not exist on the work machine, use
the existing `src.utils.retailer_factory.get_proxies()` instead — the env-var
set it reads is the same (`BRIGHTDATA_RESIDENTIAL_PROXY_*`).

---

### 3. Blend location cookies with harvested cookies into a single `Cookie:` string

**File:** new helper, or copy from `walmart_search_milk_prototype_3.py:26`.

The seeder returns only the anti-bot cookies. They must be concatenated with
the synthesized location cookies before being set on the request header.
Copy the helper verbatim:

```python
def blend_cookies(location_cookies: dict, harvested_cookies: dict) -> str:
    cookie_string = (
        f"hasLocData={location_cookies['hasLocData']}; "
        f"ACID={location_cookies['ACID']}; "
        f"locGuestData={location_cookies['locGuestData']}; "
        f"assortmentStoreId={location_cookies['assortmentStoreId']}; "
        f"hasACID=true; "
        f"locDataV3={location_cookies['locDataV3']}; "
    )
    harvested_cookie_string = "; ".join(
        f"{key}={value}" for key, value in harvested_cookies.items()
    )
    cookie_string += f"{harvested_cookie_string};"
    return cookie_string
```

Then set it as the `cookie` header on the seeded headers:

```python
blended = blend_cookies(header_builder.initial_cookies, harvested['cookies'])
seeded_headers = harvested['headers']
seeded_headers['cookie'] = blended
```

Note the **lowercase** `cookie` — prototype_3 uses lowercase because the rest
of the header set is lowercase (modern Chrome style). Keep the whole dict
lowercase for consistency; aiohttp normalizes on the way out.

---

### 4. Freeze the header dict for the lifetime of the scrape session

**Files:** `src/utils/retailer_factory.py`, `src/main.py`

This is the single most load-bearing change. In `RetailerBundle.__init__`,
`self.get_headers` is passed to `AiohttpFetcher` as a callable, and the
current implementation (`retailer_factory.py:77`) builds a new
`WalmartHeaderBuilder` and calls `build_headers()` every time — which
regenerates the ACID UUID, rotates the UA, and throws away any prior cookies.

The fix is to make `get_headers` return a **frozen** dict that was computed
once, before `fetch_all` starts.

Two equally-good options:

**Option A — minimal change: `LocalBundle` subclass in `main.py`.**
Copy the pattern from `walmart_search_milk_prototype_3.py:36-45`:

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

Then:

```python
bundle = LocalBundle(
    retailer=retailer,
    store_identification=store_identification,
    fetch_type=fetch_type,
    fetch_query=query,
    start_url=first_page_search_url,
    project_config=project_config,
    logger=logger,
)
bundle.set_headers(seeded_headers)
```

This leaves `RetailerBundle` untouched, which is safer on the work machine if
other code paths depend on its per-request behavior.

**Option B — refactor `RetailerBundle` itself.** Add an optional
`frozen_headers` constructor arg; if provided, `get_headers` returns it. More
invasive but cleaner long-term.

Start with Option A for tomorrow's fix.

---

### 5. Also update `build_retailer_bundle` if you use option B, or skip it for option A

`build_retailer_bundle` in `retailer_factory.py:133` is the factory used by
`main.py`. For Option A (subclass) you bypass the factory and instantiate
`LocalBundle` directly, the same way prototype_3 does. No change needed to
the factory.

---

## Putting it together — the `search` branch of `main.py` after the change

Pseudocode of the `search` branch once all five steps are done:

```python
if fetch_type == 'search':
    logger.info(f"Retailer: {retailer} Store: {store_id} Fetch Type: {fetch_type} Query: {query}")

    search = load_search_by_query(query=query)
    query = search.get('query')
    first_page_search_url = search.get('search_url')

    # 1. persona
    persona = BrowserPersonaChooser().get_persona(os_name='Windows', browser_name='Chrome')

    # 2. proxy + header builder
    proxies = get_proxies(proxy_type='residential')
    header_builder = WalmartCookieSeedingHeaderBuilder(
        store_identification=store_identification,
        browser_persona=persona,
    )

    # 3. seed
    seeder = WalmartCookieSeeder(
        retailer_store_id=store_id,
        initial_headers=header_builder.initial_headers,
        initial_cookies=header_builder.initial_cookies,
        proxies=proxies,
        logger=logger,
    )
    harvested = await seeder.get_seeded_cookies(browser_persona=persona)
    if not harvested['success']:
        raise RuntimeError("Cookie seeding failed")

    # 4. blend
    blended = blend_cookies(header_builder.initial_cookies, harvested['cookies'])
    seeded_headers = harvested['headers']
    seeded_headers['cookie'] = blended

    # 5. bundle with frozen headers
    bundle = LocalBundle(
        retailer=retailer,
        store_identification=store_identification,
        fetch_type=fetch_type,
        fetch_query=query,
        start_url=first_page_search_url,
        project_config=project_config,
        logger=logger,
    )
    bundle.set_headers(seeded_headers)

    results = await bundle.fetcher.fetch_all(first_page_search_url, bundle.handle_result)
```

The other three branches (`product`, `store-directory`, `store-directory-by-state`)
can stay as-is for now, but note they have the same weakness — if any of them
start getting bot-detected past page 1, apply the same pattern.

---

## Verification

After the change, the first thing to check in the logs is:

1. `WalmartCookieSeeder` logs `Found store ID '1198'` matching the requested
   store. If it doesn't, the seeder retries up to 10 times; if it exhausts
   retries, your proxy exit node is not geo-consistent with store 1198 —
   switch proxy region before blaming the code.
2. The `Cookie:` header on page 2+ contains `_px3`, `ak_bmsc`, `bm_sv`
   (harvested) **and** `ACID`, `locDataV3`, `assortmentStoreId` (location).
   Log `seeded_headers['cookie']` once before `fetch_all` to confirm.
3. `walmart_response_analyzer` (`src/utils/response_analyzers.py:4`) passes
   its "not blocked / UA accepted / store ID matches" checks on every page,
   not just page 1.

---

## Prerequisites to verify on the work machine

Before starting, confirm these files exist and have the same shape as on this
machine. If any are missing, copy them over first:

- `src/utils/walmart_cookie_seeder.py` — the seeder class
- `src/utils/browser_personas.py` — `BrowserPersona` + `BrowserPersonaChooser`
- `src/utils/proxy_builder_simple.py` — `get_proxies(proxy_type='residential')`
  (or confirm `retailer_factory.get_proxies` works as a substitute)

Also confirm `tenacity` is in `requirements.txt` — the seeder imports
`Retrying`, `stop_after_attempt`, `retry_if_exception_type`,
`before_sleep_log`, `RetryError` from it.

---

## Summary of what changes and why

| Change | Why it matters |
|---|---|
| Swap `WalmartHeaderBuilder` → `WalmartCookieSeedingHeaderBuilder` | Adds modern Chrome Client Hints + Fetch Metadata that Walmart expects, and pins UA to a consistent persona |
| Pick one `BrowserPersona` and reuse it | Stops UA from rotating mid-session; keeps UA / sec-ch-ua / platform internally consistent |
| Run `WalmartCookieSeeder` against `walmart.com` before scraping | Validates the proxy-store geo match, and populates the cookie jar with the PX/Akamai session tokens Walmart looks for on page 2+ |
| `blend_cookies(...)` into one `Cookie:` string | The seeder returns anti-bot cookies only; Walmart also needs the location cookies on every request |
| `LocalBundle.set_headers(...)` to freeze headers | Stops per-request regeneration of `ACID`/UA/cookies, which was the actual thing making page 2+ look like a brand-new visitor |
