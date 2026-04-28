"""ALDI store registry builder — Batch 1: Shop ID Enumeration

Joins two data sources to produce a registry of every US ALDI store with its
Instacart shop IDs:

  - Uberall snapshot  (all-aldi-us-locations.json): 2,677 physical stores
    Source URL (fetched April 2026):
    https://locator.uberall.com/api/storefinders/LETA2YVm6txbe0b9lS297XdxDX4qVQ/locations/all
      ?v=20260101&country=US&fieldMask=id&fieldMask=identifier&fieldMask=name
      &fieldMask=streetAndNumber&fieldMask=city&fieldMask=province&fieldMask=zip
      &fieldMask=lat&fieldMask=lng
  - Instacart /idp/v1/shops?postal_code=<zip>: delivery/pickup/instore shop IDs

The join key is normalized (zip5, street_address). Province/state normalization
handles the mixed full-name / 2-letter format in the Uberall data.

Output files (all written to stand_alone_scripts/):
  aldi_store_registry.jsonl          — one JSON record per matched store
  aldi_store_registry_mismatches.jsonl — unmatched / ambiguous records
  aldi_zip_cache.json                 — cached API responses; supports resume

Usage:
    cd /path/to/arachne
    venv/bin/python3 stand_alone_scripts/aldi_build_store_registry.py
"""

import json
import random
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from aldi_session_seeder import seed_aldi_session  # noqa: E402

# ─── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
REGISTRY_DATA_DIR = SCRIPT_DIR / "data" / "registry"
REPO_DATA_DIR = SCRIPT_DIR.parent.parent / "data"
INPUT_FILE = REGISTRY_DATA_DIR / "all-aldi-us-locations.json"
ZIP_CACHE_FILE = REGISTRY_DATA_DIR / "aldi_zip_cache.json"
REGISTRY_FILE = REPO_DATA_DIR / "aldi_store_registry.jsonl"
MISMATCHES_FILE = REGISTRY_DATA_DIR / "aldi_store_registry_mismatches.jsonl"

SHOPS_API = "https://www.aldi.us/idp/v1/shops"

_API_HEADERS = {
    "accept": "application/json",
    "referer": "https://www.aldi.us/",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    ),
    "x-client-identifier": "web",
}

# Re-seed the curl_cffi session every N API calls to guard against expiry.
_RESEED_INTERVAL = 250


# ─── Province / state normalization ───────────────────────────────────────────

_PROVINCE_TO_STATE: dict[str, str] = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "District of Columbia": "DC",
}


def normalize_state(province: str) -> str:
    """Return 2-letter USPS state code. Pass-through if already a 2-letter code."""
    s = province.strip()
    if len(s) == 2:
        return s.upper()
    return _PROVINCE_TO_STATE.get(s, s.upper()[:2])


# ─── Address normalization ─────────────────────────────────────────────────────

# Map full and abbreviated street-type tokens to a canonical short form.
_STREET_TYPE_MAP: dict[str, str] = {
    "avenue": "ave",
    "boulevard": "blvd",
    "circle": "cir",
    "court": "ct",
    "drive": "dr",
    "expressway": "expy",
    "highway": "hwy",
    "lane": "ln",
    "parkway": "pkwy",
    "place": "pl",
    "road": "rd",
    "square": "sq",
    "street": "st",
    "terrace": "ter",
    "terr": "ter",
    "trail": "trl",
    "turnpike": "tpke",
    "way": "way",
}

# Map full and abbreviated cardinal/ordinal directional tokens to single-letter form.
_DIRECTION_MAP: dict[str, str] = {
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
    "northeast": "ne",
    "northwest": "nw",
    "southeast": "se",
    "southwest": "sw",
}

# Matches suite/unit designators and everything that follows them.
# Empirical analysis confirmed these are the primary low-risk normalization gap:
# Instacart often appends "Suite 100" / "Ste 1" / "Building 2" / "PMB E" etc.
# while Uberall records the base street only (or vice-versa).
_SUITE_RE = re.compile(
    r",?\s*\b(suite|ste\.?|unit|apt\.?|bldg\.?|building|floor|fl\.?|pmb|#|lot|space|spc)\b.*$",
    re.IGNORECASE,
)


