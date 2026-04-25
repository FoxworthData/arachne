# Porting the Walmart cookie-seeding fix into a greenfield work codebase

## Scope and context

This document is a sprint-level execution plan for porting the cookie-seeding
approach proven out in `src/walmart_search_milk_prototype_3.py` into a
greenfield Walmart scraper that currently has the shape of arachne's
`src/main.py` path.

Assumptions baked in:

- The work codebase is a near-verbatim copy of arachne's `main.py` path —
  same `retailer_factory.py`, same `header_builders.py`, same
  `AiohttpFetcher`, same `RetailerBundle`. If names have drifted, steps
  translate, line numbers will not.
- Legal sign-off and leadership go-ahead are already in place.
- Bright Data residential proxy budget is available and provisioned.
- This is Interpretation A from the planning conversation: a mechanical
  port to unblock the team, not an architectural refactor. The latter is a
  separate, later effort.

For the diagnostic background — why `main.py` fails page 2+ and why
prototype_3 works — see
`walmart-main-py-cookie-seeding-migration.md` in this same directory. This
document is the execution plan; that one is the root-cause analysis.

---

## Execution order

### Step 0 — Inventory what exists at work vs. what needs to come over

Before writing any new code, walk through this checklist literally. Nothing
else compiles without these pieces in place.

- [ ] `src/utils/walmart_cookie_seeder.py` — probably missing, copy from arachne
- [ ] `src/utils/browser_personas.py` — probably missing, copy from arachne.
      If it's not where expected in arachne either, the fallback source is
      `walmart_home_page.py:45-150` (verify before assuming)
- [ ] `src/utils/proxy_builder_simple.py` — maybe missing. If so, use the
      existing `retailer_factory.get_proxies()` as a substitute; it reads the
      same `BRIGHTDATA_RESIDENTIAL_PROXY_*` env vars
- [ ] `tenacity` in `requirements.txt` — the seeder imports `Retrying`,
      `stop_after_attempt`, `retry_if_exception_type`, `before_sleep_log`,
      `RetryError`

Do this step first. Everything downstream depends on it.

---

### Step 1 — Promote `WalmartCookieSeedingHeaderBuilder` to a first-class builder

**File:** `src/utils/header_builders.py`

In prototype_3 this class is inline in the script. Move it into
`header_builders.py` as a sibling of `WalmartHeaderBuilder`, which it
subclasses. Copy the class body verbatim from prototype_3 lines 47–85.

It exposes two attributes the seeder caller needs:

- `initial_headers` — modern Chrome header set including Client Hints and
  Fetch Metadata, pinned to a `BrowserPersona`
- `initial_cookies` — the location cookie dict, parsed out of
  `self.location_cookie()`

**One known smell to leave in place for this sprint:** `assortmentStoreId`
in `initial_cookies` is read from `self.store_id`, while the other location
cookies are parsed from `self.location_cookie()` output. Two sources of
truth for store identity. Add a `# TODO: unify store_id source with
location_cookie output` comment so it doesn't get forgotten, but don't fix
it in this sprint — getting the port green is the goal.

---

### Step 2 — Add `LocalBundle` to the search entry point

