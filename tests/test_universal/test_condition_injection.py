"""Pytest suite for condition injection (D3 — null / passthrough / augmenting injectors)."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from adaptive_reflow.universal.condition_injection import (
    AugmentingConditionInjector,
    ConditionInjectionProtocol,
    NullConditionInjector,
    PassthroughConditionInjector,
    default_null_injector,
    validate_condition_injector,
)
from adaptive_reflow.universal.state import ODEConditionDelta


def _make_delta(
    *,
    delta_spec: Mapping[str, object] | None = None,
    target_round: int = 3,
    calibration_artifact_hash: str = "cal-v1",
) -> ODEConditionDelta:
    return ODEConditionDelta(
        delta_spec=dict(delta_spec or {"source_key": "source_value"}),
        source="engine",
        target_round=target_round,
        calibration_artifact_hash=calibration_artifact_hash,
    )


# (1) NullConditionInjector kind + delta_spec shape.


def test_null_injector_kind_is_null() -> None:
    inj = NullConditionInjector(dataset="flowmol3", variant="v1")
    assert inj.kind() == "null"


def test_null_injector_delta_spec_shape() -> None:
    inj = NullConditionInjector(dataset="flowmol3_smiles_pl", variant="v1")
    out = inj.compose_delta(bundle=None, delta=_make_delta())  # type: ignore[arg-type]
    assert out.delta_spec["condition_kind"] == "null"
    assert out.delta_spec["dataset"] == "flowmol3_smiles_pl"
    assert out.delta_spec["variant"] == "v1"
    assert out.delta_spec["round_trace_only"] is True
    assert out.delta_spec["source_key"] == "source_value"


def test_null_injector_preserves_target_round_and_hash() -> None:
    inj = NullConditionInjector(dataset="d", variant="v")
    out = inj.compose_delta(bundle=None, delta=_make_delta(target_round=7, calibration_artifact_hash="cal-h-7"))  # type: ignore[arg-type]
    assert out.target_round == 7
    assert out.calibration_artifact_hash == "cal-h-7"


def test_null_injector_does_not_overwrite_existing_kind() -> None:
    inj = NullConditionInjector(dataset="d", variant="v")
    out = inj.compose_delta(
        bundle=None,  # type: ignore[arg-type]
        delta=_make_delta(delta_spec={"condition_kind": "pocket"}),
    )
    assert out.delta_spec["condition_kind"] == "pocket"


# (2) PassthroughConditionInjector.


def test_passthrough_injector_returns_equal_spec() -> None:
    inj = PassthroughConditionInjector()
    delta = _make_delta()
    out = inj.compose_delta(bundle=None, delta=delta)  # type: ignore[arg-type]
    assert dict(out.delta_spec) == dict(delta.delta_spec)
    assert out.target_round == delta.target_round
    assert out.calibration_artifact_hash == delta.calibration_artifact_hash


# (3) AugmentingConditionInjector.


def test_augmenting_injector_adds_defaults() -> None:
    inj = AugmentingConditionInjector(defaults={"target_distribution": "mnist"})
    out = inj.compose_delta(bundle=None, delta=_make_delta())  # type: ignore[arg-type]
    assert out.delta_spec["target_distribution"] == "mnist"
    assert out.delta_spec["source_key"] == "source_value"


def test_augmenting_injector_does_not_overwrite_existing_keys() -> None:
    inj = AugmentingConditionInjector(defaults={"target_distribution": "mnist"})
    delta = _make_delta(delta_spec={"target_distribution": "fashion_mnist"})
    out = inj.compose_delta(bundle=None, delta=delta)  # type: ignore[arg-type]
    assert out.delta_spec["target_distribution"] == "fashion_mnist"


# (4) Validator.


@pytest.mark.parametrize(
    "inj",
    [
        NullConditionInjector(dataset="d", variant="v"),
        PassthroughConditionInjector(),
        AugmentingConditionInjector(defaults={}),
        default_null_injector(),
    ],
)
def test_validate_condition_injector_accepts_well_formed(inj) -> None:
    ok, errs = validate_condition_injector(inj)
    assert ok, errs


def test_validate_condition_injector_rejects_non_protocol() -> None:
    ok, errs = validate_condition_injector(object())  # type: ignore[arg-type]
    assert not ok
    assert errs


# (5) Protocol conformance (runtime_checkable).


@pytest.mark.parametrize(
    "inj",
    [
        NullConditionInjector(dataset="d", variant="v"),
        PassthroughConditionInjector(),
        AugmentingConditionInjector(defaults={}),
    ],
)
def test_injector_implements_protocol(inj) -> None:
    assert isinstance(inj, ConditionInjectionProtocol)


# (6) Audit metadata.


def test_audit_metadata_returns_mapping() -> None:
    meta = NullConditionInjector(dataset="d", variant="v").audit_metadata()
    assert isinstance(meta, Mapping)
    assert meta["injector_kind"] == "null"
    assert meta["dataset"] == "d"


def test_audit_metadata_passthrough() -> None:
    meta = PassthroughConditionInjector().audit_metadata()
    assert meta["injector_kind"] == "passthrough"


def test_audit_metadata_augmenting() -> None:
    meta = AugmentingConditionInjector(defaults={"a": 1, "b": 2}).audit_metadata()
    assert meta["injector_kind"] == "augmenting"
    assert meta["defaults_keys"] == ("a", "b")


# (7) Constructor validation.


def test_invalid_constructor_args() -> None:
    with pytest.raises(ValueError):
        NullConditionInjector(dataset="", variant="v")
    with pytest.raises(ValueError):
        NullConditionInjector(dataset="d", variant="")
