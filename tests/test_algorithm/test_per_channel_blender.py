"""Per-channel blender dispatcher tests (Design #3 D9).

Verifies the :class:`PerChannelBlender` dispatcher picks the correct
:class:`BlendStrategy` per channel and emits the audit codes:

* short-circuit detection (``m=0`` / ``m=1``)
* sentinel passthrough (GraphBFN ``-inf`` diagonal)
* mask fallback (FlowMol3 padded positions)
* tau-floor degeneration (Gumbel-max → argmax)
* fall-through audit code for untyped channels

The tests exercise each concrete strategy (LinearBlend, LogitBlend,
MaskedBlend, GumbelBlend, SampleBlend, GraphBlend) via the
dispatcher and via the strategy directly.
"""

from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.algorithm.per_channel_blender import (
    BLEND_FAMILY_BY_CHANNEL,
    DEFAULT_BLEND_FAMILY_BY_CHANNEL,
    DEFAULT_TAU_FLOOR,
    GUMBEL_FAMILY,
    GRAPH_FAMILY,
    GumbelBlend,
    LINEAR_FAMILY,
    LinearBlend,
    LOGIT_FAMILY,
    LogitBlend,
    MASKED_FAMILY,
    MaskedBlend,
    PER_CHANNEL_BLEND_FALLTHROUGH,
    PER_CHANNEL_BLEND_MASK_FRESH_FALLBACK,
    PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT,
    PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT,
    PER_CHANNEL_BLEND_SENTINEL_PASSTHROUGH,
    PER_CHANNEL_BLEND_TAU_FLOOR_HIT,
    PerChannelBlender,
    SAMPLE_FAMILY,
    SampleBlend,
    BlendStrategy,
    GraphBlend,
    default_per_channel_blender,
)
from adaptive_reflow.contracts.state_channel import STATE_CHANNELS, StateChannel
from adaptive_reflow.contracts.types import ChannelName


# ---------------------------------------------------------------------------
# Concrete strategies — direct tests
# ---------------------------------------------------------------------------


class TestLinearBlend:
    """``LinearBlend`` is the canonical convex combination."""

    def test_family(self) -> None:
        assert LinearBlend().family() == LINEAR_FAMILY

    def test_convex_combination(self) -> None:
        prior = np.array([1.0, 2.0, 3.0])
        fresh = np.array([4.0, 5.0, 6.0])
        out = LinearBlend().blend(prior, fresh, memory_fraction=0.5)
        np.testing.assert_allclose(out, np.array([2.5, 3.5, 4.5]))

    def test_m_zero_shortcircuit_returns_fresh(self) -> None:
        prior = np.array([10.0, 20.0])
        fresh = np.array([1.0, 2.0])
        audits: list[str] = []
        out = LinearBlend().blend(
            prior, fresh, memory_fraction=0.0, audit_codes=audits
        )
        np.testing.assert_array_equal(out, fresh)
        assert any(PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT in a for a in audits)

    def test_m_one_shortcircuit_returns_prior(self) -> None:
        prior = np.array([10.0, 20.0])
        fresh = np.array([1.0, 2.0])
        audits: list[str] = []
        out = LinearBlend().blend(
            prior, fresh, memory_fraction=1.0, audit_codes=audits
        )
        np.testing.assert_array_equal(out, prior)
        assert any(PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT in a for a in audits)

    def test_shape_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="shape_mismatch"):
            LinearBlend().blend(
                np.array([1.0]), np.array([1.0, 2.0]), memory_fraction=0.5
            )


class TestLogitBlend:
    """``LogitBlend`` lifts to softmax + returns ``argmax``."""

    def test_family(self) -> None:
        assert LogitBlend().family() == LOGIT_FAMILY

    def test_argmax_on_blended_softmax(self) -> None:
        # Two-row logits, prior favours index 0, fresh favours index 1.
        prior = np.array([[2.0, 0.5], [0.5, 2.0]])
        fresh = np.array([[0.5, 2.0], [2.0, 0.5]])
        out = LogitBlend().blend(prior, fresh, memory_fraction=0.5)
        # Blended = [1.25, 1.25] then [1.25, 1.25] — argmax ties to index 0.
        np.testing.assert_array_equal(out, np.array([0, 0]))

    def test_m_zero_returns_argmax_fresh(self) -> None:
        prior = np.array([[0.0, 100.0]])
        fresh = np.array([[100.0, 0.0]])
        audits: list[str] = []
        out = LogitBlend().blend(
            prior, fresh, memory_fraction=0.0, audit_codes=audits
        )
        np.testing.assert_array_equal(out, np.array([0]))
        assert any(PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT in a for a in audits)

    def test_m_one_returns_argmax_prior(self) -> None:
        prior = np.array([[0.0, 100.0]])
        fresh = np.array([[100.0, 0.0]])
        audits: list[str] = []
        out = LogitBlend().blend(
            prior, fresh, memory_fraction=1.0, audit_codes=audits
        )
        np.testing.assert_array_equal(out, np.array([1]))
        assert any(PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT in a for a in audits)


