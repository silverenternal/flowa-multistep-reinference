# Changelog

All notable changes to `flowa-multistep-reinference` are documented in
this file. The format follows [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/);
this project does **not** adhere to [Semantic Versioning](https://semver.org/)
because the contract surface evolves with the research questions, not
on a fixed cadence. Version markers in commit messages follow the
`vMAJOR.MINOR.PATCH` schema used by GitHub tags.

## [Unreleased] — S-tier governance upgrade

### Added

- `ROADMAP.md` — three-bucket (Now / Next / Later) roadmap anchored on
  `todo.json` and the S-tier closure list (DTB-R0 §3 case 2/5,
  ToyGaussianAdapter, synthetic oracle, stress test, reader docs). See
  the dated entries that close each of those items.
- `CONTRIBUTING.md` — single-maintainer contributor guide covering the
  four recurring workflows (hostile-case test, adapter, mutation test,
  docs scanner catalogue).
- `docs/DEPRECATION.md` — versioned deprecation table for the
  `adaptive_reflow.legacy/` quarantine subpackage; documents the
  removal schedule with no symbols removed yet.
- `docs/adr/0001-record-architecture-decisions.md` — meta-ADR adopting
  MADR 4.0 as the ADR format; this file is itself an example.
- `docs/adr/0002-typed-contracts-core-boundary.md` — pins
  `adaptive_reflow.contracts` as the canonical contract surface and
  freezes the import direction (contracts is leaf; molecular and
  universal may import from contracts but never the reverse).
- `docs/adr/0003-universal-vs-molecular-split.md` — freezes the
  universal / molecular split and requires a non-molecular adapter
  (ToyGaussianAdapter) as the proof artifact before any later universal
  surface change.
- `docs/adr/0004-engine-seven-step-operation-order.md` — pins the
  seven-step `Engine.run_round` operation order as a load-bearing
  invariant; changes require a new ADR.
- `docs/adr/0005-fail-closed-audit-code-policy.md` — pins the policy
  that every `AUDIT_*` constant is re-exported in the public
  `__init__.py` and indexed by `tools/check_docs_against_code.py`.
- `SECURITY.md` — explicit "no security-sensitive surface" statement
  with the standard supported-versions and reporting boilerplate.
- `CODEOWNERS` — assigns the load-bearing boundaries
  (`adaptive_reflow/contracts/**`, `adaptive_reflow/universal/**`,
  `adaptive_reflow/frame/engine.py`) to `@flowa-maintainer`; the rest
  of the repo inherits the same ownership.

### Changed

- The doc-drift scanner target was raised from 817 to 880+ verified
  claims as part of the S-tier upgrade; the scanner catalogue now
  resolves every governance-doc identifier in this changelog.
- `README.md` cross-references the new `ROADMAP.md`, `CONTRIBUTING.md`,
  `CHANGELOG.md`, `SECURITY.md`, `CODEOWNERS`, and `docs/adr/` files.

### Deprecated

- None. `adaptive_reflow.legacy/` is already quarantined and continues
  to emit `DeprecationWarning` on import; see `docs/DEPRECATION.md` for
  the removal schedule.

### Removed

- None. No public symbols were removed in this release. The eight
  legacy modules under `adaptive_reflow/legacy/` remain in place until
  their consumers are migrated (see `docs/DEPRECATION.md`).

### Fixed

- None at this release. The previous release's tests, ruff gate, and
  doc scanner (817 / 817 verified) remain green; the S-tier upgrade
  adds governance scaffolding without touching the typed-contracts core.

### Security

- None. The project has no security-sensitive surface (see `SECURITY.md`).
  The audit-code policy documented in ADR-0005 is a *contract-correctness*
  invariant, not a security boundary.

---

## [Unreleased] - Algorithmic Gap Closure

### Fixed

- A1: channel_rule stability-collapse is fail-closed on malformed inputs
- A2: bounded_merge_with_schedule honors per-channel floor config
- A3: bounded_merge uses prev anchored to last_emitted, not scheduled_cap
- A4: engine.run_round coerces round_index on all paths
- A5: engine emits ERR_CHANNEL_DOMAIN_UNDECLARED for undeclared domains
- B1: CosineScheduleSampler split compute/record for purity
- B2: engine wraps all adapter calls in _safe_adapter_call
- B3: claim_gate delegates to _resolve_decision helper (R7-ready)
- B5: bounded_merge emits MERGE_DEGENERATE_INTERVAL audit code
- C1: RMSPreservingCoordinateMixer renamed to EqualRmsCoordinateMixer with back-compat alias
- C2: bounded_merge_with_schedule rejects prev=None with ERR_PREV_REQUIRED
- C3: engine coerces bundle.source_round

### Added

- ADR-0006: engine-wraps-adapter pattern
- ADR-0007: prev-anchored bounded-merge
- ADR-0008: claim-gate deferral placeholder
- ADR-0009: mixer RMS-preservation precondition

---

## How to read this changelog

* Items in **Added** are user-visible additions to the public surface or
  to the governance docs.
* Items in **Changed** are behaviour-affecting modifications to existing
  surface. A reader who upgrades between two releases should diff the
  **Changed** sections.
* Items in **Deprecated** will be removed in a future release; the date
  appears in `docs/DEPRECATION.md`, not here.
* Items in **Removed** are gone. Search the diff between this and the
  previous release for the removal commit hash.
* Items in **Fixed** close a regression. They reference the test or
  fixture that pins the fix.
* Items in **Security** are reserved for vulnerabilities in the supply
  chain. Today this section is empty by construction (see `SECURITY.md`).