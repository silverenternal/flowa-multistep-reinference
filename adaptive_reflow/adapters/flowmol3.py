"""FlowMol3 read-only mechanics adapter skeleton (DTB-G2).

This module defines a placeholder :class:`FlowMatchingODEAdapter`
implementation for the FlowMol3 model pinned at commit
``77cae22174b7792b0e25e9e0414038420736d841``. The adapter is
**read-only**: it does not import or modify FlowMol3 source code; it
exercises only the public :class:`flow_matching_engine.Engine` protocol
surface and produces deterministic placeholder state suitable for the
mechanics-parity test gate.

Non-claim boundary
------------------

FlowMol3 is admitted in the candidate registry as
``admitted_unconditional_only``. This adapter therefore **does not**
participate in any pocket-conditioned efficacy claim. Its sole purpose
is to validate that the public engine + adapter protocol surface
(DTB-G1) is sufficient for the FlowMol3 integrate/step ``(x, a, c, e)``
state family.

Tasks satisfied:

* ``DTB-G2`` — first registered candidate (FlowMol3) mechanics adapter.
* ``MUST-3`` / ``D.1`` (Wave 41) — per-adapter refactor onto the
  framework-core glue in :mod:`adaptive_reflow.core`. FlowMol3's native
  ``(x, a, c, e)`` state is graph-shaped, so the restart boundary now
  delegates to :mod:`adaptive_reflow.core.graph_wrapper` rather than
  carrying an inlined no-op. See ``docs/audit/wave41-flowmol3-shrink.md``.

Design notes
------------

* The adapter keeps a frozen capability token so the engine can perform
  its fail-closed handshake up-front (DTB-G1 acceptance: capability
  mismatch / unknown channel / shape mismatch all fail closed).
* All ``TensorRef`` values returned by this adapter are deterministic
  hash-stable strings derived from the inputs; the engine never inspects
  them.
* No third-party FlowMol3 source is imported. ``from flowmol3 import …``
  is forbidden here; the adapter is the **placeholder** the actual
  integration would replace.
* The fail-closed ``validate_state_bundle`` gate is centralised in
  :func:`_require_valid` — every protocol entry point routes through
  it instead of repeating the check inline.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.adapters._adapter_common import (
    coerce_nfe_budget,
    low_nfe_restart_gate,
    per_position_entropy_reduction,
)
from adaptive_reflow.core.graph_wrapper import (
    GraphPayload,
    blend_graph_features,
    random_graph_payload,
)
from adaptive_reflow.frame.adapter import (
    AdapterCapabilities,
    CapabilityMissingError,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)
from adaptive_reflow.framework.interfaces import (
    AdapterObservationProtocol,
    FlowMatchingODEAdapterWithObservation,
    ObservationKind,
    ObservationResult,
    implements,
)
from adaptive_reflow.universal.adapter import ChannelDomain, FlowMatchingODEAdapter
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
)
from adaptive_reflow.writer.registry import (
    FLOWMOL3_PINNED_COMMIT,
    make_default_flowmol3_entry,
)

# Local type alias — kept parallel to other adapters.
ArrayF64 = NDArray[np.float64]

#: Default absolute path to the published FlowMol3 PyTorch Lightning
#: checkpoint used by :func:`default_flowmol3_adapter` when
#: ``force_mode in {"real", "auto"}``. The artifact is a 65 MB
#: ``last.ckpt`` shipped under ``data/flowmol3/weights_real/``.
FLOWMOL3_REAL_CKPT_PATH: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "flowmol3",
    "weights_real",
    "checkpoints",
    "last.ckpt",
)

#: Audit marker stamped on the adapter provenance when a real ckpt
#: load succeeded. See :func:`_try_load_real_ckpt`.
FLOWMOL3_REAL_CKPT_LOADED_MARKER: str = "flowmol3_real_ckpt_loaded"

# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


# FlowMol3 mixed state channels — declared in the engine's domain
# vocabulary. FlowMol3's native state is ``(x, a, c, e)``; we expose it
# via the engine's existing channel names so the public engine + adapter
# protocol (DTB-G1) can route them through each adapter's own
# ``AdapterCapabilities.channel_domains`` declaration:
#
#   x (position)         -> coordinate    (continuous)
#   c (formal charge)    -> charge        (continuous)
#   e (edge / bond)      -> raw_pair      (discrete)
#
# The native ``a`` (atom type) channel is a model-local label, not an
# adaptive-reflow evidence surface; it stays inside the adapter and is
# documented in the registry entry's ``audit_notes``.
FLOWMOL3_CHANNELS: tuple[str, ...] = ("coordinate", "charge", "raw_pair")
"""Engine-domain channel names exposed by the FlowMol3 adapter."""


FLOWMOL3_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = cast(
    Mapping[ChannelName, ChannelDomain],
    {
        "coordinate": "continuous",
        "charge": "continuous",
        "raw_pair": "discrete",
    },
)
"""Per-channel domain-kind declaration for FlowMol3 (molecule-specific).

