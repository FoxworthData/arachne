# Aldi Item Data Gathering — Reconnaissance Findings

**Date**: April 24, 2026  
**Status**: Active reconnaissance. Store registry complete with mismatch analysis. No production scraper has been built yet.  
**Goal of this document**: Share findings with an LLM for strategy brainstorming on building out an Aldi search scraper.

---

## 1. Site Architecture

Aldi completed a major digital redesign on **March 30, 2026**. The redesigned `www.aldi.us` (also accessible as `shop.aldi.us`) is a white-label deployment of **Instacart's Storefront Pro** platform. Instacart is the exclusive fulfillment partner. This is the single most important architectural fact — there is no homegrown Aldi e-commerce backend. Everything flows through Instacart's infrastructure.

Three subdomains serve different functions:

| Subdomain | Role |
|---|---|
| `www.aldi.us` / `shop.aldi.us` | Instacart Storefront Pro — search, PDPs, cart, checkout. **Our target.** |
| `info.aldi.us` | Legacy/content CMS — weekly ads, static product catalog, store locator. |
| `corporate.aldi.us` | Press, sustainability, recalls. Not relevant. |

---

## 2. Bot Detection Assessment

We examined the full cookie jar via Chrome DevTools after a real browser session. Findings:

**NOT present** (these systems are not in use):
- No PerimeterX / HUMAN (`_px3`, `_pxvid`)
- No Akamai Bot Manager (`_abck`, `ak_bmsc`, `bm_sz`)
- No DataDome
- No Cloudflare (`cf_clearance`, `__cf_bm`)
- No F5 / Shape (`TS01*`)

**Present**:
- `__Host-instacart_sid` — Instacart session ID. Critical. Server-issued via `Set-Cookie` on the first GET of the homepage. No JavaScript execution required to obtain it.
- `_instacart_session_id` — A second Rails-style encrypted session cookie, set by JavaScript. We have confirmed this is **not required** for GraphQL calls.
- `forterToken` — Forter fraud detection, focused on transaction-level events (payment, account takeover). Not a scraper blocker for read-only data collection.
- Marketing/analytics cookies (GA, Stripe, Pinterest, TikTok, Snapchat) — noise.

**Unknown/unverified risks**:
- TLS fingerprinting (JA3/JA4) at the CDN layer (origin IP `13.224.187.11` is AWS CloudFront)
- Server-side rate limiting on the GraphQL endpoint
- Potential IP reputation scoring at Instacart's infrastructure layer

**Current mitigation**: `curl_cffi` with `impersonate="chrome"` to match Chrome's TLS fingerprint. This has successfully produced HTTP 200 responses on all operations tested so far.

---

## 3. Session Seeding

We confirmed that obtaining a valid session requires only a single unauthenticated GET to the homepage:

```
GET https://www.aldi.us/
```

The server responds with `Set-Cookie: __Host-instacart_sid=v2.<token>`. No JavaScript execution, no CAPTCHA, no challenge flow. This makes session refresh trivially automatable.

We have a working library module (`stand_alone_scripts/aldi/aldi_session_seeder.py`) that seeds a fresh session and returns a `curl_cffi.Session` object:

```python
from aldi_session_seeder import seed_aldi_session
session = seed_aldi_session()
```

---

## 4. The GraphQL API

All data is served through a single GraphQL endpoint:

```
https://www.aldi.us/graphql
```

Requests are **GET** (not POST), with the operation encoded as URL query string parameters:

```
?operationName=<n>&variables=<url-encoded-json>&extensions=<url-encoded-json>
```

Instacart uses **Apollo persisted queries**: the full GraphQL query text is never sent. Only a `sha256Hash` in the `extensions` parameter identifies the query shape. These hashes are stable until Instacart deploys new frontend code (observable via the `build_sha` cookie changing).

### 4.1 Location Context

The only real location identifier is `shopId`. Empirical testing (April 23, 2026) revealed:

| Parameter | `Items` | `SearchResultsPlacements` |
|---|---|---|
| `shopId` | ✅ Required, **the only real key** | ✅ Required |
| `postalCode` | ✅ Syntactically required; **semantically ignored** | ✅ Required |
| `zoneId` | ✅ Syntactically required; **semantically ignored** | ✅ Optional (omit or null — identical results) |

