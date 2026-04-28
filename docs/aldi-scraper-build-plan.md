# Aldi Scraper Build Plan

**Status:** Phase 1 complete · Phase 1.5 complete (April 24, 2026)  
**Goal:** Add Aldi as a retailer in the Arachne orchestration layer alongside Walmart.

---

## Overview

The build is split into two phases:

| Phase | Scope | Status | Output |
|---|---|---|---|
| **1** | Stand-alone search script — validates full pipeline end-to-end | ✅ Complete | `stand_alone_scripts/aldi/aldi_search.py` |
| **1.5** | Stand-alone product detail enrichment — description, ingredients, directions, warnings, images, nutrition | ✅ Complete | `stand_alone_scripts/aldi/aldi_fetch_product_detail.py` |
| **2** | Integrate Aldi into `src/` orchestration layer | ⏳ Not started | Aldi works via `main.py` like Walmart |

---

## Phase 1 — Stand-alone Search Script

### Goal

A self-contained CLI script that accepts an arbitrary Aldi store identifier and search term, fetches all search results from the Instacart GraphQL API, and writes structured output to disk. No dependencies on `src/`.

### Usage (target)

```bash
venv/bin/python3 stand_alone_scripts/aldi/aldi_search.py \
    --store 444-089 \
    --query "milk"
```

`--store` is the `location_code` from `data/aldi_store_registry.jsonl` (e.g. `"444-089"`).

### Output

`stand_alone_scripts/aldi/data/aldi_search_{location_code}_{query}_{timestamp}.json`

One JSON file per run containing:
```json
{
  "meta": {
    "location_code": "444-089",
    "shop_id": "606700",
    "query": "milk",
    "fetched_at": "2026-04-24T18:00:00Z",
    "item_count": 12
  },
  "items": [
    {
      "id": "items_14655-16902710",
      "name": "Friendly Farms Whole Milk",
      "brand": "friendly farms",
      "price_string": "$3.05",
      "price_value": "3.05",
      "pricing_unit": "1 gal",
      "available": true,
      "stock_level": "highlyInStock",
      "evergreen_url": "16902710-friendly-farms-vitamin-d-milk-1-gal"
    }
  ]
}
```

---

### Key Design Decisions

#### 1. Two-phase fetch is required: `SearchResultsPlacements` + `Items` fallback

**Confirmed during implementation.** The `first` variable in `SearchResultsPlacements` controls how many item grids are inline-hydrated (i.e., have their full `ItemsItem` data populated in `content.items`). The remaining result grids have a populated `content.itemIds` but an empty `content.items` array.

With `first=200`, only **1 of 67 items** was inline-hydrated for the "milk" query at store `444-089`. The other 66 were returned as bare IDs and required a follow-up `Items` batch call.

The implemented strategy:
1. Fire `SearchResultsPlacements` with `first=200`. Collect inline items from grids where `content.items` is non-empty. Collect overflow IDs from grids where `content.items` is empty but `content.itemIds` is non-empty.
2. Batch-fetch overflow IDs via the `Items` operation (50 IDs per call).
3. Both sources return identical `ItemsItem` schemas — the same `flatten_item()` function handles both.

The `Items` operation is therefore a core part of every search fetch, not an optional fallback.

#### 2. No GraphQL pagination — all results come back in one `SearchResultsPlacements` call

**Confirmed during implementation.** The `SearchResultsPlacements` response contains zero pagination fields (`endCursor`, `hasNextPage`, `pageInfo` are absent). All result grids for a query are returned in a single call — the `first` variable does not gate the number of result *grids*, only how many of them are inline-hydrated.

