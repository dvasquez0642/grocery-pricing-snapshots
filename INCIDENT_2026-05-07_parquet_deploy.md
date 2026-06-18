# Incident Report — Accidental Bulk Deletion via Parquet Deploy

- **Report written**: 2026-05-11T20:09:00Z
- **Incident commit**: `2afe1b1470b79b49ff1c33be9c57a0baad6f8442` on `main`
- **Mirrored on**: `deploy` branch as `8ffb0ca0995ba3c39c4ac84e0afd8c8e7861c019` (parquet only)
- **Incident timestamp**: 2026-05-07T16:11:30-0600 (commit author date)
- **Pushed to origin**: 2026-05-07 (same session)
- **Status**: Recoverable. No code or data permanently lost. Bad commit is still HEAD of `main` and `deploy`.

## TL;DR

A `python scripts/rebuild_parquet.py --deploy` invocation produced a commit titled "Rebuild pricing.parquet (970,433 rows, 246 sources)" that, in addition to the intended parquet update, **also committed 8,554 file deletions, 3,171 file additions, 542 (mostly spurious) renames, and 3 file modifications** sitting in the working tree's index from before this session began. The dirty tree was a legitimate in-progress v1 restructuring effort (retiring 97 task groups, adding 10 new ones), but it was not ready to ship and was committed without review.

The parquet itself is internally consistent — it reflects whatever CSV inputs were on disk at rebuild time. The problem is that the parquet was built from a *truncated input set*, because **1,190 priced CSV file paths** had been deleted from disk just before rebuild ran (representing **938 unique chains entirely absent from HEAD**; another 156 deleted basenames still have at least one surviving copy elsewhere in the tree). The deployed Streamlit dashboard is currently serving a parquet with 970,433 rows where it previously had 1,302,789 — a 25% drop, driven entirely by the input-shrink, not by any v1-vs-v2 quality issue.

**Canonical counts used throughout this report**: 1,190 priced CSV paths deleted; 1,094 unique priced basenames deleted; 938 unique chains entirely lost from HEAD; 156 deleted basenames recoverable via a surviving same-name copy; 1,273 no_priced CSV paths deleted; 2,463 CSV paths deleted in total.

## Known mechanism of failure

Five conditions combined to produce the outcome. Each was individually unremarkable; the combination was not anticipated.

### 1. Dirty working-tree predates this session

The outer repo's working tree carried **12,268 file changes** at session start (per `git show --stat 2afe1b1`; the raw `git show --name-status` enumeration counts 12,270 name-status records because renames are recorded as paired source/destination entries there but counted singly in the stat summary). These were not random cruft — they were a coherent in-progress refactor: retiring 97 legacy task groups, introducing 10 new ones, cleaning up `legacy/`, `docker/`, and assorted scaffolding. The dirty state had been staged (in the git index, not just unstaged in the working tree) at some point before this session began.

The session opened with `git status --short` already reporting these as `A` (added), `D` (deleted), `R100` (renamed), and `M` (modified) entries. I observed the count and characterized it as "messy working tree" without ever inspecting *what kind* of changes were staged.

### 2. Index state survived a stash/pop cycle

During the mk_2 mini-repo integration earlier in the session, I ran `git stash push -u -m "pre-mk2-integration: outer-repo dirty tree (12,269 files)"` to isolate the integration from the dirty tree, did the integration work, then `git stash pop`'d to restore the dirty state.

`git stash pop` correctly restores **both** the working tree state AND the index state. The 8,554 deletions remained in the index after pop, just as they had been before stash. I reported "working tree restored" without verifying which restored changes were staged vs unstaged.

### 3. `rebuild_parquet.py --deploy` invokes `git commit` without a path argument

The deploy function at `scripts/rebuild_parquet.py:179-190` does:

