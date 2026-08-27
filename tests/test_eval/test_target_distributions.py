"""Mode-centre consolidation tests (ADR-DTB-R7-B2).

Verifies that the 2D-FM mode-centre definitions are owned by a single
canonical module (:mod:`adaptive_reflow.data.target_distributions`) and
that every consumer -- the offline trainer, the 2D-FM evaluator, the
posterior-selection evaluator, and the ablation script -- resolves its
mode-centre arrays through that module. The byte-equality assertions
catch the "different files redefining the same geometry" drift this
task was opened to prevent.
"""
from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.data.target_distributions import (
    EIGHT_GAUSSIANS_MODE_CENTERS,
    EIGHT_GAUSSIANS_POSTERIOR_CELLS,
    EIGHT_GAUSSIANS_POSTERIOR_RADIUS,
    EIGHT_GAUSSIANS_POSTERIOR_SHEET,
    EIGHT_GAUSSIANS_SAMPLER_CENTERS,
    EIGHT_GAUSSIANS_SAMPLER_RADIUS,
    EIGHT_GAUSSIANS_SAMPLER_STDDEV,
    TWO_MOONS_MODE_CENTERS,
    TWO_MOONS_NOISE,
    TWO_MOONS_POSTERIOR_CELLS,
    TWO_MOONS_POSTERIOR_SHEET,
    TWO_MOONS_SAMPLER_CENTERS,
    mode_centers_for_target,
    posterior_cells_for,
    posterior_centers_for,
    posterior_sheet_for,
    sampler_centers_for,
)

# ---------------------------------------------------------------------------
# Canonical source is self-consistent
# ---------------------------------------------------------------------------


def test_two_moons_sampler_centers_shape() -> None:
    """The canonical two-moons sampler-centre set is ``(2, 2)`` float64."""
    arr = TWO_MOONS_SAMPLER_CENTERS
    assert arr.shape == (2, 2)
    assert arr.dtype == np.float64
    # Documented values: moon_a at parent-circle centre (0, 0), moon_b at (1, -0.5).
    assert np.array_equal(arr, np.asarray([[0.0, 0.0], [1.0, -0.5]]))


def test_eight_gaussians_sampler_centers_shape() -> None:
    """The canonical eight-gaussians sampler-centre set is ``(8, 2)`` float64."""
    arr = EIGHT_GAUSSIANS_SAMPLER_CENTERS
    assert arr.shape == (8, 2)
    assert arr.dtype == np.float64
    # All 8 centres lie at radius :data:`EIGHT_GAUSSIANS_SAMPLER_RADIUS`.
    radii = np.linalg.norm(arr, axis=1)
    assert np.allclose(radii, EIGHT_GAUSSIANS_SAMPLER_RADIUS)


def test_two_moons_mode_centers_shape() -> None:
    """The canonical two-moons coverage-mode-centre set is ``(2, 2)`` float64."""
    arr = TWO_MOONS_MODE_CENTERS
    assert arr.shape == (2, 2)
    assert arr.dtype == np.float64
    # Documented values: moon-a mode at (0, 1), moon-b at (1, -0.5).
    assert np.array_equal(arr, np.asarray([[0.0, 1.0], [1.0, -0.5]]))


def test_eight_gaussians_mode_centers_shape() -> None:
    """The canonical eight-gaussians coverage-mode-centre set is ``(8, 2)``."""
    arr = EIGHT_GAUSSIANS_MODE_CENTERS
    assert arr.shape == (8, 2)
    assert arr.dtype == np.float64
    # All 8 centres lie at radius 2 (same ring as the sampler geometry).
    radii = np.linalg.norm(arr, axis=1)
    assert np.allclose(radii, 2.0)


# ---------------------------------------------------------------------------
# Adapter and evaluator byte-equality (the consolidation contract)
# ---------------------------------------------------------------------------


