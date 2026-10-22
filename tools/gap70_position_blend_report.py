#!/usr/bin/env python3
"""GAP-70 — three-arm report for the position-selective restart blend.

Pre-registration: ``docs/audit/gap70-lineageflow-position-blend.md`` §0.

Arms
----
``A`` baseline (no restart), ``B`` scalar blend (K7's framework arm),
``C`` position-selective blend (``m_vec = m * w``, ``w = 1 - c``).

Both readouts are **per-record binary**, so the comparison is paired at the
record index (the generator emits every arm from one record loop):

* novelty — ``pctid < 30 %`` against the canonical Pfam-A target DB, or no hit
  at all. Read from ``mmseqs easy-search`` m8 files. The generator's own
  ``novelty`` metric is **not** usable here: it searches the 200-sequence
  ``pfam35/pfam_holdout_targetDB`` and saturates at 1.0 (the W280 artefact).
* validity — ``has_any_hit`` from the upstream ``family_validity_per_seq.jsonl``
  (hmmscan against Pfam-A; this one is valid).

Outputs the paired risk difference with a Newcombe 95 % CI, the exact McNemar
p-value and the paired t, plus the §0.4 rules and a single verdict.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from tools.gap48_k7_two_arm_novelty import (
    _mcnemar_exact,
    _newcombe_paired,
    _paired_t,
)

PCTID_THRESHOLD = 30.0
VALIDITY_DROP_TOLERANCE = 0.02  # 2 percentage points, §0.4 rule 1
NOVELTY_RATIO_CEILING = 2.0  # §0.4 rule 2

_QID_RE = re.compile(r"^(?:baseline|framework)_seed(\d+)\|family=(\S+)$")


def _qid(prefix: str, idx: int, fam: str) -> str:
    return f"{prefix}_seed{idx}|family={fam}"


def _load_best_pctid(m8_path: Path) -> dict[str, float]:
    """``{qid: best pctid in 0-100}``; absent qid == no hit."""
    best: dict[str, float] = {}
    with m8_path.open() as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 12:
                continue
            qid = parts[0]
            pct = float(parts[2]) * 100.0
            if qid not in best or pct > best[qid]:
                best[qid] = pct
    return best


def _load_has_any_hit(jsonl_path: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    with jsonl_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            header = str(row.get("header", ""))
            if not header:
                continue
            out[header] = bool(row.get("has_any_hit", False))
    return out


def _load_families(fasta_path: Path, arm: str) -> dict[int, str]:
    """``{record_index: family}`` from ``arm_seed<I>|family=<F>`` headers."""
    out: dict[int, str] = {}
    bad: list[str] = []
    with fasta_path.open() as fh:
        for line in fh:
            if not line.startswith(">"):
                continue
            qid = line[1:].strip().split()[0]
            m = _QID_RE.match(qid)
            if m is None:
                bad.append(qid)
                continue
            idx = int(m.group(1))
            if idx in out:
                raise ValueError(f"{arm}: duplicate record index {idx}")
            out[idx] = m.group(2)
    if bad:
        raise ValueError(
            f"{arm}: {len(bad)} headers do not match "
            f"'{{arm}}_seed<I>|family=<F>', e.g. {bad[:3]}"
        )
    return out


def _index(values: dict[str, float | bool], arm: str) -> dict[int, tuple[str, float]]:
    """``{record_index: (family, float(value))}`` from ``arm_seed<I>|family=F``."""
    out: dict[int, tuple[str, float]] = {}
    bad: list[str] = []
    for key, value in values.items():
        m = _QID_RE.match(key)
        if m is None:
            bad.append(key)
            continue
        idx = int(m.group(1))
        if idx in out:
            raise ValueError(f"{arm}: duplicate record index {idx}")
        out[idx] = (m.group(2), float(value))
    if bad:
        raise ValueError(
            f"{arm}: {len(bad)} headers do not match "
            f"'{{arm}}_seed<I>|family=<F>', e.g. {bad[:3]}"
        )
    return out


def _align(arms: dict[str, dict[int, tuple[str, float]]]) -> list[int]:
    """Record indices present in every arm, asserting the family matches."""
    names = list(arms)
    common = set.intersection(*(set(a) for a in arms.values()))
    for idx in sorted(common):
        fam = arms[names[0]][idx][0]
        for name in names[1:]:
            if arms[name][idx][0] != fam:
                raise ValueError(
                    f"record {idx}: family mismatch {names[0]}={fam} vs "
                    f"{name}={arms[name][idx][0]} — arms are not paired"
                )
    return sorted(common)


def _paired(
    left: dict[int, tuple[str, float]],
    right: dict[int, tuple[str, float]],
    idx: list[int],
) -> dict[str, Any]:
    """Paired binary comparison ``right - left`` over ``idx``."""
    a = b = c = d = 0
    deltas: list[float] = []
    for i in idx:
        x = int(right[i][1] > 0.5)
        y = int(left[i][1] > 0.5)
        if x and y:
            a += 1
        elif x and not y:
            b += 1
        elif y and not x:
            c += 1
        else:
            d += 1
        deltas.append(float(x - y))
    delta, lower, upper, phi, _ = _newcombe_paired(a, b, c, d)
    return {
        "n": len(idx),
        "both": a,
        "right_only": b,
        "left_only": c,
        "neither": d,
        "rate_left": (a + c) / len(idx) if idx else None,
        "rate_right": (a + b) / len(idx) if idx else None,
        "delta": delta,
        "ci95": [lower, upper],
        "phi": phi,
        "mcnemar_p": _mcnemar_exact(b, c),
        "paired_t": _paired_t(deltas),
        "excludes_zero": bool(lower > 0.0 or upper < 0.0),
    }


def _arm_summary(
    arm: dict[int, tuple[str, float]], idx: list[int]
) -> dict[str, Any]:
    vals = [arm[i][1] for i in idx]
    n = len(vals)
    hits = sum(1 for v in vals if v > 0.5)
    return {
        "n": n,
        "n_positive": hits,
        "rate": hits / n if n else None,
        "pct": 100.0 * hits / n if n else None,
    }


def _verdict(
    validity: dict[str, Any],
    novelty: dict[str, Any],
    ratio_a_over_c: float | None,
) -> tuple[str, list[str]]:
    notes: list[str] = []
    validity_ok = (
        validity["delta"] >= -VALIDITY_DROP_TOLERANCE
        and validity["ci95"][0] >= -VALIDITY_DROP_TOLERANCE
    )
    if not validity_ok:
        notes.append(
            "rule 1 failed: validity drop exceeds the 2 pp tolerance "
            f"(delta={validity['delta']:+.4f}, CI {validity['ci95']})"
        )
    novelty_ok = ratio_a_over_c is not None and ratio_a_over_c <= NOVELTY_RATIO_CEILING
    if not novelty_ok:
        notes.append(
            f"rule 2 failed: N_A/N_C={ratio_a_over_c!r} > "
            f"{NOVELTY_RATIO_CEILING}"
        )
    not_the_lever = not novelty["excludes_zero"]
    if not_the_lever:
        notes.append(
            "rule 3: N_C - N_B is not distinguishable from zero "
            f"(CI {novelty['ci95']})"
        )

    if validity_ok and novelty_ok:
        return "POSITION_BLEND_SUPPORTED", notes
    if not validity_ok and novelty["excludes_zero"] and novelty["delta"] > 0.0:
        return "TRADE_NOT_WIN", notes
    if not_the_lever:
        return "NOT_THE_LEVER", notes
    return "INCONCLUSIVE", notes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-m8", type=Path, required=True)
    ap.add_argument("--control-m8", type=Path, required=True,
                    help="arm B — scalar blend (K7's framework arm)")
    ap.add_argument("--treatment-m8", type=Path, required=True,
                    help="arm C — position-selective blend")
    ap.add_argument("--baseline-fasta", type=Path, required=True,
                    help="arm A FASTA (record -> family map; no-hit = novel)")
    ap.add_argument("--control-fasta", type=Path, required=True)
    ap.add_argument("--treatment-fasta", type=Path, required=True)
    ap.add_argument("--baseline-validity", type=Path, required=True,
                    help="family_validity_per_seq.jsonl for arm A")
    ap.add_argument("--control-validity", type=Path, required=True)
    ap.add_argument("--treatment-validity", type=Path, required=True)
    ap.add_argument("--n-total", type=int, default=1000,
                    help="records per arm (no-hit records are absent from m8)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    def _novel(
        m8: Path, fasta: Path, arm: str, prefix: str
    ) -> dict[int, tuple[str, float]]:
        families = _load_families(fasta, arm)
        if len(families) != args.n_total:
            raise ValueError(
                f"{arm}: {len(families)} FASTA records != n_total={args.n_total}"
            )
        best = _load_best_pctid(m8)
        out: dict[int, tuple[str, float]] = {}
        for idx, fam in families.items():
            pct = best.get(_qid(prefix, idx, fam))
            # No hit at all counts as novel (the K7 definition).
            out[idx] = (fam, 1.0 if pct is None or pct < PCTID_THRESHOLD else 0.0)
        return out

    def _valid(jsonl: Path, arm: str) -> dict[int, tuple[str, float]]:
        return _index(_load_has_any_hit(jsonl), arm)

    novelty = {
        "A": _novel(args.baseline_m8, args.baseline_fasta, "A", "baseline"),
        "B": _novel(args.control_m8, args.control_fasta, "B", "framework"),
        "C": _novel(args.treatment_m8, args.treatment_fasta, "C", "framework"),
    }
    validity = {
        "A": _valid(args.baseline_validity, "A"),
        "B": _valid(args.control_validity, "B"),
        "C": _valid(args.treatment_validity, "C"),
    }

    nov_idx = _align(novelty)
    val_idx = _align(validity)

    nov_summary = {k: _arm_summary(v, nov_idx) for k, v in novelty.items()}
    val_summary = {k: _arm_summary(v, val_idx) for k, v in validity.items()}

    nov_cb = _paired(novelty["B"], novelty["C"], nov_idx)
    nov_ca = _paired(novelty["A"], novelty["C"], nov_idx)
    val_cb = _paired(validity["B"], validity["C"], val_idx)
    val_ba = _paired(validity["A"], validity["B"], val_idx)

    n_a = nov_summary["A"]["rate"]
    n_c = nov_summary["C"]["rate"]
    ratio = (n_a / n_c) if (n_a and n_c) else None

    verdict, notes = _verdict(val_cb, nov_cb, ratio)
    if verdict == "POSITION_BLEND_SUPPORTED":
        notes.append(
            "rule 4: a second seed is a replication, not a search — "
            f"this report is seed {args.seed} only"
        )

    payload = {
        "spec": "docs/audit/gap70-lineageflow-position-blend.md §0.4",
        "seed": args.seed,
        "n_total": args.n_total,
        "pctid_threshold": PCTID_THRESHOLD,
        "novelty": {
            "arms": nov_summary,
            "C_minus_B": nov_cb,
            "C_minus_A": nov_ca,
            "ratio_A_over_C": ratio,
        },
        "validity": {
            "arms": val_summary,
            "C_minus_B": val_cb,
            "B_minus_A": val_ba,
        },
        "rules": {
            "validity_drop_tolerance": VALIDITY_DROP_TOLERANCE,
            "novelty_ratio_ceiling": NOVELTY_RATIO_CEILING,
        },
        "verdict": verdict,
        "notes": notes,
        "inputs": {
            "baseline_m8": str(args.baseline_m8),
            "control_m8": str(args.control_m8),
            "treatment_m8": str(args.treatment_m8),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    print(json.dumps({k: payload[k] for k in ("verdict", "notes")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
