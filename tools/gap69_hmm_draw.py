#!/usr/bin/env python3
"""GAP-69 arm D — pure Pfam-profile draw, no model (CPU ceiling reference).

Answers one question: **what does sampling directly from the assigned family's
match-emission profile score on the same metric?** If this matches or beats the
model arms, the model is not contributing anything the profile does not.

The per-record ``(family_id, length)`` stream is replayed exactly as
:func:`tools.gen_lineageflow_n1000_fastas._write_framework_arm` builds it
(``random.Random(seed ^ 0x5A5A)``, family = ``family_ids[i % len]``), so the
arm is record-paired with the model arms.

Not a paired arm in the statistical sense: it decodes by *categorical sampling*
where the model arms decode by ``argmax`` after the ODE. Declared as
limitation L5 in ``docs/audit/gap69-lineageflow-profile.md`` §0.5.

Usage
-----
    python3 tools/gap69_hmm_draw.py \
        --profiles verification_outputs/gap69-lineageflow-profile/profiles.json \
        --out verification_outputs/gap69-lineageflow-profile/seed42/hmm_draw.fasta \
        --n 1000 --seed 42 --min-len 30 --max-len 150
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profiles", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-len", type=int, default=30)
    ap.add_argument("--max-len", type=int, default=150)
    args = ap.parse_args(argv)

    from tools.gen_lineageflow_n1000_fastas import FAMILY_PROFILES

    fam_ids = list(FAMILY_PROFILES.keys())
    prof = json.loads(Path(args.profiles).read_text())
    aa_order = prof["aa_order"]
    span = int(prof["span"])
    if int(args.max_len) > span:
        raise SystemExit(f"max_len_exceeds_profile_span:{args.max_len}>{span}")

    # Pre-normalise each family's per-position probability rows once. The
    # profile JSON is keyed by the stable ``PF`` number while FAMILY_PROFILES
    # uses versioned accessions (``PF00005.27``); match on the prefix and keep
    # the versioned key for the FASTA header (record-pairing with the model
    # arms). Profile version drift is limitation L2 in the audit.
    by_pf = {str(k).split(".")[0]: v for k, v in prof["families"].items()}
    probs: dict[str, np.ndarray] = {}
    for fid in fam_ids:
        pf = str(fid).split(".")[0]
        if pf not in by_pf:
            raise SystemExit(f"missing_profile_for:{fid}")
        logp = np.asarray(by_pf[pf]["logp"], dtype=np.float64)
        p = np.exp(logp)
        probs[fid] = p / p.sum(axis=-1, keepdims=True)

    rng = random.Random(int(args.seed) ^ 0x5A5A)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    n_written = 0
    with args.out.open("w") as fh:
        for i in range(int(args.n)):
            family_id = fam_ids[i % len(fam_ids)]
            length = rng.randint(int(args.min_len), int(args.max_len))
            p = probs[family_id][:length]
            draw_rng = np.random.default_rng(int(args.seed) + int(i))
            idx = (draw_rng.random(length)[:, None] >
                   np.cumsum(p, axis=-1)).sum(axis=-1)
            idx = np.clip(idx, 0, p.shape[-1] - 1)
            seq = "".join(aa_order[int(k)] for k in idx)
            fh.write(f">framework_seed{i}|family={family_id}\n{seq}\n")
            n_written += 1
    print(f"[gap69-hmm-draw] wrote {n_written} records -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
