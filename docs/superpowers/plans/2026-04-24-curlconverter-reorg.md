# curlconverter Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize `src/curlconverter/` into per-retailer subfolders with nested `outputs/` directories, delete stale `_SAVE` and `.csv` files, and gitignore future CSV artifacts.

**Architecture:** Pure file-layout refactor using `git mv`/`git rm` to preserve history, plus five one-line import edits in sibling `src/*.py` files that depend on `walmart_home_page.py`.

**Tech Stack:** git, Python 3 (for `py_compile` verification).

**Spec:** [docs/superpowers/specs/2026-04-24-curlconverter-reorg-design.md](../specs/2026-04-24-curlconverter-reorg-design.md)

---

## Task 1: Verify `_SAVE` files are safe to delete

**Files:**
- Inspect: `src/curlconverter/walmart_home_page.py` vs `src/curlconverter/walmart_home_page_SAVE.py`
- Inspect: `src/curlconverter/walmart_search_milk.py` vs `src/curlconverter/walmart_search_milk_SAVE.py`

- [ ] **Step 1: Diff walmart_home_page against its SAVE**

Run:
```bash
diff src/curlconverter/walmart_home_page.py src/curlconverter/walmart_home_page_SAVE.py | head -50
wc -l src/curlconverter/walmart_home_page.py src/curlconverter/walmart_home_page_SAVE.py
```

Expected: Either identical (no output from `diff`), or the SAVE is a shorter/earlier version. If the SAVE contains unique content the live file lacks, STOP and report to user.

- [ ] **Step 2: Diff walmart_search_milk against its SAVE**

Run:
```bash
diff src/curlconverter/walmart_search_milk.py src/curlconverter/walmart_search_milk_SAVE.py
```

Expected: Empty output (files identical — sizes matched at 21550 bytes in pre-reorg `ls`). If output appears, STOP and report.

- [ ] **Step 3: No commit for this task**

This is an inspection-only step. Proceed to Task 2.

---

## Task 2: Delete `_SAVE` backup files

**Files:**
- Delete: `src/curlconverter/walmart_home_page_SAVE.py`
- Delete: `src/curlconverter/walmart_search_milk_SAVE.py`

- [ ] **Step 1: Remove both SAVE files**

Run:
```bash
git rm src/curlconverter/walmart_home_page_SAVE.py src/curlconverter/walmart_search_milk_SAVE.py
```

Expected output: `rm 'src/curlconverter/walmart_home_page_SAVE.py'` and `rm 'src/curlconverter/walmart_search_milk_SAVE.py'`.

- [ ] **Step 2: Commit**

