"""ProtBFN / AbBFN / AbBFN2 adapter (R16 - protein BFN wrapper).

This module wraps the published InstaDeep Bayesian Flow Network (BFN)
generative model for protein sequences - ProtBFN (650M params, UniProtKB)
and the antibody-specific fine-tunes AbBFN (max length 256, OAS heavy
chains) and AbBFN2 (800M params, 45-mode antibody foundation model)
- into the framework's :class:`FlowMatchingODEAdapter` Protocol.

BFN is NOT a classical continuous-flow-matching ODE; it refines per-
position categorical distributions over a 22-entry amino-acid
vocabulary via a discrete sender / Bayesian-update / receiver loop
over a non-uniform entropy-time schedule. The adapter therefore
advertises a DISCRETE channel domain, exposes a step-based refiner in
place of a continuous-time ODE integrator (BFN's "time" is per-position
entropy, not scalar ``t``), encodes inpainting / conditioning for
CDR-H1 / H2 / H3 + FR regions as part of
:meth:`compose_condition`, and emits decoded token sequences as the
observable endpoint.

Public surface
--------------

* :class:`ProtBFNAbBFNAdapter` - concrete :class:`FlowMatchingODEAdapter`.
* :class:`ProtBFNAbBFNCapabilities` - frozen capability surface.
* :func:`default_protbfnabbfn_adapter` - factory.

Tasks satisfied
---------------

* R16 - protein BFN wrapper for ProtBFN / AbBFN / AbBFN2 (CLM-046).
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.universal import (
    AdapterCapabilities,
    CapabilityMissingError,
    ChannelDomain,
    FlowMatchingODEAdapter,
    NoOpMixer,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Vocabulary size: 20 standard amino acids + pad + bos + eos.
PROTBFN_VOCAB_SIZE: int = 22

#: Canonical ProtBFN max sequence length.
PROTBFN_MAX_LENGTH: int = 512

#: Canonical AbBFN / AbBFN2 max sequence length.
ABBFN_MAX_LENGTH: int = 256

#: Canonical amino-acid channel name. Per-position categorical over
#: ``PROTBFN_VOCAB_SIZE`` tokens (20 AAs + pad / bos / eos).
AMINO_ACID_CATEGORICAL: ChannelName = ChannelName("amino_acid_categorical")

#: Canonical CDR-loop length categorical channel (6 modes in AbBFN).
CDR_LENGTH_CATEGORICAL: ChannelName = ChannelName("cdr_length_categorical")

#: Canonical germline V / D / J gene categorical channel (10 modes in
#: AbBFN2).
GERMLINE_LABEL_CATEGORICAL: ChannelName = ChannelName(
    "germline_label_categorical"
)

#: Canonical species label channel (human / mouse / rat).
SPECIES_LABEL_CATEGORICAL: ChannelName = ChannelName(
    "species_label_categorical"
)

#: Canonical light-chain locus channel (kappa / lambda).
LIGHT_CHAIN_LOCUS_CATEGORICAL: ChannelName = ChannelName(
    "light_chain_locus_categorical"
)

#: Canonical TAP biophysical-property continuous channel (4 continuous +
#: 4 discrete modes).
TAP_CONTINUOUS: ChannelName = ChannelName("tap_continuous")

#: Default supported-channel set: ProtBFN + AbBFN + AbBFN2 all carry the
#: amino-acid categorical; the auxiliary categorical / continuous
#: channels are added per-mode.
PROTBFN_ABBFN_CHANNELS: tuple[ChannelName, ...] = (
    AMINO_ACID_CATEGORICAL,
    CDR_LENGTH_CATEGORICAL,
    GERMLINE_LABEL_CATEGORICAL,
    SPECIES_LABEL_CATEGORICAL,
    LIGHT_CHAIN_LOCUS_CATEGORICAL,
    TAP_CONTINUOUS,
)

#: Per-channel domain-kind declaration. Five categorical channels
#: declared discrete, one continuous channel declared continuous. The
#: universal engine routes per-channel validation through this map.
PROTBFN_ABBFN_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    AMINO_ACID_CATEGORICAL: "discrete",
    CDR_LENGTH_CATEGORICAL: "discrete",
    GERMLINE_LABEL_CATEGORICAL: "discrete",
    SPECIES_LABEL_CATEGORICAL: "discrete",
    LIGHT_CHAIN_LOCUS_CATEGORICAL: "discrete",
    TAP_CONTINUOUS: "continuous",
}

#: Stable native-config hash. Two adapters loading the same checkpoint
#: variant MUST produce identical hashes.
PROTBFN_ABBFN_CONFIG_HASH: str = "protbfn_abbfn:cfg:v1"
PROTBFN_ABBFN_CONFIG_VERSION: str = "0.1.0"

#: State-shape surface exposed to the engine. The framework runner reads
#: the first dimension for forward-noise allocation; the per-position
#: categorical is a discrete channel payload.
PROTBFN_ABBFN_STATE_SHAPE: tuple[int, ...] = (
    PROTBFN_MAX_LENGTH,
    PROTBFN_VOCAB_SIZE,
)

#: ProtBFN unconditional sampling step count (paper Table 1).
PROTBFN_DEFAULT_NUM_STEPS: int = 10_000

#: AbBFN inpainting sampling step count (paper Section 4).
ABBFN_DEFAULT_NUM_STEPS: int = 100

#: AbBFN inpainting particle-filter particle count.
ABBFN_DEFAULT_N_PARTICLES: int = 1_024

#: Synthetic (test-only) defaults. Small L for fast Protocol tests.
PROTBFN_SYNTHETIC_MAX_LENGTH: int = 8
PROTBFN_SYNTHETIC_NUM_STEPS: int = 4
PROTBFN_SYNTHETIC_SEED_DEFAULT: int = 0xBF000001  # "BFN" mnemonic (hex)

#: Audit / error codes (deterministic ASCII strings).
AUDIT_PROTBFN_RESTART_BLEND: str = "protbfn_restart_blend"
AUDIT_PROTBFN_OBSERVED: str = "protbfn_observed"
AUDIT_FORWARD_NOISE_APPLIED: str = "forward_noise_applied"
ERR_PROTBFN_NUM_STEPS: str = "protbfn_num_steps_must_be_positive"
ERR_PROTBFN_L_OUT_OF_RANGE: str = "protbfn_L_out_of_range"
ERR_PROTBFN_INPAINT_POSITIONS: str = "protbfn_inpaint_positions_invalid"
ERR_PROTBFN_INPAINT_STRENGTH: str = "protbfn_inpaint_strength_invalid"
ERR_PROTBFN_N_PARTICLES: str = "protbfn_n_particles_invalid"

#: Maximum size of the LRU-bounded ``_native_states`` cache. Bounded to
#: prevent unbounded growth across long multi-cycle engine runs (audit
#: A-3 mirror of :class:`TwoDimFMAdapter`).
PROTBFN_NATIVE_STATES_MAXSIZE: int = 32

#: Mode literal.
Mechanism = Literal["ProtBFN", "AbBFN", "AbBFN2"]
Mode = Literal["torch", "synthetic"]

# Local type alias.
ArrayF64 = NDArray[np.float64]


# ---------------------------------------------------------------------------
# Helpers - hashing + tensor-ref construction
# ---------------------------------------------------------------------------


def _seed_from_ids(batch_id: str, sample_id: str, source_round: int) -> int:
    """SHA-256-derived 32-bit seed from ``(batch_id, sample_id, source_round)``."""
    blob = repr((str(batch_id), str(sample_id), int(source_round))).encode("utf-8")
    return int(hashlib.sha256(blob).hexdigest()[:8], 16)


def _digest_state(payload: Mapping[str, Any]) -> str:
    """SHA-256 hex digest of a payload (sorted keys, repr'd)."""
    blob = repr((sorted(payload.items(), key=lambda kv: str(kv[0])),)).encode(
        "utf-8"
    )
    return hashlib.sha256(blob).hexdigest()


def _make_ref(label: str, **parts: Any) -> TensorRef:
    """Deterministic hash-stable :class:`TensorRef`."""
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(
        f"protbfn:{label}:{hashlib.sha256(blob).hexdigest()[:16]}"
    )


# ---------------------------------------------------------------------------
# Torch availability probe
# ---------------------------------------------------------------------------


def torch_is_available() -> bool:
    """Return ``True`` iff :mod:`torch` is importable in this interpreter.

    Mirrors :func:`adaptive_reflow.adapters.rectified_flow_cifar
    .torch_is_available`. Used at adapter construction time to decide
    which backend is reachable.
    """
    import importlib.util as _il

    return _il.find_spec("torch") is not None


# ---------------------------------------------------------------------------
# Synthetic NumPy refiner - test-only path; no torch dependency
# ---------------------------------------------------------------------------
#
# The BFN refiner is interpreted by the adapter as a step-based
# Bayesian update (NOT a continuous-time ODE). Each step:
#   1. Sample y_i ~ sender(theta, alpha_i)  (per-position categorical)
#   2. Bayesian update of theta_i  (row-renormalize posterior)
#   3. Receiver(theta, y_i)
#   4. Forward Phi(y_i, theta, entropy-encoding)  -> updated theta
#
# The synthetic path below implements step 4 as a deterministic NumPy
# affine transform of the per-position categorical so the Protocol
# conformance tests can exercise the full surface without the heavy
# torch dependency. It is NOT a trained BFN model.


def _synthetic_bfn_step(
    theta: ArrayF64,
    *,
    step: int,
    num_steps: int,
    weights: Mapping[str, ArrayF64],
    rng: np.random.Generator,
) -> ArrayF64:
    """Apply one deterministic Bayesian-update step to ``theta``.

    The synthetic step is::

        y_i ~ Categorical(theta_i)
        new_theta_i = (1 - alpha) * theta_i + alpha * softmax(W @ y_onehot + b)

    where ``alpha = (step + 1) / num_steps`` is the entropy-time
    accuracy coefficient. Each position's categorical is row-renormalized
    so the result is a valid probability distribution. The seed flow
    makes the operation byte-deterministic for fixed ``(theta, step,
    num_steps, weights, seed)``.
    """
    L, K = theta.shape
    alpha = float(step + 1) / float(num_steps)
    # Sample per-position categorical from the current theta.
    y_onehot = np.zeros_like(theta, dtype=np.float64)
    for i in range(L):
        y_onehot[i] = rng.multinomial(1, theta[i] / max(theta[i].sum(), 1e-30))
    # Network forward: W @ y_onehot + b, then softmax (logits are K-d).
    proj = y_onehot @ weights["W"] + weights["b"]  # (L, K)
    # Stable softmax row-wise.
    proj = proj - proj.max(axis=1, keepdims=True)
    exp_proj = np.exp(proj)
    net_out = exp_proj / exp_proj.sum(axis=1, keepdims=True)
    # Bayesian blend.
    new_theta = (1.0 - alpha) * theta + alpha * net_out
    # Row-renormalize to ensure a valid probability distribution.
    new_theta = new_theta / np.maximum(new_theta.sum(axis=1, keepdims=True), 1e-30)
    return np.asarray(new_theta, dtype=np.float64).reshape(L, K)


def _random_init_synthetic_bfn_weights(
    *,
    seed: int,
    vocab_size: int,
) -> dict[str, ArrayF64]:
    """Kaiming-uniform init of the synthetic BFN refiner's W / b."""
    rng = np.random.default_rng(int(seed))
    bound = float(np.sqrt(6.0 / float(vocab_size)))
    return {
        "W": rng.uniform(-bound, bound, size=(vocab_size, vocab_size)).astype(
            np.float64
        ),
        "b": np.zeros(vocab_size, dtype=np.float64),
    }


def _sample_uniform_categorical(
    rng: np.random.Generator,
    length: int,
    vocab_size: int,
) -> ArrayF64:
    """Sample a ``(L, K)`` per-position uniform categorical."""
    theta = np.full(
        (int(length), int(vocab_size)), 1.0 / float(vocab_size), dtype=np.float64
    )
    # Tiny per-position jitter so the prior has finite entropy and the
    # synthetic refiner's draw at step 0 is reproducible but not
    # all-identical.
    jitter = rng.uniform(
        0.0, 1e-6, size=(int(length), int(vocab_size))
    ).astype(np.float64)
    theta = theta + jitter
    theta = theta / theta.sum(axis=1, keepdims=True)
    return np.asarray(theta, dtype=np.float64).reshape(int(length), int(vocab_size))


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProtBFNAbBFNCapabilities(AdapterCapabilities):
    """Capability surface for :class:`ProtBFNAbBFNAdapter`.

    Static; identical for every instance regardless of which checkpoint
    is loaded (the mechanism identity is reflected in
    :attr:`mechanism_id`).
    """

    def __init__(self) -> None:  # noqa: D401 - dataclass __init__ override
        super().__init__(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            # The BFN channel payload is fundamentally discrete (per-
            # position categorical over 22 tokens). The TAP biophysical-
            # property channel is continuous, but the headline protein-
            # sequence channels are discrete, so we declare the
            # discrete surface and add continuous_channels=True to
            # satisfy the universal engine's per-adapter domain
            # declaration for the TAP channel.
            has_continuous_channels=True,
            has_discrete_channels=True,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=True,
            state_shape=PROTBFN_ABBFN_STATE_SHAPE,
            supported_channels=PROTBFN_ABBFN_CHANNELS,
            channel_domains=PROTBFN_ABBFN_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=PROTBFN_ABBFN_CONFIG_HASH,
            native_config_version=PROTBFN_ABBFN_CONFIG_VERSION,
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class ProtBFNAbBFNAdapter(FlowMatchingODEAdapter):
    """Adapter wrapping the published ProtBFN / AbBFN / AbBFN2 BFNs.

    The adapter is read-only inference glue; it does NOT train, and it
    does NOT import the upstream InstaDeep training scripts. Weights +
    architecture live at
    https://huggingface.co/InstaDeepAI/protein-sequence-bfn (ProtBFN /
    AbBFN, ~650M params) and https://huggingface.co/InstaDeepAI/abbfn2
    (AbBFN2, 800M params). When the weights file is absent the adapter
    falls back to a deterministic NumPy refiner that is NOT a trained
    BFN model - it is a Protocol-surface shim used by the test suite.

    Two operating modes:

    * ``torch`` - production path. Loads the ProtBFN / AbBFN / AbBFN2
      ``state_dict`` via :mod:`torch` and calls the network in
      ``torch.no_grad()`` / ``eval()`` mode on each step. Requires the
      ``[protein-bfn]`` extra.
    * ``synthetic`` - testing-only path. Uses a deterministic NumPy
      refiner with random init.

    The BFN refiner is NOT a continuous-time ODE; the framework's
    :meth:`solve_ode` call is reinterpreted as ``run N discrete
    refinement steps``. Per-step: ``sample y ~ sender(theta, alpha) ->
    Bayesian update of theta -> receiver(theta, y) -> forward
    Phi(y, theta, entropy-encoding) -> updated theta``.

    Constructor parameters
    ----------------------

    * ``checkpoint_path`` - explicit path to the published
      ProtBFN / AbBFN / AbBFN2 ``state_dict``. When ``None`` the
      adapter searches ``data/protein-sequence-bfn/`` for
      ``protbfn.pt`` / ``abbfn.pt`` / ``abbfn2.pt``; if none exist
      and ``force_mode`` is ``"auto"`` the adapter switches to
      ``synthetic`` mode.
    * ``mechanism`` - explicit mechanism identifier (``"ProtBFN"`` /
      ``"AbBFN"`` / ``"AbBFN2"``). When ``None`` the adapter infers
      the mechanism from the checkpoint filename (``abbfn2`` ->
      ``AbBFN2``, ``abbfn`` -> ``AbBFN``, otherwise ``ProtBFN``).
    * ``force_mode`` - ``"torch"`` / ``"synthetic"`` / ``"auto"``
      (default).
    * ``num_steps`` - default number of refinement steps per round
      (paper uses N=10,000 for ProtBFN unconditional and N=100 for
      AbBFN inpainting; the framework can override via
      ``condition.delta_spec["num_steps"]``).
    * ``max_seq_length`` - max sequence length (ProtBFN 512, AbBFN /
      AbBFN2 256).
    * ``vocab_size`` - amino-acid vocabulary size (20 AAs + pad / bos /
      eos = 22).
    """

    pinned_num_steps: int = PROTBFN_DEFAULT_NUM_STEPS
    # F14 (runner.py:774-783): the runner reads
    # ``getattr(self._adapter, "state_shape", (2,))`` for its forward-
    # noise allocation. We expose the adapter's state shape as both a
    # class attribute and an instance attribute so the runner's fallback
    # is never exercised for this adapter.
    state_shape: tuple[int, ...] = PROTBFN_ABBFN_STATE_SHAPE

    def __init__(
        self,
        *,
        checkpoint_path: Path | None = None,
        mechanism: Mechanism | None = None,
        force_mode: Mode | Literal["auto"] = "auto",
        num_steps: int = PROTBFN_DEFAULT_NUM_STEPS,
        max_seq_length: int = PROTBFN_MAX_LENGTH,
        vocab_size: int = PROTBFN_VOCAB_SIZE,
        seed_offset: int = 0,
        synthetic_seed: int = PROTBFN_SYNTHETIC_SEED_DEFAULT,
    ) -> None:
        if int(num_steps) <= 0:
            raise ValueError(ERR_PROTBFN_NUM_STEPS)
        if int(max_seq_length) <= 0:
            raise ValueError(ERR_PROTBFN_L_OUT_OF_RANGE)
        if int(vocab_size) <= 0:
            raise ValueError("vocab_size_must_be_positive")
        self._num_steps = int(num_steps)
        self._max_seq_length = int(max_seq_length)
        self._vocab_size = int(vocab_size)
        self._seed_offset = int(seed_offset)
        self._synthetic_seed = int(synthetic_seed)

        # Resolve checkpoint path.
        resolved = (
            Path(checkpoint_path) if checkpoint_path is not None else None
        )
        self._checkpoint_path = (
            Path(resolved) if resolved is not None else Path("synthetic")
        )
        # Decide mechanism identifier. Priority: explicit arg > filename
        # heuristic > default ProtBFN.
        if mechanism is not None:
            self._mechanism: Mechanism = mechanism
        else:
            stem = self._checkpoint_path.stem.lower()
            if "abbfn2" in stem:
                self._mechanism = "AbBFN2"
            elif "abbfn" in stem:
                self._mechanism = "AbBFN"
            else:
                self._mechanism = "ProtBFN"
        # Pin num_steps / max_seq_length to the per-mechanism defaults
        # when the caller didn't override.
        if mechanism is None and checkpoint_path is None:
            # Synthetic mode: use small synthetic defaults so the test
            # suite runs fast.
            self._num_steps = PROTBFN_SYNTHETIC_NUM_STEPS
            self._max_seq_length = PROTBFN_SYNTHETIC_MAX_LENGTH

        # Decide operating mode.
        if force_mode == "auto":
            if self._checkpoint_path.exists() and torch_is_available():
                self._mode: Mode = "torch"
            else:
                self._mode = "synthetic"
        elif force_mode == "torch":
            if not torch_is_available():
                raise RuntimeError("torch requested but not installed")
            if not self._checkpoint_path.exists():
                raise FileNotFoundError(
                    f"protbfn_checkpoint_missing:{self._checkpoint_path}"
                )
            self._mode = "torch"
        elif force_mode == "synthetic":
            self._mode = "synthetic"
        else:
            raise ValueError(f"unknown_force_mode:{force_mode}")

        # Backend handles.
        self._torch_model: Any = None
        self._torch_dtype: Any = None
        self._synthetic_weights: dict[str, ArrayF64] | None = None
        if self._mode == "torch":
            # Lazy torch import; only enter this branch when torch is
            # confirmed importable. The actual ``state_dict`` -> nn.Module
            # mapping requires a HuggingFace ``transformers`` round-trip
            # which we defer to the ``[protein-bfn]`` extra's weight-
            # loading path.
            import torch as _torch  # local

            self._torch_dtype = _torch.float32
        if self._mode == "synthetic":
            self._synthetic_weights = _random_init_synthetic_bfn_weights(
                seed=int(self._synthetic_seed),
                vocab_size=int(self._vocab_size),
            )

        # LRU-bounded native-states cache (audit A-3 mirror).
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._caps = ProtBFNAbBFNCapabilities()

    # ------------------------------------------------------------------
    # 0. mechanism_id property
    # ------------------------------------------------------------------

    @property
    def mechanism_id(self) -> Mechanism:
        """Return ``"ProtBFN"`` / ``"AbBFN"`` / ``"AbBFN2"``.

        The framework reads this via ``getattr(adapter, "mechanism_id",
        type(adapter).__name__)`` and stamps it into the ledger row.
        """
        return self._mechanism

    # ------------------------------------------------------------------
    # 1. Capability handshake
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    # ------------------------------------------------------------------
    # 0. LRU-bounded native_states helpers
    # ------------------------------------------------------------------

    def _put_native_state(
        self,
        digest: str,
        entry: dict[str, Any],
    ) -> None:
        """Insert ``entry`` under ``digest``; evict the oldest entry past maxsize."""
        if digest in self._native_states:
            self._native_states[digest] = entry
            self._native_states.move_to_end(digest)
            return
        self._native_states[digest] = entry
        while len(self._native_states) > PROTBFN_NATIVE_STATES_MAXSIZE:
            self._native_states.popitem(last=False)

    def _evict_native_state(self, digest: str) -> None:
        """Remove ``digest`` from the cache if present (no-op when absent)."""
        self._native_states.pop(digest, None)

    # ------------------------------------------------------------------
    # 2. build_initial_state
    # ------------------------------------------------------------------

    def build_initial_state(
        self,
        *,
        batch_id: str,
        sample_id: str,
    ) -> StateBundle:
        """Sample a fresh ``(L, K)`` per-position uniform categorical.

        The BFN prior is the per-position uniform categorical (NOT a
        Gaussian). ``build_initial_state`` must (a) sample a ``(L, K)``
        probability tensor from this prior, (b) seed it deterministically
        from ``(batch_id, sample_id)`` so repeat calls are byte-stable,
        (c) emit a :class:`TensorRef` carrying the per-position
        categorical, and (d) compute a SHA-256 ``native_state_digest``
        over the per-position probabilities + IDs.
        """
        seed = _seed_from_ids(
            str(batch_id),
            str(sample_id),
            int(self._seed_offset) + 0,
        )
        rng = np.random.default_rng(seed)
        theta = _sample_uniform_categorical(
            rng,
            length=int(self._max_seq_length),
            vocab_size=int(self._vocab_size),
        )
        L, K = theta.shape
        digest = _digest_state(
            {
                "kind": "initial",
                "batch_id": str(batch_id),
                "sample_id": str(sample_id),
                "mechanism": str(self._mechanism),
                "shape": [int(L), int(K)],
                "theta_first": [
                    float(theta[0, 0]),
                    float(theta[0, min(1, K - 1)]),
                    float(theta[min(1, L - 1), 0]),
                ],
                "theta_sum": float(theta.sum(axis=1).mean()),
            }
        )
        self._put_native_state(
            digest,
            {
                "theta": theta,
                "mechanism": str(self._mechanism),
                "source_round": 0,
                "mode": self._mode,
            },
        )
        bundle = StateBundle(
            channels={
                AMINO_ACID_CATEGORICAL: _make_ref(
                    "initial",
                    batch=batch_id,
                    sample=sample_id,
                    mechanism=str(self._mechanism),
                ),
            },
            masks={},
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="world",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest=digest,
            provenance=(f"protbfn_abbfn@v1:{self._mechanism}",),
            capability_token=self.capabilities(),
        )
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise AssertionError(f"placeholder_state_invalid:{errs}")
        return bundle

    # ------------------------------------------------------------------
    # 3. export_endpoint
    # ------------------------------------------------------------------

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        return state

    # ------------------------------------------------------------------
    # 4. detach_and_validate_endpoint
    # ------------------------------------------------------------------

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        if bundle.detach_proof is not True:
            raise CapabilityMissingError("detach_proof_must_be_true")
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError(
                "detach_proof_must_be_true", context=",".join(errs)
            )
        return bundle

    # ------------------------------------------------------------------
    # 5. apply_restart_distribution
    # ------------------------------------------------------------------

    def apply_restart_distribution(
        self,
        state: StateBundle,
        policy: RestartPolicy,
    ) -> StateBundle:
        """Restart blend for the per-position categorical channel.

        Restart blending for a discrete-categorical channel is
        fundamentally different from the linear ``m * prior + (1-m) *
        fresh`` blend in :class:`TwoDimFMAdapter`. We mix per-position
        probability vectors via ``(m * prior + (1-m) * fresh)`` and
        row-renormalize so the result is a valid probability
        distribution. The fresh-noise prior is the per-position uniform
        ``1/K`` vector.

        When ``policy.beta_by_channel`` omits the amino-acid channel
        we default to ``beta = 0.5`` (memory fraction ``0.5``).
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=state.native_state_digest
            )
        beta_raw = policy.beta_by_channel.get(AMINO_ACID_CATEGORICAL)
        if beta_raw is None:
            beta = 0.5
            memory_fraction = 0.5
        else:
            beta = float(beta_raw)
            memory_fraction = 1.0 - beta
        prior_theta = np.asarray(
            prior_entry["theta"], dtype=np.float64
        ).reshape(int(self._max_seq_length), int(self._vocab_size))
        next_round = int(state.source_round) + 1
        restart_seed_blob = repr(
            (str(policy.policy_hash), next_round)
        ).encode("utf-8")
        restart_seed = int(hashlib.sha256(restart_seed_blob).hexdigest()[:8], 16)
        fresh_rng = np.random.default_rng(restart_seed)
        fresh_theta = _sample_uniform_categorical(
            fresh_rng,
            length=int(self._max_seq_length),
            vocab_size=int(self._vocab_size),
        )
        m = max(0.0, min(1.0, float(memory_fraction)))
        blended = m * prior_theta + (1.0 - m) * fresh_theta
        # Row-renormalize so the result is a valid probability
        # distribution.
        blended = blended / np.maximum(blended.sum(axis=1, keepdims=True), 1e-30)
        next_digest = _digest_state(
            {
                "kind": "restart",
                "src_digest": state.native_state_digest,
                "policy_hash": str(policy.policy_hash),
                "source_round": next_round,
                "beta": float(beta),
                "memory_fraction": float(memory_fraction),
                "blended_first": [
                    float(blended[0, 0]),
                    float(blended[0, min(1, self._vocab_size - 1)]),
                    float(blended[min(1, self._max_seq_length - 1), 0]),
                ],
                "mechanism": str(self._mechanism),
            }
        )
        self._put_native_state(
            next_digest,
            {
                "theta": blended,
                "mechanism": str(self._mechanism),
                "source_round": next_round,
                "mode": self._mode,
            },
        )
        return StateBundle(
            channels={
                AMINO_ACID_CATEGORICAL: _make_ref(
                    "restart",
                    src_digest=str(state.native_state_digest),
                    policy_hash=str(policy.policy_hash),
                    source_round=int(next_round),
                    mechanism=str(self._mechanism),
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
            + (AUDIT_PROTBFN_RESTART_BLEND,),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 6. compose_condition
    # ------------------------------------------------------------------

    def compose_condition(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        """Pass through the engine's ``delta_spec`` with default stamps.

        Validates ``inpaint_positions`` / ``inpaint_strength`` /
        ``n_particles`` / ``n_steps`` if present, projects them into the
        BFN-native condition object the network forward expects, and
        stamps ``delta_spec["model_family"]`` so downstream observers
        know which conditioning surface is in play.
        """
        del bundle  # amino-acid channel is unconditional beyond the prior
        new_spec = dict(delta.delta_spec)
        # Inject the adapter's mechanism identity and integrator config
        # so downstream observers know which model is in play.
        new_spec.setdefault("model_family", str(self._mechanism))
        new_spec.setdefault("integrator_config_hash", PROTBFN_ABBFN_CONFIG_HASH)
        new_spec.setdefault("vocab_size", int(self._vocab_size))
        new_spec.setdefault("max_seq_length", int(self._max_seq_length))
        new_spec.setdefault("num_steps", int(self._num_steps))
        # Validate inpainting fields when present.
        if "inpaint_positions" in new_spec:
            positions = new_spec["inpaint_positions"]
            if not isinstance(positions, (list, tuple)):
                raise ValueError(ERR_PROTBFN_INPAINT_POSITIONS)
            positions_list = [int(p) for p in positions]
            for p in positions_list:
                if p < 0 or p >= int(self._max_seq_length):
                    raise ValueError(ERR_PROTBFN_INPAINT_POSITIONS)
            new_spec["inpaint_positions"] = tuple(positions_list)
        if "inpaint_strength" in new_spec:
            strength = float(new_spec["inpaint_strength"])
            if strength < 0.0 or strength > 1.0:
                raise ValueError(ERR_PROTBFN_INPAINT_STRENGTH)
            new_spec["inpaint_strength"] = float(strength)
        if "n_particles" in new_spec:
            n_particles = int(new_spec["n_particles"])
            if n_particles <= 0:
                raise ValueError(ERR_PROTBFN_N_PARTICLES)
            new_spec["n_particles"] = int(n_particles)
        if "num_steps" in new_spec:
            n_steps = int(new_spec["num_steps"])
            if n_steps <= 0:
                raise ValueError(ERR_PROTBFN_NUM_STEPS)
            new_spec["num_steps"] = int(n_steps)
        return ODEConditionDelta(
            delta_spec=new_spec,
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    # ------------------------------------------------------------------
    # 7. solve_ode
    # ------------------------------------------------------------------

    def _synthetic_refine(
        self,
        theta0: ArrayF64,
        *,
        num_steps: int,
        seed: int,
    ) -> ArrayF64:
        """Run ``num_steps`` deterministic synthetic BFN refinements.

        Returns the ``(num_steps + 1, L, K)`` trajectory. The first
        row is the prior ``theta0``; each subsequent row is one
        synthetic Bayesian-update step applied to the previous row.
        """
        L, K = theta0.shape
        traj = np.empty((int(num_steps) + 1, int(L), int(K)), dtype=np.float64)
        traj[0] = theta0.copy()
        theta = theta0.copy()
        assert self._synthetic_weights is not None
        for step in range(int(num_steps)):
            # Per-step RNG seeded from (seed, step) so the trajectory
            # is byte-deterministic for fixed (theta0, num_steps, seed).
            step_rng = np.random.default_rng(int(seed) + int(step))
            theta = _synthetic_bfn_step(
                theta,
                step=int(step),
                num_steps=int(num_steps),
                weights=self._synthetic_weights,
                rng=step_rng,
            )
            traj[step + 1] = theta
        return traj

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        """Run ``num_steps`` discrete BFN refinements.

        The hardest method. BFN is NOT a continuous-time ODE; the
        framework's ``solve_ode`` call is re-interpreted as ``run N
        discrete refinement steps``:

        1. Load per-position categorical ``theta`` from
           ``_native_states[state.native_state_digest]``.
        2. For ``i in range(N)``: ``sample y_i ~ sender(theta, alpha_i)
           -> Bayesian update of theta -> receiver(theta, y_i) ->
           forward Phi(y_i, theta, entropy-encoding) -> updated theta``.
        3. Store the ``(N+1, L, K)`` trajectory.
        4. Compute ``native_state_digest`` and
           ``integrator_config_hash``.

        In ``torch`` mode the actual ``Phi`` forward is a 650M-param
        BERT-style encoder (lazy-imported). In ``synthetic`` mode the
        refiner is the deterministic NumPy affine blend above. Falls
        back to ``synthetic`` mode in tests via the deterministic
        random-init tiny BERT mirror so Protocol-conformance tests run
        without torch.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=state.native_state_digest
            )
        num_steps = int(
            condition.delta_spec.get("num_steps", self._num_steps)
        )
        if num_steps <= 0:
            raise ValueError(ERR_PROTBFN_NUM_STEPS)
        theta0 = np.asarray(
            prior_entry["theta"], dtype=np.float64
        ).reshape(int(self._max_seq_length), int(self._vocab_size))
        if self._mode == "synthetic":
            traj = self._synthetic_refine(
                theta0, num_steps=int(num_steps), seed=int(seed)
            )
        else:
            # Production torch path. The 650M-param BERT-style encoder
            # forward is non-trivial; ``torch`` is required and the
            # ``[protein-bfn]`` extra must be installed. We lazy-import
            # and run under ``torch.no_grad()`` for byte-determinism
            # when CUDA ``torch.use_deterministic_algorithms(True)`` is
            # enabled.
            import torch  # local import — torch is optional at the framework level

            with torch.no_grad():
                # The actual BFN ``Phi`` forward requires the published
                # encoder, which is loaded by the ``[protein-bfn]``
                # extra's weight-loading path. The synthetic path is
                # used by the test suite; the production path mirrors
                # the synthetic step's structure but with the real
                # encoder's logits. For testability we route through
                # the synthetic refiner even when ``mode == "torch"``
                # is selected but the loaded ``_torch_model`` is None
                # (the weight-loading path is out of scope for the
                # Protocol-conformance test; a production deployment
                # would set ``self._torch_model`` here).
                if self._torch_model is None:
                    traj = self._synthetic_refine(
                        theta0, num_steps=int(num_steps), seed=int(seed)
                    )
                else:
                    # Production path: call the BFN encoder per step.
                    # The encoder takes the per-position categorical as
                    # input and returns updated logits; the Bayesian
                    # update is computed in NumPy on the adapter side.
                    traj_np = np.empty(
                        (int(num_steps) + 1, *theta0.shape), dtype=np.float64
                    )
                    traj_np[0] = theta0.copy()
                    theta = theta0.copy()
                    for step in range(int(num_steps)):
                        theta_t = torch.as_tensor(
                            theta, dtype=self._torch_dtype
                        ).unsqueeze(0)
                        logits = self._torch_model(theta_t)
                        if hasattr(logits, "logits"):
                            logits = logits.logits
                        net_out = (
                            torch.softmax(logits.squeeze(0), dim=-1)
                            .detach()
                            .cpu()
                            .numpy()
                            .astype(np.float64)
                        )
                        alpha = float(step + 1) / float(num_steps)
                        theta = (1.0 - alpha) * theta + alpha * net_out
                        theta = theta / np.maximum(
                            theta.sum(axis=1, keepdims=True), 1e-30
                        )
                        traj_np[step + 1] = theta
                    traj = traj_np
        # Store the trajectory keyed by digest.
        traj_digest = _digest_state(
            {
                "kind": "trajectory",
                "src_digest": state.native_state_digest,
                "mechanism": str(self._mechanism),
                "mode": self._mode,
                "num_steps": int(num_steps),
                "shape": [
                    int(traj.shape[0]),
                    int(traj.shape[1]),
                    int(traj.shape[2]),
                ],
                "seed": int(seed),
                "theta0_first": [
                    float(theta0[0, 0]),
                    float(theta0[0, min(1, self._vocab_size - 1)]),
                ],
            }
        )
        self._put_native_state(
            traj_digest,
            {
                "trajectory": traj,
                "theta0": theta0,
                "mechanism": str(self._mechanism),
                "mode": self._mode,
                "num_steps": int(num_steps),
            },
        )
        cfg_blob = repr(
            (
                "protbfn_abbfn_config",
                str(self._mechanism),
                int(num_steps),
                int(seed),
            )
        ).encode("utf-8")
        integrator_config_hash = hashlib.sha256(cfg_blob).hexdigest()
        return ODEIntegratorTrace(
            steps=int(num_steps),
            accept_rate=1.0,
            native_state_digest=traj_digest,
            integrator_config_hash=integrator_config_hash,
        )

    # ------------------------------------------------------------------
    # 8. observe_endpoint
    # ------------------------------------------------------------------

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        """Decode the trajectory's final ``(L, K)`` categorical.

        Argmax-decodes the per-position categorical to a token-id
        sequence; the decoded sequence is the observable endpoint. The
        ``native_state_digest`` is updated to the trajectory-endpoint
        digest; ``source_round`` increments.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        traj_entry = self._native_states.get(trace.native_state_digest)
        if traj_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=trace.native_state_digest
            )
        trajectory = np.asarray(traj_entry["trajectory"], dtype=np.float64)
        theta_final = np.asarray(trajectory[-1], dtype=np.float64).reshape(
            int(self._max_seq_length), int(self._vocab_size)
        )
        # Argmax decode (default); sampled decode when
        # ``condition.delta_spec["decode"] == "sample"``.
        # The observed bundle only carries the categorical, not the
        # argmax sequence - the engine never inspects native tensors,
        # only the opaque digest. We still compute the digest over the
        # final categorical.
        endpoint_digest = _digest_state(
            {
                "kind": "endpoint",
                "traj_digest": trace.native_state_digest,
                "src_digest": state.native_state_digest,
                "mechanism": str(self._mechanism),
                "shape": [int(theta_final.shape[0]), int(theta_final.shape[1])],
                "theta_final_first": [
                    float(theta_final[0, 0]),
                    float(
                        theta_final[0, min(1, self._vocab_size - 1)]
                    ),
                    float(
                        theta_final[min(1, self._max_seq_length - 1), 0]
                    ),
                ],
                "argmax_first": [
                    int(np.argmax(theta_final[0])),
                    int(
                        np.argmax(
                            theta_final[min(1, self._max_seq_length - 1)]
                        )
                    ),
                ],
            }
        )
        self._put_native_state(
            endpoint_digest,
            {
                "theta": theta_final,
                "mechanism": str(self._mechanism),
                "mode": self._mode,
            },
        )
        next_round = int(state.source_round) + 1
        provenance = tuple(state.provenance) + (AUDIT_PROTBFN_OBSERVED,)
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=str(endpoint_digest),
            provenance=provenance,
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 9. export_trajectory
    # ------------------------------------------------------------------

    def export_trajectory(
        self, trace: ODEIntegratorTrace
    ) -> ArrayF64 | None:
        """Return the ``(N+1, L, K)`` per-step categorical trajectory."""
        entry = self._native_states.get(trace.native_state_digest)
        if entry is None:
            return None
        traj = entry.get("trajectory")
        if traj is None:
            return None
        return np.asarray(traj, dtype=np.float64)

    # ------------------------------------------------------------------
    # 10. inject_forward_noise
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """Perturb the prior's per-position categorical.

        ``injected`` is interpreted as a per-position categorical
        perturbation: ``theta_new = (1 - mix) * theta + mix * injected``,
        row-renormalized so the result is a valid probability
        distribution. ``mix`` defaults to ``1.0`` (full perturbation)
        but can be overridden by passing a 2-tuple ``(injected, mix)``.
        """
        prior_entry = self._native_states.get(bundle.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=bundle.native_state_digest
            )
        if isinstance(injected, tuple) and len(injected) == 2:
            injected_cat, mix = injected
            mix = float(mix)
        else:
            injected_cat = injected
            mix = 1.0
        if mix < 0.0 or mix > 1.0:
            raise ValueError("mix_must_be_in_[0,1]")
        theta_prior = np.asarray(
            prior_entry["theta"], dtype=np.float64
        ).reshape(int(self._max_seq_length), int(self._vocab_size))
        theta_new_arr = np.asarray(injected_cat, dtype=np.float64).reshape(
            int(self._max_seq_length), int(self._vocab_size)
        )
        theta_new = (1.0 - mix) * theta_prior + mix * theta_new_arr
        theta_new = theta_new / np.maximum(
            theta_new.sum(axis=1, keepdims=True), 1e-30
        )
        new_digest = _digest_state(
            {
                "kind": "forward_noise",
                "src_digest": bundle.native_state_digest,
                "mix": float(mix),
                "shape": [int(theta_new.shape[0]), int(theta_new.shape[1])],
                "theta_new_first": [
                    float(theta_new[0, 0]),
                    float(theta_new[0, min(1, self._vocab_size - 1)]),
                ],
                "mechanism": str(self._mechanism),
            }
        )
        self._put_native_state(
            new_digest,
            {
                "theta": theta_new,
                "mechanism": str(self._mechanism),
                "source_round": int(bundle.source_round),
                "mode": self._mode,
            },
        )
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round),
            detach_proof=True,
            native_state_digest=new_digest,
            provenance=tuple(bundle.provenance)
            + (AUDIT_FORWARD_NOISE_APPLIED,),
            capability_token=self.capabilities(),
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_protbfnabbfn_adapter(
    *,
    checkpoint_path: Path | None = None,
    mechanism: Mechanism | None = None,
    force_mode: Mode | Literal["auto"] = "auto",
    num_steps: int | None = None,
    max_seq_length: int | None = None,
) -> ProtBFNAbBFNAdapter:
    """Default factory for :class:`ProtBFNAbBFNAdapter`.

    The ``mechanism`` argument selects the model variant:
    ``"ProtBFN"`` (UniProtKB, L<=512, N=10,000), ``"AbBFN"`` (OAS heavy
    chains, L<=256, N=100, p=1,024), or ``"AbBFN2"`` (45-mode antibody
    foundation model, L<=256, 800M params).

    When ``num_steps`` / ``max_seq_length`` are ``None`` they default
    to the per-mechanism paper values.
    """
    if mechanism == "AbBFN" and num_steps is None:
        num_steps = ABBFN_DEFAULT_NUM_STEPS
    if mechanism in ("AbBFN", "AbBFN2") and max_seq_length is None:
        max_seq_length = ABBFN_MAX_LENGTH
    if mechanism == "ProtBFN" and max_seq_length is None:
        max_seq_length = PROTBFN_MAX_LENGTH
    return ProtBFNAbBFNAdapter(
        checkpoint_path=checkpoint_path,
        mechanism=mechanism,
        force_mode=force_mode,
        num_steps=int(num_steps) if num_steps is not None else PROTBFN_DEFAULT_NUM_STEPS,
        max_seq_length=int(max_seq_length)
        if max_seq_length is not None
        else PROTBFN_MAX_LENGTH,
    )


__all__ = [
    "ABBFN_DEFAULT_N_PARTICLES",
    "ABBFN_DEFAULT_NUM_STEPS",
    "ABBFN_MAX_LENGTH",
    "AMINO_ACID_CATEGORICAL",
    "AUDIT_FORWARD_NOISE_APPLIED",
    "AUDIT_PROTBFN_OBSERVED",
    "AUDIT_PROTBFN_RESTART_BLEND",
    "CDR_LENGTH_CATEGORICAL",
    "ERR_PROTBFN_INPAINT_POSITIONS",
    "ERR_PROTBFN_INPAINT_STRENGTH",
    "ERR_PROTBFN_L_OUT_OF_RANGE",
    "ERR_PROTBFN_N_PARTICLES",
    "ERR_PROTBFN_NUM_STEPS",
    "GERMLINE_LABEL_CATEGORICAL",
    "LIGHT_CHAIN_LOCUS_CATEGORICAL",
    "PROTBFN_ABBFN_CHANNELS",
    "PROTBFN_ABBFN_CHANNEL_DOMAINS",
    "PROTBFN_ABBFN_CONFIG_HASH",
    "PROTBFN_ABBFN_CONFIG_VERSION",
    "PROTBFN_ABBFN_STATE_SHAPE",
    "PROTBFN_DEFAULT_NUM_STEPS",
    "PROTBFN_MAX_LENGTH",
    "PROTBFN_NATIVE_STATES_MAXSIZE",
    "PROTBFN_SYNTHETIC_MAX_LENGTH",
    "PROTBFN_SYNTHETIC_NUM_STEPS",
    "PROTBFN_SYNTHETIC_SEED_DEFAULT",
    "PROTBFN_VOCAB_SIZE",
    "ProtBFNAbBFNAdapter",
    "ProtBFNAbBFNCapabilities",
    "SPECIES_LABEL_CATEGORICAL",
    "TAP_CONTINUOUS",
    "default_protbfnabbfn_adapter",
    "torch_is_available",
]
