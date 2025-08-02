import asyncio
import base64
import json
import urllib.parse

import pprint

from src.utils.header_builders import WalmartHeaderBuilder


def decode_cookie_data(encoded_str):
    """Decode Walmart's locGuestData cookie value."""
    # Fix padding if missing (base64 strings often drop "=" padding)
    padding = '=' * (-len(encoded_str) % 4)
    encoded_str += padding

    decoded_bytes = base64.urlsafe_b64decode(encoded_str)
    decoded_str = decoded_bytes.decode()
    return json.loads(decoded_str)


def decode_cookie_data_with_url_decode(encoded_cookie_value):
    # Step 1: URL-decode
    url_decoded = urllib.parse.unquote(encoded_cookie_value)

    # Step 2: Fix base64 padding if needed
    padded = url_decoded + '=' * (-len(url_decoded) % 4)

    # Step 3: Base64-decode
    decoded_bytes = base64.urlsafe_b64decode(padded)

    # Step 4: Convert to string and parse JSON
    decoded_str = decoded_bytes.decode('utf-8')
    return json.loads(decoded_str)


def match_cookies():
    store_identification = {
        'store_id': 1198,
        'store_address': '1515 North Loop 1604 East',
        'store_city': 'San Antonio',
        'store_state': 'TX',
        'store_zip_code': 78232,
        'store_country': 'US',
        'store_country_code': 'USA',
        'store_display_name': 'San Antonio Supercenter',
        'store_brand_format': 'Walmart Supercenter',
        'store_time_zone': 'America/Chicago'
    }

    header_builder = WalmartHeaderBuilder(store_identification)
    location_cookie = header_builder.location_cookie()
    # Split and parse the cookie string
    cookie_dict = {
        k.strip(): urllib.parse.unquote(v.strip())
        for k, v in (pair.split("=", 1) for pair in location_cookie.split(";"))
    }
    # Convert to JSON string (optional)
    cookie_json = json.dumps(cookie_dict, indent=2)
    filename = '/Users/dalesmith/Projects/arachne/data/walmart_cookies_1198_store_selection_20250520.json'
    # Load the cookies from file
    with open(filename, "r") as f:
        file_cookies = json.load(f)
    file_cookie_string = "; ".join(f"{file_cookie['name']}={file_cookie['value']}"
                                   for file_cookie in file_cookies if file_cookie['name'] in ['hasLocData',
                                                                                              # '_shcc',
                                                                                              # 'bm_mi',
                                                                                              'ACID',
                                                                                              # '_intlbu',
                                                                                              'locGuestData',
                                                                                              # '_m',
                                                                                              # 'userAppVersion',
                                                                                              # 'bm_sv',
                                                                                              # 'akavpau_p1',
                                                                                              'assortmentStoreId',
                                                                                              # 'auth',
                                                                                              'hasACID',
                                                                                              'locDataV3'
                                                                                              ])
    # Split and parse the cookie string
    file_cookie_dict = {
        k.strip(): urllib.parse.unquote(v.strip())
        for k, v in (pair.split("=", 1) for pair in file_cookie_string.split(";"))
    }
    # Convert to JSON string (optional)
    file_cookie_json = json.dumps(file_cookie_dict, indent=2)
    print(f"match hasLocData: {file_cookie_dict['hasLocData'] == cookie_dict['hasLocData']}")
    print(f"file hasLocData: {file_cookie_dict['hasLocData']}")
    print(f"generated hasLocData: {cookie_dict['hasLocData']}")
    print()
    print(f"match ACID: {file_cookie_dict['ACID'] == cookie_dict['ACID']}")
    print(f"file ACID: {file_cookie_dict['ACID']}")
    print(f"generated ACID: {cookie_dict['ACID']}")
    print()
    print(f"match locGuestData: {file_cookie_dict['locGuestData'] == cookie_dict['locGuestData']}")
    print(f"file locGuestData: {file_cookie_dict['locGuestData']}")
    print(f"generated locGuestData: {cookie_dict['locGuestData']}")
    print()
    print(f"match assortmentStoreId: {file_cookie_dict['assortmentStoreId'] == cookie_dict['assortmentStoreId']}")
    print(f"file assortmentStoreId: {file_cookie_dict['assortmentStoreId']}")
    print(f"generated assortmentStoreId: {cookie_dict['assortmentStoreId']}")
    print()
    print(f"match hasACID: {file_cookie_dict['hasACID'] == cookie_dict['hasACID']}")
    print(f"file hasACID: {file_cookie_dict['hasACID']}")
    print(f"generated hasACID: {cookie_dict['hasACID']}")
    print()
    print(f"match locDataV3: {file_cookie_dict['locDataV3'] == cookie_dict['locDataV3']}")
    print(f"file locDataV3: {file_cookie_dict['locDataV3']}")
    print(f"generated locDataV3: {cookie_dict['locDataV3']}")
    print()

    return file_cookie_dict, cookie_dict

