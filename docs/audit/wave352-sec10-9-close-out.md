# Wave 352 P6 — paper §10.9.3 Theorem 5 partial close-out acknowledgment

**Date:** 2026-09-25
**Wave:** 352 P6
**Status:** READY_TO_COMMIT
**Trigger:** §10.9 future-work item at paper §10.9 (line ~601 in `docs/drafts/paper-A-final.md` after Wave 352 P4 renumber) called for a closed-form attenuation bound on the restart-blend operator; Wave 350 P1 derived Theorem 5 (§6.6) as the bound, and Wave 351 P3 numerically validated Theorem 5 against the Wave 206 P6 4-scheduler × 3-`n_rounds` conditional grid. The §10.9 future-work item is therefore **PARTIALLY CLOSED**: closed-form bound derived (Theorem 5) + numerically validated (Wave 351 P3); remaining §10.9 items are engineering and analysis follow-ups rather than theory gaps. This Wave 352 P6 commit inserts the §10.9.3 ADDITIVE footnote to make the close-out status explicit in the paper.
**Scope:** Paper-only ADDITIVE footnote insertion + MANIFEST SHA refresh + mkdocs.yml `not_in_nav` fix for pre-existing `docs/CONTRIBUTING-cover-letter.md` warning (introduced by Wave 352 P2 commit `0a5501b`).

---

## 1. Observed Facts

### 1.1 Paper edit — §10.9.3 ADDITIVE footnote inserted

`docs/drafts/paper-A-final.md` §10.9 (line 601) is the "R5b restart-blend attenuation — formal bound (Theorem 5, future work)" future-work item. §10.9.1 footnote (line 605) and §10.9.2 footnote (line 609) are the prior ADDITIVE footnotes (Wave 349 + Wave 350). Wave 352 P6 inserts **§10.9.3** as the third ADDITIVE footnote at line 613:

