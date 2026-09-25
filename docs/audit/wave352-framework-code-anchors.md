# Wave 352 P4 — §3.4-§3.7 framework code-anchor cross-references (paper-A-final.md)

**Date:** 2026-09-25
**Wave:** 352 P4
**Status:** READY_TO_COMMIT
**Trigger:** §3 (Framework) §3.4-§3.7 enumerated the four typed-contracts framework innovations with verbose inline file:line references inside the "Algorithm signature" paragraph, but lacked a single-line summary anchor that lets reviewers click through to the implementation in one click. This wave adds a one-line code-anchor cross-reference to each subsection.
**Scope:** ADDITIVE one-line italicized anchor at the top of each of §3.4-§3.7 in `docs/drafts/paper-A-final.md`. No body-text edits, no equation changes, no claim ledger edits.

---

## 1. Executive Summary

| Item | Value |
|---|---|
| §3.4 anchor | `adaptive_reflow/universal/adapter.py:132` (`class AdapterCapabilities`) |
| §3.5 anchor | `adaptive_reflow/frame/ledger_chain.py:113` (`class LedgerChain`) |
| §3.6 anchor | `adaptive_reflow/contracts/state_machine.py:372` (`class StateMachine[TState, TEvent]`) |
| §3.7 anchor | `adaptive_reflow/algorithm/scheduler/protocols.py:157` (`class SchedulerProtocol(Protocol)`) |
| Anchor format | Single italicized line: `*Implementation: see [\`path:line\`](github_url) in the silverenternal/flowa-multistep-reinference repo.*` |
| Anchor placement | Immediately after each subsection heading, before the first prose paragraph |
| Number change | **NONE** — no equation, claim, or numerical value touched |
| New file | `docs/audit/wave352-framework-code-anchors.md` (this audit doc) |
| Modified file | `docs/drafts/paper-A-final.md` (4 ADDITIVE anchor lines at lines 115, 125, 135, 145) |
| Verification gates | `check_claims_consistency.py` PASS; `pytest tests/test_d4_regression_vectors.py -q` 30/30 PASS; mkdocs strict FAIL (pre-existing nav issue: `docs/CONTRIBUTING-cover-letter.md` not in nav — verified pre-existing by `git stash` + rebuild) |

---

## 2. Observed Facts

### 2.1 What was added to paper-A-final.md

Four ADDITIVE italicized anchor lines added, one per subsection, immediately after the heading and before the first prose paragraph:

- **§3.4** (line 115): `*Implementation: see [\`adaptive_reflow/universal/adapter.py:132\`](...) in the silverenternal/flowa-multistep-reinference repo.*`
- **§3.5** (line 125): `*Implementation: see [\`adaptive_reflow/frame/ledger_chain.py:113\`](...) in the silverenternal/flowa-multistep-reinference repo.*`
- **§3.6** (line 135): `*Implementation: see [\`adaptive_reflow/contracts/state_machine.py:372\`](...) in the silverenternal/flowa-multistep-reinference repo.*`
- **§3.7** (line 145): `*Implementation: see [\`adaptive_reflow/algorithm/scheduler/protocols.py:157\`](...) in the silverenternal/flowa-multistep-reinference repo.*`

Each anchor uses the standard GitHub URL pattern already established in the paper body: `https://github.com/silverenternal/flowa-multistep-reinference/blob/main/{path}#L{line}`.

### 2.2 Path:line anchor verification

All four anchor locations were verified against the live source tree before insertion:

