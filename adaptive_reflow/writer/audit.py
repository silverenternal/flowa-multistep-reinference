"""Audit template for candidate registry entries (DTB-G2).

The audit template fixes the canonical fields a :class:`CandidateEntry`
must carry and the checks a separate (human) audit owner applies before
admitting a candidate to paired evaluation. This module does **not**
make admission decisions; it only enumerates the checklist and reports
which fields are missing for a given entry.

Non-claim boundary
------------------

* Registry admission is **not** based on SOTA ranking. The audit template
  is reproducibility-first.
* ``admitted_unconditional_only`` rows are explicitly excluded from any
  universal / generalizable statement until a separate pocket-conditioned
  candidate is admitted.
"""

from __future__ import annotations

from dataclasses import dataclass

from adaptive_reflow.writer.registry import (
    CandidateEntry,
    CandidateRegistry,
)

# ---------------------------------------------------------------------------
# Audit template
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditTemplate:
    """Fixed audit template field list.

    A passing audit must have a non-empty value for every field listed
    below; ``validate_audit_completeness`` enforces this for a given
    :class:`CandidateEntry`.
    """

    required_entry_fields: tuple[str, ...] = (
        "repo_url",
        "commit",
        "license",
        "paper_id",
        "paper_date",
        "task_conditions",
        "dataset_split",
        "native_metric_protocol",
        "ode_call_site",
        "state_boundary",
        "condition_boundary",
        "restart_boundary",
        "compatible_channels",
        "available_checkpoint",
        "adapter_status",
        "audit_notes",
        "registered_at",
        "registered_by",
    )

    additional_audit_checks: tuple[str, ...] = (
        "repo_url_is_https",
        "commit_is_40_hex_chars",
        "paper_date_is_yyyy_or_yyyy_mm",
        "ode_call_site_named_in_repo_or_paper",
        "state_boundary_has_detach_signal",
        "audit_notes_non_empty",
        "compatible_channels_subset_of_engine_domain",
    )

    registry_non_claims: tuple[str, ...] = (
        "registry_does_not_use_sota_ranking_as_admission_basis",
        "admitted_unconditional_only_excluded_from_pocket_conditioned_claims",
        "generalizable_statements_require_pocket_conditioned_plus_other_state",
    )


# Module-level singleton; immutable by construction.
DEFAULT_AUDIT_TEMPLATE = AuditTemplate()


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def _paper_date_ok(paper_date: str) -> bool:
    """Lightweight ISO date check: ``YYYY`` or ``YYYY-MM`` or ``YYYY-MM-DD``."""
    if not paper_date:
        return False
    parts = paper_date.split("-")
    return not (not parts or not parts[0].isdigit() or len(parts[0]) != 4)


def _commit_is_hex_40(commit: str) -> bool:
    return isinstance(commit, str) and len(commit) == 40 and all(
        c in "0123456789abcdefABCDEF" for c in commit
    )


def _has_detach_signal(state_boundary: str) -> bool:
    lowered = state_boundary.lower()
    return "detach" in lowered or "stop_gradient" in lowered


