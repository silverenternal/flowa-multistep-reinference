"""Tests for the standard concrete mixers in adaptive_reflow.universal.mixer.

These three mixers are advertised by docs/ADAPTER_INTERFACE_SPEC.md §4.2
as the standard mixer implementations adapter authors can use out of
the box.
"""

from __future__ import annotations

import pytest

from adaptive_reflow.universal import (
    DiscreteIdentityMixer,
    LatentConvexMixer,
    NoOpMixer,
    validate_blend_inputs,
)

# ---------------------------------------------------------------------------
# NoOpMixer
# ---------------------------------------------------------------------------


class TestNoOpMixer:
    def test_returns_prior_regardless_of_beta(self):
        m = NoOpMixer()
        assert m.blend("prior-x", "endpoint-y", 0.0) == "prior-x"
        assert m.blend("prior-x", "endpoint-y", 0.5) == "prior-x"
        assert m.blend("prior-x", "endpoint-y", 1.0) == "prior-x"

    def test_returns_prior_when_endpoint_differs(self):
        m = NoOpMixer()
        assert m.blend("P", "E", 1.0) == "P"
        assert m.blend("P", "E", 0.0) == "P"

    def test_rejects_invalid_inputs(self):
        m = NoOpMixer()
        with pytest.raises(ValueError):
            m.blend("", "e", 0.5)
        with pytest.raises(ValueError):
            m.blend("p", "", 0.5)
        with pytest.raises(ValueError):
            m.blend("p", "e", 1.5)
        with pytest.raises(ValueError):
            m.blend("p", "e", -0.1)
        with pytest.raises(ValueError):
            m.blend("p", "e", float("nan"))


# ---------------------------------------------------------------------------
# LatentConvexMixer
# ---------------------------------------------------------------------------


class TestLatentConvexMixer:
    def test_default_returns_prior_when_no_native_fn(self):
        m = LatentConvexMixer()
        assert m.blend("p", "e", 0.3) == "p"

    def test_delegates_to_native_fn(self):
        calls = []

        def fake_native(prior, endpoint, beta):
            calls.append((prior, endpoint, beta))
            return f"convex({prior},{endpoint},{beta})"

        m = LatentConvexMixer(native_blend_fn=fake_native)
        out = m.blend("p", "e", 0.3)
        assert out == "convex(p,e,0.3)"
        assert calls == [("p", "e", 0.3)]

    def test_beta_boundaries_passed_through(self):
        m = LatentConvexMixer(native_blend_fn=lambda p, e, b: f"({p},{e},{b})")
        assert m.blend("p", "e", 0.0) == "(p,e,0.0)"
        assert m.blend("p", "e", 1.0) == "(p,e,1.0)"

    def test_rejects_invalid_inputs(self):
        m = LatentConvexMixer()
        with pytest.raises(ValueError):
            m.blend("", "e", 0.5)
        with pytest.raises(ValueError):
            m.blend("p", "e", 2.0)


# ---------------------------------------------------------------------------
# DiscreteIdentityMixer
# ---------------------------------------------------------------------------


class TestDiscreteIdentityMixer:
    def test_below_one_returns_prior(self):
        m = DiscreteIdentityMixer()
        assert m.blend("prior", "endpoint", 0.0) == "prior"
        assert m.blend("prior", "endpoint", 0.5) == "prior"
        assert m.blend("prior", "endpoint", 0.999) == "prior"

    def test_one_returns_endpoint(self):
        m = DiscreteIdentityMixer()
        assert m.blend("prior", "endpoint", 1.0) == "endpoint"

    def test_rejects_invalid_inputs(self):
        m = DiscreteIdentityMixer()
        with pytest.raises(ValueError):
            m.blend("", "e", 0.5)
        with pytest.raises(ValueError):
            m.blend("p", "e", 1.5)


# ---------------------------------------------------------------------------
# validate_blend_inputs
# ---------------------------------------------------------------------------


class TestValidateBlendInputs:
    def test_valid_inputs_pass(self):
        ok, errs = validate_blend_inputs("p", "e", 0.5)
        assert ok
        assert errs == ()

    def test_empty_prior_rejected(self):
        ok, errs = validate_blend_inputs("", "e", 0.5)
        assert not ok
        assert "prior" in errs[0]

    def test_empty_endpoint_rejected(self):
        ok, errs = validate_blend_inputs("p", "", 0.5)
        assert not ok
        assert "endpoint" in errs[0]

    def test_out_of_range_beta_rejected(self):
        ok, _ = validate_blend_inputs("p", "e", 1.5)
        assert not ok
        ok, _ = validate_blend_inputs("p", "e", -0.1)
        assert not ok

    def test_nan_beta_rejected(self):
        ok, errs = validate_blend_inputs("p", "e", float("nan"))
        assert not ok
        assert any("finite" in e for e in errs)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "--no-header", "-q"]))
