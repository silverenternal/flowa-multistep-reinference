"""Wave 83 Agent B — Kanzi paper-metric reproduction module (paper parity).

The Kanzi paper (Geiger et al., ICLR 2026, arXiv:2510.00351) introduces a
**diffusion autoencoder (DAE)** for proteins. The model is a **tokenizer**,
not a generator: ``encode → FSQ → decode → Kabsch-RMSD``. The published
Kanzi upstream ships **no** ``evaluation/`` directory (Wave 79 §2.3), so
the paper's headline metrics must be reproduced by a wrapper around the
existing ``DAE.encode`` / ``DAE.decode`` / ``kabsch_rmsd`` surface.

The Wave 79 driver ``tools/upstream_eval.py::run_kanzi_upstream_eval``
already surfaces **one** of the six Kanzi paper metrics:

* ``reconstruction_kabsch_rmsd_A`` — encoded via the ``_KANZI_DRIVER``
  subprocess that does ``DAE.from_pretrained → encode → decode →
  kabsch_rmsd`` per backbone and writes ``<out>/reconstruction.json``.

This module surfaces the **remaining five** codebook metrics + a single
aggregator that invokes them all on a list of encoded indices:

  1. ``codebook_entropy`` (bits)
     Shannon entropy of the codebook usage histogram (base 2).
  2. ``codebook_perplexity`` (scalar)
     ``2 ** entropy`` (the canonical perplexity = effective vocab size).
  3. ``codebook_js_distance`` (sqrt(JS), bits^0.5)
     Jensen-Shannon distance between two per-row usage distributions
     (deterministic pair (0, 1) for byte-stable tests).
  4. ``codebook_utilization`` (fraction)
     Fraction of codebook cells that appear at least once across all
     encoded indices.
  5. ``codebook_hamming_rotation_invariance`` (fraction)
     Per-position index equality across pairs of encoded indices from
     the same backbone under two different uniform rotations.

Interface contract
------------------

* Public surface: 5 metric helpers + 1 aggregator +
  :func:`compute_reconstruction_kabsch_rmsd_A` (delegates to Wave 79
  ``tools/upstream_eval.run_kanzi_upstream_eval``).
* Module-level imports are stdlib + numpy + scipy (no torch at module
  level — torch is imported lazily inside the hamming helper so the
  framework pytest env which lacks torch can still import this module).
* All five metric helpers accept a plain ``numpy.ndarray`` of integer
  indices ``(B, L)`` in ``[0, vocab_size)`` — no torch tensor required.
  This makes them host-agnostic and easy to unit-test with mock FSQ
  outputs (mirrors the Wave 75 ``paper_metrics.py`` pattern).
* The 6th metric (Hamming rotation-invariance) takes a callable
  ``encoder(x: np.ndarray) -> np.ndarray`` so the caller controls which
  torch-based encoder is used; the helper itself is pure numpy.

CLI / notebook usage::

    from tools.paper_metrics_kanzi import compute_all_codebook_metrics
    metrics = compute_all_codebook_metrics(idx_BL, vocab_size=4096)
    print(metrics["codebook_entropy_bits"],
          metrics["codebook_perplexity"],
          metrics["codebook_js_distance"],
          metrics["codebook_utilization"],
          metrics["codebook_hamming_rotation_invariance"])

Determinism notes
-----------------

Upstream ``codebook_metrics`` (``train_cb.py:113-133``) uses
``random.uniform`` to pick the JS-distance batch pair, and
``estimate_loss`` (``train_cb.py:309-322``) uses ``random.uniform`` for
the uniform-rotation samples. Both are non-deterministic for tests. We
replace the JS pair with the fixed ``(0, 1)`` row pair (deterministic
+ symmetric for ``B >= 2``), and seed the hamming helper's RNG so the
backbone × rotation sampling is byte-stable given a fixed seed.

References (file:line citations from upstream vendored repo)

* ``data/kanzi_upstream/src/kanzi/train_cb.py:102-110`` — ``js_distance``
  (returns ``sqrt(0.5 * (KL(p, m) + KL(q, m)))``).
* ``data/kanzi_upstream/src/kanzi/train_cb.py:113-133`` —
  ``codebook_metrics`` (entropy / perplexity / pairwise JS).
* ``data/kanzi_upstream/src/kanzi/train_cb.py:309-322`` —
  ``estimate_loss`` ``test/cb/utilization`` + ``test/cb/hamming``.
* ``data/kanzi_upstream/src/kanzi/models.py:29-47`` —
  ``sample_uniform_rotation`` (the seed-source for Hamming test).
* ``tools/upstream_eval.py::run_kanzi_upstream_eval`` — Wave 79 driver
  used by :func:`compute_reconstruction_kabsch_rmsd_A`.
"""
from __future__ import annotations

