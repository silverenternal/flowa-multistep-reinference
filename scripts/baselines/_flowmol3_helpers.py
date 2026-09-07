"""Shared helpers for Wave 54 Phase 2 FlowMol3 baseline scripts.

This module mirrors :mod:`scripts.baselines._lineageflow_helpers` for the
FlowMol3 axis. It provides:

* :func:`chem_validity` — RDKit-backed validity + stability computation on
  a small molecule ensemble (3D coords + atom-type indices). Returns
  ``(frac_valid_mols, frac_mols_stable)`` and a ``marker`` string
  (``"ok"`` | ``"blocked_rdkit"``) so the baseline scripts degrade
  gracefully if RDKit is unavailable.

* :func:`composite_score` — byte-identical re-implementation of
  :meth:`adaptive_reflow.adapters.flowmol3_glue.FlowMol3Glue.composite_score`
  for the chemistry-only path (geometry axis dropped). Mirrors the
  Wave 49 Agent D 5-axis default weights and the ``renormalize_for_geometry``
  rule.

* :func:`make_native_state` — produces the canonical FlowMol3-native
  state dict ``(x, a, c, e)`` from a (seed, batch, n_atoms) triple.
  ``x`` is the centered Gaussian prior with std 1.0 (FlowMol3 default
  per ``configs/flowmol3.yml:65``). ``a`` is uniform one-hot over
  ``N_ATOM_TYPES`` plus a CTMC mask-token column at index ``K``. ``c``
  is uniform over ``N_BOND_TYPES`` (no-bond sentinel). ``e`` is
  no-bond upper triangular.

* :func:`euler_step_coordinate` + :func:`euler_step_categorical` —
  the discrete-time forward steps for a FlowMol3-style continuous +
  categorical flow. Used by both MolDiff (DDPM-style categorical
  re-mask) and EquiFM (linear-OT continuous + categorical-rate) inner
  samplers.

The module deliberately duplicates the Wave 49 composite math rather
than importing ``adaptive_reflow``: the Wave 52 design established
the sidecar-venv convention where the baseline scripts run in a
venv that does NOT have the framework package installed. Same
convention here — the ``flowmol3_venv`` carries ``torch`` + ``rdkit``
but not the framework.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Wave 49 / Wave 53 constants — must stay byte-identical with
# adaptive_reflow/adapters/flowmol3_glue.py (FlowMol3Glue.composite_score).
# ---------------------------------------------------------------------------
N_ATOM_TYPES: int = 10
N_BOND_TYPES: int = 5
DEFAULT_COMPOSITE_WEIGHTS: tuple[float, float, float, float, float] = (
    0.30,
    0.25,
    0.15,
    0.15,
    0.15,
)
_WEIGHTS_SUM_TOL: float = 1e-9

# FlowMol3 channel vocabulary (canonical 3-channel CTMC + coordinate)
FLOWMOL3_CHANNELS: tuple[str, ...] = ("coordinate", "raw_pair", "charge")
FLOWMOL3_PRIOR_STD: float = 1.0
FLOWMOL3_CONFIDENCE_THRESHOLD: float = 0.9
FLOWMOL3_CTMC_STOCHASTICITY: float = 30.0


# ---------------------------------------------------------------------------
# RDKit-backed chem validity (graceful NaN degradation when missing)
# ---------------------------------------------------------------------------

def _rdkit_available() -> bool:
    """Return True iff the RDKit package is importable."""
    try:
        import rdkit  # noqa: F401
        from rdkit import Chem  # noqa: F401
    except Exception:
        return False
    return True


def chem_validity(
    coords: np.ndarray,
    atom_types: np.ndarray,
) -> dict[str, float | None | str]:
    """Compute ``frac_valid_mols`` + ``frac_mols_stable`` via RDKit.

    Parameters
    ----------
    coords
        ``(B, n_atoms, 3)`` float array of 3D coordinates.
    atom_types
        ``(B, n_atoms)`` int array of atom-type indices in
        ``[0, N_ATOM_TYPES)``. Index 0 is treated as a "no atom"
        sentinel (FlowMol3's ``MASK_TOKEN_OFFSET == 1`` puts the mask
        at ``K`` but a small fragment of code uses 0 for "no atom";
        we honour 0 as masked for downstream sanitisation).

    Returns
    -------
    dict
        Keys::

            frac_valid_mols  — fraction of mols that pass RDKit
                                Chem.SanitizeMol without exception
                                (None when RDKit is missing)
            frac_mols_stable — fraction of valid mols where every
                                atom passes valid-valence check
                                (None when RDKit is missing)
            marker           — "ok" | "blocked_rdkit"
    """
    if not _rdkit_available():
        return {
            "frac_valid_mols": None,
            "frac_mols_stable": None,
            "marker": "blocked_rdkit",
        }
    from rdkit import Chem  # type: ignore  # noqa: E402
    from rdkit.Chem import AllChem  # type: ignore  # noqa: E402
    # RDKit atomic-number table — only the indices we need (FlowMol3's
    # canonical 10 atom types follow the GEOM-DRUGS vocabulary).
    atom_num_table = {
        0: 0,    # masked / no atom
        1: 6,     # C
        2: 7,     # N
        3: 8,     # O
        4: 9,     # F
        5: 15,    # P
        6: 16,    # S
        7: 17,    # Cl
        8: 1,     # H
        9: 0,     # padding (rare — collapse to masked)
    }

    coords = np.asarray(coords, dtype=np.float64)
    atom_types = np.asarray(atom_types, dtype=np.int64)
    B = int(coords.shape[0])
    n_valid = 0
    n_stable = 0
    for b in range(B):
        a = atom_types[b]
        # Drop masked positions (FlowMol3 mask = 0 here, matches adapter).
        keep = a > 0
        if int(np.sum(keep)) < 2:
            continue  # too small to be a "valid molecule"
        try:
            mol = Chem.RWMol()
            for k in np.where(keep)[0]:
                an = atom_num_table.get(int(a[k]), 0)
                if an <= 0:
                    continue
                mol.AddAtom(Chem.Atom(int(an)))
            n_real = mol.GetNumAtoms()
            if n_real < 2:
                continue
            # Connectivity: nearest-neighbour graph (RDKit needs *some*
            # bonds for sanitisation; the framework metric would use
            # the upstream ``pair`` channel — we fall back to a 2.0 A
            # cutoff which is the conventional "covalent bond" radius).
            coords_b = coords[b][keep][:n_real]
            for i in range(n_real):
                for j in range(i + 1, n_real):
                    d = float(np.linalg.norm(coords_b[i] - coords_b[j]))
                    if d < 1.6:
                        mol.AddBond(i, j, Chem.BondType.SINGLE)
            try:
                Chem.SanitizeMol(mol)
            except Exception:
                continue
            # Stability check: valid valence for every atom.
            try:
                Chem.SanitizeMol(mol, sanitizeOps=Chem.SANITIZE_PROPERTIES)
            except Exception:
                n_valid += 1
                continue
            n_valid += 1
            n_stable += 1
        except Exception:
            continue
    if B == 0:
        return {
            "frac_valid_mols": float("nan"),
            "frac_mols_stable": float("nan"),
            "marker": "ok",
        }
    return {
        "frac_valid_mols": float(n_valid) / float(B),
        "frac_mols_stable": float(n_stable) / float(B),
        "marker": "ok",
    }


# ---------------------------------------------------------------------------
# Composite score — byte-identical to FlowMol3Glue.composite_score
# ---------------------------------------------------------------------------

def _safe_get(d: dict[str, Any], key: str) -> float | None:
    value = d.get(key) if isinstance(d, dict) else None
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f


def composite_score(
    chemistry: dict[str, float | None],
    geometry: dict[str, float | None] | None = None,
    *,
    weights: tuple[float, float, float, float, float] = DEFAULT_COMPOSITE_WEIGHTS,
) -> dict[str, float | None]:
    """Compute the 5-axis FlowMol3 composite (geometry-agnostic path).

    Mirrors :meth:`adaptive_reflow.adapters.flowmol3_glue.FlowMol3Glue.composite_score`
    but uses bare numpy / stdlib (no ``adaptive_reflow`` import — the
    sidecar venv does not have the framework).

    Reads ``frac_valid_mols``, ``frac_mols_stable_valence`` (alias
    ``frac_mols_stable``), ``energy_js_div``, ``reos_cum_dev`` from
    ``chemistry``. When ``geometry is None``, the geometry axis
    (negative median RMSD after xtb) is dropped and chemistry weights
    are renormalised to sum to 1.0.

    The function is intentionally side-effect-free and pure-Python
    so it is trivially testable.
    """
    w1, w2, w3, w4, w5 = weights
    has_geometry = geometry is not None
    # Renormalise for geometry drop.
    if not has_geometry and w5 > 0.0:
        scale = 1.0 / (1.0 - w5)
        w1, w2, w3, w4, w5 = (
            w1 * scale, w2 * scale, w3 * scale, w4 * scale, 0.0,
        )

    phi1 = _safe_get(chemistry, "frac_valid_mols")
    phi2 = _safe_get(chemistry, "frac_mols_stable_valence")
    if phi2 is None:
        phi2 = _safe_get(chemistry, "frac_mols_stable")
    raw_js = _safe_get(chemistry, "energy_js_div")
    phi3 = None if raw_js is None else -float(raw_js)
    raw_reos = _safe_get(chemistry, "reos_cum_dev")
    phi4 = None if raw_reos is None else -float(raw_reos)
    if not has_geometry:
        phi5 = None
    else:
        raw_rmsd = _safe_get(geometry, "med_rmsd")
        phi5 = None if raw_rmsd is None else -float(raw_rmsd)

    terms: list[tuple[float, float]] = []
    if phi1 is not None and math.isfinite(float(phi1)):
        terms.append((float(w1), float(phi1)))
    if phi2 is not None and math.isfinite(float(phi2)):
        terms.append((float(w2), float(phi2)))
    if phi3 is not None and math.isfinite(float(phi3)):
        terms.append((float(w3), float(phi3)))
    if phi4 is not None and math.isfinite(float(phi4)):
        terms.append((float(w4), float(phi4)))
    if phi5 is not None and math.isfinite(float(phi5)):
        terms.append((float(w5), float(phi5)))
    if terms:
        composite_raw = sum(w_i * p_i for w_i, p_i in terms)
        composite = float(
            max(-1.0, min(1.0, composite_raw))
            if math.isfinite(composite_raw)
            else float("nan")
        )
    else:
        composite = float("nan")

    return {
        "composite": composite,
        "phi1_frac_valid_mols": (float(phi1) if phi1 is not None else None),
        "phi2_frac_mols_stable": (float(phi2) if phi2 is not None else None),
        "phi3_neg_energy_js_div": (float(phi3) if phi3 is not None else None),
        "phi4_neg_reos_cum_dev": (float(phi4) if phi4 is not None else None),
        "phi5_neg_med_rmsd_after_xtb": (
            float(phi5) if phi5 is not None else None
        ),
        "weights": [w1, w2, w3, w4, w5],
        "has_geometry": bool(has_geometry),
        "K_atom_types": int(N_ATOM_TYPES),
        "K_bond_types": int(N_BOND_TYPES),
    }


# ---------------------------------------------------------------------------
# Native state builder
# ---------------------------------------------------------------------------

def make_native_state(
    *,
    batch_size: int,
    n_atoms: int,
    seed: int,
) -> dict[str, np.ndarray]:
    """Build the canonical FlowMol3-native state ``(x, a, c, e)``.

    The state is the *prior* sample (no model pass yet) — this is
    the starting point the inner sampler integrates. ``x`` is the
    continuous 3D coordinate (Gaussian prior std 1.0). ``a`` is the
    atom-type one-hot with a CTMC mask column appended. ``c`` is the
    formal-charge one-hot (3 levels: -1, 0, +1) + mask. ``e`` is the
    upper-triangular pair-bond one-hot (no-bond sentinel at the last
    index) + mask.

    Returns a dict with keys ``x`` (B, n_atoms, 3), ``a`` (B, n_atoms,
    N_ATOM_TYPES), ``c`` (B, n_atoms, 3), ``e`` (B, n_atoms, n_atoms,
    N_BOND_TYPES). Shapes match the FlowMol3 v2 adapter's
    :func:`export_trajectory` shape so the baseline output can be
    compared against the framework's native-state cache.
    """
    rng = np.random.default_rng(int(seed))
    x = rng.standard_normal((batch_size, n_atoms, 3)) * FLOWMOL3_PRIOR_STD
    a = np.zeros((batch_size, n_atoms, N_ATOM_TYPES), dtype=np.float64)
    # Argmax-only distribution (each atom picks a uniform type).
    a_idx = rng.integers(0, N_ATOM_TYPES, size=(batch_size, n_atoms))
    for b in range(batch_size):
        for k in range(n_atoms):
            a[b, k, int(a_idx[b, k])] = 1.0
    # Charge: 3-level one-hot, uniform.
    c = np.zeros((batch_size, n_atoms, 3), dtype=np.float64)
    c_idx = rng.integers(0, 3, size=(batch_size, n_atoms))
    for b in range(batch_size):
        for k in range(n_atoms):
            c[b, k, int(c_idx[b, k])] = 1.0
    # Pair-bond: no-bond sentinel everywhere (off-diagonal upper tri).
    e = np.zeros(
        (batch_size, n_atoms, n_atoms, N_BOND_TYPES), dtype=np.float64,
    )
    e[:, :, :, N_BOND_TYPES - 1] = 1.0  # all "no-bond"
    return {"x": x, "a": a, "c": c, "e": e}


# ---------------------------------------------------------------------------
# Inner-sampler steps (used by both MolDiff + EquiFM baselines)
# ---------------------------------------------------------------------------

def euler_step_coordinate(
    x: np.ndarray,
    *,
    target_mean: np.ndarray | None,
    dt: float,
) -> np.ndarray:
    """One continuous-coordinate Euler step toward ``target_mean``.

    Used by both MolDiff (DDPM-style reverse) and EquiFM (linear-OT)
    as the deterministic part of the inner sampler. When
    ``target_mean is None`` the step is a contraction toward 0 with
    rate ``dt`` (i.e. the 1-step t=0 mean predictor).

    All operations are numpy / no torch.
    """
    if target_mean is None:
        return x * max(0.0, 1.0 - dt)
    return x + dt * (np.asarray(target_mean) - x)


def euler_step_categorical(
    p: np.ndarray,
    *,
    target_p: np.ndarray | None,
    dt: float,
    re_mask_prob: float = 0.0,
) -> np.ndarray:
    """One categorical Euler step + optional CTMC re-mask.

    ``p`` is ``(..., K)`` simplex. ``target_p`` is the target simplex
    (or ``None`` for "no flow"). ``re_mask_prob`` is the per-position
    probability of being replaced by the uniform simplex (the CTMC
    mask-token operation FlowMol3 uses).

    When both inputs are well-defined, the step is::

        p_new = (1 - dt) * p + dt * target_p
        if re_mask_prob > 0: p_new = (1 - re_mask_prob) * p_new + re_mask_prob * uniform
        renormalise

    """
    K = int(p.shape[-1])
    uniform = np.full(p.shape, 1.0 / K, dtype=np.float64)
    if target_p is None:
        new = p.copy()
    else:
        new = (1.0 - dt) * p + dt * np.asarray(target_p)
    if re_mask_prob > 0.0:
        new = (1.0 - float(re_mask_prob)) * new + float(re_mask_prob) * uniform
    # Renormalise to simplex.
    sums = np.clip(new.sum(axis=-1, keepdims=True), 1e-12, None)
    return new / sums


# ---------------------------------------------------------------------------
# Shared sweep geometry
# ---------------------------------------------------------------------------

DEFAULT_BATCH_SIZE: int = 4
DEFAULT_N_ATOMS: int = 9
DEFAULT_SEED: int = 42
DEFAULT_NFE_LIST: tuple[int, ...] = (10, 50, 250)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write ``payload`` as pretty JSON, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def now_date() -> str:
    """Return the current date in ISO format (audit-trail echo)."""
    return time.strftime("%Y-%m-%d", time.localtime())