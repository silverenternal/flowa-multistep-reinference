"""Pure-PyTorch mirror of ``data/protbfn_abbfn/repo/loss.py``.

This module re-implements the upstream BFN loss functions in pure
PyTorch / NumPy so the framework's
:class:`adaptive_reflow.adapters.protbfn_abbfn_adapter.ProtBFNAbBFNAdapter`
can compute paper metrics (perplexity, continuous-time loss,
reconstruction loss) without forcing a JAX install.

These mirrors are intentionally thin and faithful to the upstream
algorithms; they are NOT pure-torch re-trainings. They use the same
``K=32`` and ``beta_1=2.0`` constants as the upstream, and they
consume the same encoder logits interface.

Public surface
--------------

* :func:`sample_sender_distribution` - mirror of
  ``loss.sample_sender_distribution``.
* :func:`compute_continuous_time_loss` - mirror of
  ``loss.compute_continuous_time_loss``.
* :func:`compute_reconstruction_loss` - mirror of
  ``loss.compute_reconstruction_loss``.
* :func:`approximate_loss` - mirror of ``loss.approximate_loss`` with
  Monte-Carlo ELBO over ``num_approximations`` time points.
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np
import torch
from numpy.typing import NDArray


# ---------------------------------------------------------------------------
# Constants — mirror data/protbfn_abbfn/repo/loss.py
# ---------------------------------------------------------------------------

#: Tokenizer vocabulary size.
K: int = 32

#: Final BFN precision (loss.py: ``beta_1 = 2.0``).
BETA_1: float = 2.0


# ---------------------------------------------------------------------------
# Mirrors
# ---------------------------------------------------------------------------


def sample_sender_distribution(
    x: NDArray[np.int64],
    t: float,
    beta_1: float,
    rng: np.random.Generator,
) -> NDArray[np.float64]:
    """Sample from the sender distribution.

    Mirror of ``loss.sample_sender_distribution``. ``x`` has shape
    ``(N,)`` (per-position token ids), ``t`` is the BFN time in
    ``[0, 1]``, ``beta_1`` is the final precision. Returns a
    ``(N, K)`` logit-space tensor.
    """
    x_one_hot = np.eye(int(K), dtype=np.float64)[np.asarray(x, dtype=np.int64)]
    beta = float(beta_1) * float(t) ** 2.0
    mu = beta * (float(K) * x_one_hot - 1.0)
    sigma = math.sqrt(beta * float(K))
    noise = rng.normal(size=mu.shape).astype(np.float64)
    return np.asarray(mu + sigma * noise, dtype=np.float64)


def compute_continuous_time_loss(
    x: NDArray[np.int64],
    phi_logits: NDArray[np.float64],
    t: float,
    beta_1: float,
) -> float:
    """Mirror of ``loss.compute_continuous_time_loss``."""
    x_one_hot = np.eye(int(K), dtype=np.float64)[np.asarray(x, dtype=np.int64)]
    alpha = 2.0 * float(beta_1) * float(t)
    # Stable softmax on logits to avoid overflow.
    z = phi_logits - np.max(phi_logits, axis=-1, keepdims=True)
    exp_z = np.exp(z)
    phi = exp_z / np.sum(exp_z, axis=-1, keepdims=True)
    loss_per_pos = 0.5 * float(K) * alpha * (x_one_hot - phi) ** 2
    return float(np.sum(loss_per_pos))


def compute_reconstruction_loss(
    x: NDArray[np.int64],
    phi_logits: NDArray[np.float64],
) -> float:
    """Mirror of ``loss.compute_reconstruction_loss``."""
    x_one_hot = np.eye(int(K), dtype=np.float64)[np.asarray(x, dtype=np.int64)]
    # Stable log-softmax.
    z = phi_logits - np.max(phi_logits, axis=-1, keepdims=True)
    log_z = z - np.log(np.sum(np.exp(z), axis=-1, keepdims=True))
    loss_per_pos = -np.sum(x_one_hot * log_z, axis=-1)
    return float(np.sum(loss_per_pos))


def approximate_loss(
    x: NDArray[np.int64],
    transformer_fn: Callable[[NDArray[np.float64]], NDArray[np.float64]],
    *,
    beta_1: float = BETA_1,
    num_approximations: int = 1000,
    seed: int = 0,
) -> float:
    """Mirror of ``loss.approximate_loss``.

    Monte-Carlo estimate of the continuous-time ELBO at ``num_approximations``
    uniformly-sampled ``t`` values in ``[0, 1]`` plus the ``t = 1``
    reconstruction term. ``transformer_fn(theta)`` returns per-position
    logits of shape ``(N, K)``.
    """
    rng = np.random.default_rng(int(seed))
    continuous_time_loss = 0.0
    for _ in range(int(num_approximations)):
        t = float(rng.uniform())
        sender = sample_sender_distribution(x, t, beta_1, rng)
        theta = _softmax(sender, axis=-1)
        phi_logits = np.asarray(transformer_fn(theta), dtype=np.float64)
        continuous_time_loss += compute_continuous_time_loss(
            x, phi_logits, t, beta_1
        ) / float(num_approximations)
    # Reconstruction loss at t = 1 (small, sanity floor).
    sender = sample_sender_distribution(x, 1.0, beta_1, rng)
    theta = _softmax(sender, axis=-1)
    phi_logits = np.asarray(transformer_fn(theta), dtype=np.float64)
    reconstruction_loss = compute_reconstruction_loss(x, phi_logits)
    return float(continuous_time_loss + reconstruction_loss)


def _softmax(z: NDArray[np.float64], axis: int = -1) -> NDArray[np.float64]:
    z = z - np.max(z, axis=axis, keepdims=True)
    exp_z = np.exp(z)
    return exp_z / np.sum(exp_z, axis=axis, keepdims=True)


# ---------------------------------------------------------------------------
# Convenience: torch forward wrapper
# ---------------------------------------------------------------------------


def transformer_to_numpy_fn(
    torch_model: "torch.nn.Module",
    *,
    device: "torch.device | None" = None,
    dtype: "torch.dtype | None" = None,
) -> Callable[[NDArray[np.float64]], NDArray[np.float64]]:
    """Wrap a :class:`ProtBFNTransformer` as a NumPy forward fn.

    ``torch_model`` must take ``theta`` of shape ``(L, K)`` and return
    logits of shape ``(L, K)``. Returns a NumPy-input / NumPy-output
    callable suitable for :func:`approximate_loss`.
    """
    dev = device or next(torch_model.parameters()).device
    dt = dtype or next(torch_model.parameters()).dtype

    def _fn(theta: NDArray[np.float64]) -> NDArray[np.float64]:
        with torch.no_grad():
            theta_t = torch.as_tensor(
                np.asarray(theta, dtype=np.float64),
                dtype=dt,
                device=dev,
            )
            logits = torch_model(theta_t)
            if hasattr(logits, "logits"):
                logits = logits.logits
            return logits.detach().cpu().numpy().astype(np.float64)

    return _fn


__all__ = [
    "BETA_1",
    "K",
    "approximate_loss",
    "compute_continuous_time_loss",
    "compute_reconstruction_loss",
    "sample_sender_distribution",
    "transformer_to_numpy_fn",
]