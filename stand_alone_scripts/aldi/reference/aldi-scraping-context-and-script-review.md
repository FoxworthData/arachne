# Aldi.us Scraping — Context & Script Review

**Purpose**: This document transfers context from prior investigation sessions into the current working environment. It covers what we know about Aldi's web infrastructure, the approach we're taking, and specific issues found in the current feasibility-test scripts (`fetch_search.py` and `fetch_items.py`).

Read the entire document before making changes.

---

## Part 1: Background — What We're Doing and Why

The goal is to evaluate whether it's feasible to build a scraper for aldi.us that collects search results, product details, and store information. This is a reconnaissance project — we're not building production infrastructure yet, just determining whether the site is scrapable at all from Python with modest tooling.

### Site Architecture

Aldi completed a major digital redesign on March 30, 2026. The redesigned aldi.us website and mobile app are now powered by **Instacart's Storefront Pro** platform, with Instacart as the exclusive fulfillment partner. This is the single most important architectural fact — the e-commerce layer is an Instacart white-label, not a homegrown Aldi stack.

Three subdomains serve different functions:

- **`www.aldi.us` / `shop.aldi.us`** — The Instacart Storefront Pro e-commerce layer. Search, product detail, cart, checkout. This is our target.
- **`info.aldi.us`** — Legacy/content CMS. Weekly ads, static product catalog pages, store locator at `/stores/en-us/search`. Product images served from `dm.cms.aldi.cx`.
- **`corporate.aldi.us`** — Press, sustainability, recalls. Not relevant.

### Bot Detection Assessment

We examined the cookie landscape on `www.aldi.us` via Chrome DevTools. The findings suggest this is a relatively lightly-defended target:

**NOT present** (these detection systems are NOT in use):
- No `_px3`, `_pxvid`, `_pxhd` → Not PerimeterX / HUMAN
- No `_abck`, `ak_bmsc`, `bm_sz` → Not Akamai Bot Manager
- No `datadome` → Not DataDome
- No `cf_clearance`, `__cf_bm` → Not Cloudflare
- No `TS01*` → Not F5 / Shape

**Present**:
- `forterToken` — Forter fraud detection, focused on transaction-level fraud (payment, account takeover), not scraper blocking. Low concern for read-only data collection.
- `__Host-instacart_sid` — Instacart session ID. Critical cookie, secure-only, bound to origin via `__Host-` prefix.
- `_instacart_session_id` — Second Instacart session cookie, not HttpOnly.
- Various marketing/analytics cookies (GA, Stripe, Pinterest, TikTok, Snapchat, etc.) — all noise.

**Unknown layers that could still block us**:
- TLS fingerprinting (JA3/JA4) at the CDN layer — the origin IP `13.224.187.11` is AWS CloudFront
- Server-side rate limiting on the GraphQL endpoint
- Session token validation tied to JavaScript execution on first page load

The strategy chosen based on this assessment: use `curl-cffi` to impersonate Chrome's TLS fingerprint from Python, reuse captured session cookies from a real browser session, and see if the GraphQL calls reproduce successfully. If yes, `curl-cffi` plus a session-refresh strategy is sufficient. If no, escalate to Bright Data's Web Unlocker or a full headless browser approach.

### API Surface — GraphQL

All data fetching goes through a single GraphQL endpoint: `https://www.aldi.us/graphql`

Requests are **GET** (not POST), with the GraphQL operation passed as URL-encoded query string parameters (`operationName`, `variables`, `extensions`). Instacart uses **Apollo persisted queries** — the full query text is not sent, only a `sha256Hash` in the `extensions` parameter. These hashes are stable across sessions but change when Instacart deploys new code (trackable via the `build_sha` cookie).

### Critical GraphQL Operations

**`SearchResultsPlacements`** — The master search call. Returns the complete result manifest in a single response: all matching product IDs organized into sections (exact_results, related_results, bundle_results, etc.), plus refinement/filter options. No traditional pagination — the response includes ALL result IDs up front, and the frontend lazy-loads details via `Items` calls as the user scrolls.

Key variables:
- `query` — search term
- `shopId`, `postalCode`, `zoneId` — location context triplet
- `orderBy` — `"bestMatch"`, `"priceAsc"`, or `"priceDesc"`
- `first` — pagination parameter (observed set to `4` in browser)
- `contentManagementSearchParams.itemGridColumnCount` — layout parameter (observed `1` in browser)

**`Items`** — Product detail hydration. Takes a list of item IDs and returns full product data: name, brand, price, per-unit price, size, availability, nutrition, dietary badges, imagery URLs, variants.

Key variables:
- `ids` — array of item IDs in format `items_{retailer_location_id}-{product_id}`
- `shopId`, `zoneId`, `postalCode` — same location triplet

**`ViewLayoutSearchResults`** — Layout/config only, no data. Returns rendering directives (pagination variant, sort options, filter groups). Not useful for scraping.

### Location Context (Dallas, TX — test target)

The location triplet captured from browsing with Dallas zip code 75202:

- `shopId`: **`"339"`**
- `zoneId`: **`"90"`**
- `postalCode`: **`"75202"`**
- `retailer_location_id` (embedded in item IDs): `14655`
- Aldi's Instacart retailer ID: `12`