class TestMaskedBlend:
    """``MaskedBlend`` dodges ``0 * -inf = NaN`` with m=0/1 short-circuit + sentinel passthrough."""

    def test_family(self) -> None:
        assert MaskedBlend().family() == MASKED_FAMILY

    def test_m_zero_returns_fresh_with_sentinel(self) -> None:
        prior = np.array([[1.0, 2.0], [3.0, -np.inf]])
        fresh = np.array([[10.0, 20.0], [30.0, 40.0]])
        audits: list[str] = []
        out = MaskedBlend().blend(
            prior, fresh, memory_fraction=0.0, audit_codes=audits
        )
        # m=0 path: fresh with sentinel passthrough.
        np.testing.assert_allclose(out[0], fresh[0])
        assert out[1, 1] == -np.inf  # sentinel passthrough
        assert any(PER_CHANNEL_BLEND_SENTINEL_PASSTHROUGH in a for a in audits)
        assert any(PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT in a for a in audits)

    def test_m_one_returns_prior_unchanged(self) -> None:
        prior = np.array([[1.0, 2.0], [3.0, -np.inf]])
        fresh = np.array([[10.0, 20.0], [30.0, 40.0]])
        audits: list[str] = []
        out = MaskedBlend().blend(
            prior, fresh, memory_fraction=1.0, audit_codes=audits
        )
        # m=1 path: prior verbatim (with sentinel kept).
        np.testing.assert_array_equal(out, prior)
        assert any(PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT in a for a in audits)

    def test_m_zero_shortcircuit_prevents_nan_on_diag(self) -> None:
        """D9 short-circuit semantics: m=0 returns fresh; the
        ``0 * -inf`` product at the diagonal is NEVER computed."""
        prior = np.array([[1.0, -np.inf], [-np.inf, 2.0]])
        fresh = np.array([[0.0, 0.0], [0.0, 0.0]])
        out = MaskedBlend().blend(prior, fresh, memory_fraction=0.0)
        # Diagonal sentinel positions keep -inf (sentinel passthrough).
        assert out[0, 1] == -np.inf
        assert out[1, 0] == -np.inf
        assert not np.any(np.isnan(out))

    def test_m_one_shortcircuit_prevents_nan_on_diag(self) -> None:
        prior = np.array([[1.0, -np.inf], [-np.inf, 2.0]])
        fresh = np.array([[0.0, 0.0], [0.0, 0.0]])
        out = MaskedBlend().blend(prior, fresh, memory_fraction=1.0)
        assert out[0, 1] == -np.inf
        assert out[1, 0] == -np.inf
        assert not np.any(np.isnan(out))

    def test_mask_zero_falls_back_to_fresh(self) -> None:
        """FlowMol3 padded positions (mask=0) take the fresh draw."""
        prior = np.array([1.0, 2.0, 3.0])
        fresh = np.array([10.0, 20.0, 30.0])
        mask = np.array([1.0, 0.0, 1.0])
        audits: list[str] = []
        out = MaskedBlend().blend(
            prior, fresh, memory_fraction=0.5, mask=mask, audit_codes=audits
        )
        # Position 1 (mask=0) takes fresh; positions 0, 2 blended.
        np.testing.assert_allclose(out, np.array([5.5, 20.0, 16.5]))
        assert any(PER_CHANNEL_BLEND_MASK_FRESH_FALLBACK in a for a in audits)

    def test_rejects_mask_shape_mismatch(self) -> None:
        with pytest.raises(ValueError, match="mask_shape_mismatch"):
            MaskedBlend().blend(
                np.array([1.0, 2.0]),
                np.array([3.0, 4.0]),
                memory_fraction=0.5,
                mask=np.array([1.0]),
            )


