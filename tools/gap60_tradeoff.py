"""GAP-60: put R1 validity and R1 diversity on the same axis.

R1 reports +74% Pfam hits (the framework's strongest positive) and K7 reports
12.6x less novelty (3.7% vs 46.6%). They were measured on different samples, so
a reviewer reads the pair as "validity bought with collapse". This tool scores
both axes on the SAME FASTA files.

Axes
----
* ``hits``      -- ``family_validity`` hmmscan total hits per 200 records.
* ``clusters``  -- within-generation MMseqs clustering at 90% identity:
  ``n_clusters`` and ``singleton_fraction_sequences``. This is the direct
  collapse measurement: if the framework collapses the population, generated
  sequences start clustering together.
* ``novelty``   -- distance to the Pfam holdout DB. Reported for completeness;
  it is **degenerate on this corpus** (0 hits against the holdout DB makes
  every record "novel" by construction), and the tool says so rather than
  quoting a 1.0.

Isolation
---------
The vendored MMseqs pipeline hardcodes the *relative* path ``results/mmseqs_tmp``.
Two concurrent scorers therefore destroy each other. This tool ``chdir``s into a
per-arm scratch directory that owns its own ``results/`` before invoking the
upstream evaluator, so it is safe to run alongside another scoring job that uses
the repo-root ``results/``.

No new sampling: every FASTA already exists on disk.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.upstream_eval import run_lineageflow_upstream_eval  # noqa: E402

ARMS: tuple[tuple[str, str, str], ...] = (
    # (arm tag, run dir relative to repo, beta label)
    ("seed42_off", "verification_outputs/gap45-r1-blend-off-150/seed42_off", "0"),
    ("seed42_on", "verification_outputs/gap45-r1-blend-off-150/seed42_on", "1/6"),
    ("seed43_off", "verification_outputs/gap45-r1-blend-off-150/seed43_off", "0"),
    ("seed43_on", "verification_outputs/gap45-r1-blend-off-150/seed43_on", "1/6"),
    ("seed44_off", "verification_outputs/gap45-r1-blend-off-150/seed44_off", "0"),
    ("seed44_on", "verification_outputs/gap45-r1-blend-off-150/seed44_on", "1/6"),
    ("seed42_b1", "verification_outputs/gap45-r1-beta1-150/seed42", "1"),
    ("seed43_b1", "verification_outputs/gap45-r1-beta1-150/seed43", "1"),
    ("seed44_b1", "verification_outputs/gap45-r1-beta1-150/seed44", "1"),
)


def _score_one(fasta: Path, outdir: Path, scratch: Path, timeout_s: int) -> dict:
    """Score one FASTA inside an isolated scratch cwd. Returns the flat dict."""
    outdir.mkdir(parents=True, exist_ok=True)
    (scratch / "results").mkdir(parents=True, exist_ok=True)
    prev = Path.cwd()
    try:
        os.chdir(scratch)
        return run_lineageflow_upstream_eval(
            fasta_path=fasta,
            output_dir=outdir,
            metrics=("family_validity", "novelty"),
            timeout_s=int(timeout_s),
            length_bias="short",
        )
    finally:
        os.chdir(prev)


def _summary(outdir: Path) -> dict:
    p = outdir / "summary.json"
    return json.loads(p.read_text()) if p.exists() else {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path,
                    default=_REPO_ROOT / "verification_outputs" / "gap60-tradeoff")
    ap.add_argument("--timeout-s", type=int, default=5400)
    ap.add_argument("--force", action="store_true",
                    help="re-score even when a summary.json already exists")
    args = ap.parse_args(argv)

    root = Path(args.out)
    scratch_root = root / "_scratch"
    scratch_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for tag, rel, beta in ARMS:
        run_dir = _REPO_ROOT / rel
        for side in ("baseline", "framework"):
            fasta = run_dir / f"{side}.fasta"
            if not fasta.exists():
                print(f"[gap60] MISSING {fasta}", flush=True)
                continue
            outdir = root / tag / side
            done = (outdir / "summary.json").exists()
            if done and not args.force:
                print(f"[gap60] skip {tag}/{side} (cached)", flush=True)
            else:
                t0 = time.perf_counter()
                _score_one(fasta, outdir, scratch_root / f"{tag}_{side}",
                           int(args.timeout_s))
                print(f"[gap60] {tag}/{side} in {time.perf_counter() - t0:.1f}s",
                      flush=True)
            s = _summary(outdir)
            fv = s.get("family_validity", {})
            nv = s.get("novelty", {})
            wg = nv.get("within_gen_clusters", {}).get("thresholds", {}).get("0.9", {})
            rows.append({
                "arm": tag,
                "beta": beta,
                "seed": tag.split("_")[0].replace("seed", ""),
                "side": side,
                "hits": fv.get("hmmscan_total_hits"),
                "n_records": fv.get("n_total") or nv.get("n_total"),
                "n_clusters_0p9": wg.get("n_clusters"),
                "singleton_frac_0p9": wg.get("singleton_fraction_sequences"),
                "novelty_hits_kept": nv.get("hits", {}).get("hits_kept"),
                "novelty_all_0p5": nv.get("novelty_all", {}).get("0.5"),
            })

    print()
    print("| arm | beta | side | hits | clusters@0.9 | singleton frac | novelty hits |")
    print("|---|---:|---|---:|---:|---:|---:|")
    for r in rows:
        print(f"| {r['arm']} | {r['beta']} | {r['side']} | {r['hits']} | "
              f"{r['n_clusters_0p9']} | {r['singleton_frac_0p9']} | "
              f"{r['novelty_hits_kept']} |")

    by_arm: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_arm.setdefault(r["arm"], {})[r["side"]] = r
    print()
    print("| arm | beta | hits base -> fw | clusters base -> fw | collapse? |")
    print("|---|---:|---|---:|:--:|")
    for tag, _rel, beta in ARMS:
        pair = by_arm.get(tag, {})
        if "baseline" not in pair or "framework" not in pair:
            continue
        b, f = pair["baseline"], pair["framework"]
        collapsed = (f["n_clusters_0p9"] is not None
                     and b["n_clusters_0p9"] is not None
                     and f["n_clusters_0p9"] < 0.9 * b["n_clusters_0p9"])
        print(f"| {tag} | {beta} | {b['hits']} -> {f['hits']} | "
              f"{b['n_clusters_0p9']} -> {f['n_clusters_0p9']} | "
              f"{'YES' if collapsed else 'no'} |")

    (root / "tradeoff.json").write_text(json.dumps({"rows": rows}, indent=1))
    print(f"\nwrote {root / 'tradeoff.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
