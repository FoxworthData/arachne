# Aldi Integration Approach

## Overview

This document describes the plan for integrating Aldi as a second target
retailer alongside Walmart in the `src/` orchestration layer. It records
the architectural decisions made before implementation and serves as the
reference for the work that lands in commit 6.

The research foundation for this integration is the set of stand-alone
scripts in `stand_alone_scripts/aldi/`. Those scripts are intentionally
left unchanged — they exist as validated proof-of-concept code and
should not be modified as part of the integration work. The technical
findings they validated are documented in `aldi-item-data-recon.md` and
`aldi-scraper-build-plan.md` (Phase 1 / 1.5).

---

## How Aldi differs from Walmart

Walmart and Aldi require fundamentally different technical approaches,
even though they share the same high-level scraping intent (search
results → product details).

| Concern | Walmart | Aldi |
|---|---|---|
| Target URL | `walmart.com` HTML pages | `aldi.us/graphql` (Instacart Storefront Pro GraphQL API) |
| HTTP client | `aiohttp` (async) | `curl_cffi` (sync, TLS impersonation required) |
| Bot detection | Akamai / PerimeterX — requires heavy cookie seeding | CloudFront CDN — `curl_cffi` Chrome impersonation sufficient |
| Session seeding | `WalmartCookieSeeder` (multi-step, browser persona driven) | Single GET to `https://www.aldi.us/` via `curl_cffi` |
| Proxy usage | Residential proxy (BrightData) | Residential proxy (same BrightData pool) |
| Store identifier | Numeric `store_id` from `Walmart_stores.yaml` | `location_code` (e.g. `444-089`) from `data/aldi_store_registry.jsonl` |
| Response format | Raw HTML — saved, parsed separately | Structured JSON — flat, immediately usable |
| Pagination | `WalmartPaginator` — multi-page async requests | No paginator — two-phase GraphQL (search + items batch) |
| Search output | One `.html.gz` file per page | One `.json.gz` file for the full result set |
| Product output | One `.html.gz` file per product URL | One `.json.gz` file for the full detail batch |

---

## Where Aldi sits in the strategy hierarchy

The scrape strategy hierarchy as of commit 3:

```
RetailerScrapeStrategy   (ABC)
├── AiohttpScrapeStrategy   (shared base — HTML retailers using AiohttpFetcher)
│   ├── WalmartScrapeStrategy
│   ├── FashionphileScrapeStrategy
│   └── BooksToScrapeStrategy
└── (Aldi will subclass RetailerScrapeStrategy directly)
```

`AiohttpScrapeStrategy` exists to share boilerplate among retailers that
all use the same fetch shape: paginated HTML pages over aiohttp, with a
paginator, response analyzer, and gzipped-HTML persistence. Aldi shares
none of that — different transport, different output format, no
pagination — so subclassing the aiohttp base would force it to override
or ignore most of what the base provides. The cleaner choice is for
`AldiScrapeStrategy` to subclass the ABC directly.

This is consistent with the design from commit 2: when retailers diverge
enough that they don't share transport-level structure, they share only
the public ABC. The shared base earns its keep when there's a real shape
match (Walmart, Fashionphile, BooksToScrape); when there isn't, it
shouldn't be inherited from out of mistaken consistency.

---

## Fetch types

Two fetch types are supported for Aldi, matching the existing names used
for Walmart:

- **`search`** — Fetches all search results for a store + query via
  `SearchResultsPlacements` and `Items` batch GraphQL operations.
  Output is a single flat JSON array of items.
- **`product`** — Fetches `ItemDetailData` + `ProductNutritionalInfo`
  for each item returned by a prior search run. Reads from the saved
  search output; writes a matching detail output.

These map directly to the `fetch_type` values already used in
`RunConfig`. The dispatcher (`src/dispatch.py`) requires no changes —
it already routes `search` to `strategy.run_search(query)` and
`product` to `strategy.run_product_lookup()`. The retailer-specific
operations Walmart uses (`store-directory`, `store-directory-by-state`)
do not apply to Aldi and the dispatcher's `isinstance` guard already
handles that case.

---

## Files added and modified

### New files

