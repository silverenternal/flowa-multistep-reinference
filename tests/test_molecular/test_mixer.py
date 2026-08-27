"""Tests for the molecule :class:`EqualRmsCoordinateMixer` (gap C1).

The molecule concrete mixer used to be called
``RMSPreservingCoordinateMixer``. That name overpromised: the RMS of the
*blend* is preserved only when the two input tensors share the same RMS
within ``1e-6``; otherwise the implementation silently rescales the
inputs. Gap C1 fixes that contract by:

* Renaming the class to :class:`EqualRmsCoordinateMixer`.
* Adding the audit code :data:`MIXER_RMS_PRECEDENCE_FAIL` that the
  blend emits when the precondition fails.
* Narrowing the docstring to state the precondition explicitly.

These tests pin the new contract.
"""

from __future__ import annotations

import math

import pytest

try:
    import torch
except Exception:  # pragma: no cover - optional dependency
    torch = None

pytestmark = pytest.mark.skipif(
    torch is None,
    reason="torch is required for the molecule coordinate mixer",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _centered_random(shape: tuple[int, int], *, rms: float, seed: int) -> torch.Tensor:
    """Return a centred random ``(N, 3)`` tensor with the requested RMS."""
    generator = torch.Generator().manual_seed(seed)
    raw = torch.randn(*shape, generator=generator)
    raw = raw - raw.mean(dim=0, keepdim=True)
    raw_rms = raw.square().sum(dim=-1).mean().sqrt()
    return raw * (rms / raw_rms.clamp_min(1e-12))


def _centred_rms(tensor: torch.Tensor) -> float:
    """Return the centred RMS of ``tensor`` (atoms, 3) along the last axis."""
    offsets = tensor - tensor.mean(dim=0, keepdim=True)
    return float(offsets.square().sum(dim=-1).mean().sqrt().detach().cpu())


# ---------------------------------------------------------------------------
# Tests: gap C1 fixes
# ---------------------------------------------------------------------------


class TestEqualRmsCoordinateMixer:
    """The renamed mixer MUST preserve RMS only when inputs share RMS."""

    def test_class_renamed_with_deprecated_alias(self) -> None:
        """``EqualRmsCoordinateMixer`` is the canonical name; the old name
        remains as a deprecated back-compat alias."""
        from adaptive_reflow.molecular.mixer import (
            EqualRmsCoordinateMixer,
            RMSPreservingCoordinateMixer,
        )

        assert EqualRmsCoordinateMixer is RMSPreservingCoordinateMixer, (
            "RMSPreservingCoordinateMixer must be a back-compat alias of "
            "EqualRmsCoordinateMixer"
        )

    def test_audit_code_constant_present(self) -> None:
        """The module-level audit code MUST exist with the canonical value."""
        from adaptive_reflow.molecular.mixer import MIXER_RMS_PRECEDENCE_FAIL

        assert MIXER_RMS_PRECEDENCE_FAIL == "mixer_rms_precondition_fail"

    def test_equal_rms_blend_preserves_rms(self) -> None:
        """Two RMS-equal inputs must come out with the same RMS as the prior.

        The class is named ``EqualRms`` because the RMS preservation only
        holds when the two input tensors share the same RMS within
        ``1e-6``. With matching RMS the prior's RMS is preserved.
        """
        from adaptive_reflow.molecular import EqualRmsCoordinateMixer

        target_rms = 1.7
        prior = _centered_random((8, 3), rms=target_rms, seed=1)
        memory = _centered_random((8, 3), rms=target_rms, seed=2)
        assert math.isclose(_centred_rms(prior), target_rms, abs_tol=1e-5)
        assert math.isclose(_centred_rms(memory), target_rms, abs_tol=1e-5)

        restart, ledger = EqualRmsCoordinateMixer().mix(
            prior=prior,
            memory=memory,
            beta=0.4,
        )

        # The blended tensor's RMS must equal the prior's RMS.
        assert math.isclose(
            _centred_rms(restart),
            _centred_rms(prior),
            abs_tol=1e-5,
        ), (
            f"expected restart RMS == prior RMS when inputs are RMS-equal; "
            f"got restart_rms={_centred_rms(restart)} prior_rms={_centred_rms(prior)}"
        )

        # The ledger must echo the same RMS through its pre/post diagnostics.
        assert math.isclose(
            float(ledger["adaptive_reflow_restart_rms"]),
            float(ledger["adaptive_reflow_prior_rms"]),
            abs_tol=1e-5,
        )
        # And no audit code should have been raised on a clean blend.
        assert "audit_codes" not in ledger or (
            "mixer_rms_precondition_fail" not in ledger["audit_codes"]
        )

    def test_unequal_rms_emits_precedence_fail(self) -> None:
        """Two RMS-different inputs MUST emit ``MIXER_RMS_PRECEDENCE_FAIL``.

        The audit code is propagated in the ledger's ``audit_codes`` list.
        """
        from adaptive_reflow.molecular import (
            MIXER_RMS_PRECEDENCE_FAIL,
            EqualRmsCoordinateMixer,
        )

        prior = _centered_random((8, 3), rms=0.5, seed=11)
        memory = _centered_random((8, 3), rms=2.5, seed=12)
        # Sanity check: inputs really do differ in RMS by more than tolerance.
        assert abs(_centred_rms(prior) - _centred_rms(memory)) > 1e-6

        restart, ledger = EqualRmsCoordinateMixer().mix(
            prior=prior,
            memory=memory,
            beta=0.5,
        )

        # The audit code MUST be present.
        assert "audit_codes" in ledger, (
            "ledger must carry an 'audit_codes' key when the RMS precondition fails"
        )
        assert MIXER_RMS_PRECEDENCE_FAIL in ledger["audit_codes"], (
            f"expected {MIXER_RMS_PRECEDENCE_FAIL!r} in audit codes; "
            f"got {ledger['audit_codes']!r}"
        )

    def test_deprecated_alias_emits_warning_on_mix(self) -> None:
        """Importing ``RMSPreservingCoordinateMixer`` must surface a
        :class:`DeprecationWarning` (it is the back-compat alias).

        The warning is raised at module-load time so we re-import the
        module via :mod:`importlib` to capture a fresh warning event.
        """
        import importlib
        import warnings

        from adaptive_reflow.molecular import mixer as mixer_module

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            importlib.reload(mixer_module)

        assert any(
            issubclass(w.category, DeprecationWarning)
            and "RMSPreservingCoordinateMixer" in str(w.message)
            for w in caught
        ), f"expected DeprecationWarning about RMSPreservingCoordinateMixer; got {[str(w.message) for w in caught]}"

    def test_precondition_helper_emits_when_differ(self) -> None:
        """``_require_equal_rms`` MUST append the audit code when RMS differ."""
        from adaptive_reflow.molecular.mixer import (
            MIXER_RMS_PRECEDENCE_FAIL,
            _require_equal_rms,
        )

        codes: list[str] = []
        memory = _centered_random((6, 3), rms=0.7, seed=21)
        restart = _centered_random((6, 3), rms=2.1, seed=22)

        memory_rms, restart_rms = _require_equal_rms(
            memory, restart, tolerance=1e-6, audit_codes=codes
        )

        assert math.isclose(memory_rms, 0.7, abs_tol=1e-5)
        assert math.isclose(restart_rms, 2.1, abs_tol=1e-5)
        assert codes == [MIXER_RMS_PRECEDENCE_FAIL]

    def test_precondition_helper_silent_when_equal(self) -> None:
        """``_require_equal_rms`` MUST NOT append the audit code when equal."""
        from adaptive_reflow.molecular.mixer import (
            _require_equal_rms,
        )

        codes: list[str] = []
        memory = _centered_random((6, 3), rms=1.3, seed=31)
        restart = _centered_random((6, 3), rms=1.3, seed=32)

        _require_equal_rms(memory, restart, tolerance=1e-6, audit_codes=codes)

        assert codes == []
