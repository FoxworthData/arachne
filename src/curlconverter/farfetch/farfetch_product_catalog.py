#!/usr/bin/env python3
import argparse
import csv
import json
import sys
import time
from typing import Dict, Iterable, List, Optional

import httpx


LISTING_WARMUP_URL_TMPL = (
    # Any listing URL that corresponds to the categories you’re querying.
    # This just helps us obtain cookies + CSRF before hitting GraphQL.
    # Example (women bags): /shopping/women/bags-purses-1/items.aspx
    "https://www.farfetch.com/shopping/women/bags-purses-1/items.aspx"
)

GQL_ENDPOINT = "https://www.farfetch.com/experience-gateway"

# Minimal, stable selection set focused on core listing data.
# (Matches the structure you captured: ProductCatalog -> edges -> node -> fragments/fields)
PRODUCT_CATALOG_QUERY = r"""
query ProductCatalog(
  $input: ProductCatalogSearchInput!,
  $first: Int,
  $after: String,
  $isDesktop: Boolean!,
  $isMobile: Boolean!,
  $includeEdges: Boolean!,
  $includePageInfo: Boolean!
) {
  productCatalog(input: $input, first: $first, after: $after) {
    ... on ProductCatalogConnection {
      edges @include(if: $includeEdges) {
        cursor
        node {
          id
          resourceIdentifier { path __typename }
          brand { id name __typename }
          shortDescription
          label
          merchantId
          promotion { label __typename }
          stockQuantity
          rankingAlgorithm
          price {
            __typename
            value { raw formatted __typename }
            currency { isoCode symbol __typename }
          }
          productPrice {
            final { value { raw formatted __typename } type __typename }
            full { value { raw formatted __typename } __typename }
            currency { isoCode symbol __typename }
          }
          variationProperties {
            __typename
            ... on ProductCatalogItemColorVariationProperty {
              values { id swatchImage { size54 { url alt __typename } __typename } __typename }
            }
            ... on ProductCatalogItemSizeVariationProperty {
              values { id description __typename }
            }
            ... on ProductCatalogItemScaledSizeVariationProperty {
              values { id description __typename }
            }
          }
          images {
            order
            size480 @include(if: $isDesktop) { url alt __typename }
            size300 @include(if: $isMobile) { url alt __typename }
            __typename
          }
          visualizationExperience { isForMembers __typename }
          tags { id __typename }
          externalTriggers { type uri __typename }
          __typename
        }
        __typename
      }
      pageInfo @include(if: $includePageInfo) {
        hasNextPage
        endCursor
        __typename
      }
      __typename
    }
    ... on Error { message __typename }
  }
}
""".strip()

def build_variables(
    categories,
    first,
    after,
    price_type,
    sort_option,
    sort_order,
    is_desktop,
):
    return {
        "input": {
            "contextFilter": {
                "categories": categories,
                "priceType": price_type,
            },
            "filter": {},
            "negativeFilter": {},
            "sortFilter": {"option": sort_option, "order": sort_order},
        },
        "first": first,
        "after": after,
        "isDesktop": is_desktop,
        "isMobile": not is_desktop,
        "includeEdges": True,
        "includePageInfo": True,
    }

def get_csrf_from_cookies(cookies):
    """
    Return (header_name, token_value) for a CSRF cookie if present.
    We mirror the cookie name as the header name (Farfetch expects this).
    """
    candidates = [
        "__Host-CSRF-REQUEST-TOKEN",
        "__Secure-CSRF-REQUEST-TOKEN",
        "__Host-CSRF-TOKEN",
        "__Host-CSRF",
    ]
    for name in candidates:
        val = cookies.get(name)
        if val:
            return name, val
    return None, None

def default_headers(referer: str = "https://www.farfetch.com/") -> Dict[str, str]:
    # A realistic browser-like header set (pared down).
    return {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://www.farfetch.com",
        "referer": referer,             # <-- use the real listing page
        "x-client-flow": "async",  # seen in your capture
        "x-ff-gql-c": "true",      # seen in your capture on some calls
        "x-subfolder": "/",        # seen in your capture
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        ),
    }


def warmup_session(client: httpx.Client, listing_url: str) -> None:
    # Hit a listing page to receive cookies/session/CSRF like in-browser.
    resp = client.get(listing_url, timeout=30)
    resp.raise_for_status()


def gql_request(client, variables, csrf_tuple_or_str, retries: int = 3, backoff: float = 1.5):
    # Normalize CSRF input
    csrf_header_name = None
    csrf_value = None
    if isinstance(csrf_tuple_or_str, tuple):
        csrf_header_name, csrf_value = csrf_tuple_or_str
    elif isinstance(csrf_tuple_or_str, str):
        # If you pass just the token string (like your current run), assume the common header name.
        csrf_header_name, csrf_value = "__Host-CSRF-REQUEST-TOKEN", csrf_tuple_or_str

    payload = {
        "operationName": "ProductCatalog",
        "variables": variables,
        "query": PRODUCT_CATALOG_QUERY,
    }

    headers = default_headers().copy()
    if csrf_value:
        if csrf_header_name:
            headers[csrf_header_name] = csrf_value
        # Helpful fallback used by some gateways
        headers.setdefault("x-csrf-token", csrf_value)

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = client.post(GQL_ENDPOINT, json=payload, headers=headers, timeout=45)
            if resp.status_code >= 400:
                # print body for diagnostics
                sys.stderr.write(f"[HTTP {resp.status_code}] {resp.text[:8000]}\n")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoff ** attempt)
            else:
                raise

