"""Aldi store lookup utility.

Loads store records from data/aldi_store_registry.jsonl, mirroring the
pattern of yaml_util.load_store_by_id() for Walmart. Path is anchored
through src/utils/paths.py:DATA_DIR rather than being cwd-relative.
"""
import json
from typing import Optional

from src.utils.paths import DATA_DIR


def load_aldi_store_by_location_code(
    location_code: str,
    registry_file: Optional[str] = None,
) -> dict:
    """Return the registry record for the given Aldi location_code.

    Args:
        location_code: Store identifier in NNN-NNN format, e.g. "444-089".
        registry_file: Path to the JSONL registry. Defaults to
                       data/aldi_store_registry.jsonl resolved through DATA_DIR.

    Returns:
        The matching registry record dict, which includes keys:
            location_code, street_address, city, state, zip, lat, lng,
            instacart_shops (delivery/pickup/instore shopIds),
            instacart_location_name.

    Raises:
        ValueError: If no record matches the given location_code.
    """
    registry_file = registry_file or str(DATA_DIR / "aldi_store_registry.jsonl")

    with open(registry_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("location_code") == location_code:
                return record

    raise ValueError(
        f"Aldi store '{location_code}' not found in {registry_file}. "
        "Use a location_code value from data/aldi_store_registry.jsonl."
    )