```python
print("\n--- Git: commit on main ---")
run("git add data/pricing.parquet")
result = subprocess.run("git diff --cached --quiet", shell=True, cwd=ROOT)
if result.returncode == 0:
    print("  No changes to commit (parquet unchanged).")
else:
    run(f'git commit -m "Rebuild pricing.parquet ({rows:,} rows, {sources} sources)"')
```

The script's mental model: "stage the parquet, commit just the parquet." But `git commit -m "..."` (without `--only` or a path argument) commits **everything currently staged**, not just what `git add` just added. With a clean index, the script behaves as intended. With a pre-populated index, the staged dirty tree gets swept in.

This is a latent bug in the deploy script — it assumes a clean index but does not verify it.

### 4. Script ran a fresh rebuild on top of stale CSV state

The skill `update-app-parquet` says: rebuild reads from the local data directories, write the parquet. The script doesn't verify that local data is in sync with any other state (EC2, prior commit, etc.). When the dirty-tree deletions removed 1,190 priced CSV file paths from disk (representing 938 unique chains with no surviving copy elsewhere), the rebuild read whatever was left and produced a parquet from the truncated input set.

The script did the right thing given its inputs. The inputs were wrong.

### 5. No pre-commit review

The deploy script invokes commit programmatically and immediately pushes to the `deploy` branch (which Streamlit Cloud auto-deploys). There is no human-in-the-loop step that would have shown "12,268 files changed" before committing.

A `git status` before pushing would have revealed the problem in seconds. None was performed.

## Blast radius

### Code / repository state

- **`main` branch**: `2afe1b1` is the current HEAD. Contains:
  - 8,554 file deletions (intended subset: ~5,500 legacy code/scaffolding files; unintended sweep: 1,190 priced CSV paths, 1,273 no_priced CSV paths, and assorted other content)
  - 3,171 file additions (intended subset: new task group files, BUGS.md, analysis files; some of these are also "in-progress" not "ready")
  - 542 rename detections (almost all spurious — they're git's `R100` rename detection picking up coincidental content matches between deleted files and newly-added empty templates)
  - 3 actual file modifications
  - 1 intended change: `data/pricing.parquet` rebuilt
- **`deploy` branch**: `8ffb0ca` was pushed. This branch is an orphan-style "app files only" branch, so it contains only the new parquet and the app files synced from main. **The bulk file deletions did NOT propagate to `deploy`.** Only the parquet artifact did.
- **`origin/main`**: holds `2afe1b1`. Pushed without `--force`, so this was a fast-forward push.
- **`origin/deploy`**: holds `8ffb0ca`. Pushed without `--force`.

### Data state

The two columns below distinguish "delete operations recorded in `2afe1b1`" (1,190 priced paths) from "net loss of priced paths between `0766090` and HEAD" (1,055 net loss). The discrepancy is git's rename-detection: 135 deleted `_prices.csv` paths were paired by git's `R100` heuristic with newly-added empty templates in different task groups (most renames are spurious — they reflect coincidental content matches between empty/header-only files, not actual moves). The 1,190 deletion count is the canonical "what was deleted" number; the net-loss column tells you the steady-state inventory delta.

| Location | Files at `0766090` (pre) | Files at `2afe1b1` (post) | Net | Deletion ops in `2afe1b1` |
|---|---:|---:|---:|---:|
| `_prices.csv` total under `wayback grocery AO/` | 1,381 | 326 | −1,055 paths | 1,190 |
| ↳ in `wayback grocery AO/data/` (consolidated, immediate children) | 205 | 146 | −59 (m-y range — see Mechanism 5b) | 35 |
| ↳ in `wayback grocery AO/task_group_*/data/` | 1,173 | 180 | −993 paths | 1,152 |
| ↳ in `wayback grocery AO/legacy/` | 3 | 0 | −3 | 3 |
| `_no_prices.csv` total under `wayback grocery AO/` | 1,489 | 330 | −1,159 paths | 1,273 |

Unique-basename view of priced deletions:

