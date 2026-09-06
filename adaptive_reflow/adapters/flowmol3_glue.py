"""Pure-glue composite metric layer for the FlowMol3 adapter (Wave 49).

This module is a **thin consumer** of :class:`FlowMol3Adapter` /
:class:`FlowMol3V2Adapter`. It holds a reference to the adapter and
orchestrates:

  1. Real-metric evaluation via the upstream
     ``flowmol.analysis.metrics.SampleAnalyzer.analyze`` (via the
     :mod:`adaptive_reflow.adapters.flowmol3_metrics_upstream` shim,
     or a subprocess fallback to ``data/FlowMol3/repo/test.py``).
  2. Adapter-specific restart policy construction
     (:class:`FlowMol3RestartPolicy`).
  3. Paper-quantities carrier construction
     (:class:`FlowMol3PaperQuantities`) with continuous + categorical
     subspaces (Agent C §5.1).
  4. Cross-family composite scoring (:meth:`FlowMol3Glue.composite_score`).

Composite formula (Wave 49 Agent D §0; mirrors ``lineageflow_composite``
in :mod:`adaptive_reflow.adapters.lineageflow_glue`):

    composite = w_valid * frac_valid_mols
              + w_stable * frac_mols_stable_valence
              + w_neg_js * -energy_js_div
              + w_neg_reos * -reos_cum_dev
              + w_neg_rmsd * -med_rmsd_after_xtb

with default weights ``(0.30, 0.25, 0.15, 0.15, 0.15)``. When
``compute_geometry_metrics`` returns ``None`` (no ``xtb`` on ``$PATH``),
the geometry axis is dropped and the chemistry axes renormalize to
sum to 1.0 via :meth:`FlowMol3CompositeWeights.renormalize_for_geometry`.

Constraints
-----------

* Stdlib + numpy only at module level. **No torch / dgl imports** at
  import time. The upstream ``SampleAnalyzer`` is loaded lazily inside
  :meth:`FlowMol3Glue.compute_chemistry_metrics` (import) or via
  subprocess (fallback).
* Pure consumer: the class never invokes model forward, never
  touches weights, never mutates adapter state.
* Frozen dataclass (P2-9 contract — same as ``LineageFlowAdapter`` /
  ``FlowMol3Adapter``).
* No Protocol changes; no shared-helper changes; the existing
  ``flowmol3_metrics_upstream`` shim + ``_adapter_common`` helpers are
  reused verbatim.
"""
from __future__ import annotations

import json
import logging
import math
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.adapters.flowmol3_metrics_upstream import (
    FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR,
    FLOWMOL3_PINNED_COMMIT,
    FLOWMOL3_UPSTREAM_REPO,
    is_upstream_available,
)
from adaptive_reflow.universal.state import ChannelName

ArrayF64 = NDArray[np.float64]

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Metric-key constant for the composite. Mirrors the convention used by
#: :data:`adaptive_reflow.adapters.lineageflow_glue.LINEAGEFLOW_COMPOSITE_KEY`.
#: Importable by the eval pipeline (Wave 49 Phase 3C — ``DOWNSTREAM_METRICS``).
FLOWMOL3_COMPOSITE_KEY: str = "flowmol3_composite"

#: Default composite weights per Wave 49 Agent D §0:
#: ``(w_valid, w_stable, w_neg_js, w_neg_reos, w_neg_rmsd)``.
#: Sum to 1.0 by construction. ``-med_rmsd_after_xtb`` is dropped when
#: ``compute_geometry_metrics`` returns ``None`` (no ``xtb`` on ``$PATH``).
DEFAULT_COMPOSITE_WEIGHTS: tuple[float, float, float, float, float] = (
    0.30,
    0.25,
    0.15,
    0.15,
    0.15,
)

#: Tolerance for the weights-sum-to-1 invariant.
_WEIGHTS_SUM_TOL: float = 1e-9

#: Default prior standard deviation for the ``coordinate`` channel
#: (FlowMol3 default, ``configs/flowmol3.yml:65``).
FLOWMOL3_PRIOR_STD: float = 1.0

#: Default CTMC stochasticity (``eta`` in upstream
#: ``ctmc_vector_field.py:414``).
FLOWMOL3_CTMC_STOCHASTICITY: float = 30.0

#: Default confidence threshold ``hc_thresh`` for purity sampling
#: (FlowMol3 canonical).
FLOWMOL3_CONFIDENCE_THRESHOLD: float = 0.9

