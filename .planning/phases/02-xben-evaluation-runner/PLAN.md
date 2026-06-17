---
wave: 1
depends_on: []
files_modified: ["xben-benchmarks/XBEN/run_infer_cli.py"]
autonomous: true
---

# Phase 2: XBEN Evaluation Runner - Plan

<task_summary>
1 wave. 2 tasks. Task 2.1 refactors run_infer_cli.py to add --level/--tags filters, timeout tracking, and structured per-run JSON output. Task 2.2 adds post-run Markdown report generation from collected JSON results.
</task_summary>

## Requirements Covered

| ID | Requirement | Covered By |
|----|-------------|------------|
| XBEN-01 | Challenge subset selection by --level, --tags, --limit | Task 2.1 |
| XBEN-02 | Pass/fail report by difficulty tier | Task 2.2 |
| XBEN-03 | Structured JSON results per challenge | Task 2.1 |
| XBEN-04 | Reliable Docker cleanup between runs | Task 2.1 (already implemented, verified) |
| XBEN-05 | Markdown report with summary stats | Task 2.2 |

## Artifacts This Phase Produces

### Modified Files
| File | Description |
|------|-------------|
| `xben-benchmarks/XBEN/run_infer_cli.py` | Extended with --level/--tags/--timeout flags, timeout tracking, improved JSON output format |

### New Functions (in run_infer_cli.py)
| Function | Description |
|----------|-------------|
| `filter_by_level(benchmarks, levels)` | Filter benchmark list by numeric level(s) |
| `filter_by_tags(benchmarks, tags)` | Filter benchmark list by tag inclusion |
| `generate_markdown_report(results, output_path)` | Generate formatted Markdown report from JSON results |
| `generate_json_summary(results, output_path)` | Write full JSON summary with metadata |

### New CLI Flags
| Flag | Description |
|------|-------------|
| `--level N` | Filter challenges by difficulty level (1-5, single value) |
| `--tags TAG1,TAG2` | Filter challenges by vulnerability tags (comma-separated, any match) |
| `--timeout N` | Override per-challenge timeout in seconds (default: 3600) |
| `--output-dir PATH` | Custom output directory for results (default: runs/) |

### Output Files (produced at runtime)
| File | Description |
|------|-------------|
| `runs/{timestamp}/summary.json` | Full JSON results: metadata + per-challenge status + summary stats |
| `runs/{timestamp}/report.md` | Formatted Markdown report with tables and charts |
| `runs/{timestamp}/run_{XBEN-ID}/result.json` | Per-challenge result (existing pattern, enhanced) |

## Threat Model

### Attack Surface Analysis

**1. Docker Escape via Benchmark Compose Files**
- **Threat:** Malicious docker-compose.yml in a benchmark directory escapes the sandbox
- **Severity:** MEDIUM — benchmark source is trusted (bundled with repo), but compose rewrites touch host networking
- **Mitigation:** Compose files rewritten before execution with `platform: linux/amd64` enforced. Ports mapped to dynamic host ports only. `docker compose down -v` on every exit path (finally block). No privileged containers in benchmark definitions.

**2. Flag Leakage Across Challenge Runs**
- **Threat:** A previous challenge's Docker resources (volumes, networks) persist and expose flag data to the next challenge
- **Severity:** MEDIUM — would invalidate benchmark results
- **Mitigation:** Each challenge uses unique project name (`bench_path.name.lower()`). `docker compose down --remove-orphans -v` in finally block removes ALL volumes. Pre-flight `docker system prune -f` before first challenge. Rewritten compose file deleted after each run.

**3. Unbounded Execution Time**
- **Threat:** A hung strix process blocks the entire benchmark suite indefinitely
- **Severity:** LOW — timeout is existent but not code-enforced in all paths
- **Mitigation:** `subprocess.run(timeout=TIMEOUT)` enforced at 3600s. Timeout caught and reported as status "timeout" (not "unsolved"). Per-challenge try/except ensures hung challenge doesn't stall subsequent ones.

**4. Docker Not Available**
- **Threat:** Runner invoked on a system without Docker
- **Severity:** LOW — clear error is better than cryptic subprocess failure
- **Mitigation:** Pre-flight check at script entry: `shutil.which("docker")` must succeed. Exit with clear error message if Docker not found. Consistent with strix core's Docker dependency check.

### Threat Summary

| # | Threat | Severity | Mitigation Strategy |
|---|--------|----------|---------------------|
| T1 | Malicious compose escape | MEDIUM | Port rewriting, platform enforcement, down -v cleanup |
| T2 | Flag leakage across runs | MEDIUM | Unique project names, volume removal, .docker-compose.xben.yml cleanup |
| T3 | Unbounded execution | LOW | subprocess timeout, try/except catch |
| T4 | Docker not available | LOW | Pre-flight shutil.which("docker") check |