class TestGumbelBlend:
    """``GumbelBlend`` samples via Gumbel-max with tau schedule."""

    def test_family(self) -> None:
        assert GumbelBlend().family() == GUMBEL_FAMILY

    def test_tau_floor_hits_argmax(self) -> None:
        """Below tau_floor the sampler degenerates to argmax."""
        prior = np.array([[1.0, 100.0]])
        fresh = np.array([[100.0, 1.0]])
        audits: list[str] = []
        out = GumbelBlend().blend(
            prior,
            fresh,
            memory_fraction=0.5,
            tau=DEFAULT_TAU_FLOOR / 2.0,  # below floor
            audit_codes=audits,
        )
        # Blended = [50.5, 50.5] → tie → argmax returns first index.
        np.testing.assert_array_equal(out, np.array([0]))
        assert any(PER_CHANNEL_BLEND_TAU_FLOOR_HIT in a for a in audits)

    def test_m_zero_returns_argmax_fresh(self) -> None:
        prior = np.array([[0.0, 100.0]])
        fresh = np.array([[100.0, 0.0]])
        out = GumbelBlend().blend(prior, fresh, memory_fraction=0.0)
        np.testing.assert_array_equal(out, np.array([0]))

    def test_m_one_returns_argmax_prior(self) -> None:
        prior = np.array([[0.0, 100.0]])
        fresh = np.array([[100.0, 0.0]])
        out = GumbelBlend().blend(prior, fresh, memory_fraction=1.0)
        np.testing.assert_array_equal(out, np.array([1]))

    def test_invalid_tau_floor(self) -> None:
        with pytest.raises(ValueError, match="tau_floor_must_be_positive"):
            GumbelBlend(tau_floor=0.0)


class TestSampleBlend:
    """``SampleBlend`` returns fresh verbatim (uniform-Categorical)."""

    def test_family(self) -> None:
        assert SampleBlend().family() == SAMPLE_FAMILY

    def test_returns_fresh(self) -> None:
        prior = np.array([1.0, 2.0, 3.0])
        fresh = np.array([10.0, 20.0, 30.0])
        out = SampleBlend().blend(prior, fresh, memory_fraction=0.5)
        np.testing.assert_array_equal(out, fresh)


class TestGraphBlend:
    """``GraphBlend`` delegates to per-sub-tensor strategies."""

    def test_family(self) -> None:
        assert GraphBlend().family() == GRAPH_FAMILY

    def test_per_subtensor_blend(self) -> None:
        prior = {
            "theta_node": np.array([1.0, 2.0]),
            "theta_edge": np.array([3.0, 4.0]),
            "adj_logits": np.array([[1.0, -np.inf], [-np.inf, 1.0]]),
        }
        fresh = {
            "theta_node": np.array([10.0, 20.0]),
            "theta_edge": np.array([30.0, 40.0]),
            "adj_logits": np.array([[2.0, 0.0], [0.0, 2.0]]),
        }
        out = GraphBlend().blend(prior, fresh, memory_fraction=0.5)
        # theta_node / theta_edge use LinearBlend (m=0.5).
        np.testing.assert_allclose(out["theta_node"], np.array([5.5, 11.0]))
        np.testing.assert_allclose(out["theta_edge"], np.array([16.5, 22.0]))
        # adj_logits uses MaskedBlend; diagonal sentinel kept.
        assert out["adj_logits"][0, 1] == -np.inf
        assert out["adj_logits"][1, 0] == -np.inf

    def test_rejects_non_mapping(self) -> None:
        with pytest.raises(ValueError, match="graph_blend_requires_mapping_subtensors"):
            GraphBlend().blend(
                np.array([1.0]), np.array([2.0]), memory_fraction=0.5
            )

    def test_rejects_missing_subtensor(self) -> None:
        with pytest.raises(ValueError, match="graph_blend_missing_subtensor"):
            GraphBlend().blend(
                {"theta_node": np.array([1.0])},
                {"theta_node": np.array([2.0])},
                memory_fraction=0.5,
            )


# ---------------------------------------------------------------------------
# PerChannelBlender — dispatcher
# ---------------------------------------------------------------------------


class TestBlendStrategyProtocol:
    """Verify the :class:`BlendStrategy` Protocol is structural."""

    def test_linear_is_strategy(self) -> None:
        assert isinstance(LinearBlend(), BlendStrategy)

    def test_logit_is_strategy(self) -> None:
        assert isinstance(LogitBlend(), BlendStrategy)

    def test_masked_is_strategy(self) -> None:
        assert isinstance(MaskedBlend(), BlendStrategy)

    def test_gumbel_is_strategy(self) -> None:
        assert isinstance(GumbelBlend(), BlendStrategy)

    def test_sample_is_strategy(self) -> None:
        assert isinstance(SampleBlend(), BlendStrategy)

    def test_graph_is_strategy(self) -> None:
        assert isinstance(GraphBlend(), BlendStrategy)


