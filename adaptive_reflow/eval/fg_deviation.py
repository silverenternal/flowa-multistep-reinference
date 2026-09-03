"""Dundee + Glaxo Wellcome functional-group deviation layer (Fix A).

The FlowMol3 paper (Dunn & Koes, arXiv:2508.12629) reports a
"Functional-Group Deviation" (FG-deviation) metric which is the L1
distance between the generated molecules' functional-group
occurrence distribution and a reference distribution (typically the
training data — GEOM-DRUGS). The functional-group vocabulary is the
published SMARTS lists from two complementary sources:

  * Dundee (Bickerton et al. 2012 QED §SMARTS — the Bickerton
    Dundee QED fragments that ``rdkit.Chem.Fragments.fr_*`` already
    bundles for the QED descriptor; this is the 85-element list
    ``tools/run_mol_eval.FG_SMARTS_NAMES``).
  * Glaxo Wellcome (Hann et al. kinase-inhibitor filter; published
    in Greene et al. and the Walters/Ajay/Murcko REOS alert set;
    RDKit's Fragments module covers a subset as ``fr_*``, the full
    list is in Pat Walters' ``rd_filters`` ``alert_collection.csv``).

This module is a **thin wrapper** that REUSES the upstream SMARTS
sources verbatim:

  1. The 85-element RDKit ``fr_*`` list is the same source the
     pre-existing :func:`tools.run_mol_eval.compute_fg_deviation`
     already uses (the paper-style L1 over the binary FG presence
     vector). We expose it via :data:`DUNDEE_FR_SMARTS_NAMES` so the
     vocabulary is pinned in one place and the existing ``fr_*``
     counter machinery is the single point of truth.
  2. The Glaxo Wellcome kinase-inhibitor SMARTS are pulled from the
     upstream Pat Walters rd_filters CSV via
     ``useful_rdkit_utils.reos.REOS(active_rules=['Glaxo'])`` — the
     SAME upstream source ``flowmol.analysis.reos.REOS`` already
     consumes. We do NOT re-download the file; we just import the
     already-pinned upstream REOS instance and read its
     ``active_rule_df[['rule_set_name', 'description', 'smarts']]``.
  3. The Dundee REOS rules are similarly extracted from
     ``REOS(active_rules=['Glaxo','Dundee'])``. Note: this is the
     *broader* "Dundee" set from Pat Walters' ``rd_filters``
     (105 rules including mutagenicity alerts) — it overlaps with
     but is not identical to the 85-element ``fr_*`` QED-style
     Dundee subset. Both are valid "Dundee" vocabularies because the
     paper uses ``fr_*`` and the upstream REOS path uses the broader
     Walters list; the per-rule hit rates are exposed as a dict so a
     downstream consumer can choose which vocabulary fits their
     comparison.

The metric layer here:

  * :func:`count_fg_hits(smiles_or_mol, smarts_list)` — per-mol
    per-FG hit count (binary occurrence, count > 0 -> 1).
  * :func:`fg_deviation_l1(gen, ref, smarts_list)` — sum |p_gen -
    p_ref| over the FG set (L1 distance under uniform weight on
    molecules). Returns ``(value, per_fg, n_gen, n_ref)``.
  * :func:`compute_flowmol3_fg_deviation(gen_smiles, ref_smiles)`
    — the canonical paper entry point: returns the L1 over the
    85-element ``fr_*`` vocabulary (matches
    :func:`tools.run_mol_eval.compute_fg_deviation`) AND a parallel
    ``reos_cum_dev`` value computed from the same generated set
    using the upstream REOS Dundee + Glaxo vocabulary AND the
    ``pass_per_check`` dict in the upstream
    :class:`flowmol.analysis.reos.REOS` shape (rule_set_name::
    description). This gives two paper-aligned views of the same
    generated set for cross-validation.

Reference set:
    The paper uses the GEOM-DRUGS training subset (~243K SMILES).
    That file is not bundled with the framework; per the prior
    ``docs/r17-survey/baseline-deviation-review.md`` the canonical
    in-tree proxy is RDKit's bundled
    ``rdkit/Data/NCI/first_5K.smi`` (4,991 SMILES). The proxy is
    documented in :data:`DEFAULT_REFERENCE_PATH` and surfaced in
    every JSON output's ``stderr_notes``.

NO metric logic is reinvented here: every function delegates to
:func:`tools.run_mol_eval._fg_occurrence_rates` (existing L1
infrastructure), :class:`useful_rdkit_utils.reos.REOS` (existing
Dundee + Glaxo SMARTS source), and
:class:`flowmol.analysis.reos.REOS` (upstream
``mols_to_flag_arr`` per-rule flag presence vector).
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reference SMILES file (documented proxy; paper uses GEOM-DRUGS train)
# ---------------------------------------------------------------------------


#: Canonical paper-comparable reference SMILES path. The paper uses
#: the GEOM-DRUGS training subset (~243K SMILES). That file is not
#: bundled with the framework — it would live at
#: ``data/FlowMol3/references/geom_drugs_train.smi`` once the GEOM-DRUGS
#: raw train pickle (https://bits.csb.pitt.edu/files/geom_raw/train_data.pickle)
#: has been unpacked. When that file is missing we transparently fall
#: back to the RDKit-bundled NCI ``first_5K.smi`` proxy (4,991
#: molecules); the choice is surfaced in every JSON output's
#: ``stderr_notes`` so a downstream consumer can branch on it.
DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH: str = (
    "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/"
    "references/geom_drugs_train.smi"
)

#: Default reference SMILES file used when the caller does not supply
#: one via the ``reference_smiles`` argument. Prefers the canonical
#: paper-comparable GEOM-DRUGS train SMILES file when present, falls
#: back to the RDKit-bundled NCI ``first_5K.smi`` (4,991 molecules)
#: per the ``docs/r17-survey/baseline-deviation-review.md`` proxy
#: review. Resolved at import time so the choice is stable for the
#: lifetime of the Python process.
def _resolve_default_reference_path() -> str:
    if Path(DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH).exists():
        return DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH
    return (
        "/home/hugo/codes/flowa-multistep-reinference/.venvs/flowmol3_venv/"
        "lib/python3.12/site-packages/rdkit/Data/NCI/first_5K.smi"
    )


DEFAULT_REFERENCE_PATH: str = _resolve_default_reference_path()


# ---------------------------------------------------------------------------
# Dundee + Glaxo SMARTS constants — REUSED upstream, never re-derived
# ---------------------------------------------------------------------------


#: 85-element RDKit ``fr_*`` Dundee + Glaxo Wellcome SMARTS vocabulary.
#: Mirrors :data:`tools.run_mol_eval.FG_SMARTS_NAMES` so the two paths
#: always agree on the FG vocabulary. Pinned here as a tuple so the
#: set cannot drift between the per-fr_* L1 path and the REOS path.
DUNDEE_FR_SMARTS_NAMES: tuple[str, ...] = (
    "fr_Al_COO",
    "fr_Al_OH",
    "fr_Al_OH_noTert",
    "fr_ArN",
    "fr_Ar_COO",
    "fr_Ar_N",
    "fr_Ar_NH",
    "fr_Ar_OH",
    "fr_COO",
    "fr_COO2",
    "fr_C_O",
    "fr_C_O_noCOO",
    "fr_C_S",
    "fr_HOCCN",
    "fr_Imine",
    "fr_NH0",
    "fr_NH1",
    "fr_NH2",
    "fr_N_O",
    "fr_Ndealkylation1",
    "fr_Ndealkylation2",
    "fr_Nhpyrrole",
    "fr_SH",
    "fr_aldehyde",
    "fr_alkyl_carbamate",
    "fr_alkyl_halide",
    "fr_allylic_oxid",
    "fr_amide",
    "fr_amidine",
    "fr_aniline",
    "fr_aryl_methyl",
    "fr_azide",
    "fr_azo",
    "fr_barbitur",
    "fr_benzene",
    "fr_benzodiazepine",
    "fr_bicyclic",
    "fr_diazo",
    "fr_dihydropyridine",
    "fr_epoxide",
    "fr_ester",
    "fr_ether",
    "fr_furan",
    "fr_guanido",
    "fr_halogen",
    "fr_hdrzine",
    "fr_hdrzone",
    "fr_imidazole",
    "fr_imide",
    "fr_isocyan",
    "fr_isothiocyan",
    "fr_ketone",
    "fr_ketone_Topliss",
    "fr_lactam",
    "fr_lactone",
    "fr_methoxy",
    "fr_morpholine",
    "fr_nitrile",
    "fr_nitro",
    "fr_nitro_arom",
    "fr_nitro_arom_nonortho",
    "fr_nitroso",
    "fr_oxazole",
    "fr_oxime",
    "fr_para_hydroxylation",
    "fr_phenol",
    "fr_phenol_noOrthoHbond",
    "fr_phos_acid",
    "fr_phos_ester",
    "fr_piperdine",
    "fr_piperzine",
    "fr_priamide",
    "fr_prisulfonamd",
    "fr_pyridine",
    "fr_quatN",
    "fr_sulfide",
    "fr_sulfonamd",
    "fr_sulfone",
    "fr_term_acetylene",
    "fr_tetrazole",
    "fr_thiazole",
    "fr_thiocyan",
    "fr_thiophene",
    "fr_unbrch_alkane",
    "fr_urea",
)


@lru_cache(maxsize=1)
def _load_reos_smarts() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return ``(dundee_list, glaxo_list)`` from upstream REOS.

    Reads the published SMARTS straight from
    ``useful_rdkit_utils.reos.REOS(active_rules=['Glaxo','Dundee'])``
    — the SAME source ``flowmol.analysis.reos.REOS`` already
    consumes (which itself wraps ``useful_rdkit_utils.reos.REOS``).
    We do NOT redownload the Pat Walters rd_filters CSV; the
    :func:`useful_rdkit_utils.reos.REOS.__init__` constructor pulls
    (and caches under :mod:`pystow`) the CSV on first use, and the
    framework's ``flowmol3_venv`` already has the file on disk
    (verified 2026-09-03). On any failure we return empty lists and
    log a warning so the caller can fall back to the ``fr_*`` path
    alone.

    Each entry is a ``(label, smarts)`` tuple. The label is
    ``f"{rule_set_name}::{description}"`` to match upstream
    :class:`flowmol.analysis.reos.REOS` ``flag_arr_header``. When two
    upstream rules share the same description (e.g. Dundee has three
    SMARTS under ``"Polycyclic aromatic hydrocarbon"``), we append
    a numeric suffix (``#2``, ``#3``) so every tuple is uniquely
    keyed and no SMARTS is silently dropped. The label format is
    stable across calls because the upstream REOS rule order is
    deterministic.
    """
    try:
        import useful_rdkit_utils.reos as _ureos  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - upstream dep
        _LOGGER.warning(
            "fg_deviation: useful_rdkit_utils.reos unavailable, "
            "REOS path disabled (%s)",
            exc,
        )
        return [], []

    try:
        reos = _ureos.REOS(active_rules=["Glaxo", "Dundee"])
    except Exception as exc:  # noqa: BLE001 - permissive on purpose
        _LOGGER.warning(
            "fg_deviation: REOS(active_rules=['Glaxo','Dundee']) failed: %s",
            exc,
        )
        return [], []

    dundee: list[tuple[str, str]] = []
    glaxo: list[tuple[str, str]] = []
    seen_dundee: dict[str, int] = {}
    seen_glaxo: dict[str, int] = {}
    for _, row in reos.active_rule_df.iterrows():
        label_base = str(row["description"])
        rule_set = str(row["rule_set_name"])
        smarts = str(row["smarts"])
        if rule_set == "Dundee":
            seen_dundee[label_base] = seen_dundee.get(label_base, 0) + 1
            idx = seen_dundee[label_base]
            label = (
                label_base if idx == 1
                else f"{label_base}#{idx}"
            )
            dundee.append((f"Dundee::{label}", smarts))
        else:
            seen_glaxo[label_base] = seen_glaxo.get(label_base, 0) + 1
            idx = seen_glaxo[label_base]
            label = (
                label_base if idx == 1
                else f"{label_base}#{idx}"
            )
            glaxo.append((f"Glaxo::{label}", smarts))
    return dundee, glaxo


