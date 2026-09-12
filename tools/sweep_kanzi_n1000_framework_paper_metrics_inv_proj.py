#!/usr/bin/env python3
"""Wave 95 Phase 3.C — N=1000 framework paper-metric sweep via project_out⁻¹ bridge.

Mirrors :func:`tools.sweep_kanzi_n1000_framework_paper_metrics.main` but
**feeds the bridge a 512-d ``x_final``** (the framework trajectory endpoint
geometry — ``n_channels_decoder=512``, the post-``project_out`` space)
instead of the 64-d noise that the Wave 91 driver synthesises.

The Phase 3.B bridge (`tools.kanzi_latent_to_coord.kanzi_latent_to_coords`)
now strictly requires 512-d input because it routes through a *trained*
``Linear(512 → 4)`` inverse of ``project_out`` (see commit 378dc4a and
``tools/_kanzi_project_out_inv_train.py``). The Wave 91 sweep driver's
64-d noise synthesis pre-dates that wire — running it unchanged triggers
``RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x64 and 512x4)``
on every record.

This driver keeps the bridge + paper-metric + per-record logic identical
to the Wave 91 driver (so the only variable is the x_final shape, 64→512);
the change is local to this script and never touches
``tools/kanzi_latent_to_coord.py`` (Phase 3.B owns that file).

Output JSON mirrors
``verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json``
(per-arm Δ vs Wave 88 N=1000 baseline arm).

Wave 105 P1-A — the inner sweep loop is delegated to
:func:`tools._kanzi_sweep_runner.run_kanzi_sweep` (mode="framework_inv_proj",
projector="project_out_inv"). CLI surface (--help + JSON output contract)
is unchanged.

Run from the repo root with the kanzi sidecar venv::

    .venvs/kanzi_venv/bin/python \\
        tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py \\
        --input verification_outputs/kanzi_n1000_coords.txt \\
        --ckpt data/kanzi_ckpt/cleaned_model.pt \\
        --output-dir verification_outputs/kanzi_n1000_framework_paper_metrics_inv_proj
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo root must be on sys.path so ``tools.*`` imports resolve when the
# driver is invoked as a top-level script (mirrors the Wave 95 preamble).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools._kanzi_sweep_runner import (  # noqa: E402
    apply_kanzi_profile_defaults,
    run_kanzi_sweep,
    _run_kanzi_dry_run,
)
from tools.eval.config import load_run_profile  # noqa: E402


# Wave 113.A.5 Fix 2 — env-no-config gate exit code (matches the
# Autotools / sysexits.h convention: 78 = "configuration error").
# Returned when ``--dry-run`` is paired with ``--no-config`` to skip
# the shape contract probe (the caller is explicitly opting out of
# any config-driven dry-run verification).
_EXIT_ENV_NO_CONFIG = 78


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--config", type=Path, default=None,
                   help=("Wave 112.C-6: optional path to a run-profile YAML "
                         "(configs/runs/<model>_<purpose>.yaml). Loads the "
                         "schema in tools/eval/config.py; resolution order "
                         "CLI flag > YAML value > module default. Omitting "
                         "--config preserves the legacy CLI-default surface "
                         "byte-stable. Prints [PROFILE] summary on load."))
    p.add_argument("--input", type=Path, required=False,
                   help=("Wave 80 extractor output (one record per line). "
                         "Optional when --dry-run is set."))
    p.add_argument("--ckpt", type=Path,
                   default=Path(__file__).resolve().parent.parent
                                  / "data" / "kanzi_ckpt" / "cleaned_model.pt")
    p.add_argument("--output-dir", type=Path,
                   default=Path(__file__).resolve().parent.parent
                                  / "verification_outputs"
                                  / "kanzi_n1000_framework_paper_metrics_inv_proj")
    p.add_argument("--n-steps-decoder", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--limit", type=int, default=1000)
    p.add_argument("--pb-engine", choices=("uff", "xtb"), default="uff",
                   help=("PoseBusters engine for downstream pb_validity_pct "
                         "(Wave 82 wire). Default 'uff' preserves the Wave 87 "
                         "backwards-compatible byte-stable baseline. Wave 112.C-6 "
                         "(F-A001 / F-B002 closure): driver 3 (inv_proj) now "
                         "exposes --pb-engine; previously omitted (Wave 105 P0-B)."))
    p.add_argument("--adapter-force-mode", default="torch",
                   help=("KanziAdapter force_mode (Wave 111 F-A004 closure; "
                         "default 'torch' = real torch mode). One of "
                         "{torch, real, auto, synthetic}."))
    p.add_argument("--adapter-num-steps", type=int, default=50,
                   help="KanziAdapter ODE num_steps (Wave 111 F-A004 closure; default 50).")
    p.add_argument("--adapter-solver", default="euler",
                   help="KanziAdapter ODE solver (Wave 111 F-A004 closure; default 'euler').")
    # Wave 113.A.5 Fix 2 — dry-run flag for shape contract probe.
    p.add_argument("--dry-run", action="store_true",
                   help=("Wave 113.A.5 Fix 2: dry-run 1 record through "
                         "the full Kanzi protocol + call "
                         "assert_state_shape at each step. Exits 0 on "
                         "success; raises RuntimeError on shape "
                         "mismatch. Pairing with --no-config returns "
                         "exit 78 (SKIP, env-no-config gate)."))
    # Wave 113.A.5 Fix 2 — explicit opt-out flag for the
    # config-driven path.
    p.add_argument("--no-config", action="store_true",
                   help=("Wave 113.A.5 Fix 2: explicitly bypass any "
                         "config-driven code path. When combined with "
                         "--dry-run, exits 78 (env-no-config gate, "
                         "SKIP)."))
    args = p.parse_args(argv)
    # Enforce --input for the full sweep path (the dry-run bypass
    # does not need the input file).
    if not args.dry_run and args.input is None:
        print("[ERROR] --input is required when --dry-run is not set",
              file=sys.stderr)
        return 2
    profile = None
    if args.config is not None:
        try:
            profile = load_run_profile(args.config)
        except Exception as exc:  # ConfigError + OSError + yaml.YAMLError
            print(f"[ERROR] --config load failed: {exc}", file=sys.stderr)
            return 2
        args = apply_kanzi_profile_defaults(args, p, profile)

    # Wave 113.A.5 Fix 2 — handle --dry-run BEFORE entering the full
    # sweep. --dry-run --no-config → exit 78 (SKIP). --dry-run →
    # construct adapter + run 1 record through the protocol.
    if args.dry_run:
        if args.no_config:
            print(
                "[kanzi-dry-run] --dry-run --no-config → exit "
                f"{_EXIT_ENV_NO_CONFIG} (SKIP, env-no-config gate).",
                file=sys.stderr,
            )
            return _EXIT_ENV_NO_CONFIG
        return _run_kanzi_dry_run(
            ckpt_path=args.ckpt,
            adapter_force_mode=str(args.adapter_force_mode),
            adapter_num_steps=int(args.adapter_num_steps),
            adapter_solver=str(args.adapter_solver),
            seed=int(args.seed),
        )

    run_kanzi_sweep(
        mode="framework_inv_proj",
        projector="project_out_inv",
        output_dir=str(args.output_dir),
        seed=int(args.seed),
        max_records=int(args.limit),
        nfe_steps=int(args.n_steps_decoder),
        input_path=args.input,
        ckpt_path=args.ckpt,
        pb_engine=str(args.pb_engine),
        adapter_force_mode=str(args.adapter_force_mode),
        adapter_num_steps=int(args.adapter_num_steps),
        adapter_solver=str(args.adapter_solver),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
