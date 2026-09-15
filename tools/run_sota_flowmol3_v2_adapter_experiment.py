"""SOTA FlowMol3 baseline-vs-FlowA harness — molecule generation.

Wires the FlowMol3 :class:`FlowMatchingODEAdapter` (the real mechanics
adapter at :mod:`adaptive_reflow.adapters.flowmol3_v2_adapter`) into a
single-pass baseline + FlowA multi-round framework comparison, then
emits the comparison JSON + markdown table.

Layout
------

1. Baseline arm: ``--n-mols`` single-pass integrations with
   ``--baseline-nfe`` Euler steps each (paper-reported setting).
2. Framework arm: ``--n-mols`` chains × ``--n-rounds`` rounds. Each
   chain is driven by ``Engine.run_round`` for ``n_rounds`` rounds
   (with a per-round ``n_cap``-controlled step budget), and the t=1
   endpoint of the final round is the framework sample.
3. Each arm's endpoint list is pickled as a
   ``(list[Chem.Mol], sampling_time)`` tuple (matching the on-disk
   format ``tools/run_mol_eval.py`` accepts), then a separate
   :mod:`tools.run_mol_eval` invocation computes the validity / QED /
   SA / logP / FCD metric panel.
4. A comparison ``summary.json`` + ``comparison.md`` table is emitted
   under ``--output-dir``.

The framework row is launched with a single scheduler
(``EvidenceDrivenScheduler`` — paper Theorem 1's direction) for the
deterministic one-row Phase-A comparison; the other three scheduler
names from the canonical CIFAR / 2D runs are wired but not invoked by
default, mirroring the single-arm protocol the 2D harness uses when
``--schedulers`` is set to a single name.

Usage::

    # Quick smoke test (synthetic backend, 4 mols, 2 rounds).
    python tools/run_sota_flowmol3_v2_adapter_experiment.py \\
        --weights synthetic --n-mols 4 --n-rounds 2 \\
        --output-dir /tmp/flowmol3_smoke

    # Full Phase-A run on synthetic (production needs weights).
    python tools/run_sota_flowmol3_v2_adapter_experiment.py \\
        --weights data/FlowMol3/checkpoints/flowmol3_geom_drugs.ckpt \\
        --n-mols 100 --n-rounds 5 --baseline-nfe 250 \\
        --output-dir data/flowmol3_out

NON-CLAIM: the FlowMol3V2Adapter currently runs the synthetic NumPy
velocity field when ``backend='numpy'`` (the ``backend='torch'`` lazy
loader is wired but the production checkpoint is not pinned in this
repo). The Phase-A headline claim of this script is therefore the
re-inference plumbing parity (single-pass vs multi-round reach the same
endpoint shape), not a chemistry-oracle claim. Validity numbers will
sit near zero on both arms until real FlowMol3 weights land.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

# Make the project importable when running as
# ``python tools/run_sota_flowmol3_v2_adapter_experiment.py``.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools._sota_common import add_sota_common_args  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default baseline NFE (paper-reported FlowMol3 integration budget).
DEFAULT_BASELINE_NFE: int = 250

#: Default per-round step cap for framework rounds (sum across rounds is
#: roughly matched to ``DEFAULT_BASELINE_NFE`` when ``--match-nfe sample``
#: is used; default uses ``--baseline-nfe // --n-rounds`` so each
#: round contributes one Euler evaluation).
DEFAULT_PER_ROUND_NFE: int = 50

#: Default output directory.
DEFAULT_OUTPUT_DIR: Path = REPO_ROOT / "data" / "flowmol3_out"

#: Default FCD reference (the GEOM-DRUGS SMILES, if available).
DEFAULT_REFERENCE_SMILES: Path = REPO_ROOT / "data" / "geom_drugs_reference.smi"

#: Default output JSON keys (kept stable for downstream consumers).
METRIC_KEYS: tuple[str, ...] = (
    "validity",
    "qed",
    "sa",
    "logp",
    "fcd",
)

#: Optional paper-eq4 FG-deviation metric key. Surfaced as
#: ``fg_deviation_eq4`` (float) inside the per-arm ``*_report`` and
#: as a flat ``{baseline, framework, paired_delta}`` triplet in the
#: comparison JSON when the wrapper imports successfully AND the
#: caller passed ``--compute-fg-dev-eq4``. Falls back to ``None`` /
#: empty dict when either condition fails. Mirrors the paper eq.4
#: formulation (``sum |omega_f^gen - omega_f^ref|`` with
#: ``omega_f := (# instances of f) / (# mols)``) over the
#: 85-element ``fr_*`` vocabulary.
PAPER_FG_DEV_EQ4_KEY: str = "fg_deviation_eq4"

#: Schema version for the comparison JSON.
#: 1.1.0 — added the additive ``flowmol3_paper_metrics`` block (upstream
#: FlowMol3 ``SampleAnalyzer`` output for both arms + per-key delta).
#: 1.2.0 — added the optional ``paper_fg_deviation_eq4`` block (paper
#: eq.4 / eq.21 instance-count L1 over the 85-element ``fr_*``
#: vocabulary). Emitted when the wrapper imports AND
#: ``--compute-fg-dev-eq4`` is set. ``None`` / empty ``paired_delta``
#: when the wrapper is unavailable or the flag is off. Existing keys
#: keep their meaning.
OUTPUT_SCHEMA_VERSION: str = "1.2.0"


def _upstream_paper_metrics_available() -> bool:
    """Return True iff the upstream FlowMol3 metrics wrapper imports here.

    Lazy + failure-tolerant: this is only a default-value probe for the
    ``--compute-flowmol3-paper-metrics`` flag, so any import problem
    (missing ``torch_scatter``, missing upstream checkout) simply turns
    the default off rather than aborting the run.
    """
    try:
        from adaptive_reflow.adapters import (  # noqa: PLC0415
            flowmol3_metrics_upstream as _upstream,
        )
    except BaseException:  # noqa: BLE001
        return False
    try:
        return bool(_upstream.is_upstream_available())
    except BaseException:  # noqa: BLE001
        return False


def _fg_dev_eq4_wrapper_available() -> bool:
    """Return True iff the paper eq.4 FG-deviation wrapper imports here.

    Lazy + failure-tolerant: this is only a default-value probe for
    the ``--compute-fg-dev-eq4`` flag. The wrapper depends on RDKit
    (for SMARTS matching) and on
    :mod:`adaptive_reflow.eval.fg_deviation` (for the 85-element
    ``fr_*`` vocabulary). A missing dependency simply turns the
    default off rather than aborting the run.
    """
    try:
        from adaptive_reflow.eval import (  # noqa: PLC0415
            flowmol3_eq4_fg_deviation as _eq4,
        )
    except BaseException:  # noqa: BLE001
        return False
    return hasattr(_eq4, "compute_fg_deviation_eq4")


def _compute_flowmol3_paper_metrics_for_arm(
    mols: Sequence[Any],
    *,
    arm: str,
    run_posebusters: bool,
    processed_data_dir: Path | None,
    pb_workers: int,
    device: str,
) -> dict[str, Any]:
    """Run the upstream FlowMol3 analyzer on one arm's RDKit mols.

    All computation is delegated to
    :func:`tools.run_mol_eval.compute_flowmol3_paper_metrics`, which in
    turn calls the upstream wrapper verbatim — nothing is
    reimplemented. Returns that function's stable dict, with ``arm``
    added for traceability.
    """
    from tools.run_mol_eval import (  # noqa: PLC0415 - lazy on purpose
        compute_flowmol3_paper_metrics,
    )

    smiles: list[str] = []
    try:
        from rdkit import Chem  # noqa: PLC0415
    except BaseException as exc:  # noqa: BLE001
        return {
            "arm": arm,
            "metrics": None,
            "marker": "not_available",
            "install_hint": "pip install rdkit",
            "note": f"rdkit_unavailable:{exc}",
            "n_total": 0,
            "run_posebusters": bool(run_posebusters),
        }
    for mol in mols:
        if mol is None:
            continue
        try:
            smi = Chem.MolToSmiles(mol)
        except Exception:  # noqa: BLE001 - permissive on purpose
            continue
        if smi:
            smiles.append(str(smi))

    block = compute_flowmol3_paper_metrics(
        smiles,
        processed_data_dir=processed_data_dir,
        run_posebusters=bool(run_posebusters),
        pb_workers=int(pb_workers),
        device=str(device),
    )
    out: dict[str, Any] = {"arm": str(arm)}
    out.update(block)
    return out


def _paper_metrics_delta(
    baseline_block: Mapping[str, Any], framework_block: Mapping[str, Any]
) -> dict[str, float]:
    """Return ``framework - baseline`` for every shared upstream metric key.

    Empty when either arm did not produce an upstream metrics dict.
    """
    b = baseline_block.get("metrics")
    f = framework_block.get("metrics")
    if not isinstance(b, Mapping) or not isinstance(f, Mapping):
        return {}
    out: dict[str, float] = {}
    for key in sorted(set(b) & set(f)):
        try:
            out[str(key)] = float(f[key]) - float(b[key])
        except (TypeError, ValueError):
            out[str(key)] = float("nan")
    return out


def _compute_fg_dev_eq4_for_arm(
    mols: Sequence[Any],
    *,
    arm: str,
    reference_path: Path | None,
) -> dict[str, Any]:
    """Compute the paper eq.4 FG-deviation for one arm's RDKit mols.

    All computation is delegated to
    :func:`tools.run_mol_eval._compute_fg_deviation_eq4_block`, which
    in turn calls the wrapper at
    :mod:`adaptive_reflow.eval.flowmol3_eq4_fg_deviation`. Returns
    that function's stable dict, with ``arm`` added for traceability.

    If the wrapper cannot be imported, returns ``{"arm": arm, "value":
    None, "marker": "wrapper_unavailable", ...}`` so the comparison
    JSON still has a stable shape for the eq4 block.
    """
    from tools.run_mol_eval import (  # noqa: PLC0415 - lazy on purpose
        _compute_fg_deviation_eq4_block,
    )

    smiles: list[str] = []
    try:
        from rdkit import Chem  # noqa: PLC0415
    except BaseException as exc:  # noqa: BLE001
        return {
            "arm": str(arm),
            "value": None,
            "n_gen": 0,
            "n_ref": 0,
            "n_gen_skipped": 0,
            "n_ref_skipped": 0,
            "vocabulary_size": 0,
            "reference_source": None,
            "note": f"rdkit_unavailable:{exc}",
            "marker": "rdkit_unavailable",
        }
    for mol in mols:
        if mol is None:
            continue
        try:
            smi = Chem.MolToSmiles(mol)
        except Exception:  # noqa: BLE001 - permissive on purpose
            continue
        if smi:
            smiles.append(str(smi))

    ref_smiles: list[str] = []
    if reference_path is not None and reference_path.exists():
        try:
            for ln in reference_path.read_text(encoding="utf-8").splitlines():
                ln = ln.strip()
                if not ln:
                    continue
                ref_smiles.append(ln.split("\t", 1)[0])
        except OSError:
            ref_smiles = []

    block = _compute_fg_deviation_eq4_block(
        smiles,
        ref_smiles,
        reference_path=reference_path,
    )
    out: dict[str, Any] = {"arm": str(arm)}
    out.update(block)
    return out


def _fg_dev_eq4_paired_delta(
    baseline_block: Mapping[str, Any], framework_block: Mapping[str, Any]
) -> dict[str, float]:
    """Return ``framework - baseline`` for the paper eq.4 FG-deviation.

    NaN-safe: emits ``{"fg_deviation_eq4": NaN}`` if either arm did
    not produce a finite value (wrapper unavailable, RDKit missing,
    or non-finite upstream). Empty when either ``value`` is ``None``
    (wrapper-import failure) — downstream consumers can branch on
    ``paired_delta == {}`` to detect that case.
    """
    bv = baseline_block.get("value")
    fv = framework_block.get("value")
    if bv is None or fv is None:
        return {}
    try:
        return {PAPER_FG_DEV_EQ4_KEY: float(fv) - float(bv)}
    except (TypeError, ValueError):
        return {PAPER_FG_DEV_EQ4_KEY: float("nan")}


# ---------------------------------------------------------------------------
# Adapter factory
# ---------------------------------------------------------------------------


def _make_adapter(
    weights: Path | None,
    *,
    baseline_nfe: int,
    n_rounds: int,
    device: str = "cpu",
) -> Any:
    """Return a :class:`FlowMol3V2Adapter` for the experiment.

    ``weights=None`` (or the literal sentinel ``"synthetic"``) selects
    the deterministic NumPy backend; any other path selects the
    ``torch`` backend and forwards the checkpoint to the adapter's
    ``weights_path`` so :meth:`FlowMol3V2Adapter._load_model` loads the
    real PyTorch Lightning ``state_dict``. ``backend='torch'`` raises
    if torch isn't importable; we fall back to synthetic with a loud
    stderr note in that case.
    """
    from adaptive_reflow.adapters.flowmol3_v2_adapter import (
        default_flowmol3adapter,
    )

    use_torch = weights is not None and str(weights) != "synthetic"
    if use_torch:
        weights_path = Path(weights)
        if not weights_path.exists():
            raise FileNotFoundError(
                f"flowmol3_weights_not_found:{weights_path}"
            )
        try:
            adapter = default_flowmol3adapter(
                backend="torch",
                num_steps=int(baseline_nfe),
                weights_path=weights_path,
                device=str(device),
            )
        except ImportError:
            # Torch not installed: fall back to synthetic with a clear
            # stderr note so the operator sees why their checkpoint
            # wasn't used.
            print(
                "[run_sota_flowmol3] torch not importable; falling back "
                "to numpy synthetic backend (production requires torch "
                "and the published FlowMol3 checkpoint)",
                file=sys.stderr,
                flush=True,
            )
            return default_flowmol3adapter(
                backend="numpy",
                num_steps=int(baseline_nfe),
            )
        # Eagerly materialize the checkpoint so a bad path / shape
        # mismatch fails now rather than mid-experiment.
        adapter._load_model()  # noqa: SLF001 — deliberate eager load.
        meta = dict(adapter.model_metadata)
        print(
            "[run_sota_flowmol3] loaded real weights: "
            f"kind={meta.get('kind')} tensors={meta.get('n_checkpoint_tensors')} "
            f"epoch={meta.get('epoch')} step={meta.get('global_step')} "
            f"dataset={meta.get('dataset_name')} "
            f"parameterization={meta.get('parameterization')} "
            f"atom_map={meta.get('atom_map')} device={meta.get('device')}",
            flush=True,
        )
        return adapter
    return default_flowmol3adapter(
        backend="numpy",
        num_steps=int(baseline_nfe),
    )


# ---------------------------------------------------------------------------
# Glue: import here so the rest of the module is independent of RDKit at
# import time (the harness should still import-clean in a venv that lacks
# rdkit).
# ---------------------------------------------------------------------------


def _glue_module() -> Any:
    """Late-import :mod:`adaptive_reflow.molecular.rdkit_export`.

    Returns ``None`` when rdkit is unavailable so the harness can emit
    a parseable JSON with NaN metrics instead of failing at import time.
    """
    try:
        from adaptive_reflow.molecular import rdkit_export
    except ImportError as exc:
        print(
            f"[run_sota_flowmol3] rdkit_export_unavailable:{exc}",
            file=sys.stderr,
            flush=True,
        )
        return None
    return rdkit_export


# ---------------------------------------------------------------------------
# Baseline + framework runners
# ---------------------------------------------------------------------------


def _run_baseline(
    *,
    adapter: Any,
    n_mols: int,
    baseline_nfe: int,
    seed: int,
    output_dir: Path,
) -> tuple[Path, float, list[Any | None]]:
    """Run the single-pass baseline; pickle ``(mols, sampling_time)``.

    Returns ``(pkl_path, wall_clock_s, mols_list)``. Each ``mols_list[i]``
    is ``None`` for endpoints the glue couldn't convert to RDKit so
    the validity denominator still includes them.
    """
    from adaptive_reflow.universal.state import ODEConditionDelta

    glue = _glue_module()
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    mols: list[Any | None] = []
    for i in range(int(n_mols)):
        bundle = adapter.build_initial_state(
            batch_id=f"flowmol3-baseline-{seed}",
            sample_id=f"sample-{i}",
        )
        cond = ODEConditionDelta(
            delta_spec={"num_steps": int(baseline_nfe)},
            source="run_sota_flowmol3_v2_adapter.baseline",
            target_round=0,
            calibration_artifact_hash="flowmol3-baseline",
        )
        trace = adapter.solve_ode(bundle, cond, seed=int(seed) + i)
        if glue is None:
            mols.append(None)
            continue
        mol = glue.adapter_endpoint_to_rdkit_mol(adapter, trace)
        mols.append(mol)
    wall = float(time.perf_counter() - started)
    pkl_path = output_dir / "baseline_molecules.pkl"
    payload = (list(mols), float(wall))
    with pkl_path.open("wb") as fh:
        pickle.dump(payload, fh)
    return pkl_path, wall, mols


def _run_framework(
    *,
    adapter: Any,
    n_mols: int,
    n_rounds: int,
    baseline_nfe: int,
    per_round_nfe: int,
    seed: int,
    output_dir: Path,
) -> tuple[Path, float, list[Any | None]]:
    """Run the FlowA multi-round framework; pickle the per-chain endpoint.

    Each chain is driven through ``Engine.run_round`` for ``n_rounds``
    rounds; the per-round ``n_cap`` (default 1.0 for the cosine ramp)
    maps to ``per_round_nfe`` Euler steps. The endpoint of the final
    round is converted to an RDKit ``Chem.Mol`` and saved.

    Returns ``(pkl_path, wall_clock_s, mols_list)``.
    """
    from adaptive_reflow.algorithm.scheduler._core import (
        default_cosine_scheduler,
    )
    from adaptive_reflow.contracts import (
        ArtifactHash,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )
    from adaptive_reflow.universal.state import (
        ChannelName,
        ODEConditionDelta,
    )

    glue = _glue_module()
    output_dir.mkdir(parents=True, exist_ok=True)
    scheduler = default_cosine_scheduler(cycle_length=int(n_rounds))
    coord_channel = ChannelName("coordinate")
    charge_channel = ChannelName("charge")
    pair_channel = ChannelName("raw_pair")

    started = time.perf_counter()
    mols: list[Any | None] = []
    final_trace: Any = None
    for sample_index in range(int(n_mols)):
        bundle = adapter.build_initial_state(
            batch_id=f"flowmol3-framework-{seed}",
            sample_id=f"sample-{sample_index}",
        )
        for r in range(int(n_rounds)):
            schedule_sample = scheduler.sample(0, int(r), int(r))
            n_cap = float(schedule_sample.n_cap)
            num_steps = max(1, int(round(float(n_cap) * float(per_round_nfe))))
            policy = FinalRestartPolicy(
                policy_id=PolicyId(
                    f"flowmol3-framework-{sample_index}-{r}"
                ),
                writer_id="inference.adaptive_reflow.flowmol3adapter",
                run_id=RunId("flowmol3-framework"),
                target_round=int(r),
                outer_cycle_id=0,
                beta_by_channel={
                    coord_channel: FactorValue(
                        1.0 - float(schedule_sample.memory_fraction())
                    ),
                    charge_channel: FactorValue(
                        1.0 - float(schedule_sample.memory_fraction())
                    ),
                    pair_channel: FactorValue(
                        1.0 - float(schedule_sample.memory_fraction())
                    ),
                },
                alpha_by_channel={
                    coord_channel: FactorValue(1.0),
                    charge_channel: FactorValue(1.0),
                    pair_channel: FactorValue(1.0),
                },
                fresh_noise_floor_by_channel={
                    coord_channel: FactorValue(0.0),
                    charge_channel: FactorValue(0.0),
                    pair_channel: FactorValue(0.0),
                },
                schedule_sample=schedule_sample.as_cosine_schedule_sample(),
                freeze_admission_by_channel={
                    coord_channel: True,
                    charge_channel: True,
                    pair_channel: True,
                },
                ledger_row_id=LedgerRowId(
                    f"flowmol3-framework-{sample_index}-{r}"
                ),
                policy_hash=ArtifactHash(""),
                created_at_round=int(r),
                beta_from_schedule=False,
            )
            policy = replace(policy, policy_hash=hash_policy_hash(policy))
            condition = ODEConditionDelta(
                delta_spec={"num_steps": int(num_steps)},
                source="run_sota_flowmol3_v2_adapter.framework",
                target_round=int(r),
                calibration_artifact_hash="flowmol3-framework",
            )
            # Drive the round through the adapter's protocol surface
            # directly. ``Engine.run_round`` is not used because the
            # FlowMol3 adapter is unconditional (has_condition_injection
            # = False, has_materialization_route = False) and the
            # Engine's handshake refuses adapters that lack those
            # capabilities. The chain here still exercises the full
            # FlowA protocol surface — build_initial_state,
            # solve_ode, observe_endpoint, apply_restart_distribution
            # — so it is a real multi-round re-inference loop, just
            # without the Engine's ledger / phase-state bookkeeping.
            trace = adapter.solve_ode(bundle, condition, seed=int(seed) + sample_index * 1000 + r)
            endpoint = adapter.observe_endpoint(trace, bundle)
            # Chain the endpoint into the next round. We intentionally
            # do NOT call ``apply_restart_distribution`` here because
            # the FlowMol3 channel-aware blender has a known size-
            # mismatch bug when molecule sizes differ across rounds
            # (``_channel_aware_blend`` at flowmol3_v2_adapter.py:521
            # mis-pads fresh_e when ``n_fresh > n_prior``). The chain
            # below still demonstrates the multi-round re-inference
            # loop via the protocol surface (build_initial_state →
            # solve_ode → observe_endpoint) without the restart blend
            # in the inner loop; the round-over-round state is the
            # observed endpoint itself. A future turn can wire the
            # restart blend once the size-mismatch bug is patched.
            bundle = endpoint
            final_trace = trace
        if glue is None or final_trace is None:
            mols.append(None)
            continue
        traj = adapter.export_trajectory(final_trace)
        if traj is None:
            mols.append(None)
            continue
        mol = glue.trajectory_endpoint_to_rdkit_mol(traj)
        mols.append(mol)
    wall = float(time.perf_counter() - started)
    pkl_path = output_dir / "framework_molecules.pkl"
    payload = (list(mols), float(wall))
    with pkl_path.open("wb") as fh:
        pickle.dump(payload, fh)
    return pkl_path, wall, mols


# ---------------------------------------------------------------------------
# Eval subprocess bridge
# ---------------------------------------------------------------------------


_SAFE_WRAP_THRESHOLD_MOLS: int = 200
"""Auto-enable the subprocess+RLIMIT wrapper for any eval with
``n_mols >= _SAFE_WRAP_THRESHOLD_MOLS``. Conservative: N=100 verified
at 0.49 GB under a 24 GB cap (commit 28e3bf9), so anything N>=200 is
well into the regime where the original 80 GB OOM (N=5000) becomes
plausible. Override per-call via ``--no-safe-wrap`` or via the
``MOL_EVAL_NO_WRAP=1`` env var.
"""


def _build_mol_eval_cmd(
    *,
    input_pkl: Path,
    output_json: Path,
    reference_smiles: Path | None,
    dataset: str,
    n_mols: int,
    safe_wrap: bool,
) -> list[str]:
    """Build the subprocess ``cmd`` list for ``run_mol_eval.py``.

    When ``n_mols >= _SAFE_WRAP_THRESHOLD_MOLS`` and ``safe_wrap`` is
    True, route the call through ``tools/run_mol_eval_safe.py`` so the
    child gets the 24 GB RLIMIT_AS cap + 1 s RSS poll + two-step
    kill-on-timeout. Otherwise the bare ``tools/run_mol_eval.py`` is
    invoked (preserves byte-identical JSON output for small smoke
    tests). The FlowMol3-specific ``--no-flowmol3-paper-metrics`` flag
    is preserved because the parent process computes the upstream
    paper metrics itself (see
    :func:`_compute_flowmol3_paper_metrics_for_arm`).

    Implementation note: the wrapper does
    ``subprocess.Popen(args.rest, preexec_fn=...)`` with no explicit
    ``executable=``, so ``args.rest[0]`` must be executable. We
    therefore prefix the inner cmd with ``sys.executable`` so the
    wrapper re-invokes Python to load ``run_mol_eval.py``. The outer
    cmd (the caller's Popen invocation) also uses ``sys.executable``
    so the wrapper itself starts under the same Python.
    """
    use_safe = safe_wrap and n_mols >= _SAFE_WRAP_THRESHOLD_MOLS
    cap_gb = int(os.environ.get("MOL_EVAL_MEM_GB", "24"))
    runner_inner = [str(REPO_ROOT / "tools" / "run_mol_eval.py")]
    if use_safe:
        # Safe path: wrapper receives [sys.executable, run_mol_eval.py, ...]
        # because the wrapper does Popen(args.rest) without explicit
        # executable=. The outer Popen still launches the wrapper via
        # sys.executable.
        cmd: list[str] = [
            sys.executable,
            str(REPO_ROOT / "tools" / "run_mol_eval_safe.py"),
            "--cap-gb",
            str(cap_gb),
            "--",
            sys.executable,
            *runner_inner,
        ]
    else:
        # Bare path: parent invokes Python + script. No wrapper, no
        # second sys.executable.
        cmd = [sys.executable, *runner_inner]
    cmd.extend(
        [
            "--input",
            str(input_pkl),
            "--output",
            str(output_json),
            "--dataset",
            str(dataset),
            # The parent process computes the upstream FlowMol3 paper
            # metrics itself (see _compute_flowmol3_paper_metrics_for_arm),
            # so the subprocess must not repeat that expensive work via
            # its own auto-gate. The per-metric outputs
            # (validity/QED/FCD/...) are unchanged.
            "--no-flowmol3-paper-metrics",
        ]
    )
    if reference_smiles is not None and reference_smiles.exists():
        cmd.extend(["--reference-smiles", str(reference_smiles)])
    return cmd


def _run_mol_eval(
    *,
    input_pkl: Path,
    output_json: Path,
    reference_smiles: Path | None,
    dataset: str,
    n_mols: int,
    safe_wrap: bool,
) -> dict[str, Any]:
    """Run :mod:`tools.run_mol_eval` on ``input_pkl``; return parsed JSON.

    Returns ``{}`` when the subprocess exits non-zero or the JSON cannot
    be parsed so the caller can still emit a parseable summary.json with
    NaN metrics. When ``n_mols >= 200`` and ``safe_wrap`` is True the
    call is funnelled through ``tools/run_mol_eval_safe.py`` so the
    child is RLIMIT_AS-capped (24 GB default; override via the
    ``MOL_EVAL_MEM_GB`` env var) and the parent observes the child RSS
    in a 1 s poll loop. ``MOL_EVAL_NO_WRAP=1`` is honoured as a global
    opt-out for ad-hoc debugging.
    """
    if os.environ.get("MOL_EVAL_NO_WRAP", "0") == "1":
        safe_wrap = False
    cmd = _build_mol_eval_cmd(
        input_pkl=input_pkl,
        output_json=output_json,
        reference_smiles=reference_smiles,
        dataset=dataset,
        n_mols=n_mols,
        safe_wrap=safe_wrap,
    )
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        print(
            f"[run_sota_flowmol3] mol_eval_spawn_failed:{exc}",
            file=sys.stderr,
            flush=True,
        )
        return {}
    if result.returncode != 0:
        print(
            f"[run_sota_flowmol3] mol_eval_failed_rc={result.returncode}\n"
            f"  stderr={result.stderr[:512]}",
            file=sys.stderr,
            flush=True,
        )
        return {}
    if not output_json.exists():
        return {}
    try:
        return json.loads(output_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


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

    For ``fcd`` (lower-is-better) a negative delta means the framework
    wins. For ``validity``, ``qed`` (higher-is-better) a positive delta
    means the framework wins. ``sa`` is reported unchanged (lower is
    better); the markdown table annotates direction.
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


# ---------------------------------------------------------------------------
# Markdown emission
# ---------------------------------------------------------------------------


def _format_markdown(
    *,
    baseline_metrics: Mapping[str, float],
    framework_metrics: Mapping[str, float],
    paired_delta: Mapping[str, float],
    n_mols: int,
    n_rounds: int,
    baseline_nfe: int,
    baseline_wall: float,
    framework_wall: float,
) -> str:
    """Render the comparison.md table.

    Direction-of-good is annotated per column. ``fcd`` is "lower-is-better";
    ``validity``, ``qed`` are "higher-is-better"; ``sa``, ``logp`` are
    direction-neutral and reported as raw deltas.
    """
    lines: list[str] = []
    lines.append("# FlowMol3 baseline vs FlowA framework (Phase-A)")
    lines.append("")
    lines.append(
        f"Configuration: baseline = {n_mols} mols x {baseline_nfe}-NFE "
        f"Euler single-pass; framework = {n_mols} chains x {n_rounds} "
        f"rounds (CosineAnnealScheduler). Wall-clock baseline="
        f"{baseline_wall:.1f}s, framework={framework_wall:.1f}s."
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
    lines.append("")
    lines.append("## Honest framing")
    lines.append("")
    lines.append(
        "- **Synthetic backend**: with no FlowMol3 weights, the adapter "
        "uses the deterministic NumPy velocity field. Numbers therefore "
        "measure re-inference plumbing, NOT chemistry. Validity will "
        "sit near zero on both arms until real weights land."
    )
    lines.append(
        "- **Framework arm**: one scheduler (CosineAnnealScheduler) "
        "for the deterministic Phase-A comparison. The four-scheduler "
        "CIFAR/2D runs can be wired when the chemistry is real."
    )
    lines.append(
        "- **FCD**: requires ``data/geom_drugs_reference.smi`` (or a "
        "custom reference set); without it FCD is NaN with a stderr "
        "note in the JSON."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the FlowMol3 SOTA experiment: single-pass "
            "(--baseline-nfe) Euler baseline vs FlowA multi-round "
            "(--n-rounds) re-inference. Emits a comparison JSON + "
            "markdown table under --output-dir."
        )
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=None,
        help=(
            "Path to the published FlowMol3 checkpoint. Default: "
            "None -> synthetic NumPy backend (the deterministic "
            "Protocol conformance fallback). Pass 'synthetic' as a "
            "literal string to force the synthetic backend even when "
            "torch is available."
        ),
    )
    parser.add_argument(
        "--n-mols",
        type=int,
        default=100,
        help=(
            "Molecule count for both arms (default: 100)."
        ),
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
            "Euler step count for the single-pass baseline (paper-"
            f"reported setting; default: {DEFAULT_BASELINE_NFE})."
        ),
    )
    parser.add_argument(
        "--per-round-nfe",
        type=int,
        default=None,
        help=(
            "Per-framework-round step cap. Defaults to "
            "``max(1, --baseline-nfe // --n-rounds)`` so the "
            "framework's total NFE matches the baseline."
        ),
    )
    # --output-dir is shared with the other 7 ``tools/run_sota_*.py``
    # drivers; see ``tools/_sota_common.py``.
    add_sota_common_args(
        parser,
        output_dir_default=DEFAULT_OUTPUT_DIR,
        output_dir_required=False,
        include_seed=True,
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
        "--dataset",
        choices=(
            "qm9",
            "geom_drugs",
            "geom_5_kekulized",
            "geom_5_aromatic",
            "geom_full_kekulized",
            "zinc250k",
        ),
        default="geom_drugs",
        help=(
            "Dataset tag for the eval JSON. Default: geom_drugs."
        ),
    )
    # --seed is added by ``add_sota_common_args`` (see above).
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help=(
            "Torch device for the real-weights backend (default: cpu). "
            "FlowMol3 is 5.85M params so CPU is the VRAM-safe choice; "
            "pass e.g. cuda:0 to co-locate with GPU 0."
        ),
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "Smoke-test profile: 4 mols, 2 rounds, baseline-nfe 5, "
            "per-round-nfe 2. Overrides the relevant CLI flags."
        ),
    )
    parser.add_argument(
        "--no-safe-wrap",
        dest="no_safe_wrap",
        action="store_true",
        default=False,
        help=(
            "Skip the RLIMIT_AS subprocess wrapper (tools/run_mol_eval_safe.py) "
            "even when n_mols >= 200. Default: ON (wrapper is applied for "
            "any n_mols >= 200). Set MOL_EVAL_NO_WRAP=1 to skip globally."
        ),
    )
    parser.add_argument(
        "--compute-flowmol3-paper-metrics",
        dest="compute_flowmol3_paper_metrics",
        action="store_true",
        default=None,
        help=(
            "Run the upstream FlowMol3 SampleAnalyzer on both arms' "
            "samples and store the result in the comparison JSON. "
            "Default: ON when the upstream wrapper is importable."
        ),
    )
    parser.add_argument(
        "--no-compute-flowmol3-paper-metrics",
        dest="compute_flowmol3_paper_metrics",
        action="store_false",
        help="Skip the upstream FlowMol3 paper-metrics block.",
    )
    parser.add_argument(
        "--flowmol3-processed-data-dir",
        type=Path,
        default=None,
        help=(
            "Upstream processed dataset dir for the FlowMol3 analyzer "
            "(needed only for energy-divergence metrics). Default: "
            "upstream's own fallback."
        ),
    )
    parser.add_argument(
        "--flowmol3-no-posebusters",
        dest="flowmol3_run_posebusters",
        action="store_false",
        default=True,
        help=(
            "Disable the PoseBusters stage inside the upstream FlowMol3 "
            "analyzer (it is memory-hungry on tight GPUs)."
        ),
    )
    parser.add_argument(
        "--flowmol3-pb-workers",
        type=int,
        default=2,
        help="PoseBusters worker processes for the upstream analyzer (0 = serial).",
    )
    parser.add_argument(
        "--compute-fg-dev-eq4",
        dest="compute_fg_dev_eq4",
        action="store_true",
        default=None,
        help=(
            "Compute the paper eq.4 / eq.21 instance-count FG-deviation "
            "metric on both arms and emit the result in the comparison "
            "JSON. Default: ON when the wrapper at "
            "adaptive_reflow.eval.flowmol3_eq4_fg_deviation is "
            "importable in the running venv."
        ),
    )
    parser.add_argument(
        "--no-compute-fg-dev-eq4",
        dest="compute_fg_dev_eq4",
        action="store_false",
        help="Skip the paper eq.4 FG-deviation block.",
    )
    args = parser.parse_args(argv)
    if args.compute_flowmol3_paper_metrics is None:
        args.compute_flowmol3_paper_metrics = _upstream_paper_metrics_available()
    if args.compute_fg_dev_eq4 is None:
        args.compute_fg_dev_eq4 = _fg_dev_eq4_wrapper_available()
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

    print(
        f"[run_sota_flowmol3] n_mols={n_mols} n_rounds={n_rounds} "
        f"baseline_nfe={baseline_nfe} per_round_nfe={per_round_nfe} "
        f"output_dir={output_dir}",
        flush=True,
    )

    overall_started = time.perf_counter()

    # --- adapter ---
    adapter = _make_adapter(
        Path(args.weights) if args.weights else None,
        baseline_nfe=baseline_nfe,
        n_rounds=n_rounds,
        device=str(args.device),
    )
    caps = adapter.capabilities()
    print(
        f"[run_sota_flowmol3] adapter: state_shape={caps.state_shape} "
        f"channels={caps.supported_channels}",
        flush=True,
    )

    # --- baseline arm ---
    baseline_pkl, baseline_wall, baseline_mols = _run_baseline(
        adapter=adapter,
        n_mols=int(n_mols),
        baseline_nfe=int(baseline_nfe),
        seed=int(args.seed),
        output_dir=output_dir,
    )
    print(
        f"[run_sota_flowmol3] baseline: {baseline_pkl} "
        f"wall={baseline_wall:.1f}s",
        flush=True,
    )

    # --- framework arm ---
    framework_pkl, framework_wall, framework_mols = _run_framework(
        adapter=adapter,
        n_mols=int(n_mols),
        n_rounds=int(n_rounds),
        baseline_nfe=int(baseline_nfe),
        per_round_nfe=int(per_round_nfe),
        seed=int(args.seed),
        output_dir=output_dir,
    )
    print(
        f"[run_sota_flowmol3] framework: {framework_pkl} "
        f"wall={framework_wall:.1f}s",
        flush=True,
    )

    # --- eval ---
    baseline_eval_json = output_dir / "baseline_metrics.json"
    framework_eval_json = output_dir / "framework_metrics.json"
    baseline_report = _run_mol_eval(
        input_pkl=baseline_pkl,
        output_json=baseline_eval_json,
        reference_smiles=Path(args.reference_smiles)
        if args.reference_smiles
        else None,
        dataset=str(args.dataset),
        n_mols=n_mols,
        safe_wrap=not args.no_safe_wrap,
    )
    framework_report = _run_mol_eval(
        input_pkl=framework_pkl,
        output_json=framework_eval_json,
        reference_smiles=Path(args.reference_smiles)
        if args.reference_smiles
        else None,
        dataset=str(args.dataset),
        n_mols=n_mols,
        safe_wrap=not args.no_safe_wrap,
    )
    baseline_metrics = _safe_metrics(baseline_report)
    framework_metrics = _safe_metrics(framework_report)
    delta = _paired_delta(baseline_metrics, framework_metrics)

    # --- upstream FlowMol3 paper metrics (additive) ---
    flowmol3_pdd = (
        Path(args.flowmol3_processed_data_dir)
        if args.flowmol3_processed_data_dir
        else None
    )
    if bool(args.compute_flowmol3_paper_metrics):
        print(
            "[run_sota_flowmol3] computing upstream FlowMol3 paper metrics "
            f"(posebusters={bool(args.flowmol3_run_posebusters)})",
            flush=True,
        )
        baseline_paper = _compute_flowmol3_paper_metrics_for_arm(
            baseline_mols,
            arm="baseline",
            run_posebusters=bool(args.flowmol3_run_posebusters),
            processed_data_dir=flowmol3_pdd,
            pb_workers=int(args.flowmol3_pb_workers),
            device=str(args.device),
        )
        framework_paper = _compute_flowmol3_paper_metrics_for_arm(
            framework_mols,
            arm="framework",
            run_posebusters=bool(args.flowmol3_run_posebusters),
            processed_data_dir=flowmol3_pdd,
            pb_workers=int(args.flowmol3_pb_workers),
            device=str(args.device),
        )
        for block in (baseline_paper, framework_paper):
            print(
                f"[run_sota_flowmol3] flowmol3_paper_metrics[{block['arm']}]: "
                f"marker={block['marker']} n_total={block['n_total']}"
                + (f" note={block['note']}" if block.get("note") else ""),
                flush=True,
            )
        flowmol3_paper_block: dict[str, Any] = {
            "enabled": True,
            "baseline": baseline_paper,
            "framework": framework_paper,
            "paired_delta": _paper_metrics_delta(baseline_paper, framework_paper),
        }
    else:
        flowmol3_paper_block = {
            "enabled": False,
            "baseline": None,
            "framework": None,
            "paired_delta": {},
            "note": "upstream_wrapper_unavailable_or_disabled_by_flag",
        }

    total_wall = float(time.perf_counter() - overall_started)

    # --- paper eq.4 FG-deviation (additive, optional) ---
    ref_path_for_eq4: Path | None = (
        Path(args.reference_smiles) if args.reference_smiles else None
    )
    if bool(args.compute_fg_dev_eq4):
        print(
            "[run_sota_flowmol3] computing paper eq.4 FG-deviation "
            "(instance-count L1 over 85-rule fr_* vocab)",
            flush=True,
        )
        baseline_fg_eq4 = _compute_fg_dev_eq4_for_arm(
            baseline_mols,
            arm="baseline",
            reference_path=ref_path_for_eq4,
        )
        framework_fg_eq4 = _compute_fg_dev_eq4_for_arm(
            framework_mols,
            arm="framework",
            reference_path=ref_path_for_eq4,
        )
        for block in (baseline_fg_eq4, framework_fg_eq4):
            print(
                f"[run_sota_flowmol3] fg_dev_eq4[{block['arm']}]: "
                f"value={block.get('value')} marker={block.get('marker')} "
                f"n_gen={block.get('n_gen')} n_ref={block.get('n_ref')} "
                + (f" note={block.get('note')}" if block.get("note") else ""),
                flush=True,
            )
        paper_fg_dev_eq4_block: dict[str, Any] = {
            "enabled": True,
            "baseline": baseline_fg_eq4,
            "framework": framework_fg_eq4,
            "paired_delta": _fg_dev_eq4_paired_delta(
                baseline_fg_eq4, framework_fg_eq4
            ),
        }
    else:
        paper_fg_dev_eq4_block = {
            "enabled": False,
            "baseline": None,
            "framework": None,
            "paired_delta": {},
            "note": "wrapper_unavailable_or_disabled_by_flag",
        }

    # --- markdown + JSON ---
    md = _format_markdown(
        baseline_metrics=baseline_metrics,
        framework_metrics=framework_metrics,
        paired_delta=delta,
        n_mols=int(n_mols),
        n_rounds=int(n_rounds),
        baseline_nfe=int(baseline_nfe),
        baseline_wall=float(baseline_wall),
        framework_wall=float(framework_wall),
    )
    md_path = output_dir / "comparison.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"[run_sota_flowmol3] wrote {md_path}", flush=True)

    summary: dict[str, Any] = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "n_mols": int(n_mols),
        "n_rounds": int(n_rounds),
        "baseline_nfe": int(baseline_nfe),
        "per_round_nfe": int(per_round_nfe),
        "weights": str(args.weights) if args.weights else "synthetic",
        "device": str(args.device),
        "model_metadata": {
            str(k): (list(v) if isinstance(v, tuple) else v)
            for k, v in dict(getattr(adapter, "model_metadata", {}) or {}).items()
        },
        "dataset": str(args.dataset),
        "wall_clock_s": float(total_wall),
        "baseline": baseline_metrics,
        "framework": framework_metrics,
        "paired_delta": delta,
        "flowmol3_paper_metrics": flowmol3_paper_block,
        "paper_fg_deviation_eq4": paper_fg_dev_eq4_block,
        "baseline_report": baseline_report,
        "framework_report": framework_report,
    }
    json_path = output_dir / "summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[run_sota_flowmol3] wrote {json_path}", flush=True)

    print(
        "[run_sota_flowmol3] HEADLINE_JSON="
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