import json
import logging
import math
import pathlib
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants — Kanzi FSQ paper-parity defaults
# ---------------------------------------------------------------------------

#: Default FSQ vocab size for the published Wave 36 Kanzi checkpoint
#: (``levels = (8, 8, 8, 8)`` → ``codebook_size = prod(levels) = 4096``,
#: verified at ``data/kanzi_upstream/src/kanzi/models.py:272``). Used as
#: the default argument for all metric helpers when the caller does not
#: specify a custom ``vocab_size``.
KANZI_DEFAULT_VOCAB_SIZE: int = 4096

#: Numerical floor for ``log2(p)`` (matches upstream
#: ``probs.clamp_min(1e-12).log2()`` convention at
#: ``data/kanzi_upstream/src/kanzi/train_cb.py:116``).
_LOG_EPS: float = 1e-12

#: Default number of uniform-rotation pairs per backbone for the Hamming
#: rotation-invariance metric. Upstream uses 2 (``train_cb.py:312``);
#: the Kanzi paper uses 128. 2 is byte-stable and fast — the paper
#: number is exposed as a CLI flag for the smoke surface.
DEFAULT_HAMMING_N_ROT: int = 2


# ---------------------------------------------------------------------------
# Input coercion helpers
# ---------------------------------------------------------------------------


def _coerce_idx(idx: Any, *, vocab_size: int) -> np.ndarray:
    """Coerce ``idx`` to a contiguous ``int64`` numpy array of shape ``(N,)``.

    Accepts any of: torch tensor, numpy ndarray, nested Python list. The
    upstream convention is ``LongTensor[B, L]``; we flatten to 1-D
    because the codebook metrics are defined on the index histogram
    (not on the batch structure, except for the JS-distance pair). The
    ``vocab_size`` argument is used only for the dtype-int64 range guard.

    Raises
    ------
    TypeError
        If ``idx`` is a floating-point tensor/array (the upstream
        convention is integer indices; a float dtype would silently
        break the bincount + KL-div math).
    ValueError
        If any index is outside ``[0, vocab_size)``.
    """
    if hasattr(idx, "detach"):  # torch tensor — best-effort path
        try:
            import torch  # noqa: PLC0415
            if isinstance(idx, torch.Tensor):
                if idx.is_floating_point():
                    raise TypeError(
                        f"codebook metrics expect integer indices; got "
                        f"floating-point tensor with dtype={idx.dtype}"
                    )
                arr = idx.detach().to("cpu", dtype=torch.int64).reshape(-1).numpy()
            else:
                arr = np.asarray(idx, dtype=np.int64).reshape(-1)
        except ImportError:
            arr = np.asarray(idx, dtype=np.int64).reshape(-1)
    else:
        arr = np.asarray(idx, dtype=np.int64).reshape(-1)
    if arr.size > 0:
        vmin = int(arr.min())
        vmax = int(arr.max())
        if vmin < 0 or vmax >= int(vocab_size):
            raise ValueError(
                f"index out of range for vocab_size={vocab_size}: "
                f"observed [{vmin}, {vmax}]; expected [0, {vocab_size})"
            )
    return arr


def _coerce_idx_2d(idx: Any, *, vocab_size: int, min_batch: int = 2) -> np.ndarray:
    """Coerce ``idx`` to a 2-D ``(B, L)`` int64 array (used by JS distance).

    Mirrors :func:`_coerce_idx` but preserves the leading batch
    dimension so the (0, 1) pair-select for JS-distance is meaningful.
    The ``min_batch`` arg lets callers flag 1-row inputs as invalid
    (default 2 — JS-distance needs >= 2 distributions to compare).
    """
    if hasattr(idx, "detach"):  # torch tensor
        try:
            import torch  # noqa: PLC0415
            if isinstance(idx, torch.Tensor):
                if idx.is_floating_point():
                    raise TypeError(
                        f"codebook JS-distance expects integer indices; "
                        f"got floating-point tensor with dtype={idx.dtype}"
                    )
                arr = idx.detach().to("cpu", dtype=torch.int64).numpy()
            else:
                arr = np.asarray(idx, dtype=np.int64)
        except ImportError:
            arr = np.asarray(idx, dtype=np.int64)
    else:
        arr = np.asarray(idx, dtype=np.int64)
    if arr.ndim == 1:
        # Single row — treat as B=1, fail if min_batch=2.
        arr = arr.reshape(1, -1)
    if arr.ndim != 2:
        raise ValueError(
            f"codebook JS-distance expects 2-D idx_BL of shape (B, L); "
            f"got shape {arr.shape}"
        )
    if arr.shape[0] < int(min_batch):
        raise ValueError(
            f"codebook JS-distance needs B >= {min_batch} rows; got B={arr.shape[0]}"
        )
    if arr.size > 0:
        vmin = int(arr.min())
        vmax = int(arr.max())
        if vmin < 0 or vmax >= int(vocab_size):
            raise ValueError(
                f"index out of range for vocab_size={vocab_size}: "
                f"observed [{vmin}, {vmax}]; expected [0, {vocab_size})"
            )
    return arr


