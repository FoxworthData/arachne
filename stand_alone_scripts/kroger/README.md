# Kroger reconnaissance

Captured reference material from early Kroger reconnaissance (April 2026).
**No working scrape code lives here yet** — only the captures that informed
the recon work.

## What's here

All files are under `reference/`:

- **Sitemaps** (`*.xml`) — pulled from `https://www.kroger.com/sitemap.xml`
  and its referenced sub-sitemaps. These are the entry points to Kroger's
  product, store, and department URL space.
- **HTML page sources** (`*.html`) — saved-as captures of representative
  store-detail pages, taken via Chrome DevTools "view-source" and
  "inspect" snapshots. Useful for understanding the page structure
  without re-fetching live pages during early design.

## What's gitignored

HAR files (`*.har`) captured from real browser sessions are gitignored
project-wide. They contain raw HTTP request/response pairs and may
include cookies, tokens, or other session data that shouldn't live in
version control. Re-capture as needed for any future Kroger work.

When this directory was first ported from the fork (April 2026), the
HAR files were left on disk locally:
- `www.kroger.com.har` (~7 MB) — full kroger.com browsing session
- `www.kroger.com.stores.search.har` (~3 MB) — store search flow
- `www.kroger.com.stores.v2.locator.har` (~44 KB) — store locator API

Those local copies may or may not still exist depending on disk hygiene.

## What to do when real Kroger work starts

The captures here are point-in-time snapshots. Before treating any of
them as ground truth, **re-pull the live versions**:

1. `curl https://www.kroger.com/sitemap.xml` — confirm structure hasn't
   changed.
2. Re-capture HARs in Chrome DevTools (Network tab → Save all as HAR
   with content) for the actual flow you're investigating. Keep them
   local.
3. Cross-reference against these snapshots if behavior diverges
   unexpectedly — sometimes "what changed since April 2026" is a
   useful framing.

The pattern from the Aldi recon (`docs/aldi-item-data-recon.md`) is a
reasonable model for how to turn this kind of raw capture material into
a working scraper: identify the bot-detection surface, identify the
real data endpoints, characterize their auth/session requirements,
build a stand-alone proof-of-concept, then port to a
`RetailerScrapeStrategy`.
