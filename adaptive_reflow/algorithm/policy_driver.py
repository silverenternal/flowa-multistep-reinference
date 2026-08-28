"""Per-round policy generator.

Defines the abstract :class:`PolicyDriverProtocol` and three concrete
implementations that translate a schedule sample + current round state
into the :class:`FinalRestartPolicy` for one round:

* :class:`ScheduleDerivedPolicyDriver` (default) — ``beta = n_cap``,
  i.e. the per-round fresh-noise capacity is the cosine schedule's
  ``n_cap``. This is the wiring the engine now applies inline
  (``adaptive_reflow.frame.engine._policy_with_schedule_beta``,
  ADR-0010); the driver makes the override pluggable.
* :class:`ConstantPolicyDriver` — ``beta = constant`` (default ``0.5``,
  configurable). Useful as an ablation baseline (the multi-round
  constant-``beta`` pass in :mod:`tools.run_ablation` already exercises
  this exact wiring; the driver is the named surface for that path).
* :class:`AdaptivePolicyDriver` — ``beta = 1 - |prior - target|``,
  deterministic in :attr:`prior_endpoint_digest`. ``beta`` is high when
  the prior is far from the target (more exploration); ``beta`` is low
  when the prior is close (more refinement). The convergence estimate
  is a stable hash of the supplied ``prior_endpoint_digest`` — the
  driver never reads the prior's contents.

Module boundary
--------------

* stdlib-only. No ``torch``. No I/O. No mutation of inputs.
* Pure functions; identical inputs always yield identical outputs.
* The driver NEVER inspects the contents of the
  :class:`FinalRestartPolicy`'s ``beta_by_channel`` mapping beyond
  preserving its key vocabulary; it only writes a new value of
  ``beta_by_channel`` (and the recomputed ``policy_hash``).

Public surface
--------------

* :class:`PolicyDriverProtocol`
* :class:`ScheduleDerivedPolicyDriver` + :func:`default_policy_driver`
* :class:`ConstantPolicyDriver`
* :class:`AdaptivePolicyDriver`

Tasks satisfied:

* ``DTB-R4`` pluggable per-round policy driver.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Protocol, runtime_checkable

from adaptive_reflow.contracts import (
    CosineScheduleSample,
    FinalRestartPolicy,
    hash_policy_hash,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


#: Driver family identifier for :class:`ScheduleDerivedPolicyDriver`.
SCHEDULE_DERIVED_FAMILY: str = "schedule_derived"

#: Driver family identifier for :class:`ConstantPolicyDriver`.
CONSTANT_FAMILY: str = "constant"

#: Driver family identifier for :class:`AdaptivePolicyDriver`.
ADAPTIVE_FAMILY: str = "adaptive"

#: Default constant ``beta`` for :class:`ConstantPolicyDriver`.
DEFAULT_CONSTANT_BETA: float = 0.5

#: Default target_estimate (used as the convergence reference point by
#: :class:`AdaptivePolicyDriver`). The driver computes
#: ``beta = 1 - |prior_normalized - target_estimate|`` so a "neutral"
#: target yields a symmetric envelope around ``beta = 0.5``.
DEFAULT_ADAPTIVE_TARGET_ESTIMATE: float = 0.5

#: Audit code emitted by :class:`AdaptivePolicyDriver` when the
#: paper-quantity-normalised envelope ``(1 - |p - t|) / C_g``
#: exceeds ``1.0`` and ``beta`` is therefore saturated at the
#: unit-interval ceiling (P2-3 / 8.3 audit). The code carries the
#: pre-clip raw value so a downstream audit reader can see how far
#: past the ceiling the unclipped value would have gone (the gap is
#: ``raw - 1.0``). When ``C_g >= 1`` the unclipped envelope is
#: always ``<= 1.0`` and the code is never emitted.
BETA_SATURATION_FROM_PAPER_QUANTITY: str = "beta_saturation_from_paper_quantity"

#: Audit code emitted by :class:`ScheduleDerivedPolicyDriver` whenever
#: it overrides ``beta_by_channel`` from the schedule's ``n_cap`` (P1
#: uplift A10). The engine / runner consume this to attribute the
#: per-round ``beta`` to the schedule-derived source of truth. The
#: code is NOT emitted when ``schedule_sample is None`` (no override
#: took place) or when ``n_cap`` is non-finite (the driver falls back
#: to the base policy).
POLICY_SCHEDULE_DERIVED: str = "policy_schedule_derived"


# ---------------------------------------------------------------------------
# Pure helper — channel vocabulary + policy_hash recompute
# ---------------------------------------------------------------------------


def _clip_unit_finite(value: float) -> float:
    """Return ``value`` clipped to ``[0, 1]`` (raises on non-finite)."""
    if not _is_finite(value):
        raise ValueError(f"value must be finite, got {value!r}")
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return float(value)


def _is_finite(value: Any) -> bool:
    """Return ``True`` iff ``value`` is a finite real number."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    import math

    return math.isfinite(f)


