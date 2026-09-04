"""Tests for the candidate registry, audit template, and FlowMol3 adapter
(DTB-G2 acceptance)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

# Make sure the project root is importable when tests are invoked from
# any CWD.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from adaptive_reflow.adapters import (
    FLOWMOL3_CHANNEL_DOMAINS,
    FLOWMOL3_CHANNELS,
    default_flowmol3_adapter,
)
from adaptive_reflow.frame import (
    StateBundle,
    validate_state_bundle,
)
from adaptive_reflow.universal.state import ODEConditionDelta
from adaptive_reflow.molecular.domain import MOLECULE_DOMAIN_BY_CHANNEL
from adaptive_reflow.writer import (
    DEFAULT_AUDIT_TEMPLATE,
    FLOWMOL3_PINNED_COMMIT,
    AdapterStatus,
    CandidateEntry,
    CandidateRegistry,
    TaskCondition,
    admit_entry,
    default_registry,
    make_default_flowmol3_entry,
    registry_summary,
    render_audit_checklist,
    validate_audit_completeness,
)

# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def _good_entry(
    *,
    adapter_status: AdapterStatus = "admitted",
    task_conditions: tuple[TaskCondition, ...] = ("pocket_conditioned",),
    commit: str = "a" * 40,
    paper_date: str = "2026-01",
) -> CandidateEntry:
    """Construct a structurally-valid CandidateEntry."""
    return CandidateEntry(
        repo_url="https://github.com/example/repo",
        commit=commit,
        license="MIT",
        paper_id="example-paper",
        paper_date=paper_date,
        task_conditions=task_conditions,
        dataset_split="train/val/test split manifest v1",
        native_metric_protocol="GNINA + QED via evaluator v1",
        ode_call_site="model.integrate",
        state_boundary="model.integrate -> state.detach()",
        condition_boundary="pocket-conditioned via model.compose_condition",
        restart_boundary="model.integrate restart boundary",
        compatible_channels=("coordinate", "charge", "raw_pair"),
        available_checkpoint="ckpt-001",
        adapter_status=adapter_status,
        audit_notes="paper + code evidence + parity report + capability manifest",
        registered_at="2026-08-25",
        registered_by="DTB-G2 audit",
    )


# ---------------------------------------------------------------------------
# Structural / construction tests
# ---------------------------------------------------------------------------


def test_default_flowmol3_entry_status_unconditional_only():
    entry = make_default_flowmol3_entry()
    assert entry.adapter_status == "admitted_unconditional_only"
    assert "pocket_conditioned" not in entry.task_conditions


def test_admitted_unconditional_only_cannot_carry_pocket_conditioned():
    with pytest.raises(ValueError, match="pocket_conditioned"):
        CandidateEntry(
            repo_url="https://example.com",
            commit="a" * 40,
            license="MIT",
            paper_id="bad",
            paper_date="2026",
            task_conditions=("pocket_conditioned",),  # <- forbidden combo
            dataset_split="x",
            native_metric_protocol="x",
            ode_call_site="x",
            state_boundary="x.detach",
            condition_boundary="x",
            restart_boundary="x",
            compatible_channels=("coordinate",),
            available_checkpoint=None,
            adapter_status="admitted_unconditional_only",
            audit_notes="should fail",
            registered_at="2026-08-25",
            registered_by="test",
        )


def test_empty_string_field_rejected():
    with pytest.raises(ValueError):
        CandidateEntry(
            repo_url="",  # <- empty
            commit="a" * 40,
            license="MIT",
            paper_id="x",
            paper_date="2026",
            task_conditions=("other",),
            dataset_split="x",
            native_metric_protocol="x",
            ode_call_site="x",
            state_boundary="x.detach",
            condition_boundary="x",
            restart_boundary="x",
            compatible_channels=("coordinate",),
            available_checkpoint=None,
            adapter_status="unsupported",
            audit_notes="x",
            registered_at="2026-08-25",
            registered_by="test",
        )


def test_invalid_adapter_status_rejected():
    with pytest.raises(ValueError):
        CandidateEntry(
            repo_url="https://example.com",
            commit="a" * 40,
            license="MIT",
            paper_id="x",
            paper_date="2026",
            task_conditions=("other",),
            dataset_split="x",
            native_metric_protocol="x",
            ode_call_site="x",
            state_boundary="x.detach",
            condition_boundary="x",
            restart_boundary="x",
            compatible_channels=("coordinate",),
            available_checkpoint=None,
            adapter_status="bogus",  # <- invalid literal
            audit_notes="x",
            registered_at="2026-08-25",
            registered_by="test",
        )


def test_invalid_task_condition_rejected():
    with pytest.raises(ValueError):
        CandidateEntry(
            repo_url="https://example.com",
            commit="a" * 40,
            license="MIT",
            paper_id="x",
            paper_date="2026",
            task_conditions=("not_a_real_condition",),
            dataset_split="x",
            native_metric_protocol="x",
            ode_call_site="x",
            state_boundary="x.detach",
            condition_boundary="x",
            restart_boundary="x",
            compatible_channels=("coordinate",),
            available_checkpoint=None,
            adapter_status="unsupported",
            audit_notes="x",
            registered_at="2026-08-25",
            registered_by="test",
        )


# ---------------------------------------------------------------------------
# Registry behaviour tests
# ---------------------------------------------------------------------------


def test_default_registry_seeds_flowmol3():
    reg = default_registry()
    assert len(reg.entries) == 1
    assert reg.entries[0].commit == FLOWMOL3_PINNED_COMMIT


def test_registry_hash_stable_across_construction_order():
    reg_a = default_registry()
    reg_b = CandidateRegistry(entries=tuple(reversed(reg_a.entries)))
    # Order-invariant: sorted by (repo_url, commit) before hashing.
    assert reg_a.registry_hash == reg_b.registry_hash


def test_admit_entry_appends():
    reg = default_registry()
    extra = _good_entry(adapter_status="admitted")
    reg2 = admit_entry(reg, extra)
    assert len(reg2.entries) == 2
    assert reg2.entries[1].adapter_status == "admitted"


def test_by_status_filters():
    reg = default_registry()
    extra_admitted = _good_entry(adapter_status="admitted")
    blocked = CandidateEntry(
        repo_url="https://github.com/example/blocked",
        commit="b" * 40,
        license="Apache-2.0",
        paper_id="blocked-paper",
        paper_date="2025-12",
        task_conditions=("other",),
        dataset_split="train/val/test",
        native_metric_protocol="internal-only",
        ode_call_site="model.integrate",
        state_boundary="model.state.detach()",
        condition_boundary="none",
        restart_boundary="model.integrate restart",
        compatible_channels=("coordinate",),
        available_checkpoint=None,
        adapter_status="blocked",
        audit_notes="audit failed: license incompatible with downstream use",
        registered_at="2026-08-25",
        registered_by="DTB-G2 audit",
    )
    reg2 = admit_entry(admit_entry(reg, extra_admitted), blocked)
    admitted = reg2.by_status("admitted")
    assert len(admitted) == 1
    assert admitted[0].paper_id == "example-paper"
    assert len(reg2.by_status("blocked")) == 1
    assert len(reg2.by_status("unsupported")) == 0


def test_admitted_only_includes_unconditional_only():
    reg = default_registry()
    extra = _good_entry(adapter_status="admitted")
    reg2 = admit_entry(reg, extra)
    assert len(reg2.admitted_only()) == 2  # FlowMol3 + the new admitted row


def test_registry_is_readonly():
    reg = default_registry()
    with pytest.raises((AttributeError, dataclass_FrozenInstanceError())):
        reg.entries = ()  # type: ignore[misc]


def dataclass_FrozenInstanceError():
    from dataclasses import FrozenInstanceError

    return FrozenInstanceError


# ---------------------------------------------------------------------------
# Audit template tests
# ---------------------------------------------------------------------------


def test_validate_audit_completeness_passes_for_good_entry():
    entry = _good_entry()
    ok, errs = validate_audit_completeness(entry)
    assert ok, errs


def test_validate_audit_completeness_fails_for_bad_commit():
    entry = _good_entry(commit="not-hex")
    ok, errs = validate_audit_completeness(entry)
    assert not ok
    assert any("commit" in e for e in errs)


def test_validate_audit_completeness_fails_for_non_https_url():
    entry = _good_entry()
    bad = CandidateEntry(
        **{**entry.__dict__, "repo_url": "http://example.com"}
    )
    ok, errs = validate_audit_completeness(bad)
    assert not ok
    assert any("repo_url" in e for e in errs)


def test_validate_audit_completeness_fails_for_unknown_channel():
    # __post_init__ itself doesn't check the channel against
    # MOLECULE_DOMAIN_BY_CHANNEL; only validate_audit_completeness does. So we
    # build the entry then validate.
    entry = CandidateEntry(
        repo_url="https://example.com",
        commit="a" * 40,
        license="MIT",
        paper_id="x",
        paper_date="2026",
        task_conditions=("other",),
        dataset_split="x",
        native_metric_protocol="x",
        ode_call_site="x",
        state_boundary="x.detach",
        condition_boundary="x",
        restart_boundary="x",
        compatible_channels=("not_a_real_channel",),
        available_checkpoint=None,
        adapter_status="unsupported",
        audit_notes="x",
        registered_at="2026-08-25",
        registered_by="test",
    )
    ok, errs = validate_audit_completeness(entry)
    assert not ok
    assert any("compatible_channels_unknown" in e for e in errs)


def test_render_audit_checklist_has_result_line():
    entry = _good_entry()
    txt = render_audit_checklist(entry)
    assert "RESULT: PASS" in txt
    assert "repo_url" in txt
    assert "non-claims" in txt.lower() or "non_claims" in txt.lower()


def test_registry_summary_counts():
    reg = default_registry()
    extra = _good_entry()
    reg2 = admit_entry(reg, extra)
    summary = registry_summary(reg2)
    assert summary["total_entries"] == 2
    assert summary["admitted"] == 1
    assert summary["admitted_unconditional_only"] == 1
    assert summary["audit_pass"] == 2
    assert summary["audit_fail"] == 0


def test_default_template_has_required_fields():
    template = DEFAULT_AUDIT_TEMPLATE
    assert "repo_url" in template.required_entry_fields
    assert "commit" in template.required_entry_fields
    assert "audit_notes" in template.required_entry_fields
    assert "registry_does_not_use_sota_ranking_as_admission_basis" in (
        template.registry_non_claims
    )


# ---------------------------------------------------------------------------
# FlowMol3 adapter tests
# ---------------------------------------------------------------------------


def test_flowmol3_pinned_commit_is_40_hex():
    assert len(FLOWMOL3_PINNED_COMMIT) == 40
    assert all(c in "0123456789abcdef" for c in FLOWMOL3_PINNED_COMMIT)


def test_flowmol3_adapter_capabilities_match_engine_protocol():
    adapter = default_flowmol3_adapter()
    caps = adapter.capabilities()
    assert caps.has_ode_integration_surface is True
    assert caps.has_continuous_channels is True
    assert caps.has_discrete_channels is True
    # D3 — FlowMol3 now declares has_condition_injection=True so the
    # engine handshake accepts it; the model itself is unconditional
    # and delegates to NullConditionInjector for audit provenance.
    assert caps.has_condition_injection is True  # D3 — null-condition injector
    assert caps.has_materialization_route is True  # D2 — materializer field wired
    assert caps.has_trajectory_digest is False  # placeholder
    assert caps.supported_channels == FLOWMOL3_CHANNELS
    # All channels must be declared in the adapter's own channel_domains
    # (the per-adapter replacement for the legacy
    # frame.adapter.DOMAIN_BY_CHANNEL molecule-only table).
    assert caps.channel_domains == FLOWMOL3_CHANNEL_DOMAINS
    for ch in caps.supported_channels:
        assert ch in caps.channel_domains


def test_flowmol3_build_initial_state_validates():
    adapter = default_flowmol3_adapter()
    state = adapter.build_initial_state(batch_id="batch-1", sample_id="sample-1")
    ok, errs = validate_state_bundle(state)
    assert ok, errs
    assert state.detach_proof is True
    assert state.source_round == 0
    assert set(state.channels) == set(FLOWMOL3_CHANNELS)


def test_flowmol3_build_initial_state_deterministic():
    adapter = default_flowmol3_adapter()
    s1 = adapter.build_initial_state(batch_id="b", sample_id="s")
    s2 = adapter.build_initial_state(batch_id="b", sample_id="s")
    assert s1.native_state_digest == s2.native_state_digest
    for ch in FLOWMOL3_CHANNELS:
        assert s1.channels[ch] == s2.channels[ch]


def test_flowmol3_solve_ode_produces_trace():
    adapter = default_flowmol3_adapter()
    state = adapter.build_initial_state(batch_id="b", sample_id="s")
    from adaptive_reflow.universal.state import ODEConditionDelta
    delta = ODEConditionDelta(
        delta_spec={"pocket": "ligand", "num_steps": 10},
        source="test",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )
    trace = adapter.solve_ode(state, delta, seed=42)
    assert trace.steps == 10
    assert 0.0 <= trace.accept_rate <= 1.0
    assert trace.native_state_digest is not None


def test_flowmol3_compose_condition_accepts_delta_via_null_injector():
    """D3 — FlowMol3's ``compose_condition`` delegates to
    :class:`NullConditionInjector` for non-empty deltas so the engine
    handshake's ``has_condition_injection=True`` gate is satisfied.
    The model itself is unconditional; the injector annotates the
    audit trail with null-condition provenance (``condition_kind='null',
    dataset='flowmol3_smiles_pl', variant='v1', round_trace_only=True``).
    """
    adapter = default_flowmol3_adapter()
    state = adapter.build_initial_state(batch_id="b", sample_id="s")
    # Non-empty delta is now accepted via NullConditionInjector (D3).
    delta = ODEConditionDelta(
        delta_spec={"pocket": "ligand"},
        source="test",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )
    out = adapter.compose_condition(state, delta)
    assert isinstance(out, ODEConditionDelta)
    # Empty delta is still allowed (back-compat).
    empty_delta = ODEConditionDelta(
        delta_spec={},
        source="test",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )
    same = adapter.compose_condition(state, empty_delta)
    assert isinstance(same, ODEConditionDelta)
    # P2-9: compose_condition now returns an ODEConditionDelta (Protocol
    # conformance). Provenance is recorded on the trace's source_round
    # delta_spec, not on the bundle.
    assert "flowmol3_adapter" in same.source


def test_flowmol3_apply_restart_distribution_revalidates():
    adapter = default_flowmol3_adapter()
    state = adapter.build_initial_state(batch_id="b", sample_id="s")
    out = adapter.apply_restart_distribution(state, policy=None)
    assert out.detach_proof is True
    assert out.native_state_digest != state.native_state_digest


def test_flowmol3_export_endpoint_is_identity():
    adapter = default_flowmol3_adapter()
    state = adapter.build_initial_state(batch_id="b", sample_id="s")
    assert adapter.export_endpoint(state) is state


# ---------------------------------------------------------------------------
# Cross-cutting: registry ↔ adapter ↔ engine handshake
# ---------------------------------------------------------------------------


def test_flowmol3_registry_entry_pairs_with_adapter():
    reg = default_registry()
    assert len(reg.entries) == 1
    entry = reg.entries[0]
    adapter = default_flowmol3_adapter()
    assert entry.commit == adapter.pinned_commit
    # The adapter's reported channels must be a subset of the entry's
    # declared compatible_channels.
    caps = adapter.capabilities()
    assert set(caps.supported_channels).issubset(set(entry.compatible_channels))


def test_engine_handshake_rejects_non_pocket_conditioned_for_pocket_claims():
    """Re-admitting the FlowMol3 row with pocket_conditioned must fail.

    The audit template doesn't do this check; the
    :class:`CandidateEntry` constructor does. This test asserts the
    non-claim boundary at the registry layer.
    """
    with pytest.raises(ValueError):
        # Same as default but with pocket_conditioned in task conditions.
        CandidateEntry(
            repo_url="https://github.com/zavalab/ML/tree/FlowMol3",
            commit=FLOWMOL3_PINNED_COMMIT,
            license="MIT",
            paper_id="FlowMol3",
            paper_date="2025",
            task_conditions=("pocket_conditioned",),  # <- would be invalid
            dataset_split="n/a",
            native_metric_protocol="model-internal",
            ode_call_site="integrate/step over (x, a, c, e)",
            state_boundary="state.detach()",
            condition_boundary="none",
            restart_boundary="integrate restart",
            compatible_channels=FLOWMOL3_CHANNELS,
            available_checkpoint=None,
            adapter_status="admitted_unconditional_only",
            audit_notes="pocket-conditioned claim not validated by FlowMol3",
            registered_at="2026-08-25",
            registered_by="DTB-G2",
        )


def test_registry_hash_is_deterministic_json():
    """Sanity-check that the hash matches an explicit JSON serialization."""
    reg = default_registry()
    payload = json.dumps(
        [
            {
                "repo_url": e.repo_url,
                "commit": e.commit,
                "license": e.license,
                "paper_id": e.paper_id,
                "paper_date": e.paper_date,
                "task_conditions": list(e.task_conditions),
                "dataset_split": e.dataset_split,
                "native_metric_protocol": e.native_metric_protocol,
                "ode_call_site": e.ode_call_site,
                "state_boundary": e.state_boundary,
                "condition_boundary": e.condition_boundary,
                "restart_boundary": e.restart_boundary,
                "compatible_channels": list(e.compatible_channels),
                "available_checkpoint": e.available_checkpoint,
                "adapter_status": e.adapter_status,
                "audit_notes": e.audit_notes,
                "registered_at": e.registered_at,
                "registered_by": e.registered_by,
            }
            for e in sorted(reg.entries, key=lambda x: (x.repo_url, x.commit))
        ],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    expected = hashlib.sha256(payload).hexdigest()
    assert reg.registry_hash == expected


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "--no-header", "-q"]))
