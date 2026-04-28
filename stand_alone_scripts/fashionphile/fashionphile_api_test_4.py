#!/usr/bin/env python3
import argparse, httpx, json, urllib.parse, time, re, sys, unicodedata
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Optional

ALG_URL = "https://nsjaz0qg7k-dsn.algolia.net/1/indexes/*/queries"
HEADERS = {
    "content-type": "application/json",
    "accept": "application/json",
    "x-algolia-application-id": "NSJAZ0QG7K",
    "x-algolia-api-key": "f26f1dfb62b97a9c1002bbae62a9f7e1",  # public search key from your capture
    "origin": "https://www.fashionphile.com",
    "referer": "https://www.fashionphile.com/",
}
INDEX = "prod_ecom_products_date_desc"

# ---------- helpers ----------
def slugify(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s

def build_base_params(hits_per_page: int, page: int = 0) -> str:
    # IMPORTANT: keep the original category filter encoding exactly as captured
    return (
        "clickAnalytics=true"
        "&facets=%5B%22*%22%5D"
        "&filters=%22categories_page_id%22%3A%20%22shoes%22"
        "&highlightPostTag=__%2Fais-highlight__"
        "&highlightPreTag=__ais-highlight__"
        "&maxValuesPerFacet=999"
        f"&hitsPerPage={hits_per_page}"
        f"&page={page}"
        "&query="
    )

def add_param(params_enc: str, key: str, value: str) -> str:
    q = urllib.parse.parse_qs(params_enc, keep_blank_values=True)
    q[key] = [value]
    return "&".join(f"{k}={v}" for k, vals in q.items() for v in vals)

def add_facet_filters(params_enc: str, facet_filters_json: str) -> str:
    q = urllib.parse.parse_qs(params_enc, keep_blank_values=True)
    q["facetFilters"] = [urllib.parse.quote(facet_filters_json, safe="")]
    return "&".join(f"{k}={v}" for k, vals in q.items() for v in vals)

def set_page(params_enc: str, page: int) -> str:
    return add_param(params_enc, "page", str(page))

def query(params_enc: str):
    body = {"requests": [{"indexName": INDEX, "params": params_enc}]}
    r = httpx.post(ALG_URL, headers=HEADERS, data=json.dumps(body), timeout=60)
    r.raise_for_status()
    return r.json()["results"][0]

# --- image normalization to prod-images/main ---
IMG_HOST = "https://prod-images.fashionphile.com"

def _to_main_image_url(rel_or_abs: Optional[str]) -> Optional[str]:
    if not rel_or_abs:
        return None
    if rel_or_abs.startswith("http"):
        rel_path = urlparse(rel_or_abs).path or ""
    else:
        rel_path = rel_or_abs
    if not rel_path.startswith("/"):
        rel_path = "/" + rel_path
    rel_path = re.sub(r"^/(tiny|thumb|main)/", "/main/", rel_path)
    return IMG_HOST + rel_path

def expand_images(hit: dict) -> List[str]:
    thumbs = sorted((hit.get("thumbnails") or []), key=lambda t: t.get("order", 0))
    urls = []
    for t in thumbs:
        rel = t.get("path") or t.get("thumb") or t.get("tiny")
        url = _to_main_image_url(rel)
        if url:
            urls.append(url)
    out, seen = [], set()
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def build_product_url(hit: dict) -> Optional[str]:
    oid = str(hit.get("objectID") or hit.get("id") or "").strip()
    if not oid:
        return None
    title = (hit.get("title") or hit.get("title_without_brand") or "").strip()
    filters = hit.get("filters") or {}
    brand = None
    brands = filters.get("brands")
    if isinstance(brands, list) and brands:
        brand = brands[0]
    elif isinstance(brands, str):
        brand = brands
    if title and brand and (hit.get("title_without_brand") and hit["title_without_brand"].strip()):
        slug_source = f"{brand} {hit['title_without_brand']}"
    else:
        slug_source = title or (f"{brand} {oid}" if brand else oid)
    slug = slugify(slug_source)
    return f"https://www.fashionphile.com/p/{slug}-{oid}"

def collapse(v):
    return v[0] if isinstance(v, list) and len(v) == 1 else v

def normalize_hit(hit: dict) -> dict:
    f = hit.get("filters") or {}
    return {
        "id": hit.get("objectID") or hit.get("id"),
        "title": hit.get("title") or hit.get("title_without_brand"),
        "brand": collapse(f.get("brands")),
        "category": collapse(f.get("shoes") or f.get("accessories")),
        "color": collapse(f.get("color")),
        "material": collapse(f.get("material")),
        "size": collapse(f.get("shoe_size")),
        "condition": collapse(f.get("condition")),
        "price": hit.get("discounted_price") or hit.get("price"),
        "price_bucket": f.get("price"),
        "location": collapse(f.get("locations")),
        "made_available_at": hit.get("made_available_at"),
        "priced_at": hit.get("priced_at"),
        "product_url": build_product_url(hit),
        "images": expand_images(hit),
    }

def build_facet_filters(
    brands: List[str],
    sizes: List[str],
    conditions: List[str],
    price_buckets: List[str],
    extra_facets: List[str],
) -> str:
    """
    Build Algolia facetFilters JSON.
    - Each inner list is OR within that facet;
    - Each top-level entry is AND across groups.
    Known facet keys from your index:
      filters.brands, filters.shoe_size, filters.condition, filters.price
    extra_facets: allow raw entries like 'filters.material:Patent Leather'
    """
    groups: List[List[str]] = []

    if brands:
        groups.append([f"filters.brands:{b}" for b in brands])
    if sizes:
        groups.append([f"filters.shoe_size:{s}" for s in sizes])
    if conditions:
        groups.append([f"filters.condition:{c}" for c in conditions])
    if price_buckets:
        groups.append([f"filters.price:{p}" for p in price_buckets])

    # extra facets allow power users to pass arbitrary key:value pairs
    # e.g. --facet filters.material:"Patent Leather" --facet filters.color:Black
    if extra_facets:
        # group all extra facets together as AND of ORs, per facet key
        # We'll bucket by facet key for proper OR behavior per key
        by_key = {}
        for entry in extra_facets:
            # expect "key:value"
            if ":" not in entry:
                continue
            k, v = entry.split(":", 1)
            k, v = k.strip(), v.strip()
            by_key.setdefault(k, []).append(f"{k}:{v}")
        for _, vals in by_key.items():
            groups.append(vals)

    return json.dumps(groups)

# ---------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser(
        description="Scrape Fashionphile 'Shoes' via Algolia, with optional facet filters."
    )
    p.add_argument("--brand", "-b", action="append", default=[],
                   help="Brand label exactly as in facets (repeatable). e.g. 'Christian Louboutin'")
    p.add_argument("--size", "-s", action="append", default=[],
                   help="Shoe size value exactly as in facets (repeatable). e.g. '37.5'")
    p.add_argument("--condition", "-c", action="append", default=[],
                   help="Condition label exactly as in facets (repeatable). e.g. 'Excellent'")
    p.add_argument("--price-bucket", "-p", action="append", default=[],
                   help="Price bucket label exactly as in facets (repeatable). e.g. '$500-$1000'")
    p.add_argument("--facet", action="append", default=[],
                   help="Extra facet as key:value (repeatable). e.g. 'filters.material:Patent Leather'")
    p.add_argument("--hits-per-page", type=int, default=120)
    p.add_argument("--page-delay", type=float, default=0.25)
    p.add_argument("--csv", action="store_true", default=True, help="Write CSV (default on).")
    p.add_argument("--no-csv", dest="csv", action="store_false")
    p.add_argument("--parquet", action="store_true", help="Also write Parquet (requires pyarrow/fastparquet).")
    p.add_argument("--output-stem", default="fashionphile_shoes")
    return p.parse_args()