if __name__ == "__main__":
    cookie_value = "eyJpc0RlZmF1bHRlZCI6ZmFsc2UsImluc3RvcmUiOmZhbHNlLCJpbnRlbnQiOiJQSUNLVVAiLCJwaWNrdXAiOlt7Im5vZGVJZCI6IjEyNTMiLCJkaXNwbGF5TmFtZSI6IkF1c3RpbiBTdXBlcmNlbnRlciIsImFkZHJlc3MiOnsicG9zdGFsQ29kZSI6Ijc4NzA0IiwiYWRkcmVzc0xpbmUxIjoiNzEwIEUgQkVOIFdISVRFIEJMVkQiLCJjaXR5IjoiQXVzdGluIiwic3RhdGUiOiJUWCIsImNvdW50cnkiOiJVUyJ9LCJnZW9Qb2ludCI6eyJsYXRpdHVkZSI6MzAuMjIxMDMzLCJsb25naXR1ZGUiOi05Ny43NTM5MjZ9LCJzY2hlZHVsZWRFbmFibGVkIjp0cnVlLCJ1blNjaGVkdWxlZEVuYWJsZWQiOnRydWUsInN0b3JlSHJzIjoiMDY6MDAtMjM6MDAiLCJhbGxvd2VkV0lDQWdlbmNpZXMiOlsiVFgiXSwic3VwcG9ydGVkQWNjZXNzVHlwZXMiOlsiQUNDX0lOR1JPVU5EIiwiQUNDIiwiUElDS1VQX0NVUkJTSURFIiwiUElDS1VQX0lOU1RPUkUiLCJQSUNLVVBfU1BFQ0lBTF9FVkVOVCIsIlBJQ0tVUF9CQUtFUlkiXSwidGltZVpvbmUiOiJBbWVyaWNhL0NoaWNhZ28iLCJzdG9yZUJyYW5kRm9ybWF0IjoiV2FsbWFydCBTdXBlcmNlbnRlciIsInNlbGVjdGlvblR5cGUiOiJDVVNUT01FUl9TRUxFQ1RFRCJ9LHsibm9kZUlkIjoiMjEzMyJ9LHsibm9kZUlkIjoiNTMxNyJ9LHsibm9kZUlkIjoiMTE4NSJ9LHsibm9kZUlkIjoiNDU1NCJ9LHsibm9kZUlkIjoiNDIxOSJ9LHsibm9kZUlkIjoiMzU2OSJ9LHsibm9kZUlkIjoiMzE2OSJ9LHsibm9kZUlkIjoiMTEyOSJ9XSwic2hpcHBpbmdBZGRyZXNzIjp7ImxhdGl0dWRlIjozMC4yNDMyLCJsb25naXR1ZGUiOi05Ny43NjM4LCJwb3N0YWxDb2RlIjoiNzg3MDQiLCJjaXR5IjoiQXVzdGluIiwic3RhdGUiOiJUWCIsImNvdW50cnlDb2RlIjoiVVNBIiwiZ2lmdEFkZHJlc3MiOmZhbHNlLCJ0aW1lWm9uZSI6IkFtZXJpY2EvQ2hpY2FnbyIsImFsbG93ZWRXSUNBZ2VuY2llcyI6WyJUWCJdfSwiYXNzb3J0bWVudCI6eyJub2RlSWQiOiIxMjUzIiwiZGlzcGxheU5hbWUiOiJBdXN0aW4gU3VwZXJjZW50ZXIiLCJpbnRlbnQiOiJQSUNLVVAifSwiaXNFeHBsaWNpdCI6ZmFsc2UsImRlbGl2ZXJ5Ijp7Im5vZGVJZCI6IjEyNTMiLCJkaXNwbGF5TmFtZSI6IkF1c3RpbiBTdXBlcmNlbnRlciIsImFkZHJlc3MiOnsicG9zdGFsQ29kZSI6Ijc4NzA0IiwiYWRkcmVzc0xpbmUxIjoiNzEwIEUgQkVOIFdISVRFIEJMVkQiLCJjaXR5IjoiQXVzdGluIiwic3RhdGUiOiJUWCIsImNvdW50cnkiOiJVUyJ9LCJnZW9Qb2ludCI6eyJsYXRpdHVkZSI6MzAuMjIxMDMzLCJsb25naXR1ZGUiOi05Ny43NTM5MjZ9LCJzY2hlZHVsZWRFbmFibGVkIjpmYWxzZSwidW5TY2hlZHVsZWRFbmFibGVkIjpmYWxzZSwiYWNjZXNzUG9pbnRzIjpbeyJhY2Nlc3NUeXBlIjoiREVMSVZFUllfQUREUkVTUyJ9XSwiaXNFeHByZXNzRGVsaXZlcnlPbmx5IjpmYWxzZSwiYWxsb3dlZFdJQ0FnZW5jaWVzIjpbIlRYIl0sInN1cHBvcnRlZEFjY2Vzc1R5cGVzIjpbIkRFTElWRVJZX0FERFJFU1MiLCJBQ0MiXSwidGltZVpvbmUiOiJBbWVyaWNhL0NoaWNhZ28iLCJzdG9yZUJyYW5kRm9ybWF0IjoiV2FsbWFydCBTdXBlcmNlbnRlciIsInNlbGVjdGlvblR5cGUiOiJMU19TRUxFQ1RFRCJ9LCJyZWZyZXNoQXQiOjE3NDc4NjAzMTU5MzYsImlzZ2VvSW50bFVzZXIiOmZhbHNlLCJtcERlbFN0b3JlQ291bnQiOjQsIm1wcyI6WyIxNTIwMjE5IiwiMTUyMjc1NSIsIjE1MjM3MjYiLCIxNTIwNTA5IiwiMTUxOTkyOSIsIjE1MjA3MjAiLCIxNTE4MzQ4IiwiMTUyNDU3OCIsIjE1MTg4MDAiLCIxNTE4Mzg3IiwiMTUxODQwOCIsIjE1MjA1MDIiLCIxNTE4Mzg2IiwiMTUxODc4MiIsIjE1MjUxNDEiLCIxNTE4MzgzIl0sInZhbGlkYXRlS2V5IjoicHJvZDp2MjpkYTYyNDVjNy0wYTQ0LTQxZjItYTczMy03MzE3NDliMWFmMGYifQ%3D%3D"
    # decoded_data = decode_cookie_data(cookie_value)
    decoded_data = decode_cookie_data_with_url_decode(cookie_value)

    pprint.pprint(decoded_data)


    # file_cookie_dict, cookie_dict = match_cookies()

    # print("*** file locGuestData ***")
    # pprint.pprint(decode_cookie_data(file_cookie_dict['locGuestData']))
    # print()
    # print("*** generated locGuestData ***")
    # pprint.pprint(decode_cookie_data(cookie_dict['locGuestData']))

    # print("*** file locDataV3 ***")
    # pprint.pprint(decode_cookie_data_with_url_decode(file_cookie_dict['locDataV3']))
    # print()
    # print("*** generated locDataV3 ***")
    # pprint.pprint(decode_cookie_data_with_url_decode(cookie_dict['locDataV3']))