| Subsection | Path:line | Definition verified |
|---|---|---|
| §3.4 | `adaptive_reflow/universal/adapter.py:132` | `class AdapterCapabilities:` at line 132 (paper inline ref says line 131; anchor uses the actual `class` definition line, 132, which is the click-target that renders correctly in GitHub's permalink view) |
| §3.5 | `adaptive_reflow/frame/ledger_chain.py:113` | `class LedgerChain:` at line 113 (matches paper inline ref exactly) |
| §3.6 | `adaptive_reflow/contracts/state_machine.py:372` | `class StateMachine[TState, TEvent]:` at line 372 (matches paper inline ref exactly) |
| §3.7 | `adaptive_reflow/algorithm/scheduler/protocols.py:157` | `class SchedulerProtocol(Protocol):` at line 157 (matches paper inline ref exactly) |

The §3.4 anchor line was bumped from 131 (the `@dataclass(frozen=True)` decorator line) to 132 (the `class AdapterCapabilities:` line) so that the GitHub permalink lands directly on the class declaration rather than on its decorator — this is the click-target a reviewer would expect from "the implementation".

### 2.3 Anchor line counts

Each anchor is a single italicized line (one Markdown paragraph wrapping at the rendered width). The four anchors together add ~4 lines + 4 blank-line separators = 8 lines to `docs/drafts/paper-A-final.md`. Total file line count went from 737 to 745 lines.

### 2.4 Verification gates

| Gate | Result | Notes |
|---|---|---|
| `python3 tools/check_claims_consistency.py` | **PASS** | "No drift detected." — 61 ACTIVE claims, 0 PROVISIONAL, 2 DEPRECATED. No CLM wording changed. |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30/30 PASS** | D.4 byte-stable regression suite green |
| `ruff check` (canonical scope) | **N/A** | No .py files touched |
| `mkdocs build --strict` | **FAIL pre-existing** | 1 nav warning (`docs/CONTRIBUTING-cover-letter.md` not in nav). Verified by `git stash` + rebuild before my changes (output matches). Unrelated to this wave. |

---

## 3. Interpretation

### 3.1 Why a one-line summary anchor, separate from the inline references

The §3.4-§3.7 subsections already contained many inline file:line references inside the "Algorithm signature" paragraph (the `AdapterCapabilities` description referenced 5 adapter files plus 2 test files; the `LedgerChain` description referenced 4 file:line anchors plus 3 test files; the `StateMachine` description referenced 4 file:line anchors plus 3 test files; the `SchedulerProtocol` description referenced 5 file:line anchors plus 3 test files). Reviewers reading the first paragraph of each subsection had to scroll past the prose to find the first inline anchor.

The new single-line summary anchor sits **between the heading and the first prose paragraph** so that a reviewer scanning the section heading immediately sees a click-through to the primary implementation file before reading the prose. This is the standard pattern for cross-reference papers (e.g., TNNLS / NeurIPS reproducibility checklists) where reviewers expect to find a code link at the top of each technical subsection.

### 3.2 Why only one anchor per subsection (additive, minimal)

Per Wave 268 strict-clean + AGENTS.md §3 hard guardrail #2 ("no destructive edits") + #7 ("Stricter = cleaner: pick the cleaner option, fewer files touched, fewer lines changed, more additive"), this wave adds exactly the minimum needed — a single italicized anchor per subsection — rather than rewriting the existing inline references or restructuring the section. The inline references inside the "Algorithm signature" paragraph are preserved verbatim because they are already load-bearing for the §3.4-§3.7 detailed prose.

### 3.3 Path:line accuracy

All four anchor locations were verified against the live source tree (`adaptive_reflow/` and `tests/`) before insertion. The GitHub permalink `#L{line}` fragment renders correctly in the public repo (the `#L132` fragment on `adapter.py` lands directly on the `class AdapterCapabilities:` line, not on the surrounding `@dataclass` decorator). The §3.4 anchor was deliberately adjusted from line 131 to 132 to land on the class declaration rather than the decorator — this is the click-target a reviewer would expect from "the implementation".

---

## 4. Unresolved Gaps (Honest Disclosures)

1. **Anchor lines do not match every test reference in the paper.** The paper's existing inline test references (e.g. `tests/test_capability_handshake.py`, `tests/test_ledger_chain.py`, `tests/test_state_machine_byte_deterministic.py`, `tests/test_protocol_conformance.py`) are not necessarily present at those exact paths in the current `tests/` tree (the actual test files live under `tests/test_engine/test_capability_dispatch.py`, `tests/test_frame/test_ledger_chain.py`, `tests/test_contracts/test_state_machine.py`, etc.). However, **this is a pre-existing paper drift issue, not introduced by this wave**. The anchor lines added by this wave point only to the primary implementation files (verified against the live source), not to test files, so this wave is robust against that pre-existing drift. **The pre-existing test-path drift is out of scope for this wave** (would require a separate Wave 352 P5 audit to fix the inline test references).

2. **§3.7 anchor points to `SchedulerProtocol` only, not to the other three protocols.** The paper's inline text for §3.7 claims `SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, and `RestartBlenderProtocol` all live in `adaptive_reflow/algorithm/scheduler/protocols.py:157`, but the actual codebase splits them across 4 files:
   - `SchedulerProtocol` → `adaptive_reflow/algorithm/scheduler/protocols.py:157`
   - `PolicyDriverProtocol` → `adaptive_reflow/algorithm/policy_driver.py:181`
   - `MergeOperatorProtocol` → `adaptive_reflow/algorithm/merge/merge_operator.py:249` (and duplicated in `adaptive_reflow/framework/interfaces.py:207`)
   - `RestartBlenderProtocol` → `adaptive_reflow/algorithm/blender/blender.py:425`

   The anchor picks the canonical `SchedulerProtocol` location because (a) the paper's existing inline reference points there, (b) `SchedulerProtocol` is the most-frequently-instantiated of the four protocols, and (c) the anchor line budget is one line per subsection. The discrepancy between the paper's "all four in protocols.py" claim and the actual code-split is a **pre-existing paper drift issue** preserved verbatim by this wave — fixing the paper's claim would be out of scope (a paper-claim change goes through the `flowa-paper-evidence` skill, not a one-line anchor wave).

3. **mkdocs strict fails due to pre-existing nav issue.** `docs/CONTRIBUTING-cover-letter.md` is not in the `mkdocs.yml` nav, which fails `--strict`. Verified pre-existing by `git stash` + rebuild (the same warning appears with my changes stashed). Unrelated to this wave's edits.

---

## 5. Files Modified (Wave 352 P4)

| File | Mode | Reason |
|---|---|---|
| `docs/drafts/paper-A-final.md` | MODIFIED | 4 ADDITIVE italicized one-line anchor paragraphs at lines 115 (§3.4), 125 (§3.5), 135 (§3.6), 145 (§3.7). Total +8 lines. |
| `docs/audit/wave352-framework-code-anchors.md` | **NEW** | This audit doc |

No CLAIMS.md edit (no claim changed; the anchors are paper-draft content, not claim ledger).
No `tnnls_submission/*.md` edit (paper-A-final.md is not in the tnnls_submission package; the tnnls_submission/MANIFEST.md `paper-A-final.md` row SHA-256 will need to be refreshed by the tnnls_submission package maintainer in a follow-up wave).
No vendored upstream edit (no `data/<vendored>/` touched).
No `tools/*.py` edit (no tools code touched).
No `adaptive_reflow/*.py` edit (no framework code touched — the anchors are read-only references to existing files).

---

## 6. Hard Requirements Before Commit (per AGENTS.md §2.1)

| Requirement | Status |
|---|---|
| `python3 tools/check_claims_consistency.py` exits 0 | **PASS** — "No drift detected" |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` 30/30 PASS | **PASS** — D.4 byte-stable regression suite green |
| `ruff check` 0 findings in any *.py touched | **PASS** — no .py files touched by this wave |
| `mkdocs build --strict` exits 0 | **FAIL pre-existing** — `docs/CONTRIBUTING-cover-letter.md` not in nav; verified by `git stash` + rebuild before my changes |
| Vendored upstream untouched (data/FlowMol3/, data/LineageFlow/, etc.) | **PASS** — no `data/<vendored>/` edits |
| No destructive edits (additive only) | **PASS** — ADDITIVE italicized anchor lines only; no body-text rewrite, no inline reference change, no claim wording change |
| NO-PUSH policy (per AGENTS.md §3 hard guardrail #3) | **PASS** — local commit only, awaiting user gating before push (consistent with `todo/PUSH-READY.md`) |
| Honest uncertainty (no provisional promotion by wording) | **PASS** — §4 unresolved gaps (3 items) preserve honest disclosures about the pre-existing test-path drift and §3.7 protocol-split drift |
| Per-phase audit doc (Wave format mirrors Wave 121-273) | **PASS** — this file (`wave352-framework-code-anchors.md`) follows the Observed/Interpretation/Unresolved-gaps template |
| SHA-256 columns regenerated for any `tnnls_submission/*.md` edit | **N/A** — no `tnnls_submission/*.md` edited in this wave; the tnnls_submission/MANIFEST.md `paper-A-final.md` row SHA-256 will need a follow-up refresh when the tnnls_submission package is next updated |
| TNNLS submission freeze is sacred (per AGENTS.md §3 hard guardrail #5) | **PASS** — additive only; no body-text change in the §3 framework narrative |

---

## 7. References

- **§3.4 Capability-Token Handshake** (`docs/drafts/paper-A-final.md` lines 113-121) — primary implementation `class AdapterCapabilities` at `adaptive_reflow/universal/adapter.py:132`
- **§3.5 Hash-Chained Ledger** (`docs/drafts/paper-A-final.md` lines 123-131) — primary implementation `class LedgerChain` at `adaptive_reflow/frame/ledger_chain.py:113`
- **§3.6 PEP 695 Generic State Machine** (`docs/drafts/paper-A-final.md` lines 133-141) — primary implementation `class StateMachine[TState, TEvent]` at `adaptive_reflow/contracts/state_machine.py:372`
- **§3.7 Typed Four-Port Wire Carrier** (`docs/drafts/paper-A-final.md` lines 143-149) — primary implementation `class SchedulerProtocol(Protocol)` at `adaptive_reflow/algorithm/scheduler/protocols.py:157`
- **Wave 352 P3 audit** (`docs/audit/wave352-l-local-appendix.md`) — predecessor wave; same paper-A-final.md touched (added Appendix A at lines 661-738)
- **Wave 351 P3 audit** (`docs/audit/wave351-thm5-numerical.md`) — source of the $L_\text{local}$ numerical validation cross-referenced in §6.6.1 footnote
- **AGENTS.md §2.1 `flowa-paper-evidence` skill** — governs paper-draft edits; this wave follows the "ADDITIVE only, no body-text rewrite, no claim wording change" constraint

---

**End of Wave 352 P4 audit doc — READY_TO_COMMIT (USER AUTHORIZED, NO PUSH)**