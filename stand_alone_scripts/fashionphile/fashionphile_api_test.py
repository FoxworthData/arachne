import httpx, json, urllib.parse

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

# Paste your EXACT params from cURL here (no modifications)
PARAMS_ENC = (
    "clickAnalytics=true"
    "&facets=%5B%22*%22%5D"
    "&filters=%22categories_page_id%22%3A%20%22shoes%22"
    "&highlightPostTag=__%2Fais-highlight__"
    "&highlightPreTag=__ais-highlight__"
    "&maxValuesPerFacet=999"
    "&page=0"     # start at 0 to be safe
    "&query="
)

def build_body(params_enc: str):
    return {"requests": [{"indexName": INDEX, "params": params_enc}]}

r = httpx.post(ALG_URL, headers=HEADERS, data=json.dumps(build_body(PARAMS_ENC)), timeout=30)
r.raise_for_status()
res = r.json()["results"][0]
print("nbHits:", res.get("nbHits"), "nbPages:", res.get("nbPages"), "hits on this page:", len(res.get("hits", [])))

# Peek facet keys so we know the brand facet name to use later:
facets = res.get("facets", {}) or {}
print("Facet keys present:", list(facets.keys())[:10])