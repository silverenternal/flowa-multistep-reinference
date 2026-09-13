"""FlowMol3 paper eq.4 / eq.21 wrapper — instance-count normalized FG-deviation.

The FlowMol3 paper (Dunn & Koes, arXiv:2508.12629, Digital Discovery 2026,
5, 2052–2066) reports a "Functional-Group Deviation" (FG-deviation) metric
on Table 1 with the headline FlowMol3 number 0.27 +/- 0.03 (preprint) /
0.37 +/- 0.01 (Digital Discovery). The paper defines it as:

    FG dev. = sum_{f in F} |omega_f^{train} - omega_f^{generated}|       (eq.21)

where ``omega_f`` is the **frequency** of functional group ``f``, defined
as:

    omega_f := (# instances of functional group f in sample) /
               (# molecules in sample)

"Number of instances" is the raw integer count of SMARTS matches per
molecule (NOT a binary 0/1 flag — a molecule with two hydroxyl groups
contributes two instances to ``fr_Al_OH``). The set ``F`` is the 85-element
RDKit ``fr_*`` vocabulary used in
:data:`adaptive_reflow.eval.fg_deviation.DUNDEE_FR_SMARTS_NAMES`, which
mirrors :data:`tools.run_mol_eval.FG_SMARTS_NAMES`.

This wrapper is the **paper-equivalent** of the existing
:func:`adaptive_reflow.eval.fg_deviation.fg_deviation_l1`, which uses
**binary** occurrence (a mol contributes 1 to ``sums[k]`` if it has at
least one ``fr_k`` match, 0 otherwise). The paper's
``omega_f = (# instances)/(# mols)`` differs from the binary version
``p_f = (# mols containing f)/(# mols)`` whenever a FG can appear more
than once per molecule — e.g. ``fr_Al_OH``, ``fr_benzene``, ``fr_NH1``.
For those FGs, the paper's instance-count version is strictly larger
than the binary version, and the deviation between gen and ref is
typically larger as well.

This module is a thin wrapper:

  * It **REUSES** :func:`adaptive_reflow.eval.fg_deviation.count_fg_hits`
    for the per-mol raw instance counts (RDKit ``fr_*`` integer counts
    or literal SMARTS match counts via ``GetSubstructMatches``).
  * It **REUSES** :data:`adaptive_reflow.eval.fg_deviation.DUNDEE_FR_SMARTS_NAMES`
    for the 85-element vocabulary.
  * It does NOT re-implement any FG-counting logic; the upstream
    ``rdkit.Chem.Fragments.fr_*`` SMARTS — already pinned in
    :data:`adaptive_reflow.eval.fg_deviation.DUNDEE_FR_SMARTS_NAMES` —
    are the single point of truth.

The headline number for FlowMol3 trained on GEOM-DRUGS with N=5000
generated molecules is **0.37 +/- 0.01** (Digital Discovery Table 1) /
**0.27 +/- 0.03** (arXiv preprint Table 1). With a non-GEOM-DRUGS
proxy reference (e.g. RDKit's NCI ``first_5K.smi``) the number will
shift slightly because the reference distribution differs.

Reference set:
    The paper uses GEOM-DRUGS train (~243K SMILES). When that file is
    missing we transparently fall back to RDKit's NCI ``first_5K.smi``
    proxy (4,991 SMILES) per the same convention as
    :data:`adaptive_reflow.eval.fg_deviation.DEFAULT_REFERENCE_PATH`.
    The choice is surfaced in every JSON output's ``stderr_notes``.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# REUSE the upstream 85-element RDKit fr_* vocabulary + per-mol counter.
# Both are defined in fg_deviation.py — we do NOT redefine them here.
from adaptive_reflow.eval.fg_deviation import (  # noqa: E402
    DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH,
    DEFAULT_REFERENCE_PATH,
    DUNDEE_FR_SMARTS_NAMES,
    _parse_smiles_list,
    count_fg_hits,
)

# ---------------------------------------------------------------------------
# Instance-count aggregation (paper eq.21 normalization)
# ---------------------------------------------------------------------------


def _aggregate_instance_rates(
    items: Sequence[Any],
    smarts_list: Sequence[str] | Mapping[str, str],
) -> tuple[dict[str, float], int]:
    """Mean instance count per FG over ``items`` (paper eq.21 normalization).

    Unlike :func:`adaptive_reflow.eval.fg_deviation._aggregate_occurrence_rates`
    which uses **binary** presence (a mol contributes 1 to ``sums[k]`` if
    it contains ``FG_k`` at least once, 0 otherwise), this function sums
    the **raw integer count** of FG matches per molecule — matching the
    paper's "number of instances of the functional group" definition.

    Returns ``(rates, n_used)`` where ``rates[key] = total_count /
    n_used`` and ``n_used`` is the number of items that parsed +
    contributed at least one FG hit.

    Items that fail to parse are silently skipped; an entirely empty
    / unparseable input returns ``({}, 0)`` so the caller can branch
    on ``n_used == 0``.
    """
    is_mapping = isinstance(smarts_list, Mapping)
    keys: list[str] = (
        list(smarts_list.keys()) if is_mapping
        else list(smarts_list)
    )
    sums: dict[str, int] = {k: 0 for k in keys}
    n_used = 0
    for item in items:
        hits = count_fg_hits(item, smarts_list)
        if not hits:
            continue
        n_used += 1
        for k in keys:
            # Paper: "number of instances of the functional group".
            # count_fg_hits already returns the integer match count
            # (NOT a 0/1 flag); we accumulate it as-is here.
            sums[k] += int(hits.get(k, 0))
    if n_used == 0:
        return {}, 0
    rates = {k: sums[k] / n_used for k in keys}
    return rates, n_used


# ---------------------------------------------------------------------------
# Paper eq.4 / eq.21 entry point
# ---------------------------------------------------------------------------


def fg_deviation_eq4(
    gen_smiles: Sequence[str],
    ref_smiles: Sequence[str],
    fr_vocabulary: Sequence[str] | Mapping[str, str] | None = None,
) -> float:
    """FlowMol3 paper eq.4 / eq.21 — FG-deviation with instance-count omega_f.

    Implements the exact paper formulation:

        FG dev. = sum_{f in F} | omega_f^{ref} - omega_f^{gen} |

    where ``omega_f := (# instances of f) / (# mols)``.

    Parameters
    ----------
    gen_smiles : sequence of str
        Generated molecules as SMILES. Items that fail to parse are
        silently dropped; the denominator ``n_gen`` is the count of
        items that parsed AND contributed at least one FG hit.
    ref_smiles : sequence of str
        Reference molecules as SMILES. Same tolerance as ``gen_smiles``.
    fr_vocabulary : sequence or mapping, optional
        The FG vocabulary to use. Defaults to the 85-element RDKit
        ``fr_*`` list
        (:data:`adaptive_reflow.eval.fg_deviation.DUNDEE_FR_SMARTS_NAMES`).
        Pass a custom list of SMARTS or a mapping of ``{name:
        smarts_or_fr_func_name}`` to use a different vocabulary.

    Returns
    -------
    float
        The paper FG-deviation value. ``NaN`` when either set is empty
        after parsing / FG-counting, so callers can chain safely with
        other metrics. The value is in ``[0, inf)`` — there is no
        theoretical upper bound because instance counts per mol are
        unbounded, but for drug-like sets with the 85-element
        vocabulary the value is typically in ``[0, 5]`` (FlowMol3
        reports 0.37 +/- 0.01 on GEOM-DRUGS / Digital Discovery Table 1).

    Notes
    -----
    * This differs from
      :func:`adaptive_reflow.eval.fg_deviation.fg_deviation_l1` in two
      ways: (a) it uses raw instance counts per mol (not binary 0/1
      flags), and (b) it does NOT divide by ``|F|`` (the paper's eq.21
      is a raw sum, not a per-FG mean). For matched distributions
      (``gen_smiles == ref_smiles``) both functions return ``0.0``.
    * The vocabulary is NOT normalized by ``|F|``. The paper's headline
      number 0.37 is the raw sum over the 85-element set.
    """
    vocab = (
        DUNDEE_FR_SMARTS_NAMES
        if fr_vocabulary is None
        else fr_vocabulary
    )

    gen_mols, _ = _parse_smiles_list(gen_smiles)
    ref_mols, _ = _parse_smiles_list(ref_smiles)
    if not gen_mols or not ref_mols:
        return float("nan")

    gen_rates, n_gen = _aggregate_instance_rates(gen_mols, vocab)
    ref_rates, n_ref = _aggregate_instance_rates(ref_mols, vocab)
    if n_gen == 0 or n_ref == 0:
        return float("nan")

    keys = list(gen_rates.keys())
    value = 0.0
    for k in keys:
        d = gen_rates[k] - ref_rates.get(k, 0.0)
        value += abs(d)
    return float(value)


# ---------------------------------------------------------------------------
# Convenience wrapper: load reference from disk and emit a JSON-friendly dict
# ---------------------------------------------------------------------------


def compute_fg_deviation_eq4(
    gen_smiles: Sequence[str],
    *,
    reference_smiles_path: str | os.PathLike[str] | None = DEFAULT_REFERENCE_PATH,
    reference_smiles: Sequence[str] | None = None,
    fr_vocabulary: Sequence[str] | Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Compute FG-dev per eq.4 and return a JSON-friendly dict.

    This is a thin convenience wrapper around
    :func:`fg_deviation_eq4` that handles reference loading from disk
    (defaulting to :data:`DEFAULT_REFERENCE_PATH`) and surfaces the
    paper-parity status in a ``stderr_notes``-style note, mirroring the
    contract of :func:`adaptive_reflow.eval.fg_deviation.compute_flowmol3_fg_deviation`.

    Returns a dict with:

      * ``value`` — paper eq.4 FG-deviation (float; NaN on parse failure)
      * ``n_gen`` / ``n_ref`` — molecule counts after parse + FG filter
      * ``n_gen_skipped`` / ``n_ref_skipped`` — parse failures
      * ``reference_source`` — path or ``"explicit_smiles_arg"``
      * ``vocabulary_size`` — number of FG groups used
      * ``note`` — human-readable summary (proxy choice + vocabulary)

    On RDKit unavailable the function returns ``{"value": NaN, ...}``
    with a note describing the failure rather than raising.
    """
    nan = float("nan")
    base: dict[str, Any] = {
        "value": nan,
        "n_gen": 0,
        "n_ref": 0,
        "n_gen_skipped": 0,
        "n_ref_skipped": 0,
        "reference_source": (
            str(reference_smiles_path)
            if reference_smiles_path is not None
            else "explicit_smiles_arg"
        ),
        "vocabulary_size": (
            len(fr_vocabulary)
            if fr_vocabulary is not None
            else len(DUNDEE_FR_SMARTS_NAMES)
        ),
        "note": None,
    }

    try:
        import rdkit  # noqa: F401, PLC0415
    except ImportError as exc:
        base["note"] = f"rdkit_unavailable:{exc}"
        return base

    gen_mols, n_gen_skipped = _parse_smiles_list(gen_smiles)
    if not gen_mols:
        base["note"] = "fg_dev_eq4_no_usable_generated_mols"
        base["n_gen_skipped"] = int(n_gen_skipped)
        return base

    if reference_smiles is not None:
        ref_raw = list(reference_smiles)
        base["reference_source"] = "explicit_smiles_arg"
    else:
        ref_raw: list[str] = []
        if reference_smiles_path is not None:
            ref_path = Path(reference_smiles_path)
            if ref_path.exists():
                # Stream line-by-line: the GEOM-DRUGS reference has
                # ~1M+ SMILES — Path.read_text().splitlines() would
                # double-materialize the file (full string + full
                # line list). Only one line sits in memory at a
                # time plus the growing output list.
                with ref_path.open("r", encoding="utf-8") as f:
                    for ln in f:
                        ln = ln.strip()
                        if not ln:
                            continue
                        ref_raw.append(ln.split("\t", 1)[0])
        if not ref_raw:
            base["note"] = "fg_dev_eq4_reference_unavailable"
            base["n_gen"] = int(len(gen_mols))
            base["n_gen_skipped"] = int(n_gen_skipped)
            return base
    ref_mols, n_ref_skipped = _parse_smiles_list(ref_raw)

    base["n_gen"] = int(len(gen_mols))
    base["n_ref"] = int(len(ref_mols))
    base["n_gen_skipped"] = int(n_gen_skipped)
    base["n_ref_skipped"] = int(n_ref_skipped)

    if not ref_mols:
        base["note"] = "fg_dev_eq4_reference_all_unparseable"
        return base

    value = fg_deviation_eq4(
        gen_mols, ref_mols, fr_vocabulary=fr_vocabulary,
    )
    base["value"] = float(value) if value == value else nan

    if base["note"] is None:
        proxy_note = (
            "reference=GEOM_DRUGS_TRAIN_PAPER_PARITY"
            if base["reference_source"] == DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH
            else (
                "reference=GEOM_DRUGS_TRAIN_FALLBACK_TO_NCI_first_5K_proxy:"
                "download_geom_raw_train_pickle_to_enable_paper_parity"
                if base["reference_source"] != "explicit_smiles_arg"
                and DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH
                and not Path(DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH).exists()
                else "reference=explicit_smiles_arg"
            )
        )
        base["note"] = (
            f"fg_dev_eq4=paper_instance_count_L1_over_{base['vocabulary_size']}_rules:"
            f"{proxy_note}:reference_path={base['reference_source']}"
        )
    return base


__all__ = [
    "compute_fg_deviation_eq4",
    "fg_deviation_eq4",
]


if __name__ == "__main__":
    # Minimal CLI smoke entry: load NCI first_5K.smi as both gen and ref
    # (self-comparison should yield exactly 0.0), then load gen as a
    # 100-mol subset of NCI and ref as the next 100-mol chunk and report
    # the resulting FG-dev. Saves the result to /tmp/eq4_smoke_output.json.
    import sys

    nci_path = (
        "/home/hugo/codes/flowa-multistep-reinference/.venvs/"
        "flowmol3_venv/lib/python3.12/site-packages/rdkit/Data/NCI/first_5K.smi"
    )

    def _load_nci(path: str, n: int, start: int = 0) -> list[str]:
        out: list[str] = []
        with open(path, encoding="utf-8") as fh:
            for ln in fh:
                if not ln.strip():
                    continue
                out.append(ln.split("\t", 1)[0])
                if len(out) >= start + n:
                    break
        return out[start : start + n]

    ref_smiles = _load_nci(nci_path, 100, start=0)
    # Use a shifted slice as "generated" — close enough to the reference
    # to exercise the metric without diverging wildly from drug-likeness.
    gen_smiles = _load_nci(nci_path, 100, start=200)

    result = compute_fg_deviation_eq4(
        gen_smiles,
        reference_smiles=ref_smiles,
    )
    # Self-check: gen == ref should be exactly 0.0
    self_check = compute_fg_deviation_eq4(
        ref_smiles,
        reference_smiles=ref_smiles,
    )

    out = {
        "smoke_test": "eq4_fg_deviation_100mols_vs_100mols",
        "ref_source": "rdkit NCI first_5K.smi",
        "gen_subset": "indices [200, 300) of first_5K.smi",
        "ref_subset": "indices [0, 100) of first_5K.smi",
        "result_cross": result,
        "self_check_value": self_check["value"],
        "expected_self_check": 0.0,
        "headline_paper_digital_discovery_table1": 0.37,
        "headline_paper_arxiv_preprint_table1": 0.27,
    }

    out_path = "/tmp/eq4_smoke_output.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)

    print(f"Wrote smoke output to {out_path}")
    print(f"cross fg_dev_eq4 = {result['value']:.6f}")
    print(f"self fg_dev_eq4  = {self_check['value']:.6f}  (expected 0.0)")
    sys.exit(0 if self_check["value"] == 0.0 else 1)
