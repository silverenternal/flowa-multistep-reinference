# Manuscript citation integrity — §3.4–§3.7 test references + dead links

**Date:** 2026-10-12
**Scope:** Fix the fabricated/dead references in `docs/drafts/paper-A-final.md`
identified by a systematic link sweep during the Tier-1 gap-checklist pass
(`todo/SUBMISSION-GAP-CHECKLIST.md` GAP-18 + GAP-21). Repoint every cited test to
the real file, replace the fabricated pass counts with measured counts, fix the
`StateBundle` source link, and repoint two dead audit-doc links. **No headline
number, verdict, theorem, or metric changed.**
**Status:** COMPLETE. All gates green. Not pushed (NO-PUSH policy).

---

## 1. Observed facts

A `re` sweep over every `github.com/.../blob|tree/main/<path>` link in
`docs/drafts/paper-A-final.md` (73 distinct paths) found **15 missing paths**.

### 1.1 Fabricated test citations (§3.4–§3.7)

Ten cited test files **never existed in git history** (`git log --all -- <path>` →
empty) and do not exist on disk. Every such link 404s and every parenthetical
pass count is unverifiable. This was **already known**: `docs/audit/wave352-framework-code-anchors.md`
§2.1 item 1 recorded the drift as "out of scope" and it was never fixed.

| Cited (fabricated) | Cited count | Real file | Measured |
|---|---|---|---|
| `tests/test_capability_handshake.py` | 50/50 | `tests/test_engine/test_capability_dispatch.py` | 3 passed |
| `tests/test_adapter_capabilities_dataclass.py` | 30/30 | `tests/test_adapters/test_adapter_common.py` | 26 passed |
| `tests/test_ledger_chain.py` | 50/50 | `tests/test_frame/test_ledger_chain.py` | 17 passed |
| `tests/test_ledger_chain_parallel.py` | 25/25 | `tests/test_frame/test_round2_frame_uplifts.py` | 3 passed |
| `tests/test_state_machine_byte_deterministic.py` | 60/60 | `tests/property/test_state_machine_byte_determinism.py` | (hypothesis suite) |
| `tests/test_state_machine_hsm.py` | 40/40 | `tests/test_contracts/test_state_machine.py` | 56 passed |
| `tests/test_state_machine_typed_generics.py` | 20/20 | `tests/test_contracts/test_state_machine.py` | 56 passed |
| `tests/test_protocol_conformance.py` | 80/80 | `tests/test_universal/test_adapter_protocol_conformance.py` | 170 passed |
| `tests/test_condition_auto_wrap.py` | 40/40 | `tests/test_universal/test_condition_typed.py` | 46 passed |
| `tests/test_state_bundle_byte_stable.py` | 35/35 | — (no counterpart; see §1.2) | — |

The cited counts (50/50, 80/80, 60/60, …) do **not** match any real file's test
count.

### 1.2 A doubly-false claim (§3.7)

§3.7 claimed `tests/test_state_bundle_byte_stable.py` "certifies that the
`StateBundle.to_bytes()` serialisation is byte-stable". Two independent errors:
- `StateBundle` is a `@dataclass(frozen=True)` defined in
  `adaptive_reflow/universal/state.py:114`, **not** `adaptive_reflow/contracts/bundle.py`
  (the file §3.7 linked — it contains zero occurrences of `StateBundle`);
- `StateBundle` has **no `to_bytes()` method** at all.

The fabricated claim was removed (the sentence now cites the two real §3.7 tests).

### 1.3 Dead audit-doc links

- §7.11 R1 row → `docs/audit/wave280-p-framework-fallback-contamination.md`
  (missing) → repointed to `docs/audit/wave280-p-r1-sweep-result.md`.
- §7.8.1 → `docs/audit/wave183-p4-aggregate.md` (missing) → repointed to the real
  artifact `verification_outputs/wave183-p4-aggregate.py`.

The remaining 3 missing paths are `data/cifar/`, `data/kanzi/upstream/`,
`data/flowmol3/repo/` — vendored directories that resolve on a full checkout, not
in this tree.

## 2. Interpretation

- The functionality the citations describe is real and tested; **only the paths
  and counts were wrong** (a documentation-integrity defect, not a code defect).
- Per AGENTS.md guardrail #4 (honest uncertainty), a citation that cannot be
  verified must not remain. The fix replaces each with a verifiable file + a
  measured count.
- The PDF is built from `paper-A-final.tex` (a condensed IEEEtran build), which
  contains none of the affected text (`grep` = 0) — so **no `.tex` change and no
  PDF rebuild** are required; only the MANIFEST `.md` row.

## 3. Changes

- `docs/drafts/paper-A-final.md`: 4 "Verification reference:" tails rewritten
  (§3.4–§3.7) + the §3.7 `StateBundle` link + 2 dead audit-doc links. SHA
  `49e8880e85c1dac56551422cb039581a8adf74cd80472b644205db2c2b8baf33` (211553 B).
- `tnnls_submission/MANIFEST.md`: row 32 (and the duplicate row) re-hashed to the
  new `.md` SHA/size + an additive provenance note; self-SHA row updated.
- `todo/SUBMISSION-GAP-CHECKLIST.md`: GAP-18 + GAP-21 marked resolved.
- `mkdocs.yml`: this audit doc registered in `not_in_nav`.

## 4. Gate results

| Gate | Command | Result |
|---|---|---|
| readiness verifier | `python tools/verify_submission_readiness.py` | **READY_WITH_SKIPS: mypy_0** (exit 0) |
| claims consistency | `python tools/check_claims_consistency.py` | **PASS** — no drift (61 active) |
| docs-against-code | `python tools/check_docs_against_code.py` | **PASS** |
| D.4 byte-stable | `pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` | **72 passed / 0 failed** |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **PASS** |
| mkdocs strict | `mkdocs build --strict` | **PASS** — exit 0 |

## 5. Digests

| File | sha256 | size |
|---|---|---|
| `docs/drafts/paper-A-final.md` | `49e8880e85c1dac56551422cb039581a8adf74cd80472b644205db2c2b8baf33` | 211553 |
| `tnnls_submission/MANIFEST.md` | `55f0ba7fa580a5b5e3fe0d156e70fe545564a8b34b412d28a10c1f8b71328fb9` | 72765 |

**Self-referencing-SHA note.** `MANIFEST.md` row 47 displays the **pre-edit**
MANIFEST hash (`e9928c93…`, 72445 B); the **post-edit** MANIFEST hash is
`55f0ba7f…` (72765 B), recorded here per the established convention.

## 6. Deferred / follow-up

- **GAP-19** (stale Q1-odds citations across `SUBMISSION_READINESS.md` §5,
  `submission_checklist.md:87`, `MANIFEST.md` row-32 provenance) remains **OPEN** —
  it needs a decision on which estimate is canonical (50-65 vs 60-75) and whether
  the submission docs should carry a self-assessed acceptance probability at all
  (the manuscript removed it at Wave 370).
- **Deeper sweep:** only file *existence* was checked. A "right name, wrong file"
  sweep (a linked file exists but does not contain the referenced symbol) is not
  exhaustive — the `StateBundle` case was found by hand.
