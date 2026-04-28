# Follow-ups

Items deliberately deferred during the `feature/seeding_proxy` merge work
(commits 1 through 6, April 2026). These are real but bounded — none
block production use of `python -m src.main` against either retailer.
File a ticket, address opportunistically, or punt.

Ordered roughly from highest leverage / lowest effort first.

---

## 1. `proxy_builder_simple.get_proxies()` silently returns `None`-strings on missing env vars

**Where**: `src/utils/proxy_builder_simple.py`

**The bug**: When any of `BRIGHTDATA_RESIDENTIAL_PROXY_USER`, `_PASSWORD`,
`_HOST`, or `_PORT` is unset, `os.getenv()` returns `None` and the
function returns `{'http': 'http://None:None@None:None', 'https': '...'}`.
Callers can't tell the proxy is misconfigured; they get a syntactically
valid string that aiohttp / curl_cffi will use until something downstream
fails confusingly.

**The fix**: Raise `RuntimeError` listing the missing env vars when any
of the four is unset. One small function change, no caller changes
required.

**Why it matters**: Bit us during commit 2.6 troubleshooting — when env
vars were genuinely loaded but a shell test made it look like they
weren't, we burned time chasing a Bright Data zone issue that didn't
exist. A loud failure mode here would have cut the diagnostic short.

---

## 2. Bright Data MITM cert: replace `verify=False` with a pinned CA bundle

**Where**:
- `src/utils/aldi_session_seeder.py` (`session.verify = False`)
- `src/utils/walmart_cookie_seeder.py` (`aiohttp.TCPConnector(ssl=False)`)

**The trade-off**: Bright Data's residential proxy gateway performs
HTTPS MITM with a self-signed cert chain. Both the Aldi and Walmart
seeding paths currently disable TLS verification entirely to allow
routing through the residential pool. This is necessary today; it's
also a real reduction in TLS guarantee that should not stay in the
codebase indefinitely.

**The fix**: Install Bright Data's published CA chain locally, then in
both seeders pin `verify=<path-to-bd-ca-bundle>` instead of disabling
verification. The cert bundle is downloadable from Bright Data's
dashboard. This restores chain-of-trust verification (just trusting
their CA in addition to the system CAs) without re-introducing the
MITM wall.

**Why it matters**: `verify=False` is the kind of choice that quietly
proliferates when not flagged. Better to fix it before someone copies
the pattern into a context where the trade-off isn't justified.

---

## 3. `WalmartScrapeStrategy.run_*` methods mutate strategy state after construction

**Where**: `src/utils/strategies/walmart_scrape_strategy.py`

**The smell**: Each `run_*` method on `WalmartScrapeStrategy` updates
`self.fetch_query`, `self.start_url`, `self.session.fetch_query`, and
`self.session.url` after the fact, because those fields were set at
construction time before the strategy knew the resolved query/URL. The
strategy was built with a placeholder `fetch_query` (the raw query from
RunConfig) and `start_url=None`, then patched up inside `run_search`,
`run_store_directory`, etc.

**The fix**: Defer `FetcherSession` creation until the first `run_*`
method runs (lazy on first access, like `_ensure_seeded`). Drop
`fetch_query` and `start_url` from the constructor. The factory and
`main.py` get slightly cleaner — neither needs to pass placeholder
values for fields the strategy will resolve itself.

**Why it matters**: Each individual mutation is visible and explained
by a comment, but the pattern as a whole is fragile — adding a new
`run_*` method means remembering to update all the bookkeeping fields,
and forgetting one creates a session-summary bug nobody notices for
weeks.

---

## 4. Fashionphile and BooksToScrape `run_*` methods are stubs

**Where**:
- `src/utils/strategies/fashionphile_scrape_strategy.py`
- `src/utils/strategies/books_to_scrape_strategy.py`

**The state**: Both strategies have working header builders, file
namers, paginators, and response analyzers — everything below the
`run_search` / `run_product_lookup` interface. The `run_*` methods
themselves raise `NotImplementedError` with a docstring pointing at
`WalmartScrapeStrategy` as the pattern to follow.