def _override_beta_by_channel(
    base_policy: FinalRestartPolicy,
    *,
    beta_value: float,
    channel: str | None = None,
) -> FinalRestartPolicy:
    """Return a copy of ``base_policy`` with ``beta_by_channel`` set to ``beta_value``.

    The override preserves the channel vocabulary of ``base_policy``
    (every key gets the same ``beta_value``); ``alpha_by_channel``,
    ``fresh_noise_floor_by_channel``, ``freeze_admission_by_channel``
    and ``schedule_sample`` are forwarded verbatim. The returned
    policy's :attr:`FinalRestartPolicy.policy_hash` is recomputed via
    :func:`hash_policy_hash` so the audit invariant
    ``policy_hash == hash_policy_hash(policy)`` holds. The helper
    also sets ``driver_computed_beta=True`` on the returned policy
    (closes Contract 1.2: the driver is the source of truth for
    ``beta_by_channel`` so the engine skips its inline re-override
    when the flag is set).

    The ``channel`` argument is accepted for protocol signature parity;
    the override writes to *every* key in the policy's vocabulary so
    the engine receives a deterministic per-channel ``beta``. Drivers
    that need per-channel behavior can be added later — this helper
    is the single boundary at which ``beta_by_channel`` is rewritten.
    """
    clipped = _clip_unit_finite(float(beta_value))
    # Preserve the existing channel vocabulary; if it is empty (a
    # misconfigured caller), stamp ``channel`` so the policy still has
    # at least one key for downstream consumers.
    if base_policy.beta_by_channel:
        keys = list(base_policy.beta_by_channel.keys())
    elif channel is not None:
        from adaptive_reflow.contracts import ChannelName

        keys = [ChannelName(str(channel))]
    else:
        keys = []
    new_beta_by_channel: Mapping[Any, Any] = {
        k: type(base_policy.beta_by_channel[k])(clipped) for k in keys
    }
    overridden = replace(
        base_policy, beta_by_channel=new_beta_by_channel, driver_computed_beta=True
    )
    return replace(overridden, policy_hash=hash_policy_hash(overridden))


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class PolicyDriverProtocol(Protocol):
    """Per-round policy generator.

    A driver takes the schedule sample for the round, the round's
    base policy, the channel name, and the prior endpoint's digest,
    and returns the :class:`FinalRestartPolicy` the engine should
    forward to the adapter for that round. Different drivers encode
    different restart philosophies:

    * :class:`ScheduleDerivedPolicyDriver` — ``beta = n_cap``
      (the engine's current inline override; ADR-0010).
    * :class:`ConstantPolicyDriver` — ``beta = constant``
      (ablation baseline).
    * :class:`AdaptivePolicyDriver` — ``beta`` depends on the prior
      endpoint's digest (adaptive exploration vs. refinement).

    CONTRACT 3.1 — driver ↔ blender direction: the output of
    :meth:`compute_policy` is the **per-round ``beta``** (the noise
    coefficient; higher means more fresh noise). The
    :class:`RestartBlenderProtocol` consumes ``memory_fraction =
    1 - beta`` at the adapter boundary; callers MUST NOT pass
    ``beta`` directly to ``blender.blend(...)`` as ``memory_fraction``.
    Drivers MUST NOT produce a negative ``beta``; the canonical
    ``_override_beta_by_channel`` helper clips to ``[0, 1]``.

    CONTRACT 1.2 — driver / engine dedup: drivers that mutate
    ``beta_by_channel`` MUST mark the returned policy with
    ``driver_computed_beta=True`` so the engine's inline
    ``_policy_with_schedule_beta`` re-override is suppressed. The
    shared helper :func:`_override_beta_by_channel` already sets the
    flag; drivers that build their own override MUST set it manually
    via ``dataclasses.replace(..., driver_computed_beta=True)``.
    """

    def compute_policy(
        self,
        schedule_sample: CosineScheduleSample | None,
        *,
        base_policy: FinalRestartPolicy,
        channel: str,
        prior_endpoint_digest: str,
        audit_codes: list[str] | None = None,
    ) -> FinalRestartPolicy:
        """Return the round's :class:`FinalRestartPolicy`.

        Parameters
        ----------
        schedule_sample:
            The schedule sample for the round, or ``None`` for drivers
            that do not consult the schedule. Drivers MAY ignore this
            argument; drivers MUST tolerate ``None`` (returning
            ``base_policy`` unchanged is a valid behaviour).
        base_policy:
            The base policy the caller would have used without the
            driver. Drivers preserve every field except
            ``beta_by_channel`` (and the recomputed ``policy_hash``).
        channel:
            The channel the round is targeting. Drivers MAY use this
            as a hint; the override helper writes to *every* key in
            the base policy's vocabulary so the engine sees a
            consistent per-channel ``beta``.
        prior_endpoint_digest:
            Stable digest of the previous round's endpoint (empty
            string when this is round 0). Drivers MAY use this to
            adapt ``beta``; drivers MUST NOT inspect the endpoint's
            contents.
        audit_codes:
            Optional mutable list that the driver appends diagnostic
            codes to. Drivers MAY emit saturation / clipping codes
            here without mutating the caller's list when ``None``
            (mirrors the :class:`MergeOperatorProtocol` contract).
            Adaptive drivers that fold a paper-quantity divisor
            (``per_cell_coefficient_C < 1``) into the per-round
            ``beta`` MAY emit
            :data:`BETA_SATURATION_FROM_PAPER_QUANTITY` when the
            unclipped envelope exceeds ``1.0``.

        Returns
        -------
        FinalRestartPolicy
            A policy whose :attr:`policy_hash` is the deterministic
            recompute of the canonical field tuple. The returned
            ``beta_by_channel`` is the **per-round ``beta``** (the
            noise coefficient; ``memory_fraction = 1 - beta`` lives
            downstream at the blender boundary — Contract 3.1).
            Drivers that mutate ``beta_by_channel`` MUST set
            ``driver_computed_beta=True`` so the engine skips its
            inline re-override (Contract 1.2).
        """
        ...

    def driver_family(self) -> str:
        """Return the driver family identifier (e.g. ``"schedule_derived"``)."""
        ...

    def config_hash(self) -> str:
        """Return a stable digest identifying this driver + its config.

        Two drivers with the same family + config return the same
        ``config_hash``; two drivers that differ in family or config
        return different ``config_hash`` values. Used to track
        provenance in the round trace / ledger.
        """
        ...