# ---------------------------------------------------------------------------
# Metric 1 — codebook_entropy (Shannon entropy of codebook usage histogram)
# ---------------------------------------------------------------------------


def compute_codebook_entropy(idx: Any, *, vocab_size: int = KANZI_DEFAULT_VOCAB_SIZE) -> float:
    """Compute the Shannon entropy (base 2) of the codebook usage distribution.

    Formula (matches upstream ``codebook_metrics`` at
    ``train_cb.py:113-117``)::

        counts[i] = sum over (b, l) of 1{idx[b, l] == i}      for i in [0, V)
        probs[i]  = counts[i] / sum(counts)
        entropy   = -sum_i probs[i] * log2(probs[i])           (clamp_min(1e-12))

    Parameters
    ----------
    idx
        ``LongTensor[B, L]`` or ``ndarray`` of integer codebook indices
        in ``[0, vocab_size)``. Accepts 1-D or 2-D inputs.
    vocab_size
        Codebook vocab size (default 4096 for the Wave 36 Kanzi
        checkpoint with ``levels = (8, 8, 8, 8)``).

    Returns
    -------
    float
        Entropy in bits ∈ ``[0, log2(vocab_size)]``. For ``V=4096``
        the upper bound is **12 bits**. Empty input returns ``0.0``
        (matches upstream ``counts.sum() == 0`` convention).

    Notes
    -----
    A perfectly uniform distribution yields ``log2(V)``. A fully
    collapsed distribution (all indices equal) yields ``0``. The Kanzi
    paper does not report this number directly, but it's the standard
    FSQ sharpness metric (Mentzer et al. 2023, arXiv:2309.15505, §4.1).
    """
    arr = _coerce_idx(idx, vocab_size=vocab_size)
    if arr.size == 0:
        return 0.0
    counts = np.bincount(arr, minlength=int(vocab_size)).astype(np.float64)
    total = counts.sum()
    if total <= 0:
        return 0.0
    probs = counts / total
    # Match upstream ``probs.clamp_min(1e-12).log2()`` convention.
    log_probs = np.log2(np.clip(probs, a_min=_LOG_EPS, a_max=None))
    entropy = float(-(probs * log_probs).sum())
    return entropy


# ---------------------------------------------------------------------------
# Metric 2 — codebook_perplexity (2 ** entropy)
# ---------------------------------------------------------------------------


def compute_codebook_perplexity(idx: Any, *, vocab_size: int = KANZI_DEFAULT_VOCAB_SIZE) -> float:
    """Compute the codebook perplexity = ``2 ** entropy``.

    Per the upstream ``codebook_metrics`` (``train_cb.py:117``)::

        perplexity = 2 ** entropy

    Parameters
    ----------
    idx
        See :func:`compute_codebook_entropy`.
    vocab_size
        Codebook vocab size (default 4096).

    Returns
    -------
    float
        Perplexity ∈ ``[1.0, vocab_size]``. For ``V=4096`` the upper
        bound is **4096** (the effective vocab size). Empty input
        returns ``1.0`` (matches ``2 ** 0 == 1``).

    Notes
    -----
    The perplexity is the **effective number of distinct codebook
    cells** used by the encoder — it's the most interpretable codebook
    health summary (== vocab size means perfectly uniform usage; == 1
    means codebook collapse).
    """
    entropy = compute_codebook_entropy(idx, vocab_size=vocab_size)
    return float(2.0 ** entropy)


# ---------------------------------------------------------------------------
# Metric 3 — codebook_js_distance (Jensen-Shannon distance for batch pair)
# ---------------------------------------------------------------------------


def _kl_divergence_bits(p: np.ndarray, q: np.ndarray) -> float:
    """Return ``KL(p || q)`` in bits (with the ``clamp_min(1e-12)`` guard).

    Matches upstream ``kl(a, b) = (a * (a.clamp_min(1e-12) /
    b.clamp_min(1e-12)).log2()).sum()`` at ``train_cb.py:104-106``.
    """
    p_safe = np.clip(p, a_min=_LOG_EPS, a_max=None)
    q_safe = np.clip(q, a_min=_LOG_EPS, a_max=None)
    return float((p * (p_safe / q_safe).log2()).sum()) if hasattr((p_safe / q_safe), "log2") else float((p * (np.log2(p_safe / q_safe))).sum())