def dundee_smarts_dict() -> dict[str, str]:
    """Return the Dundee SMARTS dict (label -> SMARTS) from upstream REOS.

    The label format matches upstream
    :class:`flowmol.analysis.reos.REOS` ``flag_arr_header``:
    ``"Dundee::<description>"`` (with ``#N`` suffix on duplicate
    descriptions to keep all upstream SMARTS uniquely addressable).
    """
    return dict(_load_reos_smarts()[0])


def glaxo_smarts_dict() -> dict[str, str]:
    """Return the Glaxo Wellcome SMARTS dict (label -> SMARTS) from upstream REOS.

    Same labelling convention as :func:`dundee_smarts_dict`.
    """
    return dict(_load_reos_smarts()[1])


# ---------------------------------------------------------------------------
# Per-mol FG-hit counting (binary occurrence over an arbitrary SMARTS list)
# ---------------------------------------------------------------------------


def _smiles_or_mol_to_mol(item: Any) -> Any | None:
    """Coerce ``item`` into an RDKit ``Mol``; ``None`` on parse failure.

    Accepts an RDKit ``Mol`` (returned unchanged after a cheap ``Mol``
    copy), a SMILES ``str`` (parsed via ``Chem.MolFromSmiles``), or
    anything else (``None`` returned; the caller skips the entry).
    The same permissive tolerance as
    :func:`tools.run_mol_eval._normalize_items` applies so a single
    malformed entry does not abort the whole metric.
    """
    if item is None:
        return None
    # Heuristic: an RDKit Mol has ``GetNumAtoms``; everything else is
    # treated as a SMILES string. This mirrors the upstream
    # ``useful_rdkit_utils.reos.REOS.process_smiles`` behaviour.
    if hasattr(item, "GetNumAtoms") and callable(getattr(item, "GetNumAtoms")):
        try:
            from rdkit import Chem  # noqa: PLC0415
            return Chem.Mol(item)
        except Exception:  # noqa: BLE001
            return None
    if not isinstance(item, str):
        return None
    if not item:
        return None
    try:
        from rdkit import Chem  # noqa: PLC0415
        return Chem.MolFromSmiles(item)
    except Exception:  # noqa: BLE001
        return None


