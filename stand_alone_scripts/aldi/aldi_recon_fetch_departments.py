"""Recon script: fetch the Aldi department/category navigation for a given
shopId.

The department list (left-rail sidebar navigation) is embedded in the Apollo
SSR cache on every Aldi storefront page under the key
`DesktopSidebarNavigations`. It is not a separate GraphQL call at runtime —
it is server-rendered into the page as a URL-encoded JSON blob in the
`<script id="node-apollo-state">` tag.

This script seeds a session, fetches the Aldi storefront for a given shopId,
parses the Apollo state blob, and extracts the ordered list of department
navigation entries (name + slug).

The resulting slugs are the canonical category identifiers for Aldi/Instacart.
They can be used as inputs to a future `BrowsePlacementsSource` call to
enumerate all item IDs in each department, enabling an item→category mapping
that Aldi does not provide directly in its `Items` or `SearchResultsPlacements`
API responses.

Output: writes aldi_departments.json to the same directory.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).parent))
from aldi_session_seeder import seed_aldi_session

# Storefront URL. shopId is embedded in the SSR query key, not this URL —
# the page at this URL returns the SSR cache for whatever shop the session
# is associated with (i.e. the default shop for the user's location).
STOREFRONT_URL = "https://www.aldi.us/store/aldi/storefront"

PAGE_HEADERS = {
    "accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "accept-language": "en-US,en;q=0.9",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    ),
}

_APOLLO_STATE_RE = re.compile(
    r'<script\s+id="node-apollo-state"\s+type="application/json">\s*([^<]+)\s*</script>',
    re.DOTALL,
)


def extract_departments(html: str) -> list[dict]:
    """Parse the Apollo SSR cache and return the ordered department list.

    Each entry is a dict with keys:
        name  — display name (e.g. "Dairy & Eggs")
        slug  — URL slug used as the collection identifier (e.g. "dairy-and-eggs")
        type  — "department", "feature", or "link" (non-department entries like
                "Buy It Again" and external URLs are included for completeness)

    Raises ValueError if the Apollo state blob or DesktopSidebarNavigations
    key is not present.
    """
    m = _APOLLO_STATE_RE.search(html)
    if not m:
        raise ValueError(
            "node-apollo-state script tag not found. "
            "Page may not have rendered SSR data."
        )

    apollo = json.loads(unquote(m.group(1)))

    dsn = apollo.get("DesktopSidebarNavigations")
    if not dsn:
        raise ValueError(
            "DesktopSidebarNavigations not found in Apollo state. "
            "The shop may not have a configured sidebar layout."
        )

    # The key is a JSON-encoded variables object: {"previewToken":null,"shopId":"..."}
    variables_key = next(iter(dsn))
    navs = (
        dsn[variables_key]
        .get("desktopSidebarLayoutV1Navigations", {})
        .get("navs", [])
    )

    departments = []
    for nav in navs:
        for item in nav.get("items", []):
            action = item.get("action", {})
            text = action.get("viewSection", {}).get("textString", "")
            if not text:
                continue

            slug = action.get("slug")
            destination = action.get("destination")  # e.g. "buyItAgain"
            url = action.get("url")  # external URLs

            if slug:
                entry_type = "department"
            elif destination:
                entry_type = "feature"
                slug = destination
            elif url:
                entry_type = "link"
                slug = url
            else:
                entry_type = "unknown"
                slug = None

            departments.append({"name": text, "slug": slug, "type": entry_type})

    return departments


def main() -> int:
    here = Path(__file__).parent
    output_path = here / "data" / "aldi_departments.json"

    print(f"Seeding session...")
    session = seed_aldi_session()
    sid = session.cookies.get("__Host-instacart_sid")
    print(f"session cookie: {sid[:40]}...")

    print(f"Fetching {STOREFRONT_URL}...")
    resp = session.get(
        STOREFRONT_URL,
        headers=PAGE_HEADERS,
        impersonate="chrome",
        timeout=30,
        allow_redirects=True,
    )
    print(f"status: {resp.status_code}  content-length: {len(resp.content):,}")

    if resp.status_code != 200:
        print(f"ERROR: unexpected status {resp.status_code}")
        return 1

    try:
        departments = extract_departments(resp.text)
    except ValueError as e:
        print(f"ERROR: {e}")
        print("First 500 chars of body:")
        print(resp.text[:500])
        return 1

    output_path.write_text(json.dumps(departments, indent=2))
    print(f"\nwrote {output_path.name} ({len(departments)} entries)")

    print("\nDepartments:")
    for d in departments:
        marker = "  " if d["type"] == "department" else " *"
        print(f"{marker} {d['name']:35} -> {d['slug']}")

    dept_only = [d for d in departments if d["type"] == "department"]
    print(f"\n{len(dept_only)} department slugs, {len(departments) - len(dept_only)} other entries (* = non-department)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
