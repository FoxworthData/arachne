# Batch 1: ALDI Store Shop-ID Enumeration

**Date**: April 23, 2026
**Purpose**: Hand off a narrowly-scoped implementation task to the VS Code coding agent. Build a single batch script that produces a complete registry of ALDI US stores with their Instacart shop IDs, suitable as input for product/price scraping.

---

## 1. The Goal

Produce one structured output file — a registry of every US ALDI store — that joins two data sources:

- **Uberall** (physical store inventory): 2,677 stores with addresses and geocoordinates
- **Instacart** (e-commerce shop inventory): three shop IDs per physical store, one for each fulfillment mode (delivery, pickup, instore)

The output is a single registry where each row represents one physical ALDI store and contains every identifier needed to scrape that store's product data downstream.

## 2. Why This Is Now the Bottleneck

Prior investigation established that:

- `shopId` is the only Instacart identifier that affects product/price query routing. `zoneId` and `postalCode` are schema-validated but semantically ignored when making `Items` GraphQL calls.
- A full list of US ALDI stores with addresses is obtainable from Uberall in one unauthenticated HTTP call.
- A postal-code-scoped list of Instacart shop IDs for stores serving that zip is obtainable from an ALDI-hosted REST endpoint.

What's missing is the join: given a physical store, what are its Instacart shop IDs? That join is this batch's job.

Once complete, downstream scraping can operate on any US ALDI store by looking up its shopId(s) from the registry.

## 3. Input

An existing file you already have:

```
stand_alone_scripts/all-aldi-us-locations.json
```

Shape:

```json
{
  "status": "SUCCESS",
  "response": {
    "locations": [
      {
        "id": 5766261,
        "identifier": "L822",
        "name": "ALDI",
        "streetAndNumber": "4120 Gaston Ave",
        "city": "Dallas",
        "province": "Texas",
        "zip": "75246",
        "lat": 32.79403,
        "lng": -96.77667
      },
      // ... 2,676 more
    ]
  }
}
```

## 4. The API to Call

**Endpoint**:
```
GET https://www.aldi.us/idp/v1/shops?postal_code={zip}
```

**Auth**: none strictly required for the data itself, but a valid `__Host-instacart_sid` cookie from a seeded session is recommended (the existing `aldi_session_seeder.py` module produces one).

**Response shape** (truncated example):

```json
{
  "shops": [
    {
      "id": "339",
      "name": "ALDI",
      "retailer_key": "aldi",
      "phone_number": "",
      "fulfillment_option": "delivery",
      "address": {
        "street_address": "4120 Gaston Ave.",
        "city": "Dallas",
        "state": "TX",
        "postal_code": "75246",
        "country_code": "US"
      },
      "retailer_logo_url": "...",
      "background_color_hex": "#55c3f0",
      "location_name": "ALDI -  DEN 42 - Dallas",
      "location_code": "475-042"
    },
    {
      "id": "15030",
      "fulfillment_option": "pickup",
      "address": { "street_address": "4120 Gaston Ave.", ... },
      "location_code": "475-042",
      ...
    },
    {
      "id": "514928",
      "fulfillment_option": "instore",
      "address": { "street_address": "4120 Gaston Ave.", ... },
      "location_code": "475-042",
      ...
    },
    // ... other stores in the zip's catchment, mostly pickup-only
  ]
}
```

Important quirks observed in prior investigation:

- Querying a single zip returns ~30 shops — the "catchment area" of stores serving that zip. Most are pickup-only.
- Only the **primary** store for a zip returns all three fulfillment modes (delivery + pickup + instore). All other stores in the catchment appear as pickup-only entries, even though they probably have delivery and instore shop IDs that would only surface if queried with a zip closer to them.
- **This means**: to get all three shop IDs for every store, query with the zip of *each store's own address*, not a single metro-level zip. The zip field in the Uberall data is what you use.

## 5. The Join Key

The `location_code` field (format `475-NNN`, e.g., `475-042`) is the canonical physical-store identifier. All three fulfillment-mode shop IDs for one physical store share the same `location_code`. This is what joins the Uberall `identifier` (e.g., `L822`) to the three Instacart `shopId`s.

There is no direct ID match between Uberall's `identifier` and Instacart's `location_code` — they're different identifier systems. The join between the two is by **physical address**. Match on:

- `street_address` (normalize: lowercase, strip trailing periods, collapse whitespace, expand/normalize "Ave." / "Avenue" / "Rd" / "Road" / "Blvd" / "Boulevard" etc.)
- `city` (lowercase, strip whitespace)
- `state` / `province` (map full names → 2-letter postal codes, or vice versa)
- Optionally the first 5 digits of zip as a tiebreaker

Plan for imperfect matches. Log mismatches for human review rather than failing silently.

## 6. Output Schema

Produce a JSON-lines file (one record per line) or a single JSON array, writer's choice. Claude Code can choose the format based on what's easiest to consume downstream.

Each record represents one physical store, with fields from both sources joined:

