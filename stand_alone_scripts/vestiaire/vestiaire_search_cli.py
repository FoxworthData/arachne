#!/usr/bin/env python3
"""
vestiaire_search_cli.py
A small CLI to query Vestiaire Collective's product search endpoint.
- Supports keyword queries, category links, basic filters, pagination, and JSON dumps.
- Uses httpx with retry/backoff and generates per-run device/query/session IDs.
"""

import argparse
import json
import sys
import time
import uuid
from typing import Dict, Any, List, Optional

import httpx

ENDPOINT = "https://search.vestiairecollective.com/v1/product/search"

DEFAULT_FIELDS = [
    "name","description","brand","model","country","price","discount","link","sold",
    "likes","editorPicks","shouldBeGone","seller","directShipping","local","pictures",
    "colors","size","stock","universeId","createdAt","dutyFree"
]

DEFAULT_FACET_FIELDS = [
    "brand","universe","country","stock","color","categoryLvl0","priceRange","price",
    "condition","region","editorPicks","watchMechanism","discount","sold",
    "directShippingEligible","directShippingCountries","localCountries","sellerBadge",
    "isOfficialStore","materialLvl0",
    # A bunch of size facets are exposed by the site; keep the common ones small by default
    "size0","size1","size2","size3","size4","size5","size6","size7","size8","size9"
]

def make_headers(origin: str) -> Dict[str, str]:
    device_id = str(uuid.uuid4())
    query_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "origin": origin,
        "referer": origin + "/",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36",
        # Vestiaire uses these to track a search session; UUIDs work fine for public searches
        "x-deviceid": device_id,
        "x-search-query-id": query_id,
        "x-search-session-id": session_id,
        "x-use-case": "plpStandard",
        # "x-userid": ""  # intentionally omitted for anon
    }

def build_filters(args: argparse.Namespace) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}

    # Universe/category defaults roughly mirror "Women > Bags"
    if args.universe_id:
        filters.setdefault("universe.id", [str(args.universe_id)])
    if args.category0_id:
        filters.setdefault("categoryLvl0.id", [str(args.category0_id)])

    # Support the URL-style catalog link filter Vestiaire uses
    if args.category_link:
        filters.setdefault("catalogLinksWithoutLanguage", [args.category_link])

    # Optional simple filters
    if args.brands:
        filters.setdefault("brand", list(args.brands))

    # Price: API supports "price" facet; use a "priceRange" expression when provided.
    price_range = []
    if args.min_price is not None:
        price_range.append({"gte": args.min_price})
    if args.max_price is not None:
        if price_range:
            price_range[0]["lte"] = args.max_price
        else:
            price_range.append({"lte": args.max_price})
    if price_range:
        filters["priceRange"] = price_range

    if args.condition:
        # conditions appear as strings on site (e.g., "Very good", "Good", "Excellent")
        filters["condition"] = [args.condition]

    return filters

def build_payload(args: argparse.Namespace, offset: int) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "pagination": {"offset": offset, "limit": args.limit},
        "fields": DEFAULT_FIELDS if not args.fields else args.fields,
        "facets": {"fields": DEFAULT_FACET_FIELDS, "stats": ["price"]},
        "q": args.q if args.q else None,
        "sortBy": args.sort_by,
        "filters": build_filters(args),
        "locale": {
            "country": args.country,
            "currency": args.currency,
            "language": args.language,
            "sizeType": args.size_type,
        },
        "mySizes": None,
        "options": {
            "innerFeedContext": "genericPLP",
            "disableHierarchicalParentFiltering": True,
            "enableGuidedSearch": True,
        },
        "recentlyViewedProductIDs": [],
    }
    return payload

def request_with_retries(client: httpx.Client, url: str, json_body: Dict[str, Any], max_retries: int = 3, timeout: float = 20.0) -> httpx.Response:
    backoff = 1.0
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.post(url, json=json_body, timeout=timeout)
            if resp.status_code >= 500:
                # transient server error
                raise httpx.HTTPStatusError(f"Server error: {resp.status_code}", request=resp.request, response=resp)
            return resp
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(backoff)
                backoff *= 2
            else:
                raise
    # Should never hit here
    assert last_exc
    raise last_exc

