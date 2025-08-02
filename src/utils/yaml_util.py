import random

import yaml



def load_store_directories_by_state(state_code: str, yaml_file: str = '../data/Walmart_store_directories_by_state_retry.yaml') -> dict:
    with open(yaml_file, 'r') as file:
        state_directories = yaml.safe_load(file)

    # Find the state data
    city_directories = next((entry for entry in state_directories if entry['state'] == state_code.lower()), None)

    if not city_directories:
        return []

    # Convert list of cities to a dictionary
    # return {city['city']: city['url'] for city in city_directories['cities']}
    return city_directories['cities']



def load_store_by_id(store_id: str, yaml_file: str = '../data/Walmart_stores.yaml') -> dict:
    with open(yaml_file, 'r') as file:
        stores = yaml.safe_load(file)

    for store in stores:
        if store.get('store_id') == store_id:
            return store

    raise ValueError(f"Store with store_id {store_id} not found.")


def load_search_by_query(query: str, yaml_file: str = '../data/Walmart_fetch_search.yaml') -> dict:
    query_lower = query.lower()

    with open(yaml_file, 'r') as file:
        saved_queries = yaml.safe_load(file)

    for saved_query in saved_queries:
        if saved_query.get('query', '').lower() == query_lower:
            return saved_query

    raise ValueError(f"Search with query '{query}' not found.")


def get_random_products(yaml_file: str = '../data/Walmart_products.yaml', n: int = 10) -> list:
    """
    Load a YAML file and return `n` random entries.

    Args:
        yaml_file (str): Path to the YAML file.
        n (int): Number of random entries to return.

    Returns:
        list: List of random entries.
    """
    with open(yaml_file, 'r') as f:
        entries = yaml.safe_load(f)

    return random.sample(entries, min(n, len(entries)))