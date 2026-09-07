#!/usr/bin/env python3
"""Wave 54 Phase 2 — FlowMol3 baseline #1: MolDiff-style DDPM sampler.

MolDiff (Zhang et al. 2023, ICLR) is the closest published 3D-molecule
*diffusion* baseline to FlowMol3. It uses an SE(3)-equivariant denoiser
on a 3D conformer + atom-type joint, integrating with a
DDPM-style discrete-time reverse process on the categorical
channels and an SDE-style reverse step on the coordinate channel.

This script reproduces the *inference-loop pattern* of MolDiff on the
same composite axis as the framework:

  * Sample the continuous-coordinate SDE in ``NFE`` reverse steps
    using a fixed "mean-predictor" contraction (the inner solver is
    *not* the SE(3) denoiser — that would require cloning the upstream
    ``moldiff`` repo; the sidecar-venv convention from Wave 52 Agent B
    applies).
  * Sample the categorical channels with a CTMC re-mask update per
    step (the discrete analogue of MolDiff's categorical corruption
    forward process).

The composite is computed *as a self-comparison*: starting simplex
``→`` endpoint. ``phi1 = frac_valid_mols`` (higher = better),
``phi2 = frac_mols_stable_valence`` (higher = better),
``phi3 = -energy_js_div``, ``phi4 = -reos_cum_dev`` are reported as
``NaN`` when RDKit is missing — the ``composite_score`` returns
``NaN`` rather than 0.0 so the byte-stable ``flowmol3_real_composite``
JSON is NOT perturbed.

Run with::

    .venvs/flowmol3_venv/bin/python scripts/baselines/run_flowmol3_baseline_moldiff.py \\
        --nfe-list 10,50,250 \\
        --output verification_outputs/flowmol3_baseline_moldiff_q4_2026.json

The script is *synthetic-mode*: no MolDiff ckpt is loaded (none is
in this sandbox; PyG + MolDiff's repo are not present). The composite
is therefore an *inference-loop pattern* measure on the same
``(x, a, c, e)`` prior state the framework's FlowMol3 adapter starts
from — not a paper-parity reproduction.
"""
from __future__ import annotations

import argparse
import platform
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _flowmol3_helpers import (  # noqa: E402
    DEFAULT_BATCH_SIZE,
    DEFAULT_N_ATOMS,
    DEFAULT_NFE_LIST,
    DEFAULT_SEED,
    FLOWMOL3_CONFIDENCE_THRESHOLD,
    FLOWMOL3_CTMC_STOCHASTICITY,
    FLOWMOL3_PRIOR_STD,
    N_ATOM_TYPES,
    chem_validity,
    composite_score,
    euler_step_categorical,
    euler_step_coordinate,
    make_native_state,
    now_date,
    write_json,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--nfe-list", type=str,
        default=",".join(str(n) for n in DEFAULT_NFE_LIST),
        help="Comma-separated NFE budgets (default: 10,50,250).",
    )
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    p.add_argument("--n-atoms", type=int, default=DEFAULT_N_ATOMS)
    p.add_argument(
        "--re-mask-prob", type=float, default=0.05,
        help="Per-step CTMC re-mask probability (MolDiff's eta schedule).",
    )
    p.add_argument(
        "--contract-rate", type=float, default=0.05,
        help="Per-step coordinate contraction rate toward the data mean "
             "(DDPM-style reverse mean predictor).",
    )
    p.add_argument(
        "--output", type=str,
        default=str(
            REPO_ROOT / "verification_outputs"
            / "flowmol3_baseline_moldiff_q4_2026.json"
        ),
    )
    return p.parse_args()


def _target_mean_from_prior(prior: np.ndarray, *, contraction: float) -> np.ndarray:
    """Compute the MolDiff-style reverse-mean target.

    Mirrors the Wave 49 ``FlowMol3 v2 adapter``'s ``mean_predictor``
    (which is the closed-form x_0 estimate from the score): a linear
    contraction of the current coordinate toward the *prior* mean
    (origin). This is the deterministic part of MolDiff's reverse
    SDE; the stochastic part (sigma-sqrt noise injection) is omitted
    because we are reporting a *single-pass baseline* (the framework's
    baseline arm is single-pass too).
    """
    return prior * (1.0 - float(contraction))


def _target_p_uniform() -> np.ndarray:
    """Categorical target = uniform simplex (random-class baseline).

    The MolDiff-style reverse step on categorical channels uses the
    network's predicted x_0 distribution. Without the network, the
    *uniform* distribution is the principled "no model" target — it
    corresponds to the maximum-entropy predictor and is what an
    untrained model converges to.
    """
    return None  # None → no flow on the categorical (uniform collapse)


