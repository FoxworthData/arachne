#!/usr/bin/env python3
# rebag_chanel_scrape.py
import argparse, csv, re, sys, json, urllib.parse as ul
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Iterable

import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139 Safari/537.36"

SECTION_IDS = [
    "main-collection-product-grid",
    "collection-product-grid",
    "collection-template",
]

@dataclass
class Product:
    title: str
    price: Optional[float]
    currency: Optional[str]
    url: str
    image: Optional[str]

def _client(timeout=20):
    return httpx.Client(
        headers={
            "User-Agent": UA,
            "Accept": "application/json, text/html;q=0.8, */*;q=0.5",
            "Referer": "https://shop.rebag.com/",
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=timeout,
        follow_redirects=True,
    )

def _abs_url(path: str) -> str:
    if path.startswith("http"):
        return path
    return ul.urljoin("https://shop.rebag.com/", path.lstrip("/"))

# ---------- Parsers ----------
def parse_collection_html(html: str) -> List[Product]:
    soup = BeautifulSoup(html, "html.parser")
    prods: List[Product] = []

    cards = soup.select("[data-product-id], article, li, div")
    # Filter to elements that look like product cards (with a link to /products/)
    cards = [c for c in cards if c.find("a", href=re.compile(r"/products/"))]

    for card in cards:
        a = card.find("a", href=re.compile(r"/products/"))
        if not a:
            continue
        url = _abs_url(a.get("href", "").strip())
        # Title
        title = (a.get("title") or a.get_text(" ", strip=True) or "").strip()
        if not title:
            # try nested heading
            h = card.select_one("h2,h3,.product-title,.card__heading")
            title = (h.get_text(" ", strip=True) if h else "").strip()

        # Image
        img = card.find("img")
        image = None
        if img:
            image = img.get("data-src") or img.get("data-original-src") or img.get("src")
            if image:
                image = re.sub(r"(?<=\.)_(\d+x\d+|crop_[^.]*)", "", image)  # untransform if possible
                image = _abs_url(image)

        # Price (grab first numeric)
        price = None
        currency = None
        price_container = card.select_one(
            ".price, .product-price, .price__regular, .price__container, [data-product-price]"
        )
        txt = price_container.get_text(" ", strip=True) if price_container else card.get_text(" ", strip=True)
        m = re.search(r"([$\u00A3\u20AC])\s*([0-9][0-9,]*(?:\.[0-9]{2})?)", txt)
        if m:
            symbol, amt = m.groups()
            currency = {"$": "USD", "£": "GBP", "€": "EUR"}.get(symbol, None)
            price = float(amt.replace(",", ""))

        prods.append(Product(title=title, price=price, currency=currency, url=url, image=image))
    # Deduplicate by URL
    uniq = {}
    for p in prods:
        uniq[p.url] = p
    return list(uniq.values())

def parse_sections_json(obj: Dict[str, Any]) -> List[Product]:
    # Shopify 'sections=' returns JSON: { "<section_id>": "<HTML>" }
    products: List[Product] = []
    for _, html in obj.items():
        if isinstance(html, str):
            products.extend(parse_collection_html(html))
    return products

def parse_products_json(obj: Dict[str, Any]) -> List[Product]:
    products = []
    for p in obj.get("products", []):
        title = p.get("title", "")
        handle = p.get("handle", "")
        url = _abs_url(f"/products/{handle}") if handle else _abs_url(p.get("url", ""))
        # price from first variant (Shopify cents)
        price = None
        currency = "USD"
        if p.get("variants"):
            v0 = p["variants"][0]
            cents = v0.get("price") or v0.get("price_cents")
            if isinstance(cents, (int, float, str)):
                try:
                    price = float(cents) / (100.0 if float(cents) > 1000 else 1.0)
                except Exception:
                    pass
        # images
        image = None
        if p.get("images"):
            image = p["images"][0].get("src") or p["images"][0]
            if image:
                image = _abs_url(image)
        products.append(Product(title=title, price=price, currency=currency, url=url, image=image))
    return products

def parse_predictive_json(obj: Dict[str, Any]) -> List[Product]:
    products = []
    resources = obj.get("resources", {})
    results = resources.get("results", {})
    for p in results.get("products", []):
        title = p.get("title") or ""
        url = _abs_url(p.get("url") or "")
        image = None
        # predictive often has image attached directly or in 'image' dict
        if isinstance(p.get("image"), dict):
            image = p["image"].get("url")
        else:
            image = p.get("image")
        if image:
            image = _abs_url(image)
        # price may be absent; try a few keys
        price = None
        currency = "USD"
        for key in ("price", "price_min", "price_max"):
            if p.get(key) is not None:
                try:
                    val = p[key]
                    # sometimes integer cents
                    price = float(val) / (100.0 if float(val) > 1000 else 1.0)
                    break
                except Exception:
                    pass
        products.append(Product(title=title, price=price, currency=currency, url=url, image=image))
    return products

# ---------- Fetchers ----------
def fetch_collection_sections(base_url: str, designer: str, page: int, client: httpx.Client) -> List[Product]:
    params = {"pf_v_designers": designer, "page": page}
    # try ?section_id=
    for sid in SECTION_IDS:
        url = f"{base_url}?{ul.urlencode({**params, 'section_id': sid})}"
        r = client.get(url, headers={"Accept": "text/html,*/*"})
        if r.status_code == 200 and r.text.strip():
            return parse_collection_html(r.text)
    # try ?sections=
    url = f"{base_url}?{ul.urlencode({**params, 'sections': SECTION_IDS[0]})}"
    r = client.get(url, headers={"Accept": "application/json"})
    if r.status_code == 200:
        try:
            obj = r.json()
            return parse_sections_json(obj)
        except Exception:
            pass
    return []

def fetch_products_json(base_url: str, page: int, limit: int, client: httpx.Client) -> List[Product]:
    url = ul.urljoin(base_url, "products.json")
    r = client.get(url, params={"page": page, "limit": limit})
    if r.status_code == 200:
        try:
            return parse_products_json(r.json())
        except Exception:
            return []
    return []

def fetch_predictive(q: str, limit: int, client: httpx.Client) -> List[Product]:
    url = "https://shop.rebag.com/search/suggest.json"
    params = {
        "q": q,
        "resources[type]": "product",
        "resources[limit]": str(limit),
    }
    r = client.get(url, params=params, headers={"Accept": "application/json"})
    if r.status_code == 200:
        try:
            return parse_predictive_json(r.json())
        except Exception:
            return []
    return []

def write_csv(products: Iterable[Product], path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["title", "price", "currency", "url", "image"])
        for p in products:
            w.writerow([p.title, p.price if p.price is not None else "", p.currency or "", p.url, p.image or ""])

def main():
    ap = argparse.ArgumentParser(description="Fetch Chanel bag listings from shop.rebag.com")
    ap.add_argument("--designer", default="Chanel", help="Designer filter for Shopify collection (pf_v_designers)")
    ap.add_argument("--collection", default="all-bags", help="Collection handle (e.g., all-bags)")
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--limit", type=int, default=24)
    ap.add_argument("--query", default="chanel bag", help="Predictive search fallback query")
    ap.add_argument("--output", default="rebag_chanel.csv")
    args = ap.parse_args()

    base_collection = f"https://shop.rebag.com/collections/{args.collection}"

    with _client() as client:
        products: List[Product] = []

        # 1) Preferred: collection grid via sections (honors pf_v_designers=Chanel)
        products = fetch_collection_sections(base_collection, args.designer, args.page, client)
        if not products:
            # 2) Legacy JSON (not filtered by pf_v_designers)
            products = fetch_products_json(base_collection + "/", args.page, args.limit, client)
        if not products:
            # 3) Predictive search fallback (lightweight)
            products = fetch_predictive(args.query, args.limit, client)

    if not products:
        print("No products found via sections, products.json, or predictive search.", file=sys.stderr)
        sys.exit(2)

    write_csv(products, args.output)
    print(f"✅ Wrote {len(products)} products to {args.output}")

if __name__ == "__main__":
    main()