def iter_products(
    client: httpx.Client,
    categories: List[str],
    first: int,
    max_pages: int,
    price_type: str,
    sort_option: str,
    sort_order: str,
    listing_url: str,
) -> Iterable[Dict]:
    warmup_session(client, listing_url)
    csrf_tuple = get_csrf_from_cookies(client.cookies)  # <-- tuple (name, value) or (None, None)

    after = None
    pages = 0

    while True:
        variables = build_variables(
            categories=categories,
            first=first,
            after=after,
            price_type=price_type,
            sort_option=sort_option,
            sort_order=sort_order,
            is_desktop=True,
        )
        data = gql_request(client, variables, csrf_tuple)

        # GraphQL errors?
        if "errors" in data and data["errors"]:
            raise RuntimeError(f"GraphQL errors: {data['errors']}")

        pc = data.get("data", {}).get("productCatalog")
        if not pc:
            break

        # Connection case
        edges = pc.get("edges") or []
        for edge in edges:
            node = (edge or {}).get("node") or {}
            yield node

        page_info = pc.get("pageInfo") or {}
        has_next = page_info.get("hasNextPage", False)
        after = page_info.get("endCursor")

        pages += 1
        if not has_next or pages >= max_pages:
            break


def select_fields(node: Dict) -> Dict:
    # Map out a few useful fields from each product node
    rid = (node.get("resourceIdentifier") or {})
    path = rid.get("path")
    brand = (node.get("brand") or {}).get("name")
    price_final = (
        ((node.get("productPrice") or {}).get("final") or {}).get("value") or {}
    )
    price_full = (
        ((node.get("productPrice") or {}).get("full") or {}).get("value") or {}
    )
    currency = (node.get("productPrice") or {}).get("currency") or {}
    image = None
    images = node.get("images") or []
    if images:
        # Prefer desktop size if present
        img = images[0]
        image = ((img.get("size480") or {}) or {}).get("url") or ((img.get("size300") or {}) or {}).get("url")

    return {
        "id": node.get("id"),
        "brand": brand,
        "label": node.get("label"),
        "shortDescription": node.get("shortDescription"),
        "merchantId": node.get("merchantId"),
        "stockQuantity": node.get("stockQuantity"),
        "product_url": f"https://www.farfetch.com{path}" if path else None,
        "price_final_raw": price_final.get("raw"),
        "price_full_raw": price_full.get("raw"),
        "currency": currency.get("isoCode"),
        "image_url": image,
    }


def main():
    ap = argparse.ArgumentParser(description="Fetch product listings from Farfetch ProductCatalog GraphQL.")
    ap.add_argument(
        "--categories",
        nargs="+",
        required=True,
        help="Category IDs (e.g. 141258 135971)",
    )
    ap.add_argument(
        "--first",
        type=int,
        default=96,
        help="Page size (default: 96)",
    )
    ap.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="Max number of pages to fetch (default: 1)",
    )
    ap.add_argument(
        "--price-type",
        default="FULL",
        help='Price type (default: "FULL")',
    )
    ap.add_argument(
        "--sort-option",
        default="RANKING",
        help='Sort option (e.g. "RANKING", "PRICE", "NEW_IN"; default: "RANKING")',
    )
    ap.add_argument(
        "--sort-order",
        default="ASC",
        choices=["ASC", "DESC"],
        help='Sort order (default: "ASC")',
    )
    ap.add_argument(
        "--listing-url",
        default=LISTING_WARMUP_URL_TMPL,
        help="Listing URL to warm up cookies/CSRF (default: women/bags listing).",
    )
    ap.add_argument(
        "--output",
        default="-",
        help="Output path for JSONL or CSV (default: stdout).",
    )
    ap.add_argument(
        "--format",
        choices=["jsonl", "csv"],
        default="jsonl",
        help="Output format (default: jsonl).",
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-request timeout seconds (default: 30).",
    )
    args = ap.parse_args()

    client = httpx.Client(
        headers=default_headers(referer=args.listing_url),
        timeout=args.timeout,
        follow_redirects=True,
    )

    try:
        rows = []
        for node in iter_products(
            client=client,
            categories=args.categories,
            first=args.first,
            max_pages=args.max_pages,
            price_type=args.price_type,
            sort_option=args.sort_option,
            sort_order=args.sort_order,
            listing_url=args.listing_url,
        ):
            rows.append(select_fields(node))

        if args.format == "jsonl":
            out = sys.stdout if args.output == "-" else open(args.output, "w", encoding="utf-8")
            try:
                for r in rows:
                    out.write(json.dumps(r, ensure_ascii=False) + "\n")
            finally:
                if out is not sys.stdout:
                    out.close()
        else:
            # CSV
            if rows:
                fieldnames = list(rows[0].keys())
            else:
                fieldnames = [
                    "id", "brand", "label", "shortDescription", "merchantId",
                    "stockQuantity", "product_url", "price_final_raw",
                    "price_full_raw", "currency", "image_url"
                ]
            out = sys.stdout if args.output == "-" else open(args.output, "w", newline="", encoding="utf-8")
            try:
                w = csv.DictWriter(out, fieldnames=fieldnames)
                w.writeheader()
                for r in rows:
                    w.writerow(r)
            finally:
                if out is not sys.stdout:
                    out.close()

    finally:
        client.close()


if __name__ == "__main__":
    main()