| File | Purpose |
|---|---|
| `src/utils/strategies/aldi_scrape_strategy.py` | `AldiScrapeStrategy` — direct subclass of `RetailerScrapeStrategy` |
| `src/utils/aldi_session_seeder.py` | `seed_aldi_session()` — proxy-aware single-GET seeding |
| `src/utils/aldi_store_util.py` | `load_aldi_store_by_location_code()` — JSONL loader |
| `data/aldi_store_registry.jsonl` | Store registry built by `aldi_build_store_registry.py` |

### Modified files

| File | Change |
|---|---|
| `src/utils/file_namer.py` | Add `AldiNamer` class (no `page_num` argument) |
| `src/utils/retailer_factory.py` | Add `Aldi` branch in `build_scrape_strategy()` |
| `src/main.py` | Resolve `store_identification` differently when retailer is `Aldi` (JSONL vs. YAML) |

`src/dispatch.py` requires **no changes**. `src/run_config.py` requires
**no changes**. `src/utils/strategies/scrape_strategy.py` (the ABC)
requires **no changes** — `run_search` and `run_product_lookup` are
already on it.

The orchestration layer was deliberately designed in commit 3 so that
adding a new retailer means writing one strategy module and adding one
elif branch to the factory. This integration validates that intent.

---

## Session seeding inside the strategy

`AldiScrapeStrategy` adopts the same lazy-seeding pattern that
`WalmartScrapeStrategy` uses (commit 2.6). On first call to
`run_search` or `run_product_lookup`, the strategy:

1. Constructs a `curl_cffi.Session` with the residential proxy
   pre-applied.
2. Issues a single GET to `https://www.aldi.us/` via that session.
3. Verifies a `__Host-instacart_sid` cookie was issued.
4. Caches the session on `self._curl_session` for all subsequent
   GraphQL calls.

If seeding fails, `_ensure_seeded()` raises `RuntimeError` and the
scrape aborts. There is no silent fallback to un-seeded calls — Aldi's
GraphQL endpoint requires the session cookie, and continuing without
it would just produce errors a few seconds later anyway.

The lazy-seeding pattern is intentionally consistent with Walmart's
even though the underlying mechanism (single GET vs. multi-step cookie
harvest) is completely different. Callers don't need to know which
seeding flow is happening; the strategy hides that.

The `aldi_session_seeder.py` library version lives at
`src/utils/aldi_session_seeder.py` rather than
`stand_alone_scripts/aldi/aldi_session_seeder.py`, which is the
standalone version used by recon scripts. The `src/` version always
applies the proxy; the standalone version doesn't, as a development
convenience.

---

## Store identification

Walmart uses a numeric `store_id` looked up from `Walmart_stores.yaml`
via `load_store_by_id()`.

Aldi uses a `location_code` (e.g. `"444-089"`) looked up from
`data/aldi_store_registry.jsonl` via `load_aldi_store_by_location_code()`.
The registry contains 2,163 stores and includes the `shopId` value
required by the Instacart GraphQL API.

`main.py` selects the right loader based on `config.retailer`. There is
no runtime polymorphism here — the orchestration layer just calls the
retailer-appropriate loader before constructing the strategy:

```python
if config.retailer == "Aldi":
    store_identification = load_aldi_store_by_location_code(config.store_id)
else:
    store_identification = load_store_by_id(store_id=config.store_id)
```

This is the only retailer-aware branch in `main.py`. It exists because
strategy construction needs `store_identification` *before* the strategy
exists, so the strategy can't own this responsibility. Pushing it into
the factory was considered and rejected — the factory would then need a
factory-level dispatch on retailer for the loader, which is the same
two-line if/else, just relocated.

---

## File storage and naming

Aldi output uses the existing `FileStorage` infrastructure unchanged.
The output directory structure follows the same convention as Walmart:

```
$SAVE_LOCATION/
└── Aldi/
    ├── search/
    │   └── Aldi_search_444-089_milk_20260427T142412Z.json.gz
    └── product/
        └── Aldi_product_444-089_milk_20260427T142512Z.json.gz
```

`AldiNamer` (added to `file_namer.py`) produces filenames in this
format. Unlike `WalmartNamer`, it has no `page_num` argument — a single
file covers the full result set for one run.

Output is saved via the existing `FileStorage.save_cleaned_json()`
method, gzip-compressed. No new storage infrastructure is required.

---

## Fetch tracking

`FetcherSession` and `FetchedFile` require no schema changes — all
fields are already nullable or general enough. For Aldi:

