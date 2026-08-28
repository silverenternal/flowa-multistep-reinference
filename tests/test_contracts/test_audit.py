"""Tests for the audit-code typed structure (CONTRACTS.md §9.1, §9.2)."""

from __future__ import annotations

import dataclasses

import pytest

from adaptive_reflow.contracts import (
    AuditCode,
    coerce_audit_code,
    coerce_audit_codes,
    make_audit_code,
    parse_audit_code,
    validate_audit_chain,
    validate_audit_code,
)
from adaptive_reflow.contracts.audit import parse_audit_code as _parse

# ---------------------------------------------------------------------------
# AuditCode basics
# ---------------------------------------------------------------------------


def test_audit_code_constructs_with_kind_only() -> None:
    code = AuditCode(kind="channel_not_in_supported_channels")
    assert code.kind == "channel_not_in_supported_channels"
    assert dict(code.payload) == {}


def test_audit_code_constructs_with_payload() -> None:
    code = AuditCode(
        kind="capability_unsupported",
        payload={"channel": "foo", "reason": "not_advertised"},
    )
    assert code.kind == "capability_unsupported"
    assert dict(code.payload) == {"channel": "foo", "reason": "not_advertised"}


def test_audit_code_rejects_empty_kind_via_validator() -> None:
    # The dataclass accepts an empty kind (parse_audit_code("") returns
    # AuditCode(kind="", payload={}) as a sentinel); semantic rejection
    # happens in validate_audit_code.
    code = AuditCode(kind="")
    ok, errors = validate_audit_code(code)
    assert ok is False
    assert "kind_must_be_non_empty" in errors


def test_audit_code_rejects_non_str_kind() -> None:
    with pytest.raises(ValueError, match="kind"):
        AuditCode(kind=123)  # type: ignore[arg-type]


def test_audit_code_rejects_non_str_payload_value() -> None:
    with pytest.raises(ValueError, match="payload"):
        AuditCode(kind="x", payload={"a": 1})  # type: ignore[dict-item]


def test_audit_code_is_frozen() -> None:
    code = AuditCode(kind="x")
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
        code.kind = "y"  # type: ignore[misc]


def test_audit_code_equality() -> None:
    a = AuditCode(kind="k", payload={"a": "1", "b": "2"})
    b = AuditCode(kind="k", payload={"b": "2", "a": "1"})
    assert a == b


# ---------------------------------------------------------------------------
# Round-trip encoding
# ---------------------------------------------------------------------------


def test_as_legacy_string_no_payload() -> None:
    code = AuditCode(kind="integrator_trace_missing")
    assert code.as_legacy_string() == "integrator_trace_missing"


def test_as_legacy_string_with_payload() -> None:
    code = AuditCode(
        kind="capability_unsupported",
        payload={"channel": "foo", "reason": "not_advertised"},
    )
    # Sorted lexicographically: channel,foo,reason,not_advertised
    assert (
        code.as_legacy_string()
        == "capability_unsupported:channel:foo:reason:not_advertised"
    )


def test_parse_audit_code_accepts_pre_formed_instance() -> None:
    original = AuditCode(kind="x", payload={"a": "1"})
    parsed = parse_audit_code(original)
    assert parsed is original


def test_parse_audit_code_handles_legacy_string() -> None:
    parsed = parse_audit_code("capability_unsupported:channel:foo:reason:bar")
    assert parsed.kind == "capability_unsupported"
    assert dict(parsed.payload) == {"channel": "foo", "reason": "bar"}


def test_parse_audit_code_handles_kind_only_legacy_string() -> None:
    parsed = parse_audit_code("bundle_must_not_be_none")
    assert parsed.kind == "bundle_must_not_be_none"
    assert dict(parsed.payload) == {}


def test_parse_audit_code_handles_empty_string() -> None:
    parsed = parse_audit_code("")
    assert parsed.kind == ""
    assert dict(parsed.payload) == {}


def test_parse_audit_code_rejects_non_str_non_audit_code() -> None:
    with pytest.raises(ValueError, match="audit code"):
        parse_audit_code(123)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Coercion (back-compat)
# ---------------------------------------------------------------------------


def test_coerce_audit_code_audit_code_passthrough() -> None:
    original = AuditCode(kind="x")
    assert coerce_audit_code(original) is original


def test_coerce_audit_code_string_passthrough() -> None:
    out = coerce_audit_code("x:y:z")
    assert out.kind == "x"
    assert dict(out.payload) == {"y": "z"}


