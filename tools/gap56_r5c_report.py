"""GAP-56: consolidate the R5c mechanism screen into one markdown table.

Reads ``<run-dir>/sweep_summary.json`` (always) and
``<run-dir>/paired_bootstrap.json`` (when present) for every config listed on
the command line and prints a markdown table using the **headline** FID
(full 10k reference) as the point estimate and the paired record-level
bootstrap as the interval.

The chunk-level estimator emitted by the sweep driver is reported only as a
diagnostic column, because a 20-image reference chunk biases the Fréchet
distance in an arm-dependent way and can flip the sign of the delta.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CONFIGS: tuple[tuple[str, str], ...] = (
    ("legacy_const", "legacy (beta const 0.5, t0=0)"),
    ("eqbeta_zero", "equal_budget, t0=0"),
    ("sched_eq", "equal_budget, t0=memory, sched alloc"),
    ("prop_eq", "equal_budget, t0=memory, proportional alloc"),
    ("const_mem", "beta const 0.5, t0=memory"),
    ("betacurve_0.1", "equal_budget beta=0.10, t0=0"),
    ("betacurve_0.2", "equal_budget beta=0.20, t0=0"),
    ("betacurve_0.35", "equal_budget beta=0.35, t0=0"),
)

ARMS = ("cosine", "codimension_sheet", "evidence_driven")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("verification_outputs/gap56-r5c-memory-t0"))
    args = ap.parse_args(argv)

    print("| config | baseline FID | arm | FID | delta | delta% | 95% CI | p (Bonf) | sig |")
    print("|---|---:|---|---:|---:|---:|---|---:|:--:|")
    for name, label in CONFIGS:
        run = Path(args.root) / name
        summary = run / "sweep_summary.json"
        if not summary.exists():
            print(f"| {label} | — | — | — | — | — | — | — | pending |")
            continue
        d = json.loads(summary.read_text())
        boot_path = run / "paired_bootstrap.json"
        boot = json.loads(boot_path.read_text()) if boot_path.exists() else None
        for arm in ARMS:
            a = d["framework_arms"][arm]
            if boot is None:
                print(f"| {label} | {d['baseline_fid']:.4f} | {arm} | "
                      f"{a['fid_headline']:.4f} | — | "
                      f"{(a['fid_headline']/d['baseline_fid']-1)*100:+.2f} | — | — | no CI |")
                continue
            b = boot["arms"][arm]
            ci = f"[{b['delta_ci95'][0]:+.4f}, {b['delta_ci95'][1]:+.4f}]"
            print(f"| {label} | {b['fid_baseline']:.4f} | {arm} | {b['fid_arm']:.4f} | "
                  f"{b['delta']:+.4f} | {b['delta_pct']:+.2f} | {ci} | "
                  f"{b['p_bonferroni']:.2e} | {'YES' if b['bonferroni_significant'] else 'no'} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
