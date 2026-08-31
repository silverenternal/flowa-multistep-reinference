"""SOTA GraphBFN baseline-vs-FlowA harness — molecular graph generation.

Wires the GraphBFN :class:`FlowMatchingODEAdapter` (the mechanics
adapter at :mod:`adaptive_reflow.adapters.graphbfn`) into a single-pass
baseline + FlowA multi-round framework comparison, then emits the
comparison JSON + markdown table. Sibling of
``tools/run_sota_flowmol3_v2_adapter_experiment.py``; same CLI shape,
same output schema, same eval bridge.

Layout
------

1. Baseline arm: ``--n-mols`` single-pass BFN integrations with
   ``--baseline-nfe`` Bayesian-update steps each (the paper-reported
   setting for QM9 / ZINC250k).
2. Framework arm: ``--n-mols`` chains x ``--n-rounds`` rounds. Each
   round runs ``build_initial_state`` (round 0) /
   ``apply_restart_distribution`` (rounds 1..N-1) -> ``compose_condition``
   -> ``solve_ode`` -> ``observe_endpoint`` with a ``--per-round-nfe``
   step budget driven by the cosine schedule's ``n_cap``. The t=1
   endpoint of the final round is the framework sample.
3. Each arm's molecule list is pickled as a
   ``(list[Chem.Mol | None], sampling_time)`` tuple (the on-disk format
   ``tools/run_mol_eval.py`` accepts), then a separate
   :mod:`tools.run_mol_eval` invocation computes the validity / QED / SA
   / logP / FCD metric panel.
4. A comparison ``summary.json`` + ``comparison.md`` table is emitted
   under ``--output-dir``.

Unlike the FlowMol3 sibling, the framework arm here DOES exercise
``apply_restart_distribution``: GraphBFN's per-channel blender draws its
fresh tensors at the prior's own shape
(``adaptive_reflow/adapters/graphbfn.py`` ``apply_restart_distribution``),
so it has no analogue of the FlowMol3 size-mismatch bug that forced that
harness to chain raw endpoints instead.

The framework row is launched with a single scheduler (the cosine
annealer) for the deterministic one-row Phase-A comparison, mirroring
the FlowMol3 harness and the single-arm protocol the 2D harness uses
when ``--schedulers`` is set to a single name.

Usage::

    # Quick smoke test (synthetic backend, 4 mols, 2 rounds).
    python tools/run_sota_graphbfn_experiment.py \\
        --weights synthetic --n-mols 4 --n-rounds 2 \\
        --output-dir /tmp/graphbfn_smoke

    # Full Phase-A run on synthetic (production needs weights).
    python tools/run_sota_graphbfn_experiment.py \\
        --weights data/graphbfn/graphbfn_qm9.pt --dataset qm9 \\
        --n-mols 100 --n-rounds 5 --baseline-nfe 100 \\
        --output-dir data/graphbfn_out

NON-CLAIM: the GraphBFN torch loader
(:func:`adaptive_reflow.adapters.graphbfn._load_torch_bfn`) still raises
``NotImplementedError`` — the published checkpoints are not in
``data/graphbfn/`` (``weights_metadata.json`` status='failed', and the
clone holds only a README). The adapter therefore runs its synthetic
NumPy BFN update loop, whose own docstring says it "is NOT a
reproduction of the ICLR-2025 / Hierarchical GraphBFN papers". On top of
that, the element-symbol vocabulary used by the decoder is authored in
:mod:`adaptive_reflow.molecular.rdkit_export` rather than read off a
checkpoint. The Phase-A headline claim of this script is therefore the
re-inference plumbing parity (single-pass vs multi-round reach the same
endpoint shape through the full Protocol surface), NOT a chemistry
claim. Validity will sit near zero on both arms until real weights and
a real vocabulary land.
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

# Make the project importable when running as
# ``python tools/run_sota_graphbfn_experiment.py``.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default baseline NFE. The GraphBFN paper reports ~1000 BFN updates on
#: QM9 and ~500 on ZINC250k; 100 is the harness default so a Phase-A run
#: on the synthetic backend finishes in seconds. Production callers
#: should raise this to the paper-reported budget.
DEFAULT_BASELINE_NFE: int = 100

#: Default output directory.
DEFAULT_OUTPUT_DIR: Path = REPO_ROOT / "data" / "graphbfn_out"

#: Default FCD reference SMILES (per-dataset). FCD is NaN when the file
#: is absent, which is the expected Phase-A state.
DEFAULT_REFERENCE_SMILES: Path = REPO_ROOT / "data" / "qm9_reference.smi"

#: Output JSON metric keys (kept identical to the FlowMol3 harness so a
#: downstream consumer can parse both with one code path).
METRIC_KEYS: tuple[str, ...] = (
    "validity",
    "qed",
    "sa",
    "logp",
    "fcd",
)

#: Schema version for the comparison JSON. Matches the FlowMol3 harness.
OUTPUT_SCHEMA_VERSION: str = "1.0.0"


# ---------------------------------------------------------------------------
# Adapter factory
# ---------------------------------------------------------------------------


def _make_adapter(
    weights: Path | None,
    *,
    dataset: str,
    variant: str,
    baseline_nfe: int,
) -> Any:
    """Return a :class:`GraphBFNAdapter` for the experiment.

    ``weights=None`` (or the literal sentinel ``"synthetic"``) forces
    the synthetic NumPy BFN backend. Any other path is forwarded as the
    adapter's ``weights_path`` with ``force_mode="auto"``, which selects
    torch when both the file and :mod:`torch` are present. Note that the
    adapter's own ``__init__`` swallows the loader's
    ``NotImplementedError`` and downgrades to synthetic, so a checkpoint
    path is currently accepted but not honoured; the resulting mode is
    reported in ``summary.json`` so the operator can see which path ran.
    """
    from adaptive_reflow.adapters.graphbfn import GraphBFNAdapter

    use_weights = weights is not None and str(weights) != "synthetic"
    if not use_weights:
        return GraphBFNAdapter(
            variant=variant,  # type: ignore[arg-type]
            dataset=dataset,  # type: ignore[arg-type]
            num_steps=int(baseline_nfe),
            force_mode="synthetic",
        )
    weights_path = Path(weights)  # type: ignore[arg-type]
    if not weights_path.exists():
        raise FileNotFoundError(f"graphbfn_weights_not_found:{weights_path}")
    try:
        return GraphBFNAdapter(
            variant=variant,  # type: ignore[arg-type]
            dataset=dataset,  # type: ignore[arg-type]
            num_steps=int(baseline_nfe),
            weights_path=weights_path,
            force_mode="auto",
        )
    except (ImportError, RuntimeError) as exc:
        print(
            f"[run_sota_graphbfn] torch_backend_unavailable:{exc}; falling "
            "back to the synthetic NumPy BFN backend (production requires "
            "torch and the published GraphBFN checkpoint)",
            file=sys.stderr,
            flush=True,
        )
        return GraphBFNAdapter(
            variant=variant,  # type: ignore[arg-type]
            dataset=dataset,  # type: ignore[arg-type]
            num_steps=int(baseline_nfe),
            force_mode="synthetic",
        )


def _adapter_mode(adapter: Any) -> str:
    """Return the adapter's operating mode for the summary metadata.

    Read off the private ``_mode`` attribute because the adapter exposes
    no public accessor; this is metadata for the JSON only and never
    feeds a decision.
    """
    return str(getattr(adapter, "_mode", "unknown"))


# ---------------------------------------------------------------------------
# Glue: late-imported so this module stays importable in a venv without
# rdkit (the harness then emits a parseable JSON with NaN metrics).
# ---------------------------------------------------------------------------


def _glue_module() -> Any:
    """Late-import :mod:`adaptive_reflow.molecular.rdkit_export`.

    Returns ``None`` when rdkit is unavailable so the harness can emit a
    parseable JSON with NaN metrics instead of failing at import time.
    """
    try:
        from adaptive_reflow.molecular import rdkit_export
    except ImportError as exc:
        print(
            f"[run_sota_graphbfn] rdkit_export_unavailable:{exc}",
            file=sys.stderr,
            flush=True,
        )
        return None
    return rdkit_export


def _pickle_mols(path: Path, mols: list[Any | None], wall: float) -> None:
    """Write ``(mols, sampling_time)`` in the format run_mol_eval accepts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        pickle.dump((list(mols), float(wall)), fh)


