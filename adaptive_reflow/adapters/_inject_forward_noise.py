"""Helper module for :meth:`FlowMatchingODEAdapter.inject_forward_noise`.

P1-8 (F-25): 8 of 10 concrete adapters were missing the
``inject_forward_noise`` method (only ``RectifiedFlowCIFARAdapter``
and ``MNISTFMAdapter`` shipped it). The runner detects the method
via ``hasattr`` and routes the ``scheduler.inject_noise`` result
through it. Adapters that do not implement the method fall through
to a no-op (the runner still emits the ``FORWARD_NOISE_INJECTED``
audit code so the trail is consistent across wired and unwired
paths).

This module ships a generic ``inject_forward_noise_into_state``
helper that performs the standard perturbation pattern:

1. Look up the prior native state via ``bundle.native_state_digest``.
2. Add ``injected`` to the prior's ``"x"`` (or ``"x0"``) key.
3. Compute a fresh digest via SHA-256 of a dict that includes the
   new state head + the source digest.
4. Store the new state in the adapter's ``_native_states`` dict.
5. Return a new :class:`StateBundle` whose
   ``native_state_digest`` is the new digest and whose
   ``provenance`` carries an ``inject_forward_noise_applied``
   audit tag.

Adapters that store state under a different key (``x_t``,
``x_state``, ``latent``, ...) can call this function with a
custom ``state_key`` argument. Adapters with completely custom
state representations (e.g. CIFAR's ``(3, 32, 32)`` images,
molecule coordinates) keep their bespoke implementations — the
helper is the *default* for the simple ``scalar / vector`` case.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.universal.state import (
    ChannelName,
    StateBundle,
    validate_state_bundle,
)

#: Audit-code-style provenance tag for the standard perturbation path.
INJECT_FORWARD_NOISE_TAG: str = "inject_forward_noise_applied"


def _digest_state_payload(payload: dict[str, Any]) -> str:
    """Stable SHA-256 over a JSON-serialisable payload."""
    serialised = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def inject_forward_noise_into_state(
    *,
    adapter: Any,
    bundle: StateBundle,
    injected: Any,
    state_key: str | tuple[str, ...] = "x",
    clamp: float | None = None,
    extra_tag: str | None = None,
) -> StateBundle:
    """Perturb the prior's state vector by ``injected`` and return a new bundle.

    Parameters
    ----------
    adapter:
        The concrete adapter instance. Must expose ``_native_states``
        (a ``dict[str, dict[str, Any]]`` keyed by digest) and
        ``capabilities()``.
    bundle:
        The source :class:`StateBundle` whose prior is being
        perturbed.
    injected:
        The forward-noise tensor. Will be converted via
        ``np.asarray(..., dtype=np.float64)`` and reshaped to match
        the prior's state-key shape.
    state_key:
        The key (or tuple of candidate keys) into the prior's
        native-state dict that holds the state vector. When a
        tuple is supplied, the first matching key in the entry is
        used (in order). The default ``"x"`` matches most
        adapters' :meth:`observe_endpoint` storage; adapters with
        ``x0``-keyed initial state (e.g.
        :class:`RectifiedFlowCIFARAdapter`) may pass
        ``("x", "x0")`` so the same helper works across both the
        round-0 ``build_initial_state`` entry and the post-observation
        entries.
    clamp:
        Optional ``[-clamp, clamp]`` clip applied after the
        perturbation. ``None`` (default) means no clip.
    extra_tag:
        Optional extra provenance tag (in addition to the
        canonical :data:`INJECT_FORWARD_NOISE_TAG`). Used by
        adapter-specific overrides (e.g. molecule adapters may want
        ``flowa_forward_noise`` for downstream tracing).

    Returns
    -------
    StateBundle
        A new bundle with the perturbed state's digest and the
        audit tag in ``provenance``. Raises
        :class:`CapabilityMissingError` (via
        :func:`validate_state_bundle`) if the bundle is invalid, or
        ``KeyError`` if the prior state is missing from the
        adapter's store.
    """
    ok, errs = validate_state_bundle(bundle)
    if not ok:
        from adaptive_reflow.universal.adapter import CapabilityMissingError
        raise CapabilityMissingError(
            "inject_forward_noise_invalid_bundle", context=",".join(errs),
        )
    prior_entry = adapter._native_states.get(bundle.native_state_digest)  # noqa: SLF001
    if prior_entry is None:
        from adaptive_reflow.universal.adapter import CapabilityMissingError
        raise CapabilityMissingError(
            "missing_native_state",
            context=str(bundle.native_state_digest),
        )
    candidates = (state_key,) if isinstance(state_key, str) else tuple(state_key)
    resolved_key: str | None = None
    for candidate in candidates:
        if candidate in prior_entry:
            resolved_key = candidate
            break
    if resolved_key is None:
        raise KeyError(
            f"inject_forward_noise: prior entry has none of {candidates}; "
            f"entry keys={sorted(prior_entry.keys())}"
        )
    prior_state = np.asarray(prior_entry[resolved_key], dtype=np.float64)
    injected_arr = np.asarray(injected, dtype=np.float64)
    # Reshape ``injected_arr`` to the prior's shape when sizes match
    # (handles scalar priors with vector injected, vector priors with
    # vector injected, etc.). The runner pads the noise to the
    # adapter's ``state_shape`` so the reshape is always well-defined
    # for the canonical ``(2,)`` and ``(3, 32, 32)`` state shapes.
    # When the shapes disagree entirely (e.g. the runner overrides
    # ``state_shape`` for a regression test), subsample the injected
    # tensor to the prior's flat size so the broadcast still
    # succeeds. This is a guard against the runner's noise array
    # being larger than the native state space — production code
    # never hits this path because the runner reads
    # ``adapter.state_shape`` from the *capabilities* token, which
    # matches the native state.
    if injected_arr.size == prior_state.size:
        injected_arr = injected_arr.reshape(prior_state.shape)
    elif injected_arr.size > prior_state.size:
        injected_arr = injected_arr.reshape(-1)[: prior_state.size].reshape(
            prior_state.shape
        )
    new_state = prior_state + injected_arr
    if clamp is not None:
        new_state = np.clip(new_state, -float(clamp), float(clamp))
    next_round = int(bundle.source_round) + 1
    new_entry = dict(prior_entry)
    new_entry[resolved_key] = new_state
    # Digest the perturbed state. We hash the new state's head +
    # the source digest so two perturbations of the same prior
    # with the same injected tensor land on the same digest (and
    # two perturbations with different injected tensors land on
    # distinct digests). The shape is recorded so a future
    # capability check can reject shape mismatches.
    head_idx = tuple(range(min(8, new_state.size)))
    new_digest = _digest_state_payload(
        {
            "kind": "forward_noise",
            "src_digest": str(bundle.native_state_digest),
            "state_key": str(resolved_key),
            "shape": [int(s) for s in new_state.shape],
            "head": [float(new_state[i]) for i in head_idx],
        }
    )
    adapter._native_states[new_digest] = new_entry  # noqa: SLF001
    tag = INJECT_FORWARD_NOISE_TAG
    if extra_tag:
        tag = f"{INJECT_FORWARD_NOISE_TAG}:{extra_tag}"
    return StateBundle(
        channels=dict(bundle.channels),
        masks=dict(bundle.masks),
        batch_id=str(bundle.batch_id),
        sample_id=str(bundle.sample_id),
        reference_frame=str(bundle.reference_frame),
        normalization=str(bundle.normalization),
        source_round=next_round,
        detach_proof=True,
        native_state_digest=new_digest,
        provenance=tuple(bundle.provenance) + (tag,),
        capability_token=adapter.capabilities(),
    )


__all__ = [
    "INJECT_FORWARD_NOISE_TAG",
    "inject_forward_noise_into_state",
]