**`shopId` is the sole location key**: Passing Beverly Hills (`90210`) or Manhattan (`10001`) as `postalCode` alongside Dallas `shopId: "339"` returns identical Dallas inventory at Dallas prices. `postalCode` does not affect routing when `shopId` is set.

**`zoneId` is a dummy validator for `Items`**: Any non-null string value is accepted (`"1"`, `"89"`, `"999"` — all work). The value is validated for presence but never used. It can safely be hard-coded to `"1"` or any other constant.

Consequence for store discovery: once you have a `shopId`, you can ignore `zoneId` entirely and use any postal code. You do **not** need to discover the matching `zoneId` or `postalCode` for a store.

Dallas 75202 test store reference values:

| Parameter | Value |
|---|---|
| `shopId` | `"339"` |
| `zoneId` | `"90"` (arbitrary; any non-null string works) |
| `postalCode` | `"75202"` (arbitrary; any postal code works) |
| `retailerLocationId` | `14655` (embedded in item IDs) |
| Aldi's Instacart `retailerId` | `12` |

The `shopId` is the key store identifier for Instacart's backend. A single **physical Aldi store** has three distinct shop IDs depending on the fulfillment mode:
- Delivery: `339`
- Pickup: `15030`
- In-store: `514928`

The search and items scripts use the delivery shop ID (`339`).

#### shopId/zoneId Disambiguation — Empirically Verified (April 23, 2026)

An earlier session proposed that `339/90` might be a URL-decoding error and the correct values were `22339/290`. **This was tested and resolved.** Both triplets are valid Instacart shop IDs that return HTTP 200 with real product data — but they are **different physical stores**:

| Triplet | Item IDs returned | `retailerLocationId` in item IDs | Interpretation |
|---|---|---|---|
| `shopId: "339"`, `zoneId: "90"` | 151 | `14655` | ✅ Dallas 75202 delivery store — **correct** |
| `shopId: "22339"`, `zoneId: "290"` | 52 | `73470` | ❌ A different physical store at an unknown location |

The `339/90` triplet is confirmed correct for the Dallas 75202 delivery context. The `22339/290` values are not a transcription error — they are a real but different store. The server echoes back the input `shopId` in its response, making the distinction unambiguous.

### 4.2 Confirmed Operations

#### `SearchResultsPlacements`
The master search call. Returns the complete result manifest in a single response.

- **Hash**: `6e6b53b10516829d9b7b9fae0cbc9b65bcbbc8792d77836f65b9db6a606057a7`
- **Method**: GET
- **Key variables**: `shopId`, `postalCode`, `query`, `first`, `itemGridColumnCount`
- **`zoneId` is optional** — omitting it or passing `null` returns identical results. Confirmed empirically: 151 item IDs returned with or without `zoneId`. Only `shopId` + `postalCode` are required for location resolution.
- **What it returns**: 81 placements (for "milk" at Dallas 75202). Placements include carousel slots, ad slots, and product grid sections. Product grid sections contain `itemIds` arrays — our primary interest.
- **Item ID format**: `items_{retailerLocationId}-{productId}` (e.g. `items_14655-16902710`)
- **A typical search**: 151 unique item IDs returned across all placements for "milk"
- **Inline hydration**: Only 1 item gets full inline data (controlled by `first` parameter). All other items are IDs only — full data requires a follow-up `Items` call.
- **`first` parameter**: Controls only how many items are hydrated inline. All item IDs are returned regardless of its value. Safe to leave at `4` (the browser default).
- **Pagination**: None in the traditional sense. All matching item IDs are returned in one shot.

#### `Items`
Product detail hydration. Takes a batch of item IDs and returns full product records.