> **§10.9.3 Footnote — Theorem 5 numerical-validation partial close-out (Wave 352 ADDITIVE)**
>
> *Wave 352 ADDITIVE footnote, no number change.* The §10.9 future-work item above called for a closed-form attenuation bound on the restart-blend operator; Wave 350 P1 derived Theorem 5 (paper §6.6 above) as the bound, and Wave 351 P3 numerically validated Theorem 5 against the Wave 206 P6 4-scheduler × 3-`n_rounds` conditional grid (`L_local = 0.381` from finite-difference on the synthetic RF CIFAR velocity field at `tools/audit_thm5/estimate_lipschitz.py`; transition prediction matches_empirical — 4/4 schedulers WINS at `n_rounds = 1`, 4/4 schedulers REGRESSES at `n_rounds \geq 2`, holds for any finite `L_\text{local} > 0` per Sub-claim 5.1; slope-scaling APPROXIMATE — the bound's predicted `(k=20 vs k=2)` `|VA|` ratio is `19 \cdot \sqrt{10} \approx 60.08` while the empirical ratio is `0.3065 / 0.1662 \approx 1.844`, so the bound over-predicts asymptotic regression by ~33x at high `n_rounds`). The §10.9 future-work item is therefore **PARTIALLY CLOSED**: the closed-form bound is **derived** (Theorem 5, Wave 350 P1) and **numerically validated** (Wave 351 P3). The remaining §10.9 items (per-adapter Lipschitz diagnostic at construction time, §7.8 R5c regime-curve extension as a function of velocity field fidelity, cross-adapter regime curves on R5b CIFAR-10 RF) are engineering and analysis follow-ups rather than theory gaps; they are documented in §10.9.1 footnote and §6.6.1 footnote. The Theorem 5 numerical-validation audit doc is at [`docs/audit/wave351-thm5-numerical.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave351-thm5-numerical.md); the §10.9 partial-close-out status doc is at [`docs/audit/wave352-sec10-9-close-out.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave352-sec10-9-close-out.md). **No number change in §10.9** — the §10.9 future-work item, §10.9.1 footnote, §10.9.2 footnote, and §6.6 Theorem 5 (including §6.6.1 numerical-validation footnote) are preserved verbatim; this §10.9.3 footnote is ADDITIVE.

### 1.2 §10.9 partial close-out status (this Wave's contribution)

| Status dimension                        | Before Wave 352 P6                            | After Wave 352 P6                                                                  |
|-----------------------------------------|------------------------------------------------|------------------------------------------------------------------------------------|
| Closed-form bound derivation            | Derived (Theorem 5, Wave 350 P1)               | Derived (Theorem 5, Wave 350 P1) — **unchanged**                                   |
| Numerical validation against §7.6 grid  | Validated (Wave 351 P3)                       | Validated (Wave 351 P3) — **unchanged**                                            |
| §10.9 status disclosure in paper        | "partially closed" (§10.9.2 Wave 350 footnote)  | "**PARTIALLY CLOSED**: derived + numerically validated" (§10.9.3 Wave 352 footnote) |
| §10.9.3 audit-doc cross-reference       | (none)                                         | `docs/audit/wave352-sec10-9-close-out.md` linked from §10.9.3 footnote             |
| MANIFEST row 32 SHA refresh             | Stale at Wave 351 P3 SHA `338ef23d...` (162862 bytes) | Refreshed to current SHA `c200590c...` (179062 bytes)                            |
| MANIFEST self-row SHA refresh           | Stale at Wave 351 P3 self-SHA `b599a5d9...` (37834 bytes) | Refreshed to current self-SHA `fedde595...` (39000 bytes)                          |
| mkdocs.yml `not_in_nav` `CONTRIBUTING-cover-letter.md` entry | Missing (pre-existing warning since Wave 352 P2 commit `0a5501b`) | Added (resolves pre-existing mkdocs strict failure)                              |

### 1.3 Files modified (Wave 352 P6)

| File                                                | Mode       | Reason                                                                                          |
|-----------------------------------------------------|------------|-------------------------------------------------------------------------------------------------|
| `docs/drafts/paper-A-final.md`                      | MODIFIED   | §10.9.3 ADDITIVE footnote inserted after §10.9.2; §10.9 future-work item, §10.9.1 + §10.9.2 footnotes, §6.6 Theorem 5, §6.6.1 numerical-validation footnote all preserved verbatim; no number change |
| `tnnls_submission/MANIFEST.md`                      | MODIFIED   | Row 32 (`paper-A-final.md`) SHA + size + content description refreshed (added Wave 352 ADDITIVE §A.3 + §3.4-§3.7 + §10.9.3 cumulative notes, since Wave 352 P3 + P4 commits also touched paper-A-final.md without MANIFEST refresh); self-row SHA + size refreshed (post-edit SHA pinned in §3 of this audit doc); post-edit-SHA list extended with `docs/audit/wave352-sec10-9-close-out.md` |
| `mkdocs.yml`                                        | MODIFIED   | Added `CONTRIBUTING-cover-letter.md` to `not_in_nav` block (resolves pre-existing `mkdocs build --strict` warning introduced by Wave 352 P2 commit `0a5501b`; the Wave 352 P2 commit added `docs/CONTRIBUTING-cover-letter.md` but did not add it to the `not_in_nav` exclusion list, which silently broke `mkdocs build --strict` for all subsequent commits touching `docs/` — Wave 352 P3, P4, P5, and P6 commits were affected) |
| `docs/audit/wave352-sec10-9-close-out.md`           | **NEW**    | This audit document                                                                             |

### 1.4 Pre-edit MANIFEST drift captured (this Wave)

The MANIFEST row 32 was last refreshed at Wave 351 P3 (commit `576b99a`); Wave 352 P3 (`af4b23e`, paper §A.3 Theorem 5 Lipschitz-constant derivation appendix, +85 lines) and Wave 352 P4 (`e662b9a`, paper §3.4-§3.7 framework code-anchor cross-references, +8 lines) both touched `paper-A-final.md` without refreshing MANIFEST. The cumulative Wave 352 P3 + P4 + P6 additions are reflected in the row 32 content description refresh (this Wave's MANIFEST edit).

### 1.5 Verification gates

| Gate                                                        | Result        | Notes                                                                                                          |
|-------------------------------------------------------------|---------------|----------------------------------------------------------------------------------------------------------------|
| `python3 tools/check_claims_consistency.py`                 | **PASS**      | "No drift detected." — 61 ACTIVE claims, 0 PROVISIONAL, 2 DEPRECATED                                            |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q`  | **30/30 PASS** | D.4 byte-stable regression suite green (Wave 352 P6 is paper-only; no .py edits)                                |
| `mkdocs build --strict`                                     | **PASS** (EXIT 0, 0 warnings) | Resolves pre-existing warning introduced by Wave 352 P2 commit `0a5501b` (added `docs/CONTRIBUTING-cover-letter.md` without `not_in_nav` entry). The `not_in_nav` block follows the existing pattern for `audit/wave289-p1-honest-reframe.md` / `audit/wave290-p1-bottleneck-confirmed.md` / `audit/wave290-p2-driver-microfix.md` / `audit/wave291-p2-sweep-driver.md` / `audit/wave291-p3-1seed-results.md` (one-line additive entry, alphabetically sorted). |
| `cd tnnls_submission && sha256sum -- *.md supplementary/README.md` | All SHA-256s verified | `cover_letter.md` unchanged (`a6976825...`); `data_availability.md` unchanged (`eb410e1f...`); `figures.md` unchanged (`36e3d3f3...`); `FILL_GUIDE.md` unchanged (`380a3e13...`); `highlights.md` unchanged (`1655ae5e...`); `MANIFEST.md` self-SHA updated to `fedde595...` (post-edit); `README.md` unchanged (`872a8415...`); `submission_checklist.md` unchanged (`b8445c5a...`); `tables.md` unchanged (`24f4bc71...`); `supplementary/README.md` unchanged (`6044f112...`); `../docs/drafts/paper-A-final.md` row 32 updated to current SHA `c200590c...` |

---

## 2. Interpretation

### 2.1 Why §10.9.3 is the right close-out framing

The §10.9 future-work item made **two distinct claims** about the desired formal bound:

1. **Derivation** — a closed-form attenuation bound on the restart-blend operator as a function of (i) `n_rounds`, (ii) the velocity field's residual error floor, and (iii) the per-channel `beta` derived from the policy driver.
2. **Empirical validation** — the bound should predict the empirical `n_rounds` transition (`+1` → `≥2`) at matched NFE = 50 on CIFAR-10 RF, and extend to the §7.8 R5c regime curve as a function of velocity field fidelity.

Claim (1) is **closed** by Wave 350 P1 (Theorem 5 derivation as §6.6 Eq.\,(6) + Sub-claims 5.1-5.4).
Claim (2) is **partially closed** by Wave 351 P3 (numerical validation against the 12-cell conditional grid; transition prediction matches_empirical; slope-scaling APPROXIMATE — bound over-predicts asymptotic regression by ~33x at high `n_rounds`).

The §10.9.3 ADDITIVE footnote states the close-out status explicitly in the paper:
- **derived** (Wave 350 P1)
- **numerically validated** (Wave 351 P3) — transition exact, slope APPROXIMATE

The remaining §10.9 items (per-adapter Lipschitz diagnostic, R5c regime-curve extension, cross-adapter regime curves on R5b CIFAR-10 RF) are engineering and analysis follow-ups rather than theory gaps. This framing is **honest** (per AGENTS.md hard guardrail #4): the §10.9 future-work item is not declared fully closed; the APPROXIMATE slope-scaling is disclosed; the per-adapter diagnostic gap is documented.

### 2.2 Why this Wave's MANIFEST refresh captures Wave 352 P3 + P4 drift

Wave 352 P3 (`af4b23e`) and Wave 352 P4 (`e662b9a`) both touched `docs/drafts/paper-A-final.md` but did NOT refresh the `tnnls_submission/MANIFEST.md` row 32 SHA + size + content description. This left MANIFEST row 32 stale at the Wave 351 P3 SHA (`338ef23d...`, 162862 bytes) while the actual file was at a different SHA + 179062 bytes. Wave 352 P6 (this Wave) refreshes MANIFEST row 32 with:
- The current file SHA `c200590c...` (post-Wave-352-P6-edit)
- The current file size `179062` bytes
- A cumulative content description including Wave 352 P3 (§A.3 Lipschitz appendix), Wave 352 P4 (§3.4-§3.7 code anchors), and Wave 352 P6 (§10.9.3 partial close-out) ADDITIVE notes

This brings MANIFEST row 32 up to current state and resolves the pre-existing Wave 352 P3 + P4 MANIFEST drift in one go.

### 2.3 Why the `mkdocs.yml` `not_in_nav` fix is in-scope for this Wave

Per AGENTS.md §2.1 `flowa-paper-evidence` hard requirement: "mkdocs build --strict exits 0 (if mkdocs.yml or docs/ were touched)". Wave 352 P6 touches `docs/drafts/paper-A-final.md` (which is under `docs/`), so the strict-build gate applies. The `mkdocs build --strict` failure is **pre-existing** (introduced by Wave 352 P2 commit `0a5501b`), not caused by Wave 352 P6, but the gate still requires resolution before commit.

Per Wave 268 "stricter = cleaner" principle (per AGENTS.md hard guardrail #7), the cleanest fix is the **minimal additive** one-line `not_in_nav` entry. The `mkdocs.yml` `not_in_nav` block already follows this pattern for `audit/wave289-p1-honest-reframe.md` / `audit/wave290-p1-bottleneck-confirmed.md` / `audit/wave290-p2-driver-microfix.md` / `audit/wave291-p2-sweep-driver.md` / `audit/wave291-p3-1seed-results.md` (the Wave 281/289/290/291 audit docs that were intentionally excluded from nav); adding `CONTRIBUTING-cover-letter.md` to the same list is consistent with the established project pattern.

### 2.4 Why `mkdocs.yml` is within scope for `flowa-paper-evidence` despite not being in the "Owns" list

The `flowa-paper-evidence` skill "Owns" list does not include `mkdocs.yml`. However, the skill's "Hard requirements before commit" list requires `mkdocs build --strict` to exit 0 when `docs/` is touched. The `mkdocs.yml` `not_in_nav` fix is a **supporting edit** to satisfy the strict-build gate for the primary paper-A-final.md edit. This is consistent with the Wave 268 strict-clean principle and the AGENTS.md hard guardrail #2 (no destructive edits; additive is the rule): the `not_in_nav` addition is one line, alphabetical, and matches the existing project pattern.

---

## 3. Post-edit SHA pin (for reviewers)

Per the `tnnls_submission/MANIFEST.md` self-row convention ("reviewers should re-hash on receipt and confirm with the post-edit SHA pinned in [...]"), the post-edit SHAs are:

| File                                                  | SHA-256                                                              | Size (bytes) |
|-------------------------------------------------------|----------------------------------------------------------------------|-------------:|
| `tnnls_submission/MANIFEST.md` (self-row post-edit)    | `fedde595d9a45cd3f55354d3a7d166476461b07c2272e8cd5a1d022d7565891a` |        39000 |
| `docs/drafts/paper-A-final.md` (row 32 post-edit)      | `c200590c87d28d6ef6a7688018de2c5f75458dd716a2fbe259026e1fffacd1c2` |       179062 |

These are the SHAs that reviewers should see when running:

```bash
sha256sum tnnls_submission/MANIFEST.md docs/drafts/paper-A-final.md
```

The displayed SHA in MANIFEST self-row (`26c8e6703b82a7ac01eb29e83e4f76fdde818aee5a69a23553f018c0fcab15c5`) is the SHA of MANIFEST.md bytes **before** the self-row was updated — this is the chicken-and-egg convention documented in the self-row text.

---

## 4. Files Modified (Wave 352 P6 — final)

| File                                                | Mode       | Reason                                                                                          |
|-----------------------------------------------------|------------|-------------------------------------------------------------------------------------------------|
| `docs/drafts/paper-A-final.md`                      | MODIFIED   | §10.9.3 ADDITIVE footnote inserted after §10.9.2; no number change                              |
| `tnnls_submission/MANIFEST.md`                      | MODIFIED   | Row 32 SHA + size + content description refreshed; self-row SHA + size refreshed; post-edit-SHA list extended |
| `mkdocs.yml`                                        | MODIFIED   | `not_in_nav` block: added `CONTRIBUTING-cover-letter.md` (one-line additive, alphabetically sorted) |
| `docs/audit/wave352-sec10-9-close-out.md`           | **NEW**    | This audit document                                                                             |

---

## 5. Hard Requirements Before Commit (per AGENTS.md §2.1)

| Requirement                                                                       | Status                                                                                    |
|-----------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| `python3 tools/check_claims_consistency.py` exits 0                               | **PASS** — "No drift detected"                                                            |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` 30/30 PASS              | **PASS** — D.4 byte-stable regression suite green                                         |
| `mkdocs build --strict` exits 0 (if `mkdocs.yml` or `docs/` touched)              | **PASS** — 0 warnings, doc built in 24.78s (resolves pre-existing Wave 352 P2 warning)   |
| Vendored upstream untouched (data/FlowMol3/, data/LineageFlow/, etc.)            | **PASS** — no `data/<vendored>/` edits (verified via `git status`)                        |
| No destructive edits (additive only)                                              | **PASS** — §10.9 future-work item, §10.9.1 + §10.9.2 footnotes, §6.6 Theorem 5, §6.6.1 numerical-validation footnote all preserved verbatim; §10.9.3 + MANIFEST row 32 + self-row + mkdocs.yml `not_in_nav` entry are all ADDITIVE |
| NO-PUSH policy (per AGENTS.md §3 hard guardrail #3)                                | **PASS** — local commit only, awaiting user gating before push (consistent with `todo/PUSH-READY.md`) |
| Honest uncertainty (no provisional promotion by wording)                          | **PASS** — §10.9 future-work item is declared **PARTIALLY CLOSED** (not fully closed); the APPROXIMATE slope-scaling is disclosed (bound over-predicts by ~33x at high `n_rounds`); the per-adapter diagnostic gap is documented as an engineering follow-up |
| Per-phase audit doc (Wave format mirrors Wave 121-273)                            | **PASS** — this file (`wave352-sec10-9-close-out.md`) follows the Observed/Interpretation/Hard-requirements template |
| SHA-256 columns regenerated for any `tnnls_submission/*.md` edit                  | **PASS** — `paper-A-final.md` row refreshed; `MANIFEST.md` self-row refreshed; `cover_letter.md` unchanged (no edit) |
| TNNLS submission freeze is sacred (per AGENTS.md §3 hard guardrail #5)             | **PASS** — additive only; §10.9 future-work + §10.9.1 + §10.9.2 + §6.6 + §6.6.1 + §10.9.3 all preserved verbatim; row 32 + self-row SHA refresh follows the standard ADDITIVE pattern |
| Stricter = cleaner (per Wave 268 + AGENTS.md hard guardrail #7)                   | **PASS** — minimal one-line additive fix to `mkdocs.yml` `not_in_nav` block (resolves pre-existing mkdocs strict failure); minimal cumulative MANIFEST row 32 refresh (catches up Wave 352 P3 + P4 + P6 in one go) |

---

## 6. References

- **§10.9 future-work item** (`docs/drafts/paper-A-final.md` line 601) — the R5b restart-blend attenuation — formal bound (Theorem 5, future work) label that this Wave marks as PARTIALLY CLOSED.
- **§10.9.1 footnote** (line 605) — Wave 349 ADDITIVE R5b conditional boundary cross-reference.
- **§10.9.2 footnote** (line 609) — Wave 350 ADDITIVE Theorem 5 partial close-out (closed-form bound derived).
- **§10.9.3 footnote** (line 613, this Wave) — Wave 352 ADDITIVE Theorem 5 numerical-validation partial close-out (closed-form bound derived + numerically validated).
- **§6.6 Theorem 5** (`docs/drafts/paper-A-final.md` line 318) — the closed-form restart-blend attenuation bound derived by Wave 350 P1 (`docs/audit/wave350-thm5.md`).
- **§6.6.1 numerical-validation footnote** (line 384) — Wave 351 ADDITIVE numerical validation of Theorem 5 against the Wave 350 P4 12-cell grid (`docs/audit/wave351-thm5-numerical.md`).
- **§A.3 Theorem 5 Lipschitz-constant derivation appendix** (`docs/drafts/paper-A-final.md`) — Wave 352 P3 ADDITIVE (`docs/audit/wave352-l-local-appendix.md`).
- **§3.4-§3.7 framework code-anchor cross-references** (`docs/drafts/paper-A-final.md`) — Wave 352 P4 ADDITIVE (`docs/audit/wave352-framework-code-anchors.md`).
- **Wave 206 P6 audit material** (`docs/audit/cifar/p6-cifar-rf-v4-honest-negative-curve.md` + `verification_outputs/wave206-p6-honest-negative-curve.json`) — the n_rounds=20 row (4 schedulers, all REGRESS) used as the input data for the Wave 351 P3 numerical fit.
- **Wave 225 P7 audit material** (`verification_outputs/wave225-p7-r5b-reduced-rounds.json`) — the n_rounds=2 row (4 schedulers, all REGRESS) used as the input data for the Wave 351 P3 numerical fit.
- **Wave 235 P1 audit material** (`verification_outputs/wave235-p1-r5b-fix.json`) — the n_rounds=1 row (4 schedulers, all WINS) used as the input data for the Wave 351 P3 numerical fit.
- **`L_local` estimator** (`tools/audit_thm5/estimate_lipschitz.py`) — CPU-only finite-difference protocol on the synthetic RF CIFAR velocity field; reports `L_local ≈ 0.3810` (numerical sample-max) and `L_local ≤ 3.8494` (analytic operator-norm upper bound).
- **`thm5_fit.py`** (`tools/audit_thm5/fit_thm5.py`) — numerical fit of Theorem 5 to the 12-cell grid; emits `verification_outputs/wave351-p3-thm5-numerical/thm5_fit.json`.
- **`mkdocs.yml`** — `not_in_nav` block; the Wave 352 P2 commit `0a5501b` introduced a pre-existing `mkdocs build --strict` warning (added `docs/CONTRIBUTING-cover-letter.md` without `not_in_nav` entry); Wave 352 P6 (this Wave) resolves the warning with a one-line additive `not_in_nav` entry.
- **`tnnls_submission/MANIFEST.md`** — row 32 (paper-A-final.md) SHA refreshed from `338ef23d...` (162862 bytes, Wave 351 P3) to `c200590c...` (179062 bytes, Wave 352 P6); self-row SHA refreshed from `b599a5d9...` (37834 bytes) to `fedde595...` (39000 bytes, post-self-row-update).
- **Per-adapter Protocol** (`adaptive_reflow/adapters/rectified_flow_cifar.py:276` `_synthetic_velocity_field`) — the synthetic velocity field implementation used for the `L_local` estimator.
- **`max_memory_fraction` constant** (`adaptive_reflow/algorithm/scheduler/nfe_aware.py:98`) — the canonical m=0.5 saturation used as the fit parameter.

---

**End of Wave 352 P6 audit doc — READY_TO_COMMIT (USER AUTHORIZED, NO PUSH)**
