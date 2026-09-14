"""Dynamic noise bias (D4 — iterative Theorem 1 application across rounds).

This module realises the user's core insight:
"动态把上轮推理结果加入下一轮噪声偏置" (inject the previous round's
inference result as the next round's noise bias) as the iterative
application of paper Theorem 1 across the re-inference loop.

Paper Theorem 1 (Li 2026, lines 87-92) gives BL-distance convergence
of the noised posterior ``mu_{g,eps}`` to the sheet measure ``nu_g``
as ``eps -> 0``. The proof combines four estimates (Lemma 2 sheet-
tube rescaling, Lemma 3 per-root-cell bound ``C_g e^{-z^2/4} eps^2``,
Lemma 4 exterior suppression ``exp(-e_rho / (2 eps^2))``, Lemma 5
Gaussian packing). At each ``eps`` the posterior has the structure
of a Gaussian noise likelihood around a fibre plus a coarea weight on
the sheet.

Iterating Theorem 1 across rounds turns the bounded-Lipschitz
convergence into a per-round convergence trace (selection ratio ->
1 as ``eps -> 0``). The four paper quantities ``A_g``, ``B_g``,
``C_g``, ``e_rho`` jointly constrain the per-round ``eps(r)``
schedule. The natural monotone-decreasing schedule is
``eps(r) = max(e_rho/4, sheet_A * (1 - r/(L-1)))``; the
``e_rho/4`` envelope mirrors :class:`BoundedMergeOperator`'s
``MERGE_PAPER_QUANTITY_FLOOR_LIFTED` for the inject_noise path.

Module boundary
---------------

stdlib-only (math + dataclasses; no numpy, no torch, no I/O, no
mutation of inputs). The math is closed-form; numpy is unnecessary
for the scalar ``eps(r)`` computation.

Public surface
--------------

* :class:`DynamicNoiseBiasProtocol` (abstract)
* :class:`Theorem1DynamicNoiseBias` (canonical continuous-channel impl)
* :class:`CategoricalDynamicNoiseBias` (categorical sibling)
* :class:`IdentityDynamicNoiseBias` (back-compat no-op)
* :func:`default_dynamic_noise_bias` (canonical factory)
* Audit-code constants
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from adaptive_reflow.contracts.dynamic_noise_bias import (
    DynamicNoiseBiasResult,
    PaperQuantitiesSnapshot,
)
from adaptive_reflow.universal.state import ChannelName

# ---------------------------------------------------------------------------
# Module-level constants (audit codes + defaults)
# ---------------------------------------------------------------------------

NEW_DYNAMIC_NOISE_BIAS_COMPUTED: str = "new_dynamic_noise_bias_computed"
NEW_DYNAMIC_NOISE_BIAS_GUMBEL_TEMP_COMPUTED: str = "new_dynamic_noise_bias_gumbel_temp_computed"
NEW_DYNAMIC_NOISE_BIAS_EPSILON_NONPOSITIVE: str = "new_dynamic_noise_bias_epsilon_nonpositive"
NEW_DYNAMIC_NOISE_BIAS_SHEET_NONPOSITIVE: str = "new_dynamic_noise_bias_sheet_nonpositive"
NEW_DYNAMIC_NOISE_BIAS_EPSILON_FLOORED_BY_PAPER_EXTERIOR_GAP: str = (
    "new_dynamic_noise_bias_epsilon_floored_by_paper_exterior_gap"
)
NEW_DYNAMIC_NOISE_BIAS_PREV_ANCHORED_TO_PREV_ENDPOINT: str = (
    "new_dynamic_noise_bias_prev_anchored_to_prev_endpoint"
)
NEW_DYNAMIC_NOISE_BIAS_GUMBEL_HEURISTIC: str = "new_dynamic_noise_bias_gumbel_heuristic"
NEW_DYNAMIC_NOISE_BIAS_NO_MATERIALIZER: str = "new_dynamic_noise_bias_no_materializer"
NEW_DYNAMIC_NOISE_BIAS_DIGEST_ONLY: str = "new_dynamic_noise_bias_digest_only"

DEFAULT_MIN_GUMBEL_TEMP: float = 1e-3
"""Floor for Gumbel-anneal temperature (categorical analog of ``eps``)."""

DEFAULT_DECAY_KIND: str = "linear_decay"
"""Default decay kind tag for ``config_hash`` stability."""


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class DynamicNoiseBiasProtocol(Protocol):
    """Abstract dynamic noise bias — per-round ``eps(r)`` from paper quantities.

    Methods
    -------

    * :meth:`compute_noise_bias` — return a
      :class:`DynamicNoiseBiasResult` for the given
      ``previous_endpoint`` + paper quantities + round index. When
      ``paper_quantities`` is ``None``, implementations SHOULD fall
      back to a schedule-fallback path (see
      :class:`IdentityDynamicNoiseBias`).
    """

    def compute_noise_bias(
        self,
        previous_endpoint: Any,
        paper_quantities: PaperQuantitiesSnapshot | None,
        *,
        round_index: int,
        total_rounds: int,
        channel_domain: str,
        previous_round_sample: Any = None,
        audit_codes: list[str] | None = None,
    ) -> DynamicNoiseBiasResult: ...


# ---------------------------------------------------------------------------
# IdentityDynamicNoiseBias — back-compat no-op (schedule fallback)
# ---------------------------------------------------------------------------


class IdentityDynamicNoiseBias:
    """Back-compat no-op: returns ``epsilon_per_channel = n_cap`` (legacy cosine path).

    For categorical channels returns ``gumbel_temperature_per_channel =
    None`` so the existing Bernoulli-keep / uniform-fresh path remains
    unchanged. Used by callers that have not yet wired
    :class:`PaperQuantitiesSnapshot` to the scheduler.
    """

    FAMILY: str = "identity"

    def __init__(self) -> None:
        self._family = "identity"

    def bias_family(self) -> str:
        return self._family

    def compute_noise_bias(
        self,
        previous_endpoint: Any,
        paper_quantities: PaperQuantitiesSnapshot | None,
        *,
        round_index: int,
        total_rounds: int,
        channel_domain: str,
        previous_round_sample: Any = None,
        audit_codes: list[str] | None = None,
    ) -> DynamicNoiseBiasResult:
        """Return a back-compat result with ``bias_source='schedule_fallback'``."""
        n_cap = 1.0
        if previous_round_sample is not None:
            n_cap_attr = getattr(previous_round_sample, "n_cap_base", None)
            if isinstance(n_cap_attr, (int, float)) and not isinstance(n_cap_attr, bool):
                n_cap = float(n_cap_attr)
        epsilon_per_channel: dict[ChannelName, float] = {ChannelName("default"): n_cap}
        codes: tuple[str, ...] = (NEW_DYNAMIC_NOISE_BIAS_DIGEST_ONLY,)
        if audit_codes is not None:
            audit_codes.extend(codes)
        return DynamicNoiseBiasResult(
            epsilon_per_channel=epsilon_per_channel,
            posterior_mean_proxy=previous_endpoint,
            gumbel_temperature_per_channel=None,
            selection_ratio=0.0,
            audit_codes=codes,
            bias_source="schedule_fallback",
        )


# ---------------------------------------------------------------------------
# Theorem1DynamicNoiseBias — canonical continuous-channel implementation.
# ---------------------------------------------------------------------------


class Theorem1DynamicNoiseBias:
    """Canonical paper-grounded implementation of Theorem 1 iterative application.

    Computes ``eps(r) = max(e_rho/4, sheet_A * (1 - r/(L-1)))`` so the
    per-round implicit noise scale decreases monotonically toward
    ``e_rho/4``. The selection ratio at round ``r`` is

        selection_ratio = sheet_A * eps / (sheet_A * eps + cell_C * packing_B * eps^2)

    and converges to ``1`` as ``eps -> 0`` (paper BL-distance
    convergence analogue at finite ``L``).

    The posterior-mean proxy is the ``previous_endpoint`` passed
    through the optional ``materializer`` callable (default: identity).
    """

    FAMILY: str = "theorem1"

    def __init__(
        self,
        *,
        materializer: Any | None = None,
        min_gumbel_temp: float = DEFAULT_MIN_GUMBEL_TEMP,
        decay_kind: str = DEFAULT_DECAY_KIND,
    ) -> None:
        if not isinstance(min_gumbel_temp, (int, float)) or isinstance(min_gumbel_temp, bool):
            raise ValueError("min_gumbel_temp_must_be_real_number")
        mgt = float(min_gumbel_temp)
        if not math.isfinite(mgt) or mgt <= 0.0:
            raise ValueError(f"min_gumbel_temp_must_be_positive_finite: got {mgt!r}")
        if not isinstance(decay_kind, str) or not decay_kind:
            raise ValueError("decay_kind_must_be_nonempty_str")
        self._materializer = materializer
        self._min_gumbel_temp = mgt
        self._decay_kind = str(decay_kind)

    @property
    def materializer(self) -> Any:
        return self._materializer

    @property
    def min_gumbel_temp(self) -> float:
        return float(self._min_gumbel_temp)

    @property
    def decay_kind(self) -> str:
        return str(self._decay_kind)

    def bias_family(self) -> str:
        return self.FAMILY

    def compute_noise_bias(
        self,
        previous_endpoint: Any,
        paper_quantities: PaperQuantitiesSnapshot | None,
        *,
        round_index: int,
        total_rounds: int,
        channel_domain: str,
        previous_round_sample: Any = None,
        audit_codes: list[str] | None = None,
    ) -> DynamicNoiseBiasResult:
        """Compute the per-round ``eps(r)`` and selection ratio."""
        if paper_quantities is None:
            # Fallback to identity (no paper quantities wired).
            return IdentityDynamicNoiseBias().compute_noise_bias(
                previous_endpoint,
                None,
                round_index=round_index,
                total_rounds=total_rounds,
                channel_domain=channel_domain,
                previous_round_sample=previous_round_sample,
                audit_codes=audit_codes,
            )
        # Lazy-validate: extract values first, fail-closed on the
        # ZERO-sheet case BEFORE raising ValueError so the audit code
        # is emitted and the fallback path engages. Strict validation
        # (NaN / inf / negative) still raises via ValueError.
        sheet_A = float(paper_quantities.sheet_A)
        packing_B = float(paper_quantities.packing_B)
        cell_C = float(paper_quantities.cell_C)
        e_rho = float(paper_quantities.exterior_gap_e_rho)
        for v in (sheet_A, packing_B, cell_C, e_rho):
            if v != v or v in (float("inf"), float("-inf")):
                raise ValueError(
                    f"paper_quantities_invalid:nonfinite_value:{v!r}"
                )
            if v < 0.0:
                raise ValueError(
                    f"paper_quantities_invalid:negative_value:{v!r}"
                )
        if sheet_A == 0.0:
            if audit_codes is not None:
                audit_codes.append(NEW_DYNAMIC_NOISE_BIAS_SHEET_NONPOSITIVE)
            return IdentityDynamicNoiseBias().compute_noise_bias(
                previous_endpoint,
                None,
                round_index=round_index,
                total_rounds=total_rounds,
                channel_domain=channel_domain,
                previous_round_sample=previous_round_sample,
                audit_codes=audit_codes,
            )

        L = max(1, int(total_rounds))
        r = max(0, min(int(round_index), L - 1))
        decay = 1.0 - (r / max(1, L - 1))
        eps_candidate = sheet_A * decay
        envelope = e_rho / 4.0
        if eps_candidate < envelope:
            eps = envelope
            if audit_codes is not None:
                audit_codes.append(NEW_DYNAMIC_NOISE_BIAS_EPSILON_FLOORED_BY_PAPER_EXTERIOR_GAP)
        else:
            eps = eps_candidate
        if eps <= 0.0:
            if audit_codes is not None:
                audit_codes.append(NEW_DYNAMIC_NOISE_BIAS_EPSILON_NONPOSITIVE)
            return IdentityDynamicNoiseBias().compute_noise_bias(
                previous_endpoint,
                None,
                round_index=round_index,
                total_rounds=total_rounds,
                channel_domain=channel_domain,
                previous_round_sample=previous_round_sample,
                audit_codes=audit_codes,
            )

        sheet = sheet_A * eps
        cell = cell_C * packing_B * eps * eps
        denom = sheet + cell
        ratio = 0.0 if denom <= 0.0 else sheet / denom

        # Posterior-mean proxy via materializer (identity if None).
        if self._materializer is None:
            proxy = previous_endpoint
        else:
            try:
                proxy = self._materializer(previous_endpoint, "prev_endpoint")
            except Exception:
                proxy = previous_endpoint

        gumbel: dict[ChannelName, float] | None = None
        if channel_domain in ("discrete", "graph"):
            tau = max(eps, self._min_gumbel_temp)
            gumbel = {ChannelName("default"): float(tau)}
            if audit_codes is not None:
                audit_codes.append(NEW_DYNAMIC_NOISE_BIAS_GUMBEL_TEMP_COMPUTED)
                audit_codes.append(NEW_DYNAMIC_NOISE_BIAS_GUMBEL_HEURISTIC)

        codes: tuple[str, ...] = (
            NEW_DYNAMIC_NOISE_BIAS_COMPUTED,
            NEW_DYNAMIC_NOISE_BIAS_PREV_ANCHORED_TO_PREV_ENDPOINT,
        )
        if audit_codes is not None:
            audit_codes.extend(codes)
        return DynamicNoiseBiasResult(
            epsilon_per_channel={ChannelName("default"): float(eps)},
            posterior_mean_proxy=proxy,
            gumbel_temperature_per_channel=gumbel,
            selection_ratio=float(ratio),
            audit_codes=codes,
            bias_source="prev_endpoint",
        )


# ---------------------------------------------------------------------------
# CategoricalDynamicNoiseBias — categorical sibling (Gumbel temperature)
# ---------------------------------------------------------------------------


class CategoricalDynamicNoiseBias:
    """Categorical sibling: tau(r) = max(eps(r), MIN_GUMBEL_TEMP).

    Implements the categorical analog of the iterative Theorem 1
    selection mechanism via Gumbel-softmax sampling. The
    posterior-mean proxy is the previous endpoint's argmax
    (computed via the optional ``materializer`` callable).

    Audit code :data:`NEW_DYNAMIC_NOISE_BIAS_GUMBEL_HEURISTIC` is
    emitted to mark the implementation as a HEURISTIC anchored on
    the user's insight, NOT a paper-claimed extension. Until the
    categorical Theorem-1 analog (GAP-F10) is stated and proved,
    the categorical implementation's claims are framework-heuristic.
    """

    FAMILY: str = "categorical"

    def __init__(
        self,
        *,
        materializer: Any | None = None,
        min_gumbel_temp: float = DEFAULT_MIN_GUMBEL_TEMP,
    ) -> None:
        if not isinstance(min_gumbel_temp, (int, float)) or isinstance(min_gumbel_temp, bool):
            raise ValueError("min_gumbel_temp_must_be_real_number")
        mgt = float(min_gumbel_temp)
        if not math.isfinite(mgt) or mgt <= 0.0:
            raise ValueError(f"min_gumbel_temp_must_be_positive_finite: got {mgt!r}")
        self._materializer = materializer
        self._min_gumbel_temp = mgt

    @property
    def materializer(self) -> Any:
        return self._materializer

    @property
    def min_gumbel_temp(self) -> float:
        return float(self._min_gumbel_temp)

    def bias_family(self) -> str:
        return self.FAMILY

    def compute_noise_bias(
        self,
        previous_endpoint: Any,
        paper_quantities: PaperQuantitiesSnapshot | None,
        *,
        round_index: int,
        total_rounds: int,
        channel_domain: str,
        previous_round_sample: Any = None,
        audit_codes: list[str] | None = None,
    ) -> DynamicNoiseBiasResult:
        """Compute categorical bias via the Theorem1 sibling."""
        if channel_domain not in ("discrete", "graph"):
            raise ValueError(
                f"CategoricalDynamicNoiseBias requires discrete/graph channel_domain, got {channel_domain!r}"
            )
        return Theorem1DynamicNoiseBias(
            materializer=self._materializer,
            min_gumbel_temp=self._min_gumbel_temp,
        ).compute_noise_bias(
            previous_endpoint,
            paper_quantities,
            round_index=round_index,
            total_rounds=total_rounds,
            channel_domain=channel_domain,
            previous_round_sample=previous_round_sample,
            audit_codes=audit_codes,
        )


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------


def default_dynamic_noise_bias() -> DynamicNoiseBiasProtocol:
    """Return the canonical paper-grounded :class:`Theorem1DynamicNoiseBias`.

    Per user directive 2026-09-05: the framework's default dynamic-noise-bias
    implementation is the **Theorem 1 iterative** version, which derives
    ``eps(r) = max(e_rho/4, sheet_A * (1 - r/(L-1)))`` from the paper-quantity
    snapshot (sheet_A, packing_B, cell_C, exterior_gap_e_rho). The previous
    :class:`IdentityDynamicNoiseBias` (legacy cosine back-compat no-op
    returning ``epsilon_per_channel = n_cap`` with
    ``bias_source='schedule_fallback'``) is retained as an exportable class
    for back-compat callers but is no longer the default.

    For categorical channels use :class:`CategoricalDynamicNoiseBias`
    explicitly (it wraps :class:`Theorem1DynamicNoiseBias` internally).
    """
    return Theorem1DynamicNoiseBias()


__all__ = [
    "CategoricalDynamicNoiseBias",
    "DEFAULT_DECAY_KIND",
    "DEFAULT_MIN_GUMBEL_TEMP",
    "DynamicNoiseBiasProtocol",
    "IdentityDynamicNoiseBias",
    "NEW_DYNAMIC_NOISE_BIAS_COMPUTED",
    "NEW_DYNAMIC_NOISE_BIAS_DIGEST_ONLY",
    "NEW_DYNAMIC_NOISE_BIAS_EPSILON_FLOORED_BY_PAPER_EXTERIOR_GAP",
    "NEW_DYNAMIC_NOISE_BIAS_EPSILON_NONPOSITIVE",
    "NEW_DYNAMIC_NOISE_BIAS_GUMBEL_HEURISTIC",
    "NEW_DYNAMIC_NOISE_BIAS_GUMBEL_TEMP_COMPUTED",
    "NEW_DYNAMIC_NOISE_BIAS_NO_MATERIALIZER",
    "NEW_DYNAMIC_NOISE_BIAS_PREV_ANCHORED_TO_PREV_ENDPOINT",
    "NEW_DYNAMIC_NOISE_BIAS_SHEET_NONPOSITIVE",
    "Theorem1DynamicNoiseBias",
    "default_dynamic_noise_bias",
]
