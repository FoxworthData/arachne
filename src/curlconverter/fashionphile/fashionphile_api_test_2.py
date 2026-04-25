import httpx, json, urllib.parse, time

ALG_URL = "https://nsjaz0qg7k-dsn.algolia.net/1/indexes/*/queries"
HEADERS = {
    "content-type": "application/json",
    "accept": "application/json",
    "x-algolia-application-id": "NSJAZ0QG7K",
    "x-algolia-api-key": "f26f1dfb62b97a9c1002bbae62a9f7e1",  # from your cURL
    "origin": "https://www.fashionphile.com",
    "referer": "https://www.fashionphile.com/",
}

INDEX = "prod_ecom_products_date_desc"

# Your exact working params (start page at 0)
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

def add_facet_filters(params_enc: str, facet_filters_json: str) -> str:
    q = urllib.parse.parse_qs(params_enc, keep_blank_values=True)
    # Keep the original 'filters' for category; add brand via facetFilters
    q["facetFilters"] = [urllib.parse.quote(facet_filters_json, safe="")]
    # Rebuild
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
    r = httpx.post(ALG_URL, headers=HEADERS, data=json.dumps(body), timeout=30)
    r.raise_for_status()
    return r.json()["results"][0]

# Add brand facet filter using the discovered facet key
facet_filters_json = '[["filters.brands:Christian Louboutin"]]'
params_with_brand = add_facet_filters(BASE_PARAMS, facet_filters_json)

# First page (to read nbPages/nbHits)
res0 = query(params_with_brand)
nb_hits = res0.get("nbHits", 0)
nb_pages = res0.get("nbPages", 0)
print(f"Christian Louboutin — nbHits: {nb_hits}, nbPages: {nb_pages}, hits on page 1: {len(res0.get('hits', []))}")

# Paginate and collect (optional)
all_hits = list(res0.get("hits", []))
for page in range(1, nb_pages):
    time.sleep(0.25)
    res = query(set_page(params_with_brand, page))
    print(f"Page {page+1}/{nb_pages} → {len(res.get('hits', []))} hits")
    all_hits.extend(res.get("hits", []))

print("Total collected:", len(all_hits))

# Peek at a few fields safely (since schemas vary)
def summarize(hit):
    keys = hit.keys()
    return {
        "objectID": hit.get("objectID"),
        "brand": hit.get("brand") or hit.get("filters", {}).get("brands"),
        "name": hit.get("name") or hit.get("title"),
        "price": hit.get("price") or hit.get("discounted_price"),
        "discounted_price": hit.get("discounted_price"),
        "url": hit.get("url") or hit.get("slug"),
        "condition": hit.get("condition") or hit.get("filters", {}).get("condition"),
    }

for h in all_hits[:5]:
    print(summarize(h))

sample = all_hits[0]
print(sorted(sample.keys()))
print(sample.get("slug") or sample.get("permalink") or sample.get("handle"))
print(sample)