# ---------------------------------------------------------------------------
# Baseline + framework runners
# ---------------------------------------------------------------------------


def _run_baseline(
    *,
    adapter: Any,
    n_mols: int,
    baseline_nfe: int,
    seed: int,
    dataset: str,
    condition_kind: str,
    property_value: float | None,
    output_dir: Path,
) -> tuple[Path, float, list[Any | None]]:
    """Run the single-pass baseline; pickle ``(mols, sampling_time)``.

    Returns ``(pkl_path, wall_clock_s, mols_list)``. Entries the glue
    could not convert to RDKit stay ``None`` so the validity denominator
    still counts them (matching the FlowMol3 harness convention).
    """
    from adaptive_reflow.universal.state import ODEConditionDelta

    glue = _glue_module()
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    mols: list[Any | None] = []
    for i in range(int(n_mols)):
        bundle = adapter.build_initial_state(
            batch_id=f"graphbfn-baseline-{seed}",
            sample_id=f"sample-{i}",
        )
        spec: dict[str, Any] = {
            "num_steps": int(baseline_nfe),
            "condition_kind": str(condition_kind),
        }
        if property_value is not None:
            spec["property_value"] = float(property_value)
        condition = adapter.compose_condition(
            bundle,
            ODEConditionDelta(
                delta_spec=spec,
                source="run_sota_graphbfn.baseline",
                target_round=0,
                calibration_artifact_hash="graphbfn-baseline",
            ),
        )
        trace = adapter.solve_ode(bundle, condition, seed=int(seed) + i)
        if glue is None:
            mols.append(None)
            continue
        mols.append(
            glue.graphbfn_endpoint_to_rdkit_mol(adapter, trace, dataset=dataset)
        )
    wall = float(time.perf_counter() - started)
    pkl_path = output_dir / "baseline_molecules.pkl"
    _pickle_mols(pkl_path, mols, wall)
    return pkl_path, wall, mols


