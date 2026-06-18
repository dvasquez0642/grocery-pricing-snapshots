# BUGS.md — Open Issues Inventory

This document captures bugs, deferred work, and process gaps identified during
the v2 wayback scrape cycle (script_version 2.0 → 2.1). It is intended as a
working hand-off for whoever picks up the project next.

The bug-numbering follows the order they surfaced in the live debugging
session; Bugs 1B, 2, and 3 were diagnosed *and fixed* during the session
(Fix 1B = partial-manifest preservation, Fix 2 = HTTP 400 = end-of-pages,
Fix 3 = target-rotation CDX scheduler). Bug 4 onward are still open.

## Quick triage table

| ID  | Area                               | Severity      | Fix difficulty | Status                        |
| --- | ---------------------------------- | ------------- | -------------- | ----------------------------- |
| 4   | scrape — runs.csv aggregation      | Low           | Trivial        | Deferred                      |
| 5   | scrape — between-page sleep        | Low           | Trivial        | Mostly moot                   |
| 6   | scrape — task accumulation         | Medium        | Moderate       | Deferred                      |
| 7   | scrape — NO_CDX_COVERAGE chains    | Unknown       | Unknown        | Needs investigation           |
| 8   | scrape — ShopRite 0 priced rows    | Unknown       | Unknown        | Needs investigation           |
| 9   | scrape — Plum Market wallclock     | Low           | Hard           | Deferred                      |
| 10  | scrape — single-process arch       | Architectural | Hard           | Deferred until next big sweep |
| 11  | rebuild — v2 invisible to parquet  | High          | Trivial        | Pending integration           |
| 12  | rebuild — v2 columns silently lost | Medium        | Trivial        | Pending schema decision       |
| 13  | QA — no deduplication anywhere     | Medium        | Moderate       | Pending QA decision           |
| 14  | QA — screening dormant + bad path  | Medium        | Hard           | Pending QA decision           |
| 15  | deploy — no regression check       | Low           | Easy           | Pending QA decision           |
| G1  | docs — v1 manifests survived       | Cosmetic      | N/A            | Note in retrospective         |
| G2  | docs — status CSV staleness        | Cosmetic      | Easy           | Note + optional fix           |
| G3  | docs — v2 retrospective unwritten  | Process       | Easy           | Outstanding                   |
| G4  | git — Fix 1B/2/3 uncommitted       | Process       | Trivial        | Awaits user request           |

---

## In `scrape_wayback_universe.py` (the wayback scrape)

### Bug 4 — `runs.csv` error-counting has an operator-precedence quirk

**Severity: Low.** The accounting still produces correct totals, but only by
coincidence.

**Location:** `scrape_wayback_universe.py`, around lines 1861-1865 (in the
`runs.csv` summary-aggregation block at end of `run()`).

**Symptom:** The `or` between two `sum(...)`-comprehensions binds at the
wrong logical level. Python parses it as `(A and B) or (C and D)` where the
author seems to have intended `A and (B or C) and D`. The current expression
gets the right answer because `B` and `C` are in fact equivalent in practice,
but a future refactor that changes either side would silently break the
count.

**Why deferred:** Doesn't block any output. The new `COMPLETED_PARTIAL_*`
statuses introduced by Fix 1B fall through `n_completed`'s
`startswith("COMPLETED")` check correctly, so partial completions are still
counted as completed (not errored).

**How to fix:** Add explicit parentheses around the OR clauses, or
restructure as a single comprehension with a unioned predicate.

---

### Bug 5 — 0.5s between-page sleep is too short (mostly moot)

**Severity: Low.** Effectively dead code path under the new architecture.

**Location:** Inside `cdx_query()`, line ~624 — `await asyncio.sleep(0.5)`
between successive CDX page requests.

**Symptom:** Wayback CDX rate limits are per-target (URL+params, not source
IP) and operate on minute-to-hour timescales. A half-second pause between
pages is meaningless against that.

