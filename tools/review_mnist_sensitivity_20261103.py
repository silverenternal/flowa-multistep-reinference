#!/usr/bin/env python3
"""Aggregate existing production-checkpoint sensitivity runs; no sampling.

Intervals describe three generating seeds. Missing beta/budget cells stay absent.
Legacy beta_framework and sweep_command are not treated as effective provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from statistics import mean, stdev

T975_DF2 = 4.302652729749464
ARMS = ("cosine", "codimension_sheet", "evidence_driven")


def aggregate(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        groups.setdefault(
            (row["axis"], row["beta_total"], row["rounds"], row["steps"], row["arm"]), []
        ).append(row)
    result = []
    for key, cells in sorted(groups.items()):
        if sorted(c["seed_label"] for c in cells) != [42, 43, 44]:
            raise ValueError("each group must have exactly seed labels 42/43/44")
        if len({c["protocol"] for c in cells}) != 1:
            raise ValueError("mixed protocols within seed group")
        differences = [c["framework"] - c["baseline"] for c in cells]
        if not all(math.isfinite(x) for x in differences):
            raise ValueError("non-finite result")
        delta = mean(differences)
        half = T975_DF2 * stdev(differences) / math.sqrt(3)
        result.append(
            {
                "axis": key[0],
                "beta_total": key[1],
                "rounds": key[2],
                "integration_steps": key[3],
                "velocity_calls": 4 * key[3],
                "arm": key[4],
                "n_generating_seeds": 3,
                "delta": delta,
                "seed_delta": differences,
                "ci95_seed_t": [delta - half, delta + half],
                "baseline_mean": mean(c["baseline"] for c in cells),
                "framework_mean": mean(c["framework"] for c in cells),
                "source_paths": [c["source"] for c in cells],
            }
        )
    return result


def collect(repo: Path) -> tuple[list[dict], list[dict]]:
    roots = [
        ("beta", repo / "verification_outputs/gap93-beta-dose"),
        ("rounds", repo / "verification_outputs/gap84c-round-dose"),
    ]
    rows, sources = [], []
    for axis, root in roots:
        for p in sorted(root.rglob("sweep_summary.json")):
            raw = p.read_bytes()
            b = json.loads(raw)
            label = re.fullmatch(r"production_nfe(\d+)(?:_r(\d+))?_s(\d+)", p.parent.name)
            if label is None:
                raise ValueError(f"unrecognized cell label: {p}")
            steps, rounds, seed = int(label[1]), int(b["n_rounds"]), int(label[3])
            if steps != b["nfe"] or (label[2] and rounds != int(label[2])):
                raise ValueError(f"label/summary mismatch: {p}")
            if b["n_records"] != 1000 or not b["mean_preserve"] or b["restart_t0_mode"] != "memory":
                raise ValueError(f"unexpected configuration: {p}")
            beta = float(b["beta_total"])
            expected = 1 - (1 - beta) ** (1 / (rounds - 1))
            if not all(abs(float(x) - expected) < 1e-12 for x in b["beta_per_round"]):
                raise ValueError(f"effective beta inconsistent: {p}")
            relative = str(p.relative_to(repo))
            protocol = (
                b["checkpoint_sha256"],
                b["n_records"],
                b["fid_metric"],
                b["mean_preserve"],
                b["restart_t0_mode"],
            )
            sources.append(
                {
                    "path": relative,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "seed_provenance": "directory label plus jobs.txt; summary has no seed field",
                    "legacy_beta_framework": b.get("beta_framework"),
                    "effective_beta_total": beta,
                    "checkpoint_sha256": b["checkpoint_sha256"],
                }
            )
            for arm in ARMS:
                value = b["framework_arms"][arm]
                parts = value["per_round_num_steps"]
                if len(parts) != rounds or sum(parts) != steps or min(parts) < 1:
                    raise ValueError(f"invalid step allocation: {p}/{arm}")
                rows.append(
                    {
                        "axis": axis,
                        "beta_total": beta,
                        "rounds": rounds,
                        "steps": steps,
                        "arm": arm,
                        "seed_label": seed,
                        "baseline": float(b["baseline_fid"]),
                        "framework": float(value["fid_headline"]),
                        "protocol": protocol,
                        "source": relative,
                    }
                )
    return rows, sources


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows, sources = collect(args.repo)
    plateau_rows = []
    for beta in [0.15, 0.70]:
        for seed in [42, 43, 44]:
            for arm in ARMS:
                cells = [
                    r
                    for r in rows
                    if r["axis"] == "beta"
                    and r["beta_total"] == beta
                    and r["seed_label"] == seed
                    and r["arm"] == arm
                    and r["steps"] in [100, 200]
                ]
                if sorted(r["steps"] for r in cells) != [100, 200]:
                    raise ValueError("missing plateau rung")
                plateau_rows.append(
                    {
                        **cells[0],
                        "axis": "beta_plateau",
                        "steps": 0,
                        "baseline": mean(r["baseline"] for r in cells),
                        "framework": mean(r["framework"] for r in cells),
                        "source": [r["source"] for r in cells],
                    }
                )
    plateau = aggregate(plateau_rows)
    for row in plateau:
        row.pop("integration_steps")
        row.pop("velocity_calls")
        row["integration_step_grid"] = [100, 200]
        row["velocity_call_grid"] = [400, 800]
    result = {
        "plateau_groups": plateau,
        "groups": aggregate(rows),
        "sources": sources,
        "scope": "Existing production checkpoint only. Seed-label aggregation; "
        "unadjusted exploratory intervals. Beta .5 plateau unmeasured. "
        "Per-round allocation permits one step; cap parameter 2 limits average budget only. "
        "Raw samples/checkpoints and executed historical source revision not revalidated.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"{len(sources)} summaries; {len(result['groups'])} seed-level groups")
    for row in result["groups"]:
        if row["arm"] == "evidence_driven":
            print(
                row["axis"],
                row["beta_total"],
                row["rounds"],
                row["integration_steps"],
                round(row["delta"], 6),
                [round(x, 6) for x in row["ci95_seed_t"]],
            )


if __name__ == "__main__":
    main()