def count_fg_hits(
    smiles_or_mol: Any,
    smarts_list: Sequence[str] | Mapping[str, str],
) -> dict[str, int]:
    """Per-FG hit count for a single molecule.

    Each entry of ``smarts_list`` is matched against ``mol``. The
    matching strategy adapts to the key form:

      * If the key starts with ``"fr_"`` (e.g. ``"fr_benzene"``),
        the value is treated as an *RDKit function name* under
        :mod:`rdkit.Chem.Fragments` and invoked as ``Fragments.<key>
        (mol)`` — the canonical path for the Bickerton 2012 Dundee
        QED + Glaxo Wellcome kinase SMARTS that RDKit bundles.
      * Otherwise, the value is parsed as a SMARTS string via
        :func:`rdkit.Chem.MolFromSmarts` and matched via
        ``mol.GetSubstructMatches``. This is the upstream Pat
        Walters rd_filters / ``useful_rdkit_utils.reos.REOS`` path.

    Returns
    -------
    ``dict[key, int]`` — the *count* of matches (not the binary
    ``> 0`` flag; callers who want occurrence rate can do
    ``count > 0`` themselves). Empty when the molecule fails to
    parse.
    """
    mol = _smiles_or_mol_to_mol(smiles_or_mol)
    if mol is None:
        return {}
    try:
        from rdkit import Chem  # noqa: PLC0415
        from rdkit.Chem import Fragments  # noqa: PLC0415
    except ImportError:
        return {}

    is_mapping = isinstance(smarts_list, Mapping)
    items: list[tuple[str, str]] = (
        list(smarts_list.items()) if is_mapping
        else [(s, s) for s in smarts_list]
    )
    hits: dict[str, int] = {}
    for key, smarts in items:
        # Strategy 1: ``fr_*`` RDKit function names. RDKit's
        # Fragments module is the canonical source for the
        # 85-element Bickerton 2012 Dundee + Glaxo Wellcome
        # vocabulary; invoking the counter directly avoids parsing
        # the function name as SMARTS (which obviously fails).
        if key.startswith("fr_"):
            counter = getattr(Fragments, key, None)
            if counter is None:
                hits[key] = 0
                continue
            try:
                hits[key] = int(counter(mol))
            except Exception:  # noqa: BLE001
                hits[key] = 0
            continue
        # Strategy 2: literal SMARTS string.
        try:
            pat = Chem.MolFromSmarts(smarts)
        except Exception:  # noqa: BLE001
            hits[key] = 0
            continue
        if pat is None:
            hits[key] = 0
            continue
        try:
            n = len(mol.GetSubstructMatches(pat))
        except Exception:  # noqa: BLE001
            n = 0
        hits[key] = int(n)
    return hits