def _framework_policy(
    *,
    schedule_sample: Any,
    sample_index: int,
    round_index: int,
) -> Any:
    """Build the per-round :class:`FinalRestartPolicy` for a framework round.

    Every GraphBFN channel gets the same ``beta = 1 - memory_fraction``
    from the cosine schedule, ``alpha = 1``, and a zero fresh-noise
    floor — the deterministic one-row Phase-A setting. The policy hash
    is recomputed after construction so the adapter's restart-seed
    derivation (which hashes ``policy_hash``) is stable across runs.
    """
    from adaptive_reflow.adapters.graphbfn import GRAPHBFN_CHANNELS
    from adaptive_reflow.contracts import (
        ArtifactHash,
        ChannelName,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        MechanismId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )

    # ``GRAPHBFN_CHANNELS`` is typed with the ``universal.state``
    # ``ChannelName`` NewType while ``FinalRestartPolicy`` keys on the
    # ``contracts.types`` one. They are the same strings at runtime; the
    # re-wrap keeps the policy's declared key type honest.
    channels = tuple(ChannelName(str(ch)) for ch in GRAPHBFN_CHANNELS)
    memory_fraction = float(schedule_sample.memory_fraction())
    beta = FactorValue(1.0 - memory_fraction)
    policy = FinalRestartPolicy(
        policy_id=PolicyId(f"graphbfn-framework-{sample_index}-{round_index}"),
        writer_id=MechanismId("inference.adaptive_reflow.graphbfn"),
        run_id=RunId("graphbfn-framework"),
        target_round=int(round_index),
        outer_cycle_id=0,
        beta_by_channel={ch: beta for ch in channels},
        alpha_by_channel={ch: FactorValue(1.0) for ch in channels},
        fresh_noise_floor_by_channel={
            ch: FactorValue(0.0) for ch in channels
        },
        schedule_sample=schedule_sample.as_cosine_schedule_sample(),
        freeze_admission_by_channel={ch: True for ch in channels},
        ledger_row_id=LedgerRowId(
            f"graphbfn-framework-{sample_index}-{round_index}"
        ),
        policy_hash=ArtifactHash(""),
        created_at_round=int(round_index),
        beta_from_schedule=False,
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _run_framework(
    *,
    adapter: Any,
    n_mols: int,
    n_rounds: int,
    per_round_nfe: int,
    seed: int,
    dataset: str,
    condition_kind: str,
    property_value: float | None,
    output_dir: Path,
) -> tuple[Path, float, list[Any | None]]:
    """Run the FlowA multi-round framework; pickle the per-chain endpoint.

    Each chain runs ``n_rounds`` rounds of the full adapter Protocol
    surface — ``build_initial_state`` (round 0), ``compose_condition``,
    ``solve_ode``, ``observe_endpoint``, then
    ``apply_restart_distribution`` to carry state into the next round.
    The per-round step budget is ``round(n_cap * per_round_nfe)`` where
    ``n_cap`` comes from the cosine schedule.

    ``Engine.run_round`` is not used: its handshake requires
    ``has_materialization_route``, which
    :class:`GraphBFNCapabilities` declares ``False``
    (``adaptive_reflow/frame/engine.py`` capability loop). The loop here
    still drives the real re-inference cycle through the adapter's own
    Protocol methods, just without the Engine's ledger / phase-state
    bookkeeping.

    Returns ``(pkl_path, wall_clock_s, mols_list)``.
    """
    from adaptive_reflow.algorithm.scheduler._core import (
        default_cosine_scheduler,
    )
    from adaptive_reflow.universal.state import ODEConditionDelta

    glue = _glue_module()
    output_dir.mkdir(parents=True, exist_ok=True)
    scheduler = default_cosine_scheduler(cycle_length=int(n_rounds))

    started = time.perf_counter()
    mols: list[Any | None] = []
    for sample_index in range(int(n_mols)):
        bundle = adapter.build_initial_state(
            batch_id=f"graphbfn-framework-{seed}",
            sample_id=f"sample-{sample_index}",
        )
        final_trace: Any = None
        for r in range(int(n_rounds)):
            schedule_sample = scheduler.sample(0, int(r), int(r))
            num_steps = max(
                1,
                int(round(float(schedule_sample.n_cap) * float(per_round_nfe))),
            )
            spec: dict[str, Any] = {
                "num_steps": int(num_steps),
                "condition_kind": str(condition_kind),
            }
            if property_value is not None:
                spec["property_value"] = float(property_value)
            condition = adapter.compose_condition(
                bundle,
                ODEConditionDelta(
                    delta_spec=spec,
                    source="run_sota_graphbfn.framework",
                    target_round=int(r),
                    calibration_artifact_hash="graphbfn-framework",
                ),
            )
            trace = adapter.solve_ode(
                bundle,
                condition,
                seed=int(seed) + sample_index * 1000 + r,
            )
            endpoint = adapter.observe_endpoint(trace, bundle)
            final_trace = trace
            if r + 1 < int(n_rounds):
                # Carry state into the next round through the real
                # restart blend. GraphBFN's blender draws its fresh
                # tensors at the prior's own shape, so unlike the
                # FlowMol3 path there is no size-mismatch hazard here.
                bundle = adapter.apply_restart_distribution(
                    endpoint,
                    _framework_policy(
                        schedule_sample=schedule_sample,
                        sample_index=int(sample_index),
                        round_index=int(r),
                    ),
                )
            else:
                bundle = endpoint
        if glue is None or final_trace is None:
            mols.append(None)
            continue
        mols.append(
            glue.graphbfn_endpoint_to_rdkit_mol(
                adapter, final_trace, dataset=dataset
            )
        )
    wall = float(time.perf_counter() - started)
    pkl_path = output_dir / "framework_molecules.pkl"
    _pickle_mols(pkl_path, mols, wall)
    return pkl_path, wall, mols


# ---------------------------------------------------------------------------
# Eval subprocess bridge
# ---------------------------------------------------------------------------


def _run_mol_eval(
    *,
    input_pkl: Path,
    output_json: Path,
    reference_smiles: Path | None,
    dataset: str,
) -> dict[str, Any]:
    """Run :mod:`tools.run_mol_eval` on ``input_pkl``; return parsed JSON.

    Returns ``{}`` when the subprocess exits non-zero or the JSON cannot
    be parsed, so the caller can still emit a parseable summary.json
    with NaN metrics.
    """
    cmd: list[str] = [
        sys.executable,
        str(REPO_ROOT / "tools" / "run_mol_eval.py"),
        "--input",
        str(input_pkl),
        "--output",
        str(output_json),
        "--dataset",
        str(dataset),
    ]
    if reference_smiles is not None and reference_smiles.exists():
        cmd.extend(["--reference-smiles", str(reference_smiles)])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        print(
            f"[run_sota_graphbfn] mol_eval_spawn_failed:{exc}",
            file=sys.stderr,
            flush=True,
        )
        return {}
    if result.returncode != 0:
        print(
            f"[run_sota_graphbfn] mol_eval_failed_rc={result.returncode}\n"
            f"  stderr={result.stderr[:512]}",
            file=sys.stderr,
            flush=True,
        )
        return {}
    if not output_json.exists():
        return {}
    try:
        parsed = json.loads(output_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return dict(parsed)


def _safe_metrics(report: Mapping[str, Any]) -> dict[str, float]:
    """Return the metric subset of a ``run_mol_eval`` JSON report."""
    out: dict[str, float] = {}
    for key in METRIC_KEYS:
        value = report.get(key, float("nan"))
        try:
            out[key] = float(value)
        except (TypeError, ValueError):
            out[key] = float("nan")
    return out


def _paired_delta(
    baseline: Mapping[str, float], framework: Mapping[str, float]
) -> dict[str, float]:
    """Return ``framework - baseline`` per metric key (NaN-safe).

    For ``fcd`` (lower is better) a negative delta means the framework
    wins; for ``validity`` / ``qed`` (higher is better) a positive delta
    means the framework wins. ``sa`` and ``logp`` are reported as raw
    deltas and annotated in the markdown table.
    """
    out: dict[str, float] = {}
    for key in METRIC_KEYS:
        b = float(baseline.get(key, float("nan")))
        f = float(framework.get(key, float("nan")))
        if math.isnan(b) or math.isnan(f):
            out[key] = float("nan")
        else:
            out[key] = float(f - b)
    return out


def _uniqueness(mols: list[Any | None]) -> float:
    """Fraction of unique canonical SMILES over the VALID molecules.

    The GraphBFN paper's uniqueness denominator is the valid set, not
    the full sample count. Returns NaN when rdkit is unavailable or no
    molecule is valid.
    """
    try:
        from rdkit import Chem
    except ImportError:
        return float("nan")
    smiles: list[str] = []
    for mol in mols:
        if mol is None:
            continue
        try:
            smi = Chem.MolToSmiles(mol)
        except Exception:  # noqa: BLE001 — permissive on purpose
            continue
        if smi:
            smiles.append(smi)
    if not smiles:
        return float("nan")
    return float(len(set(smiles))) / float(len(smiles))


# ---------------------------------------------------------------------------
# Markdown emission
# ---------------------------------------------------------------------------


def _format_markdown(
    *,
    baseline_metrics: Mapping[str, float],
    framework_metrics: Mapping[str, float],
    paired_delta: Mapping[str, float],
    baseline_uniqueness: float,
    framework_uniqueness: float,
    n_mols: int,
    n_rounds: int,
    baseline_nfe: int,
    per_round_nfe: int,
    dataset: str,
    mode: str,
    baseline_wall: float,
    framework_wall: float,
) -> str:
    """Render the comparison.md table with per-column direction-of-good."""
    lines: list[str] = []
    lines.append("# GraphBFN baseline vs FlowA framework (Phase-A)")
    lines.append("")
    lines.append(
        f"Configuration: dataset={dataset}, adapter mode={mode}. Baseline = "
        f"{n_mols} mols x {baseline_nfe}-step single-pass BFN loop; "
        f"framework = {n_mols} chains x {n_rounds} rounds x "
        f"{per_round_nfe}-step budget (cosine scheduler, real restart "
        f"blend). Wall-clock baseline={baseline_wall:.1f}s, "
        f"framework={framework_wall:.1f}s."
    )
    lines.append("")
    lines.append("| Metric | baseline | framework | paired delta | direction |")
    lines.append("|---|---:|---:|---:|:---:|")
    direction = {
        "validity": "higher is better",
        "qed": "higher is better",
        "sa": "lower is better",
        "logp": "neutral (raw)",
        "fcd": "lower is better",
    }
    for key in METRIC_KEYS:
        b = float(baseline_metrics.get(key, float("nan")))
        f = float(framework_metrics.get(key, float("nan")))
        d = float(paired_delta.get(key, float("nan")))
        lines.append(
            f"| {key} | {b:.4f} | {f:.4f} | {d:+.4f} | "
            f"{direction.get(str(key), 'neutral')} |"
        )
    uniq_delta = (
        float(framework_uniqueness) - float(baseline_uniqueness)
        if not (
            math.isnan(baseline_uniqueness) or math.isnan(framework_uniqueness)
        )
        else float("nan")
    )
    lines.append(
        f"| uniqueness | {baseline_uniqueness:.4f} | "
        f"{framework_uniqueness:.4f} | {uniq_delta:+.4f} | higher is better |"
    )
    lines.append("")
    lines.append("## Honest framing")
    lines.append("")
    lines.append(
        "- **Synthetic backend**: the GraphBFN torch loader still raises "
        "``NotImplementedError`` (no published checkpoint in "
        "``data/graphbfn/``), so both arms run the adapter's synthetic "
        "NumPy BFN update loop. Numbers measure re-inference plumbing, "
        "NOT chemistry."
    )
    lines.append(
        "- **Provisional vocabulary**: the atom-type index -> element "
        "symbol table lives in "
        "``adaptive_reflow/molecular/rdkit_export.py`` and was authored "
        "against the adapter's declared cardinalities, not read off a "
        "checkpoint. It must be re-pinned when weights land."
    )
    lines.append(
        "- **No 3D geometry**: the GraphBFN adapter exposes no coordinate "
        "channel, so molecules are built without a conformer. Topology "
        "metrics (validity / QED / SA / logP / FCD / uniqueness) are "
        "reachable; PoseBusters / RMSD / xTB geometry metrics are not."
    )
    lines.append(
        "- **NSPDK MMD is Phase B**: the fourth paper metric needs EDeN "
        "in an isolated venv and cannot be validated before real "
        "weights exist. Only validity / uniqueness / FCD from the "
        "paper's Table 1 are reachable here."
    )
    lines.append(
        "- **FCD**: requires both the ``fcd`` package and a reference "
        "SMILES file (``--reference-smiles``); NaN with a stderr note "
        "recorded in the JSON when either is missing. The paper computes "
        "FCD against the TRAINING set (NSPDK against the test set) — do "
        "not conflate the two reference sets."
    )
    lines.append(
        "- **Framework arm**: one scheduler (cosine annealer) for the "
        "deterministic Phase-A comparison, matching the FlowMol3 "
        "sibling harness."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="run_sota_graphbfn_experiment",
        description=(
            "Run the GraphBFN SOTA experiment: single-pass "
            "(--baseline-nfe) BFN baseline vs FlowA multi-round "
            "(--n-rounds) re-inference on molecular graphs. Emits a "
            "comparison JSON + markdown table under --output-dir."
        ),
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=None,
        help=(
            "Path to the published GraphBFN checkpoint. Default: None -> "
            "synthetic NumPy BFN backend. Pass 'synthetic' as a literal "
            "string to force the synthetic backend explicitly."
        ),
    )
    parser.add_argument(
        "--n-mols",
        type=int,
        default=100,
        help="Molecule count for both arms (default: 100).",
    )
    parser.add_argument(
        "--n-rounds",
        type=int,
        default=5,
        help=(
            "Framework multi-round rounds (default: 5). The per-round "
            "step cap is ``--baseline-nfe // --n-rounds`` unless "
            "--per-round-nfe overrides it."
        ),
    )
    parser.add_argument(
        "--baseline-nfe",
        type=int,
        default=DEFAULT_BASELINE_NFE,
        help=(
            "BFN update-step count for the single-pass baseline "
            f"(default: {DEFAULT_BASELINE_NFE}; the paper reports ~1000 "
            "on QM9 and ~500 on ZINC250k)."
        ),
    )
    parser.add_argument(
        "--per-round-nfe",
        type=int,
        default=None,
        help=(
            "Per-framework-round step cap. Defaults to "
            "``max(1, --baseline-nfe // --n-rounds)`` so the framework's "
            "total step budget matches the baseline."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(
            f"Output directory (default: {DEFAULT_OUTPUT_DIR}). "
            "comparison.md and summary.json are written here."
        ),
    )
    parser.add_argument(
        "--dataset",
        choices=("qm9", "zinc250k"),
        default="qm9",
        help="Benchmark dataset (default: qm9).",
    )
    parser.add_argument(
        "--variant",
        choices=("iclr2025", "hierarchical"),
        default="iclr2025",
        help="GraphBFN variant (default: iclr2025).",
    )
    parser.add_argument(
        "--condition-kind",
        choices=(
            "unconditional",
            "property_logp",
            "property_qed",
            "property_sa",
        ),
        default="unconditional",
        help="Generation condition kind (default: unconditional).",
    )
    parser.add_argument(
        "--property-value",
        type=float,
        default=None,
        help=(
            "Target property scalar for property-conditioned generation. "
            "Required when --condition-kind is not 'unconditional'."
        ),
    )
    parser.add_argument(
        "--reference-smiles",
        type=Path,
        default=DEFAULT_REFERENCE_SMILES,
        help=(
            "Reference SMILES file (one per line) for the FCD metric. "
            "Optional; FCD is NaN when missing."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Base seed for both arms (default: 0).",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "Smoke-test profile: 4 mols, 2 rounds, baseline-nfe 5, "
            "per-round-nfe 2. Overrides the relevant CLI flags."
        ),
    )
    args = parser.parse_args(argv)
    if bool(args.smoke):
        args.n_mols = 4
        args.n_rounds = 2
        args.baseline_nfe = 5
        args.per_round_nfe = 2
    if int(args.n_mols) <= 0:
        raise ValueError("n_mols must be >= 1")
    if int(args.n_rounds) <= 0:
        raise ValueError("n_rounds must be >= 1")
    if int(args.baseline_nfe) <= 0:
        raise ValueError("baseline_nfe must be >= 1")
    if args.per_round_nfe is None:
        args.per_round_nfe = max(
            1, int(args.baseline_nfe) // int(args.n_rounds)
        )
    elif int(args.per_round_nfe) <= 0:
        raise ValueError("per_round_nfe must be >= 1")
    if str(args.condition_kind) != "unconditional" and args.property_value is None:
        raise ValueError(
            "property_value_required_for_conditioned_generation"
        )
    return args


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on a successful emit, 1 otherwise."""
    args = _parse_args(argv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    n_mols = int(args.n_mols)
    n_rounds = int(args.n_rounds)
    baseline_nfe = int(args.baseline_nfe)
    per_round_nfe = int(args.per_round_nfe)
    dataset = str(args.dataset)
    condition_kind = str(args.condition_kind)
    property_value = (
        float(args.property_value) if args.property_value is not None else None
    )

    print(
        f"[run_sota_graphbfn] n_mols={n_mols} n_rounds={n_rounds} "
        f"baseline_nfe={baseline_nfe} per_round_nfe={per_round_nfe} "
        f"dataset={dataset} output_dir={output_dir}",
        flush=True,
    )

    overall_started = time.perf_counter()

    # --- adapter ---
    adapter = _make_adapter(
        Path(args.weights) if args.weights else None,
        dataset=dataset,
        variant=str(args.variant),
        baseline_nfe=baseline_nfe,
    )
    caps = adapter.capabilities()
    mode = _adapter_mode(adapter)
    print(
        f"[run_sota_graphbfn] adapter: mode={mode} "
        f"state_shape={caps.state_shape} "
        f"channels={caps.supported_channels}",
        flush=True,
    )

    # --- baseline arm ---
    baseline_pkl, baseline_wall, baseline_mols = _run_baseline(
        adapter=adapter,
        n_mols=n_mols,
        baseline_nfe=baseline_nfe,
        seed=int(args.seed),
        dataset=dataset,
        condition_kind=condition_kind,
        property_value=property_value,
        output_dir=output_dir,
    )
    print(
        f"[run_sota_graphbfn] baseline: {baseline_pkl} "
        f"wall={baseline_wall:.1f}s",
        flush=True,
    )

    # --- framework arm ---
    framework_pkl, framework_wall, framework_mols = _run_framework(
        adapter=adapter,
        n_mols=n_mols,
        n_rounds=n_rounds,
        per_round_nfe=per_round_nfe,
        seed=int(args.seed),
        dataset=dataset,
        condition_kind=condition_kind,
        property_value=property_value,
        output_dir=output_dir,
    )
    print(
        f"[run_sota_graphbfn] framework: {framework_pkl} "
        f"wall={framework_wall:.1f}s",
        flush=True,
    )

    # --- eval ---
    reference_smiles = (
        Path(args.reference_smiles) if args.reference_smiles else None
    )
    baseline_eval_json = output_dir / "baseline_metrics.json"
    framework_eval_json = output_dir / "framework_metrics.json"
    baseline_report = _run_mol_eval(
        input_pkl=baseline_pkl,
        output_json=baseline_eval_json,
        reference_smiles=reference_smiles,
        dataset=dataset,
    )
    framework_report = _run_mol_eval(
        input_pkl=framework_pkl,
        output_json=framework_eval_json,
        reference_smiles=reference_smiles,
        dataset=dataset,
    )
    baseline_metrics = _safe_metrics(baseline_report)
    framework_metrics = _safe_metrics(framework_report)
    delta = _paired_delta(baseline_metrics, framework_metrics)
    baseline_uniqueness = _uniqueness(baseline_mols)
    framework_uniqueness = _uniqueness(framework_mols)

    total_wall = float(time.perf_counter() - overall_started)

    # --- markdown + JSON ---
    md = _format_markdown(
        baseline_metrics=baseline_metrics,
        framework_metrics=framework_metrics,
        paired_delta=delta,
        baseline_uniqueness=baseline_uniqueness,
        framework_uniqueness=framework_uniqueness,
        n_mols=n_mols,
        n_rounds=n_rounds,
        baseline_nfe=baseline_nfe,
        per_round_nfe=per_round_nfe,
        dataset=dataset,
        mode=mode,
        baseline_wall=float(baseline_wall),
        framework_wall=float(framework_wall),
    )
    md_path = output_dir / "comparison.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"[run_sota_graphbfn] wrote {md_path}", flush=True)

    summary: dict[str, Any] = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "n_mols": n_mols,
        "n_rounds": n_rounds,
        "baseline_nfe": baseline_nfe,
        "per_round_nfe": per_round_nfe,
        "weights": str(args.weights) if args.weights else "synthetic",
        "adapter_mode": mode,
        "dataset": dataset,
        "variant": str(args.variant),
        "condition_kind": condition_kind,
        "property_value": property_value,
        "seed": int(args.seed),
        "wall_clock_s": float(total_wall),
        "baseline": baseline_metrics,
        "framework": framework_metrics,
        "paired_delta": delta,
        "baseline_uniqueness": float(baseline_uniqueness),
        "framework_uniqueness": float(framework_uniqueness),
        "baseline_report": baseline_report,
        "framework_report": framework_report,
    }
    json_path = output_dir / "summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[run_sota_graphbfn] wrote {json_path}", flush=True)

    print(
        "[run_sota_graphbfn] HEADLINE_JSON="
        + json.dumps(
            {
                "baseline": baseline_metrics,
                "framework": framework_metrics,
                "paired_delta": delta,
            }
        ),
        flush=True,
    )
    return 0


__all__: list[str] = ["main"]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
