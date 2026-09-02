"""Pytest suite for the typed :class:`Condition` discriminated union (D8).

These tests verify:

1. Each concrete :class:`Condition` subclass (Null / CFG / Inpainting /
   BFNInpaint / Property) has a stable ``condition_kind`` discriminator
   and a faithful ``to_mapping()`` wire form.

2. :class:`MappingConditionAdapter` preserves the legacy back-compat
   contract: dict-based ``delta_spec`` continues to work, including
   dict-style ``.get(key, default)``, ``[key]``, ``"key" in spec``,
   ``iter(spec)``, ``len(spec)``, and ``.items()``.

3. :class:`ODEConditionDelta` constructor auto-wraps raw mappings
   into :class:`MappingConditionAdapter` so the type change from
   ``Mapping[str, Any]`` to :class:`Condition` is non-breaking.

4. :func:`validate_condition_delta` accepts typed Conditions and rejects
   empty spec (including empty MappingConditionAdapter).

5. :func:`wrap_condition`, :func:`condition_to_mapping`,
   :func:`condition_kind_of` provide the canonical conversion helpers.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from adaptive_reflow.contracts.condition import (
    BFNInpaintCondition,
    CFGCondition,
    CONDITION_KINDS,
    Condition,
    InpaintingCondition,
    MappingConditionAdapter,
    NullCondition,
    PropertyCondition,
    condition_kind_of,
    condition_to_mapping,
    validate_condition,
    wrap_condition,
)
from adaptive_reflow.universal.state import ODEConditionDelta, validate_condition_delta


# ---------------------------------------------------------------------------
# (1) Concrete Condition subclasses — discriminator + wire form
# ---------------------------------------------------------------------------


def test_null_condition_discriminator_and_wire_form() -> None:
    cond = NullCondition(dataset="flowmol3_smiles_pl", variant="v1")
    assert cond.condition_kind == "null"
    mapping = cond.to_mapping()
    assert mapping["condition_kind"] == "null"
    assert mapping["dataset"] == "flowmol3_smiles_pl"
    assert mapping["variant"] == "v1"
    assert mapping["round_trace_only"] is True


def test_null_condition_empty_dataset_raises() -> None:
    with pytest.raises(ValueError, match="dataset_must_be_non_empty_str"):
        NullCondition(dataset="", variant="v1")


def test_null_condition_empty_variant_raises() -> None:
    with pytest.raises(ValueError, match="variant_must_be_non_empty_str"):
        NullCondition(dataset="d", variant="")


def test_cfg_condition_discriminator_and_wire_form() -> None:
    cond = CFGCondition(
        text_prompt="a cat",
        negative_prompt="blurry",
        guidance_scale=7.5,
        cfg_trunc_ratio=0.92,
        cfg_normalization="lumina",
        rope_axes=(16, 16),
    )
    assert cond.condition_kind == "cfg"
    mapping = cond.to_mapping()
    assert mapping["condition_kind"] == "cfg"
    assert mapping["text_prompt"] == "a cat"
    assert mapping["negative_prompt"] == "blurry"
    assert mapping["guidance_scale"] == 7.5
    assert mapping["cfg_trunc_ratio"] == 0.92
    assert mapping["cfg_normalization"] == "lumina"
    assert mapping["rope_axes"] == (16, 16)


def test_cfg_condition_rejects_negative_guidance_scale() -> None:
    with pytest.raises(ValueError, match="guidance_scale_must_be_non_negative"):
        CFGCondition(text_prompt="x", guidance_scale=-1.0)


def test_cfg_condition_rejects_out_of_range_trunc_ratio() -> None:
    with pytest.raises(ValueError, match="cfg_trunc_ratio_must_be_in_"):
        CFGCondition(text_prompt="x", cfg_trunc_ratio=1.5)


def test_cfg_condition_rejects_unknown_normalization() -> None:
    with pytest.raises(ValueError, match="cfg_normalization_must_be"):
        CFGCondition(text_prompt="x", cfg_normalization="bogus")


def test_inpainting_condition_discriminator_and_wire_form() -> None:
    cond = InpaintingCondition(
        positions=(0, 2, 5),
        strength=0.5,
        n_particles=8,
        num_steps=20,
        model_family="abbfn",
    )
    assert cond.condition_kind == "inpainting"
    mapping = cond.to_mapping()
    assert mapping["condition_kind"] == "inpainting"
    assert mapping["positions"] == (0, 2, 5)
    assert mapping["strength"] == 0.5
    assert mapping["n_particles"] == 8
    assert mapping["num_steps"] == 20
    assert mapping["model_family"] == "abbfn"


def test_inpainting_condition_rejects_unknown_model_family() -> None:
    with pytest.raises(ValueError, match="model_family_must_be"):
        InpaintingCondition(positions=(0,), model_family="bogus")


def test_inpainting_condition_rejects_out_of_range_strength() -> None:
    with pytest.raises(ValueError, match="strength_must_be_in_"):
        InpaintingCondition(positions=(0,), strength=1.5)


def test_inpainting_condition_rejects_zero_particles() -> None:
    with pytest.raises(ValueError, match="n_particles_must_be_positive_int"):
        InpaintingCondition(positions=(0,), n_particles=0)


def test_bfn_inpaint_condition_discriminator_and_wire_form() -> None:
    cond = BFNInpaintCondition(slot_index=5, n_particles=10, t_grid_len=32)
    assert cond.condition_kind == "bfn_inpaint"
    mapping = cond.to_mapping()
    assert mapping["condition_kind"] == "bfn_inpaint"
    assert mapping["slot_index"] == 5
    assert mapping["n_particles"] == 10
    assert mapping["t_grid_len"] == 32


def test_bfn_inpaint_condition_rejects_negative_slot_index() -> None:
    with pytest.raises(ValueError, match="slot_index_must_be_non_negative_int"):
        BFNInpaintCondition(slot_index=-1)


def test_property_condition_logp() -> None:
    cond = PropertyCondition(property_kind="logp", property_value=2.5)
    assert cond.condition_kind == "property"
    assert cond.to_mapping()["property_value"] == 2.5


def test_property_condition_qed_in_range() -> None:
    cond = PropertyCondition(property_kind="qed", property_value=0.85)
    assert cond.to_mapping()["property_value"] == 0.85


def test_property_condition_qed_out_of_range_rejects() -> None:
    with pytest.raises(ValueError, match="property_value_for_qed_must_be_in_"):
        PropertyCondition(property_kind="qed", property_value=1.5)


def test_property_condition_sa_out_of_range_rejects() -> None:
    with pytest.raises(ValueError, match="property_value_for_sa_must_be_in_"):
        PropertyCondition(property_kind="sa", property_value=0.5)


def test_property_condition_unknown_kind_rejects() -> None:
    with pytest.raises(ValueError, match="property_kind_must_be"):
        PropertyCondition(property_kind="bogus", property_value=0.0)


def test_all_concrete_conditions_implement_protocol() -> None:
    """Each concrete Condition MUST isinstance check as Condition."""
    for cond in (
        NullCondition(),
        CFGCondition(text_prompt="x"),
        InpaintingCondition(positions=(0,)),
        BFNInpaintCondition(slot_index=0),
        PropertyCondition(property_kind="qed", property_value=0.5),
    ):
        assert isinstance(cond, Condition)
        assert cond.condition_kind in CONDITION_KINDS


# ---------------------------------------------------------------------------
# (2) MappingConditionAdapter back-compat surface
# ---------------------------------------------------------------------------


def test_mapping_adapter_from_mapping_preserves_keys() -> None:
    raw = {"num_steps": 100, "source_key": "value"}
    adapter = MappingConditionAdapter.from_mapping(raw)
    assert isinstance(adapter, Condition)
    # Underlying data is preserved verbatim via duck-typed mapping methods.
    assert adapter.get("num_steps") == 100
    assert adapter.get("missing", "default") == "default"
    assert adapter["source_key"] == "value"
    assert "num_steps" in adapter
    assert sorted(iter(adapter)) == ["num_steps", "source_key"]
    assert len(adapter) == 2
    assert dict(adapter.items()) == {"num_steps": 100, "source_key": "value"}


def test_mapping_adapter_default_kind_is_mapping() -> None:
    adapter = MappingConditionAdapter.from_mapping({"k": "v"})
    assert adapter.condition_kind == "mapping"
    # to_mapping() injects condition_kind when absent in the
    # underlying data — wire form is stable.
    assert adapter.to_mapping()["condition_kind"] == "mapping"


def test_mapping_adapter_respects_explicit_kind() -> None:
    adapter = MappingConditionAdapter.from_mapping(
        {"condition_kind": "null", "dataset": "x"}
    )
    assert adapter.condition_kind == "null"
    assert adapter.to_mapping()["condition_kind"] == "null"


def test_mapping_adapter_rejects_non_mapping_data() -> None:
    with pytest.raises(ValueError, match="_data_must_be_mapping"):
        MappingConditionAdapter(_data=42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# (3) ODEConditionDelta auto-wrap + typed-passthrough
# ---------------------------------------------------------------------------


def test_ode_condition_delta_accepts_typed_condition() -> None:
    cond = CFGCondition(text_prompt="x")
    delta = ODEConditionDelta(
        delta_spec=cond,
        source="engine",
        target_round=3,
        calibration_artifact_hash="cal-v1",
    )
    assert delta.delta_spec is cond  # typed Condition passes through unchanged


def test_ode_condition_delta_auto_wraps_dict_to_mapping_adapter() -> None:
    raw = {"num_steps": 100, "source_key": "source_value"}
    delta = ODEConditionDelta(
        delta_spec=raw,
        source="engine",
        target_round=5,
        calibration_artifact_hash="cal-v2",
    )
    assert isinstance(delta.delta_spec, MappingConditionAdapter)
    assert delta.delta_spec.condition_kind == "mapping"
    assert delta.delta_spec.get("num_steps") == 100


def test_ode_condition_delta_preserves_typed_round_and_hash() -> None:
    cond = NullCondition(dataset="d", variant="v")
    delta = ODEConditionDelta(
        delta_spec=cond,
        source="engine",
        target_round=7,
        calibration_artifact_hash="cal-h-7",
    )
    assert delta.target_round == 7
    assert delta.calibration_artifact_hash == "cal-h-7"


# ---------------------------------------------------------------------------
# (4) validate_condition_delta + validate_condition
# ---------------------------------------------------------------------------


def test_validate_condition_delta_accepts_typed_condition() -> None:
    cond = InpaintingCondition(positions=(0, 1, 2), strength=0.7)
    delta = ODEConditionDelta(
        delta_spec=cond,
        source="engine",
        target_round=3,
        calibration_artifact_hash="cal-v1",
    )
    ok, errors = validate_condition_delta(delta)
    assert ok is True
    assert errors == ()


def test_validate_condition_delta_rejects_empty_dict() -> None:
    delta = ODEConditionDelta(
        delta_spec={},
        source="x",
        target_round=1,
        calibration_artifact_hash="abc",
    )
    ok, errors = validate_condition_delta(delta)
    assert ok is False
    assert "delta_spec_must_be_non_empty_mapping" in errors


def test_validate_condition_delta_rejects_empty_mapping_adapter() -> None:
    """Even after auto-wrap, an empty MappingConditionAdapter is rejected."""
    delta = ODEConditionDelta(
        delta_spec=MappingConditionAdapter(_data={}),
        source="x",
        target_round=1,
        calibration_artifact_hash="abc",
    )
    ok, errors = validate_condition_delta(delta)
    assert ok is False
    assert "delta_spec_must_be_non_empty_mapping" in errors


def test_validate_condition_accepts_concrete_kinds() -> None:
    for cond in (
        NullCondition(),
        CFGCondition(text_prompt="x"),
        InpaintingCondition(positions=(0,)),
        BFNInpaintCondition(slot_index=0),
        PropertyCondition(property_kind="qed", property_value=0.5),
    ):
        ok, errors = validate_condition(cond)
        assert ok is True, f"{type(cond).__name__} failed: {errors}"


def test_validate_condition_rejects_none() -> None:
    ok, errors = validate_condition(None)  # type: ignore[arg-type]
    assert ok is False
    assert "condition_must_not_be_none" in errors


# ---------------------------------------------------------------------------
# (5) Helpers — wrap_condition / condition_to_mapping / condition_kind_of
# ---------------------------------------------------------------------------


def test_wrap_condition_with_dict_returns_mapping_adapter() -> None:
    wrapped = wrap_condition({"a": 1})
    assert isinstance(wrapped, MappingConditionAdapter)
    assert wrapped.condition_kind == "mapping"


def test_wrap_condition_with_condition_returns_it_unchanged() -> None:
    cond = CFGCondition(text_prompt="x")
    wrapped = wrap_condition(cond)
    assert wrapped is cond


def test_wrap_condition_with_non_condition_non_mapping_raises() -> None:
    with pytest.raises(TypeError, match="condition_must_be_Condition_or_Mapping"):
        wrap_condition(42)  # type: ignore[arg-type]


def test_condition_to_mapping_serializes_typed() -> None:
    cond = CFGCondition(text_prompt="x", guidance_scale=5.0)
    mapping = condition_to_mapping(cond)
    assert mapping["condition_kind"] == "cfg"
    assert mapping["guidance_scale"] == 5.0


def test_condition_to_mapping_rejects_non_condition() -> None:
    with pytest.raises(TypeError, match="condition_must_implement_Condition_protocol"):
        condition_to_mapping("not a condition")  # type: ignore[arg-type]


def test_condition_kind_of_typed() -> None:
    cond = PropertyCondition(property_kind="qed", property_value=0.5)
    assert condition_kind_of(cond) == "property"


def test_condition_kind_of_mapping_returns_inner_kind() -> None:
    assert condition_kind_of({"condition_kind": "null"}) == "null"
    assert condition_kind_of({"k": "v"}) == "mapping"


def test_condition_kind_of_rejects_non_condition_non_mapping() -> None:
    with pytest.raises(TypeError, match="condition_kind_of_requires"):
        condition_kind_of(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# (6) Round-trip via dict serialization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cond",
    [
        NullCondition(dataset="d1", variant="v1"),
        CFGCondition(text_prompt="x", guidance_scale=7.0, cfg_normalization="lumina"),
        InpaintingCondition(positions=(0, 2), strength=0.5, model_family="abbfn2"),
        BFNInpaintCondition(slot_index=3, n_particles=8, t_grid_len=16),
        PropertyCondition(property_kind="logp", property_value=2.0),
    ],
)
def test_roundtrip_through_ode_condition_delta(cond: Condition) -> None:
    """Each Condition subclass roundtrips through ODEConditionDelta intact."""
    delta = ODEConditionDelta(
        delta_spec=cond,
        source="engine",
        target_round=3,
        calibration_artifact_hash="cal-v1",
    )
    assert delta.delta_spec is cond
    assert delta.delta_spec.condition_kind == cond.condition_kind
    assert condition_to_mapping(delta.delta_spec) == cond.to_mapping()


def test_mapping_kind_in_closed_set() -> None:
    """CONDITION_KINDS contains every discriminator value we accept."""
    for expected in (
        "null",
        "cfg",
        "inpainting",
        "bfn_inpaint",
        "property",
        "mapping",
    ):
        assert expected in CONDITION_KINDS


def test_condition_in_runtime_checkable() -> None:
    """isinstance(cond, Condition) MUST work at runtime."""
    cond = NullCondition()
    assert isinstance(cond, Condition)
    assert isinstance(MappingConditionAdapter.from_mapping({"k": 1}), Condition)
    # Non-Condition object fails isinstance.
    assert not isinstance(42, Condition)
