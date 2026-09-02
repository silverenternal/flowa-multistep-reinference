"""Per-channel state-type + blend-protocol tests (Design #3).

Two test modules verify the D5 + D9 surface:

1. ``test_state_channel.py`` — verifies the per-channel
   :class:`StateChannel` enum + :class:`StateShape` dataclass
   contract (validate, reject, back-compat). Lives in
   ``tests/test_contracts/``.

2. ``test_per_channel_blender.py`` — verifies the
   :class:`PerChannelBlender` dispatcher picks the correct
   :class:`BlendStrategy` per channel and emits the audit codes
   (short-circuit, sentinel passthrough, mask fallback, tau floor).
   Lives in ``tests/test_algorithm/``.

Both modules are stdlib + numpy only and exercise the contract
surface without depending on any concrete adapter.
"""

from __future__ import annotations

import pytest

from adaptive_reflow.contracts.state_channel import (
    STATE_CHANNELS,
    StateChannel,
    StateChannelKind,
    StateShape,
    validate_channel_types,
    validate_state_channel,
    validate_state_shape,
)
from adaptive_reflow.contracts.types import ChannelName


# ---------------------------------------------------------------------------
# StateChannel — closed enum
# ---------------------------------------------------------------------------


class TestStateChannelClosedSet:
    """Verify :data:`STATE_CHANNELS` is the canonical closed set."""

    def test_canonical_six_kinds(self) -> None:
        """Six kinds cover the LCM (continuous, mask, argmax, sample, mixed, graph)."""
        assert STATE_CHANNELS == (
            "continuous",
            "categorical_mask",
            "categorical_argmax",
            "categorical_sample",
            "mixed",
            "graph",
        )

    def test_literal_typing(self) -> None:
        """The :data:`StateChannelKind` literal aliases the closed set."""
        # Pure structural check — the literal is a typing construct.
        expected: tuple[StateChannelKind, ...] = (
            "continuous",
            "categorical_mask",
            "categorical_argmax",
            "categorical_sample",
            "mixed",
            "graph",
        )
        assert tuple(expected) == STATE_CHANNELS


class TestValidateStateChannel:
    """Verify :func:`validate_state_channel` accepts/rejects correctly."""

    @pytest.mark.parametrize("kind", list(STATE_CHANNELS))
    def test_accepts_closed_set(self, kind: StateChannel) -> None:
        ok, errs = validate_state_channel(kind)
        assert ok is True
        assert errs == ()

    @pytest.mark.parametrize(
        "value",
        ["", "unknown", "CONTINUOUS", "categorical", "Continuous", "GRAPH"],
    )
    def test_rejects_unknown_or_empty(self, value: str) -> None:
        ok, errs = validate_state_channel(value)
        assert ok is False
        assert len(errs) >= 1

    @pytest.mark.parametrize("value", [None, 0, 1, 1.0, True, False, [], {}])
    def test_rejects_non_str(self, value: object) -> None:
        ok, errs = validate_state_channel(value)  # type: ignore[arg-type]
        assert ok is False
        assert errs


# ---------------------------------------------------------------------------
# StateShape — per-channel shape with variable_axes indicator
# ---------------------------------------------------------------------------


class TestValidateStateShape:
    """Verify :func:`validate_state_shape` accepts/rejects correctly."""

    def test_default_is_empty_scalar(self) -> None:
        shape = StateShape()
        assert shape.dims == ()
        assert shape.variable_axes == ()
        ok, errs = validate_state_shape(shape)
        assert ok is True
        assert errs == ()

    def test_2d_continuous(self) -> None:
        shape = StateShape(dims=(2,))
        ok, errs = validate_state_shape(shape)
        assert ok is True

    def test_image_shape(self) -> None:
        shape = StateShape(dims=(3, 32, 32))
        ok, errs = validate_state_shape(shape)
        assert ok is True

    def test_variable_axes_marker(self) -> None:
        shape = StateShape(dims=(10, 3), variable_axes=(0,))
        ok, errs = validate_state_shape(shape)
        assert ok is True

    def test_rejects_negative_dim(self) -> None:
        shape = StateShape(dims=(-1,))
        ok, errs = validate_state_shape(shape)
        assert ok is False
        assert any("must_be_non_negative" in e for e in errs)

    def test_rejects_variable_axis_out_of_range(self) -> None:
        shape = StateShape(dims=(2,), variable_axes=(5,))
        ok, errs = validate_state_shape(shape)
        assert ok is False
        assert any("out_of_range" in e for e in errs)

    def test_rejects_duplicate_variable_axis(self) -> None:
        shape = StateShape(dims=(4, 4), variable_axes=(0, 0))
        ok, errs = validate_state_shape(shape)
        assert ok is False
        assert any("duplicate" in e for e in errs)

    def test_rejects_non_tuple_dims(self) -> None:
        shape = StateShape(dims=[2])  # type: ignore[arg-type]
        ok, errs = validate_state_shape(shape)
        assert ok is False
        assert any("must_be_tuple" in e for e in errs)


# ---------------------------------------------------------------------------
# validate_channel_types — per-adapter declaration table
# ---------------------------------------------------------------------------


class TestValidateChannelTypes:
    """Verify :func:`validate_channel_types` accepts/rejects correctly."""

    def test_accepts_empty_table(self) -> None:
        ok, errs = validate_channel_types({})
        assert ok is True
        assert errs == ()

    def test_accepts_well_typed_table(self) -> None:
        table: dict[ChannelName, StateChannel] = {
            ChannelName("coordinate"): "continuous",
            ChannelName("atom_type"): "categorical_mask",
            ChannelName("amino_acid"): "categorical_argmax",
            ChannelName("adjacency"): "graph",
        }
        ok, errs = validate_channel_types(table)
        assert ok is True

    def test_accepts_table_with_subset_of_supported(self) -> None:
        """Adapters MAY type-tag a subset of supported channels."""
        table: dict[ChannelName, StateChannel] = {
            ChannelName("coordinate"): "continuous",
        }
        supported = ("coordinate", "atom_type")
        ok, errs = validate_channel_types(
            table, supported_channels=supported
        )
        assert ok is True

    def test_rejects_key_not_in_supported(self) -> None:
        """A channel-type key not in supported_channels is rejected."""
        table: dict[ChannelName, StateChannel] = {
            ChannelName("rogue"): "continuous",
        }
        supported = ("coordinate",)
        ok, errs = validate_channel_types(table, supported_channels=supported)
        assert ok is False
        assert any("must appear in supported_channels" in e for e in errs)

    def test_rejects_unknown_kind(self) -> None:
        table: dict[ChannelName, StateChannel] = {
            ChannelName("coordinate"): "weird_kind",  # type: ignore[dict-item]
        }
        ok, errs = validate_channel_types(table)
        assert ok is False
        assert any("state_channel_unknown" in e for e in errs)
