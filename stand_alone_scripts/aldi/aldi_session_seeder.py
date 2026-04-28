"""Aldi session seeder — obtains a fresh Instacart session by making a single
GET request to the Aldi homepage.

Key finding: __Host-instacart_sid is set server-side (Set-Cookie header) on
the first page load. No JavaScript execution is required. That one cookie is
sufficient to authenticate subsequent GraphQL calls. _instacart_session_id is
set by client-side JS and is NOT required for API calls.

Usage:
    # As a library — import seed_aldi_session() and use the returned Session
    # directly for all subsequent requests:

        from aldi_session_seeder import seed_aldi_session
        session = seed_aldi_session()
        resp = session.get("https://www.aldi.us/graphql?...", headers=API_HEADERS)

    # As a script — run directly to verify seeding works and inspect cookies:

        python3 aldi_session_seeder.py
"""

import sys
from curl_cffi import requests as curl_requests

SEED_URL = "https://www.aldi.us/"

# Browser-like headers for the initial page request (document navigation).
_SEED_HEADERS = {
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


def seed_aldi_session(*, timeout: int = 30) -> curl_requests.Session:
    """Return a curl_cffi Session with a fresh __Host-instacart_sid cookie.

    Makes a single GET to the Aldi homepage with Chrome TLS impersonation.
    The server issues __Host-instacart_sid via Set-Cookie on page load —
    no JS execution, no login, no location selection required.

    The returned Session maintains the cookie jar, so any subsequent
    request made through the same session will automatically include
    the Instacart session cookie.

    Raises RuntimeError if the expected cookie is not present in the
    response.
    """
    session = curl_requests.Session()
    resp = session.get(
        SEED_URL,
        headers=_SEED_HEADERS,
        impersonate="chrome",
        timeout=timeout,
        allow_redirects=True,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Session seed failed: HTTP {resp.status_code} from {SEED_URL}"
        )

    sid = session.cookies.get("__Host-instacart_sid")
    if not sid:
        raise RuntimeError(
            "Session seed did not produce __Host-instacart_sid. "
            "Instacart may have changed their session initialization flow."
        )

    return session


if __name__ == "__main__":
    print(f"Seeding session from {SEED_URL}...")
    try:
        session = seed_aldi_session()
    except RuntimeError as e:
        print(f"FAILED: {e}")
        sys.exit(1)

    sid = session.cookies.get("__Host-instacart_sid")
    print(f"OK — __Host-instacart_sid: {sid}")
    print()
    print("All cookies obtained:")
    for name, value in session.cookies.items():
        print(f"  {name}: {value[:60]}{'...' if len(value) > 60 else ''}")
