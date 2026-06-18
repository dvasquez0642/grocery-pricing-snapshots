# Grocery Pricing

Multi-source historical grocery pricing data, aggregated and visualized to study American food-price inflation. Prices come from Wayback Machine archives, newspaper advertisement OCR, and other public sources, ingested by AI-assisted scraping pipelines and surfaced through a Streamlit dashboard with map, basket-builder, and inflation-tracking views.

This is research code. It is not production-grade. It works, but it has rough edges — see the **Known issues** section below.

## Mission

There is growing discussion of an "affordability crisis" in the United States. Among the often-cited drivers are wage stagnation, housing-supply shortages, healthcare costs, and inflation as measured by CPI All Urban Consumers (~258 in Feb 2020 → 325 in Nov 2025). This project's goal is to make the **grocery component** of that inflation picture browsable and analyzable from raw and curated data, so that the user can apply their own filters and indices (Laspeyres / Paasche / Fisher Ideal) and reach defensible conclusions.

## What's where

### Streamlit dashboard (top-level)

- `app.py` — main Streamlit entry point (map, product view, basket builder, case studies)
- `data_loader.py` — three-tier loader: pre-built `data/pricing.parquet` → runtime cache → CSV rebuild
- `baskets.py`, `target_items.py` — basket and target-item definitions (Karen's Basket, NHANES meal archetypes)
- `categories.py`, `geocoder.py` — keyword categorization and bundled US location lookup
- `requirements.txt`, `.streamlit/config.toml`, `.python-version` — Streamlit Cloud config

### Wayback scraping pipelines

- **`AQ_wayback_grocery_mk_2/`** — current scrape pipeline. Two coordinated stages:
  1. SNAP search agent — for each chain in the USDA SNAP retailer registry, identify an official website (Gemini + Google Search grounding), populating `data/url_registry.csv`
  2. Wayback scrape — for each chain with a known domain, sweep web.archive.org via the CDX API, fetch snapshots, OCR images, write per-chain price CSVs

  In active development. Output lands at `AQ_wayback_grocery_mk_2/data/mk_2/`. **Not yet wired into the deployed app** — see Bug 11 below. See `AQ_wayback_grocery_mk_2/README.md` for operational details.

- **`wayback grocery AO/`** — legacy v1 fan-out. Many task groups, each a Ralph-loop scraper for a hypothesis-specific subset of chains. Live state lives in `wayback grocery AO/section_status.csv` and `wayback grocery AO/chain_assignments.csv`. Outputs land in per-task-group `data/` directories. This is what currently flows into the parquet that the deployed app reads.

### Other AOs (early-stage)

- `AO_college_university/` — Sodexo contract data for 4-year public institutions, sourced via Carnegie Classifications and Google Custom Search.
- `AO_newspaper_archive/` — newspaper advertisement OCR (Asheville Citizen-Times, Post-Bulletin).

### Analysis

- `analysis/` — R/Rmd notebooks. Karen's Basket inflation, NHANES meal archetypes, friends-of-the-project reports.

### Operational

- `scripts/` — `rebuild_parquet.py`, `deploy_app.py`, `run-r.sh`, and other one-shot tools
- `.opencode/skills/` — agent skill files (`agentflow-loop`, `deploy-app`, `r-analysis`, `update-app-parquet`)
- `AGENTS.md` — guidance for AI agents working in this repo
- `data/pricing.parquet` — pre-built parquet that the deployed dashboard loads (committed; rebuilt periodically by `scripts/rebuild_parquet.py`)

## Data flow

```
SNAP retailer registry  ──► search agent (mk_2)  ──► url_registry.csv (chain → domain)
                                                                  │
                                                                  ▼
                                              wayback scrape (mk_2) ──► AQ_wayback_grocery_mk_2/data/mk_2/*_prices.csv
                                                                                                       │
                                                                                                       │  (NOT yet
                                                                                                       │   sourced
                                                                                                       │   by the
                                                                                                       │   parquet
                                                                                                       │   builder)
                                                                                                       ▼

legacy v1 task groups  ──► task_group_*/data/*_prices.csv ──┐
                                                              ├──► scripts/rebuild_parquet.py ──► data/pricing.parquet ──► app.py (Streamlit)
            consolidated ──► wayback grocery AO/data/*_prices.csv ──┘
```

The parquet rebuilder vacuums from both `wayback grocery AO/data/` (higher priority on filename collisions) and every `wayback grocery AO/task_group_*/data/`. It does **not** currently include `AQ_wayback_grocery_mk_2/data/mk_2/`. Wiring mk_2's outputs into the rebuilder is the single most important step to get v2 work onto the deployed dashboard (see Bug 11).

## Quick start

### Run the dashboard locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

To override the data directory:

```bash
DATA_DIR=/path/to/your/data streamlit run app.py
```

### Run the mk_2 scrape pipeline

See `AQ_wayback_grocery_mk_2/README.md` for the full operational guide. Briefly:

```bash
cd AQ_wayback_grocery_mk_2
./run_on_ec2.sh                        # search agent
./run_scrape_on_ec2.sh --limit 10      # wayback scrape
./pull_from_ec2.sh                     # bring results home
```

Both scripts are restart-safe and pull-then-push EC2's authoritative state by default.

### Rebuild the parquet

```bash
python scripts/rebuild_parquet.py            # rebuild only
python scripts/rebuild_parquet.py --deploy   # rebuild + push to deploy branch
```

See also `.opencode/skills/update-app-parquet/`.

### Deploy the app

The dashboard is hosted privately on Streamlit Community Cloud. See `.opencode/skills/deploy-app/` for the deployment workflow.

## Development setup

- Python: 3.12 (see `.python-version`)
- Dashboard dependencies: `requirements.txt`. Each scraping pipeline maintains its own dependencies.
- Secrets: `.env` per pipeline (gitignored). Streamlit Cloud secrets via `.streamlit/secrets.toml` (gitignored). The dashboard expects an `app_password` secret for access control.
- The mk_2 pipeline uses Bright Data static-IP proxies for wayback scraping; Gemini API keys for both the search agent and OCR.

## Known issues

This section catalogues open bugs and deferred work. Each entry has location, severity, symptom, and (where known) a planned fix. Resolved bugs are removed from this list — git history preserves the diagnostic record.

### Wayback scrape pipeline (`AQ_wayback_grocery_mk_2/scrape_wayback_universe.py`)

The bug numbering follows the order issues surfaced during the v2 development cycle. Bugs 1B, 2, and 3 were fixed in script_version 2.1 (partial-manifest preservation, HTTP 400 = end-of-pages, target-rotation CDX scheduler). The fixes are in the current code; their landing-commits are now part of this repo's history.

#### Bug 4 — `runs.csv` error-counting has an operator-precedence quirk

- **Severity**: Low. Accounting still produces correct totals, but only by coincidence.
- **Location**: `scrape_wayback_universe.py`, around lines 1861-1865 (runs.csv aggregation block at end of `run()`).
- **Symptom**: The `or` between two `sum(...)` comprehensions binds at the wrong logical level. Python parses it as `(A and B) or (C and D)` rather than the apparently-intended `A and (B or C) and D`. Works today because B and C are equivalent in practice; a future refactor of either side could silently break the count.
- **Planned fix**: Add explicit parentheses, or restructure as a single comprehension with a unioned predicate.

#### Bug 5 — 0.5s between-page sleep is too short (mostly moot)

- **Severity**: Low. Effectively dead code under v2.1.
- **Location**: `cdx_query()`, line ~624 (`await asyncio.sleep(0.5)` between successive CDX pages).
- **Symptom**: Wayback CDX rate limits are per-target (URL+params, not source IP) and operate on minute-to-hour timescales; a half-second pause is meaningless.
- **Status**: Largely irrelevant under the v2.1 target-rotation scheduler (`cdx_phase()`), which does not paginate the same target back-to-back. Fix 2 confirmed Wayback returns the entire dataset on page 0 for almost all chains, so most chains never hit page 1.

#### Bug 6 — `in_flight` task accumulation in `cdx_phase` scheduler

- **Severity**: Medium. Real memory cost; would compound on bigger sweeps.
- **Location**: `cdx_phase()` worker dispatch loop. Tasks are created via `asyncio.create_task(_wrapped(target))` immediately and added to an `in_flight` set; the semaphore gates only the actual CDX request inside `_wrapped`, not the task creation.
- **Symptom**: During the weekend run we observed `in_flight=5,328` shortly after launch (with `--cdx-concurrency 32`) — ~5,000 tasks were sitting waiting on the semaphore, each holding a `CdxTarget` and a coroutine frame. Process RSS reached 5.8 GB during a 7,691-chain sweep.
- **Cost in practice**: Acceptable for 7K-chain sweeps on a 60 GB box; would explode on hundred-thousand-chain runs.
- **Planned fix**: Gate task *creation*, not just task execution. Pop a target from the queue only when the semaphore has capacity. Or refactor to a fixed pool of N worker coroutines pulling from the queue.

#### Bug 7 — ~1,025 chains marked `NO_CDX_COVERAGE`

- **Severity**: Medium. The diagnostic answer was discovered late in the v2 cycle; the fix is architectural.
- **Symptom**: 1,025 of 7,691 chains in the v2 weekend run ended up with status `NO_CDX_COVERAGE` — manifest existed on disk but decoded to zero usable URLs. Spot-check confirmed Wayback DOES have data for several of these chains (`acmemarkets.com`, `99ranch.com`, `10boxcostplus.com` all returned valid CDX results from a direct probe).
- **Root cause**: A prior aborted run wrote zero-row manifests for many chains (each ~37-49 bytes — gzip header only, no compressed payload). The current `cdx_phase` reuse-check trusts any manifest with `size > 20 bytes`, so empty zombie files get treated as "already done." ~2,400 manifests under 200 bytes exist on disk; ~1,025 chains have already been finalized as `NO_CDX_COVERAGE`, with the rest queued to follow the same fate when fetch+OCR reaches them.
- **Architectural shape of the fix** (mirrors the search agent's `__NOT-FOUND__` sentinel pattern): manifests should carry a positive completion sentinel — either a `_meta` header line in the NDJSON or a sidecar `.done` file. Empty files without the sentinel re-trigger CDX work. Successful "Wayback genuinely has nothing" outcomes leave a positive marker. The skip-decision becomes data-driven instead of file-existence-driven.
- **Workaround**: Targeted `--rebuild-manifest` run against the empty-manifest cohort.

#### Bug 8 — ShopRite has 251K `_no_prices` rows but 0 priced rows

- **Severity**: Unknown — high-traffic chain producing no priced data is suspicious.
- **Symptom**: ShopRite was processed by the validation run, fetched 251,152 snapshots, produced zero priced rows. Mariano's, processed under similar conditions, produced ~131K priced rows from comparable volume (~33% hit rate).
- **Two hypotheses**: (1) ShopRite genuinely doesn't publish prices in our extraction cascade's recognized formats; (2) ShopRite's HTML or JSON has a quirk that defeats one or more cascade stages.
- **Investigation needed**: Spot-check 5 random URLs from `shoprite_no_prices.csv`. Other big-name chains may be in the same situation; a QA pass across all `_no_prices` files (priced/no_priced ratio per chain) would surface them.

#### Bug 9 — Plum Market burned ~6+ hours on cached/blacklisted bookkeeping

- **Severity**: Low. Wallclock symptom, not a data-correctness issue.
- **Location**: `process_chain()` per-snapshot loop checking `processed_urls` and basename-blacklist before deciding to fetch.
- **Symptom**: During the weekend run, Plum Market's chain processing was observed at 220K of 271K pages, with `priced=9465 ocr=14778` frozen for hours. Throughput was ~80 page-iterations/sec but each was just "snapshot is in dedup or blacklist set → skip." No actual fetch or OCR work was happening.
- **Why it matters**: Single-chain processing serializes the whole run, and ~6-hour bookkeeping passes per chain do not compose well.
- **Planned fix**: Fast-path for chains where >X% of the manifest is already in dedup/blacklist sets — bulk-test the manifest against the dedup set before entering the per-snapshot loop.

#### Bug 10 — Single-process asyncio underutilizes the EC2 box

- **Severity**: Architectural. Costs roughly a factor of 30× on hardware utilization.
- **Symptom**: c8i.8xlarge instance (32 cores, 61 GB RAM) ran the weekend scrape at load average ~0.05; one core at ~9% CPU, the other 31 at 100% idle. The pipeline is one Python process, one asyncio event loop. Within-chain concurrency exists (`--snapshot-concurrency 400`, `--ocr-concurrency 64`) but cannot help when the chain is mostly cached or per-snapshot async I/O is the bottleneck. **No cross-chain parallelism in the fetch+OCR phase** — chains are processed strictly sequentially.
- **Two reasonable fixes**: (a) multi-process worker pool sharing a chain-level queue, each process running its own asyncio loop; (b) right-size the instance — a `c7i.large` or similar would be cheaper and the underutilization wouldn't matter.
- **Best tackled before the next big sweep**, not retrofit.

### Search agent (`AQ_wayback_grocery_mk_2/search_snap_universe.py`)

#### Bug — Search agent process hangs in `futex_do_wait` after completion

- **Severity**: Process hygiene. Doesn't affect data correctness; blocks restart-by-supervisor patterns.
- **Identified**: 2026-05-07 (PID 2604704 confirmed stuck since 2026-05-06).
- **Symptom**: After the script finishes processing all chains and writes its final progress line, the Python process never exits. Stuck in `futex_do_wait` (waiting on a lock). Holds onto file handles.
- **Probable cause**: ThreadPoolExecutor or memory-monitor task isn't shut down cleanly during exit.
- **Workaround**: Explicit kill after observing the final progress line.
- **Planned fix**: Audit shutdown sequence — cancel background tasks, shut down executor with explicit `wait=False` or join with timeout.

#### Bug — Search agent has no quota-aware throttling

- **Severity**: Medium. Forces a multi-launch usage pattern; wastes API calls on errors.
- **Identified**: 2026-04-29; recurred on 2026-05-06 and 2026-05-07.
- **Symptom**: `DynamicSemaphore` adapts on RAM pressure, not on API error rate. A run typically resolves ~4,500-5,000 chains successfully then hits Gemini's quota wall and produces error sidecars for the rest of the queue at full concurrency. Resilience pattern (`domain=""` stays as retry marker) makes this safe but slow — full coverage requires multiple runs.
- **Workaround**: Multi-launch — each run resolves ~4-5K chains; follow-up runs pick up the unresolved remainder. Safe (no phantom skips) but wasteful.
- **Planned fix**: Sliding-window error-rate monitor that throttles cap when 429 rate exceeds a threshold; restores cap when error rate drops. ~30-line addition.

### Parquet rebuild + data loader (`data_loader.py`, `scripts/rebuild_parquet.py`)

#### Bug 11 — `rebuild_parquet.py` doesn't include v2 (mk_2) data

- **Severity**: HIGH. The 1.37M priced rows from the v2 weekend run are **invisible to the deployed app** as currently configured. Single biggest blocker between v2 work and the dashboard.
- **Location**: `scripts/rebuild_parquet.py`, lines 56-82.
- **Symptom**: `collect_csv_files()` walks `wayback grocery AO/data/` and `wayback grocery AO/task_group_*/data/`. Neither glob reaches `AQ_wayback_grocery_mk_2/data/mk_2/`. Running `scripts/rebuild_parquet.py` right now produces a parquet with zero v2 rows.
- **Planned fix**: Add `AQ_wayback_grocery_mk_2/data/mk_2/` as a third source dir. Decide dedup priority: **recommendation v2 highest** (has provenance columns and was produced under the fixed pipeline). Pair with Bug 12 (schema decision) since both touch the same code path.

#### Bug 12 — v2 provenance columns silently dropped on load

- **Severity**: Medium. Loses metadata the app could use for filtering ("show only v2 rows" / "show only OCR-derived rows").
- **Location**: `data_loader.py:_load_single_csv`, lines 255-258. `out_cols` is hardcoded to a fixed 11-column subset.
- **Symptom**: V2 CSVs ship additional columns: `brand`, `source_path`, `source_image`, `pipeline`, `script_version`, `ocr_model`, `ocr_prompt_version`, `ocr_run_id`, `ocr_attempt_ts`. They're read by `pd.read_csv` but dropped at the `df[out_cols]` step.
- **Decision needed before fix**: wide schema (include all v2 columns; ~5-10% larger parquet; v1 rows get NaN) or narrow schema (drop v2-only columns, lose provenance). **Recommendation: wide.**

#### Bug 13 — No deduplication anywhere in the QA pipeline

- **Severity**: Medium. Confirmed real impact: at least one source file (`shoprite_rsid_3000_prices.csv`) has 68,082 duplicate rows that flow into the deployed parquet. Skews any aggregate stat by chain.
- **Symptom**: Neither `data_loader._load_single_csv` nor the dormant `qaqc_screening_results.csv` removes duplicate rows. The screening CSV reports duplicates as the worst issue dimension on multiple files but doesn't act on them.
- **Planned fix**: Deduplication pass after CSV load and before parquet write. Most natural key: `(chain, timestamp, product_name, price)`. Best location: post-concat in `rebuild_parquet.rebuild()`, since that catches cross-file duplicates from v1+v2 overlap.

#### Bug 14 — QAQC screening is dormant + path mismatch

- **Severity**: Medium. The diagnostic-screening framework is broken in two independent ways. Without it, no systematic 18-dimension audit on new files.
- **Symptom (a)** — path mismatch: `scripts/analyze_qaqc_flagged_in_parquet.py` looks for the screening CSV at `wayback grocery AO/data/qaqc_screening_results.csv`, but it actually exists at `AQ_wayback_grocery_mk_2/data/qaqc_screening_results.csv`. Diagnostic script will fail to find input.
- **Symptom (b)** — generator missing: The screening CSV's structure (18 issue dimensions) suggests a dedicated generator script. The analyze script references it as `helpers/confirm_stores.py`, which **does not exist in the current tree**.
- **Decision needed**: resurrect `confirm_stores.py` from git history, OR replace it with a fresh QAQC step against the unified 18-dim framework.

#### Bug 15 — No row-count regression detection in deploy

- **Severity**: Low. A safety net we don't have.
- **Symptom**: `scripts/rebuild_parquet.py --deploy` doesn't compare the new parquet against the existing one for row count, distinct-chain count, year range, or schema before pushing to the `deploy` branch. A subtle loader bug could halve the parquet and the deploy would proceed.
- **Planned fix**: Read the existing parquet at the start of `rebuild()`; refuse to deploy if any key metric drops by >20% without `--force`. Two or three new lines.

### Documentation / process gaps

#### G1 — v1 manifests survived the documented "v1 discard"

- **Severity**: Cosmetic. Doesn't affect data integrity; documentation was wrong.
- **Symptom**: Earlier project notes claimed "v1 outputs deleted from both local and EC2." But 7,686 `.ndjson.gz` manifests from v1 actually survived under `data/mk_2/manifest/` and were treated as "manifest already exists, skipping CDX" by the v2 weekend run.
- **Why it matters**: Anyone reading prior notes will assume v2 rebuilt every CDX manifest from scratch. It didn't — it reused 7,686 v1 manifests. Data is fine (CDX content is stable) but provenance attribution is muddier than the notes suggest.

#### G2 — Status CSV is stale for unprocessed chains

- **Severity**: Cosmetic but misleading during investigation.
- **Symptom**: `data/scrape_universe_status.csv` shows 6,599 chains as `CDX_PHASE_PENDING` even though Phase 1 (CDX collection) finished days ago for those chains. The per-chain row in the status CSV only updates when the chain enters fetch+OCR.
- **Fix**: Have `cdx_phase` write `CDX_PHASE_DONE_PENDING_FETCH` to the status CSV when Phase 1 completes, so the limbo state is explicitly named.

#### G3 — v2 retrospective Obsidian note never written

- **Severity**: Process — promised deliverable not yet produced.
- **Status**: Should follow the parallel-form template (Hypothesis → Change applied → Cohort → Comparison baseline → Result → Interpretation) and attribute Fix 1B, Fix 2, Fix 3 (target rotation) plus the disambiguation experiments that confirmed Wayback's per-target rate-limit semantics.

## Acknowledgments

- **USDA Food and Nutrition Service** — SNAP retailer data
- **American Council on Education** — Carnegie Classifications
- **Google** — Gemini API (search grounding, OCR)
- **Internet Archive** — Wayback Machine
- **AisleGopher.com** — historical price tracking data

## License

This project is for research and educational purposes. Data sources have their own licenses:

- USDA SNAP data: Public domain (U.S. Government work)
- Carnegie Classifications: Public use dataset
- Web-scraped data: Respect robots.txt and terms of service
