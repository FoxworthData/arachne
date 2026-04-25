import base64
import json
import time
import urllib
from datetime import datetime, timedelta
from urllib import parse
import uuid
from abc import ABC, abstractmethod

from fake_useragent import UserAgent

from src.utils.browser_personas import BrowserPersona


class RetailerHeaderBuilder(ABC):
    @abstractmethod
    def build_headers(self):
        pass

class WalmartHeaderBuilder(RetailerHeaderBuilder):
    def __init__(self, store_identification: dict):
        self.store_id = store_identification['store_id']
        self.store_address = store_identification['store_address']
        self.store_city = store_identification['store_city']
        self.store_state = store_identification['store_state']
        self.store_zip_code = store_identification['store_zip_code']
        self.store_country = store_identification['store_country']
        self.store_country_code = store_identification['store_country_code']
        self.store_display_name = store_identification['store_display_name']
        self.store_brand_format = store_identification['store_brand_format']
        self.store_time_zone = store_identification['store_time_zone']

    def encode_locDataV3(self, data: dict) -> str:
        # Step 1: Convert to compact JSON string
        json_str = json.dumps(data, separators=(',', ':'))

        # Step 2: Base64 URL-safe encoding
        base64_bytes = base64.urlsafe_b64encode(json_str.encode('utf-8'))
        base64_str = base64_bytes.decode('utf-8')

        # Step 3: URL encode the base64 string
        url_encoded = urllib.parse.quote(base64_str)

        return url_encoded

    def location_cookie(self):
        "Builds a cookie string for the specified store ID and zip code."
        acid = str(uuid.uuid4())
        # acid = 'da6245c7-0a44-41f2-a733-731749b1af0f'

        address_timestamp = int(time.time())*1000
        deliveryStoreList_timestamp = int(time.time())*1000

        # Current UTC datetime
        now = datetime.utcnow()

        # Timestamp in the future
        future = now + timedelta(hours=6)
        refreshAt_timestamp = int(future.timestamp()*1000)

        # Simplify the location_guest_data
        location_guest_data = {'intent': 'PICKUP',
 'isDefaulted': False,
 'isExplicit': False,
 'mergeFlag': True,
 'mp': [],
 'pickup': {'nodeId': self.store_id,
            'selectionSource': 'Pickup Store Selector',
            'selectionType': 'CUSTOMER_SELECTED',
            'timestamp': address_timestamp},
 'postalCode': {'base': self.store_zip_code, 'timestamp': address_timestamp},
 'shippingAddress': {'city': self.store_city,
                     'deliveryStoreList': [{'deliveryTier': None,
                                            'nodeId': self.store_id,
                                            'selectionSource': 'ZIP_CODE_BY_USER',
                                            'selectionType': 'LS_SELECTED',
                                            'timestamp': deliveryStoreList_timestamp,
                                            'type': 'DELIVERY'}],
                     'giftAddress': False,
                     'postalCode': self.store_zip_code,
                     'state': self.store_state,
                     'timestamp': address_timestamp,
                     'type': 'partial-location'},
 'showLMPEntryPoint': False,
 'showLocalExperience': False,
 'storeIntent': 'PICKUP',
 'validateKey': f'prod:v2:{acid}'}

        locDataV3 = {'assortment': {'intent': 'PICKUP',
                'nodeId': self.store_id},
 'delivery': {'accessPoints': [{'accessType': 'DELIVERY_ADDRESS'}],
              'address': {'addressLine1': self.store_address,
                          'city': self.store_city,
                          'country': self.store_country,
                          'postalCode': self.store_zip_code,
                          'state': self.store_state},
              'allowedWICAgencies': [self.store_state],
              'isExpressDeliveryOnly': False,
              'nodeId': self.store_id,
              'scheduledEnabled': False,
              'selectionType': 'LS_SELECTED',
              'supportedAccessTypes': ['DELIVERY_ADDRESS', 'ACC'],
              'timeZone': self.store_time_zone,
              'unScheduledEnabled': False},
 'instore': False,
 'intent': 'PICKUP',
 'isDefaulted': False,
 'isExplicit': False,
 'isgeoIntlUser': False,
 'pickup': [{'address': {'addressLine1': self.store_address,
                         'city': self.store_city,
                         'country': self.store_country,
                         'postalCode': self.store_zip_code,
                         'state': self.store_state},
             'allowedWICAgencies': [self.store_state],
             'nodeId': self.store_id,
             'scheduledEnabled': True,
             'selectionType': 'CUSTOMER_SELECTED',
             'timeZone': self.store_time_zone,
             'unScheduledEnabled': True},
            ],
 'refreshAt': refreshAt_timestamp,
 'shippingAddress': {'allowedWICAgencies': [self.store_state],
                     'city': self.store_city,
                     'countryCode': 'USA',
                     'giftAddress': False,
                     'postalCode': self.store_zip_code,
                     'state': self.store_state,
                     'timeZone': self.store_time_zone},
 'validateKey': f'prod:v2:{acid}'}

        # Encode the simplified data
        encoded_location_guest_data = base64.urlsafe_b64encode(json.dumps(location_guest_data).encode()).decode()
        encoded_locDataV3 = self.encode_locDataV3(locDataV3)

        return f"hasLocData=1; ACID={acid}; locGuestData={encoded_location_guest_data}; assortmentStoreId={self.store_id}; hasACID=true; locDataV3={encoded_locDataV3}"

    def get_random_user_agent(self):
        # Instantiate the UserAgent class with a browser list
        user_agents = UserAgent(browsers=['safari', 'chrome'])
        user_agent = user_agents.random
        return user_agent

    def build_headers(self):
        ac = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
        headers = {
            "Accept": ac,
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": self.location_cookie(),
            "Referer": "https://www.google.com",
            "Connection": "Keep-Alive",
            "User-Agent": self.get_random_user_agent(),
        }
        return headers