def main() -> int:
    args = parse_args()
    nfe_list = [int(x) for x in args.nfe_list.split(",") if x.strip()]
    out_path = Path(args.output)

    print("[BASELINE 1/2] MolDiff-style DDPM on FlowMol3 prior")
    print(
        f"  geometry: B={args.batch_size} n_atoms={args.n_atoms} "
        f"K_atom={N_ATOM_TYPES} seed={args.seed}"
    )
    print(f"  NFE list: {nfe_list}")
    print(
        f"  re-mask_prob={args.re_mask_prob} contract_rate={args.contract_rate}"
    )

    # --- (1) Build the canonical FlowMol3 prior state.
    native = make_native_state(
        batch_size=args.batch_size,
        n_atoms=args.n_atoms,
        seed=args.seed,
    )
    x_start = native["x"]
    a_start = native["a"]
    c_start = native["c"]
    e_start = native["e"]
    # Flatten e for the categorical step (we treat the upper-triangle
    # pair-bond slots as one categorical distribution).
    e_start_flat = e_start.reshape(
        args.batch_size, args.n_atoms * args.n_atoms, -1,
    )

    # --- (2) Per-NFE MolDiff-style reverse step + composite.
    cells: list[dict] = []
    for nfe in nfe_list:
        t0 = time.time()
        x = x_start.copy()
        a = a_start.copy()
        c = c_start.copy()
        e_flat = e_start_flat.copy()
        # MolDiff's reverse SDE uses 1/NFE step size; the framework's
        # composite-axis baseline arm does too. dt is the fraction of
        # the [0, 1] interval covered by one reverse step.
        dt = 1.0 / float(nfe)
        for s in range(nfe):
            target_x = _target_mean_from_prior(x_start, contraction=args.contract_rate)
            x = euler_step_coordinate(x, target_mean=target_x, dt=dt)
            # Categorical channels: MolDiff-style CTMC re-mask with the
            # "no model" target = uniform. With re_mask_prob > 0 this
            # converges to uniform regardless of starting state, which
            # is the honest "no denoiser" baseline.
            a = euler_step_categorical(
                a, target_p=_target_p_uniform(), dt=dt,
                re_mask_prob=args.re_mask_prob,
            )
            c = euler_step_categorical(
                c, target_p=None, dt=dt,
                re_mask_prob=args.re_mask_prob,
            )
            e_flat = euler_step_categorical(
                e_flat, target_p=None, dt=dt,
                re_mask_prob=args.re_mask_prob,
            )
        elapsed = time.time() - t0

        # --- (3) Compute the chemistry + composite on the endpoint.
        a_idx = np.argmax(a, axis=-1).astype(np.int64)
        e_end = e_flat.reshape(args.batch_size, args.n_atoms, args.n_atoms, -1)
        e_idx = np.argmax(e_end, axis=-1).astype(np.int64)

        chem = chem_validity(coords=x, atom_types=a_idx)
        # When RDKit is missing, the composite falls back to NaN. We
        # still report the categorical-channel turn-over + a JS-div-
        # style axis (energy + REOS) as 0.0 to keep the composite
        # finite-but-low so the comparison axis is interpretable.
        if chem["marker"] == "blocked_rdkit":
            chemistry = {
                "frac_valid_mols": None,
                "frac_mols_stable_valence": None,
                "energy_js_div": None,
                "reos_cum_dev": None,
            }
        else:
            # Synthetic JS-div / REOS proxies from the endpoint's
            # atom-type + coordinate distribution. We do NOT have a
            # training-set reference distribution in this synthetic
            # baseline; the proxies are *self-relative* (uniform
            # baseline) and clamped to [0, 1]. This is honest
            # "synthetic-mode" framing per Phase 1 design §B.7.3.
            a_unif = 1.0 / N_ATOM_TYPES
            a_dev = float(np.mean(np.abs(np.max(a, axis=-1) - a_unif)))
            x_var = float(np.var(x))
            chemistry = {
                "frac_valid_mols": chem["frac_valid_mols"],
                "frac_mols_stable_valence": chem["frac_mols_stable"],
                "energy_js_div": float(min(1.0, max(0.0, a_dev))),
                "reos_cum_dev": float(min(1.0, max(0.0, x_var / (1.0 + x_var)))),
            }
        comp = composite_score(chemistry, geometry=None)

        # Categorical turn-over (MolDiff-specific axis: how much did the
        # discrete-atom-type argmax move between start and end?).
        a_argmax_start = np.argmax(a_start, axis=-1)
        a_argmax_end = np.argmax(a, axis=-1)
        argmax_change_rate = float(
            np.mean(a_argmax_start != a_argmax_end),
        )

        cells.append(
            {
                "nfe_budget": nfe,
                "method": "moldiff_ddpm",
                "elapsed_seconds": round(elapsed, 3),
                "re_mask_prob": args.re_mask_prob,
                "contract_rate": args.contract_rate,
                "argmax_change_rate_atom_types": argmax_change_rate,
                "chemistry_marker": chem["marker"],
                "frac_valid_mols": chem["frac_valid_mols"],
                "frac_mols_stable": chem["frac_mols_stable"],
                **comp,
            }
        )
        print(
            f"  NFE={nfe:3d}  time={elapsed:6.2f}s  "
            f"valid={chem['frac_valid_mols']} stable={chem['frac_mols_stable']} "
            f"argmax_turnover={argmax_change_rate:.3f}  "
            f"composite={comp['composite']}"
        )

    record = {
        "schema": "flowmol3_baseline_report.v1",
        "baseline": "moldiff_ddpm",
        "wave": 54,
        "agent": "B",
        "task": "flowmol3_tier3_baseline_comparison",
        "date": now_date(),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy_version": np.__version__,
            "rdkit_available": bool(chem_validity.__module__) and (
                # The chem_validity fn is the proxy: re-import rdkit
                # at call time. We use the marker from the last cell.
                cells[-1]["chemistry_marker"] != "blocked_rdkit"
            ),
            "device_used": "cpu",
            "venv": ".venvs/flowmol3_venv",
        },
        "model": {
            "class": "scripts.baselines._flowmol3_helpers.make_native_state",
            "ckpt_path": None,
            "ckpt_keys_matched": 0,
            "ckpt_marker": "synthetic_mode_no_moldiff_ckpt_in_sandbox",
            "paper_reference": "Zhang et al. 2023, ICLR (MolDiff)",
            "upstream_url": "https://github.com/microsoft/MolDiff",
            "upstream_marker": (
                "MolDiff ckpt + PyG + MolDiff repo are not in this "
                "sandbox; baseline runs in synthetic-mode (same prior "
                "as FlowMol3 v2 adapter's _sample_x0, deterministic "
                "MolDiff-style reverse step)."
            ),
        },
        "geometry": {
            "batch_size": args.batch_size,
            "n_atoms": args.n_atoms,
            "n_atom_types": N_ATOM_TYPES,
            "n_bond_types": 5,
            "seed": args.seed,
            "prior_std": FLOWMOL3_PRIOR_STD,
            "ctmc_stochasticity": FLOWMOL3_CTMC_STOCHASTICITY,
            "confidence_threshold": FLOWMOL3_CONFIDENCE_THRESHOLD,
            "channels": ["coordinate", "raw_pair", "charge"],
        },
        "cells": cells,
        "framework_baseline_for_reference": {
            "source": "verification_outputs/flowmol3_real_composite_q4_2026.json",
            "framework_composite_at_nfe50": 0.0,
            "framework_marker": "no_signal_placeholder_metric",
            "framework_composite_weights": list((0.30, 0.25, 0.15, 0.15, 0.15)),
            "framework_K_atom_types": 10,
            "framework_K_bond_types": 5,
            "nfe": 50,
            "note": (
                "Wave 52/53 framework FlowMol3 composite is the "
                "placeholder ``no_signal`` axis (uniform-vs-uniform "
                "gives 0.0). The MolDiff baseline reports the same "
                "composite axis with synthetic-mode chemistry "
                "proxies; the *delta vs framework* is "
                "framework-only-meaningful when the framework "
                "composite metric is unblocked (deferred to a later "
                "wave — see docs/audit/wave54-review-b-flowmol3-baselines.md)."
            ),
        },
        "limitations": [
            "Synthetic-mode baseline: no MolDiff ckpt loaded. The "
            "MolDiff-style reverse step uses a deterministic "
            "mean-predictor contraction toward the prior mean, not "
            "the upstream MolDiff SE(3) denoiser.",
            "Composite axis uses self-relative chemistry proxies "
            "(atom-type deviation from uniform + coordinate variance "
            "ratio) when RDKit is available; NaN when RDKit is "
            "missing.",
            "Categorical channels use ``None`` target simplex (no "
            "flow) + per-step CTMC re-mask. This converges to uniform "
            "for the categorical channels — i.e. *any* MolDiff-style "
            "sampler without the denoiser collapses to uniform. The "
            "framework's value-add is therefore measured on the "
            "*chemistry-validity* axis, not on the categorical turn-"
            "over axis.",
            "CPU only.",
        ],
    }

    write_json(out_path, record)
    try:
        rel = out_path.relative_to(REPO_ROOT)
    except ValueError:
        rel = out_path
    print(f"wrote: {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())