**Status:** Largely irrelevant under the v2.1 target-rotation scheduler
(`cdx_phase()`), which doesn't paginate the same target back-to-back.
Additionally, Fix 2 confirmed Wayback returns the entire dataset on page 0
for almost all chains, so most chains never hit page 1 at all.

**Why deferred:** Functionally moot.

---

### Bug 6 — `in_flight` task accumulation in `cdx_phase` scheduler

**Severity: Medium.** Real memory cost; would compound on bigger sweeps.

**Location:** `cdx_phase()`, the worker dispatch loop. Tasks are created
via `asyncio.create_task(_wrapped(target))` immediately and added to an
`in_flight` set. The semaphore (`asyncio.Semaphore(args.cdx_concurrency)`)
gates only the actual CDX request *inside* `_wrapped`, not the task creation.

**Symptom:** During the weekend run we observed `in_flight=5,328` shortly
after launch (with `--cdx-concurrency 32`), meaning ~5,000 tasks were
sitting waiting on the semaphore, each holding a `CdxTarget` object and a
coroutine frame. Process RSS reached **5.8 GB** during a 7,691-chain sweep.

**Cost in practice:** Acceptable for 7K-chain sweeps on a 60 GB box, but
would explode on larger ones (hundred-thousand-chain runs would OOM).

**How to fix:** Gate task *creation* (not just task execution). Pop a target
from the queue only when there's semaphore capacity available — e.g. wrap
the entire dispatch in `await sem.acquire()`, then create the task and have
the task release at the end. Or refactor to a fixed pool of N worker
coroutines that all pull from the queue.

---

### Bug 7 — ~1,025 chains marked `NO_CDX_COVERAGE` undiagnosed

**Severity: Unknown — could be benign, could indicate a real classifier
problem.** Affects ~13% of the universe.

**Symptom:** 1,025 of 7,691 chains in the v2 weekend run ended up with
status `NO_CDX_COVERAGE` — meaning their on-disk manifest existed but
decoded to zero usable URLs after the URL classifier's dedup-filter pass.

**Two possible explanations, both plausible:**
1. The chains genuinely have no archived priced content — Wayback only
   captured cookie-walls, redirect pages, static asset stubs, etc.
2. The URL classifier (`helpers/url_classifier.py`) is over-aggressive on
   certain domain shapes and rejects everything.

**Why deferred:** Read-only investigation only. We need to sample 5-10 of
these chains, gunzip the manifest, count rows by `kept` status, and look
at what URLs were dropped vs retained.

**Suggested investigation:** A short R or Python script that, for the 1,025
NO_CDX_COVERAGE chains: (a) loads the manifest, (b) counts total URLs and
kept URLs, (c) for the rejected URLs samples 20 and lists their drop
reasons. This will tell us whether the classifier is the problem or
whether the chains are genuinely empty.

---

### Bug 8 — ShopRite has 251K `_no_prices` rows but 0 priced rows

**Severity: Unknown — high-traffic chain producing no priced data is
suspicious.**

**Symptom:** ShopRite was processed by the validation run, fetched 251,152
snapshots, and produced **zero** priced rows. Compare to Mariano's, which
processed similar volume from the same Wayback CDX endpoint and produced
~131K priced rows (~33% hit rate).

**Two possible explanations:**
1. ShopRite genuinely doesn't publish prices in formats our extraction
   cascade recognizes (no JSON-LD `Product` offers, no `__NEXT_DATA__`
   price keys, no OCR-able image flyers, etc.).
2. ShopRite's HTML or JSON structure has a quirk that defeats one or more
   stages of the extraction cascade.

**Why deferred:** Need to spot-check ShopRite snapshots manually. Pick 5
random `wayback_url` values from `shoprite_no_prices.csv`, fetch them,
look at the page structure, and decide whether the cascade is missing
something or whether ShopRite simply doesn't put pricing on the homepage.

**Note:** Several other big-name chains may have the same situation.
A QA pass across all `_no_prices` files (with `priced/no_priced` ratio per
chain) would surface them.

---

