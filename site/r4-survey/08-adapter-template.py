"""Adapter template — :class:`MySotaModelAdapter` (DTB-G1 conformance).

This file lives in :mod:`docs.r4-survey` so the user can copy it into
their project and rename ``MySotaModelAdapter`` to their adapter's real
class name. It ships **stubbed bodies** for the five methods the user
must implement (2, 3, 6, 7, 8) and **working defaults** for the three
methods that almost never need custom logic (1, 4, 5). After the user
fills in their model's specifics, the class satisfies the
:class:`adaptive_reflow.universal.FlowMatchingODEAdapter` Protocol and
can be dropped into any FlowA driver (``tools/run_sota_comparison.py``,
``tools/run_ablation.py``, :class:`ReInferenceRunner`, etc.).

Usage example::

    # 1. Copy this file into your project's adapters/ directory and
    #    rename the class to e.g. ``MyCIFARFlowAdapter``.
    # 2. Fill in the five stubs to wire your model into the engine:
    #       build_initial_state     (line ~150)
    #       export_endpoint         (line ~190)
    #       compose_condition       (line ~270)
    #       solve_ode               (line ~310)
    #       observe_endpoint        (line ~370)
    # 3. Plug into the SOTA harness:
    #       python tools/run_sota_comparison.py \\
    #           --adapter-class your_pkg.adapters.my_adapter:MyCIFARFlowAdapter \\
    #           --n-samples 200 --n-rounds 20 --output-dir ./my_sota_out

Constraints the template guarantees:

* **No torch dependency**. The stub bodies use only ``numpy`` and
  stdlib so the file imports cleanly even on a CPU-only machine. If
  your model is a ``torch.nn.Module``, replace the stub bodies with
  your torch-forward code; the rest of the protocol surface stays
  identical (opaque ``TensorRef`` handles flow through the engine
  regardless of the underlying framework).
* **Byte-deterministic**. Every stub stores its inputs in a stable
  ``dict`` keyed by string labels; the canonical digest can be
  replaced with the user's stable hasher.
* **Single-channel default** (``"samples"``). Change
  :data:`MY_SOTA_CHANNELS` to match your model's output vocabulary.

Method map (the 8-method Protocol; the 5 the user fills in are
highlighted):

    1. capabilities                                — **default impl**
    2. build_initial_state                         — **stub** (user fills)
    3. export_endpoint                             — **stub** (user fills)
    4. detach_and_validate_endpoint                — **default impl**
    5. apply_restart_distribution                  — **default impl**
    6. compose_condition                           — **stub** (user fills)
    7. solve_ode                                   — **stub** (user fills)
    8. observe_endpoint                            — **stub** (user fills)

The default impls (1, 4, 5) match the canonical 2D adapter's
behaviour; they are correct for ``continuous`` channels and will only
need customisation for discrete/latent/graph-shaped state spaces.
"""
from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# We import the Protocol surface by name only so the file stays
# import-clean even when the user has not installed the framework yet.
# Replace these imports with your project's actual import paths when
# you copy this template into your own adapter package.
try:
    from adaptive_reflow.universal import (
        AdapterCapabilities,
        CapabilityMissingError,
        FlowMatchingODEAdapter,
        NoOpMixer,
    )
    from adaptive_reflow.universal.state import (
        ChannelDomain,
        ChannelName,
        ODEConditionDelta,
        ODEIntegratorTrace,
        StateBundle,
        TensorRef,
        validate_state_bundle,
    )