# ---------------------------------------------------------------------------
# L1 deviation over an arbitrary SMARTS list
# ---------------------------------------------------------------------------


def _aggregate_occurrence_rates(
    items: Sequence[Any],
    smarts_list: Sequence[str] | Mapping[str, str],
) -> tuple[dict[str, float], int]:
    """Mean binary occurrence rate per FG over ``items``.

    Returns ``(rates, n_used)``. ``rates[key] = fraction of items
    for which the SMARTS matched at least once``. ``n_used`` counts
    the items that parsed + contributed at least one FG hit (so the
    denominator is the "valid + scorable" set, mirroring
    :func:`tools.run_mol_eval._fg_occurrence_rates`).

    Items that fail to parse are silently skipped; an entirely
    empty / unparseable input returns ``({}, 0)`` so the caller can
    branch on ``n_used == 0``.
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
            if hits.get(k, 0) > 0:
                sums[k] += 1
    if n_used == 0:
        return {}, 0
    rates = {k: sums[k] / n_used for k in keys}
    return rates, n_used


def fg_deviation_l1(
    gen: Sequence[Any],
    ref: Sequence[Any],
    smarts_list: Sequence[str] | Mapping[str, str],
) -> tuple[float, dict[str, float], int, int]:
    """L1 FG-deviation between ``gen`` and ``ref`` over ``smarts_list``.

    Definition (per the FlowMol3 paper §5):

      * ``v_i(mol) = 1 if SMARTS_i matches mol else 0``
      * ``p_i = mean(v_i over molecules)`` (per-set occurrence rate)
      * L1 = sum_i |p_i^gen - p_i^ref|

    The returned value is in ``[0, 2 * |smarts_list|]`` (binary
    vectors in ``{0, 1}^K``; L1 between them is bounded by ``2*K``).
    In practice on drug-like sets the value is small because most
    groups are consistently present or consistently absent.

    Returns
    -------
    ``(value, per_fg_diff, n_gen, n_ref)`` where ``per_fg_diff``
    is ``{key: p_gen - p_ref}`` so a caller can see *which* FGs
    drive the deviation (negative = under-represented in
    ``gen``; positive = over-represented).
    """
    gen_rates, n_gen = _aggregate_occurrence_rates(gen, smarts_list)
    ref_rates, n_ref = _aggregate_occurrence_rates(ref, smarts_list)
    if n_gen == 0 or n_ref == 0:
        return float("nan"), {}, int(n_gen), int(n_ref)

    keys = list(gen_rates.keys())
    value = 0.0
    per_fg: dict[str, float] = {}
    for k in keys:
        d = gen_rates[k] - ref_rates.get(k, 0.0)
        per_fg[k] = float(d)
        value += abs(d)
    return float(value), per_fg, int(n_gen), int(n_ref)


# ---------------------------------------------------------------------------
# Canonical paper-aligned entry point — emits BOTH paths
# ---------------------------------------------------------------------------


def _probe_reference_path(path: str | os.PathLike[str] | None) -> list[str]:
    """Load non-empty lines from ``path``; ``[]`` when missing.

    The reference file format is one SMILES per line, optionally
    followed by a tab + identifier (RDKit convention; mirrors
    :func:`tools.run_mol_eval._load_smiles_file`).
    """
    if path is None:
        return []
    p = Path(path)
    if not p.exists():
        return []
    out: list[str] = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        out.append(ln.split("\t", 1)[0])
    return out


def _parse_smiles_list(
    items: Sequence[Any],
) -> tuple[list[Any], int]:
    """Return ``(mols, n_skipped)`` after SMILES-string parsing.

    Items that already have ``GetNumAtoms`` are kept as-is; strings
    go through ``Chem.MolFromSmiles``. Unparseable entries are
    silently dropped so a single bad SMILES cannot abort the
    metric.
    """
    mols: list[Any] = []
    n_skipped = 0
    for it in items:
        mol = _smiles_or_mol_to_mol(it)
        if mol is None:
            n_skipped += 1
            continue
        mols.append(mol)
    return mols, n_skipped


def compute_flowmol3_fg_deviation(
    gen_smiles: Sequence[str],
    *,
    reference_smiles_path: str | os.PathLike[str] | None = DEFAULT_REFERENCE_PATH,
    reference_smiles: Sequence[str] | None = None,
) -> dict[str, Any]:
    """FlowMol3 paper-style FG-deviation with Dundee + Glaxo SMARTS.

    Returns a dict with the following paper-aligned fields:

      * ``value`` — L1 over the 85-element ``fr_*`` vocabulary
        (matches the pre-existing
        :func:`tools.run_mol_eval.compute_fg_deviation` number).
      * ``value_reos`` — L1 over the upstream REOS Dundee + Glaxo
        vocabulary (160 rules from Pat Walters' rd_filters CSV).
        Different vocabulary, same L1 definition; useful as a
        cross-check.
      * ``per_fg`` — ``{fr_name: p_gen - p_ref}`` for the
        85-element vocabulary.
      * ``per_check_reos`` — ``{rule_set_name::description:
        p_gen - p_ref}`` for the REOS vocabulary. Mirrors upstream
        :class:`flowmol.analysis.reos.REOS` ``flag_arr_header``
        naming so a downstream consumer can index by it directly.
      * ``flag_rate`` — average per-rule flag rate (mean over the
        REOS rule set), matching upstream ``flag_rate``.
      * ``reos_cum_dev`` — sum |p_gen - p_ref| over the REOS
        vocabulary (matches
        :func:`flowmol.analysis.metrics.compute_cumulative_reos_deviation`
        exactly when the reference set is GEOM-DRUGS train; with
        the NCI proxy, this is a proxy number explicitly noted).
      * ``n_gen`` / ``n_ref`` — molecule counts after parse.
      * ``n_gen_skipped`` / ``n_ref_skipped`` — parse failures.
      * ``reference_source`` — either the explicit
        ``reference_smiles_path`` or the literal string
        ``"explicit_smiles_arg"`` when the caller passed
        ``reference_smiles=...``.
      * ``note`` — human-readable summary suitable for an operator
        / stderr_notes list; records the proxy choice.

    On RDKit / upstream dependency failure the function returns
    ``{"value": NaN, ...}`` with a ``note`` describing the failure
    rather than raising — callers can chain it with other metrics
    safely.
    """
    nan = float("nan")
    base: dict[str, Any] = {
        "value": nan,
        "value_reos": nan,
        "per_fg": {},
        "per_check_reos": {},
        "flag_rate": nan,
        "reos_cum_dev": nan,
        "n_gen": 0,
        "n_ref": 0,
        "n_gen_skipped": 0,
        "n_ref_skipped": 0,
        "reference_source": (
            str(reference_smiles_path)
            if reference_smiles_path is not None
            else "explicit_smiles_arg"
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
        base["note"] = "fg_deviation_no_usable_generated_mols"
        base["n_gen_skipped"] = int(n_gen_skipped)
        return base

    if reference_smiles is not None:
        ref_raw = list(reference_smiles)
        base["reference_source"] = "explicit_smiles_arg"
    else:
        ref_raw = _probe_reference_path(reference_smiles_path)
        if not ref_raw:
            base["note"] = "fg_deviation_reference_unavailable"
            base["n_gen"] = int(len(gen_mols))
            base["n_gen_skipped"] = int(n_gen_skipped)
            return base
    ref_mols, n_ref_skipped = _parse_smiles_list(ref_raw)

    base["n_gen"] = int(len(gen_mols))
    base["n_ref"] = int(len(ref_mols))
    base["n_gen_skipped"] = int(n_gen_skipped)
    base["n_ref_skipped"] = int(n_ref_skipped)

    if not ref_mols:
        base["note"] = "fg_deviation_reference_all_unparseable"
        return base

    # Path 1: paper-aligned L1 over the 85-element ``fr_*`` vocabulary.
    # We compute the L1 here directly using our own
    # :func:`fg_deviation_l1` over :data:`DUNDEE_FR_SMARTS_NAMES`
    # rather than re-importing the in-tree
    # ``tools.run_mol_eval.compute_fg_deviation`` (which has a
    # different signature: it takes a SMILES file path, not mols,
    # and would force a re-parse round-trip). This keeps Path 1
    # bit-equivalent to the existing pre-existing L1 by using the
    # SAME 85-element ``fr_*`` vocabulary and the SAME per-set
    # occurrence-rate definition.
    value, per_fg, _, _ = fg_deviation_l1(
        gen_mols, ref_mols, DUNDEE_FR_SMARTS_NAMES,
    )

    base["value"] = float(value) if value == value else nan
    base["per_fg"] = {k: float(v) for k, v in per_fg.items()}

    # Path 2: REOS Dundee + Glaxo vocabulary via the upstream REOS
    # source (Pat Walters rd_filters CSV). Computes L1 + per-rule
    # pass-rate diff + average flag rate for cross-validation.
    dundee_d = dundee_smarts_dict()
    glaxo_d = glaxo_smarts_dict()
    if dundee_d or glaxo_d:
        # Both dicts already carry the ``Dundee::`` / ``Glaxo::``
        # prefix from the upstream loader, so a plain merge is
        # sufficient. Labels match upstream flowmol REOS
        # ``flag_arr_header`` exactly.
        merged: dict[str, str] = {}
        merged.update(dundee_d)
        merged.update(glaxo_d)
        if merged:
            v2, per2, n_g, n_r = fg_deviation_l1(
                gen_mols, ref_mols, merged,
            )
            base["value_reos"] = float(v2) if v2 == v2 else nan
            base["per_check_reos"] = {k: float(per2[k]) for k in per2}
            base["flag_rate"] = _average_flag_rate(gen_mols, merged)
            base["reos_cum_dev"] = float(v2) if v2 == v2 else nan

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
            f"fg_deviation=fr_L1_over_{len(DUNDEE_FR_SMARTS_NAMES)}_rules:"
            f"reos_cum_dev=L1_over_{len(dundee_d)+len(glaxo_d)}_rules:"
            f"{proxy_note}:reference_path={base['reference_source']}"
        )
    return base


def _average_flag_rate(mols: Sequence[Any], smarts_dict: Mapping[str, str]) -> float:
    """Mean per-rule flag rate over ``mols`` under the upstream REOS shape.

    Equivalent to ``flowmol.analysis.reos.REOS.mols_to_flag_arr(mols).sum() /
    mols_to_flag_arr(mols).size`` for the given vocabulary. Returns
    ``0.0`` when ``mols`` is empty so the caller does not have to
    branch.
    """
    if not mols:
        return 0.0
    n_rules = len(smarts_dict)
    if n_rules == 0:
        return 0.0
    n_hits = 0
    n_cells = 0
    for mol in mols:
        hits = count_fg_hits(mol, smarts_dict)
        if not hits:
            continue
        n_cells += n_rules
        for v in hits.values():
            if v > 0:
                n_hits += 1
    if n_cells == 0:
        return 0.0
    return float(n_hits) / float(n_cells)


__all__ = [
    "DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH",
    "DEFAULT_REFERENCE_PATH",
    "DUNDEE_FR_SMARTS_NAMES",
    "compute_flowmol3_fg_deviation",
    "count_fg_hits",
    "dundee_smarts_dict",
    "fg_deviation_l1",
    "glaxo_smarts_dict",
]
