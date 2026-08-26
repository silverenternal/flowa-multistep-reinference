# Deprecation Policy

This document is the authoritative record of every deprecation in
`flowa-multistep-reinference`. The versioned table at the top tracks
**what** is deprecated and **when** it will be removed; the narrative
below explains **how** the policy works in practice and **why** we
quarantined `adaptive_reflow.legacy/` rather than deleting it.

## Deprecation table

| Feature | Introduced version | Deprecated in | Sunset version | Replacement | Removal version |
|---------|-------------------:|---------------|---------------:|------------|----------------:|
| `adaptive_reflow.legacy.control_policy` | pre-refactor | S-tier governance upgrade (Unreleased) | next minor (TBD) | `adaptive_reflow.policy.noise_mass` + `adaptive_reflow.writer.authority` | next minor +1 (TBD) |
| `adaptive_reflow.legacy.loop` | pre-refactor | S-tier governance upgrade (Unreleased) | next minor (TBD) | `adaptive_reflow.frame.engine.Engine` | next minor +1 (TBD) |
| `adaptive_reflow.legacy.loop_contract` | pre-refactor | S-tier governance upgrade (Unreleased) | next minor (TBD) | `adaptive_reflow.frame.operation.OperationCompositionContract` | next minor +1 (TBD) |
| `adaptive_reflow.legacy.mechanism_adapter` | pre-refactor | S-tier governance upgrade (Unreleased) | next minor (TBD) | `adaptive_reflow.universal.adapter.FlowMatchingODEAdapter` | next minor +1 (TBD) |
| `adaptive_reflow.legacy.metric_feedback` (ex `external_metric_feedback.py`) | pre-refactor | S-tier governance upgrade (Unreleased) | next minor (TBD) | `adaptive_reflow.eval.protocol` + `adaptive_reflow.eval.calibration` | next minor +1 (TBD) |
| `adaptive_reflow.legacy.orchestration` | pre-refactor | S-tier governance upgrade (Unreleased) | next minor (TBD) | `adaptive_reflow.frame.orchestrator.AdaptiveReflowPolicyOrchestrator` | next minor +1 (TBD) |
| `adaptive_reflow.legacy.plan` (ex `reinference_plan.py`) | pre-refactor | S-tier governance upgrade (Unreleased) | next minor (TBD) | `adaptive_reflow.schedule.cosine.CosineScheduleSampler` | next minor +1 (TBD) |
| `adaptive_reflow.legacy.restart_mixer` (ex `restart_memory.py`) | pre-refactor | S-tier governance upgrade (Unreleased) | next minor (TBD) | `adaptive_reflow.molecular.mixer.RMSPreservingCoordinateMixer` | next minor +1 (TBD) |
| `adaptive_reflow.legacy.services` | pre-refactor | S-tier governance upgrade (Unreleased) | next minor (TBD) | `adaptive_reflow.writer.handoff.CoreRuntimeHandoff` | next minor +1 (TBD) |

> **No symbols removed yet.** The table documents the policy; the
> removal versions are marked `TBD` because the S-tier upgrade is the
> first release that announces the deprecation. A concrete sunset tag
> will be added when each replacement lands its first non-preview
> release.

## Naming convention

A row in the table has five date-shaped cells:

* **Introduced version** — the first release that shipped the feature.
  Pre-refactor modules were carried over from the in-tree monolithic
  Python file layout; they have no formal version.
* **Deprecated in** — the first release that emits the
  `DeprecationWarning`. Today: "S-tier governance upgrade (Unreleased)".
* **Sunset version** — the first release in which the feature still
  works but is officially end-of-life. Code that still imports the
  feature in this version is *expected* to break in the next release.
* **Replacement** — the public-API symbol or subpackage that supersedes
  the deprecated feature. The replacement must already exist and be
  covered by tests before the deprecation is announced.
* **Removal version** — the first release in which the symbol no
  longer exists. Importing it raises a Python import error at
  import time.

A "no symbols removed yet" project uses the table as a forward-looking
ledger, not a backward-looking one. Rows are added when a feature is
first marked deprecated; rows are *not* removed when the removal
version is reached. The removal is recorded as a CHANGELOG entry instead.

## How the `legacy/` quarantine works

`adaptive_reflow.legacy/` is the destination for every pre-refactor
module that still has consumer code we have not yet migrated. The
quarantine policy is:

1. **Empty `__all__`.** Nothing in `legacy/` is re-exported from the
   package `__init__.py`. To reach a legacy symbol, callers must use
   the explicit form `from adaptive_reflow.legacy import plan`.
2. **`DeprecationWarning` on import.** The `legacy/__init__.py`
   module emits `DeprecationWarning` so any code path that accidentally
   reaches in is warned at import time.
3. **No new code may depend on `legacy/`.** The dependency-direction
   rules in `ARCHITECTURE.md` §3 are enforced by code review and by
   the doc scanner (`tools/check_docs_against_code.py`).
4. **Each legacy module has a replacement.** The table above names
   the replacement for every legacy module; the replacement is
   already shipped and tested before the deprecation is announced.
5. **Removal is staged.** A legacy module is removed in the release
   *after* its consumer code has been migrated off it. The migration
   itself is a separate PR so the diff stays auditable.

## Why a quarantine, not a deletion

The pre-refactor code is functionally a duplicate of the new public
surface — the eight modules in `legacy/` each have a one-to-one
replacement under `adaptive_reflow/frame/`, `adaptive_reflow/policy/`,
`adaptive_reflow/schedule/`, `adaptive_reflow/universal/`,
`adaptive_reflow/writer/`, or `adaptive_reflow/eval/`. The reason for
quarantining rather than deleting is that the legacy modules still
have **out-of-tree consumers** — the upstream `pocket_modules`
integration that owns the runtime executable path. Deleting the legacy
modules today would orphan those consumers before they migrate.

The quarantine therefore buys the migration window without:

* Forcing a hard fork at refactor time.
* Letting new in-tree code accidentally depend on the legacy surface.
* Letting the doc scanner catalog stale claims.

## Update cadence

* **At every release tag**, this file is reviewed and any row whose
  sunset version has passed is annotated as `ready_for_removal`. The
  actual removal happens in a separate PR (see point 5 above).
* **At every ADR that deprecates a new feature**, a row is added to
  the table and the relevant section of `CHANGELOG.md` is updated.
* **At every legacy module's replacement landing**, the row's
  `Sunset version` and `Removal version` cells are filled in with
  concrete tag names.

## See also

* **[ARCHITECTURE.md](../ARCHITECTURE.md) §3** — dependency-direction
  rules that forbid new code from importing `legacy/`.
* **[docs/adr/0001](adr/0001-record-architecture-decisions.md)** — the
  meta-ADR that defines how deprecation decisions are recorded.
* **[CHANGELOG.md](../CHANGELOG.md)** — every deprecation appears as a
  `Deprecated:` entry on the release that introduced it.