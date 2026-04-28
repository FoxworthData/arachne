"""AldiScrapeStrategy: scrape strategy for aldi.us via the Instacart GraphQL API.

Aldi is served by Instacart's Storefront Pro platform, which differs enough
from the aiohttp/HTML retailers that this strategy subclasses
RetailerScrapeStrategy directly rather than AiohttpScrapeStrategy:
  - Transport is curl_cffi (Chrome TLS impersonation), not aiohttp
  - Output is JSON, not HTML
  - There is no pagination — all results return in one SearchResultsPlacements
    call plus follow-up Items batch calls for overflow IDs
  - Bot detection is light (CloudFront-only); seeding is a single GET that
    returns a __Host-instacart_sid cookie

The same lazy-seeding pattern WalmartScrapeStrategy uses applies here: on
first call to run_search or run_product_lookup, the strategy seeds a
curl_cffi session with the residential proxy applied, caches it, and reuses
it for all subsequent GraphQL calls.

See docs/aldi-integration-approach.md for the architectural rationale and
docs/aldi-item-data-recon.md / docs/aldi-scraper-build-plan.md for the
GraphQL schema details and persisted query hashes.
"""
import asyncio
import gzip
import json
import time
import uuid
from datetime import datetime, timezone
from logging import Logger
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import urlencode

from src.utils.fetcher_tracking import FetchedFile, FetcherSession
from src.utils.file_namer import AldiNamer
from src.utils.file_storage import FileStorage
from src.utils.proxy_builder_simple import get_proxies
from src.utils.strategies.scrape_strategy import RetailerScrapeStrategy
from src.utils.aldi_session_seeder import seed_aldi_session

GRAPHQL_URL = "https://www.aldi.us/graphql"

# Confirmed persisted query hashes (extracted from SSR apollo-state, April 2026).
# These are stable until Instacart deploys new frontend code; the build_sha cookie
# tracks the deploy version and can be used to detect rotation.
_SEARCH_HASH = "6e6b53b10516829d9b7b9fae0cbc9b65bcbbc8792d77836f65b9db6a606057a7"
_ITEMS_HASH = "5116339819ff07f207fd38f949a8a7f58e52cc62223b535405b087e3076ebf2f"
_ITEM_DETAIL_DATA_HASH = "1498d8c45b80c63ada20d2a07c07bde2364a3c69e1252ed3dfd6a095c2f2e4c8"
_NUTRITIONAL_INFO_HASH = "9bc43a13c48e633ba4c8016118f101942a44603c5d10f913e9e471ffb730185a"

_ITEMS_BATCH_SIZE = 50
_DETAIL_DELAY_SECS = 0.3   # courtesy delay between per-item detail calls
_SEARCH_FIRST = 200        # max items to inline-hydrate in SearchResultsPlacements

_GRAPHQL_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "priority": "u=1, i",
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
    "x-ic-view-layer": "true",
}