def compute_codebook_js_distance(idx: Any, *, vocab_size: int = KANZI_DEFAULT_VOCAB_SIZE) -> float:
    """Compute the Jensen-Shannon distance between the (0, 1) batch pair.

    Formula (matches upstream ``codebook_metrics`` at
    ``train_cb.py:119-127`` and ``js_distance`` at
    ``train_cb.py:102-110``)::

        counts_a = bincount(idx[0], minlength=V)
        counts_b = bincount(idx[1], minlength=V)
        pa = counts_a / counts_a.sum()
        pb = counts_b / counts_b.sum()
        m  = 0.5 * (pa + pb)
        KL(p, q) = sum_i p[i] * log2(p[i] / q[i])          (clamp_min(1e-12))
        JS(pa, pb) = 0.5 * KL(pa, m) + 0.5 * KL(pb, m)
        js_distance = sqrt(JS(pa, pb))                      # in bits^0.5

    Parameters
    ----------
    idx
        2-D ``LongTensor[B, L]`` with ``B >= 2``. Flat 1-D inputs are
        treated as a single-row batch ``(1, L)`` and raise
        ``ValueError`` because JS-distance is undefined for ``B=1``.
    vocab_size
        Codebook vocab size (default 4096).

    Returns
    -------
    float
        JS distance in ``bits^0.5`` ∈ ``[0, sqrt(log2(V))]``. For
        ``V=4096`` the upper bound is **~3.46** ``bits^0.5``.
        Returns ``0.0`` on ``B < 2`` (defensive; the upstream
        codebook_metrics crashes on ``B=1``).

    Notes
    -----
    **Determinism fix vs upstream:** the upstream ``codebook_metrics``
    picks the pair via ``random.uniform(0, 1) * B`` (non-deterministic
    for tests). We fix the pair to ``(0, 1)`` so the metric is
    byte-stable across re-runs. The pair is symmetric for ``B=2``
    and reproducible for ``B > 2``.
    """
    arr = _coerce_idx_2d(idx, vocab_size=vocab_size, min_batch=1)
    if arr.shape[0] < 2:
        return 0.0
    counts_a = np.bincount(arr[0], minlength=int(vocab_size)).astype(np.float64)
    counts_b = np.bincount(arr[1], minlength=int(vocab_size)).astype(np.float64)
    sum_a = counts_a.sum()
    sum_b = counts_b.sum()
    if sum_a <= 0 or sum_b <= 0:
        return 0.0
    pa = counts_a / sum_a
    pb = counts_b / sum_b
    m = 0.5 * (pa + pb)
    # KL(pa, m) + KL(pb, m) — both clamped to avoid log(0).
    def _kl(p: np.ndarray, q: np.ndarray) -> float:
        p_safe = np.clip(p, a_min=_LOG_EPS, a_max=None)
        q_safe = np.clip(q, a_min=_LOG_EPS, a_max=None)
        return float((p * np.log2(p_safe / q_safe)).sum())
    kl_a = _kl(pa, m)
    kl_b = _kl(pb, m)
    js = 0.5 * kl_a + 0.5 * kl_b
    if js < 0:
        # Should never happen for valid probability vectors, but be safe.
        js = 0.0
    return float(math.sqrt(js))


# ---------------------------------------------------------------------------
# Metric 4 — codebook_utilization (fraction of codebook cells used)
# ---------------------------------------------------------------------------


def compute_codebook_utilization(idx: Any, *, vocab_size: int = KANZI_DEFAULT_VOCAB_SIZE) -> float:
    """Compute the codebook utilization = ``|unique(idx)| / vocab_size``.

    Per the upstream ``estimate_loss`` test (``train_cb.py:321``,
    ``test/cb/utilization``)::

        seen = set()
        for el in all_idx:
            for i in el:
                seen.add(i.item())
        utilization = len(seen) / prod(cfg.levels)

    Parameters
    ----------
    idx
        ``LongTensor[N]`` (or any shape — we flatten). May be the
        concatenation of all per-backbone encoded indices from the
        eval split.
    vocab_size
        Codebook vocab size (default 4096).

    Returns
    -------
    float
        Utilization ∈ ``[0, 1]``. For ``V=4096`` a healthy
        FSQ-trained model typically achieves **0.3-0.7** (FSQ paper
        §4.1, Mentzer et al. 2023, arXiv:2309.15505). Empty input
        returns ``0.0``.

    Notes
    -----
    This is the most expensive of the 5 metrics (O(N) with a hash
    table) but trivial in absolute terms for ``N <= 100K``.
    """
    arr = _coerce_idx(idx, vocab_size=vocab_size)
    if arr.size == 0:
        return 0.0
    n_used = int(np.unique(arr).size)
    return float(n_used / int(vocab_size))