- **1,094** distinct chain basenames appear in the deletion list
- **156** of those basenames still have a surviving copy elsewhere in HEAD (data preserved under a different path)
- **938** of those basenames have no surviving copy anywhere — these are the chains entirely absent from HEAD

**All deleted files are recoverable from `0766090c84246f44b0618205c7f5d1330cd88b28`** (the prior HEAD) — verified safe as a recovery anchor for CSVs (see "Recovery anchor verification" below). No data is permanently lost from the git object store; git's reflog and the prior commit object retain everything.

#### Recovery anchor verification

The commit message of `0766090` is "Patch pricing.parquet with Karen's basket data quality fixes," which raises an obvious concern: a parquet-mutating commit named after data-quality fixes could plausibly have modified some CSVs too. Verified by direct tree-hash comparison this is **not** the case:

```
Tree hash for 'wayback grocery AO/' at:
  d5f9b68: ad2f6e3ba818d0609ba2af33ddb003d24f937d54
  5ad3ba9: cb628f2f5425ee6b1bbc7b53afa0fc327dfdfc4d
  15e7a34: cb628f2f5425ee6b1bbc7b53afa0fc327dfdfc4d  (parent of 25aea7b)
  25aea7b: cb628f2f5425ee6b1bbc7b53afa0fc327dfdfc4d  (parent of 0766090)
  0766090: cb628f2f5425ee6b1bbc7b53afa0fc327dfdfc4d  (incident anchor — bit-identical to 25aea7b and 15e7a34)
```

The `wayback grocery AO/` subtree at `0766090` is **bit-for-bit identical** to its predecessors `25aea7b`, `15e7a34`, and `5ad3ba9`. The Karen's basket patch (`0766090`) only modified `data/pricing.parquet` itself plus seven files outside any CSV source path (`AGENTS.md`, `data/confirmed_stores.csv`, `data/qaqc_screening_results.csv`, two docker scripts, `ec2_leases.csv`, `helpers/confirm_stores.py`) — none of which are inputs to `rebuild_parquet.py`.

Equivalently safe recovery anchors: `25aea7b`, `15e7a34`, `5ad3ba9`. Use `0766090` because it's the immediate pre-incident parent and the easiest to reason about; the others would produce identical CSV restoration results.

### Deployed application

- The Streamlit Cloud dashboard auto-redeployed after the `deploy` branch push.
- The dashboard now serves a parquet with:
  - **970,433 rows** (down from 1,302,789 at prior commit `0766090`)
  - **202 unique chains** (down from larger prior count; specific delta not fully audited)
  - **246 source files** (down from 553)
- **Major chains lost from the dashboard**: Whole Foods, Safeway, Publix, Meijer, Wegmans, Piggly Wiggly, Wild Fork, ~24 ShopRite variants (out of 73), and the long tail of smaller/specialty chains. Total of 938 unique chain basenames are entirely absent from HEAD (no surviving copy anywhere).
- Users querying for any of these chains since the deploy push (~2026-05-07 16:12 UTC onward) have seen empty results.

### Mechanism 5b — the alphabetic anomaly (root cause identified)

A separate, smaller deletion pattern within the dirty tree warrants its own note. Inside the main consolidated `wayback grocery AO/data/` directory, **120 files were missing from HEAD** (85 explicit `D` deletions + 35 paths recorded as the source side of spurious `R100` renames). The missing files form a strict alphabetical range: files starting with `m` through `y`. Files starting with `a` through (most of) `m` survived.

**Root cause identified: an alphabetical-order operation failed at the first LFS-tracked file and abandoned the remainder of the sweep.**

The disposition boundary, sorted alphabetically:

