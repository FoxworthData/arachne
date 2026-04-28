"""Aldi search scraper — fetches all search results for an arbitrary store and query.

Strategy:
  1. Call SearchResultsPlacements with first=<N> (default 200).
     Each result grid placement either:
       a) has its ItemsItem fully hydrated inline in content.items  (count controlled by `first`)
       b) has an itemId in content.itemIds but an empty content.items array (overflow)
  2. For any overflow item IDs not hydrated inline, batch-fetch via the Items operation.
  3. Flatten all items to a clean output schema and write to JSON.

Usage:
    venv/bin/python3 stand_alone_scripts/aldi/aldi_search.py --store 444-089 --query milk
    venv/bin/python3 stand_alone_scripts/aldi/aldi_search.py --store 444-089 --query "whole milk"
    venv/bin/python3 stand_alone_scripts/aldi/aldi_search.py --help

Input:
    data/aldi_store_registry.jsonl  (repo root)

Output:
    stand_alone_scripts/aldi/data/aldi_search_{location_code}_{query}_{timestamp}.json
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).parent))
from aldi_session_seeder import seed_aldi_session

GRAPHQL_URL = "https://www.aldi.us/graphql"
SEARCH_HASH = "6e6b53b10516829d9b7b9fae0cbc9b65bcbbc8792d77836f65b9db6a606057a7"
ITEMS_HASH = "5116339819ff07f207fd38f949a8a7f58e52cc62223b535405b087e3076ebf2f"
ITEMS_BATCH_SIZE = 50  # recon tested 8; 50 is a conservative production ceiling

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
REGISTRY_FILE = REPO_ROOT / "data" / "aldi_store_registry.jsonl"
DATA_DIR = SCRIPT_DIR / "data" / "runs"

_GRAPHQL_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    ),
    "x-client-identifier": "web",
    "x-ic-view-layer": "true",
}


# ── Store loading ─────────────────────────────────────────────────────────────

def load_store(location_code: str) -> dict:
    """Return the registry record for the given location_code.

    Raises ValueError if the location_code is not found.
    """
    with REGISTRY_FILE.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("location_code") == location_code:
                return record
    raise ValueError(
        f"Store '{location_code}' not found in {REGISTRY_FILE}. "
        "Use a location_code value from data/aldi_store_registry.jsonl."
    )


# ── URL builders ──────────────────────────────────────────────────────────────

def _build_search_url(
    shop_id: str, zip_code: str, query: str, first: int, page_view_id: str
) -> str:
    variables = {
        "filters": [],
        "action": None,
        "query": query,
        "pageViewId": page_view_id,
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
        "first": first,
    }
    extensions = {
        "persistedQuery": {"version": 1, "sha256Hash": SEARCH_HASH}
    }
    params = {
        "operationName": "SearchResultsPlacements",
        "variables": json.dumps(variables, separators=(",", ":")),
        "extensions": json.dumps(extensions, separators=(",", ":")),
    }
    return f"{GRAPHQL_URL}?{urlencode(params)}"


def _build_items_url(item_ids: list[str], shop_id: str, zip_code: str) -> str:
    variables = {
        "ids": item_ids,
        "shopId": shop_id,
        "zoneId": "1",
        "postalCode": zip_code,
    }
    extensions = {
        "persistedQuery": {"version": 1, "sha256Hash": ITEMS_HASH}
    }
    params = {
        "operationName": "Items",
        "variables": json.dumps(variables, separators=(",", ":")),
        "extensions": json.dumps(extensions, separators=(",", ":")),
    }
    return f"{GRAPHQL_URL}?{urlencode(params)}"


# ── HTTP ──────────────────────────────────────────────────────────────────────

def _graphql_get(session, url: str, operation: str) -> dict:
    """Fire a GET GraphQL request, return parsed JSON. Raises RuntimeError on failure."""
    headers = {**_GRAPHQL_HEADERS, "x-page-view-id": str(uuid.uuid4())}
    resp = session.get(url, headers=headers, impersonate="chrome", timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(
            f"{operation} failed: HTTP {resp.status_code}\n{resp.text[:500]}"
        )
    try:
        data = resp.json()
    except Exception as exc:
        raise RuntimeError(
            f"{operation} returned non-JSON (HTTP {resp.status_code}): {exc}\n{resp.text[:500]}"
        ) from exc

    if data.get("errors"):
        raise RuntimeError(f"{operation} GraphQL errors: {data['errors']}")

    return data


# ── Response parsing ──────────────────────────────────────────────────────────

def extract_search_results(response: dict) -> tuple[list[dict], list[str]]:
    """Parse a SearchResultsPlacements response.

    Returns:
        inline_items:   fully-hydrated ItemsItem dicts (content.items was non-empty)
        overflow_ids:   itemIds whose grids had empty content.items (need Items call)
    """
    placements = response["data"]["searchResultsPlacements"]["placements"]
    inline_items: list[dict] = []
    overflow_ids: list[str] = []
    for placement in placements:
        content = placement.get("content") or {}
        if content.get("__typename") != "SearchContentManagementSearchItemGrid":
            continue
        items = content.get("items") or []
        if items:
            inline_items.extend(items)
        else:
            overflow_ids.extend(content.get("itemIds") or [])
    return inline_items, overflow_ids


def flatten_item(raw: dict) -> dict:
    """Map a raw ItemsItem (from either SearchResultsPlacements or Items) to a flat record."""
    price_vs = (raw.get("price") or {}).get("viewSection") or {}
    item_card = price_vs.get("itemCard") or {}
    item_details = price_vs.get("itemDetails") or {}
    avail = raw.get("availability") or {}
    item_vs = raw.get("viewSection") or {}
    image = item_vs.get("itemImage") or {}
    tracking = item_vs.get("trackingProperties") or {}
    on_sale_ind = tracking.get("on_sale_ind") or {}
    dietary = raw.get("dietary") or {}
    dietary_vs = dietary.get("viewSection") or {}
    qty = raw.get("quantityAttributes") or {}

    # 4-value nutrition summary (Protein/Fat/Sugar/Calories) — present on ~36% of items
    nutr_attrs = raw.get("nutritionalAttributes") or []
    nutrition_summary = (
        {
            a["viewSection"]["longLabelString"].lower(): a["viewSection"]["valueString"]
            for a in nutr_attrs
            if (a.get("viewSection") or {}).get("longLabelString")
        }
        or None
    )

    return {
        # ── Identity ──────────────────────────────────────────────────────────
        "id": raw.get("id"),
        "product_id": raw.get("productId"),
        "legacy_id": raw.get("legacyId"),
        # ── Product ───────────────────────────────────────────────────────────
        "name": raw.get("name"),
        "brand": raw.get("brandName"),
        "brand_id": raw.get("brandId"),
        "size": raw.get("size"),
        "product_category": tracking.get("product_category_name"),
        "evergreen_url": raw.get("evergreenUrl"),
        # ── Price ─────────────────────────────────────────────────────────────
        "price_string": price_vs.get("priceString"),
        "price_value": price_vs.get("priceValueString"),
        "price_per_unit": item_details.get("pricePerUnitString"),
        "is_on_sale": on_sale_ind.get("on_sale"),
        "full_price_string": item_card.get("fullPriceString"),
        "discount_string": item_card.get("discountHeaderString"),
        "buy_one_get_one": on_sale_ind.get("buy_one_get_one"),
        "cpg_coupon": on_sale_ind.get("cpg_coupon"),
        "item_promotions": price_vs.get("itemPromotions") or [],
        # ── Availability ──────────────────────────────────────────────────────
        "available": avail.get("available"),
        "stock_level": avail.get("stockLevel"),
        "ebt_eligible": raw.get("itemEbt"),
        # ── Quantity / sold-by ────────────────────────────────────────────────
        "quantity_type": qty.get("quantityType"),
        "quantity_max": qty.get("max"),
        # ── Image ─────────────────────────────────────────────────────────────
        "image_url": image.get("url"),
        # ── Dietary / nutrition ───────────────────────────────────────────────
        "tags": raw.get("tags") or [],
        "dietary_tags": dietary.get("mlShoppingAttributes") or [],
        "dietary_badges": [
            s["attributeString"]
            for s in (dietary_vs.get("attributeSections") or [])
            if s.get("attributeString")
        ],
        "nutrition_summary": nutrition_summary,
        # ── Variants ──────────────────────────────────────────────────────────
        "variant_group_id": raw.get("variantGroupId"),
        "variant_dimension_values": raw.get("variantDimensionValues") or [],
        # ── Store-specific codes (populated for produce/deli; null for CPG) ──
        "retailer_reference_code": item_vs.get("retailerReferenceCodeString"),
        "retailer_lookup_code": item_vs.get("retailerLookupCodeString"),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch all Aldi search results for a given store and query term."
    )
    parser.add_argument(
        "--store", required=True,
        help="location_code from data/aldi_store_registry.jsonl  (e.g. 444-089)"
    )
    parser.add_argument(
        "--query", required=True,
        help="Search term  (e.g. 'milk')"
    )
    parser.add_argument(
        "--first", type=int, default=200,
        help=(
            "Number of items to inline-hydrate in the SearchResultsPlacements call "
            "(default: 200). Items beyond this count are fetched via a follow-up "
            "Items call. Increase if you see a large overflow count."
        ),
    )
    args = parser.parse_args()

    # ── Load store from registry ──────────────────────────────────────────────
    print(f"Loading store {args.store!r} from registry...")
    try:
        store = load_store(args.store)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    shop_id = (store.get("instacart_shops") or {}).get("delivery")
    if not shop_id:
        print(
            f"ERROR: store {args.store!r} has no delivery shopId. "
            "Check instacart_shops in the registry record.",
            file=sys.stderr,
        )
        return 1

    zip_code = store.get("zip", "10001")
    print(
        f"  location_code={args.store}  shop_id={shop_id}  zip={zip_code}"
        f"  name={store.get('instacart_location_name')}"
    )

    # ── Seed Instacart session ────────────────────────────────────────────────
    print("Seeding Instacart session...")
    try:
        session = seed_aldi_session()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("  Session seeded OK.")

    # ── Phase 1: SearchResultsPlacements ─────────────────────────────────────
    page_view_id = str(uuid.uuid4())
    search_url = _build_search_url(shop_id, zip_code, args.query, args.first, page_view_id)
    referer_headers = {"referer": f"https://www.aldi.us/store/aldi/s?k={args.query}"}

    print(f"Fetching SearchResultsPlacements  query={args.query!r}  first={args.first}...")
    try:
        search_response = _graphql_get(
            session,
            search_url,
            "SearchResultsPlacements",
        )
        # inject referer into subsequent calls on the same session
        session.headers.update(referer_headers)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    inline_items, overflow_ids = extract_search_results(search_response)
    total_found = len(inline_items) + len(overflow_ids)
    print(f"  Total results found: {total_found}")
    print(f"  Inline-hydrated: {len(inline_items)}")
    print(f"  Overflow (need Items call): {len(overflow_ids)}")

    if total_found >= args.first:
        print(
            f"  WARNING: result count ({total_found}) >= --first ({args.first}). "
            "There may be additional results. Re-run with a larger --first value."
        )

    # ── Phase 2: Items batch-fetch for overflow ───────────────────────────────
    hydrated: list[dict] = list(inline_items)
    if overflow_ids:
        batches = [
            overflow_ids[i: i + ITEMS_BATCH_SIZE]
            for i in range(0, len(overflow_ids), ITEMS_BATCH_SIZE)
        ]
        print(f"Fetching {len(overflow_ids)} overflow items in {len(batches)} batch(es)...")
        for i, batch in enumerate(batches, 1):
            items_url = _build_items_url(batch, shop_id, zip_code)
            try:
                items_response = _graphql_get(
                    session, items_url, f"Items batch {i}/{len(batches)}"
                )
            except RuntimeError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1

            batch_items = (items_response.get("data") or {}).get("items") or []
            if len(batch_items) != len(batch):
                print(
                    f"  WARNING: requested {len(batch)} items, "
                    f"got {len(batch_items)} in batch {i}"
                )
            hydrated.extend(batch_items)
            print(f"  Batch {i}/{len(batches)}: {len(batch_items)} items fetched")

    # ── Flatten and write output ──────────────────────────────────────────────
    flat_items = [flatten_item(it) for it in hydrated]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_query = args.query.lower().replace(" ", "_")[:30]
    output_filename = f"aldi_search_{args.store}_{safe_query}_{timestamp}.json"
    output_path = DATA_DIR / output_filename

    output = {
        "meta": {
            "location_code": args.store,
            "shop_id": shop_id,
            "query": args.query,
            "fetched_at": timestamp,
            "item_count": len(flat_items),
            "inline_count": len(inline_items),
            "overflow_count": len(overflow_ids),
            "first_param": args.first,
        },
        "items": flat_items,
    }

    DATA_DIR.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\nDone. {len(flat_items)} items written to {output_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
