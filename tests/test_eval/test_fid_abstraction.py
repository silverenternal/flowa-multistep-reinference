"""Tests for ``adaptive_reflow.eval.fid`` (Phase B / Phase C).

Covers the canonical :class:`InceptionV3FIDEvaluator` introduced as
the single-source-of-truth FID abstraction. The tests exercise the
math directly with synthetic feature matrices — no InceptionV3 forward
pass is performed (that codepath is locked in by
``tests/test_eval/test_eval_rf_cifar.py``).

Tests
-----

* ``test_known_golden_input`` — both samples drawn from ``N(0, I_d)``
  converge to a near-zero FID as the sample count grows (closed-form
  ``||μ - μ||^2 + Tr(Σ + Σ - 2 sqrt(Σ Σ)) = 0`` when the two Gaussians
  coincide).
* ``test_known_golden_input_shifted_mean`` — shift the sample mean by
  a deterministic ``v``; the mean-distance term contributes
  ``||v||^2`` to the FID (so the closed-form is exact in the
  infinite-sample limit; finite-sample FID differs by an O(1/n) term).
* ``test_insufficient_stats_returns_nan`` — single-row inputs return
  ``float('nan')`` (NOT ``inf``, deliberately diverging from the legacy
  ``tools.eval_rf_cifar.compute_fid`` convention).
* ``test_complex_real_handling`` — non-commuting positive-definite
  covariances force ``scipy.linalg.sqrtm`` to return complex values;
  the evaluator must keep only the real part and return a finite,
  non-negative value.
* ``test_eigen_clipping_for_singular`` — degenerate covariance (zero
  variance on one axis) triggers the ``+ eps * I`` offset retry; the
  output must still be finite and non-negative.
* ``test_deterministic`` — calling ``compute_from_features`` twice on
  the same arrays returns bit-identical :class:`FIDResult`.
* ``test_compute_from_precomputed_matches_features`` — fitting the
  reference statistics on a separate activation matrix and feeding
  them through ``compute_from_precomputed`` yields the same value as
  feeding both matrices through ``compute_from_features``.
* ``test_audit_code_on_insufficient_stats`` — the audit constant
  :data:`FID_AUDIT_INSUFFICIENT_STATS` is exported and non-empty.
"""

from __future__ import annotations

import math
import sys

import numpy as np
import pytest