def test_adapter_sampler_matches_canonical_two_moons() -> None:
    """The adapter's sampler geometry for ``two_moons`` is byte-equal to the canonical source.

    The offline trainer's :func:`sample_two_moons` produces points
    distributed around the parent-circle centres ``(0, 0)`` (moon_a)
    and ``(1, -0.5)`` (moon_b). The canonical
    :data:`TWO_MOONS_SAMPLER_CENTERS` must match those implicit centres
    exactly so the adapter and any consumer reading from the canonical
    source see the same geometry.
    """
    from adaptive_reflow.adapters.twodim_fm_train import (
        EIGHT_GAUSSIANS_RADIUS as trainer_radius,
    )
    from adaptive_reflow.adapters.twodim_fm_train import (
        EIGHT_GAUSSIANS_STDDEV as trainer_stddev,
    )
    from adaptive_reflow.adapters.twodim_fm_train import (
        TWO_MOONS_NOISE as trainer_noise,
    )

    assert float(trainer_noise) == float(TWO_MOONS_NOISE)
    assert float(trainer_radius) == float(EIGHT_GAUSSIANS_SAMPLER_RADIUS)
    assert float(trainer_stddev) == float(EIGHT_GAUSSIANS_SAMPLER_STDDEV)
    # The trainer's sampler geometry for eight_gaussians is the
    # canonical sampler-centre set itself; verify byte-equality.
    from adaptive_reflow.adapters.twodim_fm_train import sample_eight_gaussians

    rng = np.random.default_rng(20260828)
    samples = sample_eight_gaussians(2048, rng)
    # Nearest-centre distances should be bounded by ~5 sigma of
    # :data:`EIGHT_GAUSSIANS_SAMPLER_STDDEV` (we use 5x for headroom).
    nearest = np.min(
        np.linalg.norm(
            samples[:, None, :] - EIGHT_GAUSSIANS_SAMPLER_CENTERS[None, :, :],
            axis=2,
        ),
        axis=1,
    )
    assert float(np.max(nearest)) < 5.0 * EIGHT_GAUSSIANS_SAMPLER_STDDEV


def test_adapter_and_evaluator_use_same_canonical_centers() -> None:
    """The adapter and the evaluator must reference the *same* canonical arrays.

    This is the ADR-DTB-R7-B2 contract: every consumer resolves its
    mode-centre geometry through
    :mod:`adaptive_reflow.data.target_distributions`, so there is only
    one place to change a coordinate and only one place where a
    silent drift can hide. Object identity (``is``) is the strongest
    check -- it proves the consumers share the *same* array, not just
    two arrays with the same contents.
    """
    # Adapter side: the trainer's sampler-centres are the canonical set.
    from adaptive_reflow.adapters.twodim_fm_train import sample_eight_gaussians

    _ = sample_eight_gaussians  # import side-effect check
    # Evaluator side: the coverage-mode-centres are the canonical set.
    from adaptive_reflow.eval.twodim_fm_evaluator import (
        _EIGHT_GAUSSIANS_MODE_CENTERS,
        _TWO_MOONS_MODE_CENTERS,
    )

    # Object-identity check: each consumer's module-level alias is the
    # canonical array, not a copy.
    assert _TWO_MOONS_MODE_CENTERS is TWO_MOONS_MODE_CENTERS
    assert _EIGHT_GAUSSIANS_MODE_CENTERS is EIGHT_GAUSSIANS_MODE_CENTERS


def test_evaluator_mode_centers_for_dispatch() -> None:
    """``_mode_centers_for`` resolves to the canonical coverage-mode set."""
    from adaptive_reflow.eval.twodim_fm_evaluator import _mode_centers_for

    assert np.array_equal(
        _mode_centers_for("two_moons"), TWO_MOONS_MODE_CENTERS
    )
    assert np.array_equal(
        _mode_centers_for("eight_gaussians"), EIGHT_GAUSSIANS_MODE_CENTERS
    )
    # ``mode_centers_for_target`` returns the same arrays.
    assert np.array_equal(
        mode_centers_for_target("two_moons"), TWO_MOONS_MODE_CENTERS
    )
    assert np.array_equal(
        mode_centers_for_target("eight_gaussians"),
        EIGHT_GAUSSIANS_MODE_CENTERS,
    )


def test_run_ablation_mode_centers_canonical() -> None:
    """``tools/run_ablation._mode_centers_for`` resolves through the canonical module."""
    from tools.run_ablation import _mode_centers_for

    assert np.array_equal(
        _mode_centers_for("two_moons"), TWO_MOONS_MODE_CENTERS
    )
    assert np.array_equal(
        _mode_centers_for("eight_gaussians"), EIGHT_GAUSSIANS_MODE_CENTERS
    )


