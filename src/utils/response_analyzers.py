import re


async def walmart_response_analyzer(response, url, headers, logger, store_identification, check_store_identification: bool = True):
    text = await response.text()

    """Checks Walmart's response for bot detection, browser rejection, and store ID validation"""
    blocked = "Robot or human" in text
    browser_rejected = f"Sorry, Walmart site doesn't work with your browser." in text
    store_id_found = f'"storeId":"{store_identification['store_id']}"' in text

    if blocked:
        logger.error(f"❌ Walmart detected bot activity and blocked the request.")
        raise ValueError(f"Walmart detected bot activity and blocked the request for url: {url}.")
        # return {"success": False, "reason": "Bot detected"}
    else:
        logger.info(f"✅ Not blocked by Walmart. Continuing with scraping...")

    if browser_rejected:
        logger.warning(f"⚠️ Walmart rejected the browser User-Agent.")
        raise ValueError(f"Walmart rejected the browser User-Agent for url: {url}.")
        # return {"success": False, "reason": "User-Agent rejected"}
    else:
        logger.info(f"✅ Browser User-Agent accepted by Walmart. Continuing with scraping...")

    if check_store_identification:
        if store_id_found:
            logger.info(f"✅ Store ID {store_identification['store_id']} found in response.")
        else:
            logger.warning(f"⚠️ Store ID {store_identification['store_id']} not found in response.")

            # --- Start of new code ---
            # Use regex to find what store ID *is* in the text
            match = re.search(r'"storeId":"(\d+)"', text)
            if match:
                found_id = match.group(1)  # Extracts the number from the pattern
                logger.warning(f"Found store ID '{found_id}' instead.")
            else:
                logger.warning("No 'storeId' pattern found in the HTML response.")
            # --- End of new code ---

            raise ValueError(f"Store ID {store_identification['store_id']} not found in response for url: {url}.")
            # return {"success": False, "reason": "Store ID not found in response."}

    logger.info("🟢 Scraping successful. Response passed all checks.")
    return True

async def fashionphile_response_analyzer(response, url, headers, logger, store_identification, check_store_identification: bool = False):
    text = await response.text()

    """Checks fashionphile's response for bot detection, browser rejection"""
    blocked = "Robot or human" in text
    browser_rejected = f"Sorry, fashionphile site doesn't work with your browser." in text
    store_id_found = f'"storeId":"{store_identification['store_id']}"' in text

    if blocked:
        logger.error(f"❌ fashionphile detected bot activity and blocked the request.")
        raise ValueError(f"fashionphile detected bot activity and blocked the request for url: {url}.")
        # return {"success": False, "reason": "Bot detected"}
    else:
        logger.info(f"✅ Not blocked by fashionphile. Continuing with scraping...")

    if browser_rejected:
        logger.warning(f"⚠️ fashionphile rejected the browser User-Agent.")
        raise ValueError(f"fashionphile rejected the browser User-Agent for url: {url}.")
        # return {"success": False, "reason": "User-Agent rejected"}
    else:
        logger.info(f"✅ Browser User-Agent accepted by fashionphile. Continuing with scraping...")


    logger.info("🟢 Scraping successful. Response passed all checks.")
    return True
