"""Smoke tests for adaptive_reflow.util.host_fingerprint (Wave 38 R-2).

Validates the SciMLBenchmarks.jl-style auto-append pattern: every
JSON audit output should carry a ``_host_fingerprint`` field that
identifies the host that produced it.
"""
from __future__ import annotations

import re

import pytest

from adaptive_reflow.util.host_fingerprint import (
    capture_host_fingerprint,
    compute_host_fingerprint,
    with_host_fingerprint,
)


# ---------------------------------------------------------------------------
# compute_host_fingerprint / capture_host_fingerprint
# ---------------------------------------------------------------------------


def test_compute_host_fingerprint_returns_dict() -> None:
    fp = compute_host_fingerprint()
    assert isinstance(fp, dict)
    # Required keys (independent of whether torch is installed).
    for key in ("python", "platform", "hostname_hash", "captured_at"):
        assert key in fp, f"missing required key {key!r} in {fp!r}"
        assert isinstance(fp[key], str)
        assert fp[key], f"empty value for required key {key!r}"


def test_compute_host_fingerprint_python_version_format() -> None:
    """python field is a ``X.Y.Z`` triple, not the full sys.version string."""
    fp = compute_host_fingerprint()
    assert re.match(r"^\d+\.\d+\.\d+", fp["python"]), (
        f"python field {fp['python']!r} is not a X.Y.Z version"
    )


def test_compute_host_fingerprint_hostname_hash_format() -> None:
    """hostname_hash is a ``sha256:`` prefix + 16-hex-char digest."""
    fp = compute_host_fingerprint()
    assert fp["hostname_hash"].startswith("sha256:"), (
        f"hostname_hash missing sha256: prefix: {fp['hostname_hash']!r}"
    )
    hex_part = fp["hostname_hash"].split(":", 1)[1]
    assert len(hex_part) == 16, (
        f"hostname_hash hex segment is {len(hex_part)} chars; want 16"
    )
    assert all(c in "0123456789abcdef" for c in hex_part), (
        f"hostname_hash hex segment is not lowercase hex: {hex_part!r}"
    )


def test_compute_host_fingerprint_is_deterministic_per_host() -> None:
    """hostname_hash must not change between calls (within one process)."""
    fp1 = compute_host_fingerprint()
    fp2 = compute_host_fingerprint()
    assert fp1["hostname_hash"] == fp2["hostname_hash"]
    assert fp1["python"] == fp2["python"]
    assert fp1["platform"] == fp2["platform"]
    # captured_at can vary; we test it separately below.


def test_compute_host_fingerprint_captured_at_is_iso8601_utc() -> None:
    """captured_at is an ISO-8601 string with explicit UTC offset."""
    fp = compute_host_fingerprint()
    captured = fp["captured_at"]
    # ISO-8601 with timezone: "YYYY-MM-DDTHH:MM:SS.ffffff+00:00" etc.
    assert re.match(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+00:00|Z)$",
        captured,
    ), f"captured_at is not ISO-8601 UTC: {captured!r}"


def test_torch_field_handles_missing_torch() -> None:
    """When torch is unimportable, torch/cuda fields degrade gracefully.

    On the host the test is currently running, torch may or may not be
    installed. We document the contract: the returned dict always has
    the ``torch``/``cuda`` keys (either as versions or as the
    placeholder strings), never raises.
    """
    fp = compute_host_fingerprint()
    assert "torch" in fp
    assert "cuda" in fp
    assert fp["torch"] == "not_installed" or re.match(
        r"^\d+\.\d+\.\d+", fp["torch"]
    )
    assert fp["cuda"] in {"n/a", "none"} or re.match(
        r"^\d+\.\d+", fp["cuda"]
    )


def test_capture_host_fingerprint_is_alias() -> None:
    """capture_host_fingerprint delegates to compute_host_fingerprint.

    The alias is structurally identical to compute_host_fingerprint on
    all keys *except* ``captured_at``, which can differ by microseconds
    across calls. We compare only the deterministic fields here.
    """
    fp1 = capture_host_fingerprint()
    fp2 = compute_host_fingerprint()
    for k in ("python", "platform", "hostname_hash", "torch", "cuda"):
        assert fp1[k] == fp2[k], f"alias disagrees on key {k!r}: {fp1[k]!r} vs {fp2[k]!r}"
    # Both must be ISO-8601 UTC timestamps (compare format, not value).
    assert re.match(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+00:00|Z)$",
        fp1["captured_at"],
    )
    assert re.match(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+00:00|Z)$",
        fp2["captured_at"],
    )


# ---------------------------------------------------------------------------
# with_host_fingerprint
# ---------------------------------------------------------------------------


def test_with_host_fingerprint_dict_payload() -> None:
    """Dict payloads get a ``_host_fingerprint`` field appended."""
    payload = {"summary": "ok", "n": 7}
    out = with_host_fingerprint(payload)
    assert isinstance(out, dict)
    assert out["summary"] == "ok"
    assert out["n"] == 7
    assert "_host_fingerprint" in out
    fp = out["_host_fingerprint"]
    assert fp["python"]  # non-empty
    # Original payload is not mutated.
    assert "_host_fingerprint" not in payload


def test_with_host_fingerprint_does_not_mutate_input() -> None:
    """The input dict is shallow-copied; no in-place mutation."""
    payload = {"x": 1, "nested": {"a": 2}}
    out = with_host_fingerprint(payload)
    assert out["x"] == 1
    assert out["nested"] == {"a": 2}
    assert "_host_fingerprint" not in payload
    assert "_host_fingerprint" in out


def test_with_host_fingerprint_list_payload_wraps_in_envelope() -> None:
    """List payloads are wrapped in {items: [...], _host_fingerprint: ...}."""
    payload = [1, 2, 3]
    out = with_host_fingerprint(payload)
    assert isinstance(out, dict)
    assert out["items"] == [1, 2, 3]
    assert "_host_fingerprint" in out


def test_with_host_fingerprint_rejects_unsupported_types() -> None:
    """Strings, ints, and None raise TypeError."""
    for bad in ("hello", 42, 3.14, None):
        with pytest.raises(TypeError, match="unsupported payload type"):
            with_host_fingerprint(bad)  # type: ignore[arg-type]


def test_with_host_fingerprint_idempotent() -> None:
    """Re-applying with_host_fingerprint overwrites the previous one."""
    first = with_host_fingerprint({"a": 1})
    second = with_host_fingerprint(first)
    assert second["a"] == 1
    # Both calls produced fingerprints; only the latest survives.
    assert "_host_fingerprint" in second
    # The original first dict still carries its first fingerprint.
    assert "_host_fingerprint" in first


def test_with_host_fingerprint_preserves_all_keys() -> None:
    """Every input key survives intact."""
    payload = {
        "schema_version": "1.0",
        "added_count": 3,
        "removed_count": 0,
        "nested": {"deep": [1, 2, 3]},
    }
    out = with_host_fingerprint(payload)
    for k, v in payload.items():
        assert out[k] == v, f"key {k!r} not preserved: got {out[k]!r}"
    assert "_host_fingerprint" in out