```
[ 89] KEPT  ...
[ 90] KEPT  market_of_choice_no_prices.csv
[ 91] KEPT  market_of_choice_prices.csv
[ 92] KEPT  marketplace_foods_no_prices.csv
[ 93] KEPT  marketplace_foods_prices.csv
[ 94] KEPT  mckays_market_no_prices.csv
[ 95] KEPT  mckays_market_prices.csv
[ 96] KEPT  mckays_no_prices.csv
[ 97] KEPT  mckays_prices.csv
[ 98] KEPT  megamart_supermarket_no_prices.csv          <-- last surviving file
[ 99] GONE  megamart_supermarket_prices.csv             <-- 3.5 GB LFS-tracked
[100] GONE  meijer_no_prices.csv
[101] GONE  meijer_prices.csv
[102] GONE  mercato_all_prices.csv
...
[418] GONE  yokes_fresh_market_no_prices.csv
```

Every file alphabetically before `megamart_supermarket_prices.csv` survives. Every file from that point onward is gone. The boundary is exact, sharp, and falls at the **first LFS-tracked file** in alphabetical order.

`.gitattributes` registers three LFS-tracked CSVs in the consolidated dir:

```
/wayback grocery AO/data/megamart_supermarket_prices.csv   filter=lfs ...
/wayback grocery AO/data/namaste_plaza_prices.csv          filter=lfs ...
/wayback grocery AO/data/trucchis_supermarket_prices.csv   filter=lfs ...
```

All three (`m`-, `n`-, `t`-prefix) sit in the m-y range; all three were marked deleted; all three would have been encountered in alphabetical order at positions where the sweep failed.

**Hypotheses ruled out:**

- **Size-correlation / memory overflow on large non-LFS data**: refuted. Per-band deletion rates are uniform (~25%) across size classes from 1 KB to 10 MB. The 27.7 MB `hannaford_prices.csv` (largest non-LFS file in the dir) survived. Files in the deleted range have median 18.3 KB; median surviving file is 6.6 KB. Size is not the discriminator.
- **Random or content-driven filter**: refuted. The strict alphabetical pattern with sharp boundary at the first LFS file is not consistent with any per-file-content predicate.
- **Operator running `git rm` on a sorted glob and getting cancelled**: not refuted by direct evidence, but the LFS boundary is too precise to be coincidence — far more likely the LFS file caused the interruption rather than being where an unrelated interruption happened to occur.

**Likely operational mechanism:**

Some script or git operation processed the consolidated dir in alphabetical order. At `megamart_supermarket_prices.csv` it tried to handle the 3.5 GB LFS-tracked file and failed in a way that:

1. Marked the file as deleted in the staging index (rather than leaving it alone), AND
2. Continued the alphabetical sweep but marked every subsequent file as deleted too, OR
3. Was caught by a global try/except that converted the LFS failure into "mark everything from here as deleted."

This is consistent with several real failure modes:
- A backup/sync script using LFS objects that aren't present locally (LFS pull never completed for those three files)
- An `git lfs checkout` failure that cascaded
- An automated git workflow encountering the LFS server being unreachable
- A custom script using `git lfs` subcommands that crashed on the first big LFS object

**The 35 R-renames (spurious `R100` matches) make the pattern look more chaotic than it is**: git's content-similarity heuristic paired the deleted m-y files against newly-added empty/template CSVs in the *new* task groups (`task_group_coop_natural_3`, `task_group_farm_fresh_6`, etc.), but those aren't real moves — they're coincidental matches between empty-template content and the deleted files' content (which, if LFS resolution failed, would have been just the small pointer-file text).

**This actually strengthens the LFS-failure hypothesis**: if an LFS operation replaced the actual file content with pointer-text or empty content during the failure, then git's rename detection would have seen those near-identical small contents and matched them with the newly-added empty templates in different task groups. The renames are a *side effect* of the LFS failure, not unrelated noise.

**Recovery implication:**

These 120 deletions are **virtually certainly unintentional**. The LFS-failure boundary leaves no room for an "operator chose to retire m-y chains" interpretation — the sharp cut at the first LFS file is too consistent with a mechanical failure. Recovery of these files via `git checkout 0766090 -- 'wayback grocery AO/data/'` is the right action. However, the three LFS-tracked files (megamart 3.5 GB, namaste 770 MB, trucchis 196 MB) will need actual LFS objects to be present locally; a checkout will restore the pointer files only. If LFS objects aren't recoverable from the LFS server, those three chains stay lost regardless.

