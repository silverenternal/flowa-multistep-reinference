"""Core-runtime handoff spec for the adaptive_reflow component (DTB-R3).

Records the contract the ``flowa-denovo-core`` runtime must implement
to consume ``adaptive_reflow`` outputs deterministically. The handoff
is emitted as a JSON-serializable dict so a downstream owner can
import it without any non-stdlib dependencies.

Module boundary:

* stdlib-only. No ``torch``. No I/O.
* :class:`CoreRuntimeHandoff` is frozen; this module only constructs it.
* :func:`write_handoff_spec` is pure; identical inputs always produce
  identical output dicts.

Tasks satisfied:

* ``DTB-R3`` — request the core runtime to wire
  ``adaptive_reflow`` outputs deterministically.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any

from adaptive_reflow.contracts import hash_artifact

__all__ = [
    "CORE_RUNTIME_HANDBOFF_SCHEMA_NAME",
    "CORE_RUNTIME_HANDBOFF_SCHEMA_VERSION",
    "CORE_RUNTIME_OWNER",
    "CoreRuntimeHandoff",
    "write_handoff_spec",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


#: Canonical owner string for the downstream ``flowa_denovo_core``
#: runtime. Set explicitly so the handoff record is self-describing.
CORE_RUNTIME_OWNER: str = "flowa-denovo-core"

#: Schema name written into every emitted handoff record.
CORE_RUNTIME_HANDBOFF_SCHEMA_NAME: str = (
    "adaptive_reflow.core_runtime_handoff"
)

#: Schema version of the handoff record; bump on backward-incompatible
#: changes to the field tuple or the JSON shape.
CORE_RUNTIME_HANDBOFF_SCHEMA_VERSION: str = "1.0.0"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CoreRuntimeHandoffError(ValueError):
    """Raised when :class:`CoreRuntimeHandoff` rejects its arguments.

    Inherits from :exc:`ValueError` for backward compatibility with
    ``pytest.raises(ValueError)`` patterns.
    """


# ---------------------------------------------------------------------------
# Frozen handoff record
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class CoreRuntimeHandoff:
    """Self-describing contract the core runtime must implement.

    Every field is required and non-empty; the validator surfaces a
    deterministic error code on missing data.
    """

    schema_name: str
    schema_version: str
    responsibility: str
    compatibility_path: str
    rollback_flag: bool
    target_tests: tuple[str, ...]
    owner: str = CORE_RUNTIME_OWNER
    handoff_hash: str = ""


# ---------------------------------------------------------------------------
# Validators / builders
# ---------------------------------------------------------------------------


_ERR_FIELD_EMPTY: str = "core_runtime_handoff_field_empty"
_ERR_SCHEMA_NAME_MISMATCH: str = "core_runtime_handoff_schema_name_mismatch"
_ERR_SCHEMA_VERSION_MISMATCH: str = "core_runtime_handoff_schema_version_mismatch"
_ERR_OWNER_MISMATCH: str = "core_runtime_handoff_owner_mismatch"
_ERR_ROLLBACK_NOT_BOOL: str = "core_runtime_handoff_rollback_flag_not_bool"
_ERR_TARGET_TESTS_NOT_TUPLE: str = "core_runtime_handoff_target_tests_not_tuple"


def _require_non_empty(value: Any, *, name: str) -> str:
    """Return ``str(value)``; raise on ``None`` or empty string."""
    if value is None:
        raise CoreRuntimeHandoffError(
            f"{_ERR_FIELD_EMPTY}: {name} must not be None"
        )
    text = str(value)
    if not text:
        raise CoreRuntimeHandoffError(
            f"{_ERR_FIELD_EMPTY}: {name} must be non-empty"
        )
    return text


def _coerce_target_tests(value: Any) -> tuple[str, ...]:
    """Coerce ``target_tests`` to a tuple of non-empty strings."""
    if value is None:
        raise CoreRuntimeHandoffError(
            f"{_ERR_TARGET_TESTS_NOT_TUPLE}: target_tests must not be None"
        )
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (tuple, list)):
        items = list(value)
    else:
        raise CoreRuntimeHandoffError(
            f"{_ERR_TARGET_TESTS_NOT_TUPLE}: target_tests must be a "
            f"sequence of strings, got {type(value).__name__}"
        )
    out: list[str] = []
    for item in items:
        text = str(item)
        if not text:
            raise CoreRuntimeHandoffError(
                f"{_ERR_FIELD_EMPTY}: target_tests entries must be non-empty"
            )
        out.append(text)
    return tuple(out)


def build_core_runtime_handoff(
    *,
    responsibility: str,
    compatibility_path: str,
    rollback_flag: bool,
    target_tests: Mapping[str, Any] | tuple[str, ...] | list[str] | None = None,
    schema_name: str = CORE_RUNTIME_HANDBOFF_SCHEMA_NAME,
    schema_version: str = CORE_RUNTIME_HANDBOFF_SCHEMA_VERSION,
    owner: str = CORE_RUNTIME_OWNER,
) -> CoreRuntimeHandoff:
    """Build a :class:`CoreRuntimeHandoff` with a deterministic hash.

    The function validates each field against the canonical schema and
    computes a deterministic ``handoff_hash`` from the JSON payload
    (excluding ``handoff_hash`` itself).
    """
    if isinstance(rollback_flag, bool) is False:
        raise CoreRuntimeHandoffError(
            f"{_ERR_ROLLBACK_NOT_BOOL}: rollback_flag must be a bool, "
            f"got {type(rollback_flag).__name__}"
        )
    schema_name_v = _require_non_empty(schema_name, name="schema_name")
    if schema_name_v != CORE_RUNTIME_HANDBOFF_SCHEMA_NAME:
        raise CoreRuntimeHandoffError(
            f"{_ERR_SCHEMA_NAME_MISMATCH}: schema_name must be "
            f"{CORE_RUNTIME_HANDBOFF_SCHEMA_NAME!r}, got {schema_name_v!r}"
        )
    schema_version_v = _require_non_empty(
        schema_version, name="schema_version"
    )
    if schema_version_v != CORE_RUNTIME_HANDBOFF_SCHEMA_VERSION:
        raise CoreRuntimeHandoffError(
            f"{_ERR_SCHEMA_VERSION_MISMATCH}: schema_version must be "
            f"{CORE_RUNTIME_HANDBOFF_SCHEMA_VERSION!r}, got "
            f"{schema_version_v!r}"
        )
    owner_v = _require_non_empty(owner, name="owner")
    if owner_v != CORE_RUNTIME_OWNER:
        raise CoreRuntimeHandoffError(
            f"{_ERR_OWNER_MISMATCH}: owner must be {CORE_RUNTIME_OWNER!r}, "
            f"got {owner_v!r}"
        )
    responsibility_v = _require_non_empty(
        responsibility, name="responsibility"
    )
    compatibility_path_v = _require_non_empty(
        compatibility_path, name="compatibility_path"
    )
    target_tests_v = _coerce_target_tests(target_tests or ())

    payload = {
        "schema_name": schema_name_v,
        "schema_version": schema_version_v,
        "responsibility": responsibility_v,
        "compatibility_path": compatibility_path_v,
        "rollback_flag": bool(rollback_flag),
        "target_tests": sorted(target_tests_v),
        "owner": owner_v,
    }
    handoff_hash = str(hash_artifact(payload))

    return CoreRuntimeHandoff(
        schema_name=schema_name_v,
        schema_version=schema_version_v,
        responsibility=responsibility_v,
        compatibility_path=compatibility_path_v,
        rollback_flag=bool(rollback_flag),
        target_tests=tuple(sorted(target_tests_v)),
        owner=owner_v,
        handoff_hash=handoff_hash,
    )


def write_handoff_spec(
    *,
    responsibility: str,
    compatibility_path: str,
    rollback_flag: bool,
    target_tests: Mapping[str, Any] | tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    """Return a JSON-serializable dict describing the core-runtime handoff.

    The dict contains every field of :class:`CoreRuntimeHandoff` plus a
    precomputed ``handoff_hash`` so the downstream owner can verify the
    payload without re-running the validator. ``asdict`` on a frozen
    dataclass is itself stable, so this function is pure and total.
    """
    record = build_core_runtime_handoff(
        responsibility=responsibility,
        compatibility_path=compatibility_path,
        rollback_flag=rollback_flag,
        target_tests=target_tests,
    )
    return {
        "schema_name": record.schema_name,
        "schema_version": record.schema_version,
        "responsibility": record.responsibility,
        "compatibility_path": record.compatibility_path,
        "rollback_flag": bool(record.rollback_flag),
        "target_tests": list(record.target_tests),
        "owner": record.owner,
        "handoff_hash": record.handoff_hash,
    }