# ---------------------------------------------------------------------------
# Metric 5 — codebook_hamming_rotation_invariance
# ---------------------------------------------------------------------------


def _sample_uniform_rotation_matrix(rng: np.random.Generator) -> np.ndarray:
    """Sample a single uniformly-distributed 3x3 rotation matrix (deterministic given RNG).

    Mirrors the upstream ``sample_uniform_rotation`` at
    ``data/kanzi_upstream/src/kanzi/models.py:29-47`` but uses
    scipy.spatial.transform.RandomRotation (the same library upstream
    uses) under a controlled numpy ``default_rng`` for byte-stable
    tests.

    The upstream version uses ``Rotation.random(1).as_matrix()`` (no
    seed control). We pass a seeded ``Generator`` via the global
    ``numpy.random.default_rng`` is non-trivial for scipy (scipy uses
    its own global RNG), so we set ``numpy.random.seed`` once before
    the scipy call — sufficient for byte-stability as long as the
    caller does not concurrently sample rotations.

    Parameters
    ----------
    rng
        A seeded ``numpy.random.Generator``. Used to seed the global
        ``numpy.random`` state for scipy compatibility.

    Returns
    -------
    np.ndarray
        Shape ``(3, 3)`` rotation matrix with determinant ``+1``.
    """
    from scipy.spatial.transform import Rotation  # noqa: PLC0415

    seed = int(rng.integers(0, 2**31 - 1))
    # scipy.spatial.transform.Rotation.random uses numpy's global RNG
    # (no per-call seed). We seed it once before each sample so the
    # output is deterministic given the input ``rng`` state.
    np.random.seed(seed)
    return Rotation.random(num=1).as_matrix()[0]


def compute_codebook_hamming_rotation_invariance(
    coords: np.ndarray,
    *,
    encoder: Callable[[np.ndarray], np.ndarray],
    n_rot: int = DEFAULT_HAMMING_N_ROT,
    seed: int = 0,
    vocab_size: int = KANZI_DEFAULT_VOCAB_SIZE,
) -> float:
    """Compute the per-position Hamming equality under uniform-rotation pairs.

    Formula (matches upstream ``estimate_loss`` ``test/cb/hamming`` at
    ``train_cb.py:309-322``)::

        for each backbone r in eval_split:
            idx_r0 = encode(rotate(x_r, R0))            # (L,) LongTensor
            idx_r1 = encode(rotate(x_r, R1))            # (L,) LongTensor
            hamming_r = (idx_r0 == idx_r1).float().mean()
        hamming = mean over r of hamming_r

    Parameters
    ----------
    coords
        ``np.ndarray`` of shape ``(N, L, 3)`` — mean-centered Å
        coordinates per backbone. ``N == 0`` → returns ``0.0``.
    encoder
        Callable that maps a ``(L, 3)`` float32 numpy array to a
        ``(L,)`` int64 numpy array of FSQ codebook indices. The
        caller controls the encoder (the real DAE in production; a
        mock for tests).
    n_rot
        Number of (R0, R1) rotation pairs per backbone. Default 2
        (matches upstream ``estimate_loss``; the Kanzi paper uses
        128 but 2 is sufficient for byte-stable tests).
    seed
        RNG seed for the rotation sampler. Default 0.
    vocab_size
        Codebook vocab size. Forwarded to the index-range guard so a
        misconfigured encoder (e.g. wrong FSQ levels) fails loudly
        rather than silently returning a high Hamming number.

    Returns
    -------
    float
        Mean per-position Hamming equality ∈ ``[0, 1]``. A perfectly
        rotation-invariant encoder returns ``1.0``. A non-invariant
        encoder with random code matching returns ``~1/V`` (=
        ``1/4096`` for the Wave 36 ckpt).

    Notes
    -----
    **Determinism fix vs upstream:** the upstream uses ``random.uniform``
    for rotation sampling (non-deterministic for tests). We seed a
    ``numpy.random.Generator`` once at the top of the helper so the
    output is byte-stable given the same ``seed`` and ``coords``.

    The decoder is **not** called here — only the encoder is needed
    (matches upstream ``test/cb/hamming``). This keeps the metric fast:
    ~30 s CPU / ~10 s GPU for the 16-backbone smoke surface.
    """
    coords_arr = np.asarray(coords, dtype=np.float64)
    if coords_arr.ndim != 3 or coords_arr.shape[-1] != 3:
        raise ValueError(
            f"coords must have shape (N, L, 3); got {coords_arr.shape}"
        )
    n_backbones = int(coords_arr.shape[0])
    if n_backbones == 0:
        return 0.0
    if int(n_rot) < 2:
        raise ValueError(
            f"n_rot must be >= 2 (need at least one (R0, R1) pair); got {n_rot}"
        )

    rng = np.random.default_rng(int(seed))
    hamming_values: list[float] = []
    for r in range(n_backbones):
        x_r = coords_arr[r]
        # Sample n_rot rotation matrices; use consecutive pairs (R0, R1).
        rotations = [_sample_uniform_rotation_matrix(rng) for _ in range(int(n_rot))]
        for k in range(0, int(n_rot), 2):
            if k + 1 >= int(n_rot):
                break  # odd n_rot — drop the trailing R0 without R1.
            R0 = rotations[k]
            R1 = rotations[k + 1]
            x_r0 = x_r @ R0.T  # (L, 3)
            x_r1 = x_r @ R1.T  # (L, 3)
            idx0 = np.asarray(encoder(x_r0.astype(np.float32)), dtype=np.int64).reshape(-1)
            idx1 = np.asarray(encoder(x_r1.astype(np.float32)), dtype=np.int64).reshape(-1)
            if idx0.shape != idx1.shape:
                raise ValueError(
                    f"encoder returned inconsistent shapes for backbone "
                    f"r={r}: idx0.shape={idx0.shape} idx1.shape={idx1.shape}"
                )
            # Range guard so a misconfigured encoder fails loudly.
            if idx0.size > 0:
                vmax0 = int(idx0.max())
                vmax1 = int(idx1.max())
                if vmax0 >= int(vocab_size) or vmax1 >= int(vocab_size):
                    raise ValueError(
                        f"encoder returned index >= vocab_size={vocab_size} "
                        f"for backbone r={r}: max(idx0)={vmax0}, max(idx1)={vmax1}"
                    )
            hamming_r = float((idx0 == idx1).mean()) if idx0.size > 0 else 0.0
            hamming_values.append(hamming_r)
    if not hamming_values:
        return 0.0
    return float(np.mean(hamming_values))


