#!/usr/bin/env python3
"""Stream-parse Pfam-A.hmm into per-family match-emission profiles.

Why not ``hmmfetch``
--------------------
``hmmfetch`` needs an SSI index (``Pfam-A.hmm.ssi``). The vendored copy ships
only the *pressed binary* (``.h3f/.h3i/.h3m/.h3p``), and building the text
index would write into ``data/lineageflow_upstream/**`` — which must stay
byte-identical to upstream. So we stream the 2.2 GB ASCII file once and keep
only the families we need. Read-only, no index, no writes outside ``--out``.

What it extracts
----------------
For one family with model length ``M``:

* ``logp`` — ``(M, 20)`` match-emission **log**-probabilities. The ASCII HMM
  stores ``-ln p``, so ``logp = -value`` and ``exp(logp)`` rows sum to 1.
* ``cons`` — ``(M,)`` normalised information content
  ``IC_k / log2(20)`` with ``IC_k = log2(20) + sum_a p_ka log2 p_ka``.
  ``0`` = fully variable column, ``1`` = one residue at probability 1.

GAP-69 consumes these to build the conservation-weighted init
``softmax(c_i * log p_i + (1 - c_i) * randn(20))``; see
``docs/audit/gap69-lineageflow-profile.md`` §0.1.

Usage
-----
    python3 tools/pfam_profile.py \
        --pfam data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm \
        --families PF00005 PF00072 PF00183 PF02517 \
        --span 150 \
        --out verification_outputs/gap69-lineageflow-profile/profiles.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Pfam / HMMER amino-acid column order (matches ``AA_SET`` in
#: ``tools/gen_lineageflow_n1000_fastas.py``).
AA_ORDER: str = "ACDEFGHIKLMNPQRSTVWY"

#: Largest possible per-column information content (uniform background).
_MAX_IC: float = math.log2(len(AA_ORDER))


def _match_state_rows(block: list[str]) -> list[list[float]]:
    """Return the ``(M, 20)`` ``-ln p`` matrix from one HMM record's body.

    HMMER3 ASCII layout after the ``HMM`` header line::

        <column-name header line: "m->m  m->i  ...">
        <COMPO emissions, 20>
        <COMPO insert emissions, 20>
        <COMPO transitions, 7>
        <match 1, 20 + map/cons/rf/cs>
        <insert 1, 20>
        <transitions 1, 7>
        ...

    so the match rows start three lines after the ``COMPO`` line and repeat
    every three lines.
    """
    start = next(
        (i for i, ln in enumerate(block) if ln.strip().startswith("COMPO")), None
    )
    if start is None:
        return []
    rows: list[list[float]] = []
    for line in block[start + 3 :: 3]:
        parts = line.split()
        if not parts or not parts[0].isdigit():
            break
        vals = [float(v) for v in parts[1:21]]
        rows.append(vals)
    return rows


def parse_family(hmm_path: Path, pf_number: str) -> dict | None:
    """Stream ``hmm_path`` and return the first record whose ACC starts with
    ``pf_number + "."``. Returns ``None`` when the family is absent."""
    acc_prefix = f"{pf_number}."
    acc: str | None = None
    name: str | None = None
    leng: int | None = None
    block: list[str] | None = None
    # ``skip_until_end`` — we are inside a record we do not want; consume lines
    # until its terminating ``//`` without buffering them. Handled in the main
    # loop so we never mix ``fh.readline()`` with ``for line in fh``.
    skip_until_end = False

    with hmm_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if skip_until_end:
                if line.startswith("//"):
                    skip_until_end = False
                    acc = name = None
                    leng = None
                continue
            if block is not None:
                block.append(line)
                if line.startswith("//"):
                    if leng is None:
                        raise ValueError(f"missing_LENG:{acc}")
                    rows = _match_state_rows(block)
                    if len(rows) != int(leng):
                        raise ValueError(
                            f"match_state_count_mismatch:{acc}:"
                            f"{len(rows)}!={int(leng)}"
                        )
                    return {"acc": acc, "name": name, "leng": int(leng),
                            "neg_logp": rows}
                continue
            if line.startswith("NAME"):
                name = line.split(None, 1)[1].strip() if len(line.split(None, 1)) > 1 else ""
            elif line.startswith("ACC"):
                acc = line.split(None, 1)[1].strip() if len(line.split(None, 1)) > 1 else ""
            elif line.startswith("LENG"):
                leng = int(line.split()[1])
            elif line.startswith("HMM "):
                if acc is not None and acc.startswith(acc_prefix):
                    block = [line]
                else:
                    skip_until_end = True
                    leng = None
    return None


def conservation_and_logp(neg_logp: list[list[float]]) -> tuple[list[list[float]], list[float]]:
    """Convert ``-ln p`` rows to ``(logp, normalised_information_content)``."""
    logp: list[list[float]] = []
    cons: list[float] = []
    for row in neg_logp:
        lp = [-float(v) for v in row]
        # Guard against HMMER's ``*`` (probability 0) -> parsed as a huge value
        # would break exp(); clamp to a floor far below any real emission.
        lp = [max(v, -30.0) for v in lp]
        probs = [math.exp(v) for v in lp]
        total = sum(probs)
        if total <= 0.0:
            raise ValueError("degenerate_emission_row")
        probs = [p / total for p in probs]
        logp.append([math.log(p) for p in probs])
        ic = _MAX_IC + sum(p * math.log2(p) for p in probs if p > 0.0)
        cons.append(max(0.0, min(1.0, ic / _MAX_IC)))
    return logp, cons


def resample(profile: list, span: int) -> list:
    """Nearest-neighbour resample a length-``M`` profile onto ``span`` slots.

    Slot ``i`` maps to column ``round(i * (M - 1) / (span - 1))``. This is the
    positional (N-terminal, colinear) correspondence declared as limitation L1
    in the GAP-69 pre-registration.

    ``span <= 0`` means **native**: the profile keeps its own ``M`` columns.
    That matters when the profile is a *target* rather than a *prior*: the
    resample duplicates columns whenever ``M < span`` (and drops them when
    ``M > span``), so the argmax of a resampled profile is a stretched or
    gappy sequence that the family's own HMM does not recognise. GAP-79
    measured that directly — see ``docs/audit/gap79-r1-family-lever.md`` §3.8.
    """
    m = len(profile)
    if m == 0:
        raise ValueError("empty_profile")
    if span <= 0:
        return list(profile)
    if span == 1:
        return [profile[0]]
    return [profile[round(i * (m - 1) / (span - 1))] for i in range(span)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--pfam",
        type=Path,
        default=REPO_ROOT / "data" / "lineageflow_upstream" / "databases"
        / "pfam35" / "Pfam-A.hmm",
    )
    ap.add_argument("--families", nargs="+", required=True)
    ap.add_argument(
        "--span",
        type=int,
        default=150,
        help=(
            "Slots to resample onto. 0 keeps each family's native LENG "
            "(required when the profile is used as a drift *target*, not a "
            "prior)."
        ),
    )
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    out: dict[str, object] = {
        "source_hmm": str(args.pfam),
        "aa_order": AA_ORDER,
        "span": int(args.span),
        "resample": "none" if int(args.span) <= 0 else "nearest_neighbour_relative",
        "families": {},
    }
    missing: list[str] = []
    for pf in args.families:
        rec = parse_family(args.pfam, pf)
        if rec is None:
            missing.append(pf)
            continue
        logp, cons = conservation_and_logp(rec["neg_logp"])
        out["families"][pf] = {  # type: ignore[index]
            "acc": rec["acc"],
            "name": rec["name"],
            "leng": rec["leng"],
            "logp": resample(logp, int(args.span)),
            "conservation": resample(cons, int(args.span)),
            "conservation_full_mean": sum(cons) / len(cons),
            "conservation_full_min": min(cons),
            "conservation_full_max": max(cons),
        }
        print(
            f"[pfam] {pf} -> {rec['acc']} ({rec['name']}) LENG={rec['leng']} "
            f"mean_IC={out['families'][pf]['conservation_full_mean']:.3f}",
            flush=True,
        )
    if missing:
        print(f"[pfam] MISSING: {missing}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(f"[pfam] wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
