# Wave 354 P4 — Cover Letter USER_TO_FILL Auto-fill Scaffolding

**Date:** 2026-09-25
**Author:** Wave 354 P4 (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — additive scaffolding; no number / no claim change; canonical `tnnls_submission/cover_letter.md` byte-stable (31 USER_TO_FILL grep hits preserved verbatim).
**Trigger:** User request relayed through workflow harness: "剩下能做的任务也用ultracode做一下,这些任务都要处理" — gap-fill the cover-letter auto-fill workflow with a structured, audit-trail-rich scaffolding JSON that gives every USER_TO_FILL placeholder a documented default value + provenance + rationale.
**Scope:** New `tnnls_submission/cover_letter_FILL_AUTOFILL.json` (17-entry structured scaffolding), this audit doc. **No edits to `tnnls_submission/cover_letter.md`, `tnnls_submission/FILL_GUIDE.md`, `tnnls_submission/MANIFEST.md`, `docs/CLAIMS.md`, `tools/render_cover_letter.py`, or `docs/drafts/paper-A-final.md`.**
**Hard-rule compliance:** ADDITIVE ONLY (no destructive edits); per Wave 268 strict-clean rule, per Wave 325 NO-PUSH policy, per `flowa-paper-evidence` skill (scaffolding owns only `tnnls_submission/cover_letter_FILL_AUTOFILL.json` + this audit doc); per AGENTS.md §3 guardrail #1 (no vendored code touched), #2 (no destructive edits), #3 (NO-PUSH), #4 (no wording promotion), #6 (per-phase audit doc), #7 (cleaner = fewer files touched).

---

## 1. Executive Summary

`tools/render_cover_letter.py` (Wave 351 P5 baseline + Wave 352 P2 interactive extension) already ships with a flat-dict `INTERACTIVE_DEFAULTS` dict that supplies exemplar default values for each of the 17 USER_TO_FILL placeholders. The helper renders a draft via `--config <flat.json>` or `--interactive` mode. **What was missing** is a structured, audit-trail-rich JSON scaffold that documents every default's provenance (where it came from) and rationale (why this exemplar was chosen) — independent of the renderer's code.

Wave 354 P4 closes this gap by introducing `tnnls_submission/cover_letter_FILL_AUTOFILL.json`, a 17-entry structured scaffolding with the schema:

```json
{
  "version": "wave354-p4-scaffold-v1",
  "auto_filled_count": 17,
  "placeholders": [
    { "id": "...", "default_value": "...", "source_path": "...", "rationale": "..." },
    ...
  ]
}
```

Each entry reuses the Wave 351 P5 / Wave 352 P2 `INTERACTIVE_DEFAULTS` exemplar value verbatim, anchors `source_path` to the FILL_GUIDE.md section + the helper script's `INTERACTIVE_DEFAULTS` dict, and provides a 1-sentence `rationale` that the user can scan to decide whether the exemplar is appropriate.

| Artifact | Role | Notes |
|---|---|---|
| `tnnls_submission/cover_letter_FILL_AUTOFILL.json` | Structured scaffolding (17 entries × 4 fields each) | This wave; SHA-256 pinned in §5 below |
| This audit doc | Documents the scaffolding, the schema, and the guardrail compliance | Wave 354 P4 governance doc |

| Acceptance gate | Result |
|---|---|
| `python3 -c "import json; d = json.load(open('tnnls_submission/cover_letter_FILL_AUTOFILL.json')); print(len(d['placeholders']))"` | **17** placeholders |
| `python3 tools/check_claims_consistency.py` | **No drift detected.** (61 active claims, 0 provisional, 2 deprecated; same as pre-wave) |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30 passed** (byte-stable regression preserved; not in scope but re-verified per Wave 268 strict-clean rule) |
| `ruff check tools/render_cover_letter.py` | **All checks passed!** (helper not modified; just re-verified) |
| Canonical `tnnls_submission/cover_letter.md` SHA-256 byte-stable | **PASS** (unchanged: `a6976825...`) |
| `tnnls_submission/cover_letter.md` USER_TO_FILL grep hits | **31 hits preserved** (17 fillable + 11 §0 documentation pointers + 3 §0 convention text; per FILL_GUIDE.md Wave 348 enumeration) |
| All 17 `default_value` strings reuse Wave 351 P5 / Wave 352 P2 `INTERACTIVE_DEFAULTS` | **PASS** (no newly invented names / emails / affiliations) |
| All 17 `source_path` strings anchor to FILL_GUIDE.md + `tools/render_cover_letter.py:INTERACTIVE_DEFAULTS` | **PASS** |

---

## 2. The 17 placeholders cataloged

| # | JSON key | Section | Line(s) | Default value (first 60 chars) |
|---:|---|---|---|---|
| 1 | `authors_block` | §opening header | 51–52 | `Hugo Huang, MIT CSAIL, 32 Vassar St, Cambridge, MA…` |
| 2 | `editor_header` | §opening header | 56 | `Prof. Ming Li, Department of ECE, University of Example…` |
| 3 | `reviewers_header` | §opening header | 60 | `(see §9 below — five reviewers listed with affilia…` |
| 4 | `editor_section9` | §9 | 986 | `Ming Li, Department of ECE, University of Example…` |
| 5 | `reviewer1_affiliation` | §9 | 1003 | `Meta AI Research (ProbFlow team) — to be confir…` |
| 6 | `reviewer1_email` | §9 | 1006 | `reviewer1.theory@example.com` |
| 7 | `reviewer2_affiliation` | §9 | 1017 | `Université Gustave Eiffel / LIGM (Vialard group)…` |
| 8 | `reviewer2_email` | §9 | 1020 | `reviewer2.convergence@univ-eiffel.fr` |
| 9 | `reviewer3_affiliation` | §9 | 1032 | `Stanford University (Lu DPM-Solver group) — to be…` |
| 10 | `reviewer3_email` | §9 | 1035 | `reviewer3.solver@stanford.edu` |
| 11 | `reviewer4_affiliation` | §9 | 1048 | `Meta AI (ESM-IF / EvolutionaryScale LineageFlow)…` |
| 12 | `reviewer4_email` | §9 | 1052 | `reviewer4.protein@meta.com` |
| 13 | `reviewer5_affiliation` | §9 | 1065 | `Department of Statistics, University of Example (…` |
| 14 | `reviewer5_email` | §9 | 1069 | `reviewer5.stats@example.edu` |
| 15 | `corresponding_author_name` | §11 closing | 1126 | `Hugo Huang` |
| 16 | `corresponding_author_affiliation` | §11 closing | 1127 | `MIT CSAIL, 32 Vassar St, Cambridge, MA, USA` |
| 17 | `corresponding_author_email` | §11 closing | 1128 | `hugo@example.com` |

(All 17 default_value strings are full text in the JSON; the table above is a 60-char preview.)

---

## 3. Source provenance — per-placeholder

Every placeholder's `source_path` anchor:

1. **FILL_GUIDE.md §N** (`tnnls_submission/FILL_GUIDE.md#N-...`) — the section describing what the field contains, with an `EXAMPLE_OR_HINT` exemplar that the scaffolding's `default_value` mirrors. FILL_GUIDE.md was last edited in Wave 348 (per MANIFEST.md row 25; SHA-256 `380a3e13...`).
2. **`tools/render_cover_letter.py:INTERACTIVE_DEFAULTS['<key>']`** — the flat-dict exemplar that the helper script ships with. Wave 351 P5 baseline introduced the dict (audit: `docs/audit/wave351-cover-letter-helper.md`); Wave 352 P2 added the interactive mode (audit: `docs/audit/wave352-cover-letter-interactive.md`).
3. **`docs/audit/wave351-cover-letter-helper.md`** + **`docs/audit/wave352-cover-letter-interactive.md`** — the Wave-level audit docs that introduced the `INTERACTIVE_DEFAULTS` dict and verified its 17-field round-trip.

The 4 reviewer-role anchors (ProbFlow / Convergence / ODE solver / Protein / Statistical) follow the §9 of the cover-letter itself, which already enumerates the expertise of each reviewer (cover_letter.md lines 1072-1148).

The 3 corresponding-author anchors (name / affiliation / email) follow FILL_GUIDE.md §9-§11, which already enumerates the corresponding-author fields in §11 closing.

---

## 4. Interpretation vs observed facts

### 4.1 Observed facts

- **`tnnls_submission/cover_letter.md` is byte-stable.** SHA-256 before this wave and after this wave is `a6976825d19276c4fbb98efb167cadac24ed94cc4013796e0961580ca3ebf6f1` (per the tnnls_submission `sha256sum` output above and the MANIFEST.md row 24 pinned SHA). The 17 USER_TO_FILL placeholders remain unchanged; 31 grep hits preserved verbatim.
- **`tools/render_cover_letter.py` is byte-stable.** Wave 351 P5 baseline + Wave 352 P2 interactive extension already shipped with `INTERACTIVE_DEFAULTS` containing all 17 exemplar values. The scaffolding reuses them verbatim — no new values invented.
- **`FILL_GUIDE.md` is byte-stable.** SHA-256 `380a3e13fbe6d479cb532fce6b8961d82dc24eb2036a89cf9d26e2a930305a41` (per MANIFEST.md row 25). The 11 sections §1-§11 each describe what one placeholder (or related placeholder group) must contain.
- **`tnnls_submission/cover_letter_FILL_AUTOFILL.json` SHA-256**: `fb6f3cc3bb6c8d518e1495ef58fca3ed33834f0ca870b96305e8d4b9c4e2bae1` (computed via `cd tnnls_submission && sha256sum cover_letter_FILL_AUTOFILL.json`). 17 entries, valid JSON, all 17 default values are non-empty.
- **No claim drift.** `python3 tools/check_claims_consistency.py` exits 0 — same 61 active / 0 provisional / 2 deprecated CLM distribution as pre-wave.
- **No byte-stable regression drift.** `pytest tests/test_d4_regression_vectors.py -q` → 30/30 PASS (same as pre-wave).
- **No code changes.** Only new file: `tnnls_submission/cover_letter_FILL_AUTOFILL.json` (scaffolding) + this audit doc.

### 4.2 Interpretation

The scaffolding closes a **structural readability gap** in the cover-letter auto-fill workflow. Before Wave 354 P4, the user had two ways to discover what value to put in each placeholder:

1. **Read FILL_GUIDE.md** (canonical 11-section guide with `EXAMPLE_OR_HINT` per section)
2. **Run `--interactive` mode and read the prompt defaults** (which are the `INTERACTIVE_DEFAULTS` dict from `tools/render_cover_letter.py`)

Both paths require the user to mentally cross-reference the section/line/labels. The scaffolding JSON provides a **single, audit-trail-rich, queryable artifact** that maps each placeholder to (a) the EXEMPLAR default, (b) the FILL_GUIDE.md section + INTERACTIVE_DEFAULTS line that back it, (c) a 1-sentence rationale explaining why the exemplar is appropriate.

Critically, **the scaffolding is not a drop-in `--config` input**. `tools/render_cover_letter.py --config` expects a flat dict with the 17 field names as top-level keys; the scaffolding has them nested under `placeholders[].id` for richer metadata. The `_schema_compatibility` note in the JSON documents how to derive the flat config:

```bash
# 1. Extract to flat config (17 fields as top-level keys)
python3 -c "
import json
d = json.load(open('tnnls_submission/cover_letter_FILL_AUTOFILL.json'))
flat = {p['id']: p['default_value'] for p in d['placeholders']}
json.dump(flat, open('/tmp/cover_letter_data.json', 'w'), indent=2)
"

# 2. Render the draft
python3 tools/render_cover_letter.py \
    --config /tmp/cover_letter_data.json \
    --output /tmp/cover_letter_filled.md

# 3. Review, override, apply
# ... (per FILL_GUIDE.md §"How to apply" steps 1-7)
```

Alternatively, the user can drop the scaffolding into `/tmp/cover_letter_data.template.json` and run `--interactive` mode (per Wave 352 P2 §"3-step quickstart" in `docs/CONTRIBUTING-cover-letter.md`); the `_interactive_prompt_one` helper already accepts any non-empty value as the new default, so the per-placeholder `default_value` strings become the prompt suggestions.

### 4.3 Why not a flat config (the alternative)

The flat config pattern was rejected because:

1. **No audit trail.** A flat dict `{"authors_block": "Hugo Huang, MIT CSAIL, ..."}` does not document where each value came from. Reviewers reading the file later would have no way to know which defaults came from FILL_GUIDE.md §N, which from `INTERACTIVE_DEFAULTS`, which were user-confirmed at submission time.
2. **No rationale.** A flat dict cannot carry the 1-sentence justification per field. The user would have to re-read FILL_GUIDE.md to understand *why* each EXEMPLAR was chosen.
3. **Risk of confusion with the canonical cover letter.** A flat config named `/tmp/cover_letter_data.filled.json` could be mistaken for the canonical cover letter content. The structured scaffolding (with `version`, `auto_filled_count`, `_about`, `_note`, `_schema_compatibility`) is clearly labelled as scaffolding — not as a cover-letter draft.

The Wave 351 P5 helper already supports the flat-config use case (via `--config <flat.json>`). This wave does NOT replace that path; it adds a richer artifact that the user can hand-flatten or use as a prompt-source for `--interactive`.

### 4.4 Unresolved gaps (deferred, not blockers)

- **Real researcher names / institutional emails.** The 17 `default_value` strings are EXEMPLARS from FILL_GUIDE.md + `INTERACTIVE_DEFAULTS`. The user must OVERRIDE every value with real names + institutional emails + a manual 5-year COI sweep (per FILL_GUIDE.md §4-§11) before submitting. This is documented in `usage_notes.review_and_apply` in the JSON itself.
- **Cover letter remains un-applied.** `tnnls_submission/cover_letter.md` still has 31 USER_TO_FILL grep hits (the 17 placeholders + 11 §0 documentation pointers + 3 §0 convention text). Submitting without filling the 17 placeholders will be rejected by the TNNLS Editorial Manager; the scaffolding gives the user a structured starting point, not an applied submission.
- **No `MANIFEST.md` SHA-256 update.** `tnnls_submission/cover_letter.md` SHA-256 is unchanged, so `MANIFEST.md` row 24 SHA remains valid. Only `cover_letter_FILL_AUTOFILL.json` is a new file; if the user wants it added to `MANIFEST.md` (recommended), a follow-up wave can pin its SHA-256 there.

---

## 5. SHA-256 ledger (computed after writing)

| File | SHA-256 |
|---|---|
| `tnnls_submission/cover_letter.md` (byte-stable, UNCHANGED) | `a6976825d19276c4fbb98efb167cadac24ed94cc4013796e0961580ca3ebf6f1` |
| `tnnls_submission/cover_letter_FILL_AUTOFILL.json` (NEW this wave) | `fb6f3cc3bb6c8d518e1495ef58fca3ed33834f0ca870b96305e8d4b9c4e2bae1` |
| `tools/render_cover_letter.py` (byte-stable, UNCHANGED) | (not recomputed; last edit Wave 352 P2) |
| `tnnls_submission/FILL_GUIDE.md` (byte-stable, UNCHANGED) | `380a3e13fbe6d479cb532fce6b8961d82dc24eb2036a89cf9d26e2a930305a41` |
| `docs/audit/wave351-cover-letter-helper.md` (byte-stable, UNCHANGED) | (not recomputed) |
| `docs/audit/wave352-cover-letter-interactive.md` (byte-stable, UNCHANGED) | (not recomputed) |

---

## 6. Guardrail compliance (AGENTS.md §3)

| Guardrail | Compliance |
|---|---|
| #1 Vendored upstream is sacred | **N/A** — no vendored code (`data/FlowMol3/`, `data/Lineageflow/`, `data/Kanzi/`, etc.) touched |
| #2 No destructive edits | **PASS** — only new file (`cover_letter_FILL_AUTOFILL.json`) + this audit doc; no edits to existing files |
| #3 NO-PUSH policy | **PASS** — committed locally; never pushed without explicit user gating |
| #4 Honest uncertainty | **PASS** — defaults are EXEMPLAR values (not newly invented); `_note` in JSON explicitly tells the user to OVERRIDE every value |
| #5 TNNLS submission freeze is sacred | **PASS** — `cover_letter.md` byte-stable (SHA unchanged); 17 USER_TO_FILL placeholders preserved; scaffolding is an OUT-of-band artifact |
| #6 Per-phase audit doc | **PASS** — this audit doc; format mirrors the 12-decimal-CLAIMS-table pattern from Wave 121-273 (Observed facts / Interpretation / Unresolved gaps) |
| #7 Stricter = cleaner | **PASS** — only 1 new file + 1 audit doc; no edits to existing 5+ files; the `usage_notes.review_and_apply` step reuses FILL_GUIDE.md §"How to apply" steps 1-7 rather than duplicating them |

---

## 7. Open follow-up (camera-ready deferred, not blockers)

1. **Apply the scaffolding to `cover_letter.md`** — the user must hand-flatten or run `--interactive`, override each EXEMPLAR with real names, and `cp` the rendered draft into place. The scaffolding provides the starting point; the user's review + override is the human-in-the-loop step.
2. **Optionally add `cover_letter_FILL_AUTOFILL.json` to MANIFEST.md** — pinning its SHA-256 in a new row alongside the other submission-package files. Recommended once the user finalises the cover-letter content (otherwise the SHA-256 will drift on every cover-letter edit).
3. **Wave 355+ cleanup** — if the scaffolding proves useful in practice, a follow-up wave could extend it to also include (a) `MANIFEST.md` row metadata, (b) `highlights.md` (5-bullet editor-facing summary), (c) `data_availability.md` per-cell provenance. Out of scope for this wave (only cover letter was requested).

---

**End of audit doc.**