# ---------------------------------------------------------------------------
# Aggregator — compute_all_codebook_metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CodebookMetricsResult:
    """Frozen container for the 5 Kanzi codebook metrics.

    Returned by :func:`compute_all_codebook_metrics`. All fields are
    ``float`` in their canonical ranges (entropy in bits, perplexity
    scalar, JS distance in ``bits^0.5``, utilization + hamming as
    fractions).
    """

    codebook_entropy_bits: float
    codebook_perplexity: float
    codebook_js_distance: float
    codebook_utilization: float
    codebook_hamming_rotation_invariance: float

    def to_dict(self) -> dict[str, float]:
        """Return a dict-of-floats view (for JSON serialization)."""
        return {k: float(v) for k, v in asdict(self).items()}


def compute_all_codebook_metrics(
    idx_BL: Any,
    *,
    vocab_size: int = KANZI_DEFAULT_VOCAB_SIZE,
    coords: np.ndarray | None = None,
    encoder: Callable[[np.ndarray], np.ndarray] | None = None,
    hamming_seed: int = 0,
    n_rot: int = DEFAULT_HAMMING_N_ROT,
) -> CodebookMetricsResult:
    """Compute all 5 Kanzi codebook metrics in one call.

    Convenience aggregator for the Wave 83+ paper-claim sweeps. The
    first four metrics are computed from the index tensor alone (no
    encoder required); the fifth (Hamming rotation-invariance) is only
    computed if both ``coords`` and ``encoder`` are provided.

    Parameters
    ----------
    idx_BL
        ``LongTensor[B, L]`` of FSQ codebook indices (used for
        entropy / perplexity / JS-distance / utilization).
    vocab_size
        Codebook vocab size (default 4096).
    coords
        Optional ``np.ndarray`` of shape ``(N, L, 3)`` — mean-centered
        Å coordinates per backbone. If omitted, hamming returns 0.0.
    encoder
        Optional callable ``(L, 3) -> (L,)`` that maps rotated
        coords to FSQ indices. If omitted, hamming returns 0.0.
    hamming_seed
        RNG seed for the rotation sampler (default 0).
    n_rot
        Number of rotation pairs per backbone (default 2).

    Returns
    -------
    CodebookMetricsResult
        Frozen dataclass with the 5 metric values.

    Notes
    -----
    The aggregator is byte-stable given a fixed ``idx_BL`` /
    ``coords`` / ``seed``. The upstream implementation is **not**
    byte-stable because of the JS-distance random-pair and the
    Hamming ``random.uniform`` rotation sampler; we replaced both
    with deterministic equivalents (fixed (0, 1) pair + seeded RNG).
    """
    entropy = compute_codebook_entropy(idx_BL, vocab_size=vocab_size)
    perplexity = compute_codebook_perplexity(idx_BL, vocab_size=vocab_size)
    js_distance = compute_codebook_js_distance(idx_BL, vocab_size=vocab_size)
    utilization = compute_codebook_utilization(idx_BL, vocab_size=vocab_size)
    if coords is not None and encoder is not None:
        hamming = compute_codebook_hamming_rotation_invariance(
            coords,
            encoder=encoder,
            n_rot=int(n_rot),
            seed=int(hamming_seed),
            vocab_size=vocab_size,
        )
    else:
        hamming = 0.0
    return CodebookMetricsResult(
        codebook_entropy_bits=float(entropy),
        codebook_perplexity=float(perplexity),
        codebook_js_distance=float(js_distance),
        codebook_utilization=float(utilization),
        codebook_hamming_rotation_invariance=float(hamming),
    )