class AldiScrapeStrategy(RetailerScrapeStrategy):
    """Aldi scrape strategy using the Instacart Storefront Pro GraphQL API."""

    def __init__(
        self,
        store_identification: dict,
        fetch_type: str,
        fetch_query: str,
        start_url: Optional[str],
        project_config: Any,
        logger: Logger,
        singleton: bool = False,
        # Aldi does not use a browser persona (no per-session cookie harvesting),
        # but the factory passes these for hierarchy uniformity. Accept and ignore.
        browser_persona: Any = None,
    ):
        # singleton is meaningless for Aldi (no paginator). Accept and ignore.
        del singleton, browser_persona, start_url

        self.retailer = "Aldi"
        self.store_identification = store_identification
        self.store_id = store_identification["location_code"]
        self.shop_id = store_identification["instacart_shops"]["delivery"]
        self.zip_code = store_identification.get("zip", "10001")
        self.fetch_type = fetch_type
        self.fetch_query = fetch_query
        self.project_config = project_config
        self.logger = logger

        self.file_storage = FileStorage("Aldi", project_config, logger)
        self.file_namer = AldiNamer("Aldi", fetch_type, self.store_id)

        self.session = FetcherSession(
            retailer="Aldi",
            store_id=self.store_id,
            fetch_type=fetch_type,
            fetch_query=fetch_query,
            url=GRAPHQL_URL,
        )

        # Set on first _ensure_seeded() call.
        self._curl_session: Optional[Any] = None
        self._seeding_lock = asyncio.Lock()

    # ── Cookie seeding ────────────────────────────────────────────────────────

    async def _ensure_seeded(self) -> None:
        """Seed an Instacart session via a single proxied GET. Runs once.

        Idempotent and concurrency-safe. Raises RuntimeError on failure;
        the strategy never silently falls back to un-seeded calls.
        """
        if self._curl_session is not None:
            return

        async with self._seeding_lock:
            if self._curl_session is not None:
                return

            self.logger.info(f"[SEEDING] Starting Aldi session seeding (store={self.store_id})")

            proxies = get_proxies(proxy_type="residential")
            # Skip proxy if credentials are not configured (e.g. local dev without .env).
            if not proxies.get("https") or "None" in proxies.get("https", ""):
                self.logger.warning(
                    "Residential proxy credentials not set; seeding Aldi session without proxy. "
                    "Set BRIGHTDATA_RESIDENTIAL_PROXY_* env vars for proxied requests."
                )
                proxies = None
            else:
                self.logger.info("Using residential proxy for Aldi session seed.")

            try:
                self._curl_session = seed_aldi_session(proxies=proxies)
            except RuntimeError as exc:
                raise RuntimeError(f"Aldi session seeding failed; aborting scrape. {exc}") from exc

            self.logger.info("[SEEDING] Aldi session seeding complete.")

    # ── GraphQL plumbing ─────────────────────────────────────────────────────

    def _call_graphql(self, operation: str, variables: dict, sha256hash: str) -> dict:
        """Execute a GET persisted-query request. Returns body['data']."""
        headers = {**_GRAPHQL_HEADERS, "x-page-view-id": str(uuid.uuid4())}
        params = urlencode({
            "operationName": operation,
            "variables": json.dumps(variables, separators=(",", ":")),
            "extensions": json.dumps(
                {"persistedQuery": {"version": 1, "sha256Hash": sha256hash}},
                separators=(",", ":"),
            ),
        })
        url = f"{GRAPHQL_URL}?{params}"
        r = self._curl_session.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"{operation} HTTP {r.status_code}: {r.text[:300]}")
        body = r.json()
        if body.get("errors"):
            raise RuntimeError(f"{operation} GraphQL errors: {body['errors']}")
        return body["data"]

    def _save_json(self, data: dict) -> tuple[str, int]:
        """Gzip-compress and save data. Returns (full_path, compressed_size)."""
        filename = self.file_namer.get_json_filename(self.fetch_query)
        out_dir = Path(self.file_storage.save_location) / "Aldi" / self.fetch_type
        out_dir.mkdir(parents=True, exist_ok=True)
        full_path = str(out_dir / filename)
        result = self.file_storage.save_cleaned_json(data, full_path)
        return full_path, result["size"]

    def _record_fetch(
        self,
        url: str,
        filename: Optional[str],
        size: int,
        status_code: int,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        self.session.add_fetched_file(FetchedFile(
            retailer="Aldi",
            store_id=self.store_id,
            fetch_type=self.fetch_type,
            fetch_query=self.fetch_query,
            url=url,
            filename=filename,
            size=size,
            page_number=None,
            fetched_time=time.time(),
            success=success,
            response_status_code=status_code,
            message=error,
        ))

    # ── Search-side helpers ──────────────────────────────────────────────────

    @staticmethod
    def _extract_search_results(data: dict) -> tuple[list, list]:
        """Split SearchResultsPlacements data into inline items and overflow IDs."""
        placements = data["searchResultsPlacements"]["placements"]
        inline_items, overflow_ids = [], []
        for placement in placements:
            content = placement.get("content") or {}
            if content.get("__typename") != "SearchContentManagementSearchItemGrid":
                continue
            items = content.get("items") or []
            if items:
                inline_items.extend(items)
            else:
                overflow_ids.extend(content.get("itemIds") or [])
        return inline_items, overflow_ids

    @staticmethod
    def _flatten_item(raw: dict) -> dict:
        """Map a raw ItemsItem record to a clean flat schema.

        Both inline (from SearchResultsPlacements) and batch (from Items)
        sources return the same ItemsItem shape; this function handles both.
        """
        price_vs = (raw.get("price") or {}).get("viewSection") or {}
        item_card = price_vs.get("itemCard") or {}
        item_details = price_vs.get("itemDetails") or {}
        avail = raw.get("availability") or {}
        item_vs = raw.get("viewSection") or {}
        image = item_vs.get("itemImage") or {}
        tracking = item_vs.get("trackingProperties") or {}
        on_sale_ind = tracking.get("on_sale_ind") or {}
        dietary = raw.get("dietary") or {}
        dietary_vs = dietary.get("viewSection") or {}
        qty = raw.get("quantityAttributes") or {}

        nutr_attrs = raw.get("nutritionalAttributes") or []
        nutrition_summary = (
            {
                a["viewSection"]["longLabelString"].lower(): a["viewSection"]["valueString"]
                for a in nutr_attrs
                if (a.get("viewSection") or {}).get("longLabelString")
            }
            or None
        )

        return {
            "id": raw.get("id"),
            "product_id": raw.get("productId"),
            "legacy_id": raw.get("legacyId"),
            "name": raw.get("name"),
            "brand": raw.get("brandName"),
            "brand_id": raw.get("brandId"),
            "size": raw.get("size"),
            "product_category": tracking.get("product_category_name"),
            "evergreen_url": raw.get("evergreenUrl"),
            "price_string": price_vs.get("priceString"),
            "price_value": price_vs.get("priceValueString"),
            "price_per_unit": item_details.get("pricePerUnitString"),
            "is_on_sale": on_sale_ind.get("on_sale"),
            "full_price_string": item_card.get("fullPriceString"),
            "discount_string": item_card.get("discountHeaderString"),
            "buy_one_get_one": on_sale_ind.get("buy_one_get_one"),
            "cpg_coupon": on_sale_ind.get("cpg_coupon"),
            "item_promotions": price_vs.get("itemPromotions") or [],
            "available": avail.get("available"),
            "stock_level": avail.get("stockLevel"),
            "ebt_eligible": raw.get("itemEbt"),
            "quantity_type": qty.get("quantityType"),
            "quantity_max": qty.get("max"),
            "image_url": image.get("url"),
            "tags": raw.get("tags") or [],
            "dietary_tags": dietary.get("mlShoppingAttributes") or [],
            "dietary_badges": [
                s["attributeString"]
                for s in (dietary_vs.get("attributeSections") or [])
                if s.get("attributeString")
            ],
            "nutrition_summary": nutrition_summary,
            "variant_group_id": raw.get("variantGroupId"),
            "variant_dimension_values": raw.get("variantDimensionValues") or [],
            "retailer_reference_code": item_vs.get("retailerReferenceCodeString"),
            "retailer_lookup_code": item_vs.get("retailerLookupCodeString"),
        }

    # ── Product detail helpers ────────────────────────────────────────────────

    @staticmethod
    def _product_id_from_item_id(item_id: str) -> str:
        """'items_396446-16902710' → '16902710'"""
        return item_id.split("-", 1)[-1]

    def _fetch_item_detail(self, item_id: str) -> dict:
        """Call ItemDetailData. Returns description/ingredients/warnings/directions/images."""
        variables = {"id": item_id, "isFeatured": False, "shopId": self.shop_id}
        data = self._call_graphql("ItemDetailData", variables, _ITEM_DETAIL_DATA_HASH)
        vs = data["itemDetail"]["viewSection"]

        sections: dict = {}
        for s in vs.get("detailSections") or []:
            header = s.get("headerString", "").lower()
            body = s.get("bodyString") or ""
            sections[header] = body

        product_sections: dict = {}
        for s in vs.get("productDetailSections") or []:
            variant = s.get("sectionTypeVariant", "").lower()
            body = s.get("bodyString") or ""
            if variant:
                product_sections[variant] = body

        images = [
            {"url": img["url"], "alt_text": img.get("altText")}
            for img in (vs.get("detailImages") or [])
        ]

        ws = vs.get("warningSection") or {}
        warning_body = ws.get("bodyString")

        return {
            "description": product_sections.get("details") or sections.get("details"),
            "ingredients": product_sections.get("ingredients") or sections.get("ingredients"),
            "directions": product_sections.get("directions") or sections.get("directions"),
            "warnings": warning_body or sections.get("warnings"),
            "images": images,
        }

    def _fetch_nutritional_info(self, product_id: str) -> Optional[dict]:
        """Call ProductNutritionalInfo. Returns None if unavailable."""
        variables = {"productId": product_id, "shopId": self.shop_id}
        try:
            data = self._call_graphql(
                "ProductNutritionalInfo", variables, _NUTRITIONAL_INFO_HASH
            )
        except RuntimeError:
            return None

        ni = (data.get("productNutritionalInfo") or {}).get("nutritionalInfo")
        if not ni:
            return None

        nutrition = {
            k: v for k, v in ni.items()
            if not k.startswith("__") and k != "viewSection"
        }
        vs = ni.get("viewSection") or {}
        display = {
            k: v for k, v in vs.items()
            if not k.startswith("__") and isinstance(v, str) and v
        }
        nutrition["display"] = display if display else None
        return nutrition

    def _load_aldi_item_ids_from_search_output(self) -> list[str]:
        """Find the latest search output for self.store_id+self.fetch_query and return item IDs.

        Reads from {SAVE_LOCATION}/Aldi/search/ and picks the most recently
        timestamped file whose name matches Aldi_search_{store_id}_{safe_query}_*.json.gz
        """
        search_dir = Path(self.file_storage.save_location) / "Aldi" / "search"

        if not search_dir.exists():
            raise FileNotFoundError(
                f"No Aldi search output directory found at {search_dir}. "
                "Run an Aldi search fetch first."
            )

        safe_query = self.fetch_query.lower().replace(" ", "_").replace("/", "_")[:30]
        pattern = f"Aldi_search_{self.store_id}_{safe_query}_*.json.gz"
        matches = sorted(search_dir.glob(pattern))

        if not matches:
            raise FileNotFoundError(
                f"No Aldi search file matching '{pattern}' in {search_dir}. "
                "Run an Aldi search fetch first."
            )

        latest = matches[-1]
        self.logger.info(f"[Aldi] Loading item IDs from {latest.name}")

        with gzip.open(latest, "rt", encoding="utf-8") as f:
            data = json.load(f)

        item_ids = [it["id"] for it in data.get("items", [])]
        self.logger.info(f"[Aldi] Loaded {len(item_ids)} item IDs")
        return item_ids

    # ── High-level run_* entry points ────────────────────────────────────────

    async def run_search(self, query: str) -> None:
        """Fetch all search results for query: SearchResultsPlacements + Items batches."""
        await self._ensure_seeded()

        # Update bookkeeping so the session summary reflects the resolved query.
        self.fetch_query = query
        self.session.fetch_query = query

        self.logger.info(
            f"[Aldi] search store={self.store_id} shop_id={self.shop_id} query={query!r}"
        )

        # Phase 1 — SearchResultsPlacements
        search_vars = {
            "filters": [],
            "action": None,
            "query": query,
            "pageViewId": str(uuid.uuid4()),
            "elevatedProductId": None,
            "searchSource": "search",
            "disableReformulation": False,
            "disableLlm": False,
            "forceInspiration": False,
            "orderBy": "bestMatch",
            "clusterId": None,
            "includeDebugInfo": False,
            "clusteringStrategy": None,
            "contentManagementSearchParams": {"itemGridColumnCount": 1},
            "shopId": self.shop_id,
            "postalCode": self.zip_code,
            "zoneId": "1",
            "first": _SEARCH_FIRST,
        }
        op_url = f"{GRAPHQL_URL}?operationName=SearchResultsPlacements"
        try:
            search_data = self._call_graphql(
                "SearchResultsPlacements", search_vars, _SEARCH_HASH
            )
            self._curl_session.headers.update(
                {"referer": f"https://www.aldi.us/store/aldi/s?k={query}"}
            )
            self._record_fetch(op_url, None, 0, 200, True)
        except RuntimeError as exc:
            self._record_fetch(op_url, None, 0, 0, False, str(exc))
            raise

        inline_items, overflow_ids = self._extract_search_results(search_data)
        total = len(inline_items) + len(overflow_ids)
        self.logger.info(
            f"[Aldi] {total} results ({len(inline_items)} inline, {len(overflow_ids)} overflow)"
        )
        if total >= _SEARCH_FIRST:
            self.logger.warning(
                f"[Aldi] result count ({total}) >= first ({_SEARCH_FIRST}); "
                "there may be additional results."
            )

        # Phase 2 — Items batch for overflow IDs
        hydrated = list(inline_items)
        batches = [
            overflow_ids[i: i + _ITEMS_BATCH_SIZE]
            for i in range(0, len(overflow_ids), _ITEMS_BATCH_SIZE)
        ]
        for i, batch in enumerate(batches, 1):
            items_vars = {
                "ids": batch,
                "shopId": self.shop_id,
                "zoneId": "1",
                "postalCode": self.zip_code,
            }
            batch_url = f"{GRAPHQL_URL}?operationName=Items"
            try:
                items_data = self._call_graphql("Items", items_vars, _ITEMS_HASH)
                self._record_fetch(batch_url, None, 0, 200, True)
            except RuntimeError as exc:
                self._record_fetch(batch_url, None, 0, 0, False, str(exc))
                raise

            batch_items = items_data.get("items") or []
            hydrated.extend(batch_items)
            self.logger.info(
                f"[Aldi] Items batch {i}/{len(batches)}: {len(batch_items)} items"
            )

        # Flatten and save
        flat_items = [self._flatten_item(it) for it in hydrated]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = {
            "meta": {
                "location_code": self.store_id,
                "shop_id": self.shop_id,
                "query": query,
                "fetched_at": timestamp,
                "item_count": len(flat_items),
            },
            "items": flat_items,
        }
        full_path, size = self._save_json(output)
        self._record_fetch(GRAPHQL_URL, Path(full_path).name, size, 200, True)
        self.logger.info(
            f"[Aldi] Saved {len(flat_items)} items → {Path(full_path).name}"
        )

    async def run_product_lookup(self) -> None:
        """Fetch detail records for items in the most recent matching search output.

        Loads item IDs from {SAVE_LOCATION}/Aldi/search/Aldi_search_{store}_{query}_*.json.gz,
        then fetches ItemDetailData + ProductNutritionalInfo per item.
        """
        await self._ensure_seeded()

        item_ids = self._load_aldi_item_ids_from_search_output()
        await self._run_detail_flow_for_ids(item_ids)

    async def _run_detail_flow_for_ids(self, item_ids: List[str]) -> None:
        """Shared body of the detail flow, used by both run_product_lookup and
        the lower-level fetch_singleton_urls entry point.
        """
        results = []
        errors = 0
        self.logger.info(f"[Aldi] product detail {len(item_ids)} items")

        for i, item_id in enumerate(item_ids, 1):
            product_id = self._product_id_from_item_id(item_id)
            item_url = f"{GRAPHQL_URL}?operationName=ItemDetailData&itemId={item_id}"
            try:
                detail = self._fetch_item_detail(item_id)
                nutrition = self._fetch_nutritional_info(product_id)
                results.append({
                    "item_id": item_id,
                    "product_id": product_id,
                    "shop_id": self.shop_id,
                    **detail,
                    "nutrition": nutrition,
                })
                self._record_fetch(item_url, None, 0, 200, True)
            except RuntimeError as exc:
                self.logger.warning(f"[Aldi] Error on {item_id}: {exc}")
                errors += 1
                self._record_fetch(item_url, None, 0, 0, False, str(exc))

            if i < len(item_ids):
                await asyncio.sleep(_DETAIL_DELAY_SECS)

            if i % 10 == 0 or i == len(item_ids):
                self.logger.info(
                    f"[Aldi] detail progress: {i}/{len(item_ids)} errors={errors}"
                )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = {
            "meta": {
                "location_code": self.store_id,
                "shop_id": self.shop_id,
                "query": self.fetch_query,
                "fetched_at": timestamp,
                "item_count": len(results),
                "error_count": errors,
            },
            "items": results,
        }
        full_path, size = self._save_json(output)
        self._record_fetch(GRAPHQL_URL, Path(full_path).name, size, 200, True)
        self.logger.info(
            f"[Aldi] Saved {len(results)} detail records → {Path(full_path).name} errors={errors}"
        )

    # ── RetailerScrapeStrategy ABC (low-level fetch primitives) ──────────────

    async def fetch_all(self, start_url: str) -> None:
        """ABC compliance. start_url is ignored — Aldi has no concept of a
        search URL to start from. Delegates to run_search using self.fetch_query.
        """
        del start_url
        await self.run_search(self.fetch_query)

    async def fetch_singleton_urls(self, urls: List[str]) -> None:
        """ABC compliance. For Aldi, `urls` are item IDs (e.g. items_14655-36953),
        not URLs. Runs the detail flow against them directly, bypassing the
        saved-search-file lookup that run_product_lookup does.
        """
        await self._ensure_seeded()
        await self._run_detail_flow_for_ids(urls)

    def get_session_summary(self) -> str:
        self.session.close()
        return self.session.to_string()
