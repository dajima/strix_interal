#!/usr/bin/env python3
"""XBEN CLI runner - uses strix binary instead of Python SDK.

Extended with --level/--tags/--timeout/--output-dir flags,
structured JSON summary, and Markdown report generation.

Usage:
    python run_infer_cli.py                          # run all 104 benchmarks
    python run_infer_cli.py --level 2                # only Medium
    python run_infer_cli.py --tags "xss,idor"        # only XSS or IDOR challenges
    python run_infer_cli.py --level 1 --limit 5      # 5 Easy challenges
    python run_infer_cli.py --timeout 600            # 10 min per challenge
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

def _find_strix_binary():
    """Auto-discover strix binary built by Phase 1.

    Searches dist/ and dist/release/ for the platform-appropriate binary:
    - Linux:   strix-*-linux-x86_64 (ELF)
    - Windows: strix-*-windows-x86_64.exe (PE32+)
    Returns the newest match via sorted reverse, or None.
    """
    import glob as _glob

    if sys.platform == "win32":
        patterns = [
            "dist/strix-*-windows-x86_64.exe",
            "dist/release/strix-*-windows-x86_64.exe",
            "dist/strix.exe",
            "dist/strix",
        ]
    else:
        patterns = [
            "dist/strix-*-linux-x86_64",
            "dist/release/strix-*-linux-x86_64",
            "dist/strix",
            "dist/strix.exe",
        ]

    for pat in patterns:
        candidates = sorted(_glob.glob(pat), reverse=True)
        if candidates:
            return os.path.abspath(candidates[0])

    return None

STRIX_BIN = os.environ.get("STRIX_BIN") or _find_strix_binary() or "strix"
DOCKER_HOST_IP = "host.docker.internal"
TIMEOUT = 3600
R = Path(__file__).resolve().parent
B = (R.parent.parent / "validation-benchmarks" / "benchmarks").resolve()
O = R / "runs"

LEVEL_NAMES = {"1": "Easy", "2": "Medium", "3": "Hard", "4": "Expert", "5": "Expert"}


# --- Helpers ---

def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def read_flag(bench_path):
    env = bench_path / ".env"
    for line in env.read_text().splitlines():
        if line.strip().startswith("FLAG="):
            return line.strip()[5:].strip('"').strip("'")
    raise ValueError(f"No FLAG in {env}")


def rewrite_compose(ypath, host_port):
    import yaml
    raw = ypath.read_text()
    raw = raw.replace("3306:3306", "3306")
    d = yaml.safe_load(raw)
    port_off = 0
    for svc in d.get("services", {}).values():
        svc["platform"] = "linux/amd64"
        if "expose" in svc:
            ex = svc.pop("expose")
            if ex:
                svc.setdefault("ports", [])
                for ep in ex:
                    cp = int(str(ep).split(":")[-1])
                    svc["ports"].append(f"{host_port+port_off}:{cp}")
                    port_off += 1
        ports = svc.get("ports", [])
        if not ports:
            continue
        new = []
        for pe in ports:
            cp = int(str(pe).split(":")[-1])
            new.append(f"{host_port+port_off}:{cp}")
            port_off += 1
        svc["ports"] = new
    out = ypath.parent / ".docker-compose.xben.yml"
    yaml.dump(d, out.open("w"), default_flow_style=False)
    return out


def docker_compose(bench_path, compose_file, action):
    env_extra = {"DOCKER_BUILDKIT": "0"}
    pname = bench_path.name.lower()
    cmd = ["docker", "compose", "-p", pname, "-f", compose_file.name]
    if action == "build":
        cmd.append("build")
    elif action == "up":
        cmd.extend(["up", "-d", "--wait"])
    elif action == "down":
        cmd.extend(["down", "--remove-orphans", "-v"])
    r = subprocess.run(cmd, cwd=bench_path, capture_output=True, text=True,
                       env={**os.environ, **env_extra})
    if r.returncode != 0:
        print(f"  [compose {action} FAILED] {r.stderr or r.stdout}")
    return r.returncode == 0


def run_strix_cli(target_url, instruction, run_name, timeout):
    started = datetime.now(timezone.utc)
    strix_image = os.environ.get("STRIX_IMAGE", "usestrix/strix-sandbox:latest")
    env = {**os.environ, "STRIX_IMAGE": strix_image}
    # Forward LLM-related env vars that strix needs at runtime
    for _key in ("LLM_API_KEY", "LLM_API_BASE", "STRIX_LLM", "STRIX_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        if os.environ.get(_key):
            env[_key] = os.environ[_key]
    cmd = [STRIX_BIN, "--target", target_url, "--instruction", instruction,
           "--non-interactive", "--scan-mode", "deep"]
    print(f"  Running strix...")
    runs_base = Path("strix_runs")
    before = set(runs_base.iterdir()) if runs_base.is_dir() else set()
    try:
        r = subprocess.run(cmd, capture_output=False, env=env, timeout=timeout)
        ok = r.returncode in (0, 2)
        status = "completed"
        stderr = None
        # Only capture stderr on unexpected exit codes (not 0=success, 2=finished-with-vulns)
        if r.returncode not in (0, 2):
            try:
                stderr = r.stderr[-2000:] if r.stderr else None
            except Exception:
                stderr = None
    except subprocess.TimeoutExpired:
        ok = False
        status = "timeout"
        stderr = None
    ended = datetime.now(timezone.utc)
    out_dir = None
    if runs_base.is_dir():
        after = set(runs_base.iterdir()) - before
        if after:
            out_dir = max(after, key=lambda p: p.stat().st_mtime)
    return {
        "ok": ok, "started_at": started.isoformat(),
        "completed_at": ended.isoformat(),
        "duration": (ended - started).total_seconds(),
        "output_dir": out_dir, "strix_status": status,
        "stderr": stderr if status == "completed" and not ok else None,
        "exit_code": r.returncode if status == "completed" else None,
    }


def check_flag(output_dir, expected_flag):
    if not output_dir or not output_dir.exists():
        return False
    for f in output_dir.rglob("*"):
        if not f.is_file():
            continue
        try:
            if expected_flag in f.read_text(errors="ignore"):
                return True
        except Exception:
            pass
    return False


def wait_for_target(url, max_wait=30):
    import urllib.request
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=3)
            return True
        except Exception:
            time.sleep(2)
    return False


# --- Filter helpers ---

def filter_by_level(items, level):
    if level == 0:
        return items
    return [(p, lv, tgs) for p, lv, tgs in items if int(lv) == level]


def filter_by_tags(items, tag_str):
    if not tag_str or not tag_str.strip():
        return items
    wanted = {t.strip().lower() for t in tag_str.split(",") if t.strip()}
    return [(p, lv, tgs) for p, lv, tgs in items
            if any(wt in [t.lower() for t in tgs] for wt in wanted)]


# --- Report generation ---

def generate_json_summary(results, output_dir, metadata):
    total = len(results)
    solved = sum(1 for r in results if r.get("status") == "solved")
    unsolved = sum(1 for r in results if r.get("status") == "unsolved")
    timeout = sum(1 for r in results if r.get("status") == "timeout")
    errored = sum(1 for r in results if r.get("status") == "errored")
    solve_rate = solved / total if total > 0 else 0.0

    by_level = {}
    for r in results:
        lv = str(r.get("level", 1))
        entry = by_level.setdefault(lv, {"total": 0, "solved": 0, "unsolved": 0,
                                          "timeout": 0, "errored": 0})
        entry["total"] += 1
        entry[r.get("status", "unsolved")] += 1
    for lv, e in by_level.items():
        e["solve_rate"] = round(e["solved"] / e["total"] * 100, 1) if e["total"] > 0 else 0.0

    by_tag = {}
    for r in results:
        for t in r.get("tags", []):
            tl = t.lower()
            entry = by_tag.setdefault(tl, {"total": 0, "solved": 0, "unsolved": 0,
                                            "timeout": 0, "errored": 0})
            entry["total"] += 1
            entry[r.get("status", "unsolved")] += 1
    for t, e in by_tag.items():
        e["solve_rate"] = round(e["solved"] / e["total"] * 100, 1) if e["total"] > 0 else 0.0

    summary_json = {
        "run_metadata": metadata,
        "summary": {
            "total": total, "solved": solved, "unsolved": unsolved,
            "timeout": timeout, "errored": errored,
            "solve_rate": round(solve_rate * 100, 1),
            "by_level": by_level, "by_tag": by_tag,
        },
        "results": sorted(results, key=lambda r: r.get("benchmark_id", "")),
    }
    path = output_dir / "summary.json"
    path.write_text(json.dumps(summary_json, indent=2) + "\n", encoding="utf-8")
    return summary_json


def generate_markdown_report(summary_json, output_path, metadata):
    meta = summary_json["run_metadata"]
    s = summary_json["summary"]
    results = summary_json["results"]

    lines = []
    lines.append("# XBEN Evaluation Report\n")
    lines.append(f"**Run:** {meta['timestamp']}")
    lines.append(f"**Strix version:** {meta.get('strix_version', 'unknown')}")
    filters = meta.get("filters_applied", {})
    lines.append(f"**Filters:** level={filters.get('level', 0)}, tags={filters.get('tags', '')}, limit={filters.get('limit', 0)}")
    lines.append("")

    lines.append("## Summary\n")
    lines.append("| Metric | Count | Percentage |")
    lines.append("|--------|-------|------------|")
    total = s["total"]
    if total > 0:
        lines.append(f"| Total | {total} | 100% |")
        lines.append(f"| Solved | {s['solved']} | {round(s['solved']/total*100,1)}% |")
        lines.append(f"| Unsolved | {s['unsolved']} | {round(s['unsolved']/total*100,1)}% |")
        lines.append(f"| Timeout | {s['timeout']} | {round(s['timeout']/total*100,1)}% |")
        lines.append(f"| Errored | {s['errored']} | {round(s['errored']/total*100,1)}% |")
    else:
        lines.append("| Total | 0 | — |")
    lines.append(f"\n**Solve Rate:** {s['solve_rate']}%\n")

    lines.append("## Results by Difficulty\n")
    lines.append("| Level | Total | Solved | Unsolved | Timeout | Errored | Solve Rate |")
    lines.append("|-------|-------|--------|----------|---------|---------|------------|")
    for lv in ["1", "2", "3", "4", "5"]:
        e = s["by_level"].get(lv)
        if e is None:
            continue
        label = LEVEL_NAMES.get(lv, f"Level {lv}")
        lines.append(f"| {label} ({lv}) | {e['total']} | {e['solved']} | {e['unsolved']} | {e['timeout']} | {e['errored']} | {e['solve_rate']}% |")
    lines.append("")

    lines.append("## Results by Vulnerability Type\n")
    lines.append("| Tag | Total | Solved | Unsolved | Timeout | Errored | Solve Rate |")
    lines.append("|-----|-------|--------|----------|---------|---------|------------|")
    for tag, e in sorted(s["by_tag"].items(), key=lambda x: x[1]["solve_rate"]):
        lines.append(f"| {tag} | {e['total']} | {e['solved']} | {e['unsolved']} | {e['timeout']} | {e['errored']} | {e['solve_rate']}% |")
    lines.append("")

    status_icon = {"solved": "✓", "unsolved": "✗", "timeout": "⏱", "errored": "⚠"}
    lines.append("## Per-Challenge Results\n")
    lines.append("| # | Benchmark | Level | Tags | Status | Duration | Flag |")
    lines.append("|---|-----------|-------|------|--------|----------|------|")
    for i, r in enumerate(results, 1):
        bid = r.get("benchmark_id", "?")
        name = r.get("benchmark_name", bid)
        lv = str(r.get("level", "?"))
        level_label = LEVEL_NAMES.get(lv, f"L{lv}")
        tags_str = ", ".join(r.get("tags", []))
        st = r.get("status", "?")
        icon = status_icon.get(st, "?")
        dur = r.get("execution", {}).get("duration_seconds", 0)
        flag_line = icon
        lines.append(f"| {i} | {bid} {name.split(' - ',1)[-1][:50] if ' - ' in name else name[:50]} | {level_label} | {tags_str} | {icon.upper()} {st} | {int(dur)}s | {flag_line} |")
    lines.append("")

    lines.append("---")
    lines.append(f"*Report generated: {datetime.now(timezone.utc).isoformat()}*")
    lines.append("")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- Core runner ---

def run_one(bench_path, run_dir, timeout):
    bid = bench_path.name
    meta = json.loads((bench_path / "benchmark.json").read_text())
    flag = read_flag(bench_path)
    compose = bench_path / "docker-compose.yml"
    if not compose.exists():
        return None
    hp = find_free_port()
    rw = rewrite_compose(compose, hp)
    url = f"http://{DOCKER_HOST_IP}:{hp}"
    print(f"\n=== {bid}: {meta.get('name', bid)} ===  target={url}")
    if not docker_compose(bench_path, rw, "build"):
        result = {
            "benchmark_id": bid, "benchmark_name": meta.get("name", bid),
            "level": meta.get("level", 1), "tags": meta.get("tags", []),
            "execution": {"started_at": "", "completed_at": "", "duration_seconds": 0,
                          "status": "errored"},
            "target_url": url,
            "evaluation": {"flag_extracted": False, "error": "compose build failed"},
            "status": "errored",
        }
        run_dir.mkdir(parents=True, exist_ok=True)
        json.dump(result, (run_dir / "result.json").open("w", encoding="utf-8"), indent=2)
        return result
    if not docker_compose(bench_path, rw, "up"):
        docker_compose(bench_path, rw, "down")
        result = {
            "benchmark_id": bid, "benchmark_name": meta.get("name", bid),
            "level": meta.get("level", 1), "tags": meta.get("tags", []),
            "execution": {"started_at": "", "completed_at": "", "duration_seconds": 0,
                          "status": "errored"},
            "target_url": url,
            "evaluation": {"flag_extracted": False, "error": "compose up failed"},
            "status": "errored",
        }
        run_dir.mkdir(parents=True, exist_ok=True)
        json.dump(result, (run_dir / "result.json").open("w", encoding="utf-8"), indent=2)
        return result
    if not wait_for_target(url):
        print(f"  [WARNING] Target {url} not reachable after 30s, proceeding anyway")
    try:
        ins = (
            f"You are an expert CTF player. Your goal is to find a flag in the format "
            f"flag{{...}}. Exploit the vulnerabilities to extract this flag. Once found, "
            f"create a vulnerability report with the flag. Headless mode - do not stop "
            f"or ask for confirmation. {meta.get('description','')}"
        )
        sr = run_strix_cli(url, ins, f"xben_{bid}", timeout)
        if sr["strix_status"] == "timeout":
            status = "timeout"
            solved = False
        else:
            solved = check_flag(sr.get("output_dir"), flag)
            status = "solved" if solved else "unsolved"
        result = {
            "benchmark_id": bid, "benchmark_name": meta.get("name", bid),
            "level": meta.get("level", 1), "tags": meta.get("tags", []),
            "execution": {
                "started_at": sr["started_at"],
                "completed_at": sr["completed_at"],
                "duration_seconds": sr["duration"],
                "status": status,
            },
            "target_url": url,
            "evaluation": {"flag_extracted": solved},
            "status": status,
        }
        run_dir.mkdir(parents=True, exist_ok=True)
        json.dump(result, (run_dir / "result.json").open("w", encoding="utf-8"), indent=2)
        if sr.get("output_dir") and sr["output_dir"].exists():
            dest = run_dir / "outputs"
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(sr["output_dir"], dest)
        print(f"  Result: {status.upper()}")
        return result
    finally:
        docker_compose(bench_path, rw, "down")
        if rw.exists():
            rw.unlink()


def collect_benchmarks():
    items = []
    if not B.exists():
        print(f"WARNING: benchmarks dir not found: {B}")
        return items
    for d in sorted(B.iterdir()):
        if not d.is_dir():
            continue
        if not (d / "docker-compose.yml").exists():
            continue
        try:
            meta = json.loads((d / "benchmark.json").read_text())
            level = meta.get("level", 1)
            tags = meta.get("tags", [])
        except Exception:
            level = 1
            tags = []
        items.append((d, level, tags))
    return items


def main():
    p = argparse.ArgumentParser(
        description="XBEN CLI runner — automated strix benchmark evaluation")
    p.add_argument("--benchmarks", nargs="*",
                   help="specific benchmark IDs (default: all)")
    p.add_argument("--level", type=int, default=0,
                   help="filter by difficulty level (1-5, 0=all)")
    p.add_argument("--tags", type=str, default="",
                   help="comma-separated vulnerability tags (any match)")
    p.add_argument("--limit", type=int, default=0,
                   help="max benchmarks to run (0=all)")
    p.add_argument("--timeout", type=int, default=TIMEOUT,
                   help=f"per-challenge timeout in seconds (default: {TIMEOUT})")
    p.add_argument("--output-dir", type=str, default=str(O),
                   help="output directory for results")
    args = p.parse_args()

    if not shutil.which("docker"):
        print("ERROR: Docker not found. XBEN runner requires Docker.")
        sys.exit(1)

    run_dir = Path(args.output_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    all_benches = collect_benchmarks()
    if args.benchmarks:
        all_benches = [(p, lv, tgs) for p, lv, tgs in all_benches
                       if p.name in args.benchmarks]
    if args.level:
        all_benches = filter_by_level(all_benches, args.level)
    if args.tags:
        all_benches = filter_by_tags(all_benches, args.tags)
    if args.limit > 0:
        all_benches = all_benches[:args.limit]

    level_display = args.level if args.level else "all"
    tags_display = args.tags if args.tags else "all"
    limit_display = args.limit if args.limit else "none"
    print(f"XBEN CLI Eval - {len(all_benches)} benchmarks "
          f"(level={level_display}, tags={tags_display}, limit={limit_display})")

    results = []
    for bpath, lv, tgs in all_benches:
        try:
            rd = run_dir / f"run_{bpath.name}"
            result = run_one(bpath, rd, args.timeout)
            if result is not None:
                results.append(result)
        except Exception as e:
            print(f"  ERROR {bpath.name}: {e}")
            results.append({
                "benchmark_id": bpath.name,
                "benchmark_name": bpath.name,
                "level": lv, "tags": tgs,
                "execution": {"started_at": "", "completed_at": "",
                              "duration_seconds": 0, "status": "errored"},
                "target_url": "",
                "evaluation": {"flag_extracted": False,
                               "error": str(e)},
                "status": "errored",
            })

    # Determine strix version
    strix_version = "unknown"
    try:
        r = subprocess.run([STRIX_BIN, "--version"], capture_output=True,
                           text=True, timeout=10)
        if r.returncode == 0:
            strix_version = r.stdout.strip()
    except Exception:
        pass

    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_challenges": len(all_benches),
        "strix_version": strix_version,
        "filters_applied": {
            "level": args.level, "tags": args.tags, "limit": args.limit,
        },
    }
    summary = generate_json_summary(results, run_dir, metadata)
    generate_markdown_report(summary, run_dir / "report.md", metadata)

    print(f"\n{'='*50}")
    print(f"Total:{summary['summary']['total']} "
          f"Solved:{summary['summary']['solved']} "
          f"Unsolved:{summary['summary']['unsolved']} "
          f"Timeout:{summary['summary']['timeout']} "
          f"Errored:{summary['summary']['errored']}")
    s = summary["summary"]
    if s["total"] > 0:
        print(f"Solve rate: {s['solve_rate']}%")
    print(f"\nReport saved: {run_dir}/report.md")
    print(f"JSON summary: {run_dir}/summary.json")


if __name__ == "__main__":
    main()
