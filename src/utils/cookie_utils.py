"""Cookie utilities shared across retailer scrape strategies."""


def blend_cookies(location_cookies: dict, harvested_cookies: dict) -> str:
    """Combine Walmart's location-style cookies with cookies harvested from a
    seeded session into a single Cookie header string.

    Args:
        location_cookies: dict produced by
            WalmartCookieSeedingHeaderBuilder.initial_cookies. Required keys:
            hasLocData, ACID, locGuestData, assortmentStoreId, locDataV3.
        harvested_cookies: dict of session/anti-bot cookies harvested from a
            real Walmart session by WalmartCookieSeeder (e.g. _px3, ak_bmsc,
            bm_sv, _pxvid, etc.).

    Returns:
        A single Cookie header string suitable for assignment to
        seeded_headers['cookie'].
    """
    cookie_string = (
        f"hasLocData={location_cookies['hasLocData']}; "
        f"ACID={location_cookies['ACID']}; "
        f"locGuestData={location_cookies['locGuestData']}; "
        f"assortmentStoreId={location_cookies['assortmentStoreId']}; "
        f"hasACID=true; "
        f"locDataV3={location_cookies['locDataV3']}; "
    )
    harvested_cookie_string = "; ".join(
        f"{key}={value}" for key, value in harvested_cookies.items()
    )
    cookie_string += f"{harvested_cookie_string};"
    return cookie_string
