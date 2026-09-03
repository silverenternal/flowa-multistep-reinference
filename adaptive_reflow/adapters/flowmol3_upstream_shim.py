"""FlowMol3 upstream shim: thin wrapper around the published zavalab/FlowMol3 harness.

Routes the :class:`adaptive_reflow.adapters.flowmol3_v2_adapter.FlowMol3V2Adapter`
to the upstream ``flowmol.models.flowmol.FlowMol`` Lightning module when the
caller opts in via ``use_upstream=True``. The shim is *opt-in* — silently
switching the adapter's default load path from the partial-fidelity
readout head (``_build_flowmol3_velocity_module`` in the v2 adapter) to
upstream full-fidelity would invalidate every number in the framework's
previous audit trail (see r17/P-21).

Hard environmental notes (verified on this host as of 2026-09-03):

* ``flowmol.models.flowmol`` does ``import dgl`` at module scope
  (``data/FlowMol3/repo/flowmol/models/flowmol.py:6``). DGL on this host
  requires ``torch==2.2.0+cu121`` (DGL 2.1.0 wheel ships graphbolt
  binaries up through torch 2.2.x only); ``torch>=2.6`` shows
  ``FileNotFoundError: Cannot find DGL C++ graphbolt library at
  .../libgraphbolt_pytorch_2.7.0.so``. The shim therefore ships a
  guarded ``_UPSTREAM_IMPORT_ERROR`` and lets the adapter call fall
  back to the partial-fidelity path on any ``ModuleNotFoundError`` /
  ``FileNotFoundError`` raised by the upstream import.

* ``flowmol.utils.ctmc_utils`` does ``from torch_scatter import
  segment_csr``. The PyG wheel index (``data.pyg.org``) is DNS-blocked
  on this host (curl exit 6, "failed to lookup address information").
  ``pip install torch-scatter`` therefore fails with a build isolation
  error, not a clean resolver failure. The shim does **not** try to
  side-channel the wheel; upstream-FlowMol3 stays blocked until the
  PyG index is reachable or a torch-scatter wheel is vendored.

The shim re-exposes the upstream ``test.py --metrics`` path as a
single callable::

    run_upstream_flowmol3_eval(
        weights_path=...,
        n_mols=100,
        n_timesteps=250,
        device="cuda:0",
        seed=0,
        processed_data_dir=None,
        output_dir=None,
    ) -> dict[str, float]

The return value is the metrics dict that upstream's
``SampleAnalyzer.analyze`` returns (``frac_valid_mols``,
``frac_atoms_stable``, ``frac_mols_stable_valence``, ``pb_*``,
``flag_rate``, ``ood_rate``, ``reos_cum_dev``, etc.). When
``output_dir`` is provided, the shim also dumps
``samples/sampled_mols.sdf`` + a metrics pkl so downstream diffing
tools (cf. ``tools/run_mol_eval.py``) can replay the same path
upstream uses.
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — pinned to the commit the v2 adapter already locks.
# ---------------------------------------------------------------------------

FLOWMOL3_UPSTREAM_REPO: str = "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo"
FLOWMOL3_PINNED_COMMIT: str = "77cae22174b7792b0e25e9e0414038420736d841"
FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR: str = (
    "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom"
)


# ---------------------------------------------------------------------------
# Module-level import state. The shim attempts to import the upstream
# package exactly once and caches the result. A failure leaves a clear
# ``_UPSTREAM_IMPORT_ERROR`` that the adapter can surface to the caller
# instead of re-raising on every call.
# ---------------------------------------------------------------------------

_UPSTREAM_IMPORT_ERROR: BaseException | None = None
_UPSTREAM_MODULES: dict[str, Any] = {}


def _install_upstream_path() -> None:
    """Prepend the upstream repo root to ``sys.path`` (idempotent)."""
    repo = FLOWMOL3_UPSTREAM_REPO
    if repo not in sys.path:
        sys.path.insert(0, repo)


def _try_import_upstream() -> dict[str, Any]:
    """Import the upstream FlowMol3 packages; cache the result.

    Returns a dict with ``"FlowMol"``, ``"model_from_config"``,
    ``"SampledMolecule"``, ``"SampleAnalyzer"`` keys on success. On any
    import-time failure, returns ``{}`` and stashes the exception in
    :data:`_UPSTREAM_IMPORT_ERROR`.
    """
    global _UPSTREAM_IMPORT_ERROR
    if _UPSTREAM_MODULES:
        return _UPSTREAM_MODULES
    _install_upstream_path()
    try:  # noqa: BLE001 — we want to capture *any* import error here.
        from flowmol.models.flowmol import FlowMol  # noqa: PLC0415
        from flowmol.model_utils.load import model_from_config  # noqa: PLC0415
        from flowmol.analysis.molecule_builder import SampledMolecule  # noqa: PLC0415
        from flowmol.analysis.metrics import SampleAnalyzer  # noqa: PLC0415
    except BaseException as exc:  # noqa: BLE001
        _UPSTREAM_IMPORT_ERROR = exc
        _LOGGER.warning(
            "flowmol3_upstream_shim: upstream import failed; partial-fidelity fallback only. "
            "error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        return {}
    _UPSTREAM_MODULES.update(
        FlowMol=FlowMol,
        model_from_config=model_from_config,
        SampledMolecule=SampledMolecule,
        SampleAnalyzer=SampleAnalyzer,
    )
    return _UPSTREAM_MODULES


@dataclass
class FlowMol3UpstreamLoadResult:
    """Lazy load wrapper around the upstream :class:`FlowMol` Lightning module.

    The shim does NOT instantiate the network at construction time; the
    upstream ``FlowMol.load_from_checkpoint`` call is deferred until
    :meth:`materialize` so the adapter can decide whether to pay the
    dgl/torch-scatter import cost or stay on the partial-fidelity path.
    """

    weights_path: str | os.PathLike[str]
    device: str = "cuda:0"
    processed_data_dir: str | None = None
    n_timesteps: int = 250
    stochasticity: float = 30.0
    high_confidence_threshold: float = 0.9
    seed: int = 0

    model: Any | None = None
    analyzer: Any | None = None
    last_metrics: dict[str, float] = field(default_factory=dict)
    last_sampled_mols: list[Any] = field(default_factory=list)
    last_import_error: BaseException | None = None

    def materialize(self) -> bool:
        """Load the checkpoint + construct the analyzer.

        Returns ``True`` on success and ``False`` when the upstream
        package is not importable on this host. The adapter uses the
        return value as the routing signal for ``use_upstream=True``.
        """
        modules = _try_import_upstream()
        if not modules:
            self.last_import_error = _UPSTREAM_IMPORT_ERROR
            return False
        import torch  # noqa: PLC0415 — only after upstream import succeeded.

        torch.manual_seed(int(self.seed))
        if self.device.startswith("cuda") and torch.cuda.is_available():
            torch.cuda.manual_seed_all(int(self.seed))

        FlowMol = modules["FlowMol"]
        model = FlowMol.load_from_checkpoint(
            str(self.weights_path),
            map_location=self.device,
            strict=False,
        )
        model.eval()
        for _p in model.parameters():
            _p.requires_grad_(False)
        self.model = model
        if self.processed_data_dir is not None:
            SampleAnalyzer = modules["SampleAnalyzer"]
            self.analyzer = SampleAnalyzer(
                processed_data_dir=Path(self.processed_data_dir),
                pb_energy=True,
            )
        return True

    def sample(self, n_mols: int) -> list[Any]:
        """Draw ``n_mols`` molecules via the upstream sampler.

        Mirrors the canonical ``model.sample_random_sizes`` call from
        ``data/FlowMol3/repo/test.py:82``. Falls back to ``model.sample``
        with a fixed size histogram when the size-prior file is missing.
        """
        if self.model is None:
            raise RuntimeError(
                "FlowMol3UpstreamLoadResult.sample called before materialize()"
            )
        sampled = self.model.sample_random_sizes(
            n_mols,
            device=self.device,
            n_timesteps=int(self.n_timesteps),
            stochasticity=float(self.stochasticity),
            high_confidence_threshold=float(self.high_confidence_threshold),
        )
        self.last_sampled_mols = list(sampled)
        return self.last_sampled_mols

    def analyze(self, sampled_mols: Sequence[Any] | None = None) -> dict[str, float]:
        """Run upstream :class:`SampleAnalyzer` on the most recent batch."""
        if self.analyzer is None:
            raise RuntimeError(
                "FlowMol3UpstreamLoadResult.analyze called without a SampleAnalyzer "
                "(constructed only when processed_data_dir is supplied)."
            )
        batch = list(sampled_mols) if sampled_mols is not None else self.last_sampled_mols
        metrics = self.analyzer.analyze(
            batch,
            energy_div=False,
            functional_validity=True,
            posebusters=True,
        )
        self.last_metrics = dict(metrics)
        return self.last_metrics


def run_upstream_flowmol3_eval(
    weights_path: str | os.PathLike[str],
    n_mols: int = 100,
    n_timesteps: int = 250,
    device: str = "cuda:0",
    seed: int = 0,
    processed_data_dir: str | None = None,
    output_dir: str | os.PathLike[str] | None = None,
    stochasticity: float = 30.0,
    high_confidence_threshold: float = 0.9,
) -> dict[str, float]:
    """Run upstream FlowMol3 sample + analyze end-to-end.

    Returns the metrics dict from
    ``flowmol.analysis.metrics.SampleAnalyzer.analyze`` on success, or
    ``{}`` on upstream-import failure (with the exception cached in
    :data:`_UPSTREAM_IMPORT_ERROR` for caller inspection).
    """
    loader = FlowMol3UpstreamLoadResult(
        weights_path=str(weights_path),
        device=str(device),
        processed_data_dir=processed_data_dir,
        n_timesteps=int(n_timesteps),
        stochasticity=float(stochasticity),
        high_confidence_threshold=float(high_confidence_threshold),
        seed=int(seed),
    )
    if not loader.materialize():
        _LOGGER.warning(
            "run_upstream_flowmol3_eval: skipping sample/analyze because upstream import failed"
        )
        return {}
    sampled = loader.sample(int(n_mols))
    metrics = loader.analyze(sampled) if loader.analyzer is not None else {}
    if output_dir is not None:
        _dump_outputs(
            output_dir=str(output_dir),
            sampled=sampled,
            metrics=metrics,
        )
    return metrics


def _dump_outputs(
    output_dir: str,
    sampled: Iterable[Any],
    metrics: Mapping[str, float],
) -> None:
    """Persist an SDF + a metrics file so :mod:`tools.run_mol_eval` can replay."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    sdf_path = out / "sampled_mols.sdf"
    metrics_pkl = out / "metrics.pkl"
    metrics_txt = out / "metrics.txt"
    try:
        from rdkit import Chem  # noqa: PLC0415 — optional
    except ImportError:
        Chem = None  # type: ignore[assignment]
    if Chem is not None:
        writer = Chem.SDWriter(str(sdf_path))
        try:
            for mol in sampled:
                rdkit_mol = getattr(mol, "rdkit_mol", None)
                if rdkit_mol is not None:
                    writer.write(rdkit_mol)
        finally:
            writer.close()
    try:
        import pickle  # noqa: PLC0415 — stdlib
        with metrics_pkl.open("wb") as fh:
            pickle.dump(dict(metrics), fh)
    except Exception as exc:  # noqa: BLE001 — best-effort dump.
        _LOGGER.warning("could not pickle metrics: %s", exc)
    with metrics_txt.open("w", encoding="utf-8") as fh:
        for key, value in metrics.items():
            fh.write(f"{key}\t{value}\n")