Verification of LFS status before recovery is recommended: `git lfs ls-files` or `git lfs fetch --all` to confirm LFS object availability.

### What was actually intentional (within the dirty tree)

To be precise about what the dirty tree represents, broken down by sub-pattern:

- **97 task groups fully retired** (0 files surviving in HEAD): bulk legacy v1 cleanup. Names like `task_group_bakery_deli`, `task_group_butcher_meat`, `task_group_coop_natural`, `task_group_farm_produce`, `task_group_ethnic_specialty`, etc. **This intent is consistent with the "mk_2 is the canonical successor" project direction documented in the new README.** Source code, scaffolding, AGENTS.md copies, and per-task-group helper duplication being retired here is straightforward cleanup.
- **10 brand-new task groups added** (`task_group_gap_fill_4`, `task_group_grocery_batch_a/b/c`, `task_group_grocery_deli_a`, `task_group_hannaford_gap_fill`, `task_group_indie_grocer_a`, `task_group_market_batch_a/b/c`): these are new v1 work, paired with the retirements above. May or may not be ready for prime time.
- **17 task groups still active** with mixed adds and deletes: ongoing reorganization.
- **`wayback grocery AO/legacy/` cleanup**: 356 file deletions. Plausibly intentional.
- **`wayback grocery AO/docker/` cleanup**: 8 file deletions. Plausibly intentional.

### What was NOT intentional

The unintended part of the dirty tree, captured by the commit:

- **938 unique chains with no surviving copy anywhere in HEAD**. These are priced CSVs whose basenames were deleted (mostly from retired task groups) without being migrated to the consolidated dir, and which have no surviving same-name copy in any other location in HEAD. Either the consolidation step was supposed to happen first and didn't, or these chains were judged not worth preserving — the operator's intent is required to disambiguate. If consolidation was intended, this is real data loss until restored.
- **35 priced CSV deletions in the consolidated dir alphabetical m-y range**: probably an artifact of an interrupted in-progress operation, not deliberate.
- **The combination "let the deploy script swallow this as a single commit"**: definitely not intentional.

## Forensic evidence

### Commit identity

```
commit 2afe1b1470b79b49ff1c33be9c57a0baad6f8442
Author: Nathan Schweizer <65908773+npschweizer@users.noreply.github.com>
Date:   Thu May 7 16:11:30 2026 -0600

    Rebuild pricing.parquet (970,433 rows, 246 sources)
```

### Reflog (showing the deploy sequence)

```
2afe1b1 HEAD@{2026-05-07 16:12:17}: checkout: moving from deploy to main
8ffb0ca HEAD@{2026-05-07 16:11:52}: commit: Update pricing.parquet: 970,433 rows from 246 sources
b2d8cc5 HEAD@{2026-05-07 16:11:44}: checkout: moving from main to deploy
2afe1b1 HEAD@{2026-05-07 16:11:43}: reset: moving to HEAD
2afe1b1 HEAD@{2026-05-07 16:11:30}: commit: Rebuild pricing.parquet (970,433 rows, 246 sources)
4148c41 HEAD@{2026-05-07 14:30:47}: commit: Update README to current state; catalogue known bugs
```

### Stat summary

`git show --stat 2afe1b1` reports:
```
12268 files changed, 11539741 insertions(+), 7500035 deletions(-)
```

`git show --name-status 2afe1b1` enumerates by action letter:
```
   3171 A   (added)
   8554 D   (deleted)
    542 R   (renamed; mostly spurious — R100 means git's content-similarity
              rename detection at 100% — coincidental matches between deleted
              files and newly-added empty/template files in different paths)
      3 M   (modified)
```