---

## Waves

### Wave 1: XBEN Runner Enhancement (1 wave, 2 tasks)

This phase has 2 tasks organized in a single wave. Task 2.1 extends the core runner logic. Task 2.2 builds on the JSON output from Task 2.1 to generate Markdown reports — but can run on top of existing result.json files without requiring live Docker execution.

**Wave 1 goals:** run_infer_cli.py supports --level/--tags/--limit/--timeout; produces structured JSON summary; generates formatted Markdown report with difficulty/vulnerability-type breakdowns.

---

## Tasks

### Task 2.1: Extend run_infer_cli.py — filtering, timeout tracking, structured JSON output

**Requirement:** XBEN-01 (filtering), XBEN-03 (JSON output), XBEN-04 (Docker cleanup)
**File:** `xben-benchmarks/XBEN/run_infer_cli.py` (MODIFY)
**Wave:** 1
**Depends on:** None

<read_first>
- xben-benchmarks/XBEN/run_infer_cli.py (current state — 209 lines, understand every function)
- validation-benchmarks/benchmarks/XBEN-001-24/benchmark.json (metadata format — level, tags, name, description)
- validation-benchmarks/benchmarks/XBEN-010-24/benchmark.json (level=3 "hard" example)
- .planning/phases/02-xben-evaluation-runner/02-CONTEXT.md (locked decisions D-01 through D-10)
- .planning/REQUIREMENTS.md (XBEN-01 through XBEN-05)
</read_first>

<action>
Modify `xben-benchmarks/XBEN/run_infer_cli.py`:

1. **Fix hardcoded path** at line 11: Replace `B = Path(r"D:\AI\strix_interal\validation-benchmarks\benchmarks")` with `B = (R.parent.parent / "validation-benchmarks" / "benchmarks").resolve()` — resolves relative to repo root, not machine-specific absolute path.

2. **Add --level flag** to argparse:
   - `p.add_argument("--level", type=int, default=0, help="filter by difficulty level (1-5, 0=all)")`

3. **Add --tags flag** to argparse:
   - `p.add_argument("--tags", type=str, default="", help="comma-separated vulnerability tags (any match)")`

4. **Add --timeout flag** to argparse:
   - `p.add_argument("--timeout", type=int, default=TIMEOUT, help="per-challenge timeout in seconds")`
   - Override the module-level `TIMEOUT` with `args.timeout` in main().

5. **Add --output-dir flag** to argparse:
   - `p.add_argument("--output-dir", type=str, default=str(O), help="output directory for results")`
   - Replace hardcoded `O` usage in main() with `args.output_dir`.

6. **Add filter function `filter_by_level(items, level)`**:
   - If level is 0, return all items.
   - Filter items where the benchmark's level (from benchmark.json, normalized to int) equals `level`.
   - Items without a parsable level default to level 1 (existing behavior).

7. **Add filter function `filter_by_tags(items, tag_str)`**:
   - If tag_str is empty, return all items.
   - Split tag_str by comma, strip whitespace, lowercase.
   - Filter items where ANY of the specified tags appears in the benchmark's tags list.
   - Case-insensitive matching.

8. **Modify `collect_benchmarks()` to parse tags into the return tuple**:
   - Return `(Path, level, tags_list)` instead of just `(Path, level)`.
   - Update all callers to handle the 3-tuple.

9. **Add timeout tracking in `run_one()`**:
   - Catch `subprocess.TimeoutExpired` explicitly in `run_strix_cli()` and return status `"timeout"` instead of `"unsolved"`.
   - In the returned dict, add `"status": "timeout"` when timeout occurs.

10. **Enhance `run_one()` to mark errored runs differently**:
    - If `run_strix_cli()` returns `None` (compose failure), mark status as `"errored"` in the result dict.
    - Attach stderr from compose failures to the result dict under `"error_detail"`.

11. **Modify `main()` to collect ALL per-challenge result dicts and write a JSON summary**:
    - Collect the `result` dict from each `run_one()` call into a list.
    - After all challenges complete, write `{run_dir}/summary.json` with structure:
      ```json
      {
        "run_metadata": {
          "timestamp": "ISO datetime",
          "total_challenges": N,
          "strix_version": "from STRIX_BIN --version or 'unknown'",
          "filters_applied": {"level": N, "tags": "...", "limit": N}
        },
        "summary": {
          "total": N, "solved": N, "unsolved": N, "timeout": N, "errored": N,
          "solve_rate": 0.0
        },
        "results": [ ... per-challenge result dicts ... ]
      }
      ```
    - Compute summary counts from collected results.

12. **Add pre-flight Docker check at start of main()**:
    - Call `shutil.which("docker")` at script entry.
    - If Docker not found, print "ERROR: Docker not found. XBEN runner requires Docker." and exit 1.

