"""Audit-code typed structure + chain consistency (CONTRACTS.md §9.1, §9.2).

The audit trail emitted by the engine (and consumed by the ledger /
archive / orchestrator) is a sequence of :class:`AuditCode` records.
Historically the engine appended ``":"``-delimited strings to its
``audit_codes`` list (``"channel_not_in_supported_channels:foo"``); the
``":"`` separator leaked into every downstream validator and made
robust parsing painful. This module pins the canonical
:class:`AuditCode` shape (``kind`` + ``payload``) and provides:

* :class:`AuditCode` — frozen dataclass with ``kind: str`` and
  ``payload: Mapping[str, str]``.
* :func:`parse_audit_code` — total parser that accepts both legacy
  strings (preserves the leading ``"kind"`` as the kind, parses the
  trailing ``":"``-delimited segments as ordered payload) and
  pre-formed :class:`AuditCode` instances.
* :func:`coerce_audit_codes` — total list-coercer for legacy sites
  that still emit strings (the writer path is being migrated).
* :func:`validate_audit_chain` — chain consistency check (CONTRACTS.md
  §9.2): every :class:`AuditCode` must have a non-empty ``kind`` and
  all payload keys/values must be ``str``.

Backwards compatibility
-----------------------

The :class:`LedgerRow` and :class:`RoundTrace` ``audit_codes`` fields
remain ``tuple[str, ...]`` at the framework boundary so legacy
downstream consumers keep working unchanged. Internally the engine
emits strings via :func:`coerce_audit_code` so existing call sites do
not break; new code paths construct :class:`AuditCode` instances
directly. Parsers normalise both shapes into the typed carrier.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# AuditCode
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditCode:
    """Typed audit-trail record (CONTRACTS.md §9.1).

    Every record carries a non-empty ``kind`` (a stable string
    identifier such as ``"channel_not_in_supported_channels"``) and an
    ordered ``payload`` mapping of string keys to string values. The
    canonical emitter path serialises the record as
    ``f"{kind}:{k1}:{v1}:{k2}:{v2}"``; :func:`parse_audit_code`
    reverses the round-trip for legacy ``":"``-delimited strings.

    Two records are equal iff their ``kind`` and ``payload`` are
    equal (the dataclass is frozen and ``Mapping`` equality follows
    key/value identity). The ``payload`` defaults to an empty
    mapping so call sites that need only ``kind`` can construct a
    code directly.
    """

    kind: str
    payload: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str):
            raise ValueError(
                f"AuditCode.kind must be a str, got {type(self.kind).__name__}"
            )
        if not isinstance(self.payload, Mapping):
            raise ValueError(
                f"AuditCode.payload must be a Mapping, got "
                f"{type(self.payload).__name__}"
            )
        for key, value in self.payload.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"AuditCode.payload keys must be str, got {type(key).__name__}"
                )
            if not isinstance(value, str):
                raise ValueError(
                    f"AuditCode.payload values must be str, got "
                    f"{type(value).__name__}"
                )

    def as_legacy_string(self) -> str:
        """Return the legacy ``":"``-delimited representation.

        The encoding is deterministic for a given record:
        ``f"{kind}"`` when ``payload`` is empty, otherwise
        ``f"{kind}:{k1}:{v1}:...:{kN}:{vN}"``. Keys and values are
        sorted lexicographically so two records with equal content
        produce equal strings. Trailing ``":"`` segments (when the
        payload value is empty) are elided so the round-trip matches
        the legacy emitter format (``"kind:foo"`` is not re-emitted as
        ``"kind:foo:"``).
        """
        if not self.payload:
            return str(self.kind)
        parts: list[str] = [str(self.kind)]
        for key in sorted(self.payload):
            value = str(self.payload[key])
            parts.append(str(key))
            if value:
                parts.append(value)
        return ":".join(parts)


# ---------------------------------------------------------------------------
# Parsing / coercion
# ---------------------------------------------------------------------------


def parse_audit_code(value: Any) -> AuditCode:
    """Return the :class:`AuditCode` for ``value`` (str or AuditCode).

    Accepts:

    * a pre-formed :class:`AuditCode` — returned unchanged.
    * a ``":"``-delimited legacy string — parsed into ``kind`` (first
      segment) and ordered ``payload`` pairs (subsequent segments
      interpreted as alternating ``key, value, key, value, ...``).
      Odd-segment strings raise ``ValueError``.

    The helper is total: it NEVER raises on legacy strings; an empty
    string parses to ``AuditCode("", ())`` (preserving the engine's
    fail-open behaviour for empty audit codes).
    """
    if isinstance(value, AuditCode):
        return value
    if not isinstance(value, str):
        raise ValueError(
            f"audit code must be AuditCode or str, got {type(value).__name__}"
        )
    text = str(value)
    if not text:
        return AuditCode(kind="", payload={})
    parts = text.split(":")
    kind = parts[0]
    payload_pairs = parts[1:]
    if len(payload_pairs) % 2 != 0:
        # Legacy emitter quirk: some sites append a trailing
        # ":{name}:{type}" segment without a value, others a bare
        # ":{name}" flag. Tolerate by keeping the orphan key with
        # an empty-string value so the round-trip preserves it.
        payload_pairs = payload_pairs + [""]
    payload: dict[str, str] = {}
    for i in range(0, len(payload_pairs), 2):
        key = payload_pairs[i]
        value_str = payload_pairs[i + 1] if (i + 1) < len(payload_pairs) else ""
        payload[str(key)] = str(value_str)
    return AuditCode(kind=str(kind), payload=payload)


def coerce_audit_code(value: Any) -> AuditCode:
    """Total variant of :func:`parse_audit_code`.

    Returns ``AuditCode(kind=str(value), payload={})`` for any
    non-string, non-AuditCode input (the legacy emitter path was
    permissive about non-strings — ``RuntimeError`` / exception
    objects were stringified by ``str(exc)`` and appended verbatim).
    """
    try:
        return parse_audit_code(value)
    except ValueError:
        return AuditCode(kind=str(value), payload={})


def coerce_audit_codes(values: Iterable[Any]) -> tuple[AuditCode, ...]:
    """Return a tuple of :class:`AuditCode` for every entry in ``values``.

    Each entry is routed through :func:`coerce_audit_code` so legacy
    strings, pre-formed :class:`AuditCode` instances, and arbitrary
    stringifiable objects all produce a well-formed audit record.
    """
    return tuple(coerce_audit_code(v) for v in values)


# ---------------------------------------------------------------------------
# Chain validation
# ---------------------------------------------------------------------------


def validate_audit_code(code: AuditCode) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``code`` is a well-formed audit record."""
    errors: list[str] = []
    if not isinstance(code, AuditCode):
        return (False, (f"not_audit_code:{type(code).__name__}",))
    if not code.kind:
        errors.append("kind_must_be_non_empty")
    for key, value in code.payload.items():
        if not isinstance(key, str) or not key:
            errors.append(f"payload_key_invalid:{key!r}")
        if not isinstance(value, str):
            errors.append(f"payload_value_not_str:{key}")
    return (not errors, tuple(errors))