The `--stat` summary's 12,268 vs the `--name-status` raw line total of 12,270 differ by 2: the stat summary's edge-case accounting around renames vs git's internal rename-detection threshold. The deletion-side count (8,554) is what matters for blast-radius purposes.

### File-type breakdown of deletions

- 2,463 CSV files (1,190 `_prices.csv`, 1,273 `_no_prices.csv`)
- 95 copies of `proxy_manager.py` (one per task group)
- 95 copies of `helpers.py`
- 94 copies of `multi_model_ocr.py`
- 94 copies of `config.py`
- 94 copies of `analyze_gemini_tokens.py`
- 99 copies of `AGENTS.md`
- 89 copies each of `search_agent.md`, `review_agent.md`, `obsidian_logger.md`, `exploit_agent.md`
- 84 copies of `SKILL.md` plus other scaffolding docs
- 81 copies of `requirements.txt`
- 356 files under `wayback grocery AO/legacy/`
- 8 files under `wayback grocery AO/docker/`

## Recovery options

All options below are recoverable using git's prior-commit content. The pre-incident commit `0766090c84246f44b0618205c7f5d1330cd88b28` still contains every deleted file intact.

### Option A — full revert of `2afe1b1`

`git revert 2afe1b1` creates a forward commit that undoes everything in the incident commit, including the parquet rebuild itself. Then re-run `rebuild_parquet.py --deploy` with a clean index.

- Pros: Cleanest history. No force-push. No data lost. Recovers ALL deletions including the intended ones.
- Cons: Re-introduces the dirty tree state to the working tree (as deletions to be re-staged manually). Brings back the 5,500 intentional v1 cleanup files that probably *do* need to be deleted eventually. Operator must re-curate.

### Option B — selective restore + new parquet

Restore only the priced/no_priced CSVs that were swept in unintentionally, leave the intentional code/scaffolding deletions alone, then rebuild the parquet.

```
git checkout 0766090 -- 'wayback grocery AO/data/'
git checkout 0766090 -- 'wayback grocery AO/task_group_*/data/'
git commit -m "Restore CSV data files accidentally deleted in 2afe1b1"
python scripts/rebuild_parquet.py --deploy
```

- Pros: Restores the data without reverting the intentional code cleanup. Forward-only history.
- Cons: Requires per-pattern selective restore. Operator must verify the m-y consolidated-dir deletions are also restored. The 938 task-group CSVs with no surviving same-name copy elsewhere in HEAD get restored to retired task groups (re-creating directories that the v1 cleanup intended to be empty). Operator must then decide whether to migrate the restored CSVs to the consolidated dir or accept them in their original retired-task-group locations.

### Option C — hard reset on `main`, rebuild, force-push

```
git reset --hard 4148c41   # the README commit, before 2afe1b1
git checkout 0766090 -- 'wayback grocery AO/data/'
git checkout 0766090 -- 'wayback grocery AO/task_group_*/data/'
git commit -m "Restore v1 CSV data prior to parquet rebuild"
python scripts/rebuild_parquet.py --deploy
git push --force-with-lease origin main
```

- Pros: Cleanest end state. The incident commit disappears from history; the recovery looks like a normal rebuild against the correct inputs.
- Cons: **Requires force-push to `main`**. Anyone with the old `2afe1b1` checked out locally will diverge. Reflog still preserves `2afe1b1` for 90 days, so it's recoverable, but force-push is irreversible against the remote. Also requires force-push of `deploy` to overwrite `8ffb0ca` (lower risk — `deploy` is auto-generated).

### Option D — accept current state, document, move on

Leave `2afe1b1` as-is. Treat the deployment as "the new baseline." The 938 lost chains stay lost until a future v2 sweep produces replacement data.

- Pros: No work. History is honest.
- Cons: The deployed dashboard is missing 25% of its prior data. Major chains are absent. Until v2 catches up, the dashboard regresses for users.

## Recommended action