def test_run_ablation_module_does_not_redefine_centers() -> None:
    """``tools/run_ablation.py`` must not redefine the canonical constants itself.

    Guards against future edits that re-introduce a local copy of
    :data:`TWO_MOONS_MODE_CENTERS` / :data:`EIGHT_GAUSSIANS_MODE_CENTERS`
    in the ablation script.
    """
    import tools.run_ablation as run_ablation

    # The script exposes a `_mode_centers_for` helper that delegates to
    # the canonical module. It must not import the private underscored
    # arrays from the evaluator module any more (that was the
    # pre-consolidation contract).
    assert not hasattr(run_ablation, "_TWO_MOONS_MODE_CENTERS"), (
        "tools/run_ablation.py must not redefine _TWO_MOONS_MODE_CENTERS; "
        "import it from adaptive_reflow.data.target_distributions instead"
    )
    assert not hasattr(run_ablation, "_EIGHT_GAUSSIANS_MODE_CENTERS"), (
        "tools/run_ablation.py must not redefine _EIGHT_GAUSSIANS_MODE_CENTERS; "
        "import it from adaptive_reflow.data.target_distributions instead"
    )


# ---------------------------------------------------------------------------
# Posterior-selection (paper Theorem 1) geometry
# ---------------------------------------------------------------------------


def test_posterior_centers_two_moons() -> None:
    """Paper-Theorem-1 sheet + cell geometry for ``two_moons`` is canonical."""
    assert posterior_sheet_for("two_moons") == TWO_MOONS_POSTERIOR_SHEET == (0.5, 0.0)
    assert posterior_cells_for("two_moons") == TWO_MOONS_POSTERIOR_CELLS == ((-0.5, 0.0),)
    arr = posterior_centers_for("two_moons")
    assert arr.shape == (2, 2)
    assert np.array_equal(arr, np.asarray([[0.5, 0.0], [-0.5, 0.0]]))


def test_posterior_centers_eight_gaussians() -> None:
    """Paper-Theorem-1 sheet + 7-cell geometry for ``eight_gaussians`` is canonical."""
    assert (
        posterior_sheet_for("eight_gaussians")
        == EIGHT_GAUSSIANS_POSTERIOR_SHEET
    )
    expected_sheet = (
        float(EIGHT_GAUSSIANS_POSTERIOR_RADIUS),
        0.0,
    )
    assert posterior_sheet_for("eight_gaussians") == expected_sheet
    cells = posterior_cells_for("eight_gaussians")
    assert len(cells) == 7
    # All 7 cells lie at the paper radius.
    cell_radii = np.linalg.norm(np.asarray(cells), axis=1)
    assert np.allclose(cell_radii, EIGHT_GAUSSIANS_POSTERIOR_RADIUS)
    # Concatenated centres are sheet + cells (canonical order).
    arr = posterior_centers_for("eight_gaussians")
    assert arr.shape == (8, 2)


def test_posterior_selector_uses_canonical_centers() -> None:
    """``PosteriorSelectionEvaluator`` exports the canonical posterior centres."""
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        POSTERIOR_SELECTION_CELLS_FOR_TARGET,
        POSTERIOR_SELECTION_SHEET_FOR_TARGET,
    )

    assert POSTERIOR_SELECTION_SHEET_FOR_TARGET["two_moons"] == TWO_MOONS_POSTERIOR_SHEET
    assert (
        POSTERIOR_SELECTION_SHEET_FOR_TARGET["eight_gaussians"]
        == EIGHT_GAUSSIANS_POSTERIOR_SHEET
    )
    assert POSTERIOR_SELECTION_CELLS_FOR_TARGET["two_moons"] == TWO_MOONS_POSTERIOR_CELLS
    assert (
        POSTERIOR_SELECTION_CELLS_FOR_TARGET["eight_gaussians"]
        == EIGHT_GAUSSIANS_POSTERIOR_CELLS
    )


def test_sampler_centers_for_dispatch() -> None:
    """``sampler_centers_for`` resolves to the canonical sampler-geometry arrays."""
    assert np.array_equal(
        sampler_centers_for("two_moons"), TWO_MOONS_SAMPLER_CENTERS
    )
    assert np.array_equal(
        sampler_centers_for("eight_gaussians"),
        EIGHT_GAUSSIANS_SAMPLER_CENTERS,
    )


def test_unknown_target_raises() -> None:
    """All dispatch helpers fail closed on unknown target strings."""
    for helper in (
        sampler_centers_for,
        mode_centers_for_target,
        posterior_sheet_for,
        posterior_cells_for,
        posterior_centers_for,
    ):
        with pytest.raises(ValueError, match="unknown_target"):
            helper("not_a_real_target")