### Bug 9 — Plum Market burned ~6+ hours on cached/blacklisted bookkeeping

**Severity: Low.** Wallclock symptom, not a data-correctness issue.

**Location:** `process_chain()` — specifically the per-snapshot loop that
checks `processed_urls` and the basename-blacklist before deciding whether
to fetch.

**Symptom:** During the weekend run, Plum Market's chain processing was
observed at 220K of 271K pages, with `priced=9465 ocr=14778` frozen for
hours. Throughput was ~80 page-iterations/sec but each iteration was just
"snapshot is in dedup or blacklist set → skip." No actual fetch or OCR
work was happening; the loop counter was advancing through bookkeeping.

**Why this is bad:** Total wallclock cost was ~6 hours per chain like this,
multiplied by however many similar chains are in the queue. Single-chain
processing serializes the whole run.

**Why deferred:** Would require a "fast-path" for chains where >X% of the
manifest is in the dedup/blacklist set — e.g. test the manifest against
the dedup set in bulk before entering the per-snapshot loop. Architectural
change with non-trivial risk.

---

### Bug 10 — Single-process asyncio underutilizes the EC2 box

**Severity: Architectural.** Costs us a factor of ~30x on hardware
utilization.

**Symptom:** The c8i.8xlarge EC2 instance (32 cores, 61 GB RAM) ran the
weekend scrape at load average ~0.05, with one core at ~9% CPU and the
other 31 cores at 100% idle. The pipeline is one Python process running
one asyncio event loop. There is **no cross-chain parallelism** in the
fetch+OCR phase — chains are processed strictly sequentially.

**Within-chain concurrency exists** (`--snapshot-concurrency 400`,
`--ocr-concurrency 64`), but it can't help when the chain is mostly cached
or the bottleneck is per-snapshot async I/O.

**Why deferred:** Major refactor. Two reasonable shapes:
1. Multi-process worker pool sharing a chain-level queue, each process
   running its own asyncio loop on a chunk of chains.
2. Right-size the instance — a c7i.large or similar would be cheaper and
   the underutilization wouldn't matter.

Best tackled before the *next* big sweep, not retrofit onto the current
codebase.

---

## In `data_loader.py` and `scripts/rebuild_parquet.py`

### Bug 11 — `rebuild_parquet.py` doesn't include v2 (mk_2) data

**Severity: HIGH.** The 1.37M priced rows from the v2 weekend run are
**invisible to the deployed app** as currently configured. This is the
single most important blocker between v2 work and the streamlit dashboard.

**Location:** `scripts/rebuild_parquet.py`, lines 56-82.

**Symptom:** The `collect_csv_files()` function walks two source dirs:

```python
MAIN_DATA_DIR = ROOT / "wayback grocery AO" / "data"
TASK_GROUP_ROOT = ROOT / "wayback grocery AO"  # for task_group_*/data/
```

Neither glob reaches `AQ_wayback_grocery_mk_2/data/mk_2/`. So if you run
`scripts/rebuild_parquet.py` right now, the resulting parquet contains
zero v2 rows.

**How to fix:** Add a third source directory. Decide on dedup priority
order between v1-main, v1-task-group, and v2 (recommendation: v2 highest,
since it has provenance columns and was produced under the fixed pipeline).

**Approach options (ranked):**
1. **Direct edit (recommended):** Add `AQ_wayback_grocery_mk_2/data/mk_2/`
   as a third dir in `collect_csv_files()`.
2. Symlink `wayback grocery AO/task_group_v2_mk_2/data/` to the v2 dir.
   Zero code changes but Windows symlinks are a pain.
3. Stage v2 files into v1's data dir. Conflates provenance.
   **Not recommended.**

---

### Bug 12 — v2 provenance columns silently dropped on load

**Severity: Medium.** Loses metadata that the app could use for filtering
("show only v2 rows" / "show only OCR-derived rows").

**Location:** `data_loader.py:_load_single_csv`, lines 255-258.

**Symptom:** `out_cols` is hardcoded to a fixed 11-column subset:

