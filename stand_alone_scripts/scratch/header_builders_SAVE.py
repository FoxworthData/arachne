import base64
import json
import time
import urllib
from datetime import datetime, timedelta
from urllib import parse
import uuid
from abc import ABC, abstractmethod

from fake_useragent import UserAgent

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
    #
    # def location_cookie(self):
    #     "Builds a cookie string for the specified store ID and zip code."
    #     timestamp = int(time.time())
    #     acid = str(uuid.uuid4())
    #
    #     # Simplify the location_guest_data
    #     location_guest_data = {
    #         "intent": "SHIPPING",
    #         "storeIntent": "PICKUP",
    #         "pickup": {
    #             "nodeId": self.store_id,
    #             "timestamp": timestamp
    #         },
    #         "postalCode": {
    #             "base": self.store_zip_code,
    #             "timestamp": timestamp
    #         },
    #         "validateKey": f"prod:v2:{acid}"
    #     }
    #
    #     # Encode the simplified data
    #     encoded_location_data = base64.urlsafe_b64encode(json.dumps(location_guest_data).encode()).decode()
    #
    #     # Return a smaller cookie string
    #     return f"ACID={acid}; hasACID=true; hasLocData=1; assortmentStoreId={self.store_id}; locGuestData={encoded_location_data}"

    def encode_locDataV3(self, data: dict) -> str:
        # Step 1: Convert to compact JSON string
        json_str = json.dumps(data, separators=(',', ':'))

        # Step 2: Base64 URL-safe encoding
        base64_bytes = base64.urlsafe_b64encode(json_str.encode('utf-8'))
        base64_str = base64_bytes.decode('utf-8')

        # Step 3: URL encode the base64 string
        url_encoded = urllib.parse.quote(base64_str)

        return url_encoded

    # def location_cookie(self):
    #     "Builds a cookie string for the specified store ID and zip code."
    #     acid = str(uuid.uuid4())
    #
    #     # Simplify the location_guest_data
    #     location_guest_data = {
    #         'intent': 'PICKUP',
    #         'isDefaulted': False,
    #         'isExplicit': False,
    #         'mergeFlag': True,
    #         'mp': [],
    #         'mpUniqueSellerCount': 0,
    #         'pickup': {
    #             'nodeId': self.store_id,
    #             'selectionSource': 'Pickup Store Selector',
    #             'selectionType': 'CUSTOMER_SELECTED',
    #             'timestamp': int(time.time())
    #         },
    #         'shippingAddress': {'city': self.store_city,
    #                             'deliveryStoreList': [{'deliveryTier': None,
    #                                                    'nodeId': self.store_id,
    #                                                    'selectionSource': 'ZIP_CODE_BY_USER',
    #                                                    'selectionType': 'LS_SELECTED',
    #                                                    'timestamp': int(time.time()),
    #                                                    'type': 'DELIVERY'}],
    #                             'giftAddress': False,
    #                             'postalCode': self.store_zip_code,
    #                             'state': self.store_state,
    #                             'timestamp': int(time.time()),
    #                             'type': 'partial-location'},
    #         'showLMPEntryPoint': False,
    #         'showLocalExperience': False,
    #         'storeIntent': 'PICKUP',
    #         'postalCode': {
    #             'base': self.store_zip_code,
    #             'timestamp': int(time.time())
    #         },
    #         'validateKey': f'prod:v2:{acid}'
    #     }
    #
    #     locDataV3 = {'assortment': {'displayName': self.store_display_name,
    #                                'intent': 'PICKUP',
    #                                'nodeId': self.store_id},
    #                 'delivery': {'accessPoints': [{'accessType': 'DELIVERY_ADDRESS'}],
    #                              'address': {'addressLine1': self.store_address.upper(),
    #                                          'city': self.store_city,
    #                                          'country': self.store_country,
    #                                          'postalCode': self.store_zip_code,
    #                                          'state': self.store_state,},
    #                              'allowedWICAgencies': [self.store_state],
    #                              'displayName': self.store_display_name,
    #                              # 'geoPoint': {'latitude': 30.221033, 'longitude': -97.753926},
    #                              'isExpressDeliveryOnly': False,
    #                              'nodeId': self.store_id,
    #                              'scheduledEnabled': False,
    #                              'selectionType': 'LS_SELECTED',
    #                              'storeBrandFormat': self.store_brand_format,
    #                              'supportedAccessTypes': ['DELIVERY_ADDRESS', 'ACC'],
    #                              'timeZone': self.store_time_zone,
    #                              'unScheduledEnabled': False},
    #                 'instore': False,
    #                 'intent': 'PICKUP',
    #                 'isDefaulted': False,
    #                 'isExplicit': False,
    #                 'isgeoIntlUser': False,
    #                 # 'mpDelStoreCount': 4,
    #                 # 'mps': ['1520219',
    #                 #         '1522755',
    #                 #         '1523726',
    #                 #         '1520509',
    #                 #         '1519929',
    #                 #         '1520720',
    #                 #         '1518348',
    #                 #         '1524578',
    #                 #         '1518800',
    #                 #         '1518387',
    #                 #         '1518408',
    #                 #         '1520502',
    #                 #         '1518386',
    #                 #         '1518782',
    #                 #         '1525141',
    #                 #         '1518383'],
    #                 'pickup': [{'address': {'addressLine1': self.store_address.upper(),
    #                                         'city': self.store_city,
    #                                         'country': self.store_country,
    #                                         'postalCode': self.store_zip_code,
    #                                         'state': self.store_state,},
    #                             'allowedWICAgencies': [self.store_state],
    #                             'displayName': self.store_display_name,
    #                             # 'geoPoint': {'latitude': 30.221033, 'longitude': -97.753926},
    #                             'nodeId': self.store_id,
    #                             'scheduledEnabled': True,
    #                             'selectionType': 'CUSTOMER_SELECTED',
    #                             'storeBrandFormat': self.store_brand_format,
    #                             # 'storeHrs': '06:00-23:00',
    #                             'supportedAccessTypes': ['ACC_INGROUND',
    #                                                      'ACC',
    #                                                      'PICKUP_CURBSIDE',
    #                                                      'PICKUP_INSTORE',
    #                                                      'PICKUP_SPECIAL_EVENT',
    #                                                      'PICKUP_BAKERY'],
    #                             'timeZone': self.store_time_zone,
    #                             'unScheduledEnabled': True},
    #                            # {'nodeId': '2133'},
    #                            # {'nodeId': '5317'},
    #                            # {'nodeId': '4554'},
    #                            # {'nodeId': '1185'},
    #                            # {'nodeId': '4219'},
    #                            # {'nodeId': '3569'},
    #                            # {'nodeId': '3169'},
    #                            # {'nodeId': '1129'}
    #                            ],
    #                 'refreshAt': int(time.time()),
    #                 'shippingAddress': {'allowedWICAgencies': [self.store_state],
    #                                     'city': self.store_city,
    #                                     'countryCode': self.store_country,
    #                                     'giftAddress': False,
    #                                     # 'latitude': 30.2432,
    #                                     # 'longitude': -97.7638,
    #                                     'postalCode': self.store_zip_code,
    #                                     'state': self.store_state,
    #                                     'timeZone': self.store_time_zone,},
    #                 'validateKey': f'prod:v2:{acid}'}
    #
    #     # Encode the simplified data
    #     encoded_location_guest_data = base64.urlsafe_b64encode(json.dumps(location_guest_data).encode()).decode()
    #     encoded_locDataV3 = self.encode_locDataV3(locDataV3)
    #
    #     return f"hasLocData=1; ACID={acid}; locGuestData={encoded_location_guest_data}; assortmentStoreId={self.store_id}; hasACID=true; locDataV3={encoded_locDataV3}"

    def location_cookie(self):
        "Builds a cookie string for the specified store ID and zip code."
        acid = str(uuid.uuid4())
        acid = 'da6245c7-0a44-41f2-a733-731749b1af0f'

        address_timestamp = 1737403301901
        address_timestamp = int(time.time())*1000

        deliveryStoreList_timestamp = 1747759167114
        deliveryStoreList_timestamp = int(time.time())*1000

        # refreshAt_timestamp = 1747807598699

        # Current UTC datetime
        now = datetime.utcnow()

        # Current timestamp (in seconds)
        current_timestamp = int(now.timestamp())

        # Timestamp in the future
        future = now + timedelta(hours=6)
        refreshAt_timestamp = int(future.timestamp()*1000)
        # refreshAt_timestamp = 1747860315936
        # refreshAt_timestamp = 1747860314936

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

        filename = '/Users/dalesmith/Projects/arachne/data/walmart_cookies_1198_store_selection_20250520.json'

        # Load the cookies from file
        with open(filename, "r") as f:
            cookies = json.load(f)

        # encoded_location_guest_data = next(
        #     (cookie["value"] for cookie in cookies if cookie["name"] == "locGuestData"),
        #     None  # Default if not found
        # )

        # encoded_locDataV3 = next(
        #     (cookie["value"] for cookie in cookies if cookie["name"] == "locDataV3"),
        #     None  # Default if not found
        # )


        return f"hasLocData=1; ACID={acid}; locGuestData={encoded_location_guest_data}; assortmentStoreId={self.store_id}; hasACID=true; locDataV3={encoded_locDataV3}"

    #
    # def location_cookie(self):
    #     filename = '/Users/dalesmith/Projects/arachne/data/walmart_cookies_1198_store_selection_20250520.json'
    #
    #     # Load the cookies from file
    #     with open(filename, "r") as f:
    #         cookies = json.load(f)
    #
    #     # Build the cookie string
    #     cookie_string = "; ".join(f"{cookie['name']}={cookie['value']}"
    #                               for cookie in cookies if cookie['name'] in ['hasLocData',
    #                                                                           # '_shcc',
    #                                                                           # 'bm_mi',
    #                                                                           'ACID',
    #                                                                           # '_intlbu',
    #                                                                           'locGuestData',
    #                                                                           # '_m',
    #                                                                           # 'userAppVersion',
    #                                                                           # 'bm_sv',
    #                                                                           # 'akavpau_p1',
    #                                                                           'assortmentStoreId',
    #                                                                           # 'auth',
    #                                                                           'hasACID',
    #                                                                           'locDataV3'
    #                                                                           ])
    #
    #     return cookie_string

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