def normalize_address(street: str) -> str:
    """Return a normalized street string suitable for join-key construction.

    Transformations applied (in order):
      1. Strip suite/unit designator and trailing content  ("123 Main St Suite 100" → "123 Main St")
      2. Lowercase
      3. Strip trailing period from every token  ("Ave." → "ave")
      4. Contract street-type tokens             ("Avenue" → "ave")
      5. Contract directional tokens             ("North" → "n")
      6. Collapse multiple spaces
    """
    # Step 1: strip suite/unit suffix before tokenizing
    s = _SUITE_RE.sub("", street).strip()
    s = s.lower().strip()
    tokens = s.split()
    result: list[str] = []
    for tok in tokens:
        tok = tok.rstrip(".,")
        tok = _STREET_TYPE_MAP.get(tok, tok)
        tok = _DIRECTION_MAP.get(tok, tok)
        result.append(tok)
    # Collapse any remaining multiple spaces (shouldn't happen after split, but safe)
    return " ".join(result)


def make_join_key(zip5: str, street: str) -> str:
    """Return a string key used to match Uberall addresses to Instacart addresses."""
    return f"{zip5[:5]}:{normalize_address(street)}"


# ─── Zip cache (file-backed, supports resume) ─────────────────────────────────

def load_zip_cache() -> dict[str, list]:
    if ZIP_CACHE_FILE.exists():
        with ZIP_CACHE_FILE.open() as f:
            return json.load(f)
    return {}


def save_zip_cache(cache: dict[str, list]) -> None:
    with ZIP_CACHE_FILE.open("w") as f:
        json.dump(cache, f)


# ─── Instacart API fetch ───────────────────────────────────────────────────────