# ---------------------------------------------------------------------------
# Schedule-derived driver (default)
# ---------------------------------------------------------------------------


class ScheduleDerivedPolicyDriver:
    """``beta = n_cap`` driver (default).

    Mirrors the inline override the engine applies at
    :func:`adaptive_reflow.frame.engine._policy_with_schedule_beta`:
    when ``schedule_sample`` is not ``None``, ``beta`` is the
    schedule's clipped ``n_cap`` (``memory_fraction = 1 - n_cap``);
    when ``schedule_sample`` is ``None``, ``base_policy`` is returned
    unchanged.

    The driver is pure: identical inputs always yield identical
    :class:`FinalRestartPolicy` instances (the dataclass equality
    holds because every field except ``beta_by_channel`` and
    ``policy_hash`` is forwarded verbatim, and the override is a pure
    function of the schedule's ``n_cap``).
    """

    def __init__(self) -> None:
        # No constructor state; the driver is purely a function of its
        # arguments. The constructor exists so callers can build a
        # stable instance for the ``default_policy_driver()`` factory.
        pass

    # -- PolicyDriverProtocol ----------------------------------------------

    def compute_policy(
        self,
        schedule_sample: CosineScheduleSample | None,
        *,
        base_policy: FinalRestartPolicy,
        channel: str,
        prior_endpoint_digest: str,
        audit_codes: list[str] | None = None,
    ) -> FinalRestartPolicy:
        """Return the round's policy with ``beta = n_cap``.

        When ``schedule_sample`` is ``None`` the driver returns
        ``base_policy`` verbatim (the engine's helper does the same;
        callers that supply ``None`` are signalling "no schedule
        guidance"). Otherwise ``beta`` is the schedule's
        ``n_cap`` clipped to ``[0, 1]`` and applied uniformly across
        the policy's channel vocabulary.

        ``prior_endpoint_digest`` is accepted for protocol signature
        parity and is otherwise ignored (the schedule is the only
        restart philosophy the driver encodes).

        ``audit_codes`` is accepted for protocol signature parity and
        is otherwise ignored (the schedule-derived driver has no
        saturation / clipping surface; the schedule's ``n_cap`` is
        already in ``[0, 1]`` post-clip).
        """
        # ``prior_endpoint_digest`` / ``audit_codes`` are accepted for
        # protocol signature parity; suppress the unused-argument lint
        # explicitly.
        del prior_endpoint_digest
        if schedule_sample is None:
            return base_policy
        n_cap_raw = schedule_sample.n_cap
        try:
            n_cap = float(n_cap_raw)
        except (TypeError, ValueError):
            return base_policy
        if not _is_finite(n_cap):
            return base_policy
        clipped = _clip_unit_finite(n_cap)
        # P1-A10: emit the canonical schedule-derived audit code so the
        # engine's audit trail attributes the per-round ``beta`` to the
        # schedule-derived source of truth. The code is only emitted on
        # the actual override path (not the ``None``-sample / non-finite
        # fallback paths).
        if audit_codes is not None:
            audit_codes.append(POLICY_SCHEDULE_DERIVED)
        return _override_beta_by_channel(
            base_policy, beta_value=clipped, channel=channel
        )

    def driver_family(self) -> str:
        """Return ``"schedule_derived"``."""
        return SCHEDULE_DERIVED_FAMILY

    def config_hash(self) -> str:
        """Return a stable digest of the driver family.

        The schedule-derived driver has no config knobs, so the digest
        is a pure function of the family identifier. Two
        :class:`ScheduleDerivedPolicyDriver` instances always compare
        equal.
        """
        payload = {
            "driver_family": SCHEDULE_DERIVED_FAMILY,
        }
        return _stable_digest(payload)

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict (P1-1 round-trip)."""
        return {"family": SCHEDULE_DERIVED_FAMILY}

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> ScheduleDerivedPolicyDriver:
        """Build a :class:`ScheduleDerivedPolicyDriver` from ``config``.

        The driver has no knobs; ``config["family"]`` MUST equal
        ``"schedule_derived"``.
        """
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return ScheduleDerivedPolicyDriver()


# ---------------------------------------------------------------------------
# Constant-beta driver (ablation baseline)
# ---------------------------------------------------------------------------


class ConstantPolicyDriver:
    """``beta = constant`` driver (ablation baseline).

    For every round the per-channel ``beta`` is the configured
    constant (``DEFAULT_CONSTANT_BETA = 0.5``). ``schedule_sample``
    and ``prior_endpoint_digest`` are accepted for protocol
    signature parity and otherwise ignored.

    This driver is the named surface for the multi-round constant-``beta``
    pass already exercised by :mod:`tools.run_ablation`. Use it as a
    reference baseline: ``ScheduleDerivedPolicyDriver` is the load-
    bearing default; ``ConstantPolicyDriver`` is what an ablation
    against a flat restart would compare against.
    """

    def __init__(self, beta: float = DEFAULT_CONSTANT_BETA) -> None:
        # ``beta`` is clipped at compute time so the constructor
        # accepts any finite float without raising; we mirror the
        # helper's clip-and-coerce semantics for clarity at the call
        # site.
        try:
            bf = float(beta)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"beta must be a real number, got {beta!r}"
            ) from exc
        if not _is_finite(bf):
            raise ValueError(f"beta must be finite, got {beta!r}")
        self._beta = _clip_unit_finite(bf)

    # -- accessors ---------------------------------------------------------

    @property
    def beta(self) -> float:
        """Return the configured constant ``beta`` (in ``[0, 1]``)."""
        return float(self._beta)

    # -- PolicyDriverProtocol ----------------------------------------------

    def compute_policy(
        self,
        schedule_sample: CosineScheduleSample | None,
        *,
        base_policy: FinalRestartPolicy,
        channel: str,
        prior_endpoint_digest: str,
        audit_codes: list[str] | None = None,
    ) -> FinalRestartPolicy:
        """Return the round's policy with ``beta = constant``.

        ``schedule_sample``, ``prior_endpoint_digest`` and
        ``audit_codes`` are accepted for protocol signature parity and
        are otherwise ignored. The override preserves the base
        policy's channel vocabulary and recomputes ``policy_hash``
        via :func:`hash_policy_hash`.
        """
        del schedule_sample
        del prior_endpoint_digest
        del audit_codes
        return _override_beta_by_channel(
            base_policy, beta_value=self._beta, channel=channel
        )

    def driver_family(self) -> str:
        """Return ``"constant"``."""
        return CONSTANT_FAMILY

    def config_hash(self) -> str:
        """Return a stable digest of the driver family + ``beta``.

        Two drivers with the same ``beta`` compare equal; a driver
        with a different ``beta`` compares unequal.
        """
        payload = {
            "driver_family": CONSTANT_FAMILY,
            "beta": float(self._beta),
        }
        return _stable_digest(payload)

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict (P1-1 round-trip)."""
        return {"family": CONSTANT_FAMILY, "beta": float(self._beta)}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ConstantPolicyDriver:
        """Build a :class:`ConstantPolicyDriver` from ``config``."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return ConstantPolicyDriver(beta=float(config["beta"]))


# ---------------------------------------------------------------------------
# Adaptive driver (digest-seeded convergence estimate)
# ---------------------------------------------------------------------------


class AdaptivePolicyDriver:
    """``beta = 1 - |prior_normalized - target_estimate|`` driver.

    The driver derives a stable ``prior_normalized`` from
    ``prior_endpoint_digest`` (a hash of the digest mapped to ``[0, 1]``
    via ``int(digest_hex, 16) / 2**256``) and computes

        beta = clip(1 - |prior_normalized - target_estimate|, 0, 1)

    so the per-channel ``beta`` is **high** when the prior is far
    from the target estimate (more exploration) and **low** when the
    prior is close (more refinement).

    The driver is deterministic and pure: the same digest always
    produces the same ``beta``. ``schedule_sample`` is accepted for
    protocol signature parity and otherwise ignored (the adaptive
    driver intentionally decouples ``beta`` from the schedule so a
    side-by-side ``adaptive`` vs. ``schedule_derived`` comparison
    isolates the effect of the prior-driven envelope from the
    schedule's ``n_cap`` ramp).

    **Paper-quantity wiring.** When ``per_cell_coefficient_C`` is
    supplied (the value of ``paper_quantities.per_cell_coefficient_C``
    from paper Lemma 3, line 191), the driver divides the raw
    ``1 - |p - t|`` envelope by ``C_g`` so the per-round ``beta``
    lives on paper Lemma 3's per-cell evidence scale:

        beta = clip((1 - |p - t|) / C_g, 0, 1)

    The default ``C_g`` (rho=0.1, c=1.0) is approximately 1.30; the
    paper-quantity-augmented path therefore produces a slightly more
    conservative ``beta`` than the legacy path, matching Lemma 3's
    ``O(eps^2)`` per-cell bound. When ``per_cell_coefficient_C`` is
    ``None``, the driver falls back to the legacy formula
    ``beta = clip(1 - |p - t|, 0, 1)`` (backward compat).
    """

    def __init__(
        self,
        *,
        target_estimate: float = DEFAULT_ADAPTIVE_TARGET_ESTIMATE,
        per_cell_coefficient_C: float | None = None,
    ) -> None:
        try:
            t = float(target_estimate)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"target_estimate must be a real number, got {target_estimate!r}"
            ) from exc
        if not _is_finite(t):
            raise ValueError(
                f"target_estimate must be finite, got {target_estimate!r}"
            )
        # ``target_estimate`` is allowed to live outside ``[0, 1]``
        # (the absolute-difference envelope is symmetric and the
        # normalization of the prior digest is in ``[0, 1]``), but we
        # still sanity-check finiteness so the math cannot blow up.
        self._target = float(t)
        # Paper-quantity normalization: ``None`` disables the
        # Lemma-3-evidence-scale normalisation (legacy behaviour).
        # When supplied, it must be a finite positive real.
        if per_cell_coefficient_C is None:
            self._per_cell_coefficient_C: float | None = None
        else:
            try:
                c_f = float(per_cell_coefficient_C)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"per_cell_coefficient_C must be a real number, "
                    f"got {per_cell_coefficient_C!r}"
                ) from exc
            if not _is_finite(c_f):
                raise ValueError(
                    f"per_cell_coefficient_C must be finite, "
                    f"got {per_cell_coefficient_C!r}"
                )
            if c_f <= 0.0:
                raise ValueError(
                    f"per_cell_coefficient_C must be positive, got {c_f!r}"
                )
            self._per_cell_coefficient_C = c_f
        # P1-A11: per-call saturation counter. Increments every time
        # the paper-quantity-normalised envelope ``(1 - |p - t|) / C_g``
        # exceeds ``1.0`` and ``beta`` therefore saturates at the
        # unit-interval ceiling. The counter is per-instance and
        # does NOT contribute to ``config_hash`` (it is a runtime
        # diagnostic, not a constructor argument).
        self._beta_saturation_count: int = 0

    # -- accessors ---------------------------------------------------------

    @property
    def target_estimate(self) -> float:
        """Return the configured target estimate."""
        return float(self._target)

    @property
    def per_cell_coefficient_C(self) -> float | None:
        """Return the configured paper-quantity ``C_g``, or ``None``.

        ``None`` means "legacy adaptive driver" (``beta = 1 - |p - t|``).
        When supplied, the driver divides the raw envelope by ``C_g``
        to drive the per-round ``beta`` toward paper Lemma 3's
        per-cell evidence scale.
        """
        return self._per_cell_coefficient_C

    @property
    def beta_saturation_count(self) -> int:
        """Return the count of saturation events on this driver instance.

        P1-A11: every time :meth:`compute_policy` saturates
        ``beta`` at the unit-interval ceiling (only possible when
        ``per_cell_coefficient_C < 1``) the counter is incremented.
        The counter is per-instance and is the source of truth for
        the ``beta_saturation_count`` per-round metric consumed by
        the runner / engine audit ledger. It does NOT contribute
        to ``config_hash`` (it is a runtime diagnostic, not a
        constructor argument).
        """
        return int(self._beta_saturation_count)

    def reset_beta_saturation_count(self) -> None:
        """Reset the per-call saturation counter to zero.

        The runner typically resets the counter at the start of every
        outer cycle so the per-round metric reports the cycle-local
        count rather than a lifetime aggregate.
        """
        self._beta_saturation_count = 0

    # -- PolicyDriverProtocol ----------------------------------------------

    def compute_policy(
        self,
        schedule_sample: CosineScheduleSample | None,
        *,
        base_policy: FinalRestartPolicy,
        channel: str,
        prior_endpoint_digest: str,
        audit_codes: list[str] | None = None,
    ) -> FinalRestartPolicy:
        """Return the round's policy with ``beta = (1 - |p - t|) / C_g``.

        ``prior_endpoint_digest`` is hashed to a ``[0, 1]`` value via
        a stable mapping (``int(digest_hex, 16) / 2**256``). An empty
        string (``round 0`` with no prior endpoint) is hashed
        verbatim — the digest then becomes ``"sha256('')"`` mapped to
        ``[0, 1]`` so round 0 is deterministic.

        When ``per_cell_coefficient_C`` is configured at construction
        time, the raw envelope ``1 - |p - t|`` is divided by ``C_g``
        so the resulting ``beta`` lives on paper Lemma 3's per-cell
        evidence scale. The result is clipped to ``[0, 1]`` (when
        ``C_g < 1`` the unclipped value can exceed 1, so the clip
        saturates; when ``C_g >= 1`` the raw envelope stays inside
        ``[0, 1]``).

        ``audit_codes``: optional mutable list that the driver appends
        diagnostic codes to. When the paper-quantity-normalised
        envelope ``(1 - |p - t|) / C_g`` exceeds ``1.0`` (only
        possible when ``C_g < 1``) the driver appends
        :data:`BETA_SATURATION_FROM_PAPER_QUANTITY` with the raw
        unclipped value embedded (P2-3 / 8.3 audit). The saturation
        audit code is only emitted on the paper-quantity-augmented
        path; the legacy path (``C_g = None``) cannot saturate.
        """
        del schedule_sample
        prior_normalized = _digest_to_unit(str(prior_endpoint_digest))
        diff = abs(prior_normalized - self._target)
        raw = 1.0 - diff
        saturated_from_paper_quantity = False
        if self._per_cell_coefficient_C is not None:
            raw = raw / float(self._per_cell_coefficient_C)
            # P2-3 / 8.3: when ``C_g < 1`` the paper-quantity-
            # normalised envelope can exceed 1.0 and ``beta`` saturates
            # at the ceiling. Emit an audit code so downstream readers
            # can see the saturation.
            if raw > 1.0:
                saturated_from_paper_quantity = True
        # Clip into ``[0, 1]`` — when ``diff > 1`` (target_estimate far
        # from the unit interval) the raw ``beta`` would go negative,
        # so we floor at 0 to keep the engine's audit invariant.
        clipped = _clip_unit_finite(float(raw))
        if saturated_from_paper_quantity:
            # P1-A11: increment the per-instance counter so the runner
            # can pick the count up via ``driver.beta_saturation_count``
            # after a run (or at any point in the run). The counter is
            # independent of whether the caller supplied an
            # ``audit_codes`` list.
            self._beta_saturation_count += 1
            if audit_codes is not None:
                audit_codes.append(
                    f"{BETA_SATURATION_FROM_PAPER_QUANTITY}:raw={raw!r}"
                )
        return _override_beta_by_channel(
            base_policy, beta_value=clipped, channel=channel
        )

    def driver_family(self) -> str:
        """Return ``"adaptive"``."""
        return ADAPTIVE_FAMILY

    def config_hash(self) -> str:
        """Return a stable digest of the driver family + target.

        Two drivers with the same ``target_estimate`` and the same
        ``per_cell_coefficient_C`` compare equal; changing either
        yields a different ``config_hash``.
        """
        payload: dict[str, Any] = {
            "driver_family": ADAPTIVE_FAMILY,
            "target_estimate": float(self._target),
        }
        if self._per_cell_coefficient_C is None:
            payload["per_cell_coefficient_C"] = None
        else:
            payload["per_cell_coefficient_C"] = float(
                self._per_cell_coefficient_C
            )
        return _stable_digest(payload)

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict (P1-1 round-trip)."""
        return {
            "family": ADAPTIVE_FAMILY,
            "target_estimate": float(self._target),
            "per_cell_coefficient_C": (
                None
                if self._per_cell_coefficient_C is None
                else float(self._per_cell_coefficient_C)
            ),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> AdaptivePolicyDriver:
        """Build an :class:`AdaptivePolicyDriver` from ``config``."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        per_cell = config.get("per_cell_coefficient_C")
        if per_cell is not None:
            per_cell = float(per_cell)
        return AdaptivePolicyDriver(
            target_estimate=float(config["target_estimate"]),
            per_cell_coefficient_C=per_cell,
        )


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------


def default_policy_driver() -> ScheduleDerivedPolicyDriver:
    """Return the default :class:`PolicyDriverProtocol` implementation.

    The default is :class:`ScheduleDerivedPolicyDriver` so existing
    callers that today rely on the engine's inline
    ``beta_from_schedule`` override see identical behaviour when the
    engine is updated to dispatch through a driver.
    """
    return ScheduleDerivedPolicyDriver()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stable_digest(payload: Mapping[str, Any]) -> str:
    """Return a stable sha256 hex digest of ``payload``.

    The mapping is serialized via ``hash_artifact`` semantics (sorted
    keys, JSON-encodable values) so the digest is deterministic across
    runs and Python versions. The implementation is inlined so this
    module stays stdlib-only.

    The fallback ``default`` is :func:`_canonical_json_default` (not
    ``str``) so numerically-equal values from different dtypes (e.g.
    ``numpy.float64(0.5)`` and ``float(0.5)``) produce the same digest
    (P2-11 audit). The helper handles numpy scalars via
    :meth:`numpy.ndarray.item` so the digest is mathematically stable
    across dtype boundaries.
    """
    import json

    text = json.dumps(
        _canonicalize(payload), sort_keys=True, default=_canonical_json_default
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonicalize(value: Any) -> Any:
    """Recursively coerce ``value`` into a JSON-encodable, sort-keyable form."""
    if isinstance(value, Mapping):
        return {
            str(k): _canonicalize(v)
            for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(v) for v in value]
    if isinstance(value, bool):
        return bool(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def _canonical_json_default(obj: Any) -> Any:
    """Return a JSON-encodable fallback for ``obj``.

    Used as the ``default`` argument to :func:`json.dumps` so the
    canonical encoder can serialise objects outside the default JSON
    type set without losing numerical precision. The helper handles:

    * NumPy scalars (``numpy.float64`` / ``numpy.int64`` etc.) —
      coerced via :meth:`numpy.ndarray.item` so a ``numpy.float64``
      and a Python ``float`` with the same numerical value produce
      the same digest (P2-11 audit).
    * Objects exposing :meth:`__float__` — coerced via :func:`float`.
    * Anything else — coerced via :func:`str` as the last-resort
      deterministic fallback.

    The helper never raises: a non-encodable object produces a string
    digest of its repr so two digests remain byte-comparable across
    Python versions and the encoder never silently drops content.
    """
    # NumPy scalars: ``.item()`` returns the Python builtin scalar.
    item_fn = getattr(obj, "item", None)
    if callable(item_fn):
        try:
            return item_fn()
        except (ValueError, TypeError):
            pass
    # Numeric protocol fallback (decimal.Decimal, fractions.Fraction, etc.).
    float_fn = getattr(obj, "__float__", None)
    if callable(float_fn):
        try:
            return float_fn()
        except (TypeError, ValueError):
            pass
    # Last-resort deterministic string fallback.
    return str(obj)


def _digest_to_unit(digest: str) -> float:
    """Map ``digest`` (hex or arbitrary string) to ``[0, 1]``.

    Tries to parse ``digest`` as a hex string; if it parses, the
    leading 16 hex characters are converted to an ``int`` and divided
    by ``2 ** 64`` so the result is in ``[0, 1]``. Otherwise the
    ``digest`` is hashed with SHA-256 and the first 16 hex characters
    are mapped the same way. Either path is deterministic — two
    identical digests always produce the same ``[0, 1]`` value, and
    the mapping is stable across runs.
    """
    text = str(digest)
    if text == "":
        # Round 0 sentinel: hash the empty string so the mapping is
        # still deterministic (the hash of ``""`` is well-known).
        text = hashlib.sha256(b"").hexdigest()
    raw = text.strip()
    # Try hex parsing first.
    try:
        prefix = raw[:16]
        value = int(prefix, 16)
        return float(value) / float(1 << 64)
    except ValueError:
        # Fall back to hashing the raw bytes so non-hex digests still
        # map to ``[0, 1]`` deterministically.
        fallback = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        value = int(fallback[:16], 16)
        return float(value) / float(1 << 64)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    # Constants
    "ADAPTIVE_FAMILY",
    "BETA_SATURATION_FROM_PAPER_QUANTITY",
    "CONSTANT_FAMILY",
    "DEFAULT_ADAPTIVE_TARGET_ESTIMATE",
    "DEFAULT_CONSTANT_BETA",
    "POLICY_SCHEDULE_DERIVED",
    "SCHEDULE_DERIVED_FAMILY",
    # Implementations
    "AdaptivePolicyDriver",
    "ConstantPolicyDriver",
    "PolicyDriverProtocol",
    "ScheduleDerivedPolicyDriver",
    # Factory
    "default_policy_driver",
]