# ---------- main ----------
def main():
    args = parse_args()

    # Start from exact captured params and inject dynamic hitsPerPage
    params = build_base_params(hits_per_page=args.hits_per_page, page=0)

    # Build facetFilters JSON from CLI args
    facet_filters_json = build_facet_filters(
        brands=args.brand,
        sizes=args.size,
        conditions=args.condition,
        price_buckets=args.price_bucket,
        extra_facets=args.facet,
    )
    params = add_facet_filters(params, facet_filters_json)

    # First page to discover nbPages
    res0 = query(params)
    nb_hits = res0.get("nbHits", 0)
    nb_pages = res0.get("nbPages", 0)
    page_hits = res0.get("hits", [])
    print(f"nbHits={nb_hits} nbPages={nb_pages} hits_on_page1={len(page_hits)}")

    if nb_hits == 0:
        facets = res0.get("facets", {}) or {}
        # Print a few helpful facets to correct spelling/casing
        for facet_key in ("filters.brands", "filters.shoe_size", "filters.condition", "filters.price"):
            vals = facets.get(facet_key) or {}
            if vals:
                top = sorted(vals.items(), key=lambda kv: kv[1], reverse=True)[:20]
                print(f"\nTop {facet_key} values:")
                for v, count in top:
                    print(f"  {v} -> {count}")
        sys.exit(0)

    # Collect all pages
    all_hits = list(page_hits)
    for page in range(1, nb_pages):
        time.sleep(args.page_delay)
        res = query(set_page(params, page))
        hits = res.get("hits", [])
        print(f"page {page+1}/{nb_pages} → {len(hits)} hits")
        all_hits.extend(hits)

    print("total_collected:", len(all_hits))

    # Preview a few
    for h in all_hits[:5]:
        f = h.get("filters") or {}
        print({
            "id": h.get("objectID"),
            "title": h.get("title") or h.get("title_without_brand"),
            "brand": f.get("brands"),
            "price": h.get("discounted_price") or h.get("price"),
            "condition": f.get("condition"),
            "url_candidate": build_product_url(h),
            "imgs": expand_images(h)[:2],
        })

    sample = all_hits[0]
    print(sorted(sample.keys()))

    # Normalize and optionally persist
    rows = [normalize_hit(h) for h in all_hits]

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    if args.csv or args.parquet:
        try:
            import pandas as pd
        except Exception as e:
            print("Skipping file writes (pandas not installed):", e)
            sys.exit(0)

        df = pd.DataFrame(rows)
        if args.csv:
            csv_path = f"{args.output_stem}_{ts}.csv"
            df.to_csv(csv_path, index=False)
            print("wrote CSV:", csv_path)
        if args.parquet:
            try:
                pq_path = f"{args.output_stem}_{ts}.parquet"
                df.to_parquet(pq_path, index=False)
                print("wrote Parquet:", pq_path)
            except Exception as e:
                print("Parquet write failed (install pyarrow or fastparquet):", e)

if __name__ == "__main__":
    main()

# •    Christian Louboutin only
# python fashionphile_api_test_4.py --brand "Christian Louboutin"

# 	•	Brand + size 37 or 37.5 + Excellent condition
# python fashionphile_api_test_4.py --brand "Christian Louboutin" --size 37 --size 37.5 --condition "Excellent"

# 	•	Add a price bucket (must match the facet label exactly, e.g. $500-$1000)
# python fashionphile_api_test_4.py --brand "Christian Louboutin" --price-bucket "$500-$1000"

# 	•	Add an extra facet (arbitrary key:value) like material
# python fashionphile_api_test_4.py --brand "Christian Louboutin" --facet 'filters.material:Patent Leather'

# 	•	Write Parquet too
# python fashionphile_api_test_4.py --brand "Christian Louboutin" --parquet