**The fix**: When either retailer becomes a real driving target on
this branch, implement the missing methods. For Fashionphile this
means deciding where canonical search URLs come from (a YAML similar
to `Walmart_fetch_search.yaml`?) and where the product list comes
from. For books.toscrape.com it's even smaller — the site's URL
scheme is well-defined and the test fixtures already exist.

**Why it matters**: The stubs are honest, not regressive — anyone
trying to use these retailers gets a clear error pointing at the
pattern. But they are dead code until exercised. Don't let them rot
for so long that they no longer match the surrounding architecture.

---

## 5. Broken prototype scripts in `stand_alone_scripts/walmart/`

**Where**: `stand_alone_scripts/walmart/` — specifically
`walmart_search_milk_prototype.py`, `walmart_search_milk_prototype_2.py`,
`test_geographic_targeting.py`, and `test_integration.py`.

**The state**: These import the now-removed `RetailerBundle` class
(replaced by the `RetailerScrapeStrategy` hierarchy in commit 2). The
import fails immediately on `python <script>.py`. They were preserved
as historical artifacts during the commit 4 reorg with the explicit
expectation that fixing them is per-script work, not a sweeping change.

**The fix**: Per script, decide either:
- Rewrite to use `WalmartScrapeStrategy` directly (the prototype's
  `LocalBundle` hack was a workaround for `RetailerBundle`'s rigid
  header path; with strategies, the workaround isn't needed)
- Or delete entirely, on the grounds that the working content has
  already been promoted into production code

`stand_alone_scripts/README.md` already flags this. No urgency; do
when next someone tries to run one of these and notices.

---

## 6. Aldi sync calls inside `async def` methods

**Where**: `src/utils/strategies/aldi_scrape_strategy.py`

**The state**: `curl_cffi` is synchronous. `AldiScrapeStrategy._call_graphql`
is a regular def called from `async def run_search` and `async def
_run_detail_flow_for_ids`. While each Aldi run is the only work on
the event loop, the blocking calls don't cause problems. The per-item
delay between detail fetches uses `asyncio.sleep` (good), but the
GraphQL calls themselves block.

**The fix (when needed)**: Wrap the sync GraphQL calls in
`asyncio.to_thread()`. No external interface change. Same approach
the integration-approach doc mentions explicitly.

**Why it matters**: Today, fine — Aldi runs are single-tenant on the
event loop. If parallel execution lands later (e.g. multiple Aldi
strategies running concurrently on the same loop, or Aldi running
alongside Walmart in one process), the blocking calls would starve
other coroutines.

---

## 7. `pyproject.toml` and `pip install -e .`

**Where**: project root (does not exist)

**The state**: The project is pip-installable via `pip install -r
requirements.txt`, but the project itself isn't a package. Running
`python -m src.main` works from the repo root only; tests would have
to do `sys.path` hackery to import from `src/`. The fork shipped a
broken-stub `pyproject.toml`; we deferred it during commit 1.

**The fix**: Write a real `pyproject.toml` declaring the project as
a package with `arachne` as the import name, deps populated from
`requirements.txt`, no Poetry. Then `pip install -e .` makes
`from arachne.utils.retailer_factory import ...` work from any cwd
and lays groundwork for tests.

**Why it matters**: Tests don't exist yet, but they will. Adding
`pyproject.toml` is most useful right before adding tests, not in
isolation.

---

## 8. Delete `arachne-20260427/` once nothing is left to mine from it

**Where**: `/Users/dalesmith/Projects/arachne-20260427/` (sibling of
this repo)

**The state**: The fork directory has been the source of truth for
several pieces brought into this branch — Aldi recon scripts, the
store registry JSONL, the strategy/seeding patterns. With commit 6
landed, every piece we wanted has been ported.

**The fix**: Spot-check there's nothing else worth pulling, then
`rm -rf arachne-20260427/`. The fork content is preserved in
`feature/seeding_proxy`'s git history; the loose directory adds
no value.

**Why it matters**: Tree hygiene. Two parallel arachne directories
on disk is a recipe for editing the wrong one.
