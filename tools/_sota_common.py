"""Shared argparse preamble for the 8 ``tools/run_sota_*.py`` scripts.

The eight per-model SOTA-comparison drivers
(``run_sota_2d_experiment``, ``run_sota_cifar_experiment``,
``run_sota_comparison``, ``run_sota_flowmol3_v2_adapter_experiment``,
``run_sota_graphbfn_experiment``, ``run_sota_hidream_i1_experiment``,
``run_sota_lumina_image_2_0_experiment``,
``run_sota_protbfn_abbfn_adapter_experiment``,
``run_sota_wan2_2_video_experiment``) all open their ``argparse.ArgumentParser``
with the same two canonical flags — ``--output-dir`` (always ``type=Path``;
the per-script default varies; ``comparison`` + ``protbfn_abbfn`` mark it
``required=True``) and ``--seed`` (``type=int``, default ``0`` in five
scripts and ``42`` in ``run_sota_comparison``; absent in three scripts).

Prior to Wave 105 P1-C, each driver carried its own copy of the
``parser.add_argument("--output-dir", ...)`` and ``parser.add_argument(
"--seed", ...)`` blocks — ~200 LOC of boilerplate across the cluster.
This module centralizes those two flags into a single
:func:`add_sota_common_args` helper so each call site becomes one line.

Per-script flags (model-specific or workflow-specific — e.g. ``--n-mols``,
``--baseline-nfe``, ``--checkpoint``, ``--adapter-class``) stay in the
script-local parser so this helper does NOT touch them. Behaviour is
byte-identical to the inline block: same flag names, same types, same
defaults, same required/optional semantics.

Wave 101 audit doc: ``docs/audit/wave101-review-layer2-algorithm-tools.md``
Rank 5 + ``todo/planned/w101-fix-layer2-algorithm-tools.md`` Section 3 P1-C.
"""
from __future__ import annotations

import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared SOTA-comparison argparse preamble
# ---------------------------------------------------------------------------


#: Default seed for the five scripts that wire ``--seed``. Mirrors the
#: dominant pattern (``flowmol3_v2``, ``graphbfn``, ``hidream``, ``lumina``,
#: ``protbfn_abbfn``). ``run_sota_comparison`` overrides to ``42`` for
#: canonical 2D-FM reproducibility.
_DEFAULT_SEED: int = 0

#: Special-case seed for ``run_sota_comparison``: the canonical 2D-FM
#: reproducibility seed (matches ``DEFAULT_SEED`` in
#: ``run_sota_comparison.py``).
_COMPARISON_DEFAULT_SEED: int = 42


def add_sota_common_args(
    parser: argparse.ArgumentParser,
    *,
    output_dir_default: Path | None = None,
    output_dir_required: bool = False,
    seed_default: int = _DEFAULT_SEED,
    include_seed: bool = True,
) -> None:
    """Add the canonical SOTA-comparison flags (``--output-dir`` and ``--seed``).

    Every :mod:`tools.run_sota_*` driver opens with these two flags; this
    helper inserts them in the order the originals used
    (``--output-dir`` near the top of the cluster, ``--seed`` toward the
    end) so each script's ``--help`` output stays positionally familiar.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The parser to extend. The caller owns the
        :class:`argparse.ArgumentParser` itself (description, prog,
        formatter_class, etc.) — this helper only appends two flags.
    output_dir_default : Path | None
        Default value for ``--output-dir``. Ignored when
        ``output_dir_required=True`` (argparse then enforces
        ``required=True`` and rejects any default). Pass ``None``
        together with ``output_dir_required=False`` to omit the flag
        entirely (not used today; reserved for future scripts that
        stream to stdout).
    output_dir_required : bool
        When True, ``--output-dir`` is marked required and no default
        is set. Defaults to False. Used by ``run_sota_comparison``
        and ``run_sota_protbfn_abbfn_adapter_experiment``.
    seed_default : int
        Default value for ``--seed``. Defaults to ``0``; the
        ``run_sota_comparison`` driver passes ``42`` for canonical
        2D-FM reproducibility.
    include_seed : bool
        When True (default), register ``--seed``. Set False for the
        three scripts that omit the flag entirely
        (``run_sota_2d_experiment`` uses ``--n-seeds`` instead;
        ``run_sota_cifar_experiment`` threads seed=0 internally;
        ``run_sota_wan2_2_video_experiment`` is a stub that does not
        run any RNG chain).
    """
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=output_dir_default,
        required=output_dir_required,
        help=(
            "Output directory for the SOTA experiment: comparison.md, "
            "summary.json, and per-row sample artifacts are written here. "
            "Created if missing."
        ),
    )
    if include_seed:
        parser.add_argument(
            "--seed",
            type=int,
            default=seed_default,
            help=(
                "Master seed threaded through every random source the "
                "experiment touches (forward-noise injection, prior draws, "
                "scheduler-state init). Deterministic for fixed "
                "(adapter, weights, seed)."
            ),
        )


__all__: list[str] = [
    "add_sota_common_args",
]