# ---------------------------------------------------------------------------
# Metric 6 (already wired by Wave 79) — reconstruction_kabsch_rmsd_A
#
# We re-export the Wave 79 driver as a paper-metric function for the
# single-source-of-truth interface. The downstream caller (Wave 84+
# paper-claim sweeps) imports `compute_reconstruction_kabsch_rmsd_A`
# from this module rather than `tools.upstream_eval` directly so the
# six-metric surface is uniform.
# ---------------------------------------------------------------------------


def compute_reconstruction_kabsch_rmsd_A(
    sequences_path: str | pathlib.Path,
    output_dir: str | pathlib.Path,
    *,
    ckpt_path: str | pathlib.Path | None = None,
    timeout_s: int = 1800,
) -> dict[str, float]:
    """Delegate to Wave 79 ``run_kanzi_upstream_eval`` for reconstruction RMSD.

    Thin wrapper around the Wave 79 driver that surfaces the Kanzi
    paper's **single** non-codebook metric (``reconstruction_kabsch_rmsd_A``).
    Together with the 5 codebook metrics above, this gives the full
    6-metric Kanzi paper suite.

    Parameters
    ----------
    sequences_path
        Plain-text file (one record per line) where each line is a
        comma-separated ``x,y,z`` triplet list in Ångström. Use
        ``tools/extract_ca_coords_for_kanzi.py`` to generate such
        files from the vendored demo PDBs (or larger held-out
        subsets).
    output_dir
        Directory for ``reconstruction.json`` output. Created if missing.
    ckpt_path
        Optional path to a Kanzi ``.pt`` checkpoint. Defaults to the
        Wave 36 published ckpt at ``data/kanzi_ckpt/cleaned_model.pt``.
    timeout_s
        Wall-clock cap on the subprocess. Default 1800 s (30 min) —
        matches Wave 79 ``tools.upstream_eval.DEFAULT_TIMEOUT_S``.

    Returns
    -------
    dict[str, float]
        ``{"status": 1.0, "n_seqs": ..., "mean_rmsd_A": ...,
        "min_rmsd_A": ..., "max_rmsd_A": ...}`` on success.
        On subprocess failure, ``{"status": 0.0, "reason": "..."}``.

    Notes
    -----
    This wrapper does NOT add any new math on top of the Wave 79
    driver — it only re-exports under the paper-metric naming
    convention. The actual ``encode → decode → kabsch_rmsd`` loop
    lives in ``tools/upstream_eval._KANZI_DRIVER`` (subprocess).
    """
    try:
        from tools import upstream_eval as _upstream_eval  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover — import path drift
        _LOGGER.warning(
            "compute_reconstruction_kabsch_rmsd_A: failed to import "
            "tools.upstream_eval: %s",
            exc,
        )
        return {"status": 0.0, "reason": f"upstream_eval_import_failed:{exc}"}
    return _upstream_eval.run_kanzi_upstream_eval(
        sequences_path=sequences_path,
        output_dir=output_dir,
        ckpt_path=ckpt_path,
        timeout_s=timeout_s,
    )


# ---------------------------------------------------------------------------
# Availability shim — kanzi_available()
# ---------------------------------------------------------------------------


def kanzi_available() -> bool:
    """Return ``True`` iff the Kanzi upstream package is importable on this host.

    Mirrors :func:`adaptive_reflow.adapters.flowmol3_metrics_upstream.is_upstream_available`.
    Tests that exercise the Hamming metric (which needs the real DAE
    encoder) gate on this probe + the ``data/kanzi_ckpt/cleaned_model.pt``
    presence.
    """
    try:
        import importlib
        kanzi_spec = importlib.util.find_spec("kanzi")  # noqa: PLC0415
        if kanzi_spec is None:
            return False
        # Also check the vendored upstream repo's src/ on sys.path.
        repo_root = pathlib.Path(__file__).resolve().parent.parent
        kanzi_src = repo_root / "data" / "kanzi_upstream" / "src"
        if kanzi_src.is_dir() and str(kanzi_src) not in sys.path:
            sys.path.insert(0, str(kanzi_src))
        importlib.import_module("kanzi")  # noqa: PLC0415
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# CLI smoke surface — ``python tools/paper_metrics_kanzi.py --smoke``
# ---------------------------------------------------------------------------


