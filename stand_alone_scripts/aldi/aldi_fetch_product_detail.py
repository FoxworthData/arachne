"""Aldi product detail fetcher — calls ItemDetailData and ProductNutritionalInfo
for a given item ID to retrieve description, ingredients, directions, warnings,
product images, and full nutrition facts.

Operations:
  ItemDetailData      — description, ingredients, warnings, directions, multi-image
  ProductNutritionalInfo — full nutrition panel (calories, macros, %DV, etc.)

Usage:
    # Single item (ad hoc / dev):
    venv/bin/python3 stand_alone_scripts/aldi/aldi_fetch_product_detail.py \\
        --item-id items_14655-36953 \\
        --shop-id 339

    # Batch from a search result file (direct pipeline):
    venv/bin/python3 stand_alone_scripts/aldi/aldi_fetch_product_detail.py \\
        --from-search "stand_alone_scripts/aldi/data/aldi_search_444-089_milk_*.json"

    # Batch from an items JSONL file (production / DB-driven pattern):
    #   Each line: {"item_id": "items_396446-16902710", "shop_id": "606700"}
    venv/bin/python3 stand_alone_scripts/aldi/aldi_fetch_product_detail.py \\
        --from-items-file stand_alone_scripts/aldi/data/items_to_enrich.jsonl

Input file formats:
    --from-search   : JSON file produced by aldi_search.py (contains meta.shop_id)
    --from-items-file: JSONL file, one record per line: {"item_id": "...", "shop_id": "..."}
                       This is the interface a production DB would generate when exporting
                       items that need initial enrichment or a periodic refresh.

Output:
    stand_alone_scripts/aldi/data/aldi_detail_{item_id}_{timestamp}.json   (single)
    stand_alone_scripts/aldi/data/aldi_detail_batch_{n}items_{timestamp}.json  (batch)
"""

import argparse
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).parent))
from aldi_session_seeder import seed_aldi_session

GRAPHQL_URL = "https://www.aldi.us/graphql"

# Confirmed hashes extracted from SSR apollo-state, April 2026
ITEM_DETAIL_DATA_HASH = "1498d8c45b80c63ada20d2a07c07bde2364a3c69e1252ed3dfd6a095c2f2e4c8"
NUTRITIONAL_INFO_HASH = "9bc43a13c48e633ba4c8016118f101942a44603c5d10f913e9e471ffb730185a"

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data" / "runs"

_GRAPHQL_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
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
}


# ─── GraphQL helpers ─────────────────────────────────────────────────────────

def _graphql_get(session, operation: str, variables: dict, sha256hash: str) -> dict:
    params = urlencode({
        "operationName": operation,
        "variables": json.dumps(variables, separators=(",", ":")),
        "extensions": json.dumps(
            {"persistedQuery": {"version": 1, "sha256Hash": sha256hash}},
            separators=(",", ":"),
        ),
    })
    url = f"{GRAPHQL_URL}?{params}"
    r = session.get(url, headers=_GRAPHQL_HEADERS, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"{operation} HTTP {r.status_code}: {r.text[:200]}")
    body = r.json()
    if "errors" in body:
        raise RuntimeError(f"{operation} GraphQL errors: {body['errors']}")
    return body["data"]


# ─── Data extractors ─────────────────────────────────────────────────────────

def fetch_item_detail(session, item_id: str, shop_id: str) -> dict:
    """Fetch ItemDetailData — description, ingredients, warnings, directions, images."""
    variables = {"id": item_id, "isFeatured": False, "shopId": shop_id}
    data = _graphql_get(session, "ItemDetailData", variables, ITEM_DETAIL_DATA_HASH)
    vs = data["itemDetail"]["viewSection"]

    # Extract detail sections (Details/description, Ingredients, Warnings, Directions)
    sections = {}
    for s in vs.get("detailSections") or []:
        header = s.get("headerString", "").lower()
        body = s.get("bodyString") or ""
        sections[header] = body

    # productDetailSections has a sectionTypeVariant field for reliable keying
    product_sections = {}
    for s in vs.get("productDetailSections") or []:
        variant = s.get("sectionTypeVariant", "").lower()
        body = s.get("bodyString") or ""
        if variant:
            product_sections[variant] = body

    # Multiple product images
    images = [
        {"url": img["url"], "alt_text": img.get("altText")}
        for img in (vs.get("detailImages") or [])
    ]

    # Warnings also appear at top level in warningSection
    warning_body = None
    ws = vs.get("warningSection")
    if ws:
        warning_body = ws.get("bodyString")

    return {
        "description": product_sections.get("details") or sections.get("details"),
        "ingredients": product_sections.get("ingredients") or sections.get("ingredients"),
        "directions": product_sections.get("directions") or sections.get("directions"),
        "warnings": warning_body or sections.get("warnings"),
        "images": images,
    }