```bash
git commit -m "$(cat <<'EOF'
Remove stale _SAVE backup copies in curlconverter

Confirmed identical to live siblings via diff.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Delete tracked CSV exports and gitignore future ones

**Files:**
- Delete: all `*.csv` in `src/curlconverter/`
- Modify: `.gitignore` (append one line)

- [ ] **Step 1: Remove all CSV files from tracking and disk**

Run:
```bash
git rm src/curlconverter/*.csv
```

Expected: 12 files removed (fashionphile_export_*, fashionphile_shoes_*, rebag_chanel.csv). If count differs, stop and investigate — the set may have changed since spec was written.

- [ ] **Step 2: Append `*.csv` to .gitignore**

Edit `.gitignore`, append at end:

```
# CSV exports (regenerated on each run)
*.csv
```

- [ ] **Step 3: Verify gitignore takes effect**

Run:
```bash
git check-ignore -v src/curlconverter/fashionphile_export_20250904_211725.csv 2>&1 || echo "not ignored"
```

Expected: Output shows `.gitignore:<line>:*.csv` matching. (Since the file was just deleted this will exit nonzero with "does not exist" unless we create a dummy — skip if that path is gone; instead verify with a touch-test:)

```bash
touch src/curlconverter/_gitignore_test.csv
git status --short src/curlconverter/_gitignore_test.csv
rm src/curlconverter/_gitignore_test.csv
```

Expected: `git status` shows nothing (file is ignored).

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "$(cat <<'EOF'
Remove tracked CSV exports and gitignore *.csv

CSV outputs are regenerated on each scraping run and should not be
tracked. Removes 12 stale exports and prevents future CSV commits.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Create retailer subfolder scaffolding

**Files:**
- Create: `src/curlconverter/chronos24/__init__.py`
- Create: `src/curlconverter/farfetch/__init__.py`
- Create: `src/curlconverter/fashionphile/__init__.py`
- Create: `src/curlconverter/fashionphile/outputs/` (directory only, no __init__)
- Create: `src/curlconverter/hermes/__init__.py`
- Create: `src/curlconverter/hermes/outputs/`
- Create: `src/curlconverter/rebag/__init__.py`
- Create: `src/curlconverter/rebag/outputs/`
- Create: `src/curlconverter/vestiaire/__init__.py`
- Create: `src/curlconverter/walmart/__init__.py`
- Create: `src/curlconverter/walmart/outputs/`

- [ ] **Step 1: Make directories and empty __init__.py files**

Run:
```bash
cd /Users/dalesmith/Projects/arachne
for retailer in chronos24 farfetch fashionphile hermes rebag vestiaire walmart; do
  mkdir -p "src/curlconverter/$retailer"
  touch "src/curlconverter/$retailer/__init__.py"
done
for retailer in fashionphile hermes rebag walmart; do
  mkdir -p "src/curlconverter/$retailer/outputs"
done
```

Expected: 7 directories created, 7 `__init__.py` files created, 4 outputs subdirs created. `outputs/` subdirs do not get `__init__.py` (they hold artifacts, not Python modules).

- [ ] **Step 2: Verify layout**

Run:
```bash
find src/curlconverter -type d | sort
```

Expected output:
```
src/curlconverter
src/curlconverter/__pycache__
src/curlconverter/chronos24
src/curlconverter/farfetch
src/curlconverter/fashionphile
src/curlconverter/fashionphile/outputs
src/curlconverter/hermes
src/curlconverter/hermes/outputs
src/curlconverter/rebag
src/curlconverter/rebag/outputs
src/curlconverter/vestiaire
src/curlconverter/walmart
src/curlconverter/walmart/outputs
```

- [ ] **Step 3: No commit yet — folder scaffolding gets committed with the moves in Task 5**

Empty directories aren't tracked by git anyway; the `__init__.py` files become tracked when the `git mv` operations below add content to these folders.

---

## Task 5: Move chronos24 files

**Files:**
- Move: `src/curlconverter/chronos24*.py` → `src/curlconverter/chronos24/`

- [ ] **Step 1: git mv all chronos24 scripts**

Run:
```bash
git mv src/curlconverter/chronos24.py              src/curlconverter/chronos24/chronos24.py
git mv src/curlconverter/chronos24_api_collect.py  src/curlconverter/chronos24/chronos24_api_collect.py
git mv src/curlconverter/chronos24_api_merchant.py src/curlconverter/chronos24/chronos24_api_merchant.py
git mv src/curlconverter/chronos24_client_infos.py src/curlconverter/chronos24/chronos24_client_infos.py
git mv src/curlconverter/chronos24_js_1.py         src/curlconverter/chronos24/chronos24_js_1.py
git mv src/curlconverter/chronos24_rolext_daytona.py src/curlconverter/chronos24/chronos24_rolext_daytona.py
```

Expected: 6 files moved, no output on success.

- [ ] **Step 2: Stage the new __init__.py and commit**

```bash
git add src/curlconverter/chronos24/__init__.py
git commit -m "$(cat <<'EOF'
Move chronos24 scripts into chronos24/ subfolder

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Move farfetch files

**Files:**
- Move: `src/curlconverter/farfetch_product_catalog.py` → `src/curlconverter/farfetch/`

- [ ] **Step 1: git mv**

```bash
git mv src/curlconverter/farfetch_product_catalog.py src/curlconverter/farfetch/farfetch_product_catalog.py
```

- [ ] **Step 2: Stage __init__.py and commit**

```bash
git add src/curlconverter/farfetch/__init__.py
git commit -m "$(cat <<'EOF'
Move farfetch scripts into farfetch/ subfolder

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Move fashionphile files and outputs

**Files:**
- Move: 10 `src/curlconverter/fashionphile_*.py` → `src/curlconverter/fashionphile/`
- Move: 4 `src/curlconverter/fashionphile_*.html` → `src/curlconverter/fashionphile/outputs/`

- [ ] **Step 1: Move Python files**

```bash
git mv src/curlconverter/fashionphile_api_test.py     src/curlconverter/fashionphile/fashionphile_api_test.py
git mv src/curlconverter/fashionphile_api_test_2.py   src/curlconverter/fashionphile/fashionphile_api_test_2.py
git mv src/curlconverter/fashionphile_api_test_3.py   src/curlconverter/fashionphile/fashionphile_api_test_3.py
git mv src/curlconverter/fashionphile_api_test_4.py   src/curlconverter/fashionphile/fashionphile_api_test_4.py
git mv src/curlconverter/fashionphile_api_test_5.py   src/curlconverter/fashionphile/fashionphile_api_test_5.py
git mv src/curlconverter/fashionphile_product_chanel_lambskin_booties.py src/curlconverter/fashionphile/fashionphile_product_chanel_lambskin_booties.py
git mv src/curlconverter/fashionphile_search_newest_louboutin_shoes.py   src/curlconverter/fashionphile/fashionphile_search_newest_louboutin_shoes.py
git mv src/curlconverter/fashionphile_search_newest_shoes.py             src/curlconverter/fashionphile/fashionphile_search_newest_shoes.py
git mv src/curlconverter/fashionphile_search_newest_shoes_page_2.py      src/curlconverter/fashionphile/fashionphile_search_newest_shoes_page_2.py
git mv src/curlconverter/fashionphile_shopify_product_parser.py          src/curlconverter/fashionphile/fashionphile_shopify_product_parser.py
```

Expected: 10 files moved (5 `api_test` + 1 `product_chanel_lambskin_booties` + 3 `search_*` + 1 `shopify_product_parser`). Verify `ls src/curlconverter/fashionphile_*.py` is empty after.

- [ ] **Step 2: Move HTML outputs (not tracked by git — use plain mv)**

HTML files are in `.gitignore` (`*.html`), so they aren't tracked. Use regular `mv`:

```bash
mv src/curlconverter/fashionphile_newest_louboutin_shoes.html     src/curlconverter/fashionphile/outputs/fashionphile_newest_louboutin_shoes.html
mv src/curlconverter/fashionphile_product_response_output.html    src/curlconverter/fashionphile/outputs/fashionphile_product_response_output.html
mv src/curlconverter/fashionphile_response_output.html            src/curlconverter/fashionphile/outputs/fashionphile_response_output.html
mv src/curlconverter/fashionphile_response_output_page_2.html     src/curlconverter/fashionphile/outputs/fashionphile_response_output_page_2.html
```

Expected: 4 HTML files moved. `git status` should still be clean for these (still ignored).

- [ ] **Step 3: Verify no fashionphile files remain at the top level**

```bash
ls src/curlconverter/fashionphile_* 2>&1
```

Expected: `No such file or directory` (or empty listing).

- [ ] **Step 4: Commit**

```bash
git add src/curlconverter/fashionphile/__init__.py
git commit -m "$(cat <<'EOF'
Move fashionphile scripts into fashionphile/ subfolder

HTML response dumps moved to fashionphile/outputs/ (still gitignored).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Move hermes output

**Files:**
- Move: `src/curlconverter/hermes_women_bags.json` → `src/curlconverter/hermes/outputs/`

- [ ] **Step 1: git mv (json is not in gitignore, so use git mv to preserve tracking)**

```bash
git mv src/curlconverter/hermes_women_bags.json src/curlconverter/hermes/outputs/hermes_women_bags.json
```

- [ ] **Step 2: Commit**

```bash
git add src/curlconverter/hermes/__init__.py
git commit -m "$(cat <<'EOF'
Move hermes sample JSON into hermes/outputs/

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Move rebag files

**Files:**
- Move: `src/curlconverter/rebag_api_test_1.py` → `src/curlconverter/rebag/`
- Move: `src/curlconverter/rebag_chanel_scrape.py` → `src/curlconverter/rebag/`
- Move: `src/curlconverter/rebag_api_test_1.txt` → `src/curlconverter/rebag/outputs/`

(Note: `rebag_chanel.csv` was already deleted in Task 3.)

- [ ] **Step 1: git mv**

```bash
git mv src/curlconverter/rebag_api_test_1.py    src/curlconverter/rebag/rebag_api_test_1.py
git mv src/curlconverter/rebag_chanel_scrape.py src/curlconverter/rebag/rebag_chanel_scrape.py
git mv src/curlconverter/rebag_api_test_1.txt   src/curlconverter/rebag/outputs/rebag_api_test_1.txt
```

- [ ] **Step 2: Commit**

```bash
git add src/curlconverter/rebag/__init__.py
git commit -m "$(cat <<'EOF'
Move rebag scripts into rebag/ subfolder

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Move vestiaire file

**Files:**
- Move: `src/curlconverter/vestiaire_search_cli.py` → `src/curlconverter/vestiaire/`

- [ ] **Step 1: git mv**

```bash
git mv src/curlconverter/vestiaire_search_cli.py src/curlconverter/vestiaire/vestiaire_search_cli.py
```

- [ ] **Step 2: Commit**

```bash
git add src/curlconverter/vestiaire/__init__.py
git commit -m "$(cat <<'EOF'
Move vestiaire script into vestiaire/ subfolder

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Move walmart files (including test_persona_*)

**Files:**
- Move: `walmart_home_page.py`, `walmart_product_milk.py`, `walmart_search_milk.py`, `test_persona_fix.py`, `test_persona_simple.py` → `src/curlconverter/walmart/`
- Move: `walmart_search_milk_output.html` → `src/curlconverter/walmart/outputs/`

- [ ] **Step 1: Move Python files**

```bash
git mv src/curlconverter/walmart_home_page.py    src/curlconverter/walmart/walmart_home_page.py
git mv src/curlconverter/walmart_product_milk.py src/curlconverter/walmart/walmart_product_milk.py
git mv src/curlconverter/walmart_search_milk.py  src/curlconverter/walmart/walmart_search_milk.py
git mv src/curlconverter/test_persona_fix.py     src/curlconverter/walmart/test_persona_fix.py
git mv src/curlconverter/test_persona_simple.py  src/curlconverter/walmart/test_persona_simple.py
```

- [ ] **Step 2: Move HTML output (gitignored, use plain mv)**

```bash
mv src/curlconverter/walmart_search_milk_output.html src/curlconverter/walmart/outputs/walmart_search_milk_output.html
```

- [ ] **Step 3: Verify test_persona_fix.py's internal import still resolves**

`test_persona_fix.py` does `from walmart_home_page import BrowserPersonaChooser, BrowserPersona`. Since both files are now siblings inside `walmart/`, the import remains valid. Confirm with:

```bash
cd src/curlconverter/walmart && python -c "import walmart_home_page; print('ok')"
```

Expected: `ok` (or, if imports in `walmart_home_page.py` itself reference other repo-level modules, you may need to run this as a module from repo root instead — don't worry about it; actual verification happens in Task 13).

Return to repo root: `cd /Users/dalesmith/Projects/arachne`

- [ ] **Step 4: Commit**

```bash
git add src/curlconverter/walmart/__init__.py
git commit -m "$(cat <<'EOF'
Move walmart scripts into walmart/ subfolder

test_persona_*.py files move with walmart_home_page since they test its
BrowserPersona classes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Update the five import statements

**Files:**
- Modify: `src/walmart_home_page_prototype_1.py:12`
- Modify: `src/walmart_search_milk_prototype_2.py:12`
- Modify: `src/walmart_search_milk_prototype_3.py:12`
- Modify: `src/fashionphile_search_newest_shoes_prototype_1.py:12`
- Modify: `src/fashionphile_search_newest_shoes_prototype_2.py:12`

Each file has this exact line 12:
```python
from src.curlconverter.walmart_home_page import load_search_by_query
```

All five must change to:
```python
from src.curlconverter.walmart.walmart_home_page import load_search_by_query
```

- [ ] **Step 1: Apply edit to all five files**

Use the Edit tool on each file with:
- old_string: `from src.curlconverter.walmart_home_page import load_search_by_query`
- new_string: `from src.curlconverter.walmart.walmart_home_page import load_search_by_query`

Apply to all five paths listed above.

- [ ] **Step 2: Verify no stale references remain**

```bash
grep -rn "from src.curlconverter.walmart_home_page" --include="*.py" .
grep -rn "from src.curlconverter import walmart_home_page" --include="*.py" .
```

Expected: Both return nothing.

- [ ] **Step 3: Confirm the new path resolves**

```bash
grep -rn "from src.curlconverter.walmart.walmart_home_page" --include="*.py" .
```

Expected: Exactly 5 matches (one per updated file).

- [ ] **Step 4: Commit**

```bash
git add src/walmart_home_page_prototype_1.py src/walmart_search_milk_prototype_2.py src/walmart_search_milk_prototype_3.py src/fashionphile_search_newest_shoes_prototype_1.py src/fashionphile_search_newest_shoes_prototype_2.py
git commit -m "$(cat <<'EOF'
Update imports for walmart_home_page's new location

Follows the curlconverter reorg that placed walmart_home_page.py under
src/curlconverter/walmart/.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: End-to-end verification

- [ ] **Step 1: Syntax-check the five edited prototype files**

```bash
python -m py_compile src/walmart_home_page_prototype_1.py \
                     src/walmart_search_milk_prototype_2.py \
                     src/walmart_search_milk_prototype_3.py \
                     src/fashionphile_search_newest_shoes_prototype_1.py \
                     src/fashionphile_search_newest_shoes_prototype_2.py
```

Expected: No output (success). Any output is an error to fix before proceeding.

- [ ] **Step 2: Resolve the new walmart_home_page import**

```bash
python -c "from src.curlconverter.walmart.walmart_home_page import load_search_by_query; print('import ok')"
```

Expected: `import ok`. If `ModuleNotFoundError` on `src.curlconverter.walmart`, check that `src/curlconverter/walmart/__init__.py` exists. If `ImportError` on `load_search_by_query`, the function is missing from the file — out of scope for this reorg but flag to user.

- [ ] **Step 3: Confirm top-level folder is clean**

```bash
ls src/curlconverter/
```

Expected: Only `__init__.py`, `__pycache__/`, and the 7 retailer subfolders. No stray `.py`, `.csv`, `.html`, `.json`, or `.txt` files.

- [ ] **Step 4: Confirm git log shows clean reorg history**

```bash
git log --oneline -15
```

Expected: Recent commits include the 9 reorg commits (SAVE deletion, CSV deletion, chronos24/farfetch/fashionphile/hermes/rebag/vestiaire/walmart moves, import fixes) plus the earlier spec commit.

- [ ] **Step 5: No additional commit — verification only**

If everything above passed, the reorg is complete.