except ImportError:  # pragma: no cover — running outside the framework
    # Stubs below let the file still lint / type-check in isolation.
    # Replace these with real imports when the framework is on the
    # Python path.
    AdapterCapabilities = Any  # type: ignore[misc,assignment]
    CapabilityMissingError = Exception  # type: ignore[misc,assignment]
    FlowMatchingODEAdapter = object  # type: ignore[misc,assignment]
    NoOpMixer = object  # type: ignore[misc,assignment]

    ChannelDomain = Any  # type: ignore[misc,assignment]
    ChannelName = str  # type: ignore[misc,assignment]
    ODEConditionDelta = Any  # type: ignore[misc,assignment]
    ODEIntegratorTrace = Any  # type: ignore[misc,assignment]
    StateBundle = Any  # type: ignore[misc,assignment]
    TensorRef = str  # type: ignore[misc,assignment]

    def validate_state_bundle(_bundle: Any) -> tuple[bool, tuple[str, ...]]:
        return True, ()


# ---------------------------------------------------------------------------
# User-supplied constants — MODIFY THESE for your model.
# ---------------------------------------------------------------------------


#: Adapter's channel vocabulary. The canonical 2D adapter uses
#: ``("xy",)``; image / latent adapters should use ``("samples",)``
#: or a tuple of channel labels matching the model's output axes.
#: The runner consumes the *first* channel as the primary (it asks
#: the policy driver to compute ``beta`` for it).
MY_SOTA_CHANNELS: tuple[str, ...] = ("samples",)

#: Stable config hash for the adapter. Derive from
#: ``model architecture + version + checkpoint digest`` so two
#: adapters with the same model instance emit byte-identical hashes.
MY_SOTA_CONFIG_HASH: str = "my_sota_model:v0"

#: Config version (free-form string; recorded in the audit trail).
MY_SOTA_CONFIG_VERSION: str = "0.1.0"

#: Domain kind for each channel. The canonical 2D adapter uses
#: ``"continuous"``; image-style flow-matching models also use
#: ``"continuous"``; latent / graph models should declare
#: ``"latent"`` or ``"graph"`` respectively.
MY_SOTA_CHANNEL_DOMAINS: Mapping[str, str] = {
    "samples": "continuous",
}

#: Optional LRU bound on the adapter's ``_native_states`` cache.
#: Set to ``None`` for an unbounded cache (acceptable for unit
#: tests; production adapters should set a bound).
MY_SOTA_NATIVE_STATES_MAXSIZE: int | None = 128


# ---------------------------------------------------------------------------
# Helpers — pure, stdlib-only, framework-free.
# ---------------------------------------------------------------------------


def _seed_from_ids(batch_id: str, sample_id: str, source_round: int) -> int:
    """Derive a deterministic 32-bit seed from identifier triple."""
    blob = repr((str(batch_id), str(sample_id), int(source_round))).encode("utf-8")
    return int(hashlib.sha256(blob).hexdigest()[:8], 16)