13. **Add `--benchmarks` flag handling for level/tag-filtered lists**:
    - When `--benchmarks` is provided, filter by name FIRST, then apply level/tags filters to the narrowed list.
    - Print the filter summary before running: "XBEN Eval — {N} benchmarks (level={L}, tags={T}, limit={M})"

14. **Preserve existing behavior**:
    - `find_free_port()`, `read_flag()`, `rewrite_compose()`, `docker_compose()`, `run_strix_cli()`, `check_flag()`, `wait_for_target()` — keep these unchanged.
    - `run_one()` — keep the core logic intact, only add timeout and error tracking.
    - `finally` block with `docker_compose(bench_path, rw, "down")` and `rw.unlink()` — keep exactly as-is (D-08).
</action>

<acceptance_criteria>
- `python xben-benchmarks/XBEN/run_infer_cli.py --help` shows --level, --tags, --timeout, --output-dir flags
- `python xben-benchmarks/XBEN/run_infer_cli.py --level 3 --limit 5` runs only level-3 challenges, max 5
- `python xben-benchmarks/XBEN/run_infer_cli.py --tags "xss,sqli"` runs only challenges tagged xss OR sqli
- `xben-benchmarks/XBEN/runs/{timestamp}/summary.json` exists after completion
- `summary.json` contains `run_metadata`, `summary` (with total/solved/unsolved/timeout/errored/solve_rate), and `results` array
- Docker not found exits non-zero with clear error message
- Per-challenge `result.json` has `status` field with values "solved"/"unsolved"/"timeout"/"errored"
- Hardcoded `D:\AI\strix_interal\` path is replaced with relative resolution
- `docker compose down` runs in finally block of every run_one() call
- No changes to strix/ Python package (pure runner enhancement)
</acceptance_criteria>

---

### Task 2.2: Generate Markdown report from JSON results

**Requirement:** XBEN-02 (difficulty/vulnerability-type breakdown), XBEN-05 (Markdown report)
**File:** `xben-benchmarks/XBEN/run_infer_cli.py` (MODIFY — add function, call from main)
**Wave:** 1
**Depends on:** Task 2.1 (needs structured JSON output format)

<read_first>
- xben-benchmarks/XBEN/run_infer_cli.py (Task 2.1 modified version — understand new JSON format)
- xben-benchmarks/XBEN/runs/run_XBEN-001-24/result.json (existing per-challenge JSON — if exists, understand format)
- .planning/phases/02-xben-evaluation-runner/02-CONTEXT.md (D-05, D-06: report format requirements)
</read_first>

<action>
Add two functions to `xben-benchmarks/XBEN/run_infer_cli.py` and call them from `main()`:

1. **Add `generate_json_summary(results, output_dir, metadata)` function**:
   - Write the full JSON summary file (this replaces the inline JSON dump in Task 2.1 main()).
   - Structure:
     ```json
     {
       "run_metadata": { "timestamp": ISO, "total_challenges": N, ... },
       "summary": {
         "total": N, "solved": N, "unsolved": N, "timeout": N, "errored": N,
         "solve_rate": float (solved/total), "by_level": { "1": {"total":N, "solved":N, "solve_rate":0.0}, ... },
         "by_tag": { "sql_injection": {"total":N, "solved":N, "solve_rate":0.0}, ... }
       },
       "results": [ sorted by benchmark_id ]
     }
     ```
   - `by_level` groups results by their level field (1→Easy, 2→Medium, 3→Hard).
   - `by_tag` groups results by each tag (a challenge with ["xss","idor"] appears in both groups).

2. **Add `generate_markdown_report(results, output_path, metadata)` function**:
   - Write `report.md` to `output_path`.
   - Report structure:
     ```
     # XBEN Evaluation Report
     
     **Run:** {timestamp}
     **Strix version:** {version}
     **Filters:** level={L}, tags={T}, limit={M}
     
     ## Summary
     
     | Metric | Count | Percentage |
     |--------|-------|------------|
     | Total | {N} | 100% |
     | Solved | {N} | {P}% |
     | Unsolved | {N} | {P}% |
     | Timeout | {N} | {P}% |
     | Errored | {N} | {P}% |
     
     **Solve Rate:** {P}%
     
     ## Results by Difficulty
     
     | Level | Total | Solved | Unsolved | Timeout | Errored | Solve Rate |
     |-------|-------|--------|----------|---------|---------|------------|
     | Easy (1) | {N} | {N} | {N} | {N} | {N} | {P}% |
     | Medium (2) | {N} | {N} | {N} | {N} | {N} | {P}% |
     | Hard (3) | {N} | {N} | {N} | {N} | {N} | {P}% |
     
     ## Results by Vulnerability Type
     
     | Tag | Total | Solved | Unsolved | Timeout | Errored | Solve Rate |
     |-----|-------|--------|----------|---------|---------|------------|
     | {tag} | {N} | {N} | {N} | {N} | {N} | {P}% |
     (one row per unique tag, sorted by solve rate ascending)
     
     ## Per-Challenge Results
     
     | # | Benchmark | Level | Tags | Status | Duration | Flag |
     |---|-----------|-------|------|--------|----------|------|
     | 1 | XBEN-001-24 IDOR Trading Platform | Easy | idor, default_credentials | SOLVED | 245s | ✓ |
     | 2 | XBEN-010-24 SSRF Injection | Hard | ssrf, rce | UNSOLVED | 864s | ✗ |
     (sorted by benchmark_id)
     
     ---
     *Report generated: {ISO datetime}*
     ```

3. **Call both functions from `main()`** after all challenges complete:
   - After collecting all results, compute `by_level` and `by_tag` summary dicts.
   - Call `generate_json_summary(results, run_dir, metadata)`.
   - Call `generate_markdown_report(results, run_dir / "report.md", metadata)`.
   - Print "Report saved: {run_dir}/report.md" to stdout.

4. **Level name mapping**: Use a dict `LEVEL_NAMES = {"1": "Easy", "2": "Medium", "3": "Hard", "4": "Expert", "5": "Expert"}`.

5. **Status display in per-challenge table**: Use emoji indicators: ✓ (solved), ✗ (unsolved), ⏱ (timeout), ⚠ (errored).
</action>

<acceptance_criteria>
- `report.md` exists in run directory after completion
- Report contains "## Summary" section with metrics table
- Report contains "## Results by Difficulty" table with Easy/Medium/Hard rows
- Report contains "## Results by Vulnerability Type" table with per-tag breakdown
- Report contains "## Per-Challenge Results" table with all challenges listed
- `summary.json` contains `by_level` and `by_tag` objects with per-group stats
- Solve rate in JSON matches report (both computed from same data)
- Empty runs (0 challenges) produce valid report with "No challenges executed"
- Report generation is at end of main() — after all challenges complete, not during
</acceptance_criteria>

---

## Verification Criteria

### Goal-Backward Verification

| Success Criterion (from ROADMAP) | How Plan Achieves It |
|----------------------------------|---------------------|
| 1. Filter by --level, --tags, --limit from CLI | Task 2.1: argparse --level/--tags/--limit flags + filter functions |
| 2. Pass/fail summary by difficulty tier | Task 2.2: "Results by Difficulty" table in Markdown + by_level in JSON |
| 3. Pass/fail summary by vulnerability type | Task 2.2: "Results by Vulnerability Type" table in Markdown + by_tag in JSON |
| 4. No orphaned Docker resources after each run | Task 2.1: `docker compose down -v` in finally block (verified in existing code — no changes needed, D-08) |
| 5. Structured JSON results file | Task 2.1: summary.json with metadata, summary stats, and per-challenge results |
| 6. Markdown report with summary statistics | Task 2.2: report.md with summary table, difficulty breakdown, vulnerability-type breakdown, timing data |

### must_haves

1. `python xben-benchmarks/XBEN/run_infer_cli.py --level 2` runs only level-2 challenges
2. `python xben-benchmarks/XBEN/run_infer_cli.py --tags "xss"` runs only xss-tagged challenges
3. `--limit N` caps total challenges run to N
4. JSON summary file contains `summary.by_level` and `summary.by_tag` with per-group solve_rates
5. Markdown report contains "Results by Difficulty" and "Results by Vulnerability Type" tables
6. `docker compose down -v` executes in finally block for every challenge (existing behavior preserved)
7. Hardcoded Windows path `D:\AI\strix_interal\` replaced with relative resolution
8. Pre-flight Docker check exits with clear error if Docker not found
9. Per-challenge status is one of: "solved", "unsolved", "timeout", "errored"
10. Timeout challenges tracked separately from unsolved in summary stats

### Integration Test (E2E verification)

```bash
# Dry-run with filtering
python xben-benchmarks/XBEN/run_infer_cli.py --level 1 --limit 2 --timeout 60

# Verify output files exist
ls xben-benchmarks/XBEN/runs/*/summary.json
ls xben-benchmarks/XBEN/runs/*/report.md

# Verify JSON structure
python -c "
import json
with open('xben-benchmarks/XBEN/runs/.../summary.json') as f:
    d = json.load(f)
    assert 'run_metadata' in d
    assert 'summary' in d
    assert 'results' in d
    assert 'by_level' in d['summary']
    assert 'by_tag' in d['summary']
    print('OK')
"

# Verify report has required sections
grep -q "Results by Difficulty" xben-benchmarks/XBEN/runs/*/report.md
grep -q "Results by Vulnerability Type" xben-benchmarks/XBEN/runs/*/report.md
```
