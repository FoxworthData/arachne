"""Feasibility test: reproduce the Items GraphQL call from Python using
curl-cffi. Seeds a fresh Instacart session automatically, then hydrates full
product data for a batch of 8 item IDs observed in the milk search. Writes
raw body and response headers to disk; prints a short diagnostic. On failure,
dumps the first 500 chars of the body."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from aldi_session_seeder import seed_aldi_session


URL = (
    "https://www.aldi.us/graphql"
    "?operationName=Items"
    "&variables=%7B%22ids%22%3A%5B%22items_14655-21059061%22%2C%22items_14655-20989941%22%2C%22items_14655-20975177%22%2C%22items_14655-20994220%22%2C%22items_14655-64484580%22%2C%22items_14655-20741641%22%2C%22items_14655-18648038%22%2C%22items_14655-76041384%22%5D%2C%22shopId%22%3A%22339%22%2C%22zoneId%22%3A%2290%22%2C%22postalCode%22%3A%2275202%22%7D"
    "&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%225116339819ff07f207fd38f949a8a7f58e52cc62223b535405b087e3076ebf2f%22%7D%7D"
)

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://www.aldi.us/store/aldi/s?k=milk",
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
    "x-ic-qp": "0552cb98-864b-599d-8011-7f734556397c,ec19447a-455c-546f-85c9-0448bab8e648",
    "x-ic-view-layer": "true",
    "x-page-view-id": "8d6636b7-86f3-58fc-9276-0290aa2b7cd8",
}

EXPECTED_ID_COUNT = 8


def main() -> int:
    here = Path(__file__).parent
    body_path = here / "data" / "aldi_items_response.json"
    headers_path = here / "data" / "aldi_items_response_headers.json"

    print("Seeding session...")
    session = seed_aldi_session()
    sid = session.cookies.get("__Host-instacart_sid")
    print(f"session cookie: {sid[:40]}...")

    resp = session.get(URL, headers=HEADERS, impersonate="chrome", timeout=30)

    body_path.write_bytes(resp.content)
    headers_path.write_text(json.dumps(dict(resp.headers), indent=2))

    print(f"status: {resp.status_code}")
    print(f"content-length: {len(resp.content)}")

    set_cookie = resp.headers.get("set-cookie") or resp.headers.get("Set-Cookie")
    server = resp.headers.get("server") or resp.headers.get("Server")
    via = resp.headers.get("via") or resp.headers.get("Via")
    print(f"server: {server!r}")
    print(f"via: {via!r}")
    print(f"set-cookie present: {bool(set_cookie)}")

    parsed = None
    is_json = False
    try:
        parsed = resp.json()
        is_json = True
    except Exception as e:
        print(f"json parse failed: {e}")

    print(f"parsed as json: {is_json}")

    items = None
    if is_json and isinstance(parsed, dict) and isinstance(parsed.get("data"), dict):
        items = parsed["data"].get("items")
    print(f"data.items is list: {isinstance(items, list)}")
    print(f"items returned: {len(items) if isinstance(items, list) else 'n/a'} (requested {EXPECTED_ID_COUNT})")

    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict):
            print(f"first item: id={first.get('id')!r} name={first.get('name')!r}")

    if is_json and isinstance(parsed, dict) and parsed.get("errors"):
        print(f"graphql errors: {parsed['errors']}")

    failed = resp.status_code >= 400 or not is_json or not isinstance(items, list) or not items
    if failed:
        print("\n--- first 500 chars of body ---")
        print(resp.text[:500])
        print("--- end preview ---")
        return 1

    print(f"\nwrote {body_path.name} ({len(resp.content)} bytes)")
    print(f"wrote {headers_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