def fetch_shops_for_zip(
    session,
    zip_code: str,
    *,
    retries: int = 3,
) -> list[dict]:
    """Fetch the shops list for a zip code from the Instacart shops endpoint.

    Returns a (possibly empty) list of shop dicts on success.
    Returns [] on permanent errors (4xx) or after exhausting retries.
    """
    url = f"{SHOPS_API}?postal_code={zip_code}"
    for attempt in range(retries):
        try:
            resp = session.get(
                url,
                headers=_API_HEADERS,
                impersonate="chrome",
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json().get("shops", [])
            if resp.status_code < 500:
                print(
                    f"  [SKIP] zip {zip_code}: HTTP {resp.status_code} (permanent)",
                    file=sys.stderr,
                )
                return []
            # 5xx — transient; retry
            print(
                f"  [RETRY {attempt + 1}/{retries}] zip {zip_code}: HTTP {resp.status_code}",
                file=sys.stderr,
            )
        except Exception as exc:
            print(
                f"  [RETRY {attempt + 1}/{retries}] zip {zip_code}: {exc}",
                file=sys.stderr,
            )
        # Exponential backoff with jitter
        time.sleep(2**attempt + random.uniform(0.0, 1.0))

    print(f"  [FAIL] zip {zip_code}: giving up after {retries} attempts", file=sys.stderr)
    return []


# ─── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # Verify input file exists before doing any work.
    if not INPUT_FILE.exists():
        sys.exit(f"ERROR: input file not found: {INPUT_FILE}")

    # ── Load Uberall data ──────────────────────────────────────────────────────
    with INPUT_FILE.open() as f:
        raw = json.load(f)
    uberall_locs: list[dict] = raw["response"]["locations"]
    print(f"Loaded {len(uberall_locs)} Uberall locations.")

    # ── Load zip cache (supports resume after interruption) ───────────────────
    zip_cache = load_zip_cache()
    print(f"Zip cache: {len(zip_cache)} zips already fetched.")

    # ── Phase 1: Fetch Instacart shops for every store zip ────────────────────
    unique_zips: list[str] = sorted({loc["zip"] for loc in uberall_locs})
    zips_to_fetch: list[str] = [z for z in unique_zips if z not in zip_cache]
    print(f"Unique zips: {len(unique_zips)}.  To fetch: {len(zips_to_fetch)}.")

    if zips_to_fetch:
        print("Seeding Instacart session...")
        session = seed_aldi_session()
        call_count = 0

        try:
            for i, zip_code in enumerate(zips_to_fetch, 1):
                # Periodically re-seed to guard against session expiry.
                if call_count > 0 and call_count % _RESEED_INTERVAL == 0:
                    print(f"  Re-seeding session at call {call_count}...")
                    session = seed_aldi_session()

                shops = fetch_shops_for_zip(session, zip_code)
                zip_cache[zip_code] = shops
                call_count += 1

                if i % 50 == 0 or i == len(zips_to_fetch):
                    save_zip_cache(zip_cache)
                    print(f"  {i}/{len(zips_to_fetch)} zips fetched — cache saved.")

                time.sleep(random.uniform(0.5, 1.0))
        finally:
            # Always persist the cache, even on Ctrl+C.
            save_zip_cache(zip_cache)
            print(f"Cache saved ({len(zip_cache)} zips).")
    else:
        print("All zips already cached — skipping API calls.")

    # ── Phase 2: Build Instacart shop registry from cache ────────────────────
    # location_code → {"location_code", "location_name", "address", "shops": {mode: id}}
    instacart_by_lc: dict[str, dict] = {}
    duplicate_mode_mismatches: list[dict] = []

    for zip_code, shops in zip_cache.items():
        for shop in shops:
            lc: str | None = shop.get("location_code")
            if not lc:
                continue
            mode: str = shop.get("fulfillment_option", "unknown")
            shop_id: str = shop.get("id", "")
            addr: dict = shop.get("address") or {}
            loc_name: str = shop.get("location_name") or ""

            if lc not in instacart_by_lc:
                instacart_by_lc[lc] = {
                    "location_code": lc,
                    "location_name": loc_name,
                    "address": addr,
                    "shops": {},
                }

            entry = instacart_by_lc[lc]

            if mode in entry["shops"]:
                # Same location_code + fulfillment_option seen again.
                # Log only if the shop ID actually differs (otherwise it's just
                # a harmless duplicate from overlapping catchment queries).
                if entry["shops"][mode] != shop_id:
                    duplicate_mode_mismatches.append({
                        "type": "instacart_duplicate_mode",
                        "location_code": lc,
                        "fulfillment_option": mode,
                        "existing_shop_id": entry["shops"][mode],
                        "conflicting_shop_id": shop_id,
                        "reason": (
                            "same location_code+fulfillment_option seen with "
                            "two distinct shop IDs"
                        ),
                    })
            else:
                entry["shops"][mode] = shop_id
                # Prefer the address from a query whose zip matches the store's
                # own postal code — that's the "home" query for this store.
                store_zip5 = (addr.get("postal_code") or "")[:5]
                if store_zip5 == zip_code[:5]:
                    entry["address"] = addr
                    if loc_name:
                        entry["location_name"] = loc_name

    print(f"Instacart location_codes collected: {len(instacart_by_lc)}")

    # ── Phase 3: Build address-keyed lookup index ─────────────────────────────
    # Maps join_key → location_code. Keys with multiple matching location_codes
    # are removed and recorded as ambiguous.
    ic_index: dict[str, str] = {}
    ic_index_collisions: dict[str, list[str]] = defaultdict(list)

    for lc, entry in instacart_by_lc.items():
        addr = entry["address"]
        zip5 = (addr.get("postal_code") or "")[:5]
        street = addr.get("street_address") or ""
        if not zip5 or not street:
            continue
        key = make_join_key(zip5, street)
        if key in ic_index:
            # Collision: two distinct location_codes normalize to the same key.
            ic_index_collisions[key].append(lc)
            if ic_index[key] not in ic_index_collisions[key]:
                ic_index_collisions[key].append(ic_index[key])
        else:
            ic_index[key] = lc

    ambiguous_keys: set[str] = set(ic_index_collisions.keys())
    for key in ambiguous_keys:
        ic_index.pop(key, None)

    # ── Phase 4: Join Uberall records to Instacart location_codes ─────────────
    output_records: list[dict] = []
    mismatches: list[dict] = []
    matched_lcs: set[str] = set()

    # Pre-scan for duplicate Uberall addresses within the same zip (data quality).
    uberall_key_to_ids: dict[str, list[int]] = defaultdict(list)
    for loc in uberall_locs:
        key = make_join_key(loc["zip"], loc["streetAndNumber"])
        uberall_key_to_ids[key].append(loc["id"])
    duplicate_uberall_keys: set[str] = {
        k for k, ids in uberall_key_to_ids.items() if len(ids) > 1
    }

    for loc in uberall_locs:
        state = normalize_state(loc.get("province") or "")
        addr_display = f"{loc['streetAndNumber']}, {loc['city']}, {state} {loc['zip']}"
        join_key = make_join_key(loc["zip"], loc["streetAndNumber"])

        if join_key in duplicate_uberall_keys:
            mismatches.append({
                "type": "uberall_duplicate",
                "uberall_id": loc["id"],
                "uberall_identifier": loc.get("identifier"),
                "address": addr_display,
                "reason": "two or more Uberall records share this normalized address+zip",
            })
            continue

        if join_key in ambiguous_keys:
            mismatches.append({
                "type": "instacart_ambiguous_match",
                "uberall_id": loc["id"],
                "uberall_identifier": loc.get("identifier"),
                "address": addr_display,
                "location_codes": list(set(ic_index_collisions[join_key])),
                "reason": (
                    "multiple Instacart location_codes matched this "
                    "normalized address+zip"
                ),
            })
            continue

        lc = ic_index.get(join_key)
        if lc is None:
            mismatches.append({
                "type": "uberall_unmatched",
                "uberall_id": loc["id"],
                "uberall_identifier": loc.get("identifier"),
                "address": addr_display,
                "join_key": join_key,
                "reason": "no Instacart location_code matched this normalized address+zip",
            })
            continue

        matched_lcs.add(lc)
        ic_entry = instacart_by_lc[lc]
        output_records.append({
            "location_code": lc,
            "uberall_id": loc["id"],
            "uberall_identifier": loc.get("identifier"),
            "street_address": loc["streetAndNumber"],
            "city": loc["city"],
            "state": state,
            "zip": loc["zip"],
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "instacart_shops": ic_entry["shops"],
            "instacart_location_name": ic_entry["location_name"],
        })

    # Instacart location_codes with no matching Uberall record.
    for lc, entry in instacart_by_lc.items():
        if lc in matched_lcs:
            continue
        addr = entry["address"]
        addr_display = (
            f"{addr.get('street_address', '')}, "
            f"{addr.get('city', '')}, "
            f"{addr.get('state', '')} "
            f"{addr.get('postal_code', '')}"
        ).strip(", ")
        mismatches.append({
            "type": "instacart_unmatched",
            "location_code": lc,
            "address": addr_display,
            "fulfillment_options": list(entry["shops"].keys()),
            "reason": "no Uberall record matched this Instacart location_code by normalized address+zip",
        })

    # Append duplicate-mode conflicts to the mismatch log.
    mismatches.extend(duplicate_mode_mismatches)

    # ── Write output files ────────────────────────────────────────────────────
    with REGISTRY_FILE.open("w") as f:
        for rec in output_records:
            f.write(json.dumps(rec) + "\n")

    with MISMATCHES_FILE.open("w") as f:
        for m in mismatches:
            f.write(json.dumps(m) + "\n")

    # ── Summary ───────────────────────────────────────────────────────────────
    n_uberall_unmatched = sum(1 for m in mismatches if m["type"] == "uberall_unmatched")
    n_ic_unmatched = sum(1 for m in mismatches if m["type"] == "instacart_unmatched")
    n_other_mismatches = len(mismatches) - n_uberall_unmatched - n_ic_unmatched
    n_all_three = sum(1 for r in output_records if len(r["instacart_shops"]) == 3)
    n_partial = sum(1 for r in output_records if 0 < len(r["instacart_shops"]) < 3)
    n_delivery = sum(1 for r in output_records if "delivery" in r["instacart_shops"])

    print()
    print("=" * 64)
    print("SUMMARY")
    print("=" * 64)
    print(f"Uberall locations (input):            {len(uberall_locs)}")
    print(f"Matched output records:               {len(output_records)}")
    print(f"  of which — all 3 fulfillment modes: {n_all_three}")
    print(f"  of which — partial modes only:      {n_partial}")
    print(f"  of which — has delivery shopId:     {n_delivery}")
    print(f"Instacart location_codes found:       {len(instacart_by_lc)}")
    print(f"Uberall unmatched:                    {n_uberall_unmatched}")
    print(f"Instacart unmatched:                  {n_ic_unmatched}")
    print(f"Other mismatches / collisions:        {n_other_mismatches}")
    print()
    print(f"Registry:   {REGISTRY_FILE}")
    print(f"Mismatches: {MISMATCHES_FILE}")
    print(f"Zip cache:  {ZIP_CACHE_FILE}")


if __name__ == "__main__":
    main()