def test_coerce_audit_code_non_str_returns_stringified_kind() -> None:
    out = coerce_audit_code(42)
    assert out.kind == "42"
    assert dict(out.payload) == {}


def test_coerce_audit_codes_list() -> None:
    codes = coerce_audit_codes(
        [
            "channel_not_in_supported_channels:foo",
            AuditCode(kind="capability_unsupported", payload={"channel": "bar"}),
            "integrator_trace_missing",
        ]
    )
    assert len(codes) == 3
    assert codes[0].kind == "channel_not_in_supported_channels"
    assert codes[0].payload["foo"] == ""
    assert codes[1].kind == "capability_unsupported"
    assert codes[1].payload["channel"] == "bar"
    assert codes[2].kind == "integrator_trace_missing"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_validate_audit_code_accepts_well_formed() -> None:
    ok, errors = validate_audit_code(
        AuditCode(kind="x", payload={"a": "1"})
    )
    assert ok is True
    assert errors == ()


def test_validate_audit_code_rejects_empty_kind() -> None:
    ok, errors = validate_audit_code(AuditCode(kind=""))
    assert ok is False
    assert "kind_must_be_non_empty" in errors


def test_validate_audit_chain_accepts_mixed_input() -> None:
    chain = (
        "channel_not_in_supported_channels:foo",
        AuditCode(kind="capability_unsupported", payload={"op": "x"}),
        "integrator_trace_missing",
    )
    ok, errors = validate_audit_chain(chain)
    assert ok is True
    assert errors == ()


def test_validate_audit_chain_rejects_garbage() -> None:
    # A non-AuditCode, non-string entry would never come from the
    # engine today, but validate_audit_chain routes everything through
    # parse_audit_code first so it stays total.
    chain = (123,)
    ok, errors = validate_audit_chain(chain)
    assert ok is False
    assert any("not_audit_code" in e for e in errors)


def test_validate_audit_chain_rejects_empty_kind() -> None:
    chain = (AuditCode(kind=""),)
    ok, errors = validate_audit_chain(chain)
    assert ok is False
    assert any("kind_must_be_non_empty" in e for e in errors)


# ---------------------------------------------------------------------------
# make_audit_code helper
# ---------------------------------------------------------------------------


def test_make_audit_code_with_kwargs() -> None:
    code = make_audit_code(
        "capability_unsupported", channel="foo", reason="not_advertised"
    )
    assert code.kind == "capability_unsupported"
    assert dict(code.payload) == {"channel": "foo", "reason": "not_advertised"}


def test_make_audit_code_no_payload() -> None:
    code = make_audit_code("integrator_trace_missing")
    assert code.kind == "integrator_trace_missing"
    assert dict(code.payload) == {}


def test_make_audit_code_rejects_non_str_value() -> None:
    with pytest.raises(ValueError, match="payload"):
        make_audit_code("x", foo=123)  # type: ignore[arg-type]


def test_make_audit_code_rejects_empty_kind() -> None:
    with pytest.raises(ValueError, match="kind"):
        make_audit_code("")


# ---------------------------------------------------------------------------
# Round-trip from engine emitted audit codes (smoke test)
# ---------------------------------------------------------------------------


def test_engine_emitted_codes_parse_cleanly() -> None:
    """Codes that match the engine's emit format round-trip through
    validate_audit_chain without errors."""
    engine_codes = [
        "adapter_must_not_be_none",
        "round_index_must_be_non_negative",
        "schedule_sample_missing",
        "channel_not_in_supported_channels:foo",
        "capability_unsupported:bar:not_advertised",
        "channel_domain_mismatch:charge",
        "integrator_trace_missing:invalid_steps",
    ]
    ok, errors = validate_audit_chain(engine_codes)
    assert ok is True, f"errors: {errors}"
    parsed = coerce_audit_codes(engine_codes)
    assert all(isinstance(c, AuditCode) for c in parsed)


def test_legacy_engine_format_round_trips() -> None:
    """The engine's legacy ``":"``-string emission round-trips into
    the typed carrier and back."""
    raw = "channel_not_in_supported_channels:foo"
    parsed = parse_audit_code(raw)
    assert parsed.kind == "channel_not_in_supported_channels"
    assert parsed.payload.get("foo") == ""
    # Re-encoding produces the same canonical string.
    assert parsed.as_legacy_string() == raw