- **Hash**: `5116339819ff07f207fd38f949a8a7f58e52cc62223b535405b087e3076ebf2f`
- **Method**: GET
- **Key variables**: `ids` (array of item IDs), `shopId`, `postalCode`, `zoneId`
- **`zoneId` is syntactically required but semantically ignored** — omitting it or passing `null` returns `data: null` (GraphQL schema validation error). However, **any non-null string value works** (`"1"`, `"89"`, `"999"`). Hard-code it to `"1"` for simplicity. `postalCode` is similarly ignored — any value is accepted.
- **Batch size tested**: 8 items per call (browser behavior; maximum batch size not yet determined)
- **What it returns**: Per item:
  - `id`, `name`, `brandName`, `size`
  - `price.viewSection.priceString` (e.g. `"$4.85"`)
  - `price.viewSection.priceValueString` (e.g. `"4.85"`)
  - `nutritionalAttributes[]` — Protein, Fat, Sugar, Calories (from label)
  - `dietary.mlShoppingAttributes[]` — ML-inferred dietary tags (e.g. `["organic"]`)
  - `dietary.mlDietaryAttributes[]` — Dietary certifications
  - `availability` — in-stock status
  - `variantGroup` / `variantDimensionValues` — size/variant info
  - `evergreenUrl` — stable PDP URL slug
  - `productCanonicalUrl` — full canonical URL
  - `tags[]` — e.g. `["storeBrand"]`
  - `inStoreItemLocation` — aisle/location string (when available)
  - `productRating` — aggregate rating (when available)

#### `SearchFacets`
Returns search filter facets (department filters, brand filters, etc.).

- **Hash**: `239be7211ba1456b45268b8207a8f3ca87bc28639fd87165b940053062f8f6ae`
- **Variables**: `shopId`, `postalCode`, `query` (no `zoneId`)
- **Result**: `searchFacets: []` — **Facets are disabled in Aldi's Instacart configuration.** This operation returns no useful data.

### 4.3 Store Discovery — `/idp/v1/shops` REST Endpoint

A separate REST endpoint (not GraphQL) returns all Instacart shop IDs for stores serving a given postal code:

```
GET https://www.aldi.us/idp/v1/shops?postal_code={zip}
```

- **Auth**: None required. A seeded `__Host-instacart_sid` cookie is included for safety but appears optional.
- **Response**: A `shops[]` array. Each element represents one store × fulfillment mode combination, with fields:
  - `id` — the Instacart `shopId` (what all GraphQL operations consume)
  - `fulfillment_option` — `"delivery"`, `"pickup"`, or `"instore"`
  - `address` — `street_address`, `city`, `state`, `postal_code`
  - `location_code` — canonical physical-store identifier (format `475-NNN`). All three fulfillment-mode entries for one physical store share the same `location_code`.
  - `location_name` — human-readable name, e.g. `"ALDI - DEN 42 - Dallas"`

**Catchment quirk**: Querying a single zip returns ~30 shops — all stores whose delivery zone includes that zip. To get all three fulfillment-mode shop IDs for a given store, you must query with that store's **own** zip. Querying a zip that is just within a store's catchment area will only surface it as a pickup-only entry.

This endpoint is the foundation for the store registry (see Section 8).

---

## 5. The Category Problem

This is the most significant gap in the current data model.

**The problem**: Neither `Items` nor `SearchResultsPlacements` returns any category or department classification for individual items. The fields `category`, `categories`, `department`, and `tags` (beyond `"storeBrand"`) in the `Items` response are all `null` or irrelevant. Aldi has not exposed item-level taxonomy in their Instacart configuration.

**What does exist**: The left-rail department navigation on the Aldi storefront (visible when browsing by department) contains a taxonomy of 20 department slugs. This navigation is rendered server-side and embedded in every page's Apollo SSR cache — it is not a runtime GraphQL call.

**Where it lives**: The `<script id="node-apollo-state" type="application/json">` tag in the page HTML contains a URL-encoded JSON blob. Within that blob, the key `"DesktopSidebarNavigations"` holds the full navigation tree, keyed by `{"previewToken":null,"shopId":"339"}`.

**Full department taxonomy** (from `aldi_departments.json`, retrieved live April 23, 2026):