```python
out_cols = [
    "timestamp", "year", "chain", "location", "product_name",
    "price", "unit", "sale", "description", "wayback_url", "source_file",
]
```

V2 CSVs ship additional columns: `brand`, `source_path`, `source_image`,
`pipeline`, `script_version`, `ocr_model`, `ocr_prompt_version`,
`ocr_run_id`, `ocr_attempt_ts`. These are present in the source CSV and
read by `pd.read_csv` but dropped at the `df[out_cols]` step.

**Decision needed before fix:**
- **Wide schema** (recommended): include all v2 columns in the parquet,
  fall back to empty/NaN for v1 rows. ~5-10% larger parquet.
- **Narrow schema:** drop v2-only columns. Smaller, simpler, but loses
  provenance.

**Why deferred:** Schema decision is yours.

---

### Bug 13 — No deduplication anywhere in the QA pipeline

**Severity: Medium.** Confirmed real impact: at least one source file
(`shoprite_rsid_3000_prices.csv`) has 68,082 duplicate rows that flow
into the deployed parquet. Skews any aggregate stat by chain.

**Symptom:** Neither Gate 1 (`data_loader._load_single_csv`) nor Gate 2
(the dormant `qaqc_screening_results.csv`) removes duplicate rows. The
screening CSV *reports* duplicates as the worst issue dimension on
multiple files but doesn't act on them.

**How to fix:** Add a deduplication pass after CSV load and before
parquet write. Decision: dedup on what columns? Most natural is
`(chain, timestamp, product_name, price)` — exact-match dedup. More
aggressive would also collapse on near-duplicate `product_name`.

**Where to put it:** In `_load_single_csv` (per-file, prevents in-file
duplicates) or in `rebuild_parquet.rebuild()` (post-concat, also catches
cross-file duplicates from v1+v2 overlap on the same chain).
Recommendation: post-concat in `rebuild()`.

---

### Bug 14 — QAQC screening is dormant + path mismatch

**Severity: Medium.** The diagnostic-screening framework is broken in two
independent ways. Without it, there's no systematic 18-dimension audit on
new files.

**Symptom (a) — path mismatch:** `scripts/analyze_qaqc_flagged_in_parquet.py`
looks for the screening CSV at `wayback grocery AO/data/qaqc_screening_results.csv`.
The file actually exists at
`AQ_wayback_grocery_mk_2/data/qaqc_screening_results.csv`. Diagnostic
script will fail to find input.

**Symptom (b) — generator missing:** The screening CSV's structure
(`blank_name, unknown_name, short_name, unit_only_name, size_code_name,
garbage_exact, garbage_substring, page_dump, price_in_name,
location_as_name, zero_negative_price, non_numeric_price, bad_timestamp,
non_wayback_url, non_store_specific, duplicates, missing_columns, read_error`)
suggests a dedicated generator script. The analyze script references it
as `helpers/confirm_stores.py`, which **does not exist** in the current
tree. So even if we wanted to regenerate the screening CSV with v2 data
included, we don't have the producer code.

**Decision needed:**
- Resurrect `confirm_stores.py` from git history, OR
- Replace it with a fresh QAQC step that operates on the unified 18-dim
  framework against the combined v1+v2 dataset.

**Why deferred:** This is a non-trivial chunk of work and depends on how
much QA rigor we want before the next deploy.

---

### Bug 15 — No row-count regression detection in deploy

**Severity: Low.** A safety net we don't have.

**Symptom:** `scripts/rebuild_parquet.py --deploy` does not compare the
new parquet against the existing one for row count, distinct-chain count,
year range, or schema before pushing to the `deploy` branch. A subtle bug
in the loader could halve the parquet (or worse) and the deploy would
proceed without complaint.

**How to fix:** Read the existing parquet at the start of `rebuild()`,
compare key counts before/after the rebuild, refuse to deploy if any
metric drops by more than a threshold (e.g. 20%) without `--force`. Two
or three new lines of code; an easy "Gate 1.5" addition.

---

## Documentation / process gaps