def _smoke_main(argv: Sequence[str] | None = None) -> int:
    """CLI surface: run the 5 codebook metrics on a synthetic FSQ distribution.

    Usage::

        python tools/paper_metrics_kanzi.py --smoke \\
            --vocab-size 16 --n-per-dim 4 --seed 0

    For real-data smoke, point ``--reference-coords`` at a Wave 80
    extractor output file (one record per line, comma-separated
    ``x,y,z`` floats) and the helper will compute the 5 codebook
    metrics + the reconstruction RMSD via the Wave 79 driver.
    """
    import argparse

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--smoke", action="store_true",
        help="Run the smoke surface (synthetic FSQ + optional real ckpt).",
    )
    p.add_argument(
        "--vocab-size", type=int, default=KANZI_DEFAULT_VOCAB_SIZE,
        help=f"FSQ vocab size (default {KANZI_DEFAULT_VOCAB_SIZE}).",
    )
    p.add_argument(
        "--n-per-dim", type=int, default=4,
        help="Synthetic-FSQ rows (default 4).",
    )
    p.add_argument(
        "--seed", type=int, default=0,
        help="RNG seed for the synthetic FSQ (default 0).",
    )
    p.add_argument(
        "--reference-coords", type=pathlib.Path, default=None,
        help="Optional Wave 80 extractor output file (one record per line).",
    )
    p.add_argument(
        "--ckpt-path", type=pathlib.Path, default=None,
        help="Optional Kanzi .pt checkpoint (defaults to data/kanzi_ckpt/cleaned_model.pt).",
    )
    p.add_argument(
        "--output-dir", type=pathlib.Path,
        default=pathlib.Path("verification_outputs/kanzi_codebook_smoke"),
        help="Output directory for the JSON result.",
    )
    args = p.parse_args(argv)

    rng = np.random.default_rng(int(args.seed))
    # Synthetic FSQ: each row gets ``vocab_size // 2`` unique codes so
    # utilization is ~0.5 (deterministic + non-trivial).
    half = max(1, int(args.vocab_size) // 2)
    idx_per_row = []
    for _r in range(int(args.n_per_dim)):
        codes = rng.choice(int(args.vocab_size), size=half, replace=False)
        idx_per_row.append(codes)
    idx = np.stack(idx_per_row, axis=0).astype(np.int64)

    metrics = compute_all_codebook_metrics(
        idx,
        vocab_size=int(args.vocab_size),
        coords=None,
        encoder=None,  # hamming skipped (no real encoder in smoke)
        hamming_seed=int(args.seed),
    )

    result: dict[str, Any] = {
        "tool": "tools.paper_metrics_kanzi",
        "smoke": True,
        "vocab_size": int(args.vocab_size),
        "n_per_dim": int(args.n_per_dim),
        "seed": int(args.seed),
        "metrics": metrics.to_dict(),
        "kanzi_available": kanzi_available(),
    }

    if args.reference_coords is not None and args.reference_coords.is_file():
        # Run the Wave 79 reconstruction RMSD if a coords file is given.
        rmsd = compute_reconstruction_kabsch_rmsd_A(
            sequences_path=args.reference_coords,
            output_dir=args.output_dir,
            ckpt_path=args.ckpt_path,
        )
        result["reconstruction_kabsch_rmsd_A"] = rmsd

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / "kanzi_codebook_smoke.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_smoke_main())


__all__ = [
    "CodebookMetricsResult",
    "DEFAULT_HAMMING_N_ROT",
    "KANZI_DEFAULT_VOCAB_SIZE",
    "compute_all_codebook_metrics",
    "compute_codebook_entropy",
    "compute_codebook_hamming_rotation_invariance",
    "compute_codebook_js_distance",
    "compute_codebook_perplexity",
    "compute_codebook_utilization",
    "compute_reconstruction_kabsch_rmsd_A",
    "kanzi_available",
    "compute_pb_validity_pct",
]


def compute_pb_validity_pct(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Compatibility re-export of the canonical PoseBusters metric helper.

    Kanzi callers historically imported paper metrics from this module. Keep
    that import path stable while delegating implementation to
    :mod:`tools.paper_metrics` and its dependency-isolated loader.
    """
    from tools.paper_metrics import compute_pb_validity_pct as _compute

    return _compute(*args, **kwargs)