class TestDefaultFamilyTable:
    """Verify the canonical :data:`DEFAULT_BLEND_FAMILY_BY_CHANNEL` table."""

    def test_canonical_mapping(self) -> None:
        assert DEFAULT_BLEND_FAMILY_BY_CHANNEL == BLEND_FAMILY_BY_CHANNEL

    def test_covers_every_kind(self) -> None:
        for kind in STATE_CHANNELS:
            assert kind in DEFAULT_BLEND_FAMILY_BY_CHANNEL, (
                f"missing default family for {kind}"
            )

    def test_continuous_to_linear(self) -> None:
        assert DEFAULT_BLEND_FAMILY_BY_CHANNEL["continuous"] == LINEAR_FAMILY

    def test_categorical_argmax_to_logit(self) -> None:
        assert (
            DEFAULT_BLEND_FAMILY_BY_CHANNEL["categorical_argmax"] == LOGIT_FAMILY
        )

    def test_categorical_mask_to_masked(self) -> None:
        assert (
            DEFAULT_BLEND_FAMILY_BY_CHANNEL["categorical_mask"] == MASKED_FAMILY
        )

    def test_categorical_sample_to_gumbel(self) -> None:
        assert (
            DEFAULT_BLEND_FAMILY_BY_CHANNEL["categorical_sample"] == GUMBEL_FAMILY
        )

    def test_graph_to_graph(self) -> None:
        assert DEFAULT_BLEND_FAMILY_BY_CHANNEL["graph"] == GRAPH_FAMILY


class TestPerChannelBlenderDispatch:
    """Verify the dispatcher picks the correct :class:`BlendStrategy` per channel."""

    def test_continuous_channel_uses_linear(self) -> None:
        types: dict[ChannelName, StateChannel] = {
            ChannelName("coordinate"): "continuous",
        }
        blender = PerChannelBlender(channel_types=types)
        assert blender.strategy_for(ChannelName("coordinate")).family() == LINEAR_FAMILY

    def test_argmax_channel_uses_logit(self) -> None:
        types: dict[ChannelName, StateChannel] = {
            ChannelName("amino_acid"): "categorical_argmax",
        }
        blender = PerChannelBlender(channel_types=types)
        assert blender.strategy_for(ChannelName("amino_acid")).family() == LOGIT_FAMILY

    def test_mask_channel_uses_masked(self) -> None:
        types: dict[ChannelName, StateChannel] = {
            ChannelName("atom_type"): "categorical_mask",
        }
        blender = PerChannelBlender(channel_types=types)
        assert blender.strategy_for(ChannelName("atom_type")).family() == MASKED_FAMILY

    def test_sample_channel_uses_gumbel(self) -> None:
        types: dict[ChannelName, StateChannel] = {
            ChannelName("bond_type"): "categorical_sample",
        }
        blender = PerChannelBlender(channel_types=types)
        assert blender.strategy_for(ChannelName("bond_type")).family() == GUMBEL_FAMILY

    def test_graph_channel_uses_graph(self) -> None:
        types: dict[ChannelName, StateChannel] = {
            ChannelName("graph"): "graph",
        }
        blender = PerChannelBlender(channel_types=types)
        assert blender.strategy_for(ChannelName("graph")).family() == GRAPH_FAMILY

    def test_untyped_channel_falls_through_to_linear(self) -> None:
        """Channel not in the type table → LinearBlend (back-compat)."""
        types: dict[ChannelName, StateChannel] = {
            ChannelName("coordinate"): "continuous",
        }
        blender = PerChannelBlender(channel_types=types)
        assert (
            blender.strategy_for(ChannelName("untyped_channel")).family()
            == LINEAR_FAMILY
        )

    def test_no_table_falls_through_to_linear(self) -> None:
        blender = PerChannelBlender(channel_types=None)
        assert (
            blender.strategy_for(ChannelName("anything")).family() == LINEAR_FAMILY
        )

    def test_family_override_takes_precedence(self) -> None:
        """Caller can override the channel-kind → family lookup."""
        types: dict[ChannelName, StateChannel] = {
            ChannelName("atom_type"): "categorical_mask",
        }
        overrides = {ChannelName("atom_type"): GUMBEL_FAMILY}
        blender = PerChannelBlender(
            channel_types=types, family_overrides=overrides
        )
        assert (
            blender.strategy_for(ChannelName("atom_type")).family() == GUMBEL_FAMILY
        )

    def test_rejects_unknown_kind_in_table(self) -> None:
        with pytest.raises(ValueError, match="invalid channel_types"):
            PerChannelBlender(
                channel_types={ChannelName("foo"): "weird_kind"}  # type: ignore[dict-item]
            )


