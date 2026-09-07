#!/usr/bin/env python3
"""Wave 54 Phase 2 — FlowMol3 baseline #2: EquiFM-style linear-OT flow.

EquiFM (Song et al. 2023, ICLR) is the closest *flow-matching*
predecessor to FlowMol3. Both use SE(3)-equivariant continuous-time
coupling; EquiFM is *not* CTMC (it uses the linear-interpolant OT
path), while FlowMol3 wraps a CTMC around the categorical channels.
Running EquiFM as a baseline lets the framework make the precise
"FlowMol3's CTMC parameterisation adds value over a straight
continuous-time flow-matching baseline" argument.

This script reproduces the *inference-loop pattern* of EquiFM on the
same composite axis as the framework:

  * Linear-OT interpolant ``x_t = (1 - t) * x_0 + t * x_1`` is
    integrated forward from ``t=0`` to ``t=1`` in ``NFE`` Euler
    steps. The "denoiser" is replaced by a deterministic
    contraction toward the *prior* — same convention as the MolDiff
    baseline.
  * Categorical channels use the FlowMatching-style rate matrix
    (no CTMC re-mask): ``p_t = (1 - t) * one_hot(p_0) + t *
    one_hot(p_1)`` where ``p_0`` is uniform + mask.

Run with::

    .venvs/flowmol3_venv/bin/python scripts/baselines/run_flowmol3_baseline_equifm.py \\
        --nfe-list 10,50,250 \\
        --output verification_outputs/flowmol3_baseline_equifm_q4_2026.json

Like the MolDiff baseline, this runs in *synthetic-mode*: no EquiFM
ckpt is loaded (none is in this sandbox — e3nn + EquiFM repo are not
present). The composite is therefore an *inference-loop pattern*
measure on the same ``(x, a, c, e)`` prior state the framework's
FlowMol3 adapter starts from — not a paper-parity reproduction.
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
        "--contract-rate", type=float, default=0.05,
        help="Per-step coordinate contraction rate toward the data mean "
             "(EquiFM linear-OT analogue; with no denoiser this is the "
             "no-model flow direction).",
    )
    p.add_argument(
        "--output", type=str,
        default=str(
            REPO_ROOT / "verification_outputs"
            / "flowmol3_baseline_equifm_q4_2026.json"
        ),
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    nfe_list = [int(x) for x in args.nfe_list.split(",") if x.strip()]
    out_path = Path(args.output)

    print("[BASELINE 2/2] EquiFM-style linear-OT on FlowMol3 prior")
    print(
        f"  geometry: B={args.batch_size} n_atoms={args.n_atoms} "
        f"K_atom={N_ATOM_TYPES} seed={args.seed}"
    )
    print(f"  NFE list: {nfe_list}")
    print(f"  contract_rate={args.contract_rate}")

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
    e_start_flat = e_start.reshape(
        args.batch_size, args.n_atoms * args.n_atoms, -1,
    )

    # The linear-OT endpoint (target distribution at t=1): a fixed
    # chemistry-correct *prior collapse* — the categorical simplex
    # collapses to a single carbon-atom-type (C, type 1 in the FlowMol3
    # vocabulary) and the coordinate target is a tight cluster around
    # origin. This is the "no denoiser, but consistent with the
    # training distribution" target — it gives a non-trivial composite
    # that the MolDiff baseline (uniform collapse) does not.
    target_a = np.zeros_like(a_start)
    target_a[..., 1] = 1.0  # canonical C (FlowMol3 atom type 1)
    target_c = np.zeros_like(c_start)
    target_c[..., 1] = 1.0  # neutral formal charge (index 1)
    target_e_flat = np.zeros_like(e_start_flat)
    target_e_flat[..., -1] = 1.0  # all no-bond (FlowMol3 sentinel)
    target_x = x_start * 0.1  # tight cluster around origin (5x contraction)

    # --- (2) Per-NFE EquiFM-style linear-OT Euler step + composite.
    cells: list[dict] = []
    for nfe in nfe_list:
        t0 = time.time()
        x = x_start.copy()
        a = a_start.copy()
        c = c_start.copy()
        e_flat = e_start_flat.copy()
        dt = 1.0 / float(nfe)
        for s in range(nfe):
            # Linear-OT continuous: Euler toward target.
            x = euler_step_coordinate(x, target_mean=target_x, dt=dt)
            # Linear-OT categorical: Euler toward target simplex.
            # EquiFM has NO CTMC re-mask — categorical channels just
            # track the linear-OT flow. Setting re_mask_prob=0 is the
            # principled distinction from MolDiff.
            a = euler_step_categorical(
                a, target_p=target_a, dt=dt, re_mask_prob=0.0,
            )
            c = euler_step_categorical(
                c, target_p=target_c, dt=dt, re_mask_prob=0.0,
            )
            e_flat = euler_step_categorical(
                e_flat, target_p=target_e_flat, dt=dt, re_mask_prob=0.0,
            )
        elapsed = time.time() - t0

        # --- (3) Compute the chemistry + composite on the endpoint.
        a_idx = np.argmax(a, axis=-1).astype(np.int64)
        e_end = e_flat.reshape(args.batch_size, args.n_atoms, args.n_atoms, -1)
        chem = chem_validity(coords=x, atom_types=a_idx)

        if chem["marker"] == "blocked_rdkit":
            chemistry = {
                "frac_valid_mols": None,
                "frac_mols_stable_valence": None,
                "energy_js_div": None,
                "reos_cum_dev": None,
            }
        else:
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

        a_argmax_start = np.argmax(a_start, axis=-1)
        a_argmax_end = np.argmax(a, axis=-1)
        argmax_change_rate = float(
            np.mean(a_argmax_start != a_argmax_end),
        )

        cells.append(
            {
                "nfe_budget": nfe,
                "method": "equifm_linear_ot",
                "elapsed_seconds": round(elapsed, 3),
                "re_mask_prob": 0.0,
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
        "baseline": "equifm_linear_ot",
        "wave": 54,
        "agent": "B",
        "task": "flowmol3_tier3_baseline_comparison",
        "date": now_date(),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy_version": np.__version__,
            "rdkit_available": bool(cells[-1]["chemistry_marker"] != "blocked_rdkit"),
            "device_used": "cpu",
            "venv": ".venvs/flowmol3_venv",
        },
        "model": {
            "class": "scripts.baselines._flowmol3_helpers.make_native_state",
            "ckpt_path": None,
            "ckpt_keys_matched": 0,
            "ckpt_marker": "synthetic_mode_no_equifm_ckpt_in_sandbox",
            "paper_reference": "Song et al. 2023, ICLR (EquiFM)",
            "upstream_url": "https://github.com/hanjq17/EquiFM",
            "upstream_marker": (
                "EquiFM ckpt + e3nn + EquiFM repo are not in this "
                "sandbox; baseline runs in synthetic-mode (linear-OT "
                "Euler step on the same prior state as MolDiff "
                "baseline, with target = FlowMol3-vocabulary carbon "
                "atom + tight coordinate cluster)."
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
            "linear_ot_target": {
                "atom_type": "C (FlowMol3 type 1)",
                "formal_charge": "neutral (index 1)",
                "pair_bond": "no-bond (FlowMol3 sentinel)",
                "coordinate_amplitude": 0.1,
            },
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
                "gives 0.0). The EquiFM baseline reports the same "
                "composite axis with synthetic-mode chemistry "
                "proxies; the *delta vs framework* is "
                "framework-only-meaningful when the framework "
                "composite metric is unblocked (deferred to a later "
                "wave — see docs/audit/wave54-review-b-flowmol3-baselines.md)."
            ),
        },
        "limitations": [
            "Synthetic-mode baseline: no EquiFM ckpt loaded. The "
            "EquiFM-style linear-OT step uses a deterministic "
            "contraction toward a hand-picked chemistry-correct target "
            "(C atom + no-bond + tight coordinate cluster), not the "
            "upstream EquiFM SE(3) flow.",
            "Composite axis uses self-relative chemistry proxies "
            "(atom-type deviation from uniform + coordinate variance "
            "ratio) when RDKit is available; NaN when RDKit is "
            "missing.",
            "Categorical channels use a hand-picked target simplex "
            "(C + neutral + no-bond). This is the principled "
            "no-denoiser target for *flow-matching* — uniform is the "
            "no-denoiser target for *diffusion*. The EquiFM baseline "
            "therefore reports a strictly *less* uniform categorical "
            "endpoint than the MolDiff baseline, which is the "
            "intended qualitative distinction.",
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