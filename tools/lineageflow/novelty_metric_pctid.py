#!/usr/bin/env python3
"""Percent-identity-based novelty metric for mmseqs2 m8 hits.

The standard mmseqs2 ``easy-search`` m8 format has the following columns:
  1: query
  2: target
  3: sequence identity (fident, fraction 0-1)
  4: alignment length
  5: mismatches
  6: gap opens
  7: query start
  8: query end
  9: target start
 10: target end
 11: e-value
 12: bit score

A query is "novel" if it has no hit OR its best hit has percent identity
below the twilight-zone threshold (default 30%). The 30% cutoff is the
standard biology threshold for homology detection (Rost 1999, Pearson 2013).

Usage:
    python novelty_metric_pctid.py <m8> [pctid_threshold] [n_total]
"""

from __future__ import annotations

import json
import sys


def parse_m8_max_pctid(path: str) -> dict[str, float]:
    """Return {qid: max_pctid} across all hits in m8 (pctid in 0-100 scale)."""
    seq_best_pctid: dict[str, float] = {}
    try:
        with open(path) as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) < 12:
                    continue
                qid = parts[0]
                pctid = float(parts[2]) * 100.0  # column 3 = fident fraction -> pct
                if qid not in seq_best_pctid or pctid > seq_best_pctid[qid]:
                    seq_best_pctid[qid] = pctid
    except FileNotFoundError:
        return {}
    return seq_best_pctid


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: novelty_metric_pctid.py <m8> [pctid_threshold] [n_total]", file=sys.stderr)
        sys.exit(2)
    path = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
    n_total = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    d = parse_m8_max_pctid(path)
    n_with_hits = len(d)
    n_novel = sum(1 for q, p in d.items() if p < threshold)
    n_homolog = n_with_hits - n_novel
    # No-hit queries are counted as novel at the denominator (n_total) level.
    n_nohit = max(n_total - n_with_hits, 0)
    n_novel_total = n_novel + n_nohit
    mean_max_pctid = sum(d.values()) / max(n_with_hits, 1)
    result = {
        "m8_path": path,
        "pctid_threshold": threshold,
        "n_total": n_total,
        "n_with_hits": n_with_hits,
        "n_homolog_pctid_gte_threshold": n_homolog,
        "n_novel_pctid_lt_threshold": n_novel,
        "n_novel_via_no_hit": n_nohit,
        "n_novel_total": n_novel_total,
        "novel_rate_pctid": float(n_novel_total / n_total) if n_total > 0 else None,
        "mean_max_pctid": mean_max_pctid,
        "per_query_max_pctid": {q: round(p, 2) for q, p in sorted(d.items())},
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
