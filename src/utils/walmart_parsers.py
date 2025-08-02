import json
import os
from abc import abstractmethod, ABC
from logging import Logger
from pathlib import Path

from parsel import Selector

from src.utils.config_loader import ConfigLoader
from src.utils.file_storage import FileStorage

class WalmartParser(ABC):
    @abstractmethod
    def parse_all(self):
        pass

    @abstractmethod
    def parse(self, fetched):
        pass


class WalmartSearchParser(WalmartParser):
    def __init__(
        self,
        project_config: ConfigLoader = None,
        logger: Logger = None,
    ):
        self.project_config = project_config
        self.logger = logger
        self.file_storage = FileStorage(
            retailer='Walmart',
            project_config=self.project_config,
            logger=self.logger
        )

        self.retailer = 'Walmart'
        self.app_environment = os.environ.get("APP_ENV", "development")  # Default to 'development'
        self.fetch_type = 'search'
        self.fetched_save_location = str(Path(os.environ.get("SAVE_LOCATION"), self.retailer, self.fetch_type))
        self.parsed_save_location = str(Path(os.environ.get("PARSED_SAVE_LOCATION"), self.retailer, self.fetch_type))

    def parse_all(self):
        search_fetches = self.file_storage.list_saved_files()
        fetch_count = len(search_fetches)
        parsed_fetches = 0
        self.logger.info(f"Found {fetch_count} search fetches.")
        for search_fetch in search_fetches:
            parsed_fetches += 1
            self.logger.info(f"🔄 Parsing fetch {parsed_fetches}/{fetch_count}: {search_fetch}")
            try:
                self.parse(search_fetch)

            except Exception as e:
                self.logger.error(f"❌ Parsing failed: {e}")

    def parse(self, fetched):
        Path(self.parsed_save_location).mkdir(parents=True, exist_ok=True)
        # source_full_path = str(Path(self.forager_base_location, scrape.filename))
        source_file_name = fetched
        source_full_path = str(Path(self.fetched_save_location, source_file_name))
        # source_directory, source_file_name = os.path.split(source_full_path)
        target_filename = f"parsed_{source_file_name.replace(".html.gz", ".csv.gz")}"
        target_full_path = str(Path(self.parsed_save_location, target_filename))

        html_content = self.file_storage.get_html_content(source_full_path)
        blocked = "Robot or human?" in str(html_content)

        if blocked:
            self.logger.info("⚠️ No valid JSON product data found in the HTML file.")
            self.logger.info("This fetched file should have been marked as blocked.")
        else:
            # Extract and clean the product data
            csv_data = self.get_search_csv_data(html_content)
            if csv_data:
                saved_file_info = self.file_storage.save_cleaned_csv(csv_data, target_full_path)
                self.logger.info(f"Parsed file saved to: {target_full_path}")
            else:
                self.logger.info("⚠️ No valid JSON product data found in the HTML file.")

    def get_search_csv_data(self, html_content):
        """Extracts and cleans all product data from Walmart's JSON response inside the HTML source."""

        # Extract JSON data from Walmart's script tag
        extracted_json_data = self.extract_search_next_data(html_content)
        if not extracted_json_data:
            return []

        items = []
        item_stacks = (
            extracted_json_data.get("props", {})
            .get("pageProps", {})
            .get("initialData", {})
            .get("searchResult", {})
            .get("itemStacks", [])
        )

        for stack in item_stacks:
            for item in stack.get("items", []):
                product = {
                    # Product Identification
                    "id": item.get("id", ""),
                    "usItemId": item.get("usItemId", ""),
                    "name": item.get("name", ""),
                    "brand": item.get("brand", ""),
                    "manufacturerName": item.get("manufacturerName", ""),
                    "itemType": item.get("itemType", ""),
                    "category": self.extract_json_value(item.get("category", {}), "categoryPathId"),
                    "classType": item.get("classType", ""),
                    "keyAttributes": json.dumps(item.get("keyAttributes", {})),  # JSON string format

                    # Product Description & Details
                    "shortDescription": item.get("shortDescription", ""),
                    "description": item.get("description", ""),
                    "conditionV2": item.get("conditionV2", ""),
                    "isPreowned": item.get("isPreowned", ""),
                    "pglsCondition": item.get("pglsCondition", ""),
                    "newConditionProductId": item.get("newConditionProductId", ""),
                    "preownedCondition": item.get("preownedCondition", ""),

                    # Pricing & Discounts
                    "priceInfo": json.dumps(item.get("priceInfo", {})),  # JSON string format
                    "price": self.extract_json_value(item.get("priceInfo", {}), "linePriceDisplay"),
                    "promoDiscount": item.get("promoDiscount", ""),
                    "priceFlip": item.get("priceFlip", ""),
                    "specialBuy": item.get("specialBuy", ""),

                    # Availability & Fulfillment
                    "availabilityStatusV2": item.get("availabilityStatusV2", ""),
                    "isOutOfStock": item.get("isOutOfStock", ""),
                    "availabilityInNearbyStore": item.get("availabilityInNearbyStore", ""),
                    "availabilityStatusDisplayValue": item.get("availabilityStatusDisplayValue", ""),
                    "productLocation": item.get("productLocation", ""),
                    "productLocationDisplayValue": item.get("productLocationDisplayValue", ""),
                    "fulfillmentSpeed": item.get("fulfillmentSpeed", ""),
                    "fulfillmentSummary": item.get("fulfillmentSummary", ""),
                    "fulfillmentTitle": item.get("fulfillmentTitle", ""),
                    "fulfillmentType": item.get("fulfillmentType", ""),
                    "fulfillmentIcon": item.get("fulfillmentIcon", ""),
                    "fulfillmentBadges": json.dumps(item.get("fulfillmentBadges", [])),  # JSON string

                    # Seller Information
                    "sellerId": item.get("sellerId", ""),
                    "sellerName": item.get("sellerName", ""),
                    "hasSellerBadge": item.get("hasSellerBadge", ""),
                    "buyBoxSuppression": item.get("buyBoxSuppression", ""),

                    # Images & Media
                    "imageInfo": json.dumps(item.get("imageInfo", {})),  # JSON string format
                    "image": self.extract_json_value(item.get("imageInfo", {}), "thumbnailUrl"),
                    "imageSize": item.get("imageSize", ""),
                    "imageID": item.get("imageID", ""),
                    "imageName": item.get("imageName", ""),

                    # Product Badges & Labels
                    "badges": json.dumps(item.get("badges", [])),  # JSON string
                    "badge": item.get("badge", ""),
                    "badgeGroups": json.dumps(item.get("badgeGroups", [])),  # JSON string
                    "flag": item.get("flag", ""),
                    "topResult": item.get("topResult", ""),

                    # Shipping & Returns
                    "snapEligible": item.get("snapEligible", ""),

                    # Sponsored & Promotional Products
                    "sponsoredProduct": item.get("sponsoredProduct", ""),
                    "isSponsoredFlag": item.get("isSponsoredFlag", ""),
                    "eventAttributes": json.dumps(item.get("eventAttributes", {})),  # JSON string
                    "annualEvent": item.get("annualEvent", ""),
                    "annualEventV2": item.get("annualEventV2", ""),
                    "blitzItem": item.get("blitzItem", ""),

                    # Product Variants & Attributes
                    "variantList": json.dumps(item.get("variantList", [])),  # JSON string
                    "variantCriteria": json.dumps(item.get("variantCriteria", {})),  # JSON string
                    "isVariantTypeSwatch": item.get("isVariantTypeSwatch", ""),

                    # Miscellaneous Fields
                    "externalInfo": json.dumps(item.get("externalInfo", {})),  # JSON string
                    "externalInfoUrl": item.get("externalInfoUrl", ""),
                    "canonicalUrl": item.get("canonicalUrl", ""),
                    "moqText": item.get("moqText", ""),
                    "groupsV2": json.dumps(item.get("groupsV2", {})),  # JSON string
                    "pac": item.get("pac", ""),
                    "mhmdFlag": item.get("mhmdFlag", ""),
                    "itemBeacon": item.get("itemBeacon", ""),
                    "productIndex": item.get("productIndex", ""),
                    "itemStackPosition": item.get("itemStackPosition", ""),
                    "seeSimilar": item.get("seeSimilar", ""),
                    "quickShop": item.get("quickShop", ""),
                    "quickShopCTALabel": item.get("quickShopCTALabel", ""),
                    "shouldLazyLoad": item.get("shouldLazyLoad", ""),
                    "isLeftSideGridItem": item.get("isLeftSideGridItem", ""),
                }

                # Exclude rows that contain only empty JSON structures
                if any(val not in ["{}", "[]", "", None] for val in product.values()):
                    items.append(product)

        return items

    def extract_search_next_data(self, html_content):
        """Extracts JSON data from the <script id="__NEXT_DATA__"> tag using XPath."""
        sel = Selector(text=html_content)
        data = sel.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        return json.loads(data) if data else None

    def extract_json_value(self, json_obj, key):
        """Extracts a specific key's value from a JSON-like dictionary."""
        try:
            return json_obj.get(key, "")
        except AttributeError:
            return json_obj  # If it's not a dictionary, return as-is