| Slug | Display Name | Type |
|---|---|---|
| `explore-all-products` | Explore All Products | department |
| `this-weeks-aldi-finds` | This Week's ALDI Finds | department |
| `upcoming-aldi-finds` | Upcoming ALDI Finds | department |
| `fresh-produce` | Fresh Produce | department |
| `meat-seafood` | Meat & Seafood | department |
| `snacks-candy` | Snacks & Candy | department |
| `frozen-foods` | Frozen Foods | department |
| `dairy-and-eggs` | Dairy & Eggs | department |
| `bakery-bread` | Bakery & Bread | department |
| `beverages` | Beverages | department |
| `alcohol` | Alcohol | department |
| `pantry-essentials` | Pantry Essentials | department |
| `deli` | Deli | department |
| `household-essentials` | Household Essentials | department |
| `breakfast-cereals` | Breakfast & Cereals | department |
| `pet-supplies` | Pet Supplies | department |
| `personal-care` | Personal Care | department |
| `baby-items` | Baby Items | department |
| `recipes` | Recipes | department |
| `aldi-brands` | ALDI Brands | department |
| `buyItAgain` | Buy It Again | feature (not a product category) |

**The only known path to item→category mapping**: Crawl each department slug via the `BrowsePlacementsSource` GraphQL operation to enumerate all item IDs in each department. This would allow us to build a reverse lookup: item ID → department slug(s). The persisted query hash for `BrowsePlacementsSource` has not yet been captured.

---

## 6. SSR Cache (Apollo State)

Every Aldi storefront page includes a large Apollo SSR cache embedded as a URL-encoded JSON blob in `<script id="node-apollo-state" type="application/json">`. This blob contains pre-fetched GraphQL data for the initial page render, including:

- `GetRetailerBySlug` — retailer metadata (store name, branding, fulfillment options)
- `DesktopSidebarNavigations` — the department taxonomy (as described above)
- Layout and config operations (not data-bearing)

This SSR cache is accessible with a plain unauthenticated GET (though a session cookie speeds things up) and doesn't require capturing any persisted query hash. It is a secondary data source worth scanning on each page fetch.

---

## 7. Working Scripts

All scripts are in `stand_alone_scripts/aldi/`. They share a common session seeding library. Data outputs are written to `stand_alone_scripts/aldi/data/`, except the store registry which lives in the top-level `data/` directory.

| Script | What it does |
|---|---|
| `aldi_session_seeder.py` | Seeds a fresh Instacart session via a single unauthenticated GET. Used as a library by all other scripts. |
| `aldi_recon_fetch_search.py` | Calls `SearchResultsPlacements` for a hardcoded query ("milk") at the Dallas test store. Writes to `data/aldi_search_response.json`. |
| `aldi_recon_fetch_items.py` | Calls `Items` for a hardcoded batch of 8 item IDs. Writes to `data/aldi_items_response.json`. |
| `aldi_recon_fetch_departments.py` | Fetches the Aldi storefront page, parses the Apollo SSR cache, and extracts the department taxonomy. Writes to `data/aldi_departments.json`. |
| `aldi_build_store_registry.py` | Calls `/idp/v1/shops` for every unique zip in the Uberall store list, joins results by normalized address, and produces the store registry. Writes to `data/aldi_store_registry.jsonl` (top-level) and `data/aldi_store_registry_mismatches.jsonl`. Supports resume via `data/aldi_zip_cache.json`. |
| `aldi_probe_zoneid.py` | One-off experiment confirming that `zoneId` and `postalCode` are semantically ignored by both `Items` and `SearchResultsPlacements`. Kept for reference. |

The recon scripts (`aldi_recon_fetch_*.py`) are hardcoded to the Dallas, TX test store (shopId `339`, postalCode `75202`, zoneId `90`). None have been generalized yet. `aldi_build_store_registry.py` operates on all 2,677 US stores.

---

## 8. Store Registry

A registry of all US ALDI stores with their Instacart shop IDs has been built and is the primary input for any production scraper.

**File**: `data/aldi_store_registry.jsonl` (JSON Lines, one record per store)