from adaptive_reflow.eval.fid import (
    FID_AUDIT_INSUFFICIENT_STATS,
    FID_EIGENCLIP_EPS_DEFAULT,
    FIDProtocol,
    FIDResult,
    InceptionV3FIDEvaluator,
    compute_frechet_distance,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_unit_gaussian_features(
    *,
    n: int,
    d: int,
    seed: int,
) -> np.ndarray:
    """Sample ``(n, d)`` features from ``N(0, 1)``."""
    rng = np.random.default_rng(int(seed))
    return rng.standard_normal((int(n), int(d)))


def _make_shift_features(
    *,
    n: int,
    d: int,
    shift: np.ndarray,
    seed: int,
) -> np.ndarray:
    """Sample ``(n, d)`` features from ``N(shift, 1)``."""
    rng = np.random.default_rng(int(seed))
    base = rng.standard_normal((int(n), int(d)))
    return base + np.asarray(shift, dtype=np.float64)[None, :]


def _is_nan(value: float) -> bool:
    """Local helper — coerce to float then call ``math.isnan``."""
    return bool(math.isnan(float(value)))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("feature_dim", [4, 2048])
def test_precomputed_features_work_without_image_dependencies(
    monkeypatch: pytest.MonkeyPatch, feature_dim: int
) -> None:
    """Feature shape never determines whether image dependencies are needed."""
    monkeypatch.setitem(sys.modules, "torch", None)
    monkeypatch.setitem(sys.modules, "torchvision", None)
    evaluator = InceptionV3FIDEvaluator(feature_dim=feature_dim)
    # One observation exercises both public input boundaries without a costly
    # 2048-D matrix square root; finite arithmetic is covered below.
    features = np.zeros((1, feature_dim))
    results = [
        evaluator.compute_from_features(features, features),
        evaluator.compute_from_precomputed(
            features, np.zeros(feature_dim), np.zeros((feature_dim, feature_dim))
        ),
    ]
    for result in results:
        assert result.feature_dim == feature_dim
        assert math.isnan(result.value)


@pytest.mark.parametrize(
    "feature_dim", [True, False, None, "2048", 2048.0, [], {}, float("nan"), float("inf"), 0, -1]
)
def test_invalid_dimension_raises_value_error_without_image_dependencies(
    monkeypatch: pytest.MonkeyPatch, feature_dim: object
) -> None:
    monkeypatch.setitem(sys.modules, "torch", None)
    monkeypatch.setitem(sys.modules, "torchvision", None)
    with pytest.raises(ValueError, match="feature_dim"):
        InceptionV3FIDEvaluator(feature_dim=feature_dim)  # type: ignore[arg-type]


def test_dimension_validation_does_not_coerce_custom_objects() -> None:
    class IntLike:
        def __int__(self) -> int:
            raise AssertionError("dimension validation must not invoke __int__")

    with pytest.raises(ValueError, match="feature_dim"):
        InceptionV3FIDEvaluator(feature_dim=IntLike())  # type: ignore[arg-type]


def test_known_golden_input() -> None:
    """FID is ``0`` when both Gaussians coincide (closed-form identity).

    When ``reference_feats ~ N(0, I_d)`` and ``generated_feats ~ N(0, I_d)``
    the Fréchet distance converges to

        ||μ_r - μ_g||^2 + Tr(Σ_r + Σ_g - 2 sqrt(Σ_r Σ_g)) = 0 + Tr(2I - 2I) = 0

    in the infinite-sample limit. With ``n = 20000`` and ``d = 4`` the
    finite-sample noise on the mean-square term is bounded by
    ``d / n ~ 2e-4`` so we assert the FID is below ``1e-2`` (a
    conservative tolerance that leaves room for noise in the
    matrix-square-root step).
    """
    d = 4
    n = 20_000
    ref = _make_unit_gaussian_features(n=n, d=d, seed=1234)
    gen = _make_unit_gaussian_features(n=n, d=d, seed=4321)
    evaluator = InceptionV3FIDEvaluator(feature_dim=d)
    result = evaluator.compute_from_features(ref, gen)
    assert isinstance(result, FIDResult)
    assert result.feature_dim == d
    assert result.n_samples == n
    assert result.is_finite, (
        f"FID should be finite for coincident Gaussians; got {result.value!r}"
    )
    assert result.value >= 0.0, f"FID must be non-negative; got {result.value}"
    assert result.value < 1e-2, (
        f"FID for N(0,I) vs N(0,I) should be ~0 (mean-square noise "
        f"is O(d/n) ~ 2e-4); got {result.value}. The Fréchet arithmetic "
        f"has regressed."
    )


def test_known_golden_input_shifted_mean() -> None:
    """Mean-shift of ``v`` contributes ``||v||^2`` to the FID (closed form).

    With reference ``~ N(0, I_d)`` and generated ``~ N(v, I_d)`` the
    closed-form FID is ``||v||^2`` (covariance terms cancel because
    ``Σ_r = Σ_g = I`` ⇒ ``Tr(2I - 2I) = 0``). Finite-sample noise
    inflates the value by an ``O(d/n)`` amount; at ``n = 20000``,
    ``d = 4`` the noise is ``~ 2e-4`` which we ignore.
    """
    d = 4
    n = 20_000
    v = np.array([1.0, 2.0, 0.5, -0.5], dtype=np.float64)
    expected = float(np.dot(v, v))  # = 1 + 4 + 0.25 + 0.25 = 5.5
    ref = _make_unit_gaussian_features(n=n, d=d, seed=7)
    gen = _make_shift_features(n=n, d=d, shift=v, seed=11)
    evaluator = InceptionV3FIDEvaluator(feature_dim=d)
    result = evaluator.compute_from_features(ref, gen)
    assert result.is_finite
    # Tolerance accounts for finite-sample noise: mean-square error
    # on the mu term is ``d / n = 4 / 20000 = 2e-4``. The empirical
    # estimator's covariance noise is much smaller (order 1/n as
    # well). Use a generous 5 % relative tolerance.
    rel = abs(result.value - expected) / expected
    assert rel < 0.05, (
        f"FID for shifted-mean Gaussians should equal ||v||^2 = {expected}; "
        f"got {result.value} (relative error {rel:.4f}). The closed-form "
        f"mean-distance term has regressed."
    )


def test_insufficient_stats_returns_nan() -> None:
    """Single-row inputs must return ``float('nan')`` (NOT ``inf``).

    The canonical scientific convention is that FID is undefined for
    ``n < 2`` because the sample covariance is degenerate. The
    ``tools.eval_rf_cifar.compute_fid`` tool returns ``inf`` instead;
    this is a deliberate deviation from that tool — see the
    ``adaptive_reflow.eval.fid`` module docstring for the rationale.

    Both ``compute_from_features`` and ``compute_from_precomputed`` are
    exercised.
    """
    d = 8
    evaluator = InceptionV3FIDEvaluator(feature_dim=d)
    one_row_ref = np.zeros((1, d), dtype=np.float64)
    one_row_gen = np.ones((1, d), dtype=np.float64)
    # compute_from_features: both must have <2 rows.
    r1 = evaluator.compute_from_features(one_row_ref, one_row_gen)
    assert not r1.is_finite
    assert _is_nan(r1.value)
    # Precomputed path with <2 sample rows.
    big_ref = _make_unit_gaussian_features(n=128, d=d, seed=1)
    mu_r = np.asarray(big_ref.mean(axis=0), dtype=np.float64)
    sigma_r = np.asarray(np.cov(big_ref, rowvar=False), dtype=np.float64)
    r2 = evaluator.compute_from_precomputed(one_row_gen, mu_r, sigma_r)
    assert not r2.is_finite
    assert _is_nan(r2.value)


def test_complex_real_handling() -> None:
    """Non-PD inputs force ``sqrtm`` to return complex; ``np.real`` must fix it.

    When the inner product ``Σ_s Σ_r`` has eigenvalues with negative
    real parts (which happens for finite-sample covariances whose
    numerical roundoff pushes small eigenvalues below zero), scipy's
    ``sqrtm`` returns a complex-valued matrix. The evaluator must
    take ``np.real`` of the result (the canonical pytorch-fid pattern
    — see ``tools.compute_cifar_fid.calculate_frechet_distance`` and
    ``tools.eval_rf_cifar.compute_fid``) and produce a finite,
    non-negative FID.

    We exercise the inner method directly with a crafted pair
    (``mu_s``, ``sigma_s``) and (``mu_r``, ``sigma_r``) whose
    ``sigma_s @ sigma_r`` product provably has a negative real
    eigenvalue — this is the case the ``np.real`` fallback was
    written for.
    """
    d = 4
    # Construct two PSD-shaped matrices whose product has negative
    # real eigenvalues. The product is the matrix whose sqrtm is
    # complex; we work backwards by defining the product directly and
    # splitting it as ``sigma_s @ sigma_r``.
    prod = np.array(
        [
            [1.0, 2.0, 0.0, 0.0],
            [0.0, -1.0, 0.0, 0.0],  # negative eigenvalue triggers complex sqrtm
            [0.0, 0.0, 0.5, 0.0],
            [0.0, 0.0, 0.0, 0.5],
        ],
        dtype=np.float64,
    )
    # Use scipy.linalg.sqrtm directly to verify the test setup is
    # actually forcing the complex case (otherwise the test is
    # asserting nothing).
    from scipy.linalg import sqrtm as _sqrtm

    sanity = _sqrtm(prod)
    assert np.iscomplexobj(sanity), (
        "test setup invalid: scipy.linalg.sqrtm returned real output; "
        "the complex-real handling path is not being exercised."
    )

    # sigma_s = I, sigma_r = prod (so sigma_s @ sigma_r = prod). The
    # identity matrix is trivially PSD; only sigma_r is non-PD, but
    # the inner method does not check PSD-ness — it just feeds the
    # product through sqrtm and returns ``np.real(covmean)``.
    sigma_s = np.eye(d, dtype=np.float64)
    sigma_r = np.asarray(prod, dtype=np.float64)
    mu_s = np.zeros(d, dtype=np.float64)
    mu_r = np.zeros(d, dtype=np.float64)
    evaluator = InceptionV3FIDEvaluator(feature_dim=d)
    value = evaluator._compute_frechet_distance_inner(  # noqa: SLF001
        mu_s, sigma_s, mu_r, sigma_r
    )
    assert math.isfinite(float(value)), (
        f"FID should be finite after np.real of a complex covmean; "
        f"got {value!r}. The complex-real handling has regressed."
    )
    assert float(value) >= 0.0


def test_eigen_clipping_for_singular() -> None:
    """Degenerate covariance triggers the ``+ eps * I`` retry path.

    When one feature dimension is constant (zero variance) the
    covariance matrix is singular and the primary ``sqrtm`` may return
    non-finite entries. The evaluator must retry with
    ``+ eps * I`` and still produce a finite, non-negative FID.
    """
    d = 4
    n = 256
    # All rows have the same value on dimension 0 → zero variance on that axis.
    rng = np.random.default_rng(2)
    gen = rng.standard_normal((n, d)).astype(np.float64)
    gen[:, 0] = 0.5  # constant column → singular cov
    ref = rng.standard_normal((n, d)).astype(np.float64)
    ref[:, 0] = -0.5
    evaluator = InceptionV3FIDEvaluator(feature_dim=d)
    result = evaluator.compute_from_features(ref, gen)
    assert result.is_finite, (
        f"FID should remain finite after eigenclipping retry; got {result.value!r}. "
        f"The + eps * I retry path is broken."
    )
    assert result.value >= 0.0
    # Sanity: the default eigenclip epsilon matches the documented constant.
    assert evaluator.eigenclip_eps == FID_EIGENCLIP_EPS_DEFAULT


def test_deterministic() -> None:
    """Calling ``compute_from_features`` twice yields bit-identical results.

    The FID arithmetic has no stochastic component (``np.cov``,
    ``np.mean``, ``scipy.linalg.sqrtm``); identical inputs must
    produce identical outputs. This test pins the deterministic
    contract so future refactors (e.g. switching to a torch-based
    sqrtm) cannot silently introduce non-determinism.
    """
    d = 4
    n = 1_000
    ref = _make_unit_gaussian_features(n=n, d=d, seed=99)
    gen = _make_unit_gaussian_features(n=n, d=d, seed=101)
    evaluator = InceptionV3FIDEvaluator(feature_dim=d)
    r1 = evaluator.compute_from_features(ref, gen)
    r2 = evaluator.compute_from_features(ref, gen)
    assert r1.value == r2.value, (
        f"compute_from_features is non-deterministic across two calls "
        f"with identical inputs: {r1.value} vs {r2.value}."
    )
    assert r1.feature_dim == r2.feature_dim
    assert r1.n_samples == r2.n_samples
    assert r1.is_finite == r2.is_finite


def test_compute_from_precomputed_matches_features() -> None:
    """Precomputed path produces the same value as the raw-features path.

    Fitting ``(mu_r, sigma_r)`` on the reference activation matrix and
    passing them through ``compute_from_precomputed`` must produce the
    same FID value (to numerical tolerance) as passing the raw
    reference activations through ``compute_from_features``.
    """
    d = 4
    n = 1_000
    ref = _make_unit_gaussian_features(n=n, d=d, seed=2024)
    gen = _make_unit_gaussian_features(n=n, d=d, seed=2025)
    evaluator = InceptionV3FIDEvaluator(feature_dim=d)
    raw = evaluator.compute_from_features(ref, gen)
    mu_r = np.asarray(ref.mean(axis=0), dtype=np.float64)
    sigma_r = np.asarray(np.cov(ref, rowvar=False), dtype=np.float64)
    pre = evaluator.compute_from_precomputed(gen, mu_r, sigma_r)
    assert raw.is_finite and pre.is_finite
    # The two paths compute mu_r / sigma_r from the SAME matrix `ref`,
    # so they must match bit-for-bit.
    assert raw.value == pytest.approx(pre.value, rel=1e-9), (
        f"compute_from_features ({raw.value}) and compute_from_precomputed "
        f"({pre.value}) diverged on identical inputs. The two paths are "
        f"not routing through _compute_frechet_distance_inner as documented."
    )


def test_protocol_is_abstract() -> None:
    """``FIDProtocol`` cannot be instantiated directly.

    The protocol declares the abstract surface; concrete evaluators
    inherit and override. We pin this contract by attempting an
    instantiation and asserting ``TypeError``.
    """
    with pytest.raises(TypeError):
        FIDProtocol()  # type: ignore[abstract]


def test_audit_code_constant_exported() -> None:
    """``FID_AUDIT_INSUFFICIENT_STATS`` is exported and non-empty.

    The audit code is the framework's diagnostic hook for "FID was
    undefined because of insufficient statistics". Downstream
    manifests reference it by name; the export must remain stable.
    """
    assert isinstance(FID_AUDIT_INSUFFICIENT_STATS, str)
    assert FID_AUDIT_INSUFFICIENT_STATS, "audit code must be non-empty"


def test_compute_frechet_distance_functional_form() -> None:
    """The functional helper agrees with the evaluator's inner method.

    :func:`compute_frechet_distance` is a thin wrapper around the
    evaluator's inner method; we verify the values agree bit-for-bit
    on a fixed input. This locks the function as a public surface
    (legacy callers migrate without instantiating an evaluator).
    """
    d = 3
    n = 500
    rng = np.random.default_rng(42)
    a = rng.standard_normal((n, d))
    b = rng.standard_normal((n, d))
    mu_s = np.asarray(a.mean(axis=0), dtype=np.float64)
    sigma_s = np.asarray(np.cov(a, rowvar=False), dtype=np.float64)
    mu_r = np.asarray(b.mean(axis=0), dtype=np.float64)
    sigma_r = np.asarray(np.cov(b, rowvar=False), dtype=np.float64)
    expected = InceptionV3FIDEvaluator(feature_dim=d)._compute_frechet_distance_inner(  # noqa: SLF001
        mu_s, sigma_s, mu_r, sigma_r
    )
    got = compute_frechet_distance(
        mu_s=mu_s, sigma_s=sigma_s, mu_r=mu_r, sigma_r=sigma_r
    )
    assert float(expected) == pytest.approx(float(got), rel=1e-12)