This is the per-adapter replacement for the legacy
``frame.adapter.DOMAIN_BY_CHANNEL`` table; the universal engine routes
through each adapter's own ``AdapterCapabilities.channel_domains``
declaration.
"""


# ---------------------------------------------------------------------------
# Wave 49 Agent F — atom-type entropy metric + restart policy glue
# ---------------------------------------------------------------------------
#
# FlowMol3's native ``(x, a, c, e)`` state carries a per-atom
# categorical ``a`` over the 10 heavy-atom types in GEOM-DRUGS-filtered
# (``FLOWMOL3ADAPTER_N_ATOM_TYPES = 10`` in the v2 adapter). This is the
# molecular-axis analog of Kanzi's per-position GPT-prior logits
# (Wave 45 Agent F) and LineageFlow's per-position amino-acid
# categorical (Wave 45 Agent G): a per-atom distribution whose
# Shannon entropy is a natural confidence signal for the restart
# blend.
#
# The v1 placeholder does not preserve a native trajectory
# (``export_trajectory`` raises ``NotImplementedError``), so the
# entropy metric accepts explicit per-atom-type distribution arrays.
# In ``torch`` mode (FlowMol3V2 adapter, out of scope here) the same
# method would pull the ``(n_atoms, K_atom)`` marginal from
# ``g.ndata['a_1']`` per Wave 49 Agent C §5.1.

#: Discrete atom-type label cardinality. Mirrors
#: :data:`adaptive_reflow.adapters.flowmol3_v2_adapter.FLOWMOL3ADAPTER_N_ATOM_TYPES`
#: (heavy atoms in GEOM-DRUGS-filtered). Per the v2 adapter the
#: ``+1`` for the CTMC mask token lives at the adapter-internal
#: ``n_atom_types + 1`` slot; the framework's metric operates on
#: the chemistry-facing ``K_atom = 10`` categorical.
FLOWMOL3_ATOM_TYPE_VOCAB_SIZE: int = 10

#: Metric key returned by :meth:`FlowMol3Adapter.observe_entropy_reduction`.
#: Mirrors the LineageFlow constant
#: :data:`adaptive_reflow.adapters.lineageflow.PER_POSITION_ENTROPY_REDUCTION`
#: so a duck-typed metric caller can key on the same string across
#: the protein + molecule axes.
PER_POSITION_ENTROPY_REDUCTION: str = "per_position_entropy_reduction"

#: Audit codes (deterministic ASCII strings).
AUDIT_FLOWMOL3_RESTART_BLEND: str = "flowmol3_restart_blend"
AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART: str = "flowmol3_atom_type_entropy_restart"
AUDIT_FLOWMOL3_OBSERVED: str = "flowmol3_observed"

#: Audit code stamped on the returned bundle's ``provenance`` when the
#: Wave 58 NFE-adaptive gate skips the restart blend. Downstream eval
#: rows can key on this to tell a *gated* framework arm (≡ baseline
#: trajectory, one extra provenance entry) apart from a blended one.
AUDIT_FLOWMOL3_RESTART_SKIPPED_LOW_NFE: str = (
    "flowmol3adapter_restart_skipped_low_nfe"
)

#: Default total-NFE budget below which
#: :meth:`FlowMol3Adapter.apply_restart_distribution` skips the restart
#: blend (Wave 58 backup path B1; see
#: ``docs/audit/wave58-nfe-adaptive-gate-impl.md`` and
#: ``docs/audit/wave57-synthesis-design.md`` §6).
#:
#: Provenance of the number: Wave 57 Agent A's read of the 2026
#: NFE-adaptive literature plus Agent B's 9-cell v3 grid, where the
#: NFE=10 stratum carried 3/3 regressions. It is a **weakly-supported**
#: threshold (n=3 per stratum, no monotonicity established), which is
#: why it is a per-adapter constructor kwarg rather than a hard-wired
#: literal: pass ``restart_min_nfe=`` to recalibrate, or ``0`` to
#: disable the gate entirely.
FLOWMOL3_RESTART_MIN_NFE: int = 20


@dataclass(frozen=True)
class FlowMol3Capabilities:
    """Static capability token for the FlowMol3 adapter.

    Continuous + discrete channels; deterministic seed supported; no
    trajectory digest in the placeholder. The fields below mirror
    :class:`flow_matching_adapter.AdapterCapabilities` exactly; the
    engine reads them via duck-typing.

    D3 — :attr:`has_condition_injection` now defaults to ``True`` so
    FlowMol3 can participate in :class:`Engine.run_round`. The model
    itself is unconditional; the engine delegates to
    :class:`NullConditionInjector` which annotates the audit trail
    with the null-condition provenance. D2 — :attr:`has_materialization_route`
    defaults to ``True`` and the FlowMol3-specific materializer is
    wired via the framework's :class:`AdapterCapabilities.materializer`
    field (adapters can override).
    """

    has_ode_integration_surface: bool = True
    has_prior_export: bool = True
    has_state_export: bool = True
    has_condition_injection: bool = True  # D3 — null-condition injector.
    has_restart_boundary: bool = True
    has_continuous_channels: bool = True
    has_discrete_channels: bool = True
    has_trajectory_digest: bool = False
    has_deterministic_seed: bool = True
    has_materialization_route: bool = True  # D2 — wired via materializer field.
    supported_channels: tuple[str, ...] = FLOWMOL3_CHANNELS
    channel_domains: Mapping[str, str] = field(
        default_factory=lambda: cast(
            "Mapping[str, str]",
            {str(k): v for k, v in FLOWMOL3_CHANNEL_DOMAINS.items()},
        )
    )

    def to_engine_caps(self) -> AdapterCapabilities:
        """Project this token into the engine's ``AdapterCapabilities``.

        Every field here is named exactly as its ``AdapterCapabilities``
        counterpart, so the projection is an ``**asdict(self)`` splat
        rather than the eighteen-line manual copy this adapter carried.

        D2 — wires the FlowMol3-specific materializer via the
        ``AdapterCapabilities.materializer`` field. The placeholder uses
        :class:`NoOpMaterializer` (no real (x, a, c, e) tensor to
        project); the real FlowMol3 v2 adapter wires the
        :class:`ConcreteFlowMol3Materializer`.
        """
        # Lazy import — materializer is a new addition; we keep the
        # adapter importable for callers that haven't installed
        # numpy for the molecular layer yet.
        try:
            from adaptive_reflow.molecular.materializer import (
                ConcreteFlowMol3Materializer,
            )

            materializer_cls: type | None = ConcreteFlowMol3Materializer
        except ImportError:
            materializer_cls = None

        fields_ = asdict(self)
        fields_["channel_domains"] = cast(
            "Mapping[ChannelName, ChannelDomain]",
            dict(self.channel_domains),
        )
        return AdapterCapabilities(**fields_, materializer=materializer_cls)


def _make_tensor_ref(label: str, **parts: Any) -> TensorRef:
    """Build a deterministic ``TensorRef`` from ``label`` and a parts dict.

    The engine never inspects the value; this function exists only to
    give the placeholder state a stable hash-derived identifier so the
    parity tests can assert byte-equality across replays.

    .. note::
       The exact pre-image of this digest is pinned by the D.4
       regression vector ``regression-vectors/flowmol3.json``. Do not
       change the ``repr((label, sorted(parts.items())))`` encoding
       without regenerating that vector.
    """
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(f"flowmol3:{hashlib.sha256(blob).hexdigest()[:16]}")


def _require_valid(bundle: Any, code: str) -> StateBundle:
    """Fail-closed ``validate_state_bundle`` gate shared by every entry point.

    Replaces the six inlined copies of this block the adapter carried.
    """
    ok, errs = validate_state_bundle(bundle)
    if not ok:
        raise CapabilityMissingError(code, context=",".join(errs))
    return cast(StateBundle, bundle)


# ---------------------------------------------------------------------------
# Restart boundary — framework-core graph glue (MUST-3 / D.1)
# ---------------------------------------------------------------------------

#: Node / edge counts of the placeholder molecular graph. FlowMol3's
#: native ``(x, a, c, e)`` state is per-atom; the placeholder pins a
#: fixed 8-atom / 12-bond topology so the restart blend is reproducible.
FLOWMOL3_PLACEHOLDER_NUM_NODES: int = 8
FLOWMOL3_PLACEHOLDER_NUM_EDGES: int = 12


def _seed_from(*parts: str) -> int:
    """Derive a 32-bit deterministic seed from string material."""
    blob = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return int(hashlib.sha256(blob).hexdigest()[:8], 16)


def _graph_payload_for(*parts: str) -> GraphPayload:
    """Deterministic placeholder molecule via the framework-core builder."""
    return random_graph_payload(
        num_nodes=FLOWMOL3_PLACEHOLDER_NUM_NODES,
        num_edges=FLOWMOL3_PLACEHOLDER_NUM_EDGES,
        seed=_seed_from(*parts),
    )


def _restart_memory_fraction(policy: Any) -> float:
    """Mean restart memory ``beta`` over :data:`FLOWMOL3_CHANNELS`, clamped.

    The engine encodes per-channel ``beta`` in ``policy.beta_by_channel``;
    a policy without it yields ``0.0`` (full refresh).
    """
    by_channel = getattr(policy, "beta_by_channel", None)
    if not isinstance(by_channel, Mapping):
        return 0.0
    values = [
        float(by_channel[ch]) for ch in FLOWMOL3_CHANNELS if ch in by_channel
    ]
    if not values:
        return 0.0
    return max(0.0, min(1.0, sum(values) / len(values)))


def _explicit_nfe_budget(value: Any, *, field: str) -> int | None:
    """Validate an **explicitly supplied** total-NFE budget (Wave 58).

    ``None`` means "not supplied" and is returned as-is. Anything else
    must be an integer step count greater than 1, per
    :func:`~adaptive_reflow.adapters._adapter_common.coerce_nfe_budget`;
    a value that is not raises ``ValueError`` naming ``field``.

    The strictness boundary is deliberate: a caller that *types out* an
    NFE budget and gets it wrong (``nfe_budget="fifty"``,
    ``nfe_budget=0``) has a bug that must surface, whereas the
    duck-typed ``policy.nfe_budget`` probe in
    :meth:`FlowMol3Adapter.apply_restart_distribution` stays lenient —
    an unrelated attribute of that name on someone's restart policy must
    never crash a restart round.
    """
    if value is None:
        return None
    coerced = coerce_nfe_budget(value)
    if coerced is None:
        raise ValueError(
            f"{field}_must_be_int_gt_1_or_None:got {value!r}"
        )
    return coerced


# ---------------------------------------------------------------------------
# FlowMol3AtomTypeEntropyRestartPolicy (Wave 49 Agent F)
# ---------------------------------------------------------------------------
#
# Model-specific glue: FlowMol3's native ``(x, a, c, e)`` state carries a
# per-atom categorical ``a`` over :data:`FLOWMOL3_ATOM_TYPE_VOCAB_SIZE` (=
# 10) heavy-atom types (C, N, O, F, P, S, Cl, Br, I, mask). The
# framework's :class:`RestartBlenderProtocol` selects restart points
# from a paper-quantity-driven distribution, but FlowMol3's per-atom
# categorical is a chemistry-side signal the framework does NOT see —
# this is adapter-layer glue, by directive (Wave 45 brief, mirrored in
# Wave 49 Agent D §0).
#
# ``FlowMol3AtomTypeEntropyRestartPolicy`` reads per-atom entropy
# over the 10-way categorical and biases the restart density toward
# low-entropy atoms (where the molecule strongly believes in its
# current atom type) so re-inference preserves confident atom-type
# assignments and admits more fresh noise where the categorical is
# uncertain.
#
# Synthetic-mode degradation
# --------------------------
#
# The v1 placeholder does not carry a real per-atom-type categorical
# (it produces a graph-wrapper payload, not a real FlowMol3
# trajectory). When ``prior_entry`` is ``None`` or lacks the
# ``atom_type_distribution`` key, the policy degrades to a uniform
# ``alpha = 0.5`` vector — i.e. NO bias on the schedule-driven base
# ``m``. The caller (:meth:`FlowMol3Adapter.apply_restart_distribution`)
# records :data:`AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART` so an audit
# can distinguish a real atom-type-aware restart from the
# schedule-driven fallback. Mirrors the Wave 45 Kanzi / LineageFlow
# fallback discipline.


@dataclass(frozen=True)
class FlowMol3AtomTypeEntropyRestartPolicy:
    """Per-atom restart policy biased by atom-type entropy (Wave 49 Agent F).

    Concept
    -------

    The default FlowMol3 restart blend uses a **scalar** memory-fraction
    ``m`` for the entire graph-shaped ``(x, a, c, e)`` state — see
    :meth:`FlowMol3Adapter.apply_restart_distribution`. This is
    schedule-only: it ignores model-side information.

    FlowMol3's per-atom ``a`` categorical over the 10 heavy-atom types
    is a natural restart signal:

    * **Low entropy** — the molecule is confident in its atom-type
      assignment; re-inference should preserve it, so use a high
      ``m`` (retain more of ``prior_x``).
    * **High entropy** — the molecule is uncertain about the atom
      type; re-inference should explore, so use a low ``m`` (admit
      more ``fresh_x``).

    ``memory_fraction_vector(prior_entry, base_m)`` consumes the
    adapter's per-atom-type distribution ``p_a`` of shape
    ``(n_atoms, K_atom)`` from ``prior_entry["atom_type_distribution"]``
    and returns a per-atom restart density ``alpha`` of shape
    ``(n_atoms,)`` in ``[0, 1]``.

    The framework's :class:`RestartBlenderProtocol` would consume
    ``alpha`` as the channel-wise ``m_vec``; FlowMol3 uses ``alpha``
    to construct ``m_vec = (1 - alpha) * m_floor + alpha * m_ceiling``
    so the bias is a soft modulation around the schedule-driven base
    ``m`` (never collapses ``m_vec`` to a constant zero or one).

    Synthetic-mode degradation
    --------------------------

    Synthetic mode has no per-atom-type distribution.
    ``memory_fraction_vector`` detects the absence of
    ``atom_type_distribution`` in ``prior_entry`` and returns a
    uniform ``alpha = 0.5`` vector — i.e. NO bias on the schedule-
    driven base ``m``. The caller is responsible for emitting
    :data:`AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART` in this fallback
    path so an audit can distinguish a real atom-type-aware restart
    from the schedule-driven scalar blend.

    Stdlib + numpy only. Must be import-safe without ``torch`` or
    ``dgl``.
    """

    #: Per-atom entropy floor. Atoms with entropy ``<=`` this get the
    #: maximum ``m_ceiling`` (high retention). Default
    #: ``0.05 * log(K_atom)`` — an atom needs to be near-spike
    #: confident to count as "high confidence" for restart purposes.
    entropy_floor: float = 0.05 * float(np.log(float(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)))

    #: Per-atom entropy ceiling. Atoms with entropy ``>=`` this get
    #: the minimum ``m_floor`` (low retention). Default
    #: ``0.95 * log(K_atom)`` — near-uniform distributions count as
    #: "no useful prior".
    entropy_ceiling: float = 0.95 * float(np.log(float(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)))

    #: Maximum per-atom ``m_vec`` — used at low-entropy atoms where
    #: the per-atom-type categorical is most confident. Must be in
    #: ``(0, 1]``. Clamped against the schedule-driven base ``m`` at
    #: the call site (the policy NEVER exceeds the schedule-driven
    #: bound).
    m_ceiling: float = 0.95

    #: Minimum per-atom ``m_vec`` — used at high-entropy atoms where
    #: the per-atom-type categorical is least confident. Must be in
    #: ``[0, 1)``. Clamped against the schedule-driven base ``m``.
    m_floor: float = 0.05

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.entropy_floor) < float(self.entropy_ceiling):
            raise ValueError(
                "entropy_floor_must_be_less_than_ceiling:"
                f"{self.entropy_floor!r} vs {self.entropy_ceiling!r}"
            )
        if not 0.0 <= float(self.m_floor) <= float(self.m_ceiling) <= 1.0:
            raise ValueError(
                "m_floor_and_ceiling_must_be_in_[0,1]_with_floor_le_ceiling:"
                f"floor={self.m_floor!r}, ceiling={self.m_ceiling!r}"
            )

    @staticmethod
    def _entropy_from_logits(
        logits: NDArray[np.float64],
        eps: float = 1e-12,
    ) -> NDArray[np.float64]:
        """Numerically-stable per-row Shannon entropy of softmax logits.

        ``logits`` may be of shape ``(..., K)``; entropy is reduced
        over the trailing ``K`` axis only, preserving the leading
        axes (``(n_atoms,)`` for FlowMol3).
        """
        z = logits - np.max(logits, axis=-1, keepdims=True)
        exp_z = np.exp(z)
        p = exp_z / np.sum(exp_z, axis=-1, keepdims=True)
        return -np.sum(p * np.log(p + eps), axis=-1)

    def propose_restart(
        self,
        trace: Any,
        paper_quantities: Any,
    ) -> NDArray[np.float64]:
        """Return per-atom restart density ``alpha`` of shape ``(n_atoms,)``.

        Signature-parity with
        :class:`adaptive_reflow.adapters.kanzi.KanziGPTPriorRestartPolicy.propose_restart`
        so a duck-typed restart orchestrator can route through a
        single hook. The placeholder degrades to a uniform
        ``alpha = 0.5`` so the schedule-driven base ``m`` is
        unaffected; the caller emits
        :data:`AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART` in this
        fallback path.

        Returns
        -------
        ``(n_atoms_prior,)`` ``float64`` array in ``[0, 1]`` where
        ``n_atoms_prior`` is read from the prior entry if
        available, else defaults to :data:`FLOWMOL3_PLACEHOLDER_NUM_NODES`.
        """
        del trace, paper_quantities  # placeholder surface only.
        # Synthetic / no-prior fallback: uniform density.
        return np.full(
            int(FLOWMOL3_PLACEHOLDER_NUM_NODES), 0.5, dtype=np.float64,
        )

    def memory_fraction_vector(
        self,
        prior_entry: Mapping[str, Any] | None,
        *,
        base_m: float,
    ) -> NDArray[np.float64]:
        """Per-atom memory fraction ``m_vec`` of shape ``(n_atoms,)``.

        ``m_vec[i]`` is the atom-type-aware memory fraction at atom
        position ``i``, in ``[0, 1]``. The schedule-driven base
        ``base_m`` (= ``memory_fraction`` from
        :func:`memory_fraction_for`) is the centre of the per-atom
        modulation; ``m_vec[i]`` lives in
        ``[min(base_m, m_floor), max(base_m, m_ceiling)]`` so the
        policy NEVER exceeds the schedule-driven bound.

        Parameters
        ----------
        prior_entry
            The native-state entry fetched by
            :meth:`FlowMol3Adapter.apply_restart_distribution`. May
            carry ``atom_type_distribution`` of shape
            ``(n_atoms, K_atom)``; missing key triggers the
            synthetic-mode fallback (uniform ``m_vec = base_m``).
        base_m
            The schedule-driven base memory fraction.

        Returns
        -------
        ``(n_atoms,)`` ``float64`` array in ``[0, 1]``.
        """
        base = float(base_m)
        atom_logits_raw = (
            prior_entry.get("atom_type_distribution") if prior_entry else None
        )
        if atom_logits_raw is None:
            # Synthetic / no-prior fallback. Return the schedule-
            # driven base uniformly so the blend is identical to the
            # pre-policy behaviour.
            return np.full(
                int(FLOWMOL3_PLACEHOLDER_NUM_NODES), base, dtype=np.float64,
            )
        atom_logits = np.asarray(atom_logits_raw, dtype=np.float64)
        if (
            atom_logits.ndim != 2
            or int(atom_logits.shape[1]) != int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)
        ):
            # Malformed payload — refuse to silently substitute.
            raise ValueError(
                "atom_type_distribution_shape_invalid:"
                f"got {atom_logits.shape!r}, expected "
                f"(n_atoms, {FLOWMOL3_ATOM_TYPE_VOCAB_SIZE!r})"
            )
        entropy = self._entropy_from_logits(atom_logits)
        float(np.log(float(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)))
        # Normalise entropy into [0, 1] via the floor / ceiling
        # anchors. Values below the floor map to 0 (high
        # confidence); values above the ceiling map to 1 (no
        # confidence).
        norm = (entropy - float(self.entropy_floor)) / max(
            float(self.entropy_ceiling) - float(self.entropy_floor),
            1e-12,
        )
        norm = np.clip(norm, 0.0, 1.0)
        # ``norm == 0`` (low entropy) -> ``m_ceiling``;
        # ``norm == 1`` (high entropy) -> ``m_floor``.
        m_target = float(self.m_ceiling) + norm * (
            float(self.m_floor) - float(self.m_ceiling)
        )
        # Clamp the per-atom modulation around the schedule-driven
        # base so the policy never exceeds the schedule's bound
        # (the schedule is the load-bearing authority on memory
        # fraction; the atom-type entropy only modulates around it).
        lower = float(min(base, float(self.m_floor)))
        upper = float(max(base, float(self.m_ceiling)))
        return np.clip(m_target, lower, upper).astype(np.float64)


@implements(
    FlowMatchingODEAdapter,
    AdapterObservationProtocol,
    FlowMatchingODEAdapterWithObservation,
)
class FlowMol3Adapter(FlowMatchingODEAdapter):
    """Read-only FlowMol3 mechanics adapter.

    This is the **placeholder** adapter. It does not import FlowMol3
    source; it produces deterministic, hash-stable placeholder state
    suitable for testing the public engine contract. A real integration
    would replace the body of ``build_initial_state`` /
    ``export_endpoint`` / ``solve_ode`` with calls into FlowMol3 at the
    pinned commit.

    Wave 106.C.1 F-04 gating note: ``force_mode="synthetic"`` (the default)
    is the canonical surface for tests; ``force_mode="real"`` routes to
    :class:`FlowMol3V2Adapter` (which loads the upstream ckpt); the
    ``"auto"`` value picks the real adapter only when the ckpt SHA
    matches ``FLOWMOL3_PINNED_COMMIT``. The placeholder is NEVER silently
    substituted on a real ckpt load (constructor ``force_mode in
    {"synthetic","real","auto"}`` + ``real_ckpt_loaded`` marker gate).
    See ``docs/audit/wave106-a-1-adapter-stubs.md`` §2.2 finding #4.
    """

    pinned_commit: str = FLOWMOL3_PINNED_COMMIT

    def __init__(
        self,
        *,
        atom_type_entropy_restart_policy: (
            FlowMol3AtomTypeEntropyRestartPolicy | None
        ) = None,
        force_mode: str = "synthetic",
        real_ckpt_meta: Mapping[str, Any] | None = None,
        nfe_budget: int | None = None,
        restart_min_nfe: int = FLOWMOL3_RESTART_MIN_NFE,
    ) -> None:
        self._caps = FlowMol3Capabilities()
        # Wave 49 Agent F: optional atom-type-entropy-aware restart
        # policy. Default is ``None`` so all existing tests see the
        # schedule-driven scalar blend (byte-identical to pre-policy
        # behaviour). Pass a
        # :class:`FlowMol3AtomTypeEntropyRestartPolicy` to opt in to
        # per-atom ``m_vec`` modulation. The placeholder degrades to
        # the schedule-driven scalar blend with an audit code; a real
        # (v2) FlowMol3 adapter with an ``atom_type_distribution``
        # payload in its prior entry uses per-atom entropy.
        if (
            atom_type_entropy_restart_policy is not None
            and not isinstance(
                atom_type_entropy_restart_policy,
                FlowMol3AtomTypeEntropyRestartPolicy,
            )
        ):
            raise TypeError(
                "atom_type_entropy_restart_policy_must_be_"
                "FlowMol3AtomTypeEntropyRestartPolicy_or_None:"
                f"got {type(atom_type_entropy_restart_policy).__name__!r}"
            )
        self._atom_type_entropy_restart_policy: (
            FlowMol3AtomTypeEntropyRestartPolicy | None
        ) = atom_type_entropy_restart_policy
        # Wave 50 Agent A: ``force_mode`` kwarg unblocks
        # :func:`tools.run_real_ckpt_eval._resolve_adapter`'s
        # ``factory(force_mode=...)`` call. The placeholder adapter
        # does not run inference through the real FlowMol3 stack (that
        # is the v2 adapter's job), but it records whether a real ckpt
        # load succeeded so downstream eval reports can surface the
        # ``real_ckpt_loaded`` marker. The default ``"synthetic"``
        # keeps all 13 existing tests byte-identical.
        if force_mode not in {"synthetic", "real", "auto"}:
            raise ValueError(
                f"unknown_force_mode:{force_mode} "
                "(expected 'synthetic' | 'real' | 'auto')"
            )
        self._force_mode: str = str(force_mode)
        # ``_real_ckpt_meta`` is ``None`` when no real ckpt was loaded;
        # otherwise it carries ``{"path": str, "n_tensors": int,
        # "epoch": int, "global_step": int, "lightning_version": str}``
        # so the audit trail can attribute the load to a specific file.
        self._real_ckpt_meta: Mapping[str, Any] | None = (
            dict(real_ckpt_meta) if real_ckpt_meta is not None else None
        )
        # Wave 58 — NFE-adaptive restart gate (backup path B1 of
        # ``docs/audit/wave57-synthesis-design.md`` §6).
        #
        # ``nfe_budget`` is the cell's **total** NFE budget (not the
        # per-round split — see :func:`low_nfe_restart_gate`). It is the
        # lowest-priority of the three sources
        # :meth:`apply_restart_distribution` consults, so a caller that
        # constructs one adapter per ``(model, seed, nfe)`` cell can pin
        # it here and never touch the call site.
        #
        # Default ``None`` ⇒ budget unknown ⇒ the gate never fires, so
        # every pre-Wave-58 caller (and the pinned D.4 regression
        # vectors in ``regression-vectors/flowmol3.json``) sees a
        # byte-identical restart blend.
        self._nfe_budget: int | None = _explicit_nfe_budget(
            nfe_budget, field="nfe_budget"
        )
        # ``restart_min_nfe`` is a constructor kwarg rather than a
        # hard-wired literal because the threshold rests on n=3 per
        # stratum (Wave 57 Agent B); ``0`` disables the gate.
        if isinstance(restart_min_nfe, bool) or not isinstance(
            restart_min_nfe, int
        ):
            raise TypeError(
                f"restart_min_nfe_must_be_int:got {restart_min_nfe!r}"
            )
        if restart_min_nfe < 0:
            raise ValueError(
                f"restart_min_nfe_must_be_non_negative:got {restart_min_nfe!r}"
            )
        self._restart_min_nfe: int = int(restart_min_nfe)

    # -- protocol surface ---------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps.to_engine_caps()

    def build_initial_state(
        self,
        *,
        batch_id: str,
        sample_id: str,
    ) -> StateBundle:
        """Construct the prior ``(x, a, c, e)`` state at t=0.

        The returned bundle has ``detach_proof=True`` and a deterministic
        native digest derived from ``(batch_id, sample_id, source_round)``.
        """
        source_round = 0
        channels: dict[str, TensorRef] = {
            ch: _make_tensor_ref(
                "initial", channel=ch, batch=batch_id, sample=sample_id, r=source_round
            )
            for ch in FLOWMOL3_CHANNELS
        }
        masks: dict[str, TensorRef] = {
            ch: _make_tensor_ref("mask", channel=ch, batch=batch_id, sample=sample_id)
            for ch in FLOWMOL3_CHANNELS
        }
        bundle = StateBundle(
            channels=cast(Mapping[ChannelName, TensorRef], channels),
            masks=masks,
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="world",
            normalization="none",
            source_round=int(source_round),
            detach_proof=True,
            native_state_digest=_make_tensor_ref(
                "digest", batch=batch_id, sample=sample_id, r=source_round
            ),
            provenance=(
                f"flowmol3@{FLOWMOL3_PINNED_COMMIT}",
                "DTB-G2 placeholder",
            ),
            capability_token=self._caps.to_engine_caps(),
        )
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise AssertionError(f"placeholder_state_invalid:{errs}")
        return bundle

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        """Return ``state`` re-exported with ``source_round`` unchanged.

        The engine treats the result as the new endpoint bundle; the
        adapter does not modify any tensor.
        """
        if not isinstance(state, StateBundle):
            raise TypeError("state_must_be_state_bundle")
        return _require_valid(state, "validate_state_bundle")

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        """Fail-closed detach gate; the placeholder state already
        carries ``detach_proof=True``, so this is a re-validation."""
        _require_valid(bundle, "detach_proof_must_be_true")
        if bundle.detach_proof is not True:
            raise CapabilityMissingError("detach_proof_must_be_true")
        return bundle

    def apply_restart_distribution(
        self,
        state: StateBundle,
        policy: Any,
        *,
        nfe_budget: int | None = None,
    ) -> StateBundle:
        """Restart boundary via the framework-core graph glue.

        MUST-3 / D.1 (Wave 41). FlowMol3's native ``(x, a, c, e)`` state
        is graph-shaped, so the restart boundary delegates to
        :func:`adaptive_reflow.core.graph_wrapper.blend_graph_features`
        — the framework's canonical
        ``blended = m * prior + (1 - m) * fresh`` restart mixer — instead
        of the inlined no-op this adapter used to carry. ``m`` comes from
        :func:`_restart_memory_fraction`; the digest is
        :meth:`GraphPayload.digest` over the blended payload.

        This also fixes the previous digest, which was derived from
        ``id(policy)`` — a process-local memory address, so the old
        restart digest was **not** reproducible across processes and
        silently violated the B.2 byte-stability contract. See
        ``docs/audit/wave41-flowmol3-shrink.md``.

        Wave 49 Agent F: when an
        :class:`FlowMol3AtomTypeEntropyRestartPolicy` is wired into the
        adapter at construction time, this method consults the policy
        to derive a per-atom ``m_vec`` from the prior entry's
        ``atom_type_distribution`` payload. The default (``policy`` is
        ``None``) keeps the schedule-driven scalar blend byte-identical
        for the 13 existing tests.

        Wave 58 — NFE-adaptive gate
        ---------------------------

        The blend above replaces ``1 - m`` of the state with *fresh*
        noise. At the FlowMol3 paper default ``m = 0.5``, that is half
        the state per restart round, which corrupts the CTMC chain when
        there are too few remaining integration steps to re-absorb it.
        When the effective **total** NFE budget is below
        ``restart_min_nfe`` (default :data:`FLOWMOL3_RESTART_MIN_NFE`),
        this method therefore returns ``state`` with its channels,
        masks, source round and ``native_state_digest`` **unchanged**,
        adding only :data:`AUDIT_FLOWMOL3_RESTART_SKIPPED_LOW_NFE` to
        ``provenance`` so the skip is auditable rather than invisible.
        The framework arm then degenerates to the baseline trajectory
        for that cell — which is the point: at low NFE the measured
        blend was worse than baseline.

        The budget is resolved from three sources, in priority order:

        1. the ``nfe_budget`` keyword argument to this call;
        2. a duck-typed ``policy.nfe_budget`` attribute;
        3. the adapter's own ``nfe_budget`` constructor kwarg.

        If none of them yields a usable budget the gate does **not**
        fire and the blend proceeds — so every caller that predates this
        kwarg, the engine included, is byte-unchanged. See
        ``docs/audit/wave58-nfe-adaptive-gate-impl.md`` for the
        threshold's (weak) empirical basis and for why the *total*
        rather than the per-round NFE is the gate's input.
        """
        _require_valid(state, "validate_state_bundle")
        effective_nfe, skip_restart = low_nfe_restart_gate(
            _explicit_nfe_budget(nfe_budget, field="nfe_budget"),
            getattr(policy, "nfe_budget", None),
            self._nfe_budget,
            min_nfe=self._restart_min_nfe,
        )
        if skip_restart:
            # The blend is skipped, so nothing derived from it (the
            # ``flowmol3:restart:`` digest, the restart-boundary audit
            # code, the atom-type-entropy audit code) may be stamped:
            # the state must read as "this round did not restart".
            return replace(
                state,
                channels=dict(state.channels),
                masks=dict(state.masks),
                detach_proof=True,
                provenance=state.provenance
                + (
                    f"{AUDIT_FLOWMOL3_RESTART_SKIPPED_LOW_NFE}"
                    f":nfe={effective_nfe}"
                    f":min_nfe={self._restart_min_nfe}",
                ),
            )
        memory_fraction = _restart_memory_fraction(policy)
        # Wave 49 Agent F: optionally bias the per-atom memory
        # fraction via the atom-type entropy signal. The placeholder
        # has no ``atom_type_distribution`` payload in its
        # ``prior_entry`` so the policy degrades to the schedule-
        # driven scalar blend; the audit code is appended to
        # ``provenance`` so the caller can distinguish an
        # atom-type-aware restart from the schedule-driven fallback.
        atom_policy_obj = getattr(
            self, "_atom_type_entropy_restart_policy", None
        )
        atom_audit: tuple[str, ...] = ()
        if isinstance(atom_policy_obj, FlowMol3AtomTypeEntropyRestartPolicy):
            # The v1 placeholder does not persist a prior entry
            # (no native-state cache), so the policy's
            # ``memory_fraction_vector`` returns the uniform
            # ``m_vec = base_m`` fallback. The audit code is still
            # emitted so callers can detect the policy was active.
            atom_audit = (AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART,)
        prior = _graph_payload_for(
            "prior",
            str(state.batch_id),
            str(state.sample_id),
            str(state.native_state_digest),
        )
        fresh = _graph_payload_for(
            "fresh",
            str(state.batch_id),
            str(state.sample_id),
            str(state.source_round),
        )
        blended = blend_graph_features(prior, fresh, memory_fraction)
        return replace(
            state,
            channels=dict(state.channels),
            masks=dict(state.masks),
            detach_proof=True,
            native_state_digest=f"flowmol3:restart:{blended.digest()}",
            provenance=state.provenance
            + ("flowmol3_restart_boundary",)
            + atom_audit,
            source_round=int(state.source_round) + 1,
        )

    def compose_condition(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        """Condition injection (D3 — null-condition injector).

        FlowMol3 is an unconditional model; the engine-side handshake
        requires ``has_condition_injection=True`` so we delegate to
        :class:`NullConditionInjector` which annotates the audit
        trail with the null-condition provenance
        (``condition_kind='null', dataset='flowmol3_smiles_pl',
        variant='v1', round_trace_only=True``). The model itself does
        not consume the delta — the injector is the canonical seam
        between the engine's fail-closed audit policy and FlowMol3's
        unconditional ODE.
        """
        _require_valid(bundle, "validate_state_bundle")
        # D3 — delegate to NullConditionInjector for audit provenance.
        from adaptive_reflow.universal.condition_injection import (
            NullConditionInjector,
        )

        injector = NullConditionInjector(
            dataset="flowmol3_smiles_pl", variant="v1"
        )
        od_delta = ODEConditionDelta(
            delta_spec=dict(delta.delta_spec),
            source="flowmol3_adapter",
            target_round=int(bundle.source_round) + 1,
            calibration_artifact_hash="flowmol3_null_calibration",
        )
        composed = injector.compose_delta(bundle, od_delta)
        # The composed delta's spec is returned as the new ODEConditionDelta
        # so the engine's solve_ode call receives the null-condition
        # provenance. (Production wiring records the round-trace ledger
        # row directly.)
        return composed

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        """Single deterministic integration step.

        The placeholder returns the trace derived from
        ``(state.native_state_digest, seed, steps)``; the engine
        reconstructs the post-step bundle via ``observe_endpoint``.
        """
        steps = int(condition.delta_spec.get("num_steps", 1))
        if steps <= 0:
            raise ValueError("steps_must_be_positive")
        _require_valid(state, "validate_state_bundle")
        new_digest = _make_tensor_ref(
            "post_step", source=state.native_state_digest, seed=seed, steps=steps
        )
        trace = ODEIntegratorTrace(
            steps=int(steps),
            accept_rate=1.0,
            native_state_digest=new_digest,
            integrator_config_hash=_make_tensor_ref(
                "integrator_config", seed=seed, steps=steps
            ),
        )
        return trace

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        """Observation-only post-step; placeholder re-validates and returns."""
        del trace  # placeholder preserves no native trajectory (see export_trajectory)
        return _require_valid(state, "validate_state_bundle")

    # ------------------------------------------------------------------
    # 8b. observe (Wave 68 Phase 3 — AdapterObservationProtocol)
    # ------------------------------------------------------------------

    def observe(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
        paper_quantities: Any = None,
        *,
        strategies: tuple[ObservationKind, ...] = (
            ObservationKind.ENDPOINT_BUNDLE,
            ObservationKind.DISCRETE_TOKENS,
            ObservationKind.POSITION_ENTROPY_REDUCTION,
            ObservationKind.TRAJECTORY_NATIVE,
        ),
        theta_before: NDArray[np.float64] | None = None,
        theta_after: NDArray[np.float64] | None = None,
    ) -> tuple[ObservationResult, ...]:
        """Single typed observation surface (Wave 68 — :class:`AdapterObservationProtocol`).

        Wraps the existing :meth:`observe_endpoint` and
        :meth:`observe_entropy_reduction` into a tagged tuple. The
        DISCRETE_TOKENS and TRAJECTORY_NATIVE strategies are NOT natural
        for the v1 placeholder (no per-token integer channel and
        :meth:`export_trajectory` raises ``NotImplementedError``) so
        the result tuple contains only the supported subset.

        This method is ADDITIVE per Wave 11 / Wave 59 interface-first
        constraint. The existing ``observe_endpoint`` and
        ``observe_entropy_reduction`` methods stay in place and
        remain the single source of truth for the metric layer until
        the metric helper is refactored in Wave 67 Phase D.

        Why DISCRETE_TOKENS is skipped
        ------------------------------

        FlowMol3's native state carries a per-atom atom-type
        categorical over the 10 heavy-atom types
        (``FLOWMOL3_ATOM_TYPE_VOCAB_SIZE``), not a discrete token
        index channel like Kanzi / LineageFlow. The metric helper
        has no DISCRETE_TOKENS metric for FlowMol3 (its natural
        observation is the per-atom entropy reduction, not an argmax
        index lookup), so this strategy is intentionally omitted.

        Why TRAJECTORY_NATIVE is skipped
        --------------------------------

        :meth:`export_trajectory` raises ``NotImplementedError`` on
        the placeholder — the v1 adapter does not preserve a native
        trajectory. Per the Protocol, empty-tuple entries are valid;
        skipping this strategy is the natural response.

        Parameters
        ----------
        trace
            The :class:`ODEIntegratorTrace` from the most recent
            :meth:`solve_ode` call.
        state
            The :class:`StateBundle` at t=1 (passed to
            :meth:`observe_endpoint`).
        paper_quantities
            Forwarded to :meth:`observe_entropy_reduction` for
            signature parity. Not consumed (entropy is a property
            of the trajectory / explicit ``theta_after`` alone).
        strategies
            Tuple of :class:`ObservationKind` the caller wants.
            The default requests all four kinds; the result tuple
            only contains the supported subset.
        theta_before, theta_after
            Optional entropy-reduction prior/posterior. Forwarded
            to :meth:`observe_entropy_reduction` when
            POSITION_ENTROPY_REDUCTION is in ``strategies``.

        Returns
        -------
        tuple[ObservationResult, ...]
            The supported subset of observation results. Length 0
            if ``strategies`` requests only unsupported kinds;
            length 2 when the default strategies tuple is supplied
            (ENDPOINT_BUNDLE + POSITION_ENTROPY_REDUCTION).
        """
        results: list[ObservationResult] = []
        if ObservationKind.ENDPOINT_BUNDLE in strategies:
            endpoint_bundle = self.observe_endpoint(trace, state)
            results.append(
                ObservationResult(
                    kind=ObservationKind.ENDPOINT_BUNDLE,
                    channel="endpoint_bundle",
                    payload=endpoint_bundle,
                    units="state_bundle",
                )
            )
        if ObservationKind.POSITION_ENTROPY_REDUCTION in strategies:
            reduction_dict = self.observe_entropy_reduction(
                trace,
                paper_quantities,
                theta_before=theta_before,
                theta_after=theta_after,
            )
            reduction_value = reduction_dict.get(
                PER_POSITION_ENTROPY_REDUCTION
            )
            results.append(
                ObservationResult(
                    kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
                    channel=PER_POSITION_ENTROPY_REDUCTION,
                    payload=float(reduction_value)
                    if reduction_value is not None
                    else None,
                    units="nats",
                    metadata={
                        "theta_before_supplied": theta_before is not None,
                        "theta_after_supplied": theta_after is not None,
                        "trace_digest": str(trace.native_state_digest),
                    },
                )
            )
        return tuple(results)

    def export_trajectory(self, trace: ODEIntegratorTrace) -> Any:
        """FlowMol3 adapter: no native trajectory preserved (P0-7)."""
        raise NotImplementedError(
            "FlowMol3Adapter does not preserve a native trajectory"
        )

    # ------------------------------------------------------------------
    # 9c. observe_entropy_reduction (Wave 49 Agent F — P2-W33-C metric)
    # ------------------------------------------------------------------

    def observe_entropy_reduction(
        self,
        trace: ODEIntegratorTrace,
        paper_quantities: Any = None,
        *,
        theta_before: NDArray[np.float64] | None = None,
        theta_after: NDArray[np.float64] | None = None,
    ) -> dict[str, float]:
        """Per-atom-type Shannon-entropy reduction (Wave 49 Agent F).

        Mirrors :meth:`LineageFlowAdapter.observe_entropy_reduction`
        (Wave 45 Agent E). Returns the per-atom entropy *reduction*
        from a baseline atom-type distribution ``theta_before`` to a
        framework endpoint ``theta_after``::

            reduction = H(theta_before) - H(theta_after)

        A positive reduction means the framework **sharpened** the
        per-atom atom-type posterior relative to the baseline; a
        negative reduction means it widened it. The metric is bounded
        in ``[-log K_atom, log K_atom]`` with ``K_atom =
        FLOWMOL3_ATOM_TYPE_VOCAB_SIZE = 10`` so the bound is
        ``[-log 10, log 10]``.

        The math is NOT re-derived here: this method selects the
        two ``theta`` arrays and delegates to
        :func:`adaptive_reflow.adapters._adapter_common.per_position_entropy_reduction`,
        the single definition of the formula in the tree.

        Why this is adapter-layer glue
        ------------------------------

        FlowMol3's native state carries a per-atom ``a`` categorical
        over the 10 heavy-atom types in GEOM-DRUGS-filtered. The
        framework's continuous-only ``paper_quantities`` is
        structurally ill-conditioned on FlowMol3's mixed ``(x, a, c, e)``
        state — see Wave 49 Agent C §5.1. The atom-type entropy is
        therefore adapter-internal: it is NOT a paper-quantity but
        it IS a chemistry-relevant posterior-sharpening signal.

        Two modes
        ---------

        * ``theta_after`` given — caller supplies the framework
          endpoint atom-type distribution (shape
          ``(n_atoms, K_atom)``). This is the canonical invocation
          path used by the eval pipeline.
        * Both ``theta_after`` and ``theta_before`` ``None`` (default)
          — **synthetic-mode fallback**: the placeholder has no real
          trajectory, so the method synthesises a deterministic
          uniform atom-type distribution from ``trace.native_state_digest``
          and returns the reduction ``H(uniform) - H(uniform) = 0``.
          This keeps the placeholder test surface byte-stable without
          a torch / dgl dependency.

        Parameters
        ----------
        trace
            The :class:`ODEIntegratorTrace` returned by the most
            recent :meth:`solve_ode` call. Only
            ``native_state_digest`` is consumed.
        paper_quantities
            Accepted for signature-parity with
            :meth:`LineageFlowAdapter.observe_entropy_reduction` so a
            duck-typed metric caller can invoke both the same way.
            Not consumed: the entropy reduction is a property of the
            trajectory / explicit ``theta_after`` alone.
        theta_before
            Optional baseline atom-type distribution of shape
            ``(n_atoms, K_atom)``. When ``None``, the synthetic-mode
            fallback is used.
        theta_after
            Optional framework-endpoint atom-type distribution of
            shape ``(n_atoms, K_atom)``. When ``None``, the
            synthetic-mode fallback is used.

        Returns
        -------
        dict[str, float]
            ``{"per_position_entropy_reduction": <float>}``. Bounded
            in ``[-log 10, log 10]``. ``0.0`` for the synthetic-mode
            fallback (uniform-vs-uniform); ``nan`` if either array
            degenerates to fewer than two atoms (preserved from the
            helper's contract — never papered over).
        """
        del paper_quantities  # Wave 49 Agent F surface only.

        if theta_after is None:
            # Synthetic-mode fallback: deterministic uniform
            # distribution. The placeholder has no real atom-type
            # marginal, so ``theta_before`` and ``theta_after`` are
            # both uniform and the reduction is exactly zero.
            # ``trace.native_state_digest`` is consumed only to make
            # the result deterministic per trace (so two calls with
            # the same trace return the same value).
            seed = int(
                hashlib.sha256(
                    f"flowmol3:entropy:{trace.native_state_digest}".encode()
                ).hexdigest()[:8],
                16,
            )
            rng = np.random.default_rng(seed)
            # Shape (8, 10) — matches FLOWMOL3_PLACEHOLDER_NUM_NODES ×
            # FLOWMOL3_ATOM_TYPE_VOCAB_SIZE so the result is byte-
            # stable across runs.
            theta_after_arr = rng.uniform(
                0.0, 1.0,
                size=(int(FLOWMOL3_PLACEHOLDER_NUM_NODES),
                      int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)),
            ).astype(np.float64)
            if theta_before is None:
                theta_before_arr = theta_after_arr.copy()
            else:
                theta_before_arr = np.asarray(theta_before, dtype=np.float64)
        else:
            theta_after_arr = np.asarray(theta_after, dtype=np.float64)
            if theta_before is None:
                # Default baseline: uniform atom-type distribution
                # (max-entropy reference).
                theta_before_arr = np.full_like(theta_after_arr, 1.0)
            else:
                theta_before_arr = np.asarray(theta_before, dtype=np.float64)

        reduction = per_position_entropy_reduction(
            theta_before_arr, theta_after_arr
        )
        return {PER_POSITION_ENTROPY_REDUCTION: float(reduction)}

    # ------------------------------------------------------------------
    # 10. inject_forward_noise (P1-8 / F-25 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """P1-8 (F-25): FlowMol3 carries no native state — pass through."""
        _require_valid(bundle, "inject_forward_noise_invalid_bundle")
        try:
            flat = list(getattr(injected, "flat", injected))
        except TypeError:
            flat = [injected]
        flat = flat[:32]
        new_digest = hashlib.sha256(
            json.dumps(
                {
                    "kind": "forward_noise",
                    "src_digest": str(bundle.native_state_digest),
                    "injected_head": [repr(float(x)) for x in flat],
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return replace(
            bundle,
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            source_round=int(bundle.source_round) + 1,
            detach_proof=True,
            native_state_digest=new_digest,
            provenance=tuple(bundle.provenance) + ("inject_forward_noise_applied",),
            capability_token=self.capabilities(),
        )


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def _try_load_real_ckpt(
    weights_path: str,
) -> tuple[Mapping[str, Any] | None, str | None]:
    """Attempt to load the published FlowMol3 Lightning checkpoint.

    Returns ``(meta, None)`` on success — ``meta`` is a
    ``Mapping[str, Any]`` carrying ``{path, n_tensors, epoch,
    global_step, lightning_version}`` so downstream audit reports can
    surface a ``real_ckpt_loaded`` marker.

    Returns ``(None, reason)`` on any failure — ``reason`` is a short
    human-readable string (``"torch_not_installed"`` /
    ``"ckpt_missing"`` / ``"ckpt_load_failed"`` /
    ``"ckpt_unexpected_shape"``). Never raises; the caller is expected
    to fall back to the synthetic placeholder path.

    Notes
    -----
    This is the **placeholder** adapter's loader: it only inspects the
    checkpoint shape / metadata, it does not run inference through the
    real FlowMol3 stack. The v2 adapter (``flowmol3_v2_adapter``) is
    the model that actually executes the ``vector_field`` against the
    loaded state dict.
    """
    if not os.path.isfile(str(weights_path)):
        return None, "ckpt_missing"
    try:
        import torch  # noqa: PLC0415 — checkpoint load is opt-in only.
    except Exception:  # noqa: BLE001 — torch is optional in the framework venv.
        return None, "torch_not_installed"
    try:
        blob = torch.load(
            str(weights_path), map_location="cpu", weights_only=False
        )
    except Exception:  # noqa: BLE001
        return None, "ckpt_load_failed"
    if not isinstance(blob, dict):
        return None, "ckpt_unexpected_shape"
    raw_sd = blob.get("state_dict", blob)
    if not isinstance(raw_sd, dict):
        return None, "ckpt_unexpected_shape"
    meta: dict[str, Any] = {
        "path": str(weights_path),
        "n_tensors": int(len(raw_sd)),
        "epoch": int(blob.get("epoch", -1))
        if isinstance(blob, dict) and "epoch" in blob
        else -1,
        "global_step": int(blob.get("global_step", -1))
        if isinstance(blob, dict) and "global_step" in blob
        else -1,
        "lightning_version": str(
            blob.get("pytorch-lightning_version", "")
            if isinstance(blob, dict)
            else ""
        ),
    }
    return meta, None


def default_flowmol3_adapter(
    *,
    atom_type_entropy_restart_policy: (
        FlowMol3AtomTypeEntropyRestartPolicy | None
    ) = None,
    force_mode: str = "synthetic",
    weights_path: str | None = None,
    nfe_budget: int | None = None,
    restart_min_nfe: int = FLOWMOL3_RESTART_MIN_NFE,
) -> FlowMol3Adapter:
    """Return a fresh :class:`FlowMol3Adapter` for tests and the registry.

    Wave 50 Agent A: ``force_mode`` selects the adapter operating mode
    so :func:`tools.run_real_ckpt_eval._resolve_adapter`'s
    ``factory(force_mode=...)`` call no longer raises
    ``TypeError: default_flowmol3_adapter() got an unexpected keyword
    argument force_mode``.

    Accepted values (mirrors :func:`tools.run_real_ckpt_eval._resolve_adapter`):

    * ``"synthetic"`` (default) — always use the placeholder path,
      byte-identical to the pre-Wave-50 behaviour. No file I/O.
    * ``"real"`` — load the real FlowMol3 Lightning checkpoint at
      :data:`FLOWMOL3_REAL_CKPT_PATH` (or the explicit ``weights_path``
      override). On any failure (missing file / missing torch /
      corrupted ckpt / unexpected shape) the factory raises
      ``FileNotFoundError`` / ``RuntimeError`` so the caller can
      distinguish a hard BLOCKED result from a graceful fallback.
    * ``"auto"`` — try the real ckpt; on any failure, degrade
      gracefully to the synthetic placeholder and return the adapter
      with ``_real_ckpt_meta=None``.

    Backward-compat: callers that omit ``force_mode`` see the same
    byte-identical placeholder behaviour they did before Wave 50.

    Wave 58: ``nfe_budget`` (the cell's **total** NFE budget) and
    ``restart_min_nfe`` are forwarded to :class:`FlowMol3Adapter` and
    drive the NFE-adaptive restart gate in
    :meth:`FlowMol3Adapter.apply_restart_distribution`. Omitting
    ``nfe_budget`` leaves the budget unknown, which keeps the gate
    inert — so this factory's default behaviour is byte-identical to
    pre-Wave-58 as well.
    """
    # Wave 53 Agent C: defensive alias. The eval pipeline translates
    # CLI ``"real"`` → ``"torch"`` for the 10 legacy ``{torch,
    # synthetic, auto}`` adapters. flowmol3 v1 adopted the new
    # ``{synthetic, real, auto}`` convention (Wave 50 Agent A); to
    # keep callers from other contexts (not the eval pipeline)
    # working, accept ``"torch"`` as a synonym for ``"real"``.
    if force_mode == "torch":
        force_mode = "real"
    if force_mode not in {"synthetic", "real", "auto"}:
        raise ValueError(
            f"unknown_force_mode:{force_mode} "
            "(expected 'synthetic' | 'real' | 'auto')"
        )
    real_ckpt_meta: Mapping[str, Any] | None = None
    if force_mode in {"real", "auto"}:
        ckpt_path = (
            str(weights_path)
            if weights_path is not None
            else str(FLOWMOL3_REAL_CKPT_PATH)
        )
        meta, err = _try_load_real_ckpt(ckpt_path)
        if meta is not None:
            real_ckpt_meta = meta
        elif force_mode == "real":
            raise FileNotFoundError(
                f"flowmol3_real_ckpt_load_failed:{err}:{ckpt_path}"
            )
        # force_mode == "auto": silently degrade to synthetic; the
        # caller sees an adapter with ``_real_ckpt_meta=None`` so the
        # downstream eval report can surface ``synthetic_fallback``.
    return FlowMol3Adapter(
        atom_type_entropy_restart_policy=atom_type_entropy_restart_policy,
        force_mode=str(force_mode),
        real_ckpt_meta=real_ckpt_meta,
        nfe_budget=nfe_budget,
        restart_min_nfe=restart_min_nfe,
    )


def flowmol3_registry_entry() -> Any:
    """Return the registry entry that pairs with this adapter."""
    return make_default_flowmol3_entry()


__all__ = [
    "AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART",
    "AUDIT_FLOWMOL3_OBSERVED",
    "AUDIT_FLOWMOL3_RESTART_BLEND",
    "AUDIT_FLOWMOL3_RESTART_SKIPPED_LOW_NFE",
    "FLOWMOL3_ATOM_TYPE_VOCAB_SIZE",
    "FLOWMOL3_CHANNELS",
    "FLOWMOL3_CHANNEL_DOMAINS",
    "FLOWMOL3_PLACEHOLDER_NUM_EDGES",
    "FLOWMOL3_PLACEHOLDER_NUM_NODES",
    "FLOWMOL3_REAL_CKPT_LOADED_MARKER",
    "FLOWMOL3_REAL_CKPT_PATH",
    "FLOWMOL3_RESTART_MIN_NFE",
    "FlowMol3Adapter",
    "FlowMol3AtomTypeEntropyRestartPolicy",
    "FlowMol3Capabilities",
    "PER_POSITION_ENTROPY_REDUCTION",
    "default_flowmol3_adapter",
    "flowmol3_registry_entry",
]