**Uberall source URL** (fetched April 2026):
```
https://locator.uberall.com/api/storefinders/LETA2YVm6txbe0b9lS297XdxDX4qVQ/locations/all?v=20260101&country=US&fieldMask=id&fieldMask=identifier&fieldMask=name&fieldMask=streetAndNumber&fieldMask=city&fieldMask=province&fieldMask=zip&fieldMask=lat&fieldMask=lng
```
Saved as `stand_alone_scripts/aldi/data/all-aldi-us-locations.json`.

**Coverage** (as of April 24, 2026):
- Input: 2,677 physical stores from Uberall snapshot
- Matched output: **2,163 stores** (80.8%)
- Uberall duplicates dropped during preprocessing: 14
- Unmatched Uberall records: 498
- Instacart-only entries: 427
- Arithmetic check: 2,163 matched + 498 Uberall-unmatched + 14 duplicates = 2,675 (2 delta from other collision types) ✅

**Record schema**:
```json
{
  "location_code": "444-089",
  "uberall_id": 5757775,
  "uberall_identifier": "FG14",
  "street_address": "54 E Spring Mill Pointe Dr",
  "city": "Westfield",
  "state": "IN",
  "zip": "46074",
  "lat": 40.042187,
  "lng": -86.159088,
  "instacart_shops": {
    "delivery": "606700",
    "pickup": "606576",
    "instore": "749517"
  },
  "instacart_location_name": "ALDI - GRE 89 - Westfield"
}
```