### G1 — v1 manifests survived the documented "v1 discard"

**Severity: Cosmetic. Doesn't affect data integrity, but documentation is
wrong.**

**Symptom:** Earlier project notes claimed "v1 outputs deleted from both
local and EC2." But 7,686 `.ndjson.gz` manifests from v1 actually
survived under `data/mk_2/manifest/` and were treated as
"manifest already exists, skipping CDX" by the v2 weekend run.

**Why this matters:** Anyone reading the prior session notes will assume
the v2 weekend run rebuilt every CDX manifest from scratch. It didn't —
it reused 7,686 v1 manifests and only rebuilt CDX for the ~1,000 chains
that had no manifest. The data is fine (CDX content is stable) but the
provenance attribution is muddier than the notes suggest.

---

### G2 — Status CSV is stale for unprocessed chains

**Severity: Cosmetic but misleading during investigation.**

**Symptom:** `data/scrape_universe_status.csv` shows 6,599 chains as
`CDX_PHASE_PENDING` — even though Phase 1 (CDX collection) finished days
ago for those chains. The per-chain row in the status CSV only updates
when the chain enters fetch+OCR.

**Result:** A reader of the status table can't distinguish "CDX done,
fetch+OCR not yet started" from "nothing has happened to this chain at
all."

**Suggested fix:** Have `cdx_phase` write `CDX_PHASE_DONE_PENDING_FETCH`
to the status CSV when Phase 1 completes, so the limbo state is
explicitly named.

---

### G3 — v2 retrospective Obsidian note never written

**Severity: Process — promised deliverable not yet produced.**

**Status:** Originally framed in the session-handoff prompt as
`grocery_pricing/experiments/Wayback Scrape v2 First Run.md`, mirroring
the v1 retrospective. Should follow the parallel-form template:
Hypothesis → Change applied → Cohort → Comparison baseline → Result →
Interpretation.

**Has not yet been written.** Should include attribution of Fix 1B,
Fix 2, Fix 3 (target rotation) and the disambiguation experiments that
confirmed Wayback's per-target rate-limit semantics.

---

### G4 — Fix 1B / Fix 2 / Fix 3 not yet committed to git

**Severity: Process.**

**Status:** All script edits made during this session are uncommitted.
The script version was bumped 2.0 → 2.1 but no commit captures the
change. Per project convention, the user does commits manually.

**Suggested logical groupings for commits:**
1. **v2.1 — partial-manifest preservation (Fix 1B):** the
   `cdx_query` retry-loop refactor that introduced `OK_PARTIAL_*`
   statuses and `COMPLETED_PARTIAL_*` chain dispatch.
2. **v2.1 — HTTP 400 = end-of-pages (Fix 2):** the `end_of_pages`
   sentinel in `cdx_query` that treats empty-body 400 on page≥1 as
   clean termination.
3. **v2.1 — target-rotation CDX scheduler (Fix 3):** the new
   `cdx_phase()` function, `CdxTarget` dataclass, `_fetch_one_cdx_page`
   helper, and the new CLI flags
   (`--cdx-concurrency`, `--cdx-only`, `--cdx-max-target-attempts`,
   `--no-target-rotation`). Plus the FD-leak fix that opens manifest
   files per-write instead of per-chain.

---

## Notes for whoever picks this up

- All open bugs are described relative to **`scrape_wayback_universe.py`
  at script_version 2.1**. Earlier 2.0 numbering may differ.
- The weekend run (run_id `2026-05-01T22:23:36Z`) was stopped manually
  at the Plum Market chain. ~1.37M priced rows were produced; ~6,500 of
  7,691 candidate chains never reached fetch+OCR. The dataset is on
  disk both locally and on EC2 (`research-nathan` via Tailscale).
- The c8i.8xlarge EC2 instance is still running and accruing cost; if
  no follow-up work is planned in the near term, consider stopping it.
- Bugs 11 and 12 should be fixed *together* since they both touch the
  parquet rebuild path and a single integration commit makes them
  testable as a unit.