class TestPerChannelBlenderBlendChannel:
    """Verify ``blend_channel`` dispatches + emits the audit codes."""

    def test_dispatch_to_correct_strategy(self) -> None:
        types: dict[ChannelName, StateChannel] = {
            ChannelName("coord"): "continuous",
            ChannelName("amino"): "categorical_argmax",
        }
        blender = PerChannelBlender(channel_types=types)

        # Continuous channel gets LinearBlend math.
        out_coord = blender.blend_channel(
            ChannelName("coord"),
            np.array([1.0, 2.0]),
            np.array([3.0, 4.0]),
            memory_fraction=0.5,
        )
        np.testing.assert_allclose(out_coord, np.array([2.0, 3.0]))

        # Argmax channel gets LogitBlend math.
        out_amino = blender.blend_channel(
            ChannelName("amino"),
            np.array([[0.0, 100.0]]),
            np.array([[100.0, 0.0]]),
            memory_fraction=0.0,
        )
        np.testing.assert_array_equal(out_amino, np.array([0]))

    def test_untyped_channel_emits_fallthrough_audit(self) -> None:
        blender = PerChannelBlender(channel_types=None)
        audits: list[str] = []
        blender.blend_channel(
            ChannelName("untyped"),
            np.array([1.0]),
            np.array([2.0]),
            memory_fraction=0.5,
            audit_codes=audits,
        )
        assert any(PER_CHANNEL_BLEND_FALLTHROUGH in a for a in audits)


class TestPerChannelBlenderBlendAllChannels:
    """Verify ``blend_all_channels`` dispatches every channel independently."""

    def test_dispatches_per_channel(self) -> None:
        types: dict[ChannelName, StateChannel] = {
            ChannelName("coord"): "continuous",
            ChannelName("amino"): "categorical_argmax",
            ChannelName("atom_type"): "categorical_mask",
        }
        blender = PerChannelBlender(channel_types=types)

        prior = {
            ChannelName("coord"): np.array([1.0, 2.0]),
            ChannelName("amino"): np.array([[0.0, 100.0]]),
            ChannelName("atom_type"): np.array([5.0, 6.0]),
        }
        fresh = {
            ChannelName("coord"): np.array([3.0, 4.0]),
            ChannelName("amino"): np.array([[100.0, 0.0]]),
            ChannelName("atom_type"): np.array([50.0, 60.0]),
        }
        memory = {
            ChannelName("coord"): 0.5,
            ChannelName("amino"): 0.0,
            ChannelName("atom_type"): 1.0,
        }
        out = blender.blend_all_channels(prior, fresh, memory_fraction_by_channel=memory)

        np.testing.assert_allclose(out[ChannelName("coord")], np.array([2.0, 3.0]))
        np.testing.assert_array_equal(out[ChannelName("amino")], np.array([0]))
        np.testing.assert_array_equal(out[ChannelName("atom_type")], np.array([5.0, 6.0]))

    def test_rejects_missing_fresh(self) -> None:
        types: dict[ChannelName, StateChannel] = {ChannelName("x"): "continuous"}
        blender = PerChannelBlender(channel_types=types)
        with pytest.raises(ValueError, match="fresh_value_missing_for_channel"):
            blender.blend_all_channels(
                {ChannelName("x"): np.array([1.0])},
                {},
                memory_fraction_by_channel={ChannelName("x"): 0.5},
            )

    def test_rejects_missing_memory_fraction(self) -> None:
        types: dict[ChannelName, StateChannel] = {ChannelName("x"): "continuous"}
        blender = PerChannelBlender(channel_types=types)
        with pytest.raises(ValueError, match="memory_fraction_missing_for_channel"):
            blender.blend_all_channels(
                {ChannelName("x"): np.array([1.0])},
                {ChannelName("x"): np.array([2.0])},
                memory_fraction_by_channel={},
            )


class TestDefaultFactory:
    """Verify :func:`default_per_channel_blender` factory."""

    def test_default_no_table(self) -> None:
        blender = default_per_channel_blender()
        assert blender.channel_types is None

    def test_default_with_table(self) -> None:
        types: dict[ChannelName, StateChannel] = {
            ChannelName("x"): "continuous",
        }
        blender = default_per_channel_blender(channel_types=types)
        assert blender.channel_types == types