> **Confirmed:** The server echoes `shopId: "339"` back in the carousel sections of the `SearchResultsPlacements` response. The scripts already have the correct values.

---

## Part 2: Feasibility Scripts — Intended Scope and Shape

Two scripts were produced: `fetch_search.py` and `fetch_items.py`. The original approved scope was ONE script (`fetch_search.py`) to reproduce the `SearchResultsPlacements` GraphQL call from Python using `curl-cffi` with captured session cookies. No parsing, no abstraction, no retries — just: does the call reproduce?

The shape: hardcoded URL, hardcoded headers, hardcoded cookie string, single `curl_cffi.requests.get()` call with `impersonate="chrome"`, write response body and response headers to disk, print a short diagnostic (status code, content length, whether JSON parsed, whether `data.searchResultsPlacements` exists), and on failure dump the first 500 characters of the body for diagnosis.

The second script (`fetch_items.py`) expanded scope without approval — it tests the same pattern against the `Items` operation with a batch of 8 item IDs. The addition is useful, but represents scope drift that should be flagged for future reference.

---

## Part 3: Known Issues in the Current Scripts

### ~~Issue 1 (CRITICAL): `shopId` and `zoneId` values are wrong~~ — RESOLVED (not an issue)

The scripts use `shopId: "339"` and `zoneId: "90"`. These are the **correct values**. The server confirms this by echoing `"shopId":"339"` back in the carousel sections of the actual response.

The context document previously claimed the correct values were `"22339"` and `"290"` and attributed the difference to a URL-encoding transcription error. This was itself an error — the "correction" was wrong. The scripts do not need to be changed.

### Issue 2 (MODERATE): `itemGridColumnCount` mismatch

In `fetch_search.py`, the variable `contentManagementSearchParams.itemGridColumnCount` is set to `8`. In the captured browser request it was `1`. Not necessarily broken, but a deviation from the known-working browser request that could affect the response structure. Align it to `1` to match the browser capture, so that response comparisons against the reference file `aldi-SearchResultsPlacements-response-tab.txt` remain valid.

### Issue 3 (MINOR): `content-type: application/json` on GET requests

Both scripts send `content-type: application/json` in the request headers. Real browsers typically don't send `content-type` on GET requests (which have no body). Servers usually ignore it, but it's a deviation from real browser behavior that could theoretically be used as a fingerprinting signal. Safe to leave for now, but worth removing if we see unexplained failures.

### Issue 4 (SCOPE DRIFT): Second script produced without approval

The original approved scope was a single script for `SearchResultsPlacements`. A second script (`fetch_items.py`) was added. This isn't harmful — hydration testing is useful — but any future scope expansions should be proposed and approved before implementation, especially for a reconnaissance project where narrow scope is deliberate.

---

## Part 4: Recommended Next Steps (in order)

1. ~~**Fix Issue 1**~~ — Not needed. Scripts already have correct values (`"339"`/`"90"`), confirmed by server response.
2. **Fix Issue 2** — Align `itemGridColumnCount` to `1` in `fetch_search.py` to match the browser capture.
3. **Verify session cookies are current** — The `__Host-instacart_sid` cookie is a server-issued session token and may have expired. If the first run returns 401/403, re-capture fresh cookies from a live browser session before diagnosing other causes.
4. **Run `fetch_search.py` first**, alone. Capture the output. Success criteria:
   - HTTP 200
   - Response parses as JSON
   - `data.searchResultsPlacements.placements` exists
   - Response body resembles the reference file `aldi-SearchResultsPlacements-response-tab.txt` in structure (not necessarily in item IDs — those will differ with fresh store context)
5. **If step 4 succeeds**, run `fetch_items.py`. Success criteria similar but checking for `data.items` as a non-empty list.
6. **If either fails**, examine the first 500 characters of the body dump. The failure mode tells us which layer is blocking:
   - HTML with "Press and Hold" or CAPTCHA language → JavaScript challenge / bot detection
   - HTML with Akamai or similar vendor branding → WAF block
   - JSON with GraphQL errors → session or authorization issue (cookies expired or invalid)
   - 401/403 with no body → IP reputation or TLS fingerprint rejection
   - Connection errors → TLS handshake failure

### Diagnostic Interpretation

If both calls succeed with Chrome impersonation and captured cookies, the feasibility picture is strong: we can proceed to parameterize the scripts (configurable query, location triplet), add session refresh, and plan the harvester integration. If they fail cleanly with informative errors, we know exactly which layer to address. The point of this test is to collapse uncertainty — run the scripts minimally and let the results drive the next decision.

---

## Reference Files

- `context/aldi-scraping-recon-summary.md` — Full prior-session summary
- `context/aldi-response-tab.txt` — Reference response from the `Items` call (single product: Friendly Farms 1% Milk)
- `context/aldi-SearchResultsPlacements-response-tab.txt` — Reference response from the `SearchResultsPlacements` call (~13,000 lines, "milk" search at Dallas 75202 store)
- `context/fresh-search-curl.txt` — Latest cURL capture for the search call (authoritative source for current session cookies and variable values)
- `context/fresh-items-curl.txt` — Latest cURL capture for the items call
