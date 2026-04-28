"""One-shot test: probe whether zoneId is required for Items and Search."""
import json, sys
from pathlib import Path
from urllib.parse import urlencode
sys.path.insert(0, str(Path(__file__).parent))
from aldi_session_seeder import seed_aldi_session

ITEMS_HASH = "5116339819ff07f207fd38f949a8a7f58e52cc62223b535405b087e3076ebf2f"
SEARCH_HASH = "6e6b53b10516829d9b7b9fae0cbc9b65bcbbc8792d77836f65b9db6a606057a7"
HEADERS = {
    "accept": "*/*", "content-type": "application/json",
    "referer": "https://www.aldi.us/store/aldi/s?k=milk",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "x-client-identifier": "web", "x-ic-view-layer": "true",
    "x-page-view-id": "8d6636b7-86f3-58fc-9276-0290aa2b7cd8",
    "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
}
ITEM_IDS = ["items_14655-16902710", "items_14655-20989941"]

session = seed_aldi_session()
print("Session seeded.")

def probe(label, op, variables, hash_val):
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": hash_val}}
    params = {
        "operationName": op,
        "variables": json.dumps(variables, separators=(",", ":")),
        "extensions": json.dumps(extensions, separators=(",", ":")),
    }
    resp = session.get(
        "https://www.aldi.us/graphql?" + urlencode(params),
        headers=HEADERS, impersonate="chrome", timeout=30,
    )
    body = resp.json()
    errors = body.get("errors")
    data_val = body.get("data")
    if op == "Items":
        items = (data_val or {}).get("items") or []
        result = f"{len(items)} items" + (f" (e.g. {items[0].get('name')})" if items else "")
    else:
        placements = ((data_val or {}).get("searchResultsPlacements") or {}).get("placements") or []
        ids = set(iid for p in placements for iid in ((p.get("content") or {}).get("itemIds") or []))
        result = f"{len(ids)} item IDs"
    err_msg = (errors[0]["message"][:60] if errors else "None")
    print(f"  {label:35} | data={'null' if data_val is None else 'ok':4} | err={err_msg:45} | {result}")

def probe_items(label, variables):
    probe(label, "Items", variables, ITEMS_HASH)

BASE_ITEMS = {"ids": ITEM_IDS, "shopId": "339", "postalCode": "75202"}

print("\n=== Test A: alternate zoneId values (shopId=339, postalCode=75202) ===")
for z in ("90", "89", "91", "100", "1"):
    probe_items(f"zoneId={z}", {**BASE_ITEMS, "zoneId": z})

print("\n=== Test B: alternate postalCodes (shopId=339, zoneId=90) ===")
for label, postal in [("75202 Dallas (baseline)", "75202"), ("90210 Beverly Hills", "90210"), ("10001 Manhattan", "10001")]:
    probe_items(f"postalCode={postal} ({label.split()[0]})", {"ids": ITEM_IDS, "shopId": "339", "postalCode": postal, "zoneId": "90"})