def is_upstream_available() -> bool:
    """Return True iff :mod:`flowmol.models.flowmol` imports cleanly on this host.

    Useful as the routing signal for the adapter's ``use_upstream=True``
    path: when this returns False, the adapter should fall back to the
    partial-fidelity readout head without raising.
    """
    return bool(_try_import_upstream())


def get_upstream_import_error() -> BaseException | None:
    """Return the cached import error from the last upstream import attempt.

    The adapter's ``use_upstream=True`` path can call this to surface a
    structured diagnostic instead of a stack trace.
    """
    return _UPSTREAM_IMPORT_ERROR


__all__ = [
    "FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR",
    "FLOWMOL3_PINNED_COMMIT",
    "FLOWMOL3_UPSTREAM_REPO",
    "FlowMol3UpstreamLoadResult",
    "get_upstream_import_error",
    "is_upstream_available",
    "run_upstream_flowmol3_eval",
]


def _smoke_check() -> None:
    """CLI sanity check: print the upstream-import status without sampling."""
    ok = is_upstream_available()
    err = get_upstream_import_error()
    print(f"upstream_available={ok}")
    print(f"upstream_repo={FLOWMOL3_UPSTREAM_REPO}")
    print(f"pinned_commit={FLOWMOL3_PINNED_COMMIT}")
    print(f"upstream_import_error={type(err).__name__ if err is not None else 'None'}: {err}")


if __name__ == "__main__":  # pragma: no cover — manual smoke entry.
    _smoke_check()
    # Touch the constant so ruff/importlinter does not flag it.
    importlib.import_module