**Usage**: For product/price scraping, use `instacart_shops["delivery"]` as the `shopId`. A small fraction of records may only have `pickup` or `instore` entries (stores where the delivery shop ID wasn't exposed by the catchment query for that zip).

**How to use in a scraper**:
```python
import json

with open("data/aldi_store_registry.jsonl") as f:
    for line in f:
        store = json.loads(line)
        shop_id = store["instacart_shops"].get("delivery")
        if shop_id:
            # use shop_id for SearchResultsPlacements / Items calls
            pass
```

**District codes as a sampling axis**: The `instacart_location_name` field encodes ALDI's internal district code as a 3-letter prefix followed by a store number within that district (e.g., `"ALDI - DEN 42 - Dallas"`). 26 districts cover all 2,104 matched stores with roughly 70–130 stores each: HAI (132), FAR (99), WEB (98), CTV (95), RPB (91), SWN (89), SBY (89), MTJ (89), MOR (88), OFA (87), FRE (87), SPR (83), DEN (83), JEF (81), TUL (81), OLA (81), HIN (78), OAK (73), SXB (73), GRE (72), and others. These are ALDI's regional distribution districts. This provides a natural geographic sampling axis — one representative store per district gives 26-store coverage spanning the entire US footprint, useful for quick-scan price sampling without scraping every store.

**Fulfillment mode distribution** (of 2,163 matched stores):
- All three modes (delivery + pickup + instore): 1,419 (66%)
- Partial modes: 744 (34%)
- **Effective coverage for product scraping** (stores with a delivery `shopId`): 1,983 of 2,163 matched (92%), or 1,983 of 2,677 Uberall input (74%)

**Mismatch log**: `stand_alone_scripts/aldi/data/aldi_store_registry_mismatches.jsonl` contains all unmatched records with typed reasons and join keys for debugging. 1,065 total mismatch entries:
- `uberall_unmatched`: 498 — Uberall records with no matching Instacart `location_code`
- `instacart_unmatched`: 427 — Instacart shops with no matching Uberall record
- `uberall_duplicate`: 14 — Uberall records sharing a normalized address+zip with another Uberall record
- `instacart_duplicate_mode`: 6 — same `location_code` + `fulfillment_option` seen with two distinct shop IDs (likely stale Instacart records where a shopId was rotated but the old one wasn't cleaned up)

**Mismatch analysis — empirically measured (April 24, 2026)**:

A full diagnostic was run over all 559 unmatched Uberall records, cross-referencing Instacart candidates in the same zip from the cached API responses. Results:

| Failure mode | Count | Recovery path |
|---|---|---|
| Suite/unit token on one side only (base address identical) | **56** | Strip suite tokens before matching — safe, zero false-match risk |
| No Instacart candidates in same zip | **89** | Not recoverable via normalization — Instacart may not serve these zips, or zip differs between systems |
| No suite token involved (other mismatch) | **414** | Requires fuzzy matching (see below) |

**The dominant failure mode is house number discrepancy** (74% of failures, 414 records). Examples from the diagnostic:
- `1403 S Hiawassee Rd` (Uberall) vs `1401 South Hiawassee Rd` (Instacart) — ±2
- `13723 W Bell Rd` vs `13727 W. Bell Road` — ±4
- `12124 Moon Lake Rd` vs `12120 Moon Lake Road` — ±4
- `3988 mpstead Turnpike` (corrupted) vs `3988 Hempstead Turnpike` — data error
- `2020 EG Dr` vs `3940 Linglestown Rd` — completely different strings (shopping centre entrance vs storefront)

These are almost certainly the same physical store with slightly different address surveys in the two systems. They are **not recoverable via normalization alone** — fixing them requires either:
1. **House-number proximity matching** (same street name, house number within ±10): medium-risk; could produce false matches in dense zips where two stores share a street
2. **Street-name-only matching within same zip**: high-risk in zips with multiple ALDI stores on the same road

**Practical summary**:
- Suite-stripping improvement: **+56 stores**, 0 false-match risk → worth implementing
- Fuzzy/proximity matching: potentially **+200–300 stores** but requires human review of matches
- Hard ceiling: 89 records are structurally unresolvable with this approach
- **Realistic improvement**: suite-stripping (implemented April 24, 2026) recovered **+59 stores**, raising matched coverage from 2,104 → 2,163 (79% → 81%). The remaining 498 unmatched records are dominated by house-number discrepancies that require fuzzy matching to resolve.

**Rebuild**: Run `venv/bin/python3 stand_alone_scripts/aldi/aldi_build_store_registry.py`. The zip response cache (`aldi_zip_cache.json`) persists across runs, so interruptions are safe — the script resumes from where it left off (~35–40 min for a full cold run at 2,542 unique zips).

---

## 9. Known Unknowns / Open Questions

1. **`BrowsePlacementsSource` hash**: The persisted query hash for browsing a department by slug has not been captured. This is the missing piece for building the item→category reverse lookup.

2. **Maximum `Items` batch size**: We have tested batches of 8. The maximum batch size Instacart will accept is unknown. A larger batch size would significantly improve throughput.

3. **Rate limiting**: No rate limits have been encountered yet. We have made only a handful of calls during reconnaissance. Production-scale call volumes (thousands of Items requests to hydrate a full product catalog) have not been tested.

4. ~~**Shop ID discovery**~~ — **RESOLVED**. The `/idp/v1/shops?postal_code={zip}` REST endpoint provides all three fulfillment-mode shop IDs for every store near a zip. A complete registry of 2,104 matched US stores is at `data/aldi_store_registry.jsonl` (see Section 8).

5. **`build_sha` and hash stability**: The persisted query hashes could change when Instacart deploys new frontend code. The `build_sha` cookie value (`7c59cc6a4e71d1520462d780b39a2e4a78dfb4f8` as of April 23, 2026) appears to track the deploy version. A hash-rotation detection strategy has not been designed.

6. **`DepartmentNavCollections`**: A related SSR cache key that may contain sub-department brand collection data (e.g. "Friendly Farms", "Simply Nature" brand landing pages). Not yet inspected.

7. **`inStoreItemLocation`**: The `Items` response includes this field (aisle/section label). It is populated for some items. The consistency and structure of this data across the catalog has not been evaluated.

8. **Variant handling**: Some Aldi products have variants (different sizes). The `variantGroup` / `variantGroupId` fields in `Items` suggest a relationship between variants. The structure has not been fully explored.

---

## 10. Data Model Comparison — Aldi vs. Walmart

For reference, we have a working Walmart HTML scraper (`src/utils/walmart_parsers.py`) that extracts items from Walmart's `__NEXT_DATA__` SSR blob. A comparison of what each retailer provides:

| Field | Walmart (HTML scraper) | Aldi (GraphQL API) |
|---|---|---|
| Name | ✅ | ✅ |
| Brand | ✅ | ✅ |
| Price | ✅ | ✅ |
| Unit price | ✅ | ✅ (in viewSection, inconsistent) |
| Size/unit | ✅ | ✅ |
| Category / department | ✅ (explicit, multi-level) | ❌ (absent from item records) |
| Image URLs | ✅ | ✅ |
| Nutrition | ✅ (detailed) | ✅ (summary: Protein/Fat/Sugar/Calories) |
| Dietary badges | ✅ | ✅ (ML-inferred) |
| Ratings | ✅ | ✅ (field present, often null for Aldi) |
| Aisle location | ❌ | ✅ (`inStoreItemLocation`) |
| Variant info | ✅ | ✅ (variantGroup) |
| Item ID format | Walmart item number | `items_{locationId}-{productId}` |

The most significant gap: Walmart provides explicit multi-level category taxonomy with every item. Aldi provides none.

---

## 11. Strategy — Building the Aldi Scraper

### What's done
- Session seeding (trivial, single GET)
- `SearchResultsPlacements` confirmed working — returns all item IDs for a query in one shot, no pagination
- `Items` confirmed working — hydrates full product records in batches
- Department taxonomy captured (20 slugs)
- Store registry complete — 2,104 stores with delivery `shopId`s at `data/aldi_store_registry.jsonl`

### The remaining blocker: item→category mapping

Neither `Items` nor `SearchResultsPlacements` returns category data. The only known path is a **department crawl + reverse lookup**:

1. For each of the 18 meaningful department slugs, call `BrowsePlacementsSource` to get all item IDs in that department.
2. Build a reverse map: `item_id → [department_slug, ...]`.
3. Hydrate item details via `Items` in batches, joining with the category map.

The blocker: **the `BrowsePlacementsSource` persisted query hash has not been captured yet.** Capturing it requires intercepting a browser request while browsing a department page (e.g. `https://www.aldi.us/store/aldi/collections/fresh-produce`).

### Open questions for brainstorming

**Catalog completeness**:
- Are all products reachable via `SearchResultsPlacements` with a broad enough query, or do department crawls surface items that search misses? ALDI Finds (time-limited seasonal items) may behave differently.
- `explore-all-products` is one of the 20 department slugs — does `BrowsePlacementsSource` with this slug return the complete catalog in one call?

**Category strategy**:
- Is there a more direct path to item-level category data that we haven't found? (Hidden field, different operation, SSR cache key?)
- How to handle items in multiple departments — record all, or pick a primary?
- `aldi-brands` and `recipes` aren't product categories. Should they be excluded from the crawl?

**Scale and frequency**:
- Aldi's catalog changes weekly (ALDI Finds appear/disappear). What crawl cadence makes sense — full weekly rebuild, or incremental delta?
- With 2,104 stores × ~1,000 items per store (estimated) × batch size of 8 = ~260,000 `Items` calls per full catalog refresh. Is this feasible, and what concurrency is safe?
- Rate limiting has not been tested at scale. What happens at 5 req/s sustained over hours?

**Multi-store strategy**:
- Should the scraper target all 2,104 stores or a representative sample (e.g. one per state, or one per district code visible in `location_name`)?
- Do prices and inventory actually vary store-to-store for standard products, or only for ALDI Finds?

**Existing scraper architecture**:
- The Walmart scraper in `src/` uses an async fetch pipeline organized around `WalmartScrapeStrategy` (a concrete subclass of `RetailerScrapeStrategy`), with store configs in `data/Walmart_stores.yaml` and retailer-specific parsers in `src/utils/walmart_parsers.py`. How much of this can be reused for Aldi?
- The Walmart flow reads store IDs from a YAML config. The Aldi equivalent would read `shopId` from `data/aldi_store_registry.jsonl`.
- `curl_cffi` is synchronous but can be called from `async def` methods without issue when each scrape run is the only work on the event loop. The Walmart `aiohttp` infrastructure does not need to be reused — `AldiScrapeStrategy` will subclass `RetailerScrapeStrategy` directly rather than `AiohttpScrapeStrategy`, since its transport, pagination model, and output format all differ.
