"""Aldi session seeder for use within the /src orchestration flow.

Seeds a curl_cffi Session with a fresh __Host-instacart_sid cookie by making
a single GET to the Aldi homepage with Chrome TLS impersonation.

Unlike the stand-alone script equivalent in stand_alone_scripts/aldi/, this
version always accepts a proxies dict so that all requests — including the
seed call itself — are routed through the configured residential proxy pool.
"""
from curl_cffi import requests as curl_requests

SEED_URL = "https://www.aldi.us/"

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


def seed_aldi_session(
    proxies: dict | None = None,
    timeout: int = 30,
) -> curl_requests.Session:
    """Return a curl_cffi Session seeded with a fresh Instacart session cookie.

    Args:
        proxies: BrightData (or equivalent) proxy dict in requests format:
                 {'http': 'http://user:pass@host:port',
                  'https': 'http://user:pass@host:port'}
                 When provided, the proxy is applied to the seed request and
                 persisted on the session for all subsequent calls.
        timeout: Request timeout in seconds.

    Raises:
        RuntimeError: If the seed GET fails or does not produce the expected
                      session cookie.
    """
    session = curl_requests.Session()

    if proxies:
        session.proxies = proxies

    # Bright Data's residential proxy gateway performs HTTPS MITM with a
    # self-signed cert chain that curl will reject by default. Persist
    # verify=False on the session so it applies to the seed call here AND
    # to every subsequent GraphQL call the strategy makes through this
    # session. We accept the reduced TLS guarantee in exchange for being
    # able to route through the residential pool at all.
    session.verify = False

    resp = session.get(
        SEED_URL,
        headers=_SEED_HEADERS,
        impersonate="chrome",
        proxies=proxies,
        timeout=timeout,
        allow_redirects=True,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Aldi session seed failed: HTTP {resp.status_code} from {SEED_URL}"
        )

    sid = session.cookies.get("__Host-instacart_sid")
    if not sid:
        raise RuntimeError(
            "Aldi session seed did not produce __Host-instacart_sid. "
            "Instacart may have changed their session initialization flow."
        )

    return session
