"""Pure-glue composite metric layer for the LineageFlow adapter (Wave 47).

This module is a **thin consumer** of :class:`LineageFlowAdapter`. It
holds a reference to the adapter and computes the 100 % flow-component
composite benchmark per Wave 47 Agent C's design (see
``docs/audit/wave47-eval-pipeline-design.md`` §3 and the Phase-2A
synthesis at ``docs/audit/wave47-glue-design.md`` §3).

The composite is a 3-term scalar in ``[-1, +1]``:

    composite = w1 * phi1 + w2 * phi2 + w3 * phi3

with default weights ``(0.40, 0.35, 0.25)`` and:

* ``phi1 = (H(theta_b) - H(theta_f)) / log K``
  via :func:`adaptive_reflow.adapters._adapter_common.per_position_entropy_reduction`
* ``phi2 = mean(max(theta_f, axis=-1) - max(theta_b, axis=-1))``
* ``phi3 = 2 * mean(argmax(theta_f, axis=-1) != argmax(theta_b, axis=-1)) - 1``

Constraints
-----------

* Stdlib + numpy only at module level. **No torch imports** — this
  glue is import-safe without the LineageFlow sidecar venv.
* Pure consumer: the class never invokes model forward, never
  touches weights, never mutates adapter state.
* Frozen dataclass (P2-9 contract — same as ``LineageFlowAdapter``).
* No Protocol changes; no shared-helper changes; the existing
  ``per_position_entropy_reduction`` is reused verbatim.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, TypeAlias

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.adapters._adapter_common import (
    per_position_entropy_reduction,
)

ArrayF64: TypeAlias = NDArray[np.float64]


#: Per-position categorical vocabulary size for LineageFlow (Pfam-RP55
#: alphabet: 20 standard AAs + BOS + EOS + PAD + gap + MSA-mask). Matches
#: ``LINEAGEFLOW_VOCAB_SIZE`` in :mod:`adaptive_reflow.adapters.lineageflow`.
LINEAGEFLOW_VOCAB_SIZE: int = 33

#: Default composite weights per Wave 47 Agent C §3.3:
#: ``(w_entropy, w_max_prob, w_turnover)``. Sum to 1.0 by construction.
DEFAULT_COMPOSITE_WEIGHTS: tuple[float, float, float] = (0.40, 0.35, 0.25)

#: Metric-key constant for the composite. Mirrors the convention used by
#: the existing ``PER_POSITION_ENTROPY_REDUCTION`` key in
#: :mod:`adaptive_reflow.adapters.lineageflow`. Importable by the eval
#: pipeline (Agent C §4.1 DOWNSTREAM_METRICS entry).
LINEAGEFLOW_COMPOSITE_KEY: str = "lineageflow_composite"

#: Tolerance for the weights-sum-to-1 invariant (the shared helper
#: works in float64; 1e-9 is generous).
_WEIGHTS_SUM_TOL: float = 1e-9


@dataclass(frozen=True)
class LineageFlowGlue:
    """Pure-glue composite metric layer for LineageFlow (Wave 47).

    Holds a reference to a :class:`LineageFlowAdapter` and computes the
    100 % flow-component composite benchmark per Wave 47 Agent C. Stdlib
    + numpy only. **No model logic lives here** — that lives in the
    adapter; the glue layer is a pure consumer.

    Constructor parameters
    ----------------------

    adapter
        The :class:`LineageFlowAdapter` whose native-state cache carries
        the ODE trajectories consumed by :meth:`compute_composite`. The
        adapter must expose ``_native_states`` as a ``dict``-like (the
        concrete adapter uses an ``OrderedDict`` LRU; the glue only
        does ``adapter._native_states[trace.native_state_digest]``).
    """

    adapter: Any  # LineageFlowAdapter (forward-declared as Any to avoid circular import)

    def compute_composite(
        self,
        baseline_trace: Any,
        framework_trace: Any,
        *,
        weights: tuple[float, float, float] = DEFAULT_COMPOSITE_WEIGHTS,
        seed: int | None = None,
        nfe: int | None = None,
    ) -> dict[str, float | None]:
        """Compute the Wave 47 LineageFlow composite benchmark.

        Args:
            baseline_trace: ``ODEIntegratorTrace`` from the baseline arm
                (1 round @ NFE). Must carry ``native_state_digest`` that
                resolves to a trajectory entry in
                ``self.adapter._native_states``.
            framework_trace: ``ODEIntegratorTrace`` from the framework arm
                (``n_rounds`` rounds @ ``ceil(NFE / n_rounds)``).
            weights: ``(w1, w2, w3)`` non-negative floats summing to
                1.0 (default ``(0.40, 0.35, 0.25)``).
            seed: Optional audit-field echo of the run-level seed.
            nfe: Optional audit-field echo of the NFE budget.

        Returns:
            dict with keys (all floats unless noted):
              * ``"composite"`` — the scalar composite ∈ ``[-1, +1]``.
              * ``"phi1_entropy_reduction_normalised"`` — φ1 ∈ ``[-1, +1]``.
              * ``"phi2_max_prob_delta"`` — φ2 ∈ ``[-1, +1]``.
              * ``"phi3_argmax_turnover_signed"`` — φ3 ∈ ``[-1, +1]``.
              * ``"weights"`` — list ``[w1, w2, w3]`` (echo for audit).
              * ``"K"`` — ``LINEAGEFLOW_VOCAB_SIZE = 33`` (echo for audit).
              * ``"seed"`` — echo of the input ``seed`` (or ``None``).
              * ``"nfe"`` — echo of the input ``nfe`` (or ``None``).

        Raises:
            ValueError: if ``weights`` does not sum to 1.0 (within
                ``_WEIGHTS_SUM_TOL``) or any weight is negative.
            KeyError: if a trace's ``native_state_digest`` is not in
                ``self.adapter._native_states`` (LRU-evicted).
        """
        # ---- 1. Validate weights --------------------------------------
        if len(weights) != 3:
            raise ValueError(
                f"weights must have length 3 (got {len(weights)})"
            )
        for w in weights:
            if not math.isfinite(float(w)) or float(w) < 0.0:
                raise ValueError(
                    f"weights must be non-negative finite floats (got {w!r})"
                )
        weights_sum = float(sum(weights))
        if abs(weights_sum - 1.0) > _WEIGHTS_SUM_TOL:
            raise ValueError(
                f"weights must sum to 1.0 within {_WEIGHTS_SUM_TOL} "
                f"(got {weights_sum})"
            )
        w1, w2, w3 = float(weights[0]), float(weights[1]), float(weights[2])

        # ---- 2. Extract trajectory endpoints --------------------------
        theta_b = self._extract_endpoint(baseline_trace)
        theta_f = self._extract_endpoint(framework_trace)

        # ---- 3. Compute the three phi terms ---------------------------
        # phi1: per-position entropy reduction normalised by log K.
        # Uses the shared helper (Wave 45 Agent E / P2-W33-C).
        raw_reduction = per_position_entropy_reduction(theta_b, theta_f)
        log_k = math.log(float(LINEAGEFLOW_VOCAB_SIZE))
        if log_k <= 0.0 or not math.isfinite(raw_reduction):
            # Degenerate K (cannot happen with K=33) or NaN reduction
            # (e.g. too-few samples in theta); surface NaN, do not divide.
            phi1 = float("nan")
        else:
            phi1 = float(raw_reduction) / log_k

        # phi2: mean per-position max-prob delta (framework − baseline).
        max_b = np.max(theta_b, axis=-1)
        max_f = np.max(theta_f, axis=-1)
        phi2 = float(np.mean(max_f - max_b))

        # phi3: argmax turnover signed = 2 * mean(argmax_f != argmax_b) - 1.
        argmax_b = np.argmax(theta_b, axis=-1)
        argmax_f = np.argmax(theta_f, axis=-1)
        turnover = float(np.mean(argmax_f != argmax_b))
        phi3 = 2.0 * turnover - 1.0

        # ---- 4. Composite (clamp to [-1, 1] for numerical safety) -----
        composite_raw = w1 * phi1 + w2 * phi2 + w3 * phi3
        composite = float(
            max(-1.0, min(1.0, composite_raw)) if math.isfinite(composite_raw)
            else float("nan")
        )

        # ---- 5. Audit dict --------------------------------------------
        return {
            "composite": composite,
            "phi1_entropy_reduction_normalised": phi1,
            "phi2_max_prob_delta": phi2,
            "phi3_argmax_turnover_signed": phi3,
            "weights": [w1, w2, w3],  # type: ignore[dict-item]
            "K": int(LINEAGEFLOW_VOCAB_SIZE),
            "seed": (int(seed) if seed is not None else None),
            "nfe": (int(nfe) if nfe is not None else None),
        }

    def _extract_endpoint(self, trace: Any) -> ArrayF64:
        """Pull ``theta = trajectory[-1]`` from the adapter's native-state cache.

        Mirrors the cache-lookup pattern of
        :meth:`LineageFlowAdapter.observe_token_indices` (lineageflow.py:2008-2025).
        LineageFlow's ``observe_token_indices`` is a plain
        ``argmax(trajectory[-1], axis=-1)``, so the cache stores the full
        ``(N+1, L, K)`` trajectory and a chain-walk is **not** required
        (unlike Kanzi's :class:`KanziAdapter.observe_token_indices`).

        Shape contract: returns ``np.ndarray(shape=(L, K), dtype=float64)``.
        ``L`` is variable per trace; ``K`` is fixed at
        :data:`LINEAGEFLOW_VOCAB_SIZE` (= 33).

        Raises:
            KeyError: if ``trace.native_state_digest`` is not in
                ``self.adapter._native_states`` (LRU-evicted).
            AttributeError: if the cached entry lacks a ``"trajectory"``
                key (defensive; should not happen for adapter-produced
                traces).
        """
        native_states = self.adapter._native_states
        digest = str(trace.native_state_digest)
        entry = native_states[digest]
        trajectory = np.asarray(entry["trajectory"], dtype=np.float64)
        # trajectory has shape (N+1, L, K); the endpoint is the last step.
        theta = trajectory[-1]
        # Guard against any future change in cache shape; flatten any
        # leading batch axis to a canonical (L, K).
        if theta.ndim == 3:
            # (B, L, K) — squeeze the batch axis (B=1 in current path).
            theta = theta.reshape(-1, theta.shape[-1]) if theta.shape[0] == 1 else theta[0]
        if theta.ndim != 2:
            raise ValueError(
                f"LineageFlow endpoint must be (L, K); got shape {theta.shape!r}"
            )
        return theta


__all__ = [
    "DEFAULT_COMPOSITE_WEIGHTS",
    "LINEAGEFLOW_COMPOSITE_KEY",
    "LINEAGEFLOW_VOCAB_SIZE",
    "LineageFlowGlue",
]