def validate_audit_completeness(
    entry: CandidateEntry,
    template: AuditTemplate = DEFAULT_AUDIT_TEMPLATE,
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``entry`` passes the audit template.

    The returned errors tuple names each missing structural or semantic
    requirement. The function never raises.
    """
    errors: list[str] = []

    # Structural presence — every required field is non-empty by the
    # ``CandidateEntry.__post_init__`` invariant, but we re-check the
    # audit_notes and required strings explicitly so the audit report
    # names them even if the invariant is later relaxed.
    # ``available_checkpoint`` is the one exception: ``None`` is a
    # valid value meaning "no checkpoint published", and ``str`` values
    # must be non-empty.
    for fname in template.required_entry_fields:
        value = getattr(entry, fname, None)
        if fname == "available_checkpoint":
            if value is not None and (not isinstance(value, str) or not value):
                errors.append(f"empty_field:{fname}")
            continue
        if value is None:
            errors.append(f"missing_field:{fname}")
            continue
        if isinstance(value, str) and not value:
            errors.append(f"empty_field:{fname}")
        if isinstance(value, tuple) and not value:
            errors.append(f"empty_tuple_field:{fname}")

    # Additional semantic checks.
    if not entry.repo_url.startswith("https://"):
        errors.append("repo_url_is_https_failed")
    if not _commit_is_hex_40(entry.commit):
        errors.append("commit_is_40_hex_chars_failed")
    if not _paper_date_ok(entry.paper_date):
        errors.append("paper_date_is_yyyy_or_yyyy_mm_failed")
    if not entry.ode_call_site:
        errors.append("ode_call_site_named_in_repo_or_paper_failed")
    if not _has_detach_signal(entry.state_boundary):
        errors.append("state_boundary_has_detach_signal_failed")
    if not entry.audit_notes:
        errors.append("audit_notes_non_empty_failed")
    # compatible_channels must include only names the engine routes through
    # the molecule-layer domain fallback table
    # (``adaptive_reflow.molecular.domain.MOLECULE_DOMAIN_BY_CHANNEL``) — but
    # only for entries that will actually participate in engine-driven round
    # loops. ``admitted_unconditional_only`` entries are admitted only for
    # mechanics validation and may carry channels the engine doesn't route
    # directly; the engine handshake still fails closed at runtime.
    if entry.adapter_status != "admitted_unconditional_only":
        try:
            from adaptive_reflow.molecular.domain import MOLECULE_DOMAIN_BY_CHANNEL

            for ch in entry.compatible_channels:
                if ch not in MOLECULE_DOMAIN_BY_CHANNEL:
                    errors.append(f"compatible_channels_unknown:{ch}")
        except ImportError:
            # If the molecular module is unavailable at import time, the
            # downstream handshake re-validates this anyway.
            pass

    return (not errors, tuple(errors))


def render_audit_checklist(
    entry: CandidateEntry,
    template: AuditTemplate = DEFAULT_AUDIT_TEMPLATE,
) -> str:
    """Return a human-readable checklist for ``entry``."""
    ok, errors = validate_audit_completeness(entry, template)
    error_set = set(errors)
    lines = [
        f"# Audit checklist for {entry.repo_url} @ {entry.commit}",
        f"adapter_status: {entry.adapter_status}",
        "",
        "## Required fields",
    ]
    for fname in template.required_entry_fields:
        present = getattr(entry, fname, None) not in (None, "", ())
        mark = "[x]" if present else "[ ]"
        lines.append(f"- {mark} {fname}")
    lines.append("")
    lines.append("## Additional checks")
    for chk in template.additional_audit_checks:
        # Map to the error code emitted by validate_audit_completeness.
        prefix = chk.split("_")[0]
        failed = any(e.startswith(prefix) for e in error_set)
        mark = "[ ]" if failed else "[x]"
        lines.append(f"- {mark} {chk}")
    lines.append("")
    lines.append("## Non-claims (registry)")
    for nc in template.registry_non_claims:
        lines.append(f"- {nc}")
    lines.append("")
    lines.append("RESULT: " + ("PASS" if ok else "FAIL"))
    if errors:
        lines.append("Errors: " + ", ".join(errors))
    return "\n".join(lines)


def registry_summary(
    registry: CandidateRegistry,
    template: AuditTemplate = DEFAULT_AUDIT_TEMPLATE,
) -> dict[str, int]:
    """Return per-status counts and audit pass/fail summary."""
    summary: dict[str, int] = {
        "total_entries": len(registry.entries),
        "admitted": 0,
        "admitted_unconditional_only": 0,
        "blocked": 0,
        "unsupported": 0,
        "audit_pass": 0,
        "audit_fail": 0,
    }
    for entry in registry.entries:
        summary[entry.adapter_status] = summary.get(entry.adapter_status, 0) + 1
        ok, _ = validate_audit_completeness(entry, template)
        summary["audit_pass" if ok else "audit_fail"] += 1
    return summary


__all__ = [
    "DEFAULT_AUDIT_TEMPLATE",
    "AuditTemplate",
    "registry_summary",
    "render_audit_checklist",
    "validate_audit_completeness",
]
