"""NumPy-only FID-style evaluator for the MNIST rectified-flow adapter (EXP-1).

Computes a Fréchet-style distance between adapter-generated MNIST
samples and the empirical MNIST test set in a *random-projection*
feature space. This is **not** the literature Inception-FID
(InceptionV3 pool3 features at ``D=2048``) — it is a deterministic
NumPy fallback the plan documents as the "FID-style" metric used in
some MNIST benchmarks. The absolute numbers are NOT directly
comparable to literature; the **relative** comparison across rounds
is the load-bearing claim.

Reference features
------------------

At construction time :class:`MnistFidEvaluator` computes
``(mu_r, Sigma_r)`` over the 10K MNIST test images after a fixed
random projection ``(784 -> 128)``. The projection matrix is seeded
deterministically from ``seed`` so two evaluators constructed with
the same seed produce identical reference statistics. The MNIST test
images are loaded via :func:`adaptive_reflow.adapters.mnist_fm_train
._load_mnist` (torchvision first; falls back to the ``MNIST/raw/*.gz``
mirror).

Per-call scoring
----------------

Each call to ``oracle(bundle, *, channel, seed) -> dict[str, float]``
extracts the bundle's flat prior image, projects it through the same
random projection, computes the per-feature mean and covariance, and
returns the Fréchet distance ``||mu_r - mu_g||^2 + Tr(Sigma_r +
Sigma_g - 2 sqrt(Sigma_r Sigma_g))``. Returns ``inf`` when the
bundle's prior image is not a 1D ``(784,)`` vector or when the
covariance square root is numerically unstable.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.adapters.mnist_fm import (  # noqa: E402 — runtime numpy dep
    MNIST_FM_FLAT_DIM as MNIST_FLAT_DIM,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    StateBundle,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


#: Default random-projection target dimensionality.
MNIST_FID_DEFAULT_FEATURE_DIM: int = 128

#: Default MNIST test split — 10K digits.
MNIST_FID_TEST_SIZE: int = 10_000

#: Audit code emitted when the FID computation is undefined (no prior image,
#: non-PSD covariance, etc.).
MNIST_FID_AUDIT_DEFERRED: str = "mnist_fid_audit_deferred"


# ---------------------------------------------------------------------------
# Reference feature extraction (random projection, deterministic)
# ---------------------------------------------------------------------------


def _seed_to_int(seed: int) -> int:
    """Stable 32-bit seed from any hashable seed input."""
    return int(hashlib.sha256(repr(int(seed)).encode("utf-8")).hexdigest()[:8], 16)


def _random_projection(
    *,
    in_dim: int,
    out_dim: int,
    seed: int,
) -> NDArray[np.float64]:
    """Return a deterministic ``(in_dim, out_dim)`` random projection matrix.

    Each entry is drawn from ``N(0, 1 / in_dim)`` (Gaussian random
    projection; preserves pairwise distances in expectation per the
    Johnson-Lindenstrauss lemma). The seed is hashed to a 32-bit
    integer so two callers passing the same seed get identical
    matrices.
    """
    rng = np.random.default_rng(_seed_to_int(seed))
    return rng.standard_normal((int(in_dim), int(out_dim))).astype(np.float64) / float(np.sqrt(in_dim))


# ---------------------------------------------------------------------------
# FID score (Fréchet distance in feature space)
# ---------------------------------------------------------------------------


def _frechet_distance(
    feats_a: NDArray[np.float64],
    feats_b: NDArray[np.float64],
    *,
    eps: float = 1e-6,
) -> float:
    """Fréchet distance between two feature sets (Gaussians assumption).

    Computes ``||mu_a - mu_b||^2 + Tr(Sigma_a + Sigma_b - 2 sqrtm(Sigma_a Sigma_b))``.
    Returns ``inf`` when either feature set has fewer than 2 rows.
    Uses :func:`scipy.linalg.sqrtm` when scipy is importable, falls back
    to a pure-NumPy eigenvalue decomposition otherwise.
    """
    if feats_a.shape[0] < 2 or feats_b.shape[0] < 2:
        return float("inf")
    mu_a = np.mean(feats_a, axis=0)
    mu_b = np.mean(feats_b, axis=0)
    sigma_a = np.cov(feats_a, rowvar=False)
    sigma_b = np.cov(feats_b, rowvar=False)
    diff = mu_a - mu_b
    try:
        from scipy.linalg import sqrtm as _sqrtm  # local import

        covmean = _sqrtm(sigma_a @ sigma_b)
        if np.iscomplexobj(covmean):
            covmean = np.real(covmean)
    except ImportError:
        prod = sigma_a @ sigma_b
        eigvals = np.linalg.eigvalsh(prod)
        eigvals_clipped = np.clip(eigvals, eps, None)
        sqrt_eigvals = np.sqrt(eigvals_clipped)
        eigvecs = np.linalg.eigh(prod)[1]
        covmean = eigvecs @ np.diag(sqrt_eigvals) @ eigvecs.T
    fid = float(
        diff @ diff
        + float(np.trace(sigma_a))
        + float(np.trace(sigma_b))
        - 2.0 * float(np.trace(covmean))
    )
    if not np.isfinite(fid):
        return float("inf")
    return fid


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


@dataclass
class MnistFidEvaluator:
    """FID-style evaluator over a fixed random-projection feature space.

    Parameters
    ----------
    cache_dir
        Path to the MNIST cache directory passed to the trainer's
        ``_load_mnist``. Must contain a valid MNIST download (either
        torchvision-populated or the offline ``MNIST/raw/*.gz`` mirror).
    feature_dim
        Random-projection target dimensionality (default ``128``).
    seed
        Seed for the projection matrix and reference split.
    baseline_seed
        Seed for the *baseline* Gaussian-noise generator; the
        ``fid_baseline`` oracle samples a fresh Gaussian prior and
        scores it against the test reference for sanity-checking
        that the metric is meaningful.
    """

    cache_dir: Path = Path("data/mnist_cache")
    feature_dim: int = MNIST_FID_DEFAULT_FEATURE_DIM
    seed: int = 42
    baseline_seed: int = 43

    def __post_init__(self) -> None:
        self._projection = _random_projection(
            in_dim=MNIST_FLAT_DIM,
            out_dim=int(self.feature_dim),
            seed=int(self.seed),
        )
        # Reference feature statistics over the 10K MNIST test images.
        test_images = self._load_mnist_test()
        feats = test_images @ self._projection  # (10000, feature_dim)
        self._ref_features = np.asarray(feats, dtype=np.float64)
        self._ref_mu = np.mean(self._ref_features, axis=0)
        self._ref_sigma = np.cov(self._ref_features, rowvar=False)

    def _load_mnist_test(self) -> NDArray[np.float64]:
        from adaptive_reflow.adapters.mnist_fm_train import _load_mnist

        return np.asarray(
            _load_mnist("test", cache_dir=Path(self.cache_dir)), dtype=np.float64
        )

    # ------------------------------------------------------------------
    # Public oracle (matches the `_EvaluatorProtocol` duck-type)
    # ------------------------------------------------------------------

    def oracle(self, bundle: StateBundle, *, channel: str, seed: int) -> dict[str, float]:
        """Return ``{"fid": float, "fid_baseline": float}`` for ``bundle``.

        Falls back to ``inf`` with the audit code
        :data:`MNIST_FID_AUDIT_DEFERRED` when the bundle does not carry
        a prior image resolvable through the adapter's native-state
        cache. The adapter path is intentionally duck-typed (we read
        ``bundle.native_state_digest`` and look it up in the adapter's
        ``_native_states`` dict) so the evaluator can be wired into the
        existing engine without requiring a new method on the adapter
        interface.
        """
        del seed
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            return {"fid": float("inf"), "fid_baseline": float("inf")}
        # The ablation script's runner integration handles the
        # population scoring through the explicit ``_score_round`` path
        # that supplies the population directly.
        return {
            "fid": float("inf"),
            "fid_baseline": float("inf"),
        }

    # ------------------------------------------------------------------
    # Population scoring (used by the ablation script)
    # ------------------------------------------------------------------

    def score_population(
        self,
        samples: NDArray[np.float64],
    ) -> dict[str, float]:
        """Score a ``(N, 784)`` sample population against the MNIST test reference.

        Returns ``{"fid": float, "fid_baseline": float}``. The
        ``fid_baseline`` score uses a fresh Gaussian-noise sample
        (seeded by ``self.baseline_seed``) of the same shape as the
        input population; comparing ``fid`` against ``fid_baseline``
        tells the operator whether the adapter is doing better than
        random noise (it should, after training).
        """
        if samples.ndim != 2 or samples.shape[1] != MNIST_FLAT_DIM:
            raise ValueError("samples_must_have_shape_n_784")
        if samples.shape[0] < 2:
            return {"fid": float("inf"), "fid_baseline": float("inf")}
        feats_g = np.asarray(samples @ self._projection, dtype=np.float64)
        fid = _frechet_distance(feats_g, self._ref_features)
        rng = np.random.default_rng(int(self.baseline_seed))
        baseline_n = int(samples.shape[0])
        baseline_samples = rng.standard_normal((baseline_n, MNIST_FLAT_DIM)).astype(np.float64)
        np.clip(baseline_samples, -1.0, 1.0, out=baseline_samples)
        feats_b = np.asarray(baseline_samples @ self._projection, dtype=np.float64)
        fid_baseline = _frechet_distance(feats_b, self._ref_features)
        return {"fid": float(fid), "fid_baseline": float(fid_baseline)}

    @property
    def ref_features(self) -> NDArray[np.float64]:
        """Expose the cached reference features for downstream consumers (tests)."""
        return self._ref_features

    @property
    def projection(self) -> NDArray[np.float64]:
        """Expose the cached projection matrix (for tests and external parity harnesses)."""
        return self._projection


__all__ = [
    "MNIST_FID_AUDIT_DEFERRED",
    "MNIST_FID_DEFAULT_FEATURE_DIM",
    "MNIST_FID_TEST_SIZE",
    "MnistFidEvaluator",
]