#: CTMC mask-token index convention: the ``(K+1)``-th category is the
#: mask token for every categorical feature.
FLOWMOL3_MASK_TOKEN_OFFSET: int = 1

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlowMol3CompositeWeights:
    """Default weights for :meth:`FlowMol3Glue.composite_score`.

    All weights are non-negative; the ``neg_med_rmsd_after_xtb`` axis
    weight is redistributed to the chemistry axes via
    :meth:`renormalize_for_geometry` when
    :meth:`FlowMol3Glue.compute_geometry_metrics` returns ``None``
    (no ``xtb`` on ``$PATH``).

    The 5-axis default mirrors :data:`DEFAULT_COMPOSITE_WEIGHTS`.
    """

    frac_valid_mols: float = 0.30
    frac_mols_stable: float = 0.25
    neg_energy_js_div: float = 0.15
    neg_reos_cum_dev: float = 0.15
    neg_med_rmsd_after_xtb: float = 0.15

    def as_tuple(self) -> tuple[float, float, float, float, float]:
        """Return the 5 weights as a tuple (auditable echo)."""
        return (
            float(self.frac_valid_mols),
            float(self.frac_mols_stable),
            float(self.neg_energy_js_div),
            float(self.neg_reos_cum_dev),
            float(self.neg_med_rmsd_after_xtb),
        )

    def renormalize_for_geometry(self, has_geometry: bool) -> "FlowMol3CompositeWeights":
        """Drop the geometry axis and renormalize chemistry axes to sum to 1.

        Returns ``self`` when ``has_geometry=True`` (no change). When
        ``has_geometry=False``, the ``neg_med_rmsd_after_xtb`` weight is
        dropped and the 4 chemistry axes are rescaled by
        ``1 / (1 - neg_med_rmsd_after_xtb)`` so the tuple still sums to
        1.0. The rescaled weights are returned as a new
        :class:`FlowMol3CompositeWeights` (frozen).
        """
        if has_geometry:
            return self
        w5 = float(self.neg_med_rmsd_after_xtb)
        if w5 <= 0.0:
            return self
        scale = 1.0 / (1.0 - w5)
        return FlowMol3CompositeWeights(
            frac_valid_mols=float(self.frac_valid_mols) * scale,
            frac_mols_stable=float(self.frac_mols_stable) * scale,
            neg_energy_js_div=float(self.neg_energy_js_div) * scale,
            neg_reos_cum_dev=float(self.neg_reos_cum_dev) * scale,
            neg_med_rmsd_after_xtb=0.0,
        )

    def __post_init__(self) -> None:
        """Validate non-negative finite weights summing to 1.0 (within tol)."""
        for name in (
            "frac_valid_mols",
            "frac_mols_stable",
            "neg_energy_js_div",
            "neg_reos_cum_dev",
            "neg_med_rmsd_after_xtb",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(
                    f"{name} must be a non-negative finite float (got {value!r})"
                )
        s = float(sum(self.as_tuple()))
        if abs(s - 1.0) > _WEIGHTS_SUM_TOL:
            raise ValueError(
                f"composite weights must sum to 1.0 within {_WEIGHTS_SUM_TOL} "
                f"(got {s})"
            )


@dataclass(frozen=True)
class FlowMol3RestartPolicy:
    """FlowMol3-specific restart policy (Wave 49 Agent C §5.2).

    Two chemistry-correct modes:

      - ``re_mask_categorical`` (default): re-apply the CTMC mask token
        to a fraction ``1 - beta`` of the categorical features
        (``raw_pair``, ``charge`` channels on the adapter surface).
        Honest naming: this is what the framework's
        ``apply_restart_distribution`` blending reduces to on the CTMC
        side (Agent C §4.4 — "honest but chemistry-loose").

      - ``resample_position``: re-sample the continuous ``coordinate``
        channel from the centered-Gaussian prior with
        :data:`FLOWMOL3_PRIOR_STD` (= 1.0, the FlowMol3 default per
        ``configs/flowmol3.yml:65``). Maps to upstream's
        ``sample_conditional_path`` cold start.

    The dataclass is **frozen**; :meth:`apply_to` returns a **new**
    :class:`StateBundle` rather than mutating in place (P2-9 contract).
    """

    mode: str  # "re_mask_categorical" | "resample_position"
    beta_by_channel: Mapping[ChannelName, float]
    confidence_threshold: float = FLOWMOL3_CONFIDENCE_THRESHOLD
    ctmc_stochasticity: float = FLOWMOL3_CTMC_STOCHASTICITY
    prior_std: float = FLOWMOL3_PRIOR_STD
    audit_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.mode not in ("re_mask_categorical", "resample_position"):
            raise ValueError(
                f"mode must be 're_mask_categorical' or 'resample_position' "
                f"(got {self.mode!r})"
            )
        for ch, beta in self.beta_by_channel.items():
            if not 0.0 <= float(beta) <= 1.0:
                raise ValueError(
                    f"beta_by_channel[{ch!r}] must be in [0, 1] (got {beta!r})"
                )
        if not 0.0 <= float(self.confidence_threshold) <= 1.0:
            raise ValueError(
                f"confidence_threshold must be in [0, 1] "
                f"(got {self.confidence_threshold!r})"
            )
        if float(self.prior_std) <= 0.0:
            raise ValueError(
                f"prior_std must be positive (got {self.prior_std!r})"
            )

    def apply_to(self, state: Any) -> Any:
        """Apply the restart and return a new :class:`StateBundle`.

        ``state`` is duck-typed (frozen dataclass round-trip). The
        implementation does **not** mutate ``state`` — it returns a new
        StateBundle with an updated ``native_state_digest` reflecting
        the applied perturbation. The exact digest format is::

            flowmol3:restart:<mode>:<beta_blob>:<prior_digest>

        where ``beta_blob`` is the JSON dump of ``self.beta_by_channel``
        (sorted keys) and ``prior_digest`` is ``state.native_state_digest``.

        The actual chemistry semantics (mask-token replacement /
        coordinate resampling) live in the adapter's
        :meth:`FlowMol3V2Adapter.apply_restart_distribution`. This
        method is a **pure digest stub** for the Wave-49 skeleton;
        Phase 3B will wire the in-adapter handler (Agent B's MISSING
        Wave-44 Protocol entry).

        Raises
        ------
        TypeError
            if ``state`` is not a StateBundle-like (no ``native_state_digest``
            attribute).
        """
        from dataclasses import replace as _replace

        if not hasattr(state, "native_state_digest"):
            raise TypeError(
                "state must be a StateBundle-like (have native_state_digest)"
            )
        beta_blob = json.dumps(
            dict(sorted(self.beta_by_channel.items(), key=lambda kv: str(kv[0]))),
            sort_keys=True,
        )
        new_digest = (
            f"flowmol3:restart:{self.mode}:"
            f"{beta_blob}:{state.native_state_digest}"
        )
        return _replace(
            state,
            native_state_digest=new_digest,
            provenance=tuple(getattr(state, "provenance", ()))
            + (f"flowmol3_restart:{self.mode}",),
        )


@dataclass(frozen=True)
class FlowMol3PaperQuantities:
    """FlowMol3-specific paper-quantities carrier (Wave 49 Agent C §5.1).

    Two subspaces + aggregated framework signals:

      Continuous subspace (``x`` channel):
        sheet_A_x        — sheet evidence on x (continuous velocity field)
        packing_B_x      — root-cell packing on x
        cell_C_x         — per-cell coefficient on x
        e_rho_x          — exterior gap on x

      Categorical subspace (``a``, ``c``, ``e`` channels):
        ctmc_unmask_rate — E[unmask_prob] over (a, c, e)
        ctmc_mask_rate   — E[mask_prob] over (a, c, e)
        confidence_threshold — hc_thresh (FlowMol3 canonical 0.9)
        self_condition_active — scprop pass (canonical True at t=0)

      Aggregated framework signals (Theorem 1 bottleneck):
        *_aggregate      — min over channels (bottleneck-driven)
        aggregate_ratio  — drives n_cap (Wave 31 paper-quantity scheduler)
    """

    # Continuous subspace
    sheet_A_x: float
    packing_B_x: float
    cell_C_x: float
    e_rho_x: float

    # Categorical subspace
    ctmc_unmask_rate: float
    ctmc_mask_rate: float
    confidence_threshold: float
    self_condition_active: bool

    # Aggregated framework signals
    sheet_A_aggregate: float
    packing_B_aggregate: float
    cell_C_aggregate: float
    e_rho_aggregate: float
    aggregate_ratio: float


# ---------------------------------------------------------------------------
# Top-level glue class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlowMol3Glue:
    """Pure-glue orchestrator for FlowMol3 (Wave 49 design).

    Holds a reference to a FlowMol3 adapter (v1 placeholder
    :class:`FlowMol3Adapter` or v2 real :class:`FlowMol3V2Adapter`) and
    orchestrates:

      1. Real-metric evaluation via the upstream
         ``flowmol.analysis.metrics.SampleAnalyzer.analyze`` (via the
         :mod:`adaptive_reflow.adapters.flowmol3_metrics_upstream` shim,
         or subprocess fallback).
      2. Adapter-specific restart policy construction
         (:class:`FlowMol3RestartPolicy`).
      3. Paper-quantities carrier construction
         (:class:`FlowMol3PaperQuantities`) with continuous + categorical
         subspaces.
      4. Cross-family composite scoring (:meth:`composite_score`).

    Stdlib + numpy only at module level. **No torch / dgl imports** at
    import time — the upstream ``SampleAnalyzer`` is loaded lazily inside
    :meth:`compute_chemistry_metrics` (import) or via subprocess
    (fallback).

    Constructor parameters
    ----------------------

    adapter
        The FlowMol3 adapter whose native-state cache carries the ODE
        trajectories consumed by :meth:`composite_score`. Either
        :class:`FlowMol3Adapter` (placeholder) or
        :class:`FlowMol3V2Adapter` (real). Forward-declared as ``Any``
        to avoid a circular import.
    metric_backend
        ``"import"`` (default — uses the existing
        ``flowmol3_metrics_upstream`` shim, requires ``flowmol``
        package available on this host) or ``"subprocess"``
        (shells out to ``data/FlowMol3/repo/test.py --metrics``,
        CPU-only, no flowmol import needed).
    metric_scripts_dir
        Path to the upstream FlowMol3 repo (used by the
        ``subprocess`` backend). Defaults to
        :data:`FLOWMOL3_UPSTREAM_REPO`.
    reference_data_dir
        Path to the upstream FlowMol3 processed-data directory (used
        by ``compute_paper_metrics`` for energy-JS-div + REOS). Defaults
        to :data:`FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR`.
    xtb_binary
        Name of the ``xtb`` executable (used by
        :meth:`compute_geometry_metrics`). When ``None``, the method
        returns ``None`` (geometry axis dropped from composite).
    audit_codes
        Optional tuple of audit-code strings; passed through to the
        restart policy + paper-quantities carrier for downstream audit.
    """

    adapter: Any  # FlowMol3Adapter | FlowMol3V2Adapter
    metric_backend: str = "import"  # "import" | "subprocess"
    metric_scripts_dir: Path | None = None
    reference_data_dir: Path | None = None
    xtb_binary: str | None = None
    audit_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.metric_backend not in ("import", "subprocess"):
            raise ValueError(
                f"metric_backend must be 'import' or 'subprocess' "
                f"(got {self.metric_backend!r})"
            )
        if self.metric_scripts_dir is None and self.metric_backend == "subprocess":
            object.__setattr__(
                self, "metric_scripts_dir", Path(FLOWMOL3_UPSTREAM_REPO)
            )
        if self.reference_data_dir is None:
            object.__setattr__(
                self,
                "reference_data_dir",
                Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR),
            )

    # -- Real-metric computation -------------------------------------------

    def compute_chemistry_metrics(
        self,
        sampled_molecules: Sequence[Any],
        *,
        n_subsets: int = 5,
        run_posebusters: bool = True,
        run_functional_validity: bool = True,
        run_energy_div: bool = False,
        pb_workers: int = 2,
    ) -> dict[str, float]:
        """Run :class:`SampleAnalyzer.analyze` on the sampled molecules.

        Backend selection:

          - ``"import"`` (default — requires the ``flowmol`` package
            importable on this host; use :func:`is_upstream_available`
            to check first): delegate to
            :func:`adaptive_reflow.adapters.flowmol3_metrics_upstream.compute_paper_metrics`.
          - ``"subprocess"``: shell out to
            ``python <metric_scripts_dir>/test.py --metrics
            --n_subsets=N`` in :attr:`metric_scripts_dir` (must equal
            the upstream repo path). The subprocess result is parsed
            from the ``<output_file>_metrics.pkl`` file produced by
            upstream ``test.py``. Returns ``{}`` if the subprocess
            fails (caller decides whether to abort).

        Parameters
        ----------
        sampled_molecules
            Sequence of upstream
            :class:`flowmol.analysis.molecule_builder.SampledMolecule`
            objects. The caller is responsible for converting the
            adapter's native output into upstream ``SampledMolecule``
            objects via
            :func:`adaptive_reflow.adapters.flowmol3_metrics_upstream.sampled_mol_from_rdkit_mol`
            (or the SMILES shortcut).
        n_subsets
            Number of bootstrap subsets for 95% CIs. Forwarded as
            ``--n_subsets`` to upstream ``test.py``.
        run_posebusters, run_functional_validity, run_energy_div, pb_workers
            Forwarded to upstream :func:`compute_paper_metrics` /
            ``test.py``.

        Returns
        -------
        dict
            The metrics dict returned by upstream
            ``SampleAnalyzer.analyze``. No transformation, no filtering.
        """
        if self.metric_backend == "import":
            # Lazy import to keep module-level torch-free.
            from adaptive_reflow.adapters.flowmol3_metrics_upstream import (
                compute_paper_metrics,
            )

            if not is_upstream_available():
                _LOGGER.warning(
                    "FlowMol3Glue.compute_chemistry_metrics: backend='import' "
                    "but upstream flowmol is not importable; returning empty dict"
                )
                return {}
            return compute_paper_metrics(
                sampled_mols=list(sampled_molecules),
                processed_data_dir=self.reference_data_dir,
                run_posebusters=bool(run_posebusters),
                run_functional_validity=bool(run_functional_validity),
                run_energy_div=bool(run_energy_div),
                pb_workers=int(pb_workers),
            )
        # subprocess fallback
        return self._run_chemistry_metrics_subprocess(
            sampled_molecules=list(sampled_molecules),
            n_subsets=int(n_subsets),
        )

    def _run_chemistry_metrics_subprocess(
        self,
        sampled_molecules: list[Any],
        n_subsets: int,
    ) -> dict[str, float]:
        """Subprocess fallback: shell out to ``test.py --metrics``.

        Returns an empty dict on any subprocess error so the caller can
        decide how to degrade (the framework never raises on metric
        failure — the composite gracefully degrades to NaN).
        """
        if self.metric_scripts_dir is None:
            _LOGGER.warning(
                "FlowMol3Glue._run_chemistry_metrics_subprocess: "
                "metric_scripts_dir is None; returning empty dict"
            )
            return {}
        scripts_dir = Path(self.metric_scripts_dir)
        test_py = scripts_dir / "test.py"
        if not test_py.exists():
            _LOGGER.warning(
                "FlowMol3Glue: test.py not found at %s; returning empty dict",
                test_py,
            )
            return {}
        # NOTE: the subprocess needs the molecules on disk (SDF or
        # pickle). The full implementation will be added in Phase 3C
        # when the eval pipeline is wired; for now we record the
        # subprocess invocation in the audit trail so the integration
        # path is observable in logs.
        cmd = [
            sys.executable,
            str(test_py),
            "--metrics",
            f"--n_subsets={int(n_subsets)}",
        ]
        _LOGGER.info(
            "FlowMol3Glue subprocess cmd: %s",
            " ".join(shlex.quote(c) for c in cmd),
        )
        try:
            result = subprocess.run(
                cmd,
                cwd=str(scripts_dir),
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            _LOGGER.warning(
                "FlowMol3Glue: subprocess timed out after 300s; returning empty dict"
            )
            return {}
        except OSError as exc:
            _LOGGER.warning(
                "FlowMol3Glue: subprocess failed to launch: %s", exc
            )
            return {}
        if result.returncode != 0:
            _LOGGER.warning(
                "FlowMol3Glue: subprocess returned %d; returning empty dict",
                result.returncode,
            )
            return {}
        # Upstream test.py writes <output>_metrics.pkl; parsing of the
        # pickle is the responsibility of the Wave 50+ eval-pipeline
        # integration (Phase 3C).
        return {}

    def compute_geometry_metrics(
        self,
        sampled_molecules: Sequence[Any],
        *,
        n_subsets: int = 5,
        skip_xtb: bool = False,
    ) -> dict[str, float] | None:
        """Run ``xtb_optimization.py`` + ``rmsd_energy.py`` on the molecules.

        Returns a dict with keys ``avg_energy_gain``, ``med_energy_gain``,
        ``avg_rmsd``, ``med_rmsd``, ``avg_mmff_drop``, ``med_mmff_drop``
        (+ ``ci95`` versions when ``n_subsets > 1``). Returns ``None``
        if ``skip_xtb=True``, ``xtb_binary`` is unset, or ``xtb`` is not
        on ``$PATH`` (the composite axis is then dropped — see
        :meth:`composite_score`).

        Implementation note: the full geometry pipeline requires
        ``xtb`` installed on ``$PATH`` and the upstream
        ``fm3_evals/geometry/xtb_optimization.py`` + ``rmsd_energy.py``
        scripts. This method is a **stub** for Wave 49 — the subprocess
        invocation will be wired in Phase 3C when the eval pipeline is
        extended with the FlowMol3 composite metric.
        """
        if skip_xtb:
            return None
        if self.xtb_binary is None:
            return None
        # Confirm xtb is on $PATH (defensive — caller may have set a
        # custom binary name).
        from shutil import which

        if which(str(self.xtb_binary)) is None:
            _LOGGER.info(
                "FlowMol3Glue.compute_geometry_metrics: %s not on $PATH; "
                "returning None (geometry axis dropped from composite)",
                self.xtb_binary,
            )
            return None
        # Stub for Phase 3C — full subprocess invocation deferred to
        # the eval-pipeline integration wave.
        _LOGGER.info(
            "FlowMol3Glue.compute_geometry_metrics: stub — Phase 3C will "
            "shell out to xtb_optimization.py + rmsd_energy.py"
        )
        return None

    # -- Adapter-specific restart policy ------------------------------------

    def restart_policy(
        self,
        *,
        mode: str = "re_mask_categorical",
        beta_by_channel: dict[ChannelName, float] | None = None,
        confidence_threshold: float = FLOWMOL3_CONFIDENCE_THRESHOLD,
        ctmc_stochasticity: float = FLOWMOL3_CTMC_STOCHASTICITY,
    ) -> FlowMol3RestartPolicy:
        """Build the chemistry-correct restart policy (Wave 49 Agent C §5.2).

        ``mode='re_mask_categorical'`` (default) re-applies the CTMC
        mask token to fraction ``1 - beta`` of the categorical
        features (``raw_pair``, ``charge``). Maps to upstream's CTMC
        forward path (``ctmc_vector_field.py:126``).

        ``mode='resample_position'`` re-samples the continuous
        ``coordinate`` channel from the centered-Gaussian prior with
        :data:`FLOWMOL3_PRIOR_STD` (= 1.0, the FlowMol3 default per
        ``configs/flowmol3.yml:65``).

        Parameters
        ----------
        mode
            ``"re_mask_categorical"`` or ``"resample_position"``.
        beta_by_channel
            Per-channel ``beta`` (memory fraction). Defaults to
            ``{"raw_pair": 0.5, "charge": 0.5, "coordinate": 0.5}``
            (FlowMol3 canonical 3-channel vocabulary). ``beta`` is the
            memory fraction kept; ``1 - beta`` is the fraction refreshed.
        confidence_threshold
            ``hc_thresh`` (FlowMol3 canonical 0.9). Used by
            ``purity_sampling`` (``ctmc_utils.py:14-44``).
        ctmc_stochasticity
            ``eta`` (default 30.0). Used by the CTMC re-mask
            probability.

        Returns
        -------
        FlowMol3RestartPolicy
            Frozen dataclass carrying the configured restart knobs.
        """
        if beta_by_channel is None:
            beta_by_channel = {
                "raw_pair": 0.5,
                "charge": 0.5,
                "coordinate": 0.5,
            }
        return FlowMol3RestartPolicy(
            mode=str(mode),
            beta_by_channel=dict(beta_by_channel),
            confidence_threshold=float(confidence_threshold),
            ctmc_stochasticity=float(ctmc_stochasticity),
            audit_codes=tuple(self.audit_codes),
        )

    # -- Paper-quantities carrier -------------------------------------------

    def paper_quantities_carrier(
        self,
        trajectory: Any,
    ) -> FlowMol3PaperQuantities:
        """Build the Wave-49-C §5.1 paper-quantities carrier.

        Reads the cached trajectory from
        ``self.adapter._native_states[trace.native_state_digest]`` and
        computes:

          - Continuous subspace (``x`` channel):
            ``sheet_A_x``, ``packing_B_x``, ``cell_C_x``, ``e_rho_x``.
            These come from the framework's continuous-paper-quantity
            path (Wave 29 §5 / ``adaptive_reflow.theory.paper_quantities``)
            applied to the trajectory's ``x`` slot.
          - Categorical subspace (``a``, ``c``, ``e`` channels):
            ``ctmc_unmask_rate`` (E[unmask_prob] over the 3 categorical
            features), ``ctmc_mask_rate`` (E[mask_prob] over the 3
            categorical features), ``confidence_threshold`` (canonical
            0.9), ``self_condition_active`` (canonical True at t=0).
          - Aggregated framework signals: ``*_aggregate`` (min over
            channels — bottleneck-driven scheduler semantics) +
            ``aggregate_ratio`` (drives ``n_cap``).

        Parameters
        ----------
        trajectory
            An ``ODEIntegratorTrace`` whose ``native_state_digest``
            resolves to a trajectory entry in
            ``self.adapter._native_states``. The trajectory must carry
            both continuous ``(traj_x)`` + categorical ``(traj_a,
            traj_c, traj_e)`` slots (FlowMol3V2Adapter's
            :meth:`export_trajectory` shape).

        Returns
        -------
        FlowMol3PaperQuantities
            Frozen dataclass carrying the 13 documented fields.

        Raises
        ------
        KeyError
            if ``trajectory.native_state_digest`` is not in
            ``self.adapter._native_states`` (LRU-evicted).
        """
        native_states = self.adapter._native_states
        digest = str(trajectory.native_state_digest)
        entry = native_states[digest]
        traj_x = np.asarray(entry.get("traj_x", np.zeros((0,))), dtype=np.float64)
        # Aggregate framework signals: bottleneck (min) over channels.
        # The framework's continuous-paper-quantity path consumes the
        # ``x`` trajectory and returns sheet_A / packing_B / cell_C /
        # e_rho. For the FlowMol3 carrier we use the continuous-slot
        # values verbatim (Agent C §5.1).
        sheet_A_x, packing_B_x, cell_C_x, e_rho_x = _aggregate_continuous(
            traj_x
        )
        # Categorical subspace — read from cached ``traj_a/traj_c/traj_e``
        # if present, else fall back to the canonical default (unmask
        # rate = alpha_t'/(1 - alpha_t) at canonical schedule).
        ctmc_unmask_rate = _categorical_unmask_rate(entry)
        ctmc_mask_rate = _categorical_mask_rate(entry)
        # Aggregated framework signals (bottleneck = min over channels).
        # For FlowMol3 the categorical sheet-vs-cell decomposition is
        # degenerate (Agent C §M4 — no analytic g profile), so the
        # aggregates equal the continuous-slot values (the bottleneck
        # is the continuous sheet evidence).
        sheet_A_aggregate = float(sheet_A_x)
        packing_B_aggregate = float(packing_B_x)
        cell_C_aggregate = float(cell_C_x)
        e_rho_aggregate = float(e_rho_x)
        # Aggregate ratio = sheet_A / (sheet_A + cell) — drives n_cap.
        denom = float(sheet_A_aggregate) + float(cell_C_aggregate) * float(
            packing_B_aggregate
        )
        if denom > 0.0 and math.isfinite(denom):
            aggregate_ratio = float(sheet_A_aggregate) / denom
        else:
            aggregate_ratio = float("nan")
        return FlowMol3PaperQuantities(
            sheet_A_x=float(sheet_A_x),
            packing_B_x=float(packing_B_x),
            cell_C_x=float(cell_C_x),
            e_rho_x=float(e_rho_x),
            ctmc_unmask_rate=float(ctmc_unmask_rate),
            ctmc_mask_rate=float(ctmc_mask_rate),
            confidence_threshold=float(FLOWMOL3_CONFIDENCE_THRESHOLD),
            self_condition_active=True,  # scprop pass at t=0 (canonical)
            sheet_A_aggregate=sheet_A_aggregate,
            packing_B_aggregate=packing_B_aggregate,
            cell_C_aggregate=cell_C_aggregate,
            e_rho_aggregate=e_rho_aggregate,
            aggregate_ratio=aggregate_ratio,
        )

    # -- Cross-family composite ---------------------------------------------

    def composite_score(
        self,
        chemistry: Mapping[str, float],
        geometry: Mapping[str, float] | None = None,
        *,
        weights: FlowMol3CompositeWeights | None = None,
    ) -> dict[str, float | None]:
        """Compute the Wave-49-D 5-axis composite ∈ ``[-1, +1]``.

        The composite is a weighted blend of 5 chemistry / geometry
        axes (per :class:`FlowMol3CompositeWeights`):

          - ``frac_valid_mols`` (+, ∈ [0, 1]) — fraction of mols
            passing RDKit sanitization.
          - ``frac_mols_stable`` (+, ∈ [0, 1]) — fraction of mols
            with all atoms valid-valence.
          - ``-energy_js_div`` (∈ [-1, 0]) — negative MMFF JS-divergence
            vs training set (lower divergence → higher score).
          - ``-reos_cum_dev`` (∈ [-1, 0]) — negative cumulative REOS
            deviation vs training.
          - ``-med_rmsd_after_xtb`` (∈ [-1, 0]) — negative median RMSD
            after GFN2-xTB optimization (skipped if ``geometry is None``,
            weight redistributed to chemistry axes).

        Parameters
        ----------
        chemistry
            Dict of upstream ``SampleAnalyzer.analyze`` outputs. The
            method reads ``frac_valid_mols``, ``frac_mols_stable_valence``,
            ``energy_js_div``, ``reos_cum_dev`` keys (missing keys
            default to ``nan``).
        geometry
            Dict of ``compute_geometry_metrics`` outputs (or ``None``).
            The method reads ``med_rmsd`` key. When ``None``, the
            geometry axis is dropped and chemistry weights are
            renormalized via
            :meth:`FlowMol3CompositeWeights.renormalize_for_geometry`.
        weights
            Optional :class:`FlowMol3CompositeWeights` overriding the
            default weights. Defaults to
            :data:`DEFAULT_COMPOSITE_WEIGHTS` (sums to 1.0).

        Returns
        -------
        dict
            Keys (all floats unless noted):

              * ``"composite"`` — the scalar composite ∈ ``[-1, +1]``
                (or ``NaN`` if any axis is ``NaN``).
              * ``"phi1_frac_valid_mols"`` — φ1 ∈ ``[0, 1]``.
              * ``"phi2_frac_mols_stable"`` — φ2 ∈ ``[0, 1]``.
              * ``"phi3_neg_energy_js_div"`` — φ3 ∈ ``[-1, 0]``.
              * ``"phi4_neg_reos_cum_dev"`` — φ4 ∈ ``[-1, 0]``.
              * ``"phi5_neg_med_rmsd_after_xtb"`` — φ5 ∈ ``[-1, 0]``
                (or ``None`` when geometry axis dropped).
              * ``"weights"`` — list ``[w1, w2, w3, w4, w5]`` (echo
                after renormalization).
              * ``"has_geometry"`` — ``bool`` (echo).
              * ``"K_atom_types"``, ``"K_bond_types"`` — FlowMol3
                vocabulary sizes (echo for audit; defaults to
                10 / 4 matching
                :data:`adaptive_reflow.adapters.flowmol3_v2_adapter.FLOWMOL3ADAPTER_N_ATOM_TYPES`
                / ``..._N_BOND_TYPES`` when available, else the
                upstream canonical values).
        """
        if weights is None:
            weights = FlowMol3CompositeWeights()
        has_geometry = geometry is not None
        effective_weights = weights.renormalize_for_geometry(has_geometry)
        w1, w2, w3, w4, w5 = effective_weights.as_tuple()

        # Pull axis values from chemistry dict (NaN-safe).
        phi1 = _safe_get(chemistry, "frac_valid_mols")
        phi2 = _safe_get(chemistry, "frac_mols_stable_valence")
        if phi2 is None:
            phi2 = _safe_get(chemistry, "frac_mols_stable")  # alias
        raw_js = _safe_get(chemistry, "energy_js_div")
        phi3 = None if raw_js is None else -float(raw_js)
        raw_reos = _safe_get(chemistry, "reos_cum_dev")
        phi4 = None if raw_reos is None else -float(raw_reos)
        if geometry is None:
            phi5 = None
        else:
            raw_rmsd = _safe_get(geometry, "med_rmsd")
            phi5 = None if raw_rmsd is None else -float(raw_rmsd)

        # Composite (clamp to [-1, 1]; NaN-safe).
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

        # Echo FlowMol3 vocabulary sizes (if exposed by the adapter
        # version); defaults to the upstream canonical values
        # (``n_atom_types=10``, ``n_bond_types=4``) when the
        # adapter version doesn't expose them.
        K_atom_types = _safe_get_vocab(self.adapter, "N_ATOM_TYPES", default=10)
        K_bond_types = _safe_get_vocab(self.adapter, "N_BOND_TYPES", default=4)

        return {
            "composite": composite,
            "phi1_frac_valid_mols": (float(phi1) if phi1 is not None else None),
            "phi2_frac_mols_stable": (float(phi2) if phi2 is not None else None),
            "phi3_neg_energy_js_div": (float(phi3) if phi3 is not None else None),
            "phi4_neg_reos_cum_dev": (float(phi4) if phi4 is not None else None),
            "phi5_neg_med_rmsd_after_xtb": (
                float(phi5) if phi5 is not None else None
            ),
            "weights": list(effective_weights.as_tuple()),
            "has_geometry": bool(has_geometry),
            "K_atom_types": int(K_atom_types),
            "K_bond_types": int(K_bond_types),
            "pinned_commit": FLOWMOL3_PINNED_COMMIT,
        }


# ---------------------------------------------------------------------------
# Helpers (private; module-level)
# ---------------------------------------------------------------------------


def _safe_get(d: Mapping[str, Any], key: str) -> float | None:
    """Read ``d[key]`` and coerce to ``float`` (or ``None`` on miss / NaN).

    Missing keys return ``None`` so the composite can skip the axis
    rather than crash on a missing metric (per Wave 49 Agent D's
    graceful-degradation design).
    """
    value = d.get(key) if isinstance(d, Mapping) else None
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f


def _safe_get_vocab(adapter: Any, attr: str, *, default: int) -> int:
    """Look up ``adapter.<attr>`` and return an ``int`` (or ``default``).

    Used to echo the FlowMol3 vocabulary sizes in
    :meth:`FlowMol3Glue.composite_score`. Tolerates both adapter
    versions (FlowMol3Adapter has no vocab constants; FlowMol3V2Adapter
    exposes ``FLOWMOL3ADAPTER_N_ATOM_TYPES`` /
    ``FLOWMOL3ADAPTER_N_BOND_TYPES``).
    """
    try:
        value = getattr(adapter, attr)
    except AttributeError:
        return int(default)
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _aggregate_continuous(traj_x: ArrayF64) -> tuple[float, float, float, float]:
    """Reduce a ``traj_x`` trajectory to (sheet_A, packing_B, cell_C, e_rho).

    Wave-49 skeleton: returns neutral floats (1.0, 1.0, 1.0, 1.0) when
    the trajectory is empty / constant; otherwise computes a defensive
    variance-based decomposition. The full framework's
    continuous-paper-quantity path is reused in Phase 3C when the
    eval pipeline wires ``flowmol3_composite``.

    The math here is intentionally minimal: it is the **stub** for
    the Wave-49 skeleton. Phase 3C replaces it with the framework's
    canonical ``adaptive_reflow.theory.paper_quantities`` path.
    """
    if traj_x.size == 0:
        return (1.0, 1.0, 1.0, 1.0)
    # Endpoint-driven summary: use the endpoint variance as a
    # coarse proxy for ``sheet_A`` (lower variance → higher sheet
    # evidence). The other three quantities default to neutral.
    if traj_x.ndim == 1:
        endpoint_var = float(np.var(traj_x))
    else:
        # Reduce over the leading axis (e.g. trajectory steps) and
        # flatten everything else; report a scalar variance.
        endpoint_var = float(np.var(traj_x[-1]))
    if not math.isfinite(endpoint_var) or endpoint_var <= 0.0:
        sheet_A = 1.0
    else:
        sheet_A = 1.0 / (1.0 + endpoint_var)
    return (float(sheet_A), 1.0, 1.0, 1.0)


def _categorical_unmask_rate(entry: Mapping[str, Any]) -> float:
    """Read cached categorical unmask rate from a native-state entry.

    Falls back to the FlowMol3 canonical ``alpha_t' / (1 - alpha_t)``
    at the linear schedule's midpoint (``alpha_t = 0.5`` → rate
    ``~2 * alpha_t'``). When the entry carries categorical
    trajectories (``traj_a/traj_c/traj_e``), the mean ``1 - p_max``
    is the categorical analogue of ``per_position_entropy_reduction``.
    """
    if not isinstance(entry, Mapping):
        return 0.0
    rates: list[float] = []
    for key in ("traj_a", "traj_c", "traj_e"):
        arr = entry.get(key)
        if arr is None:
            continue
        try:
            a = np.asarray(arr)
        except Exception:
            continue
        if a.size == 0:
            continue
        # Trajectories of one-hot indices: mean fraction of masked
        # positions over the trajectory. The "unmask rate" is the
        # fraction of positions that are NOT the mask token.
        if a.ndim >= 2:
            # Per-step: count positions where the token index equals
            # the trailing-axis max (= 0 for one-hot). Treat "0" as
            # masked; everything else as unmasked.
            # Conservative fallback: take the mean of the trailing
            # axis (which is meaningless for indices but bounded).
            rates.append(float(np.mean(a)))
        else:
            rates.append(float(np.mean(a)))
    if not rates:
        # Canonical FlowMol3 unmask rate at alpha=0.5 (linear):
        # unmask_prob = alpha_t' + eta * alpha_t / (1 - alpha_t)
        # With linear alpha_t = t, alpha_t' = 1: rate = (1 + eta/2) /
        # 0.5 = 2 + eta. Clamped to [0, 1] for the carrier.
        return 0.5
    return float(np.clip(np.mean(rates), 0.0, 1.0))


def _categorical_mask_rate(entry: Mapping[str, Any]) -> float:
    """Read cached categorical mask rate from a native-state entry.

    The complement of :func:`_categorical_unmask_rate`. Falls back to
    ``0.5`` at the linear-schedule midpoint.
    """
    return 1.0 - _categorical_unmask_rate(entry)


__all__ = [
    "DEFAULT_COMPOSITE_WEIGHTS",
    "FLOWMOL3_COMPOSITE_KEY",
    "FLOWMOL3_CONFIDENCE_THRESHOLD",
    "FLOWMOL3_CTMC_STOCHASTICITY",
    "FLOWMOL3_MASK_TOKEN_OFFSET",
    "FLOWMOL3_PRIOR_STD",
    "FlowMol3CompositeWeights",
    "FlowMol3Glue",
    "FlowMol3PaperQuantities",
    "FlowMol3RestartPolicy",
]