For the "milk" query at store `444-089`, 67 result grids were returned in a single call. No second page exists. The only network round-trips after the initial `SearchResultsPlacements` call are `Items` batch fetches to hydrate the bare-ID grids (see Design Decision #1).

The script includes a truncation guard: if `total_found >= first`, a warning is printed suggesting a larger `--first` value. This is a belt-and-suspenders check; in practice `first` does not appear to cap result count.

#### 3. Location parameters

- `shopId`: sourced from `store["instacart_shops"]["delivery"]` in the registry. **This is the only meaningful location key.**
- `postalCode`: use the store's actual `zip` from the registry (semantically ignored by Instacart, but send a plausible value).
- `zoneId`: hard-code `"1"` (any non-null string works; confirmed empirically).

#### 4. Session seeding

Import `seed_aldi_session` from `aldi_session_seeder.py` (already written). This performs a single GET to `https://www.aldi.us/` to acquire `__Host-instacart_sid` via Set-Cookie. The session object's cookie jar is then used for the GraphQL request.

#### 5. Request construction

The GraphQL call is a GET request to `https://www.aldi.us/graphql` with three URL parameters:
- `operationName=SearchResultsPlacements`
- `variables=<url-encoded JSON>`
- `extensions=<url-encoded JSON with persisted query hash>`

Persisted query hash: `6e6b53b10516829d9b7b9fae0cbc9b65bcbbc8792d77836f65b9db6a606057a7`

Variables template:
```python
variables = {
    "filters": [],
    "action": None,
    "query": search_term,
    "pageViewId": str(uuid.uuid4()),   # fresh UUID per request
    "elevatedProductId": None,
    "searchSource": "search",
    "disableReformulation": False,
    "disableLlm": False,
    "forceInspiration": False,
    "orderBy": "bestMatch",
    "clusterId": None,
    "includeDebugInfo": False,
    "clusteringStrategy": None,
    "contentManagementSearchParams": {"itemGridColumnCount": 1},
    "shopId": shop_id,
    "postalCode": zip_code,
    "zoneId": "1",
    "first": 200,
}
```

Extensions:
```python
extensions = {
    "persistedQuery": {
        "version": 1,
        "sha256Hash": "6e6b53b10516829d9b7b9fae0cbc9b65bcbbc8792d77836f65b9db6a606057a7",
    }
}
```

#### 6. Transport

Use `curl_cffi` with `impersonate="chrome"` (same pattern as all other aldi scripts). `aiohttp` is not used — Aldi's Cloudfront CDN validates TLS fingerprint.

#### 7. Response parsing

Traverse `data.searchResultsPlacements.placements`, filter for `content.__typename == "SearchContentManagementSearchItemGrid"`, and split grids into inline-hydrated items vs. overflow IDs:

```python
def extract_search_results(response: dict) -> tuple[list[dict], list[str]]:
    placements = response["data"]["searchResultsPlacements"]["placements"]
    inline_items, overflow_ids = [], []
    for placement in placements:
        content = placement.get("content") or {}
        if content.get("__typename") != "SearchContentManagementSearchItemGrid":
            continue
        if content.get("items"):
            inline_items.extend(content["items"])
        else:
            overflow_ids.extend(content.get("itemIds") or [])
    return inline_items, overflow_ids
```

Overflow IDs are then batch-fetched via `Items` (50 per call). Both sources use the same `flatten_item()` function.

---

### Implementation (complete)

See `stand_alone_scripts/aldi/aldi_search.py`. Key functions:

- **`load_store(location_code)`** — scans `data/aldi_store_registry.jsonl` line-by-line, returns matching record, raises `ValueError` if not found or no delivery `shopId`.
- **`_build_search_url(...)`** — constructs the `SearchResultsPlacements` GET URL with URL-encoded `variables` and `extensions`.
- **`_build_items_url(item_ids, ...)`** — constructs the `Items` GET URL for a batch of IDs.
- **`_graphql_get(session, url, operation)`** — fires a GET with `impersonate="chrome"`, returns parsed JSON, raises `RuntimeError` on HTTP error, non-JSON, or GraphQL errors.
- **`extract_search_results(response)`** — as described in Design Decision #7 above.
- **`flatten_item(raw)`** — maps `ItemsItem` to flat output record. Handles both inline (from `SearchResultsPlacements`) and batch (from `Items`) sources identically.
- **`main()`** — arg parse → load store → seed session → search fetch → split inline/overflow → Items batch fetch → flatten → write JSON → print summary.

---

### Files

| File | Role |
|---|---|
| `stand_alone_scripts/aldi/aldi_search.py` | Phase 1 deliverable |
| `stand_alone_scripts/aldi/aldi_fetch_product_detail.py` | Phase 1.5 deliverable |
| `data/aldi_store_registry.jsonl` | Input: store → shopId mapping |
| `stand_alone_scripts/aldi/aldi_session_seeder.py` | Existing: session seeding |
| `stand_alone_scripts/aldi/data/aldi_search_{lc}_{q}_{ts}.json` | Output: per-run search results |
| `stand_alone_scripts/aldi/data/aldi_detail_{item}_{ts}.json` | Output: per-run detail results |

---

### Validation Run (April 24, 2026)

Store `444-089` (ALDI - GRE 89 - Westfield, IN), query `milk`:

```
Loading store '444-089' from registry...
  location_code=444-089  shop_id=606700  zip=46074  name=ALDI - GRE 89 - Westfiled
Seeding Instacart session...  Session seeded OK.
Fetching SearchResultsPlacements  query='milk'  first=200...
  Total results found: 67
  Inline-hydrated: 1
  Overflow (need Items call): 66
Fetching 66 overflow items in 2 batch(es)...
  Batch 1/2: 50 items fetched
  Batch 2/2: 16 items fetched
Done. 67 items written to aldi_search_444-089_milk_20260424T180734Z.json
```

Output quality: 0 items missing price, 0 items missing image URL.

### Open Questions / Remaining TODOs

- [ ] **Max result count for broad queries**: test a very broad query (e.g., `"a"` or `""`) to find the ceiling. If ≥200 grids are returned, the truncation warning will fire and `--first` should be increased.
- [ ] **`x-ic-qp` header**: recon scripts sent a static hardcoded UUID. The production script omits it (not included in `_GRAPHQL_HEADERS`). Confirm this continues to work at scale — add back as a per-request UUID if any bot-block signals appear.
- [ ] **Rate limiting at scale**: not yet characterized beyond single-store. Test district-level batch (10–20 stores) before running at full registry scale.
- [ ] **Items batch size ceiling**: recon tested 8; implementation uses 50. The true maximum is unknown. Reduce to 25 if batch errors appear.

---

## Phase 1.5 — Stand-alone Product Detail Enrichment

### Goal

A self-contained CLI script that takes items from a search result file (or a single item ID) and fetches full product detail — description, ingredients, directions, warnings, multiple product images, and a complete nutrition facts panel — via two additional GraphQL operations.

### Context: Data Sources Discovered

Phase 1 (`Items` operation) returns price, availability, brand, size, dietary tags, and stock level — but no product text content. That content is loaded client-side from two additional operations, both confirmed working via direct API calls.

The data is also present in the SSR `apollo-state` blob embedded in every product detail page (`<script id="apollo-state">`), but calling the operations directly is simpler and doesn't require HTML parsing.

### Operations

#### `ItemDetailData`

- **Hash**: `1498d8c45b80c63ada20d2a07c07bde2364a3c69e1252ed3dfd6a095c2f2e4c8`
- **Variables**: `{"id": "items_{retailerLocationId}-{productId}", "isFeatured": false, "shopId": "339"}`
- **Key**: Uses the full `items_XXXXX-YYYYY` item ID format (same as `Items` operation)
- **Returns**:
  - `detailSections[]` — array of `{headerString, bodyString}` covering Details (description), Ingredients, Warnings
  - `productDetailSections[]` — same content with a `sectionTypeVariant` field (`"details"`, `"ingredients"`, `"directions"`) for reliable keying
  - `warningSection` — warnings also surfaced as a top-level object
  - `detailImages[]` — multiple product images with `url` and `altText` (often 2+ angles vs. the single image in `Items`)

#### `ProductNutritionalInfo`

- **Hash**: `9bc43a13c48e633ba4c8016118f101942a44603c5d10f913e9e471ffb730185a`
- **Variables**: `{"productId": "36953", "shopId": "339"}`
- **Key**: Uses the bare `productId` integer string (the numeric portion of the `items_XXXXX-YYYYY` ID)
- **Returns**: Full nutrition panel:
  - Macros: `calories`, `fat`, `saturatedFat`, `transFat`, `cholesterol`, `sodium`, `carbohydrate`, `fiber`, `sugars`, `addedSugars`, `protein`
  - `servingSize`, `servingsPerContainer`
  - `viewSection` with formatted display strings (e.g. `"9g"`, `"45%"`) matching the physical nutrition label

### How product_id is derived

`Items` returns items in the format `items_{retailerLocationId}-{productId}` (e.g. `items_14655-36953`). The bare `productId` for `ProductNutritionalInfo` is the portion after the last `-` (`"36953"`). The `flatten_item()` function in `aldi_search.py` already exposes this as the `product_id` field.

### UPC / Barcode — Not Available

Confirmed definitively (April 24, 2026): **no UPC, GTIN, EAN, or barcode field exists anywhere in the Instacart API**. Checked exhaustively:
- All 60 GraphQL responses in the full-page HAR
- Full SSR `apollo-state` blob (248KB decoded)
- Every scalar field on the `ItemsItem` type

The `legacyId` field (e.g. `1465010741`) is Instacart's own internal ID and does not match UPC format. For national brands, UPCs could be enriched post-hoc from Open Food Facts (`world.openfoodfacts.org/api/v2/product/{upc}`) — but that requires the UPC as input, which Instacart doesn't provide.

### Usage

```bash
# Single item
venv/bin/python3 stand_alone_scripts/aldi/aldi_fetch_product_detail.py \
    --item-id items_14655-36953 \
    --shop-id 339

# Batch from search result file
venv/bin/python3 stand_alone_scripts/aldi/aldi_fetch_product_detail.py \
    --from-search "stand_alone_scripts/aldi/data/aldi_search_444-089_milk_*.json" \
    --limit 10
```

### Output Schema

```json
{
  "metadata": {"fetched_at": "...", "item_count": 1},
  "items": [{
    "item_id": "items_14655-36953",
    "product_id": "36953",
    "shop_id": "339",
    "description": "Goya Coconut Milk is your go-to for rich, creamy flavor...",
    "ingredients": "COCONUT MILK, WATER, POTASSIUM METABISULFITE (AS A PRESERVATIVE).",
    "directions": "Shake well for better flavor.\nDo not freeze...",
    "warnings": "Contains: tree nuts. Contains: sulfites.",
    "images": [
      {"url": "https://www.instacart.com/assets/.../large_90e754f3.jpg", "alt_text": "Front of ..."},
      {"url": "https://www.instacart.com/assets/.../large_7bc62ab3.jpg", "alt_text": "Top of ..."}
    ],
    "nutrition": {
      "calories": 100.0, "fat": 9.0, "protein": 2.0, "carbohydrate": 2.0,
      "servingSize": "0.25", "servingsPerContainer": "About 7",
      "sodium": 10.0, "sugars": 2.0, "addedSugars": 0.0,
      "saturatedFat": 9.0, "transFat": 0.0, "cholesterol": 0.0, "fiber": 0.0,
      "display": {"totalFatValueString": "9g", "saturatedFatPctString": "45%", ...}
    }
  }]
}
```

### Validation (April 24, 2026)

Single-item test on Goya Coconut Milk (`items_14655-36953`, store `444-089`):
- `description` ✓, `ingredients` ✓, `directions` ✓, `warnings` ✓
- `images`: 2 (front + top angles)
- `nutrition`: full panel — 16 nutrient fields + formatted display strings

### Files

| File | Role |
|---|---|
| `stand_alone_scripts/aldi/aldi_fetch_product_detail.py` | Phase 1.5 deliverable |
| `stand_alone_scripts/aldi/aldi_session_seeder.py` | Existing: session seeding |
| `data/aldi_store_registry.jsonl` | Not directly needed; shop_id comes from search output |

### Open Questions / Next Steps

- [ ] **Nutrition coverage rate**: `ProductNutritionalInfo` returns `null` for some items (e.g. non-food items like cleaning products). Measure null rate across a full search result set.
- [ ] **`ItemDetailData` availability rate**: Some items may not have description/ingredients (especially non-food or store-private items). Measure across a full search set.
- [ ] **Rate limiting with two calls per item**: At 67 items × 2 calls each = 134 requests. Characterize latency and any throttling signals before scaling up.
- [ ] **Combine with search**: Consider a unified `aldi_full_harvest.py` that runs search → Items batch → detail enrichment in a single pipeline, writing a combined output file with all fields.

---

## Phase 2 — Orchestration Layer Integration

The orchestration layer in `src/` is built around the `RetailerScrapeStrategy` ABC
(`src/utils/strategies/scrape_strategy.py`). Each retailer is a concrete subclass
that owns its own header building, session seeding, target resolution, and
fetch execution. Walmart inherits from `AiohttpScrapeStrategy` (the shared
base for HTML/aiohttp retailers); Aldi will subclass `RetailerScrapeStrategy`
directly because its transport (`curl_cffi`), pagination model (none), and
output format (JSON) all differ from the aiohttp family.

This is consistent with the design: when retailers diverge enough that they
don't share transport-level structure, they share only the public ABC.

For the architectural rationale and full file-by-file plan, see
`docs/aldi-integration-approach.md`. The summary version follows.

### Files added

| File | Purpose |
|---|---|
| `src/utils/strategies/aldi_scrape_strategy.py` | `AldiScrapeStrategy` — implements `RetailerScrapeStrategy` against the Instacart GraphQL API |
| `src/utils/aldi_session_seeder.py` | `seed_aldi_session()` — single-GET seeding via `curl_cffi`, proxied |
| `src/utils/aldi_store_util.py` | `load_aldi_store_by_location_code()` — reads `data/aldi_store_registry.jsonl` |
| `src/utils/file_namer.py` | Add `AldiNamer` class (no `page_num`) |
| `data/aldi_store_registry.jsonl` | Copy of the registry built by `aldi_build_store_registry.py` |

### Files modified

| File | Change |
|---|---|
| `src/utils/retailer_factory.py` | `build_scrape_strategy()` adds an `Aldi` branch returning an `AldiScrapeStrategy` |
| `src/main.py` | Resolve `store_identification` differently when retailer is `Aldi` (JSONL lookup vs. YAML lookup); the dispatcher and run flow are otherwise unchanged |

### Run-time control flow

```
main.py:
  config = RunConfig(retailer="Aldi", store_id="444-089", ...)
  store_identification = load_aldi_store_by_location_code(config.store_id)
  strategy = build_scrape_strategy(retailer="Aldi", store_identification=..., ...)
  await dispatch_fetch_type(strategy, config, logger)
  logger.info(strategy.get_session_summary())

AldiScrapeStrategy:
  __init__:
    construct curl_cffi session lazily (set on first use)
    no paginator, no aiohttp fetcher

  run_search(query):
    _ensure_seeded()                    # idempotent, single GET to aldi.us
    SearchResultsPlacements call
    Items batch calls for overflow IDs
    flatten + save to {SAVE_LOCATION}/Aldi/search/...

  run_product_lookup():
    _ensure_seeded()
    load item IDs from latest matching search output file
    ItemDetailData + ProductNutritionalInfo per item
    save to {SAVE_LOCATION}/Aldi/product/...

  fetch_all / fetch_singleton_urls:
    Required by the ABC. fetch_all delegates to run_search and ignores
    start_url; fetch_singleton_urls treats `urls` as item IDs and runs
    the detail flow against them. These exist for advanced callers
    that want to drive the strategy directly with a known target list.
```

### Run-once seeding

The `_ensure_seeded()` pattern adopted in `WalmartScrapeStrategy` carries
over directly. First call to `run_search` or `run_product_lookup` seeds
a `curl_cffi.Session` with the residential proxy applied at session
construction time. The session is reused for every subsequent call. An
`asyncio.Lock` guards against concurrent first calls.

If seeding fails, `_ensure_seeded()` raises `RuntimeError` and the run
aborts. The strategy never silently falls back to un-seeded calls.

### Store identification

Walmart uses a numeric `store_id` looked up from `Walmart_stores.yaml`.

Aldi uses a `location_code` (e.g. `"444-089"`) looked up from
`data/aldi_store_registry.jsonl`. The registry contains 2,163 stores and
includes the `shopId` value required by the Instacart GraphQL API.

`main.py` selects the loader based on `config.retailer`. There is no
runtime polymorphism here — the orchestration layer just calls the right
loader for the configured retailer before constructing the strategy.

### File storage and naming

Aldi output uses the existing `FileStorage` infrastructure unchanged. The
output directory structure follows the same convention as Walmart:

```
$SAVE_LOCATION/
└── Aldi/
    ├── search/
    │   └── Aldi_search_444-089_milk_20260427T142412Z.json.gz
    └── product/
        └── Aldi_product_444-089_milk_20260427T142512Z.json.gz
```

`AldiNamer` (added to `file_namer.py`) produces filenames in this format.
Unlike `WalmartNamer`, it has no `page_num` argument — a single file
covers the full result set for one run.

Output is saved via the existing `FileStorage.save_cleaned_json()`
method, gzip-compressed. No new storage infrastructure is required.

### Fetch tracking

`FetcherSession` and `FetchedFile` require no schema changes — all fields
are already nullable or general enough. For Aldi:

- `FetcherSession.url` is set to `"https://www.aldi.us/graphql"` as a
  static identifier.
- Each GraphQL API call produces one `FetchedFile` record (operation name
  as URL, `page_number=None`, `filename` pointing to the saved
  `.json.gz`).
- `success`, `blocked`, `size`, `response_status_code` populate normally.

A search run produces ~2 `FetchedFile` records (`SearchResultsPlacements`
+ `Items` batch). A product run produces 2 records per item
(`ItemDetailData` + `ProductNutritionalInfo`).

### Product flow: handoff between search and product runs

The product flow reads item IDs from the saved search output rather than
holding them in memory from a prior search run. This keeps each
execution stateless and independently restartable — a property required
for parallel execution on a GKE cluster.

```
Pod A: retailer=Aldi, store=444-089, fetch_type=search,  query=Milk
       → writes $SAVE_LOCATION/Aldi/search/Aldi_search_444-089_milk_{ts}.json.gz

Pod B: retailer=Aldi, store=444-089, fetch_type=product, query=Milk
       → reads  $SAVE_LOCATION/Aldi/search/Aldi_search_444-089_milk_{ts}.json.gz  (latest)
       → writes $SAVE_LOCATION/Aldi/product/Aldi_product_444-089_milk_{ts}.json.gz
```

File resolution: Pod B selects the most recent search file matching the
store ID and query. The cluster orchestration layer (not the scraper) is
responsible for sequencing Pod A before Pod B.

### Concurrency

Aldi API calls are synchronous (`curl_cffi`), made inside `async def`
methods. Because each Aldi run is the only work on the event loop,
blocking calls do not cause problems. A small fixed delay (0.3s) is
applied between per-item detail requests as a rate-limiting courtesy.

This is sufficient for the POC. If needed in production, the sync calls
can be moved to `asyncio.to_thread()` with no changes to the external
interface.

---

## Dependency Map

```
Phase 1 (stand-alone search)
└── aldi_search.py
    ├── aldi_session_seeder.py          (existing)
    └── data/aldi_store_registry.jsonl  (existing)

Phase 1.5 (stand-alone detail enrichment)
└── aldi_fetch_product_detail.py
    ├── aldi_session_seeder.py          (existing)
    └── [input] aldi_search_*.json output from Phase 1

Phase 2 (orchestration)
└── src/main.py
    ├── src/utils/retailer_factory.py            (modify: add Aldi branch)
    ├── src/utils/strategies/aldi_scrape_strategy.py  (new)
    ├── src/utils/aldi_session_seeder.py         (new — proxy-aware version)
    ├── src/utils/aldi_store_util.py             (new — JSONL loader)
    ├── src/utils/file_namer.py                  (modify: add AldiNamer)
    └── data/aldi_store_registry.jsonl           (new)
```

---

## What Phase 1 + 1.5 Validate Before Phase 2

- Session seeding works reliably across repeated calls
- `SearchResultsPlacements` returns complete results for arbitrary queries and stores
- The `first` variable behavior and pagination boundary (if any)
- Output schema is stable and parseable
- `ItemDetailData` returns description, ingredients, directions, warnings, and multi-image for each item
- `ProductNutritionalInfo` returns a full nutrition panel keyed by bare `productId`
- Both detail operations use the same session seeding approach — no additional auth required
- Rate limiting / bot detection behavior at modest scale

## Confirmed Persisted Query Hashes

Extracted from SSR `apollo-state` on `www.aldi.us/store/aldi/products/36953-goya-coconut-milk-13-5-fl-oz`, April 24, 2026.

| Operation | Hash |
|---|---|
| `SearchResultsPlacements` | `6e6b53b10516829d9b7b9fae0cbc9b65bcbbc8792d77836f65b9db6a606057a7` |
| `Items` | `5116339819ff07f207fd38f949a8a7f58e52cc62223b535405b087e3076ebf2f` |
| `ItemDetailData` | `1498d8c45b80c63ada20d2a07c07bde2364a3c69e1252ed3dfd6a095c2f2e4c8` |
| `ItemDetailSupplementalFields` | `b3e79191d1db94a2c24eac6b8016d36239d1387f2fd39fea86d1260da4d03b83` |
| `ProductNutritionalInfo` | `9bc43a13c48e633ba4c8016118f101942a44603c5d10f913e9e471ffb730185a` |
| `BrowsePlacementsSource` | `87e75f2a0a50557ad96b87cd14c9f9d312eb409ed6391a9712ee7f2a3283208b` |
| `GetItemVariantGroup` | `027131fddd11fa4aae28f51d844e27a0e1be23edd02a1dbbc70b42a0dbc77405` |
| `RecipesByProductId` | *(not yet captured — available in HAR, operation seen at 98b response)* |

Note: Hashes are stable until Instacart deploys new frontend code (detectable via `build_sha` cookie change).