class FashionphileHeaderBuilder(RetailerHeaderBuilder):
    def __init__(self, store_identification: dict):
        self.store_id = store_identification['store_id']
        self.store_address = store_identification['store_address']
        self.store_city = store_identification['store_city']
        self.store_state = store_identification['store_state']
        self.store_zip_code = store_identification['store_zip_code']
        self.store_country = store_identification['store_country']
        self.store_country_code = store_identification['store_country_code']
        self.store_display_name = store_identification['store_display_name']
        self.store_brand_format = store_identification['store_brand_format']
        self.store_time_zone = store_identification['store_time_zone']

    def encode_locDataV3(self, data: dict) -> str:
        # Step 1: Convert to compact JSON string
        json_str = json.dumps(data, separators=(',', ':'))

        # Step 2: Base64 URL-safe encoding
        base64_bytes = base64.urlsafe_b64encode(json_str.encode('utf-8'))
        base64_str = base64_bytes.decode('utf-8')

        # Step 3: URL encode the base64 string
        url_encoded = urllib.parse.quote(base64_str)

        return url_encoded

    def location_cookie(self):
        "Builds a cookie string for the specified store ID and zip code."
        acid = str(uuid.uuid4())
        # acid = 'da6245c7-0a44-41f2-a733-731749b1af0f'

        address_timestamp = int(time.time())*1000
        deliveryStoreList_timestamp = int(time.time())*1000

        # Current UTC datetime
        now = datetime.utcnow()

        # Timestamp in the future
        future = now + timedelta(hours=6)
        refreshAt_timestamp = int(future.timestamp()*1000)

        # Simplify the location_guest_data
        location_guest_data = {'intent': 'PICKUP',
 'isDefaulted': False,
 'isExplicit': False,
 'mergeFlag': True,
 'mp': [],
 'pickup': {'nodeId': self.store_id,
            'selectionSource': 'Pickup Store Selector',
            'selectionType': 'CUSTOMER_SELECTED',
            'timestamp': address_timestamp},
 'postalCode': {'base': self.store_zip_code, 'timestamp': address_timestamp},
 'shippingAddress': {'city': self.store_city,
                     'deliveryStoreList': [{'deliveryTier': None,
                                            'nodeId': self.store_id,
                                            'selectionSource': 'ZIP_CODE_BY_USER',
                                            'selectionType': 'LS_SELECTED',
                                            'timestamp': deliveryStoreList_timestamp,
                                            'type': 'DELIVERY'}],
                     'giftAddress': False,
                     'postalCode': self.store_zip_code,
                     'state': self.store_state,
                     'timestamp': address_timestamp,
                     'type': 'partial-location'},
 'showLMPEntryPoint': False,
 'showLocalExperience': False,
 'storeIntent': 'PICKUP',
 'validateKey': f'prod:v2:{acid}'}

        locDataV3 = {'assortment': {'intent': 'PICKUP',
                'nodeId': self.store_id},
 'delivery': {'accessPoints': [{'accessType': 'DELIVERY_ADDRESS'}],
              'address': {'addressLine1': self.store_address,
                          'city': self.store_city,
                          'country': self.store_country,
                          'postalCode': self.store_zip_code,
                          'state': self.store_state},
              'allowedWICAgencies': [self.store_state],
              'isExpressDeliveryOnly': False,
              'nodeId': self.store_id,
              'scheduledEnabled': False,
              'selectionType': 'LS_SELECTED',
              'supportedAccessTypes': ['DELIVERY_ADDRESS', 'ACC'],
              'timeZone': self.store_time_zone,
              'unScheduledEnabled': False},
 'instore': False,
 'intent': 'PICKUP',
 'isDefaulted': False,
 'isExplicit': False,
 'isgeoIntlUser': False,
 'pickup': [{'address': {'addressLine1': self.store_address,
                         'city': self.store_city,
                         'country': self.store_country,
                         'postalCode': self.store_zip_code,
                         'state': self.store_state},
             'allowedWICAgencies': [self.store_state],
             'nodeId': self.store_id,
             'scheduledEnabled': True,
             'selectionType': 'CUSTOMER_SELECTED',
             'timeZone': self.store_time_zone,
             'unScheduledEnabled': True},
            ],
 'refreshAt': refreshAt_timestamp,
 'shippingAddress': {'allowedWICAgencies': [self.store_state],
                     'city': self.store_city,
                     'countryCode': 'USA',
                     'giftAddress': False,
                     'postalCode': self.store_zip_code,
                     'state': self.store_state,
                     'timeZone': self.store_time_zone},
 'validateKey': f'prod:v2:{acid}'}

        # Encode the simplified data
        encoded_location_guest_data = base64.urlsafe_b64encode(json.dumps(location_guest_data).encode()).decode()
        encoded_locDataV3 = self.encode_locDataV3(locDataV3)

        return f"hasLocData=1; ACID={acid}; locGuestData={encoded_location_guest_data}; assortmentStoreId={self.store_id}; hasACID=true; locDataV3={encoded_locDataV3}"

    def get_random_user_agent(self):
        # Instantiate the UserAgent class with a browser list
        user_agents = UserAgent(browsers=['safari', 'chrome'])
        user_agent = user_agents.random
        return user_agent

    def build_headers(self):
        ac = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
        headers = {
            "Accept": ac,
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": self.location_cookie(),
            "Referer": "https://www.google.com",
            "Connection": "Keep-Alive",
            "User-Agent": self.get_random_user_agent(),
        }
        return headers

class FashionphileCookieSeedingHeaderBuilder:
    """Header builder for Fashionphile with cookie seeding support"""
    def __init__(self, store_identification:dict, browser_persona:BrowserPersona):
        # Fashionphile doesn't need complex location data like Walmart
        self.store_id = store_identification.get('store_id', 'website')
        self.browser_persona = browser_persona

        self.initial_headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'priority': 'u=0, i',
                'sec-ch-ua': self.browser_persona.sec_ch_ua,
                'sec-ch-ua-mobile': self.browser_persona.sec_ch_ua_mobile,
                'sec-ch-ua-platform': self.browser_persona.sec_ch_ua_platform,
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': self.browser_persona.user_agent
            }

        # Fashionphile uses simple initial cookies, not location-based ones
        self.initial_cookies = {
            'fpCookieAccept': 'true',
            'identityId': str(uuid.uuid4()),
            'ajs_anonymous_id': str(uuid.uuid4())
        }
