import json, re
from bs4 import BeautifulSoup

def _safe_json(text):
    try:
        return json.loads(text)
    except Exception:
        return None

def _extract_jsonld_products(soup: BeautifulSoup):
    """Return first schema.org Product JSON-LD dict if present."""
    for tag in soup.select('script[type="application/ld+json"]'):
        data = _safe_json(tag.string or tag.text or "")
        if not data:
            continue
        # JSON-LD might be a list or a single object
        if isinstance(data, list):
            for obj in data:
                if isinstance(obj, dict) and obj.get('@type') in ('Product', ['Product']):
                    return obj
        elif isinstance(data, dict) and data.get('@type') in ('Product', ['Product']):
            return data
    return None

def _extract_shopify_meta(soup: BeautifulSoup):
    """Find `var meta = { ... }` (Shopify) and return the parsed dict, else None."""
    for tag in soup.find_all('script'):
        txt = (tag.string or tag.text or "").strip()
        if 'var meta' in txt or 'window.meta' in txt:
            m = re.search(r'(?:var|window)\.?\s*meta\s*=\s*({.*?});\s*$', txt, re.S | re.M)
            if m:
                data = _safe_json(m.group(1))
                if isinstance(data, dict):
                    return data
    return None

def _extract_measurements_and_condition(soup: BeautifulSoup):
    """Best-effort scrape for condition & measurements as visible text."""
    text = soup.get_text("\n", strip=True)
    # Condition
    condition = None
    # try common “Condition: Excellent” pattern
    cm = re.search(r'Condition\s*:\s*([A-Za-z ]+)', text, re.I)
    if cm:
        condition = cm.group(1).strip()
    else:
        # fallbacks: look for standard condition keywords near 'Condition'
        window = re.search(r'Condition.{0,120}', text, re.I)
        if window:
            frag = window.group(0)
            mm = re.search(r'(New|Pristine|Excellent|Very Good|Good|Fair|Worn)', frag, re.I)
            if mm:
                condition = mm.group(1).title()

    # Measurements (in inches)
    def grab(label):
        m = re.search(rf'{label}\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*(?:in|inch|inches)\b', text, re.I)
        return m.group(1) if m else None

    measurements = {
        "height_in": grab("Height"),
        "width_in": grab("Width"),
        "depth_in": grab("Depth"),
        "strap_drop_in": grab("Strap\s*Drop"),
        "handle_drop_in": grab("Handle\s*Drop"),
    }
    # remove None values
    measurements = {k: v for k, v in measurements.items() if v is not None}

    # Availability
    sold_out = bool(re.search(r'(Sold Out|Out of Stock)', text, re.I))

    return condition, measurements, sold_out

def parse_fashionphile_product(html: str) -> dict:
    """
    Unified parser for Fashionphile product pages.
    Supports legacy Next.js (__NEXT_DATA__) and current Shopify storefront.
    Returns a normalized dict.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1) Try legacy Next.js
    next_tag = soup.find("script", id="__NEXT_DATA__")
    if next_tag:
        next_json = _safe_json(next_tag.string or next_tag.text or "")
        # You may still have older fields you used before—extract them here.
        # Example sketch (adjust to your legacy structure):
        product = None
        try:
            product = next_json["props"]["pageProps"]["apolloState"]["ROOT_QUERY"]["product"]
        except Exception:
            pass

        if product:
            return {
                "source": "nextjs",
                "title": product.get("name"),
                "brand": product.get("brand", {}).get("name"),
                "sku": product.get("sku"),
                "price": product.get("price", {}).get("amount"),
                "currency": product.get("price", {}).get("currency"),
                "availability": product.get("availability"),
                "images": [img.get("url") for img in product.get("images", []) if isinstance(img, dict)],
                "raw_next_data": next_json,  # keep if you want full access
            }

    # 2) Shopify path: JSON-LD + `var meta = { product: ... }`
    jsonld = _extract_jsonld_products(soup)
    meta = _extract_shopify_meta(soup)
    condition, measurements, sold_out = _extract_measurements_and_condition(soup)

    # Pull primary identifiers from JSON-LD if present
    jl_name = jsonld.get("name") if jsonld else None
    jl_brand = (jsonld.get("brand") or {}).get("name") if isinstance(jsonld.get("brand"), dict) else jsonld.get("brand")
    jl_sku = jsonld.get("sku") if jsonld else None
    jl_images = jsonld.get("image") if jsonld else None
    if isinstance(jl_images, str):
        jl_images = [jl_images]
    jl_offers = None
    jl_price = jl_currency = jl_availability = jl_gtin = None
    if jsonld:
        offers = jsonld.get("offers")
        # offers may be list or dict
        if isinstance(offers, list) and offers:
            jl_offers = offers[0]
        elif isinstance(offers, dict):
            jl_offers = offers
        if jl_offers:
            jl_price = jl_offers.get("price")
            jl_currency = jl_offers.get("priceCurrency")
            jl_availability = jl_offers.get("availability")
            jl_gtin = jl_offers.get("gtin12") or jl_offers.get("gtin13") or jl_offers.get("gtin")

    # Pull from Shopify `meta.product`
    mprod = (meta or {}).get("product") if isinstance(meta, dict) else None
    shopify_id = (mprod or {}).get("id")
    shopify_vendor = (mprod or {}).get("vendor")
    shopify_type = (mprod or {}).get("type")
    variants = (mprod or {}).get("variants") or []
    first_var = variants[0] if variants else {}
    var_price_cents = first_var.get("price")
    var_price = (var_price_cents / 100.0) if isinstance(var_price_cents, (int, float)) else None
    var_sku = first_var.get("sku")

    # Visible H1 as a final fallback for title
    h1 = soup.find("h1")
    h1_title = h1.get_text(strip=True) if h1 else None

    return {
        "source": "shopify",
        "title": jl_name or first_var.get("name") or h1_title,
        "brand": jl_brand or shopify_vendor,
        "sku": jl_sku or var_sku,
        "gtin": jl_gtin,
        "price": jl_price or var_price,
        "currency": jl_currency or "USD",
        "availability": ("OutOfStock" if sold_out else jl_availability),
        "category": shopify_type,
        "shopify_product_id": shopify_id,
        "images": jl_images,               # JSON-LD usually has hero; gallery often lives elsewhere
        "condition": condition,
        "measurements_in": measurements,   # dict of inches found in visible text
    }