- `FetcherSession.url` is set to `"https://www.aldi.us/graphql"` as a
  static identifier.
- Each GraphQL API call produces one `FetchedFile` record (operation
  name as URL, `page_number=None`, `filename` pointing to the saved
  `.json.gz`).
- `success`, `blocked`, `size`, `response_status_code` populate
  normally.

A search run produces ~2 `FetchedFile` records
(`SearchResultsPlacements` + one or more `Items` batches). A product
run produces 2 records per item (`ItemDetailData` +
`ProductNutritionalInfo`).

---

## Product flow: handoff between search and product runs

The product flow reads item IDs from the saved search output rather
than holding them in memory from a prior search run. This keeps each
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
store ID and query. The cluster orchestration layer (not the scraper)
is responsible for sequencing Pod A before Pod B.

`AldiScrapeStrategy.run_product_lookup()` encapsulates this loader.
The dispatcher just calls `await strategy.run_product_lookup()`; it
doesn't need to know that the strategy reads from a saved file.

---

## Low-level fetch primitives on AldiScrapeStrategy

The ABC requires `fetch_all` and `fetch_singleton_urls` as
`@abstractmethod`s — they exist for advanced callers that want to
drive the strategy directly with a known URL or target list. Aldi
implements them with retailer-appropriate semantics:

- `fetch_all(start_url)` — delegates to `run_search(self.fetch_query)`,
  ignoring `start_url`. (Aldi has no concept of a search URL to start
  from; the query goes straight into the GraphQL variables.)
- `fetch_singleton_urls(urls)` — treats `urls` as Aldi item IDs (the
  `items_XXXXX-YYYYY` format) and runs the detail flow against them
  directly, bypassing the saved-search-file lookup that
  `run_product_lookup` does.

This is a small concession to the ABC. The parameter name `urls` for
`fetch_singleton_urls` is a slight misnomer for Aldi — they're item
IDs, not URLs. The misnomer is acceptable because `fetch_singleton_urls`
is *not* the recommended public surface for Aldi callers; it exists
for parity with the ABC. The public surface is `run_product_lookup`,
which sources its own targets from disk.

---

## Concurrency

Aldi API calls are synchronous (`curl_cffi`), made inside `async def`
methods. Because each Aldi run is the only work on the event loop,
blocking calls do not cause problems. A small fixed delay (0.3s) is
applied between per-item detail requests as a rate-limiting courtesy.

This is sufficient for the POC. If needed in production, the sync
calls can be moved to `asyncio.to_thread()` with no changes to the
external interface.

---

## Developer experience: switching between retailers

To run an Aldi search scrape, edit the `DEFAULT_*` constants at the top
of `main.py`:

```python
DEFAULT_RETAILER: Final[str] = "Aldi"
DEFAULT_STORE_ID: Final[str] = "444-089"
DEFAULT_FETCH_TYPE: Final[str] = "search"
DEFAULT_QUERY: Final[str] = "Milk"
```

To run an Aldi product detail scrape:

```python
DEFAULT_RETAILER: Final[str] = "Aldi"
DEFAULT_STORE_ID: Final[str] = "444-089"
DEFAULT_FETCH_TYPE: Final[str] = "product"
DEFAULT_QUERY: Final[str] = "Milk"
```

`DEFAULT_PERSONA_OS_NAME` and `DEFAULT_PERSONA_BROWSER_NAME` remain in
the file. They are passed through to the factory by `main.py`, but
`AldiScrapeStrategy.__init__` ignores them — Aldi's seeding flow does
not use a browser persona. (The Walmart strategy does. Other retailers
ignore them as Aldi does.)

To switch back to Walmart, restore the original values. No other file
needs to change.

---

## What this integration validates

- The `RetailerScrapeStrategy` ABC is honest. Adding a fundamentally
  different retailer (different transport, different output format,
  different seeding mechanism) requires no changes to the ABC, the
  dispatcher, or any existing strategy.
- The lazy-seeding pattern from commit 2.6 generalizes. Both
  retailers' seeding flows are completely opaque to callers.
- `AiohttpScrapeStrategy` correctly stops at retailer-shape boundaries.
  When Aldi doesn't fit, it bypasses the shared base and subclasses the
  ABC directly without contortion.
- The orchestration layer's promise from commit 3 — "adding a retailer
  is one strategy module plus one factory branch" — holds.