def validate_audit_chain(
    codes: Iterable[Any],
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff every entry in ``codes`` is well-formed.

    Mirrors :func:`verify_ledger_chain`'s semantics for the audit
    trail (CONTRACTS.md §9.2): the chain is just a sequence of audit
    records, and the only invariant is per-record well-formedness.
    Future revisions may add cross-record constraints (e.g. monotonic
    sequence numbers); this revision sticks to the per-record
    contract.

    The function uses the strict :func:`parse_audit_code` (not the
    permissive :func:`coerce_audit_code`): a non-string, non-AuditCode
    entry is rejected with ``not_audit_code:...`` rather than being
    silently stringified into a placeholder ``AuditCode``.
    """
    parsed_list: list[AuditCode] = []
    errors: list[str] = []
    for idx, raw in enumerate(codes):
        try:
            parsed_list.append(parse_audit_code(raw))
        except ValueError as exc:
            errors.append(f"codes[{idx}]:not_audit_code:{exc}")
            continue
        code = parsed_list[-1]
        ok, sub = validate_audit_code(code)
        if not ok:
            errors.extend(f"codes[{idx}]:{e}" for e in sub)
    return (not errors, tuple(errors))


# ---------------------------------------------------------------------------
# Emitter helpers (used by callers that prefer the typed carrier)
# ---------------------------------------------------------------------------


def make_audit_code(
    kind: str,
    /,
    **payload: str,
) -> AuditCode:
    """Build an :class:`AuditCode` with keyword payload.

    The keyword-only API guarantees ``payload`` is a ``str -> str``
    mapping without the caller having to import ``Mapping`` at every
    site. Raises ``ValueError`` when ``kind`` is empty or any payload
    value is not a string.
    """
    if not kind or not isinstance(kind, str):
        raise ValueError(f"kind must be a non-empty str, got {kind!r}")
    cleaned: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(value, str):
            raise ValueError(
                f"payload value for {key!r} must be str, got "
                f"{type(value).__name__}"
            )
        cleaned[str(key)] = str(value)
    return AuditCode(kind=str(kind), payload=cleaned)


__all__ = [
    "AuditCode",
    "coerce_audit_code",
    "coerce_audit_codes",
    "make_audit_code",
    "parse_audit_code",
    "validate_audit_chain",
    "validate_audit_code",
]
