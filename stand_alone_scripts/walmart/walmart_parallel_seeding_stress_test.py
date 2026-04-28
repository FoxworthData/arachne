"""
Walmart parallel cookie seeding stress test.

Simulates the production pattern of seeding cookies for multiple store IDs
concurrently to reproduce and measure the StoreIdMismatchError failure mode.

Usage:
    python stand_alone_scripts/walmart_parallel_seeding_stress_test.py

Adjust STORE_IDS and BATCH_SIZE at the top of the file as needed.
"""

import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from typing import List

# Resolve src/ imports from any working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv

load_dotenv()

from utils.browser_personas import BrowserPersonaChooser
from utils.header_builders import WalmartCookieSeedingHeaderBuilder
from utils.proxy_builder_simple import get_proxies
from utils.walmart_cookie_seeder import WalmartCookieSeeder
from utils.yaml_util import load_store_by_id

# ---------------------------------------------------------------------------
# Configuration — edit these to vary the experiment
# ---------------------------------------------------------------------------

STORE_IDS: List[str] = [
    '3058',
    '1313',
    '5145',
    '1347',
    '2404',
    '5245',
    '3279',
    '3106',
    '1235',
    '3888'
]

BATCH_SIZE: int = 3   # Number of store seeds to run concurrently per batch

PERSONA_OS_NAME: str = 'Windows'
PERSONA_BROWSER_NAME: str = 'Chrome'

# ---------------------------------------------------------------------------


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(store_id)s] %(message)s',
)


def make_logger(store_id: str) -> logging.LoggerAdapter:
    logger = logging.getLogger(f'seeding.{store_id}')
    return logging.LoggerAdapter(logger, {'store_id': store_id})


@dataclass
class SeedResult:
    store_id: str
    success: bool
    duration_s: float
    error: str = ''


async def seed_one_store(store_id: str) -> SeedResult:
    logger = make_logger(store_id)
    start = time.monotonic()

    try:
        store_identification = load_store_by_id(store_id=store_id)
    except ValueError as exc:
        return SeedResult(store_id=store_id, success=False,
                          duration_s=time.monotonic() - start,
                          error=f'Store lookup failed: {exc}')

    persona = BrowserPersonaChooser().get_persona(
        os_name=PERSONA_OS_NAME,
        browser_name=PERSONA_BROWSER_NAME,
    )

    header_builder = WalmartCookieSeedingHeaderBuilder(
        store_identification=store_identification,
        browser_persona=persona,
    )

    proxies = get_proxies(proxy_type='residential')

    seeder = WalmartCookieSeeder(
        retailer_store_id=store_id,
        initial_headers=header_builder.initial_headers,
        initial_cookies=header_builder.initial_cookies,
        proxies=proxies,
        logger=logger,
    )

    result = await seeder.get_seeded_cookies(browser_persona=persona)
    duration = time.monotonic() - start

    if result['success']:
        logger.info(f'SUCCESS in {duration:.2f}s')
        return SeedResult(store_id=store_id, success=True, duration_s=duration)
    else:
        error_msg = 'Seeding returned success=False (see logs above for detail)'
        logger.warning(f'FAILED in {duration:.2f}s — {error_msg}')
        return SeedResult(store_id=store_id, success=False,
                          duration_s=duration, error=error_msg)


async def run_batched(store_ids: List[str], batch_size: int) -> List[SeedResult]:
    all_results: List[SeedResult] = []

    batches = [store_ids[i:i + batch_size] for i in range(0, len(store_ids), batch_size)]
    for batch_num, batch in enumerate(batches, start=1):
        print(f'\n--- Batch {batch_num}/{len(batches)}: stores {batch} ---')
        results = await asyncio.gather(*[seed_one_store(sid) for sid in batch])
        all_results.extend(results)

    return all_results


def print_summary(results: List[SeedResult]) -> None:
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    print('\n' + '=' * 60)
    print(f'SUMMARY  |  {len(successes)} succeeded  |  {len(failures)} failed  |  {len(results)} total')
    print('=' * 60)

    if successes:
        print('\nSucceeded:')
        for r in successes:
            print(f'  store {r.store_id:>6}  {r.duration_s:5.2f}s')

    if failures:
        print('\nFailed:')
        for r in failures:
            print(f'  store {r.store_id:>6}  {r.duration_s:5.2f}s  — {r.error}')

    if results:
        failure_rate = len(failures) / len(results) * 100
        avg_duration = sum(r.duration_s for r in results) / len(results)
        print(f'\nFailure rate : {failure_rate:.1f}%')
        print(f'Avg duration : {avg_duration:.2f}s')
    print()


async def main() -> None:
    print(f'Running parallel cookie seeding test')
    print(f'  Store IDs  : {STORE_IDS}')
    print(f'  Batch size : {BATCH_SIZE}')
    print(f'  Persona    : {PERSONA_OS_NAME} / {PERSONA_BROWSER_NAME}')

    results = await run_batched(STORE_IDS, BATCH_SIZE)
    print_summary(results)


if __name__ == '__main__':
    asyncio.run(main())