def fetch_nutritional_info(session, product_id: str, shop_id: str) -> dict | None:
    """Fetch ProductNutritionalInfo — full nutrition panel. Returns None if unavailable."""
    variables = {"productId": product_id, "shopId": shop_id}
    try:
        data = _graphql_get(session, "ProductNutritionalInfo", variables, NUTRITIONAL_INFO_HASH)
    except RuntimeError:
        return None

    ni = (data.get("productNutritionalInfo") or {}).get("nutritionalInfo")
    if not ni:
        return None

    # Flatten scalar fields; skip viewSection (display strings) and __typename
    nutrition = {}
    for k, v in ni.items():
        if k.startswith("__") or k == "viewSection":
            continue
        nutrition[k] = v

    # Also pull the formatted display strings from viewSection if present
    vs = ni.get("viewSection") or {}
    display = {}
    for k, v in vs.items():
        if k.startswith("__"):
            continue
        if isinstance(v, str) and v:
            display[k] = v

    nutrition["display"] = display if display else None
    return nutrition


# ─── Product ID extraction ────────────────────────────────────────────────────

def product_id_from_item_id(item_id: str) -> str:
    """Extract bare product_id from 'items_14655-36953' → '36953'."""
    return item_id.split("-", 1)[-1]


# ─── Output flattener ─────────────────────────────────────────────────────────

def build_full_detail(item_id: str, shop_id: str, detail: dict, nutrition: dict | None) -> dict:
    return {
        "item_id": item_id,
        "product_id": product_id_from_item_id(item_id),
        "shop_id": shop_id,
        "description": detail["description"],
        "ingredients": detail["ingredients"],
        "directions": detail["directions"],
        "warnings": detail["warnings"],
        "images": detail["images"],
        "nutrition": nutrition,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Fetch full product detail from Aldi/Instacart API")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--item-id", help="Single item ID, e.g. items_14655-36953")
    src.add_argument(
        "--from-search",
        metavar="GLOB",
        help="Glob path to a search result JSON file (aldi_search.py output); fetches detail for all items",
    )
    src.add_argument(
        "--from-items-file",
        metavar="JSONL_FILE",
        help=(
            "Path to a JSONL file where each line is {\"item_id\": \"...\", \"shop_id\": \"...\"}. "
            "This is the production/DB-driven pattern for enriching or refreshing specific items."
        ),
    )
    p.add_argument("--shop-id", default=None, help="Instacart shopId (required with --item-id)")
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max items to process (useful for large batches)",
    )
    return p.parse_args()


def main():
    args = parse_args()

    # Build work list: [(item_id, shop_id), ...]
    work: list[tuple[str, str]] = []

    if args.item_id:
        if not args.shop_id:
            print("ERROR: --shop-id is required when using --item-id", file=sys.stderr)
            sys.exit(1)
        work.append((args.item_id, args.shop_id))

    elif args.from_search:
        # Direct pipeline: enrich all items from a search result file
        files = sorted(glob.glob(args.from_search))
        if not files:
            print(f"ERROR: no files matched {args.from_search!r}", file=sys.stderr)
            sys.exit(1)
        search_file = files[-1]
        print(f"Loading search results from {search_file}")
        search_data = json.loads(Path(search_file).read_text())
        # Support both 'meta' (aldi_search.py output) and 'metadata' key names
        meta = search_data.get("meta") or search_data.get("metadata") or {}
        shop_id = meta["shop_id"]
        items = search_data["items"]
        if args.limit:
            items = items[: args.limit]
        for it in items:
            work.append((it["id"], shop_id))

    elif args.from_items_file:
        # Production / DB-driven pattern: JSONL of {item_id, shop_id}
        items_path = Path(args.from_items_file)
        if not items_path.exists():
            print(f"ERROR: file not found: {items_path}", file=sys.stderr)
            sys.exit(1)
        print(f"Loading items from {items_path}")
        for line in items_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            work.append((record["item_id"], record["shop_id"]))
        if args.limit:
            work = work[: args.limit]

    print(f"Fetching detail for {len(work)} item(s)…")

    session = seed_aldi_session()
    results = []

    for i, (item_id, shop_id) in enumerate(work, 1):
        product_id = product_id_from_item_id(item_id)
        print(f"  [{i}/{len(work)}] {item_id}", end="", flush=True)
        try:
            detail = fetch_item_detail(session, item_id, shop_id)
            nutrition = fetch_nutritional_info(session, product_id, shop_id)
            record = build_full_detail(item_id, shop_id, detail, nutrition)
            results.append(record)
            has_desc = "✓" if detail["description"] else "✗"
            has_ing = "✓" if detail["ingredients"] else "✗"
            has_nut = "✓" if nutrition else "✗"
            print(f"  desc={has_desc} ing={has_ing} nutrition={has_nut}")
        except RuntimeError as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            results.append({"item_id": item_id, "product_id": product_id, "error": str(e)})

    # Write output
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if len(work) == 1:
        slug = work[0][0].replace("items_", "").replace("-", "_")
        out_file = DATA_DIR / f"aldi_detail_{slug}_{timestamp}.json"
    else:
        out_file = DATA_DIR / f"aldi_detail_batch_{len(work)}items_{timestamp}.json"

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": {
            "fetched_at": timestamp,
            "item_count": len(results),
        },
        "items": results,
    }
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nWrote {len(results)} records to {out_file}")


if __name__ == "__main__":
    main()