class WalmartProductParser(WalmartParser):
    def __init__(
        self,
        project_config: ConfigLoader = None,
        logger: Logger = None,
    ):
        self.project_config = project_config
        self.logger = logger
        self.file_storage = FileStorage(
            retailer='Walmart',
            project_config=self.project_config,
            logger=self.logger
        )

        self.retailer = 'Walmart'
        self.app_environment = os.environ.get("APP_ENV", "development")  # Default to 'development'
        self.fetch_type = 'product'
        self.fetched_save_location = str(Path(os.environ.get("SAVE_LOCATION"), self.retailer, self.fetch_type))
        self.parsed_save_location = str(Path(os.environ.get("PARSED_SAVE_LOCATION"), self.retailer, self.fetch_type))


    def parse_all(self):
        product_fetches = self.file_storage.list_saved_files(fetch_type='product')
        fetch_count = len(product_fetches)
        parsed_fetches = 0
        self.logger.info(f"Found {fetch_count} product fetched files.")
        for product_fetch in product_fetches:
            parsed_fetches += 1
            self.logger.info(f"🔄 Parsing scrape {parsed_fetches}/{fetch_count}: {product_fetch}")
            try:
                self.parse(product_fetch)
                self.logger.info("🟢 Parse finished successfully.")
            except Exception as e:
                self.logger.error(f"❌ Parsing failed: {e}")

    def parse(self, fetched):
        Path(self.parsed_save_location).mkdir(parents=True, exist_ok=True)
        source_file_name = fetched
        source_full_path = str(Path(self.fetched_save_location, source_file_name))
        target_filename = f"parsed_{source_file_name.replace(".html.gz", ".json.gz")}"
        target_full_path = str(Path(self.parsed_save_location, target_filename))

        html_content = self.file_storage.get_html_content(source_full_path)
        blocked = "Robot or human?" in str(html_content)

        if blocked:
            self.logger.info("⚠️ No valid JSON product data found in the HTML file.")
            self.logger.info("This scrape should have been marked as blocked.")
        else:
            # Extract and clean the product data
            json_data = self.extract_product_json(html_content)
            if json_data:
                saved_file_info = self.file_storage.save_cleaned_json(json_data, target_full_path)
                self.logger.info(f"Parsed file saved to: {target_full_path}")
            else:
                self.logger.info("⚠️ No valid JSON product data found in the HTML file.")

    def extract_product_json(self, html_content):
        sel = Selector(text=html_content)
        # Step 2: Extract __NEXT_DATA__ JSON
        next_data_json = None
        next_data_element = sel.xpath('//*[@id="__NEXT_DATA__"]/text()').get()
        if next_data_element:
            next_data_json = json.loads(next_data_element)
        # Initialize product data dictionary
        product_data = {}
        # Step 3: Extract Key Fields from __NEXT_DATA__ JSON
        if next_data_json:
            try:
                product_info = self.extract_nested(next_data_json, ["props", "pageProps", "initialData", "data"], {})
                # "seoItemMetaData", "product", "idml"], {})

                # for each in sorted(product_info["seoItemMetaData"].keys()):
                #     print(f"{each}\t{product_info["seoItemMetaData"][each]}")

                product_data["averageRating"] = self.extract_nested(product_info, ["product", "averageRating"])
                product_data["brand"] = self.extract_nested(product_info, ["product", "brand"])
                product_data["brandUrl"] = self.extract_nested(product_info, ["product", "brandUrl"])
                product_data["category"] = self.extract_nested(product_info, ["product", "category"], [])
                product_data["primaryProductId"] = self.extract_nested(product_info, ["product", "primaryProductId"])
                product_data["product_type"] = self.extract_nested(product_info, ["product", "type"])
                product_data["returnPolicy"] = self.extract_nested(product_info,
                                                                   ["product", "returnPolicy", "returnPolicyText"])
                product_data["sellerName"] = self.extract_nested(product_info, ["product", "sellerName"])
                product_data["type"] = self.extract_nested(product_info, ["product", "type"])
                product_data["upc"] = self.extract_nested(product_info, ["product", "upc"])
                product_data["usItemId"] = self.extract_nested(product_info, ["product", "usItemId"])

                product_data["brandCanonical"] = self.extract_nested(product_info,
                                                                     ["seoItemMetaData", "brandCanonical"])
                product_data["breadCrumbs"] = self.extract_nested(product_info, ["seoItemMetaData", "breadCrumbs"])

                product_data["directions"] = self.extract_nested(product_info, ["idml", "directions"])
                product_data["ingredients"] = self.extract_nested(product_info, ["idml", "ingredients"])
                product_data["longDescription"] = self.extract_nested(product_info, ["idml", "longDescription"])
                product_data["nutritionFacts"] = self.extract_nested(product_info, ["idml", "nutritionFacts"])
                product_data["productHighlights"] = self.extract_nested(product_info, ["idml", "productHighlights"])
                product_data["shortDescription"] = self.extract_nested(product_info, ["idml", "shortDescription"])
                product_data["specifications"] = self.extract_nested(product_info, ["idml", "specifications"])

                product_data["totalReviewCount"] = self.extract_nested(product_info, ["reviews", "totalReviewCount"])

            except KeyError:
                pass  # Handle cases where keys don't exist
        return product_data

    def extract_nested(self, data, keys, default=None):
        """Helper function to safely extract nested JSON values."""
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
        return data