**File:** `src/main.py` (or wherever the work codebase's search entry point lives)

Copy from prototype_3 lines 36–45, but fix the class-attribute bug before
shipping.

Prototype_3 has:

```python
class LocalBundle(RetailerBundle):
    headers = {}
    def set_headers(self, headers: dict):
        self.headers = headers
    ...
```

That `headers = {}` is a class attribute. The moment two `LocalBundle`s
exist in the same process (i.e., the first time two stores are scraped
in parallel), they share state. Ship the instance-attribute version:

```python
class LocalBundle(RetailerBundle):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {}

    def set_headers(self, headers: dict):
        self.headers = headers

    def build_headers(self):
        return self.headers

    def get_headers(self):
        return self.build_headers()
```

Costs nothing. Removes a latent concurrency bug.

---

### Step 3 — Replace the `search` branch with the seeded flow

**File:** `src/main.py`

This is the core change. Replace the existing `build_retailer_bundle(...)`
call in the `search` branch with the seven-step sequence from prototype_3's
`main()`:

1. Pick a `BrowserPersona`. Start pinned:
   `BrowserPersonaChooser().get_persona(os_name='Windows', browser_name='Chrome')`.
   Matching prototype_3's known-working config is higher priority than
   rotation policy on sprint one.
2. Get proxies: `get_proxies(proxy_type='residential')`.
3. Instantiate the header builder:
   `WalmartCookieSeedingHeaderBuilder(store_identification=..., browser_persona=persona)`.
4. Instantiate the seeder with the builder's `initial_headers` and
   `initial_cookies`.
5. `await seeder.get_seeded_cookies(browser_persona=persona)`.
6. `blend_cookies(...)` the location cookies with the harvested cookies, and
   assign to `seeded_headers['cookie']` (lowercase key, to match the rest
   of the modern Chrome header set).
7. Instantiate `LocalBundle` directly — bypass `build_retailer_bundle`
   entirely — then `bundle.set_headers(seeded_headers)`, then
   `bundle.fetcher.fetch_all(...)` as before.

The pseudocode in the "Putting it together" section of
`walmart-main-py-cookie-seeding-migration.md` is the accurate target shape.
Use it verbatim as scaffolding and adapt variable names to match the work
codebase.

---

### Step 4 — Add the `blend_cookies` helper

**File:** new, `src/utils/cookie_utils.py`

Copy the helper verbatim from prototype_3. Don't leave it as a module-level
function in `main.py`. It's small and Walmart-specific, which is fine; the
goal is just that it's importable from a utils module rather than buried in
the entry point.

```python
def blend_cookies(location_cookies: dict, harvested_cookies: dict) -> str:
    cookie_string = (
        f"hasLocData={location_cookies['hasLocData']}; "
        f"ACID={location_cookies['ACID']}; "
        f"locGuestData={location_cookies['locGuestData']}; "
        f"assortmentStoreId={location_cookies['assortmentStoreId']}; "
        f"hasACID=true; "
        f"locDataV3={location_cookies['locDataV3']}; "
    )
    harvested_cookie_string = "; ".join(
        f"{key}={value}" for key, value in harvested_cookies.items()
    )
    cookie_string += f"{harvested_cookie_string};"
    return cookie_string
```

---

### Step 5 — Fix the silent-failure hole

**File:** `src/main.py`

Prototype_3 has `if harvested_result['success']:` with no `else` branch. On
a one-off local script, silent exit on seeding failure is annoying but
obvious — no data shows up. On a scheduled work job, it becomes "why is the
Walmart dashboard stale" three weeks later.

Add the explicit failure branch:

```python
if not harvested_result['success']:
    logger.error(f"Cookie seeding failed: {harvested_result}")
    raise RuntimeError("Cookie seeding failed; aborting scrape")
```

Log loudly, raise, let whatever orchestrates the job notice.

---

### Step 6 — Leave the other branches alone

The work codebase inherits `product`, `store-directory`, and
`store-directory-by-state` branches from `main.py`. These currently route
through `build_retailer_bundle` and the non-seeded path.

**Don't touch them in this sprint.** They either already work (first-touch
pages) or they'll start failing later, at which point the same pattern
applies to them.

Scope discipline matters. The team will be tempted to "fix everything while
we're in here." One-week ports become three-week ports that way.

---

### Step 7 — Prune dead imports

Prototype_3 imports `playwright` and `playwright_stealth` at the top of the
file but never uses them. Don't bring them across. Don't let them leak into
the work `requirements.txt`. Three months from now, nobody wants to debug a
Playwright installation for code that never calls Playwright.

---

## Verification before declaring done

"Page 2 returned 200" is not enough. Walmart sometimes returns 200 with a
soft-block page. Run all three checks:

1. Seeder logs `Found store ID '<your store>'` and it matches the requested
   store. If it doesn't, the seeder retries up to 10 times; exhausted
   retries means the proxy exit node is not geo-consistent with the store
   — switch proxy region before blaming the code.
2. **Log `seeded_headers['cookie']` once before `fetch_all`** and
   eyeball-confirm the string contains both:
   - Harvested anti-bot cookies: `_px3`, `ak_bmsc`, `bm_sv`
   - Location cookies: `ACID`, `locDataV3`, `assortmentStoreId`
   This is the single fastest end-to-end sanity check. Teams skip it. Don't.
3. `walmart_response_analyzer` (from `src/utils/response_analyzers.py`)
   passes its "not blocked / UA accepted / store ID matches" checks on
   every page, not just page 1.

---

## Out of scope, explicitly

So the team doesn't scope-creep:

- **Re-seeding policy.** What happens when harvested cookies expire
  mid-scrape. Prototype_3 doesn't handle this. Neither should the port.
- **Multi-store proxy-region matching.** Prototype_3 uses one store and
  one residential proxy pool. Match that.
- **Persona rotation.** Pinned Windows/Chrome, same as prototype_3.
  "Commented-out randomization" is not a rotation policy — decide
  deliberately later.
- **Retry/backoff on the scrape itself.** The seeder has `tenacity`
  retries. The `fetch_all` loop does whatever it already does. Don't change
  that in this sprint.
- **Fixes to `product` / `store-directory` / `store-directory-by-state`
  branches.**

All of these are real problems. None of them are this sprint's problem.
Capture them as follow-up tickets; ship the port.

---

## Follow-up candidates (not this sprint)

Surface these in the team's backlog grooming after the port is green:

- Unify the `store_id` source between `assortmentStoreId` and
  `location_cookie()` output in `WalmartCookieSeedingHeaderBuilder`.
- Replace the hardcoded f-string in `blend_cookies` with validation at
  construction time — fail loudly at setup if a required location cookie is
  missing, not at scrape time with a `KeyError`.
- Decide a persona rotation policy (deliberate pinning with rotation
  cadence, or deliberate randomization across runs). Document the decision.
- Extract a retailer-agnostic `CookieSeedingHeaderBuilder` abstraction once
  there's a second retailer target — not before. Premature abstraction on
  one instance is worse than duplication on two.
- Re-seeding mid-run when harvested cookies go stale, with a metric for
  seed-cache hit rate.
