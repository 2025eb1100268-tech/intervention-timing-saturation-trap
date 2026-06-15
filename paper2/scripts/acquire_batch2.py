"""Phase 5 Task 1: acquire 15 additional aime_coder trajectories.

Source (public, anonymous S3):
    s3://swe-bench-submissions/verified/20250514_aime_coder/trajs/

Selection rule (FIXED A PRIORI, applied in alphabetical instance_id order):
  - skip the 5 instances already in data/swebench_pilot/ (the Paper-1 pilot)
  - (a) must parse cleanly with the existing aime-coder parser
  - (b) must have 25-70 actions (comparable to the existing 5)
  - take the FIRST 15 that satisfy (a) and (b)

Every skip is logged with its reason to batch2/SKIP_LOG.md. Downloaded raw
files land in data/swebench_pilot/batch2/.

Downloads happen via `aws s3 cp --no-sign-request`. Files are fetched to a
temp path, parsed/checked, and only KEPT if selected (rejected downloads are
deleted so the batch2 dir contains exactly the selected set).
"""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from heart_adapters.claude_code.trajectory import parse_trajectory_file

PILOT_DIR = Path("data/swebench_pilot")
BATCH2_DIR = PILOT_DIR / "batch2"
S3_PREFIX = "s3://swe-bench-submissions/verified/20250514_aime_coder/trajs/"

ALREADY_USED = {
    "astropy__astropy-12907", "astropy__astropy-13033", "astropy__astropy-13236",
    "astropy__astropy-13398", "astropy__astropy-13453",
}

MIN_ACTIONS = 25
MAX_ACTIONS = 70
TARGET_NEW = 15


def list_s3() -> list[str]:
    r = subprocess.run(
        ["aws", "s3", "ls", S3_PREFIX, "--no-sign-request"],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        raise RuntimeError("aws s3 ls failed")
    ids = []
    for line in r.stdout.splitlines():
        parts = line.split()
        if parts and parts[-1].endswith(".json"):
            ids.append(parts[-1][:-len(".json")])
    return sorted(ids)


def download(instance_id: str, dest: Path) -> bool:
    r = subprocess.run(
        ["aws", "s3", "cp", f"{S3_PREFIX}{instance_id}.json", str(dest),
         "--no-sign-request"],
        capture_output=True, text=True, timeout=120,
    )
    return r.returncode == 0 and dest.exists()


def main():
    if not PILOT_DIR.exists():
        sys.stderr.write("run from repo root\n"); sys.exit(2)
    BATCH2_DIR.mkdir(exist_ok=True)

    all_ids = list_s3()
    print(f"S3 trajs available: {len(all_ids)}")

    selected = []
    skips = []  # (instance_id, reason)
    tmpdir = Path(tempfile.mkdtemp(prefix="batch2_dl_"))

    for iid in all_ids:
        if len(selected) >= TARGET_NEW:
            break
        if iid in ALREADY_USED:
            skips.append((iid, "already in Paper-1 pilot (the original 5)"))
            continue
        dest = BATCH2_DIR / f"{iid}.json"
        if dest.exists():
            # already downloaded in a prior run; re-check it
            tmp = dest
        else:
            tmp = tmpdir / f"{iid}.json"
            if not download(iid, tmp):
                skips.append((iid, "download failed"))
                continue
        # (a) parse cleanly
        try:
            events = parse_trajectory_file(tmp)
        except Exception as e:
            skips.append((iid, f"parse error: {e!r}"))
            if tmp != dest:
                tmp.unlink(missing_ok=True)
            continue
        n = len(events)
        # (b) action-count window
        if not (MIN_ACTIONS <= n <= MAX_ACTIONS):
            skips.append((iid, f"action count {n} outside [{MIN_ACTIONS},{MAX_ACTIONS}]"))
            if tmp != dest:
                tmp.unlink(missing_ok=True)
            continue
        # selected -> keep in batch2
        if tmp != dest:
            dest.write_bytes(tmp.read_bytes())
            tmp.unlink(missing_ok=True)
        selected.append((iid, n))
        print(f"  SELECTED {iid} ({n} actions)  [{len(selected)}/{TARGET_NEW}]")

    # write skip log
    lines = ["# Batch2 acquisition skip log (Phase 5 Task 1)", ""]
    lines.append(f"Source: `{S3_PREFIX}` (public, anonymous).")
    lines.append(f"Available trajectories: {len(all_ids)}.")
    lines.append(f"Selection rule (a priori): first {TARGET_NEW} in alphabetical "
                 f"instance_id order that parse cleanly AND have "
                 f"{MIN_ACTIONS}-{MAX_ACTIONS} actions, excluding the original 5.")
    lines.append("")
    lines.append(f"## Selected ({len(selected)})")
    lines.append("")
    lines.append("| # | instance_id | actions |")
    lines.append("|---|---|---|")
    for i, (iid, n) in enumerate(selected, 1):
        lines.append(f"| {i} | {iid} | {n} |")
    lines.append("")
    lines.append(f"## Skipped ({len(skips)}) — in order encountered")
    lines.append("")
    lines.append("| instance_id | reason |")
    lines.append("|---|---|")
    for iid, reason in skips:
        lines.append(f"| {iid} | {reason} |")
    lines.append("")
    (BATCH2_DIR / "SKIP_LOG.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"\nselected {len(selected)}, skipped {len(skips)} before reaching target")
    print(f"skip log: {BATCH2_DIR / 'SKIP_LOG.md'}")
    if len(selected) < TARGET_NEW:
        print(f"WARNING: only {len(selected)} selected (< {TARGET_NEW} target)")


if __name__ == "__main__":
    main()