def _digest_state(payload: Mapping[str, Any]) -> str:
    """Return a deterministic SHA-256 hex digest of a payload (sorted keys)."""
    blob = repr(
        (tuple(sorted(payload.items(), key=lambda kv: str(kv[0]))),)
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _make_ref(label: str, **parts: Any) -> Any:
    """Build a deterministic hash-stable :class:`TensorRef` from parts."""
    blob = repr((label, tuple(sorted(parts.items())))).encode("utf-8")
    return TensorRef(
        f"my_sota:{label}:{hashlib.sha256(blob).hexdigest()[:16]}"
    )


# ---------------------------------------------------------------------------
# Capability declaration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MySotaCapabilities(AdapterCapabilities):
    """Static capability surface advertised by :class:`MySotaModelAdapter`.

    The defaults below are the canonical 2D adapter's surface (the
    engine treats every adapter as if it has the full set of
    capabilities unless the flags say otherwise). For a model that
    does NOT support restart blending, set
    ``has_restart_boundary=False`` and the engine will skip the
    restart step. For a model without condition injection, set
    ``has_condition_injection=False``.
    """

    def __init__(self) -> None:
        super().__init__(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            has_continuous_channels=True,
            has_discrete_channels=False,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=True,
            # F14: native state shape. Override to match your
            # model's actual state shape (e.g. ``(3, 64, 64)`` for
            # a CIFAR image model). The runner uses this to size
            # the forward-noise injection prior array.
            state_shape=(2,),
            supported_channels=tuple(MY_SOTA_CHANNELS),
            channel_domains={
                ChannelName(name): dom  # type: ignore[arg-type]
                for name, dom in MY_SOTA_CHANNEL_DOMAINS.items()
            },
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=MY_SOTA_CONFIG_HASH,
            native_config_version=MY_SOTA_CONFIG_VERSION,
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class MySotaModelAdapter(FlowMatchingODEAdapter):
    """Flow-matching ODE adapter template (DTB-G1).

    Implements the 8-method :class:`FlowMatchingODEAdapter` Protocol
    against an arbitrary pre-trained flow matching model. The user
    fills in 5 stubs (``build_initial_state``, ``export_endpoint``,
    ``compose_condition``, ``solve_ode``, ``observe_endpoint``); the
    remaining 3 (``capabilities``, ``detach_and_validate_endpoint``,
    ``apply_restart_distribution``) have working defaults that match
    the canonical 2D adapter's behaviour.

    The class is **byte-deterministic**: every state-touching method
    stores its inputs under a stable SHA-256 digest in
    ``self._native_states`` so the engine's opaque
    ``TensorRef`` handles always round-trip. The cache is bounded by
    :data:`MY_SOTA_NATIVE_STATES_MAXSIZE` (LRU insertion order); set
    the constant to ``None`` to disable the bound.
    """

    #: Optional integration step count forwarded to the ``solve_ode``
    #: method via the condition delta. ``None`` means "delegate to
    #: the condition delta's ``num_steps`` field, default 100".
    pinned_num_steps: int | None = 100

    def __init__(
        self,
        *,
        # ---- model-loading kwargs the user supplies ----
        model_path: str | None = None,
        config: Mapping[str, Any] | None = None,
        seed_offset: int = 0,
        # ---- optional infra overrides ----
        native_states_maxsize: int | None = MY_SOTA_NATIVE_STATES_MAXSIZE,
    ) -> None:
        # LRU-bounded native-state cache. Without a bound, the
        # adapter's memory footprint grows with the number of engine
        # rounds (audit A-3 in the run_ablation script's design doc).
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._native_states_maxsize = native_states_maxsize
        self._seed_offset = int(seed_offset)
        self._caps = MySotaCapabilities()

        # Initialise the underlying model — the user wires this in
        # their subclass or directly via the model_path kwarg. The
        # stub below is a placeholder that records the model's
        # presence but does not load anything heavy.
        self._model: Any = self._load_model(
            model_path=str(model_path) if model_path else "",
            config=dict(config) if config is not None else {},
        )

    # ------------------------------------------------------------------
    # 1. capabilities (default impl — fill in MY_SOTA_* constants)
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        """Return the cached :class:`AdapterCapabilities` instance.

        The defaults advertise the full 2D-adapter capability set;
        override :class:`MySotaCapabilities` (or the
        :data:`MY_SOTA_*` constants) for models that do not
        support restart blending, condition injection, or
        trajectory-digest emission.
        """
        return self._caps

    # ------------------------------------------------------------------
    # LRU helpers (audit A-3 fix)
    # ------------------------------------------------------------------

    def _put_native_state(
        self, digest: str, entry: dict[str, Any]
    ) -> None:
        """Insert ``entry`` under ``digest``; evict oldest past maxsize."""
        if digest in self._native_states:
            self._native_states[digest] = entry
            self._native_states.move_to_end(digest)
            return
        self._native_states[digest] = entry
        if self._native_states_maxsize is None:
            return
        while len(self._native_states) > self._native_states_maxsize:
            self._native_states.popitem(last=False)

    def _evict_native_state(self, digest: str) -> None:
        """Remove ``digest`` from the cache if present (no-op when absent)."""
        self._native_states.pop(digest, None)

    def _resolve(self, digest: str) -> dict[str, Any] | None:
        """Return the cached entry for ``digest`` (or ``None``)."""
        return self._native_states.get(digest)

    # ------------------------------------------------------------------
    # 2. build_initial_state — STUB (USER FILLS IN)
    # ------------------------------------------------------------------

    def build_initial_state(
        self, *, batch_id: str, sample_id: str
    ) -> StateBundle:
        """Build a fresh initial state bundle for ``(batch_id, sample_id)``.

        **The user MUST implement this method.** It is the source of
        every prior draw the engine consults; the canonical pattern
        is to:

        1. Draw a fresh latent sample (e.g. ``x0 ~ N(0, I)`` for a
           continuous prior; or your model's native sampler for a
           latent prior).
        2. Compute a deterministic SHA-256 digest of the prior +
           identifiers via :func:`_digest_state`.
        3. Store the prior under that digest via
           :meth:`_put_native_state` so subsequent calls
           (``solve_ode``, ``apply_restart_distribution``,
           ``observe_endpoint``) can resolve it by digest.
        4. Return a :class:`StateBundle` whose ``native_state_digest``
           is that SHA-256 digest.

        The returned bundle MUST validate via
        :func:`validate_state_bundle` (it sets every required field:
        channels, masks, batch_id, sample_id, reference_frame,
        normalization, source_round, detach_proof, native_state_digest,
        provenance, capability_token).
        """
        raise NotImplementedError(
            "MySotaModelAdapter.build_initial_state: replace this stub "
            "with the model-specific prior-draw logic for "
            f"(batch_id={batch_id!r}, sample_id={sample_id!r})"
        )

    # ------------------------------------------------------------------
    # 3. export_endpoint — STUB (USER FILLS IN)
    # ------------------------------------------------------------------

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        """Return a fresh :class:`StateBundle` holding the model's endpoint.

        **The user MUST implement this method.** The default below
        pass-throughs the bundle when the adapter has no native
        "endpoint export" step; production adapters usually add a
        post-``observe_endpoint`` side-effect (e.g. encoding the
        observation into a checkpoint file, attaching auxiliary
        metadata to the bundle's provenance tuple, etc.).
        """
        raise NotImplementedError(
            "MySotaModelAdapter.export_endpoint: replace this stub "
            "with the model-specific endpoint export (e.g. attach "
            "checkpoint metadata, encode observation, etc.)"
        )

    # ------------------------------------------------------------------
    # 4. detach_and_validate_endpoint — DEFAULT IMPL
    # ------------------------------------------------------------------

    def detach_and_validate_endpoint(
        self, bundle: StateBundle
    ) -> StateBundle:
        """Validate ``bundle.detach_proof`` and return it unchanged.

        The engine calls this method to enforce a fail-closed
        "detached observation" guarantee: a bundle whose
        ``detach_proof is True`` carries an observation-side value
        that is independent of any in-flight trajectory, and the
        adapter MUST NOT silently reject a detached bundle. The
        canonical default below is correct for all standard flow
        matching models; override only when ``detach_proof`` is
        *not* the right detach signal for your model (e.g. when the
        detached state must round-trip through a transformer cache
        rather than a SHA-256 digest).
        """
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        if bundle.detach_proof is not True:
            raise CapabilityMissingError(
                "detach_proof_must_be_true", context="state"
            )
        return bundle

    # ------------------------------------------------------------------
    # 5. apply_restart_distribution — DEFAULT IMPL
    # ------------------------------------------------------------------

    def apply_restart_distribution(
        self, state: StateBundle, policy: Any
    ) -> StateBundle:
        """Blend the prior endpoint with fresh noise by ``memory_fraction``.

        The default below matches the canonical 2D adapter's
        ``LinearBlender`` behaviour: it computes
        ``m = 1 - beta = memory_fraction`` from ``policy.beta_by_channel``,
        blends the cached prior ``x0`` with a fresh ``N(0, I_d)``
        draw, and emits a new ``StateBundle`` whose
        ``native_state_digest`` is a fresh SHA-256 digest over the
        blended value + identifiers. Override when your model needs
        a non-linear blender (e.g. exponential decay in
        ``memory_fraction``) or the prior lives in a different
        coordinate frame.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._resolve(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=state.native_state_digest
            )
        # Memory fraction defaults to 0.5 when the policy omits the
        # primary channel. The first channel is the runner's
        # ``primary_channel``; consult ``state.channels`` for the
        # canonical key.
        primary = list(state.channels.keys())[0]
        beta_raw = policy.beta_by_channel.get(primary)  # type: ignore[union-attr]
        if beta_raw is None:
            beta = 0.5
            memory_fraction = 0.5
        else:
            beta = float(beta_raw)  # type: ignore[arg-type]
            memory_fraction = 1.0 - beta
        # Stub blend math — replace with the adapter-specific
        # ``x0 -> fresh_x0`` blend. The default below mirrors the
        # canonical 2D adapter: ``m * prior + (1 - m) * fresh``.
        prior_x0 = prior_entry["x0"]
        fresh_x0 = prior_x0  # TODO(user): sample fresh_x0 from your prior
        m_clipped = max(0.0, min(1.0, float(memory_fraction)))
        if hasattr(prior_x0, "__len__") and hasattr(fresh_x0, "__len__"):
            blended_x0 = [
                m_clipped * float(p) + (1.0 - m_clipped) * float(f)
                for p, f in zip(prior_x0, fresh_x0, strict=False)
            ]
        else:  # pragma: no cover — defensive
            blended_x0 = prior_x0
        next_round = int(state.source_round) + 1
        next_digest = _digest_state(
            {
                "kind": "restart",
                "src_digest": state.native_state_digest,
                "policy_hash": str(getattr(policy, "policy_hash", "")),
                "source_round": next_round,
                "beta": float(beta),
                "memory_fraction": float(memory_fraction),
                "blended_x0": (
                    list(blended_x0)  # type: ignore[arg-type]
                    if hasattr(blended_x0, "__iter__")
                    else [blended_x0]
                ),
            }
        )
        self._put_native_state(
            next_digest,
            {
                "x0": blended_x0,
                "source_round": next_round,
            },
        )
        return StateBundle(
            channels={
                primary: _make_ref(
                    "restart",
                    src_digest=str(state.native_state_digest),
                    source_round=int(next_round),
                ),
            },
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=str(next_digest),
            provenance=tuple(state.provenance)
            + ("my_sota_restart_blend",),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 6. compose_condition — STUB (USER FILLS IN)
    # ------------------------------------------------------------------

    def compose_condition(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        """Return an :class:`ODEConditionDelta` carrying model-specific knobs.

        **The user MUST implement this method.** The default below
        pass-throughs ``delta`` unchanged; production adapters
        typically:

        * Add a ``num_steps`` / ``time_grid`` field to
          ``delta.delta_spec`` based on the model's pinned
          ``pinned_num_steps`` and any user override from
          ``delta.delta_spec['num_steps']``.
        * Stamp the model's ``native_config_hash`` into
          ``delta.delta_spec`` so downstream consumers (audit
          ledger, evaluator) can attribute the round to the
          correct model instance.
        * Optionally replace ``delta.calibration_artifact_hash``
          with a model-specific artifact hash (default
          ``runner-calibration`` is fine when no calibration step
          is required).
        """
        raise NotImplementedError(
            "MySotaModelAdapter.compose_condition: replace this stub "
            "with model-specific condition adjustments "
            f"(delta_spec keys seen: {list(delta.delta_spec)!r})"
        )

    # ------------------------------------------------------------------
    # 7. solve_ode — STUB (USER FILLS IN)
    # ------------------------------------------------------------------

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        """Integrate the model ODE from ``state`` to its endpoint.

        **The user MUST implement this method.** The stub raises
        ``NotImplementedError`` so the adapter fails loudly when
        plugged into the engine without being filled in. Production
        implementations typically:

        1. Resolve the prior via ``self._resolve(state.native_state_digest)``
           (the prior was stashed in :meth:`build_initial_state` /
           :meth:`apply_restart_distribution`).
        2. Build an integration ``t_grid`` (default ``np.linspace(0, 1, num_steps + 1)``).
        3. Step the model forward via the user's integrator (RK4,
           Dormand-Prince, Heun, DPM-Solver, UniPC, …) and store the
           full trajectory under a fresh SHA-256 digest via
           :meth:`_put_native_state`.
        4. Return an :class:`ODEIntegratorTrace` whose
           ``native_state_digest`` matches the stored trajectory
           digest and whose ``integrator_config_hash`` is a stable
           SHA-256 over ``(method, num_steps, seed)``.

        The ``seed`` keyword is forwarded by the runner; pass it to
        your integrator's seeding kwargs so two calls with the same
        (model, state, seed) reproduce bit-for-bit.
        """
        raise NotImplementedError(
            "MySotaModelAdapter.solve_ode: replace this stub with the "
            "model-specific integration step. The default signature "
            "(state, condition, *, seed) matches every shipped "
            "adapter (TwoDimFM, MnistFM, StochasticFM, etc.)."
        )

    # ------------------------------------------------------------------
    # 8. observe_endpoint — STUB (USER FILLS IN)
    # ------------------------------------------------------------------

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        """Return the observation-side :class:`StateBundle` for ``trace``.

        **The user MUST implement this method.** The stub raises
        ``NotImplementedError``. Production implementations:

        1. Resolve the trajectory via
           ``self._resolve(trace.native_state_digest)``.
        2. Pull the *final* trajectory point (or the per-model
           observation-side reduction thereof) and stash it under a
           fresh SHA-256 digest via :meth:`_put_native_state`.
        3. Return a :class:`StateBundle` whose ``source_round`` has
           advanced by 1, whose ``detach_proof=True``, whose
           ``native_state_digest`` is the endpoint digest, and whose
           ``provenance`` carries a model-specific tag (e.g.
           ``"my_sota_observed"``).
        """
        raise NotImplementedError(
            "MySotaModelAdapter.observe_endpoint: replace this stub "
            "with the model-specific endpoint-observation logic "
            "(trajectory -> StateBundle, advance source_round)"
        )

    # ------------------------------------------------------------------
    # 9. export_trajectory (default impl — P0-7 public surface)
    # ------------------------------------------------------------------

    def export_trajectory(self, trace: ODEIntegratorTrace) -> Any | None:
        """Return the native trajectory for ``trace`` (or ``None``).

        The runner uses this public method to extract the per-round
        trajectory without reaching into the adapter's private
        ``_native_states`` dict. The default below returns the
        cached entry's ``"trajectory"`` field when present;
        production adapters can override to apply post-processing
        (normalisation, denoising, etc.).
        """
        entry = self._resolve(trace.native_state_digest)
        if entry is None:
            return None
        return entry.get("trajectory")

    # ------------------------------------------------------------------
    # model loader (stub — user replaces with their checkpoint loader)
    # ------------------------------------------------------------------

    def _load_model(
        self, *, model_path: str, config: dict[str, Any]
    ) -> Any:
        """Load the user's pretrained model from ``model_path``.

        **The user MAY override this method.** The default returns
        ``None`` so the adapter can still be type-checked without a
        real model; the stubs will fail at runtime with a clear
        diagnostic pointing at the user's stub site.
        """
        return None


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__: list[str] = [
    "MY_SOTA_CHANNEL_DOMAINS",
    "MY_SOTA_CHANNELS",
    "MY_SOTA_CONFIG_HASH",
    "MY_SOTA_CONFIG_VERSION",
    "MY_SOTA_NATIVE_STATES_MAXSIZE",
    "MySotaCapabilities",
    "MySotaModelAdapter",
]
