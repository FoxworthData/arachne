# curlconverter folder reorganization

**Status:** Approved design
**Date:** 2026-04-24

## Problem

`src/curlconverter/` has accumulated ~48 files across 7 retailers, mixing Python scripts with HTML dumps, CSV exports, and JSON response captures at a single flat level. Finding anything requires scanning the whole directory, and duplicate `_SAVE` backup files plus repeated dated CSV exports add clutter. `.csv` files are currently tracked in git but are ephemeral outputs that will be regenerated.

## Goal

Reorganize into per-retailer subfolders with each retailer's generated artifacts isolated in a nested `outputs/` folder. Delete confirmed-stale files and prevent CSV outputs from being re-tracked.

## New Structure

```
src/curlconverter/
├── __init__.py
├── chronos24/
│   ├── __init__.py
│   └── <6 chronos24_*.py files>
├── farfetch/
│   ├── __init__.py
│   └── farfetch_product_catalog.py
├── fashionphile/
│   ├── __init__.py
│   ├── <8 fashionphile_*.py files>
│   └── outputs/
│       └── <4 fashionphile_*.html files>
├── hermes/
│   ├── __init__.py
│   └── outputs/
│       └── hermes_women_bags.json
├── rebag/
│   ├── __init__.py
│   ├── rebag_api_test_1.py
│   ├── rebag_chanel_scrape.py
│   └── outputs/
│       └── rebag_api_test_1.txt
├── vestiaire/
│   ├── __init__.py
│   └── vestiaire_search_cli.py
└── walmart/
    ├── __init__.py
    ├── walmart_home_page.py
    ├── walmart_product_milk.py
    ├── walmart_search_milk.py
    ├── test_persona_fix.py
    ├── test_persona_simple.py
    └── outputs/
        └── walmart_search_milk_output.html
```

Rationale for outliers:
- `test_persona_fix.py` and `test_persona_simple.py` land in `walmart/` because `test_persona_fix.py` does `from walmart_home_page import ...` — they are Walmart-specific persona tests.
- `outputs/` subfolders exist only for retailers that have artifact files.

## Deletions

**Duplicate/backup Python files** — delete after `diff` confirms they are backup copies:
- `walmart_home_page_SAVE.py`
- `walmart_search_milk_SAVE.py`

If `diff` surfaces unique content, report it to the user before deleting.

**CSV exports** — delete all `.csv` files in `src/curlconverter/`:
- `fashionphile_export_20250904_211725.csv`
- `fashionphile_export_20250904_213649.csv`
- `fashionphile_export_20251016_142420.csv`
- `fashionphile_shoes_20250902_151843.csv`
- `fashionphile_shoes_20250902_152122.csv`
- `fashionphile_shoes_20250902_152804.csv`
- `fashionphile_shoes_20250902_152820.csv`
- `fashionphile_shoes_20250902_152836.csv`
- `fashionphile_shoes_20250902_152848.csv`
- `fashionphile_shoes_20250904_200602.csv`
- `fashionphile_shoes_20250904_205300.csv`
- `rebag_chanel.csv`

## .gitignore change

Append one line to `/Users/dalesmith/Projects/arachne/.gitignore`:

```
*.csv
```

`*.html` is already ignored — HTML dumps are local-only and moving them does not affect git.

## Import updates

Five files in `src/` import `walmart_home_page` from its current flat location. All must be updated to the new nested path:

| File | Current line 12 | New line 12 |
|---|---|---|
| `src/walmart_home_page_prototype_1.py` | `from src.curlconverter.walmart_home_page import load_search_by_query` | `from src.curlconverter.walmart.walmart_home_page import load_search_by_query` |
| `src/walmart_search_milk_prototype_2.py` | same | same |
| `src/walmart_search_milk_prototype_3.py` | same | same |
| `src/fashionphile_search_newest_shoes_prototype_1.py` | same | same |
| `src/fashionphile_search_newest_shoes_prototype_2.py` | same | same |

`test_persona_fix.py`'s internal `from walmart_home_page import ...` continues to work because it becomes a sibling of `walmart_home_page.py` inside `walmart/`.

## Execution order

1. Diff `_SAVE` files against their live siblings. If identical or clearly stale, `git rm`. If unique content exists, pause and surface to user.
2. `git rm` all `.csv` files listed above.
3. Append `*.csv` to `.gitignore`.
4. Create retailer subfolders and `outputs/` subfolders.
5. `git mv` each file into its new location (preserves history).
6. Create `__init__.py` in each new retailer subfolder.
7. Update the five import statements in `src/*.py`.
8. Verify:
   - `python -c "from src.curlconverter.walmart.walmart_home_page import load_search_by_query"` succeeds.
   - `python -m py_compile` on each of the five edited prototype files succeeds.
   - `git status` shows only moves, deletions, the `.gitignore` edit, the new `__init__.py` files, and the five import edits.

## Non-goals

- No refactoring of script internals.
- No renaming of retained Python files (e.g., `fashionphile_api_test_2.py` stays as-is).
- No changes to `data/`, `docs/`, or any file outside `src/curlconverter/`, `src/*.py` imports, and `.gitignore`.
- No deletion of HTML or JSON artifacts — they move into `outputs/` folders as-is.
