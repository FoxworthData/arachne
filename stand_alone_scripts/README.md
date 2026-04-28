# Stand-Alone Scripts

This directory contains prototype, teaching, and experimentation scripts that
are intentionally kept outside the primary `src/` execution path.

## Purpose

These scripts are useful for:
- Demonstrating alternative or exploratory approaches to a target retailer
- Preserving prototype ideas for future reference
- Running manual experiments without affecting core scraper architecture
- Teaching the codebase to a new developer by showing what came before the
  production strategies in `src/utils/strategies/`

## Important notes

- Scripts here are **not part of the main production-oriented flow**.
- The canonical scraper execution path starts from `src/main.py`.
- Parsing scraped output in production is handled by `src/parse.py`.
- Code in this folder may use different conventions and may not be
  maintained to the same integration standards as `src/` modules.
- Some scripts have stale imports — most notably anything that imported
  the old `RetailerBundle` class, which was replaced by the
  `RetailerScrapeStrategy` hierarchy. Those scripts are preserved as
  historical artifacts; fixing their imports is per-script work that
  nobody has yet needed to do.
- This is **not a Python package** — there are no `__init__.py` files.
  Scripts are run directly, not imported.

## Layout

Subdirectories are organized per retailer (or per topic for `scratch/`):

- `walmart/` — Walmart-specific prototypes, including the cookie-seeding
  prototypes that informed the production `WalmartScrapeStrategy`, plus
  Walmart-specific parsers and integration tests.
- `fashionphile/` — Fashionphile API exploration and search/product
  prototypes, including captured response HTML in `outputs/`.
- `chronos24/`, `farfetch/`, `hermes/`, `rebag/`, `vestiaire/` —
  per-retailer reconnaissance and prototype work. Some retailers
  (notably hermes) only have captured outputs at this stage; others
  have working prototype scripts.
- `scratch/` — uncategorized sketches, retired helpers, and `_SAVE`
  variants kept for reference.

Each retailer directory may contain its own `outputs/` subdirectory with
captured HTML or JSON responses from prototype runs.
