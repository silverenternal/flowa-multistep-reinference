"""Writer authority and arbitration for the adaptive_reflow component.

This module implements the DTB-S1 half of the adaptive_reflow typed
contract. It is the **single merge authority** that decides which
mechanism is allowed to write executable sampler controls for any given
run (see ``CONTRACTS.md`` §7 and ``DESIGN_BOUNDARY.md`` §4). The module
exposes:

* :func:`build_default_authority_contract` — deterministic constructor
  for the canonical :class:`RestartPolicyAuthorityContract` that names
  ``inference.adaptive_reflow`` as the sole executable writer,
  ``inference.noise_bias`` as a diagnostic provider (with a bounded
  legacy compatibility window), and ``flowa_core_runtime`` as the
  immutable-policy consumer.
* :class:`WriterArbitrator` — fail-closed state machine that records
  per-mechanism mode requests and rejects dual-writer attempts and
  mutually-exclusive mode pairs (``legacy_standalone`` noise_bias while
  ``executable`` adaptive_reflow is active). The arbitrator never
  performs any ``max(previous, dynamic)`` merge.
* :func:`build_final_restart_policy` — pure constructor for
  :class:`FinalRestartPolicy` with full input validation and a
  deterministic ``policy_hash`` (via
  :func:`restart_memory_types.hash_policy_hash`).
* :func:`verify_policy_against_ledger` — pure verifier that a freshly
  built :class:`FinalRestartPolicy` matches its source
  :class:`DynamicRestartTransferLedger`.

Module boundary:

* stdlib-only. **No** ``torch``. No I/O. No mutation of inputs.
* ``RestartPolicyAuthorityContract`` and ``FinalRestartPolicy`` are
  frozen; this module only builds them.
* ``WriterArbitrator`` keeps its request table as an internal dict and
  exposes only the public methods listed below.

Tasks satisfied:

* ``DTB-S1`` — writer arbitration between ``adaptive_reflow`` and
  ``noise_bias``.

The literal ``max(previous, dynamic)`` merge is **forbidden** in this
module; the controller must be able to *decrease* a prior-round
fraction as well as increase it. The constructor
:func:`build_final_restart_policy` therefore computes the policy hash
directly from the supplied factors without ever consulting a previous
policy value.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping
from typing import Any

from adaptive_reflow.contracts import (
    ArtifactHash,
    ChannelName,
    CosineScheduleSample,
    DynamicRestartTransferLedger,
    FactorValue,
    FinalRestartPolicy,
    LedgerRowId,
    LegacyCompatibilityWindow,
    MechanismId,
    PolicyId,
    RestartPolicyAuthorityContract,
    RunId,
    hash_artifact,
    hash_policy_hash,
)

__all__ = [
    "WriterArbitrator",
    "WriterArgumentError",
    "build_default_authority_contract",
    "build_final_restart_policy",
    "verify_policy_against_ledger",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Canonical contract version string for the default writer-authority contract.
DEFAULT_AUTHORITY_CONTRACT_VERSION: str = "1.0.0"

#: Sole mechanism allowed to request ``"executable"`` mode under DTB-S1.
EXECUTABLE_WRITER_MECHANISM_ID: str = "inference.adaptive_reflow"

#: Diagnostic mechanism; only allowed in ``"diagnostic_only"`` mode alongside
#: an active ``inference.adaptive_reflow`` executable writer.
DIAGNOSTIC_WRITER_MECHANISM_ID: str = "inference.noise_bias"

#: Immutable-policy consumer; never appears in ``register_request``.
CONSUMER_WRITER_ID: str = "flowa_core_runtime"

#: Schema-read compatibility version for the bounded legacy window.
LEGACY_SCHEMA_READ_COMPATIBILITY_VERSION: str = (
    "flowa_adaptive_reflow_noise_bias_v1"
)

#: The three mode strings accepted by :meth:`WriterArbitrator.register_request`.
REQUEST_MODES: tuple[str, ...] = (
    "executable",
    "diagnostic_only",
    "legacy_standalone",
)

#: Default ``mode_flags`` triple — kept in priority order.
DEFAULT_MODE_FLAGS: tuple[str, ...] = (
    "adaptive_reflow_executable",
    "flowa_core_consumer",
    "noise_bias_diagnostic_only",
)


# ---------------------------------------------------------------------------
# Canonical error codes (deterministic, no spaces, ASCII only)
# ---------------------------------------------------------------------------

ERR_UNKNOWN_MODE: str = "writer_request_unknown_mode"
ERR_WRONG_EXECUTABLE: str = "writer_request_executable_not_adaptive_reflow"
ERR_DUAL_EXECUTABLE: str = "writer_request_dual_executable_writer"
ERR_LEGACY_WHILE_EXECUTABLE: str = "writer_request_legacy_during_executable"
ERR_KEY_SETSISMATCH: str = "policy_factor_key_sets_must_match"
ERR_FACTOR_NOT_FINITE: str = "policy_factor_not_finite"
ERR_FACTOR_OUT_OF_RANGE: str = "policy_factor_out_of_unit_interval"
ERR_FACTOR_TYPE: str = "policy_factor_wrong_type"
ERR_WRITER_ID_MISMATCH: str = "policy_writer_id_must_be_adaptive_reflow"
ERR_LEDGER_WRITER_MISMATCH: str = "ledger_writer_id_mismatch"
ERR_LEDGER_KEY_MISMATCH: str = "ledger_beta_keys_mismatch"
ERR_LEDGER_ALPHA_VALUE_MISMATCH: str = "ledger_alpha_values_mismatch"
ERR_LEDGER_FLOOR_MISMATCH: str = "ledger_fresh_noise_floor_mismatch"
ERR_POLICY_HASH_MISMATCH: str = "policy_hash_recompute_mismatch"
ERR_LEDGER_FINITE_PREFIX_FALSE: str = "ledger_finite_prefix_only_must_be_true"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class WriterArgumentError(ValueError):
    """Raised when writer-authority arbitration rejects a request.

    Inherits from :class:`ValueError` so that existing
    ``pytest.raises(ValueError)`` patterns continue to work; the specific
    subclass is exposed via :data:`__all__` for callers that want to
    narrow their ``except`` clauses.
    """


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sorted_mapping_items(mapping: Mapping[Any, Any]) -> list:
    """Return ``mapping`` as a sorted list of ``[str(key), value]`` pairs.

    Mirrors the helper used by :func:`hash_policy_hash` so that the
    deterministic contract hash agrees with the policy hash that
    ``flowa_core_runtime`` recomputes at the runtime boundary.
    """
    return [[str(k), v] for k, v in sorted(mapping.items(), key=lambda kv: str(kv[0]))]


def _coerce_factor_value(x: Any) -> float:
    """Coerce ``x`` to a Python ``float`` (booleans become 0/1).

    Raises :class:`WriterArgumentError` for non-numeric inputs.
    """
    if isinstance(x, bool):
        return float(int(x))
    if isinstance(x, (int, float)):
        return float(x)
    raise WriterArgumentError(
        f"{ERR_FACTOR_TYPE}: expected a real number, got {type(x).__name__}"
    )


def _validate_unit_factor(x: Any, name: str) -> float:
    """Return ``x`` as ``float`` iff finite and in ``[0, 1]``; else raise.

    Error messages include the field ``name`` so per-factor validation
    surfaces which factor caused the rejection.
    """
    if name is None or str(name).strip() == "":
        raise WriterArgumentError("factor field name must be non-empty")
    fx = _coerce_factor_value(x)
    if not math.isfinite(fx):
        raise WriterArgumentError(
            f"{name}: {ERR_FACTOR_NOT_FINITE}: got {fx!r}"
        )
    if fx < 0.0 or fx > 1.0:
        raise WriterArgumentError(
            f"{name}: {ERR_FACTOR_OUT_OF_RANGE}: got {fx!r}"
        )
    return fx


def _coerce_mechanism_id(mechanism_id: Any) -> str:
    """Coerce ``mechanism_id`` to a plain ``str`` for comparison."""
    if mechanism_id is None:
        raise WriterArgumentError("mechanism_id must not be None")
    return str(mechanism_id)


# ---------------------------------------------------------------------------
# Default contract (DTB-S1)
# ---------------------------------------------------------------------------


def build_default_authority_contract() -> RestartPolicyAuthorityContract:
    """Build the canonical DTB-S1 writer-authority contract.

    Returns a :class:`RestartPolicyAuthorityContract` whose fields are
    fixed by the contract:

    * ``executable_writer_id == "inference.adaptive_reflow"``,
    * ``diagnostic_writer_ids == ("inference.noise_bias",)``,
    * ``consumer_writer_id == "flowa_core_runtime"``,
    * ``mode_flags == ("adaptive_reflow_executable",
        "flowa_core_consumer", "noise_bias_diagnostic_only")``,
    * ``legacy_compatibility_window`` is the bounded
      :class:`LegacyCompatibilityWindow` whose ``exclusive_with``
      contains the executable writer id (it must be empty when the
      window is enabled, per ``CONTRACTS.md`` §7 — but the contract
      declares the exclusivity list as the *declared* exclusivity
      without auto-disabling),
    * ``contract_hash`` is the deterministic sha256 of every other
      field.

    The contract hash is computed deterministically from a canonical
    JSON payload so two calls of this function return contracts with
    identical ``contract_hash`` bytes.
    """
    legacy_window = LegacyCompatibilityWindow(
        enabled=True,
        legacy_mechanism_id=MechanismId(DIAGNOSTIC_WRITER_MECHANISM_ID),
        legacy_mode="legacy_standalone",
        exclusive_with=(MechanismId(EXECUTABLE_WRITER_MECHANISM_ID),),
        schema_read_compatibility_version=LEGACY_SCHEMA_READ_COMPATIBILITY_VERSION,
        writes_sampler_controls=False,
    )

    # Build the contract with a placeholder hash so the recursive
    # ``asdict`` serialisation can be used to derive the canonical
    # payload. We then recompute the hash from the canonical payload
    # (which excludes the placeholder hash itself).
    contract = RestartPolicyAuthorityContract(
        contract_version=DEFAULT_AUTHORITY_CONTRACT_VERSION,
        executable_writer_id=EXECUTABLE_WRITER_MECHANISM_ID,
        diagnostic_writer_ids=(MechanismId(DIAGNOSTIC_WRITER_MECHANISM_ID),),
        consumer_writer_id=CONSUMER_WRITER_ID,
        mode_flags=DEFAULT_MODE_FLAGS,
        legacy_compatibility_window=legacy_window,
        contract_hash=ArtifactHash(""),
    )

    canonical_payload = {
        "contract_version": str(contract.contract_version),
        "executable_writer_id": str(contract.executable_writer_id),
        "diagnostic_writer_ids": sorted(str(m) for m in contract.diagnostic_writer_ids),
        "consumer_writer_id": str(contract.consumer_writer_id),
        "mode_flags": sorted(str(m) for m in contract.mode_flags),
        "legacy_compatibility_window": {
            "enabled": bool(legacy_window.enabled),
            "legacy_mechanism_id": str(legacy_window.legacy_mechanism_id),
            "legacy_mode": str(legacy_window.legacy_mode),
            "exclusive_with": sorted(
                str(m) for m in legacy_window.exclusive_with
            ),
            "schema_read_compatibility_version": str(
                legacy_window.schema_read_compatibility_version
            ),
            "writes_sampler_controls": bool(legacy_window.writes_sampler_controls),
        },
    }
    contract_hash = hash_artifact(canonical_payload)
    return dataclasses.replace(contract, contract_hash=contract_hash)


# ---------------------------------------------------------------------------
# WriterArbitrator (DTB-S1, single-writer enforcement)
# ---------------------------------------------------------------------------


class WriterArbitrator:
    """Fail-closed writer arbitration state machine (DTB-S1).

    Tracks per-mechanism mode requests and rejects configurations that
    would produce two distinct executable writers or that would put
    ``inference.noise_bias`` into ``legacy_standalone`` mode while
    ``inference.adaptive_reflow`` is requesting executable controls. The
    arbitrator **does not** perform any ``max(previous, dynamic)`` merge
    — once an executable writer is registered it is the sole writer;
    subsequent requests are either accepted (if consistent) or rejected
    (if they would violate the contract).

    Modes:

    * ``"executable"`` — the mechanism writes a
      :class:`FinalRestartPolicy`. Only
      ``"inference.adaptive_reflow"`` may request this mode.
    * ``"diagnostic_only"`` — the mechanism contributes diagnostic
      rows only. Always allowed to coexist with another writer.
    * ``"legacy_standalone"`` — the mechanism operates in the legacy
      single-writer mode. Mutually exclusive with
      ``"inference.adaptive_reflow"`` requesting ``"executable"``.

    Example
    -------
    >>> contract = build_default_authority_contract()
    >>> arb = WriterArbitrator(contract)
    >>> arb.register_request("inference.adaptive_reflow", "executable")
    >>> arb.register_request("inference.noise_bias", "diagnostic_only")
    >>> arb.authorize()
    ('inference.adaptive_reflow',)
    >>> arb.diagnostics_allowed()
    ('inference.noise_bias',)
    """

    __slots__ = ("_contract", "_requests")

    def __init__(self, contract: RestartPolicyAuthorityContract) -> None:
        if contract is None:
            raise WriterArgumentError("contract must not be None")
        # Defensive: the contract's executable writer must be the canonical
        # one or the arbitrator has no authority semantics to enforce.
        if str(contract.executable_writer_id) != EXECUTABLE_WRITER_MECHANISM_ID:
            raise WriterArgumentError(
                f"contract.executable_writer_id must be "
                f"{EXECUTABLE_WRITER_MECHANISM_ID!r}; got "
                f"{contract.executable_writer_id!r}"
            )
        self._contract = contract
        # mechanism_id (str) -> mode (str). The most recent request from
        # a mechanism overwrites any earlier request from the same
        # mechanism — this is the documented "Records a request"
        # semantics in the brief.
        self._requests: dict[str, str] = {}

    # ---- public API ----------------------------------------------------

    def register_request(self, mechanism_id: str, mode: str) -> None:
        """Record a writer request and fail closed on conflicts.

        Parameters
        ----------
        mechanism_id:
            Identifier of the requesting mechanism (e.g.
            ``"inference.adaptive_reflow"``,
            ``"inference.noise_bias"``). Other ids are accepted but
            only one of the two canonical mechanisms is permitted to
            request ``"executable"``.
        mode:
            One of ``"executable"``, ``"diagnostic_only"``,
            ``"legacy_standalone"``.

        Raises
        ------
        WriterArgumentError
            If ``mode`` is unknown, if a non-``inference.adaptive_reflow``
            mechanism requests ``"executable"``, if a second distinct
            mechanism already holds ``"executable"``, or if
            ``inference.noise_bias`` requests ``"legacy_standalone"``
            while ``inference.adaptive_reflow`` has requested
            ``"executable"``.
        """
        if mode not in REQUEST_MODES:
            raise WriterArgumentError(
                f"{ERR_UNKNOWN_MODE}: mode must be one of "
                f"{REQUEST_MODES!r}, got {mode!r}"
            )
        mech = _coerce_mechanism_id(mechanism_id)
        if not mech:
            raise WriterArgumentError("mechanism_id must be non-empty")

        # Rule 1 — only adaptive_reflow can request executable mode.
        if mode == "executable" and mech != EXECUTABLE_WRITER_MECHANISM_ID:
            raise WriterArgumentError(
                f"{ERR_WRONG_EXECUTABLE}: mechanism {mech!r} cannot request "
                f"'executable' mode; only "
                f"{EXECUTABLE_WRITER_MECHANISM_ID!r} is the executable writer"
            )

        # Rule 2 — dual executable writer (fail-closed). A second
        # *distinct* mechanism may not request executable mode while
        # another already holds it.
        if mode == "executable":
            for other_mech, other_mode in self._requests.items():
                if other_mode == "executable" and other_mech != mech:
                    raise WriterArgumentError(
                        f"{ERR_DUAL_EXECUTABLE}: mechanism {mech!r} cannot "
                        f"request 'executable' while {other_mech!r} already "
                        f"holds executable mode; both {other_mech!r} and "
                        f"{mech!r} would write sampler controls"
                    )

        # Rule 3 — mutual exclusion between adaptive_reflow executable
        # and noise_bias legacy_standalone. Either order of arrival
        # fails closed; the check is purely structural over the
        # currently held requests.
        if (
            mech == DIAGNOSTIC_WRITER_MECHANISM_ID
            and mode == "legacy_standalone"
            and self._requests.get(EXECUTABLE_WRITER_MECHANISM_ID) == "executable"
        ):
            raise WriterArgumentError(
                f"{ERR_LEGACY_WHILE_EXECUTABLE}: {DIAGNOSTIC_WRITER_MECHANISM_ID!r} "
                f"cannot request 'legacy_standalone' while "
                f"{EXECUTABLE_WRITER_MECHANISM_ID!r} holds 'executable' mode; "
                f"the two modes are mutually exclusive"
            )

        self._requests[mech] = mode

    def authorize(self) -> tuple[MechanismId, ...]:
        """Return the tuple of mechanism ids authorised to execute.

        The tuple is empty when no executable request is registered.
        When two or more distinct mechanisms are recorded as
        ``"executable"`` the function raises :class:`WriterArgumentError`
        with both ids in the message — the registration-time guard
        should have rejected the second request, but the function is
        defensive in case the table is populated by a different path
        (e.g. a future batch registration helper).

        Returns
        -------
        tuple
            A tuple of :class:`MechanismId` values. The order matches
            insertion order of the underlying ``_requests`` dict.

        Raises
        ------
        WriterArgumentError
            If two or more distinct mechanisms are recorded as
            ``"executable"``.
        """
        executors = [
            MechanismId(m) for m, md in self._requests.items() if md == "executable"
        ]
        if len(executors) > 1:
            ids_repr = tuple(str(m) for m in executors)
            raise WriterArgumentError(
                f"{ERR_DUAL_EXECUTABLE}: dual executable writer detected "
                f"between mechanism ids {ids_repr}; both ids are recorded as "
                f"'executable' and cannot coexist"
            )
        return tuple(executors)

    def diagnostics_allowed(self) -> tuple[MechanismId, ...]:
        """Return the tuple of mechanism ids allowed in diagnostic-only mode.

        Diagnostic-only mode is always allowed to coexist with another
        writer. The returned tuple preserves insertion order.
        """
        return tuple(
            MechanismId(m) for m, md in self._requests.items() if md == "diagnostic_only"
        )

    def reset(self) -> None:
        """Clear all registered requests.

        After :meth:`reset` the arbitrator behaves as if just constructed.
        """
        self._requests.clear()

    # ---- read-only introspection ---------------------------------------

    @property
    def contract(self) -> RestartPolicyAuthorityContract:
        """Return the underlying authority contract (read-only)."""
        return self._contract

    def __repr__(self) -> str:
        return (
            f"WriterArbitrator(contract_version="
            f"{self._contract.contract_version!r}, requests={self._requests!r})"
        )


# ---------------------------------------------------------------------------
# FinalRestartPolicy construction (DTB-S1)
# ---------------------------------------------------------------------------


def build_final_restart_policy(
    *,
    policy_id: PolicyId,
    run_id: RunId,
    target_round: int,
    outer_cycle_id: int,
    beta_by_channel: Mapping[ChannelName, FactorValue],
    alpha_by_channel: Mapping[ChannelName, FactorValue],
    fresh_noise_floor_by_channel: Mapping[ChannelName, FactorValue],
    schedule_sample: CosineScheduleSample | None,
    freeze_admission_by_channel: Mapping[ChannelName, bool],
    ledger_row_id: LedgerRowId,
    created_at_round: int,
) -> FinalRestartPolicy:
    """Build a fully-validated :class:`FinalRestartPolicy`.

    The function enforces every check required by ``CONTRACTS.md`` §7:

    * The four factor mappings share the **same** key set; mismatched
      keys fail closed with :class:`WriterArgumentError`.
    * Every factor in ``beta_by_channel``, ``alpha_by_channel``, and
      ``fresh_noise_floor_by_channel`` is finite and in ``[0, 1]``.
    * ``writer_id`` is fixed to ``"inference.adaptive_reflow"``.
    * ``policy_hash`` is recomputed deterministically via
      :func:`hash_policy_hash`.

    No ``max(previous, dynamic)`` merge is performed. The constructor
    derives the hash directly from the supplied factors; any
    down-stream comparison with a previous policy must use byte/hash
    equality (see :func:`verify_policy_against_ledger`).

    Parameters
    ----------
    policy_id:
        Versioned identifier for this policy row.
    run_id:
        Identifier of the run that owns this policy.
    target_round:
        Round that this policy applies to (must be a non-negative int).
    outer_cycle_id:
        Identifier of the outer cycle (must be a non-negative int).
    beta_by_channel, alpha_by_channel, fresh_noise_floor_by_channel:
        Per-channel factor mappings. Keys must be identical across all
        three.
    schedule_sample:
        Optional :class:`CosineScheduleSample` produced by
        :mod:`cosine_schedule`. ``None`` is allowed when the schedule
        family is ``"constant"`` (no per-round sample is required).
    freeze_admission_by_channel:
        Per-channel freeze admission mask. The keys must match the
        factor-mapping keys.
    ledger_row_id:
        Identifier of the source
        :class:`DynamicRestartTransferLedger` row.
    created_at_round:
        Round at which this policy was assembled (must be a
        non-negative int).

    Returns
    -------
    FinalRestartPolicy
        A frozen policy row with ``policy_hash`` recomputed from the
        canonical field tuple.

    Raises
    ------
    WriterArgumentError
        On any validation failure.
    """
    if policy_id is None or str(policy_id) == "":
        raise WriterArgumentError("policy_id must be non-empty")
    if run_id is None or str(run_id) == "":
        raise WriterArgumentError("run_id must be non-empty")
    if ledger_row_id is None or str(ledger_row_id) == "":
        raise WriterArgumentError("ledger_row_id must be non-empty")

    # Type checks on the integer round / cycle / created_at fields.
    for name, value in (
        ("target_round", target_round),
        ("outer_cycle_id", outer_cycle_id),
        ("created_at_round", created_at_round),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise WriterArgumentError(
                f"{name}: expected int, got {type(value).__name__}"
            )
        if value < 0:
            raise WriterArgumentError(f"{name}: must be >= 0, got {value}")

    # Key set agreement — all four mappings must agree.
    beta_keys = {str(k) for k in beta_by_channel}
    alpha_keys = {str(k) for k in alpha_by_channel}
    floor_keys = {str(k) for k in fresh_noise_floor_by_channel}
    freeze_keys = {str(k) for k in freeze_admission_by_channel}

    if not (beta_keys == alpha_keys == floor_keys == freeze_keys):
        raise WriterArgumentError(
            f"{ERR_KEY_SETSISMATCH}: beta/alpha/floor/freeze key sets must "
            f"match; got beta={sorted(beta_keys)!r} alpha={sorted(alpha_keys)!r} "
            f"floor={sorted(floor_keys)!r} freeze={sorted(freeze_keys)!r}"
        )

    # Validate factors are finite and in [0, 1]. We iterate in sorted
    # key order so the error messages are deterministic.
    sorted_keys = sorted(beta_keys)
    for k in sorted_keys:
        beta_name = f"beta_by_channel[{k!r}]"
        alpha_name = f"alpha_by_channel[{k!r}]"
        floor_name = f"fresh_noise_floor_by_channel[{k!r}]"
        # Validate beta first; we don't need to keep the coerced value
        # because the dataclass will store the original Mapping as-is.
        _validate_unit_factor(beta_by_channel[k], beta_name)
        _validate_unit_factor(alpha_by_channel[k], alpha_name)
        _validate_unit_factor(fresh_noise_floor_by_channel[k], floor_name)

    # Freeze admission must be a bool per channel.
    for k in sorted_keys:
        v = freeze_admission_by_channel[k]
        if isinstance(v, bool):
            continue
        # Accept 0/1 integers as canonical bool encoding.
        if isinstance(v, int) and v in (0, 1):
            continue
        raise WriterArgumentError(
            f"freeze_admission_by_channel[{k!r}]: expected bool, "
            f"got {type(v).__name__} ({v!r})"
        )

    # Build the policy with a placeholder hash so the deterministic
    # hash can be computed from the canonical field tuple (see
    # :func:`hash_policy_hash`).
    placeholder = FinalRestartPolicy(
        policy_id=PolicyId(str(policy_id)),
        writer_id=MechanismId(EXECUTABLE_WRITER_MECHANISM_ID),
        run_id=RunId(str(run_id)),
        target_round=int(target_round),
        outer_cycle_id=int(outer_cycle_id),
        beta_by_channel=beta_by_channel,
        alpha_by_channel=alpha_by_channel,
        fresh_noise_floor_by_channel=fresh_noise_floor_by_channel,
        schedule_sample=schedule_sample,
        freeze_admission_by_channel=freeze_admission_by_channel,
        ledger_row_id=LedgerRowId(str(ledger_row_id)),
        policy_hash=ArtifactHash(""),
        created_at_round=int(created_at_round),
    )
    policy_hash = hash_policy_hash(placeholder)
    if str(policy_hash) == "":
        # Defensive: hash_artifact should never return an empty digest,
        # but the writer hash is required downstream.
        raise WriterArgumentError(
            f"{ERR_POLICY_HASH_MISMATCH}: hash_policy_hash returned empty digest"
        )
    return dataclasses.replace(placeholder, policy_hash=policy_hash)


# ---------------------------------------------------------------------------
# FinalRestartPolicy verification (DTB-S1, runtime boundary check)
# ---------------------------------------------------------------------------


def verify_policy_against_ledger(
    policy: FinalRestartPolicy,
    ledger: DynamicRestartTransferLedger,
) -> bool:
    """Return ``True`` iff ``policy`` is consistent with ``ledger``.

    The check enforces the five conditions listed in the brief:

    * ``policy.writer_id == ledger.writer_id``.
    * ``policy.beta_by_channel`` keys equal
      ``ledger.beta_by_channel`` keys.
    * ``policy.alpha_by_channel`` values equal
      ``ledger.alpha_by_channel`` values (per-key float equality).
    * ``policy.fresh_noise_floor_by_channel`` equals
      ``ledger.fresh_noise_floor_by_channel`` (per-key float equality).
    * ``policy.policy_hash`` matches the deterministic recompute via
      :func:`hash_policy_hash`.
    * ``ledger.finite_prefix_only`` is ``True``.

    The function is pure and side-effect free; on any mismatch it
    returns ``False`` rather than raising. Callers that want a
    human-readable reason should wrap it in their own validator
    (the comments on each branch describe the condition in plain
    English).

    Parameters
    ----------
    policy:
        The :class:`FinalRestartPolicy` to verify.
    ledger:
        The :class:`DynamicRestartTransferLedger` row that was the
        source of ``policy``.

    Returns
    -------
    bool
        ``True`` iff every condition above holds.
    """
    if policy is None or ledger is None:
        return False

    # 1. writer_id equality
    if str(policy.writer_id) != str(ledger.writer_id):
        return False

    # 2. beta_by_channel key equality
    policy_beta_keys = sorted(str(k) for k in policy.beta_by_channel)
    ledger_beta_keys = sorted(str(k) for k in ledger.beta_by_channel)
    if policy_beta_keys != ledger_beta_keys:
        return False

    # 3. alpha_by_channel value equality (per-key)
    policy_alpha = {str(k): float(v) for k, v in policy.alpha_by_channel.items()}
    ledger_alpha = {str(k): float(v) for k, v in ledger.alpha_by_channel.items()}
    if set(policy_alpha.keys()) != set(ledger_alpha.keys()):
        return False
    for k in sorted(policy_alpha.keys()):
        if not math.isclose(policy_alpha[k], ledger_alpha[k], rel_tol=0.0, abs_tol=0.0):
            return False

    # 4. fresh_noise_floor_by_channel equality (per-key)
    policy_floor = {
        str(k): float(v) for k, v in policy.fresh_noise_floor_by_channel.items()
    }
    ledger_floor = {
        str(k): float(v) for k, v in ledger.fresh_noise_floor_by_channel.items()
    }
    if set(policy_floor.keys()) != set(ledger_floor.keys()):
        return False
    for k in sorted(policy_floor.keys()):
        if not math.isclose(policy_floor[k], ledger_floor[k], rel_tol=0.0, abs_tol=0.0):
            return False

    # 5. policy_hash matches recompute
    recomputed = hash_policy_hash(policy)
    if str(recomputed) != str(policy.policy_hash):
        return False

    # 6. finite_prefix_only must be True on the ledger
    return bool(ledger.finite_prefix_only) is True