**Option C** is the cleanest and safest given the deployment is private and the operator (sole user) controls all consumers. The force-push concern is minimal: Streamlit Cloud will simply redeploy from the new `deploy` head, the local working copy is single-developer, no collaborators are pulling. The reflog preserves the bad commit for inspection.

However, **before any recovery action**, the operator should explicitly confirm:

1. The 97 fully-retired task groups SHOULD remain deleted (intentional v1 cleanup).
2. The 938 unique chain basenames with no surviving copy anywhere in HEAD WERE supposed to be migrated to the consolidated dir before retirement.
3. The 35 m-y range deletions in the consolidated dir were NOT intentional.
4. The 10 new task groups (`gap_fill_4`, `grocery_batch_a/b/c`, etc.) and their files DO belong in HEAD.

Confirmations on these four points determine whether Option B (selective restore) or Option C (clean reset + selective restore + rebuild) is the right shape, and exactly which paths to selectively restore.

## Process gaps that allowed this

1. **No pre-commit review in `rebuild_parquet.py --deploy`.** The script should refuse to commit if the index contains anything other than `data/pricing.parquet`. A `git diff --cached --name-only` check that asserts the result is exactly `data/pricing.parquet` would have caught this.
2. **No dirty-tree awareness in the skill.** The `update-app-parquet` skill says nothing about the state of the working tree before invocation. The skill should require a clean index (or document that it commits the index wholesale, depending on which behavior is intended).
3. **`git commit` without a path argument is a footgun in scripts.** Programs invoking commit should pass explicit paths (`git commit -- data/pricing.parquet`) to guarantee scope. The current `git add` + `git commit` pattern relies on the caller's index being clean.
4. **No post-commit verification.** After committing, the script could `git show --stat HEAD` and refuse to push if the file count exceeds a threshold (e.g., > 5 files for a parquet update).
5. **The dirty tree was carried across sessions without inspection.** I (and prior agents) characterized it as "messy" without auditing what it represented. A `git status --short | wc -l` of 12,269 should have triggered a serious investigation, not been treated as background noise.

## Recommended preventative measures

(These are recommendations for future build mode, not actions taken in this report.)

1. **Patch `rebuild_parquet.py:deploy()`** to assert empty index before staging the parquet:
   ```python
   staged = subprocess.run("git diff --cached --name-only", shell=True, cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
   if staged:
       raise RuntimeError(f"Index is not clean; refusing to deploy. Staged: {staged}")
   ```
2. **Use explicit path in `git commit`**: `run('git commit -- data/pricing.parquet -m "..."')` instead of relying on caller's index.
3. **Add a post-commit stat check** that refuses to push if `git show --stat HEAD` reports more than N files.
4. **Document the skill** to require clean working tree as a precondition.
5. **Add to BUGS.md as a new entry** (resolved or unresolved depending on whether preventatives are implemented in the same commit as recovery).

## Appendix — files affected at the individual level

Full deletion list is available via:

```
git show --name-status 2afe1b1 | awk '/^D\t/ {print substr($0,3)}'
```

Full addition list:

```
git show --name-status 2afe1b1 | awk '/^A\t/ {print substr($0,3)}'
```

Full rename pairs (mostly spurious):

```
git show --name-status 2afe1b1 | awk '/^R/' 
```

The prior commit `0766090c84246f44b0618205c7f5d1330cd88b28` ("Patch pricing.parquet with Karen's basket data quality fixes") is the recovery anchor. Although the commit message implies parquet-mutating QAQC work, the `wayback grocery AO/` source-CSV tree at this commit is bit-identical (same tree-hash `cb628f2f5425ee6b1bbc7b53afa0fc327dfdfc4d`) to predecessors `25aea7b`, `15e7a34`, and `5ad3ba9` — verified via `git ls-tree`. The patch only touched `data/pricing.parquet` and a handful of non-CSV-source files (see "Recovery anchor verification" in the Data state section). Any of those four commits is an equally valid recovery anchor for restoring the CSVs.