def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Query Vestiaire Collective product search.")
    p.add_argument("--q", help="Keyword query (e.g., 'Chanel Classic Flap').")
    p.add_argument("--category-link", default="/women-bags/", help="Catalog link path such as '/women-bags/' (url language-less form).")
    p.add_argument("--universe-id", type=int, default=1, help="Universe ID (1=Women, 2=Men, etc.)")
    p.add_argument("--category0-id", type=int, default=5, help="Top-level category ID (e.g., 5=Bags).")
    p.add_argument("--brands", nargs="*", help="One or more brand names to filter (exact match as on site).")
    p.add_argument("--min-price", type=float, help="Minimum price (in currency).")
    p.add_argument("--max-price", type=float, help="Maximum price (in currency).")
    p.add_argument("--condition", help="Condition filter (e.g., 'Very good', 'Excellent', 'Good').")

    p.add_argument("--limit", type=int, default=60, help="Results per page (API default shown in captures is 60).")
    p.add_argument("--max-pages", type=int, default=1, help="How many pages to fetch (paginates using offset).")
    p.add_argument("--sort-by", default="relevance", help="Sort mode (e.g., 'relevance', 'priceAsc', 'priceDesc', etc.)")

    p.add_argument("--country", default="US")
    p.add_argument("--currency", default="USD")
    p.add_argument("--language", default="us")
    p.add_argument("--size-type", default="US")
    p.add_argument("--origin", default="https://us.vestiairecollective.com", help="Origin/referer base (controls region).")

    p.add_argument("--fields", nargs="*", help="Override default fields (advanced).")
    p.add_argument("--dump-json", help="Write raw JSON response(s) to this file.")
    p.add_argument("--print", dest="do_print", action="store_true", help="Pretty-print a summary of results to stdout.")
    return p.parse_args(argv)

def summarize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    summary = []
    for it in items:
        summary.append({
            "name": it.get("name"),
            "brand": it.get("brand"),
            "price": it.get("price"),
            "link": it.get("link"),
            "createdAt": it.get("createdAt"),
            "stock": it.get("stock"),
        })
    return summary

def main(argv: List[str]) -> int:
    args = parse_args(argv)
    headers = make_headers(args.origin)

    all_items: List[Dict[str, Any]] = []
    dump_blocks: List[Dict[str, Any]] = []

    with httpx.Client(headers=headers) as client:
        for page in range(args.max_pages):
            offset = page * args.limit
            payload = build_payload(args, offset=offset)
            resp = request_with_retries(client, ENDPOINT, payload)
            if resp.status_code != 200:
                sys.stderr.write(f"[!] Non-200 response {resp.status_code}: {resp.text[:300]}\\n")
                return 2

            data = resp.json()
            dump_blocks.append(data)

            items = data.get("data") or data.get("items") or data.get("results") or []
            if not isinstance(items, list):
                # Some APIs wrap results differently; try common paths
                items = data.get("products") or []
            if not items:
                if page == 0:
                    print("No items found.")
                break

            all_items.extend(items)

            # Stop early if the page returned fewer than limit (likely end of results)
            if len(items) < args.limit:
                break

    if args.dump_json:
        try:
            with open(args.dump_json, "w", encoding="utf-8") as f:
                json.dump(dump_blocks if args.max_pages > 1 else dump_blocks[0], f, ensure_ascii=False, indent=2)
            print(f"Wrote raw JSON to {args.dump_json}")
        except Exception as e:
            sys.stderr.write(f"[!] Failed to write JSON: {e}\\n")

    if args.do_print:
        # Print a compact summary to stdout
        for i, s in enumerate(summarize_items(all_items), start=1):
            price = s["price"]
            # handle dict or primitive price structures
            if isinstance(price, dict) and "value" in price and "currency" in price:
                price_str = f'{price.get("value")} {price.get("currency")}'
            else:
                price_str = str(price)
            print(f'{i:>4}. {s["brand"] or ""} — {s["name"] or ""} — {price_str} — {s["link"] or ""}')

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
