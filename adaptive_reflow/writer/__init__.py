"""Adaptive reflow — single-writer authority + registry + audit + handoff.

DTB-S1 writer arbitration, DTB-G2 registry + audit template, DTB-R3
core-runtime handoff. All four modules are "what talks to the rest of the
system".
"""
from .audit import (
    DEFAULT_AUDIT_TEMPLATE,
    AuditTemplate,
    registry_summary,
    render_audit_checklist,
    validate_audit_completeness,
)
from .authority import (
    CONSUMER_WRITER_ID,
    DEFAULT_AUTHORITY_CONTRACT_VERSION,
    DEFAULT_MODE_FLAGS,
    DIAGNOSTIC_WRITER_MECHANISM_ID,
    ERR_DUAL_EXECUTABLE,
    EXECUTABLE_WRITER_MECHANISM_ID,
    LEGACY_SCHEMA_READ_COMPATIBILITY_VERSION,
    REQUEST_MODES,
    WriterArbitrator,
    WriterArgumentError,
    build_default_authority_contract,
    build_final_restart_policy,
    verify_policy_against_ledger,
)
from .handoff import (
    CORE_RUNTIME_HANDBOFF_SCHEMA_NAME,
    CORE_RUNTIME_HANDBOFF_SCHEMA_VERSION,
    CORE_RUNTIME_OWNER,
    CoreRuntimeHandoff,
    CoreRuntimeHandoffError,
    build_core_runtime_handoff,
    write_handoff_spec,
)
from .registry import (
    FLOWMOL3_PINNED_COMMIT,
    AdapterStatus,
    CandidateEntry,
    CandidateRegistry,
    TaskCondition,
    admit_entry,
    default_registry,
    make_default_flowmol3_entry,
    make_default_flowmol3adapter_entry,
    make_initial_registry,
)
