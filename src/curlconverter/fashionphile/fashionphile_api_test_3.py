import httpx, json, urllib.parse, time, re, sys, unicodedata
from datetime import datetime
from urllib.parse import urlparse

# --------------------
# Config (edit safely)
# --------------------
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

# Your exact working params (from your cURL, just changed hitsPerPage=120, page=0)
BASE_PARAMS = (
    "clickAnalytics=true"
    "&facets=%5B%22*%22%5D"
    "&filters=%22categories_page_id%22%3A%20%22shoes%22"
    "&highlightPostTag=__%2Fais-highlight__"
    "&highlightPreTag=__ais-highlight__"
    "&maxValuesPerFacet=999"
    "&hitsPerPage=120"
    "&page=0"
    "&query="
)

# Change this to target a different brand (use the exact label from facets['filters.brands'])
TARGET_BRAND = "Christian Louboutin"

# polite delay between pages
PAGE_DELAY_SEC = 0.25

# Output file stems (will add timestamp)
OUTPUT_STEM = "fashionphile_shoes"
WRITE_CSV = True
WRITE_PARQUET = False  # flip to True if you have pyarrow/fastparquet installed

# --------------------
# Helpers
# --------------------
def add_facet_filters(params_enc: str, facet_filters_json: str) -> str:
    """Keep the original 'filters' for category; add brand via facetFilters."""
    q = urllib.parse.parse_qs(params_enc, keep_blank_values=True)
    q["facetFilters"] = [urllib.parse.quote(facet_filters_json, safe="")]
    parts = []
    for k, vals in q.items():
        for v in vals:
            parts.append(f"{k}={v}")
    return "&".join(parts)

def set_page(params_enc: str, page: int) -> str:
    q = urllib.parse.parse_qs(params_enc, keep_blank_values=True)
    q["page"] = [str(page)]
    return "&".join(f"{k}={v}" for k, vals in q.items() for v in vals)

def query(params_enc: str):
    body = {"requests": [{"indexName": INDEX, "params": params_enc}]}
    r = httpx.post(ALG_URL, headers=HEADERS, data=json.dumps(body), timeout=60)
    r.raise_for_status()
    return r.json()["results"][0]

def slugify(s: str) -> str:
    # Normalize unicode → ASCII, lower, replace non-alphanum with hyphens, collapse repeats
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s

def build_product_url(hit: dict) -> str | None:
    """
    Fashionphile product URLs:
      https://www.fashionphile.com/p/<slug>-<id>
    where <slug> typically includes brand + title_without_brand (or full title).
    """
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
        # Fallback to title (already contains brand on many items)
        slug_source = title or (f"{brand} {oid}" if brand else oid)

    slug = slugify(slug_source)
    return f"https://www.fashionphile.com/p/{slug}-{oid}"

# --- image normalization to prod-images/main ---
IMG_HOST = "https://prod-images.fashionphile.com"

def _to_main_image_url(rel_or_abs: str | None) -> str | None:
    """
    Accepts a relative ('/thumb/...jpg') or absolute URL and
    returns a full 'https://prod-images.fashionphile.com/main/...jpg'.
    """
    if not rel_or_abs:
        return None

    # Extract the path
    if rel_or_abs.startswith("http"):
        rel_path = urlparse(rel_or_abs).path or ""
    else:
        rel_path = rel_or_abs

    if not rel_path.startswith("/"):
        rel_path = "/" + rel_path

    # Force first segment to /main/ (tiny/thumb/main -> main)
    rel_path = re.sub(r"^/(tiny|thumb|main)/", "/main/", rel_path)

    return IMG_HOST + rel_path

def expand_images(hit: dict) -> list[str]:
    """
    Build a list of 'main' image URLs from the thumbnails array.
    """
    thumbs = sorted((hit.get("thumbnails") or []), key=lambda t: t.get("order", 0))
    urls = []
    for t in thumbs:
        # Prefer 'path' → then 'thumb' → then 'tiny'
        rel = t.get("path") or t.get("thumb") or t.get("tiny")
        url = _to_main_image_url(rel)
        if url:
            urls.append(url)

    # Deduplicate, preserve order
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

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

# --------------------
# Main flow
# --------------------
if __name__ == "__main__":
    # 1) Add brand facet (using the exact facet key you discovered)
    facet_filters_json = json.dumps([[f"filters.brands:{TARGET_BRAND}"]])
    params_with_brand = add_facet_filters(BASE_PARAMS, facet_filters_json)

    # 2) First page to discover nbPages
    res0 = query(params_with_brand)
    nb_hits = res0.get("nbHits", 0)
    nb_pages = res0.get("nbPages", 0)
    page_hits = res0.get("hits", [])

    print(f"{TARGET_BRAND} — nbHits: {nb_hits}, nbPages: {nb_pages}, hits on page 1: {len(page_hits)}")

    # If brand label is off, show top facet values to help fix spelling/casing
    if nb_hits == 0:
        facets = res0.get("facets", {}) or {}
        brands = facets.get("filters.brands") or {}
        top_brands = sorted(brands.items(), key=lambda kv: kv[1], reverse=True)[:20]
        print("No hits. Top brand facet values (try one verbatim in TARGET_BRAND):")
        for b, count in top_brands:
            print(f"  {b} -> {count}")
        sys.exit(0)

    # 3) Collect all pages
    all_hits = list(page_hits)
    for page in range(1, nb_pages):
        time.sleep(PAGE_DELAY_SEC)
        res = query(set_page(params_with_brand, page))
        hits = res.get("hits", [])
        print(f"Page {page+1}/{nb_pages} → {len(hits)} hits")
        all_hits.extend(hits)

    print("Total collected:", len(all_hits))

    # 4) Preview a few
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

    # 5) Normalize and optionally persist
    rows = [normalize_hit(h) for h in all_hits]

    for h in all_hits[:3]:
        print(h.get("objectID"), "→", build_product_url(h))

    # Optional: write files
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    if WRITE_CSV or WRITE_PARQUET:
        try:
            import pandas as pd
        except Exception as e:
            print("Skipping file writes (pandas not installed):", e)
            sys.exit(0)

        df = pd.DataFrame(rows)
        if WRITE_CSV:
            csv_path = f"{OUTPUT_STEM}_{slugify(TARGET_BRAND)}_{ts}.csv"
            df.to_csv(csv_path, index=False)
            print("Wrote CSV:", csv_path)
        if WRITE_PARQUET:
            try:
                parquet_path = f"{OUTPUT_STEM}_{slugify(TARGET_BRAND)}_{ts}.parquet"
                df.to_parquet(parquet_path, index=False)
                print("Wrote Parquet:", parquet_path)
            except Exception as e:
                print("Parquet write failed (install pyarrow or fastparquet):", e)