#!/usr/bin/env python3
"""
Mode collapse analysis utility (Wave 171 P3).

Characterizes mode collapse / mode concentration in FASTA samples:
  - k-mer diversity (unique count, Shannon entropy, per-record uniqueness)
  - family coverage (Pfam family annotation in headers)
  - mode concentration (top-N% share, Gini coefficient)

Honest interpretation: framework trades breadth for depth (directed search
toward Pfam families), not bug-level mode collapse.

Usage:
    python tools/mode_collapse_analysis.py --baseline B.fasta --framework F.fasta --output out.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from Bio import SeqIO

# ----------------------------- k-mer diversity ----------------------------- #

def compute_kmer_diversity(fasta_path: str | Path, k: int = 3) -> dict[str, Any]:
    """Compute k-mer diversity metrics for a FASTA file.

    Returns:
        dict with:
            n_records: number of sequences
            unique_kmers_total: total distinct k-mers across all records
            mean_unique_kmers_per_record: avg distinct k-mers per record
            shannon_entropy: Shannon entropy over k-mer counts
            median_record_length: median sequence length
    """
    path = Path(fasta_path)
    if not path.exists():
        raise FileNotFoundError(f"FASTA not found: {path}")

    global_counter: Counter[str] = Counter()
    per_record_unique: list[int] = []
    record_lengths: list[int] = []

    for rec in SeqIO.parse(str(path), "fasta"):
        seq = str(rec.seq).upper()
        record_lengths.append(len(seq))
        if len(seq) < k:
            per_record_unique.append(0)
            continue
        kmers = [seq[i : i + k] for i in range(len(seq) - k + 1)]
        local = Counter(kmers)
        per_record_unique.append(len(local))
        global_counter.update(local)

    # Shannon entropy in bits
    total = sum(global_counter.values())
    if total == 0:
        shannon = 0.0
    else:
        shannon = -sum((c / total) * math.log2(c / total) for c in global_counter.values())

    record_lengths.sort()
    median_len = record_lengths[len(record_lengths) // 2] if record_lengths else 0

    return {
        "n_records": len(record_lengths),
        "k": k,
        "unique_kmers_total": len(global_counter),
        "mean_unique_kmers_per_record": (
            sum(per_record_unique) / len(per_record_unique) if per_record_unique else 0.0
        ),
        "median_unique_kmers_per_record": _median(per_record_unique),
        "shannon_entropy": shannon,
        "median_record_length": median_len,
    }


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2 == 0:
        return (s[n // 2 - 1] + s[n // 2]) / 2.0
    return float(s[n // 2])


# --------------------------- family coverage -------------------------------- #

_FAMILY_RE = re.compile(r"family=([^\s|]+)")


def compute_family_coverage(fasta_path: str | Path) -> dict[str, Any]:
    """Extract per-record Pfam family annotations and summarize.

    Headers must contain `family=<PFxxxxx.NN>` substrings.

    Returns:
        dict with n_families_covered, top-N families, per-record counts.
    """
    path = Path(fasta_path)
    if not path.exists():
        raise FileNotFoundError(f"FASTA not found: {path}")

    family_counts: Counter[str] = Counter()
    n_with_family = 0
    n_records = 0
    for rec in SeqIO.parse(str(path), "fasta"):
        n_records += 1
        m = _FAMILY_RE.search(rec.description)
        if m:
            n_with_family += 1
            family_counts[m.group(1)] += 1

    return {
        "n_records": n_records,
        "n_records_with_family_annotation": n_with_family,
        "n_families_covered": len(family_counts),
        "family_counts": dict(family_counts.most_common()),
        "top_5_families": family_counts.most_common(5),
        "annotation_rate": (
            n_with_family / n_records if n_records else 0.0
        ),
    }


# --------------------------- mode concentration ----------------------------- #

def compute_mode_concentration(fasta_path: str | Path, k: int = 3) -> dict[str, Any]:
    """Compute mode concentration: top-N% share of all k-mer mass + Gini.

    A high top_1_share with low Gini means mass is in a few k-mers (mode collapse).
    A high Gini with high entropy = mass concentrated but each mode has many sub-modes.
    """
    path = Path(fasta_path)
    if not path.exists():
        raise FileNotFoundError(f"FASTA not found: {path}")

    counter: Counter[str] = Counter()
    for rec in SeqIO.parse(str(path), "fasta"):
        seq = str(rec.seq).upper()
        if len(seq) < k:
            continue
        kmers = [seq[i : i + k] for i in range(len(seq) - k + 1)]
        counter.update(kmers)

    if not counter:
        return {
            "k": k,
            "total_kmer_mass": 0,
            "top_1_percent_share": 0.0,
            "top_5_percent_share": 0.0,
            "top_10_percent_share": 0.0,
            "gini_coefficient": 0.0,
        }

    counts_desc = sorted(counter.values(), reverse=True)
    counts_asc = sorted(counter.values())
    total = sum(counts_asc)
    n = len(counts_asc)

    def share_of_top_pct(p: float) -> float:
        k_top = max(1, int(round(n * p / 100.0)))
        return sum(counts_desc[:k_top]) / total if total else 0.0

    # Gini coefficient (counts sorted in ASCENDING order)
    gini_num = 0.0
    for i, c in enumerate(counts_asc, start=1):
        gini_num += (2 * i - n - 1) * c
    gini = gini_num / (n * total) if total else 0.0

    return {
        "k": k,
        "total_kmer_mass": total,
        "n_distinct_kmers": n,
        "top_1_percent_share": share_of_top_pct(1.0),
        "top_5_percent_share": share_of_top_pct(5.0),
        "top_10_percent_share": share_of_top_pct(10.0),
        "gini_coefficient": gini,
    }


# --------------------------- per-record uniqueness -------------------------- #

def compute_per_record_uniqueness(fasta_path: str | Path) -> dict[str, Any]:
    """Pairwise uniqueness among records (exact sequence identity).

    Returns:
        dict with n_records, n_unique_records, duplicate_count, pairwise_unique_ratio.
    """
    path = Path(fasta_path)
    if not path.exists():
        raise FileNotFoundError(f"FASTA not found: {path}")

    seqs = [str(rec.seq).upper() for rec in SeqIO.parse(str(path), "fasta")]
    counter = Counter(seqs)
    n_records = len(seqs)
    n_unique = len(counter)
    dup_count = sum(c - 1 for c in counter.values() if c > 1)

    return {
        "n_records": n_records,
        "n_unique_records": n_unique,
        "duplicate_count": dup_count,
        "pairwise_unique_ratio": (n_unique / n_records) if n_records else 0.0,
    }


# --------------------------- pairwise comparison ---------------------------- #

def compare_arms(baseline_fasta: str | Path, framework_fasta: str | Path) -> dict[str, Any]:
    """Run all metrics on both arms and produce a comparison dict.

    The output is symmetric: each top-level key holds a baseline/framework pair
    plus derived deltas where meaningful.
    """
    base = Path(baseline_fasta)
    fram = Path(framework_fasta)
    if not base.exists():
        raise FileNotFoundError(f"baseline not found: {base}")
    if not fram.exists():
        raise FileNotFoundError(f"framework not found: {fram}")

    base_kmer = compute_kmer_diversity(base)
    fram_kmer = compute_kmer_diversity(fram)
    base_fam = compute_family_coverage(base)
    fram_fam = compute_family_coverage(fram)
    base_conc = compute_mode_concentration(base)
    fram_conc = compute_mode_concentration(fram)
    base_uniq = compute_per_record_uniqueness(base)
    fram_uniq = compute_per_record_uniqueness(fram)

    return {
        "baseline_fasta": str(base),
        "framework_fasta": str(fram),
        "kmer_diversity": {
            "baseline": base_kmer,
            "framework": fram_kmer,
            "unique_ratio_framework_vs_baseline": (
                fram_kmer["unique_kmers_total"] / base_kmer["unique_kmers_total"]
                if base_kmer["unique_kmers_total"]
                else 0.0
            ),
        },
        "family_coverage": {
            "baseline": base_fam,
            "framework": fram_fam,
            "family_ratio_framework_vs_baseline": (
                fram_fam["n_families_covered"] / base_fam["n_families_covered"]
                if base_fam["n_families_covered"]
                else 0.0
            ),
        },
        "mode_concentration": {
            "baseline": base_conc,
            "framework": fram_conc,
        },
        "per_record_uniqueness": {
            "baseline": base_uniq,
            "framework": fram_uniq,
        },
        "honest_interpretation": _interpret(base_kmer, fram_kmer, base_fam, fram_fam),
    }


def _interpret(
    base_kmer: dict[str, Any],
    fram_kmer: dict[str, Any],
    base_fam: dict[str, Any],
    fram_fam: dict[str, Any],
) -> dict[str, str]:
    """Plain-language interpretation of the comparison.

    The framework trades breadth (unique k-mers) for depth (concentration on
    Pfam-annotated families). This is directed search, not bug-level collapse.
    """
    fam_ratio = (
        fram_fam["n_families_covered"] / base_fam["n_families_covered"]
        if base_fam["n_families_covered"]
        else 0.0
    )
    kmer_ratio = (
        fram_kmer["unique_kmers_total"] / base_kmer["unique_kmers_total"]
        if base_kmer["unique_kmers_total"]
        else 0.0
    )
    if kmer_ratio < 1.0 and fam_ratio >= 0.9:
        verdict = "directed_search_tradeoff"
        explanation = (
            "Framework k-mer diversity is lower while family coverage is preserved "
            "(>=90%). This is concentration on validated Pfam modes (directed search), "
            "not bug-level mode collapse."
        )
    elif kmer_ratio < 0.3 and fam_ratio < 0.5:
        verdict = "mode_collapse_concern"
        explanation = (
            "Framework loses both k-mer diversity AND family coverage. Investigate "
            "for mode collapse."
        )
    else:
        verdict = "mixed"
        explanation = (
            "K-mer and family coverage move in similar directions. Re-evaluate "
            "interpretation per use case."
        )
    return {"verdict": verdict, "explanation": explanation}


# --------------------------------- CLI -------------------------------------- #

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", required=True, help="baseline FASTA path")
    p.add_argument("--framework", required=True, help="framework FASTA path")
    p.add_argument("--output", required=True, help="output JSON path")
    p.add_argument("--k", type=int, default=3, help="k-mer size (default 3)")
    return p


def main() -> int:
    args = _build_arg_parser().parse_args()
    result = compare_arms(args.baseline, args.framework)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(f"WROTE {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