```json
{
  "location_code": "475-042",
  "uberall_id": 5766261,
  "uberall_identifier": "L822",
  "street_address": "4120 Gaston Ave",
  "city": "Dallas",
  "state": "TX",
  "zip": "75246",
  "lat": 32.79403,
  "lng": -96.77667,
  "instacart_shops": {
    "delivery": "339",
    "pickup": "15030",
    "instore": "514928"
  },
  "instacart_location_name": "ALDI -  DEN 42 - Dallas"
}
```

Notes on the schema:

- `location_code` is the primary key. Every output record must have one.
- `instacart_shops` may have any subset of `delivery`, `pickup`, `instore`. If a store only returned a pickup shop ID (because we queried it with a zip that didn't expose the other fulfillment modes), record only what we got. Downstream code handles partial data.
- Include the Uberall fields needed for downstream lookups (identifier + id) and for sanity checks (address, lat/lng).
- Preserve `instacart_location_name` — useful for debugging and for the "DEN 42" district code visible in it.

Also produce a **mismatch log** — a separate file listing Uberall locations that couldn't be matched to any Instacart shop, and Instacart shops that couldn't be matched to any Uberall location. Don't quietly drop them.

## 7. Implementation Notes

### Input loading
Load `all-aldi-us-locations.json`, drill into `response.locations`. You get 2,677 Uberall records. Each has a `zip` field.

### Preprocessing
Normalize the Uberall `province` field. It's inconsistent — "Pennsylvania" and "PA" both appear (172 PA stores split 97/75 between the two forms). Other states may have similar splits. Map everything to 2-letter USPS codes for matching.

### Batch call to Instacart
For each Uberall record:

1. Extract the zip
2. Call `/idp/v1/shops?postal_code={zip}`
3. Parse the response, extract all `shops[]` entries with their `id`, `fulfillment_option`, `address`, `location_code`, `location_name`
4. Cache the response keyed by zip, since multiple Uberall stores likely share zips (saves duplicate calls)

You don't need to dedup Uberall records by zip upfront — caching handles it. But do keep track so you don't make 2,677 calls when 1,800 might suffice.

### Rate limiting
Pace calls conservatively. 1–2 requests per second with small jitter is fine. You're not in a hurry. Add a `time.sleep()` between calls or use `asyncio` with a semaphore if you prefer. Don't hammer the endpoint.

### Error handling
- Transient errors (5xx, timeouts): retry with backoff, up to 3 attempts
- Permanent errors (4xx): log and skip; don't let one bad zip stop the whole batch
- Empty responses (no shops returned): this can happen for zips where ALDI doesn't serve. Log and skip.

### Session seeding
Use `seed_aldi_session()` from the existing `aldi_session_seeder.py` module. The session cookie may or may not be required for this endpoint (prior testing was not exhaustive), but include it for safety. If the session expires mid-batch, re-seed.

### Join logic
After all API calls complete, you have:

- 2,677 Uberall records (full universe of physical stores)
- N Instacart shop records collected from M zip queries, where each Instacart shop has an address and a `location_code`

Group Instacart shops by `location_code`. Each group represents one physical store with 1–3 fulfillment modes. For each group, find the matching Uberall record by address. Build the joined output record.

### Observations worth logging at the end

- Total Uberall records: expected 2,677
- Total unique `location_code`s from Instacart: compare to 2,677 to see coverage
- Stores with all 3 fulfillment modes captured
- Stores with only partial fulfillment modes (likely most — we only queried each zip once)
- Unmatched Uberall records (address normalization failures or stores Instacart doesn't know about)
- Unmatched Instacart shops (shops with no corresponding Uberall record — possible if Instacart has stale data or serves addresses Uberall doesn't)

## 8. Explicit Non-Goals

These things are **out of scope** for this batch:

- Hydrating rich store metadata (hours, phone, payment methods). That's Batch 2.
- Re-querying stores that only returned pickup shop IDs, to fill in their delivery and instore IDs. A future pass can do this using stores' nearest-zip, but it's not required for a working first version.
- Handling stores that opened or closed after the Uberall snapshot was taken.
- Integrating with any existing scraper architecture. This is a standalone batch.
- Producing anything fancier than one output file plus a mismatch log.

Don't expand scope without checking in. The goal is one output file, usable immediately.

## 9. Deliverables

1. A script (Python, using `curl_cffi` for consistency with existing tools) that runs the batch end-to-end.
2. The output file: store registry as JSON (lines or array).
3. A mismatch log file.
4. A short summary printed at the end: coverage counts, fulfillment mode completeness, mismatch counts.

## 10. First Action

Propose the module layout and the address-normalization strategy before writing code. Specifically, suggest:

- How many Python files and what they do
- What the address normalization function does (list of transformations)
- How the caching layer works (in-memory dict keyed by zip? persistent? file-backed?)
- How the join logic handles collisions (two Uberall stores at the same address? two Instacart shops at the same address with the same fulfillment mode?)
- What the mismatch log format is

Wait for approval before implementing. This is a batch job that's expensive to rerun (2,677+ API calls). Design review is cheaper than debugging a bad run.
