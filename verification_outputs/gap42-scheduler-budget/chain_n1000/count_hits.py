"""GAP-40 bounded A/B hit counter — hmmscan total + per-record hits.

Protocol mirrors the canonical R1 counter:
    hmmscan --noali --cpu 32 --tblout <out> --acc Pfam-A.hmm <fasta>
    hits = non-comment tblout lines.
"""
from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path

HMMSCAN = "/home/hugo/hmmer_build/bin/hmmscan"
PFAM = (
    "/home/hugo/codes/flowa-multistep-reinference/"
    "data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm"
)


def scan(fasta: Path, tblout: Path) -> None:
    cmd = [
        HMMSCAN, "--noali", "--cpu", "32",
        "--tblout", str(tblout), "--acc", PFAM, str(fasta),
    ]
    with tblout.open("w") as fh:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=fh, check=True)


def count(tblout: Path) -> tuple[int, Counter]:
    total = 0
    per_record: Counter = Counter()
    for line in tblout.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        # tblout columns: target acc name tlen query acc name qlen ...
        parts = line.split()
        qname = parts[2]
        total += 1
        per_record[qname] += 1
    return total, per_record


def main() -> int:
    for arg in sys.argv[1:]:
        fasta = Path(arg)
        tblout = fasta.with_suffix(".tblout")
        scan(fasta, tblout)
        total, per_record = count(tblout)
        n_records = sum(
            1 for ln in fasta.read_text().splitlines() if ln.startswith(">")
        )
        n_with_hits = len(per_record)
        print(
            f"{fasta.parent.name}/{fasta.name}: total_hits={total} "
            f"records={n_records} records_with_hits={n_with_hits} "
            f"hits_per_record={total / max(n_records, 1):.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
