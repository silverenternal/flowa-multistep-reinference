# Wave 362 P2 — `reproduce/08_verify_R6_recipe.sh` R6 Recipe Verifier Harness

**Date:** 2026-09-27
**Author:** Wave 362 P2 (R6 verifier-harness agent — additive verifier + audit pass)
**Scope:** Author `reproduce/08_verify_R6_recipe.sh` (one-shot bash verifier for the Wave 362 P1 `R6_REPRODUCIBILITY_RECIPE.md`) so the R6 0.8-metric ("framework effect ~0.8" per Wave 361 forensic-evidence-chain user comment) has a **single-command reproducibility harness** that mirrors the existing `reproduce/verify_all_headlines.sh` per-cell pattern.
**Owning surface (NEW):** `reproduce/08_verify_R6_recipe.sh` (181-line bash verifier; 5 checks; exit 0 on PASS).
**Owning surface (AUDIT):** `docs/audit/wave362-p2-verify-r6-recipe.md` (this file).
**Adjacent edits:** none (ADDITIVE only — zero edits to `reproduce/*.sh`, zero edits to `paper-data/`, zero edits to `verification_outputs/`, zero edits to `tnnls_submission/`, zero vendored-repo edits).

---

## 1. Impact (smallest next action first)

The R6 LineageFlow k6 foldability cell now has a **single-command reproducibility harness** (`bash reproduce/08_verify_R6_recipe.sh`) that verifies a SHA-256 chain + python d_z reproduction + Wave 235 P3 best-cell verification, mirroring the per-cell verifier pattern from `reproduce/verify_all_headlines.sh` and `reproduce/07_R6_MNIST_TierAware.sh`. A reviewer can confirm the §7.2 STRONG verdict by running one bash command on the frozen Wave 161 substrate + Wave 233 P3 + Wave 235 P3 counterfactual evidence chain — without re-running the camera-ready-deferred live GPU 3-seed × N=1000 sweep.

**Smallest next action:** none required — this is a single-shot ADDITIVE verifier + audit. The R6 cell is now submittable at the **highest reproducibility standard** for a counterfactual-evidence-based paper cell: SHA-256-anchored + bash+python-verified + CPU-only + ~1 second wall time.

---

## 2. Observed facts (what the artifacts say)

### 2.1 Verifier script (NEW, this wave)

`reproduce/08_verify_R6_recipe.sh` — 181 lines, SHA-256 = `ba98ec60666d527ed9ceee9f707c109b04d93aa32749bff5186ef31863884d3e`, executable (`-rwxr-xr-x`).

The script is structured as 5 sequential checks, each guarded by `set -euo pipefail` and a per-check OK/FAIL summary:

| # | Check | Method | Expected outcome |
|---|---|---|---|
| 1 | Wave 161 frozen substrate SHA-256 (per-record foldability.jsonl) | `sha256sum < file` vs hard-coded hash | baseline `16482505…`, framework `b608edfb…` |
| 2 | Wave 233 P3 tier-aware counterfactual JSON SHA-256 | `sha256sum < file` vs hard-coded hash | `9a0c3eac…` |
| 3 | Wave 235 P3 grid-search uplift JSON SHA-256 | `sha256sum < file` vs hard-coded hash | `9a9dff18…` |
| 4 | Python snippet reproduces Wave 233 P3 tier-aware d_z = +0.2235 | embedded python heredoc; reads foldability.jsonl, applies constant-offset counterfactual on easy tier | d_z = 0.223463 ± 1e-4 |
| 5 | Wave 235 P3 best grid cell verification (cell_idx=3, easy_factor=0.0, hard_intensity=3.0) | embedded python heredoc; reads wave235 JSON; checks 6 fields | all 6 fields match |

The script mirrors the canonical 4-step pattern from `reproduce/verify_all_headlines.sh` and `reproduce/07_R6_MNIST_TierAware.sh` (venv-activate → data-check → embedded-Python verification → optional run command), but extends the data-check section to 3 separate SHA-256 checks (one per artefact group: substrate / wave-233 / wave-235) and the embedded-Python section to 2 separate heredocs (d_z reproduction + best-cell verification). This is the same pattern at slightly higher cardinality because the R6 evidence chain has 3 distinct SHA-256-anchored artefact groups (substrate + counterfactual + grid-search).

### 2.2 Verifier execution output (verified at this audit)

```
$ bash reproduce/08_verify_R6_recipe.sh
Step 1: verify Wave 161 frozen substrate SHA-256...
  OK: baseline + framework foldability.jsonl SHA-256 verified
Step 2: verify Wave 233 P3 tier-aware counterfactual SHA-256...
  OK: wave233-p3-tier-aware-r6.json SHA-256 verified
Step 3: verify Wave 235 P3 grid-search uplift SHA-256...
  OK: wave235-p3-r6-uplift.json SHA-256 verified
Step 4: reproduce Wave 233 P3 tier-aware d_z = +0.2235...
  reproduced d_z = 0.223463  (expected +0.223463)
  OK: Wave 233 P3 tier-aware d_z reproduced (+/-1e-4)
Step 5: verify Wave 235 P3 best grid cell...
  OK: Wave 235 P3 best cell verified (cell_idx=3, easy_factor=0.0, hard_intensity=3.0, d_z=0.646718)

OK: R6 recipe verified — SHA-256 chain + Wave 233 P3 d_z + Wave 235 P3 best cell
```

| Metric | Value |
|---|---|
| **Verifier exit code** | 0 |
| **Pass count** | 5 (one per step) + 1 final summary line = 6 OK lines total |
| **Fail count** | 0 |
| **Wall time** | <1 sec CPU (no GPU, no network) |
| **Reproduced d_z** | 0.223463 (matches expected +0.223463 to 6 decimal places; abs diff < 1e-4) |
| **Verified best cell d_z** | 0.646718 (matches expected +0.6467 to 4 decimal places) |

**Verifier execution: PASS.** All 5 step-level checks + the final summary line printed without any FAIL prefix. The reproduction d_z matches the Wave 233 P3 captured d_z to 6 decimal places, and the Wave 235 P3 best-cell d_z matches the recipe's expected value to 4 decimal places.

### 2.3 Hard-guardrail compliance (per AGENTS.md §3)

| Guardrail | Compliance |
|---|---|
| #1 — Vendored upstream is sacred | **n/a** — no `data/<Repo>/` touched |
| #2 — No destructive edits | **PASS** — zero `reproduce/*.sh` files modified; only `reproduce/08_verify_R6_recipe.sh` (NEW) and `docs/audit/wave362-p2-verify-r6-recipe.md` (NEW, this file) added |
| #3 — NO-PUSH policy | **PASS** — commit message ends with `(USER AUTHORIZED, NO PUSH)` |
| #4 — Honest uncertainty | **PASS** — no status promotion; no number touched; counterfactual methodology disclosure preserved verbatim from `R6_REPRODUCIBILITY_RECIPE.md §(d)` |
| #5 — TNNLS submission freeze | **n/a** — no `tnnls_submission/*` modified |
| #6 — Per-wave audit doc | **PASS** — this file is `docs/audit/wave362-p2-verify-r6-recipe.md` (mirrors the wave<NNN>-*.md pattern from Wave 121-273+) |
| #7 — Stricter = cleaner | **PASS** — 0 destructive edits; 2 NEW files only (this audit + the verifier); no existing reproduce/*.sh or paper-data/* touched |

### 2.4 Pre-commit verification gates (all PASS at this audit)

| Gate | Command | Result |
|---|---|---|
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, 3 warnings in ~4.04s |
| Claims consistency | `python3 tools/check_claims_consistency.py` | No drift detected (61 active + 2 deprecated) |
| Ruff lint | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed (0 findings) |
| Mkdocs strict build | `mkdocs build --strict` | Exit 0 (built in ~24.49s; only INFO messages about Black/Ruff formatter optionality) |
| R6 recipe verifier | `bash reproduce/08_verify_R6_recipe.sh` | Exit 0 (5/5 step-level PASS + 1 final summary; 0 FAIL) |

The 3 D.4 warnings are deprecation warnings for `RMSPreservingCoordinateMixer` + `RoundResultBundle` + `validate_round_result_bundle` (per Wave 356 P3 audit §2.2 item #1; not test failures).

---

## 3. Interpretation (what the agent concludes)

### 3.1 Why this verifier is sufficient (not a workaround)

The R6 §7.2 STRONG verdict (paper) is carried by the **counterfactual methodology applied to the frozen Wave 161 paired diff**, not by a live GPU re-run. The verifier bakes all three layers of the R6 evidence chain into a single bash command:

1. **Wave 161 frozen substrate** (`verification_outputs/k6_foldability_n1000_w161_q3_2026/`) is the **only GPU-generated artefact** in the R6 evidence chain — a single paired foldability sweep (N=1000 paired records, baseline vs framework, same seed 42/43/44 across both arms). This is the load-bearing evidence for "baseline pLDDT=42.07 vs framework pLDDT=43.20, paired Δ=+1.12" and "sc_perplexity 17.88 → 13.96, paired Δ=−3.92". Verifier check #1 confirms this artefact is byte-stable (SHA-256 chain verified).
2. **Wave 233 P3** is a CPU-only counterfactual script applying the Wave 209 P1 A3 / Wave 225 P4 REDUCED_INTENSITY_FACTOR=0.5 methodology on the per-record Wave 161 diff. It yields the §7.2 verdict (d_z=+0.2235 Bonf-sig at α=0.05/6=0.008333). Verifier check #2 confirms the Wave 233 P3 JSON is byte-stable; verifier check #4 reproduces the d_z to 6 decimal places via an independent python re-implementation.
3. **Wave 235 P3** is a 20-cell grid-search counterfactual on the same Wave 161 substrate, identifying the Pareto-optimal configuration (easy_factor=0.0, hard_intensity=3.0 → d_z=+0.6467). Verifier check #3 confirms the Wave 235 P3 JSON is byte-stable; verifier check #5 verifies the best-cell configuration (cell_idx=3, easy_factor=0.0, hard_intensity=3.0, d_z=0.646718, bonf_sig=true, easy_regression_eliminated=true).

The verifier's job is to make **all three layers** (substrate + counterfactual + grid-search) **byte-addressable and reproducible**, so a reviewer can verify the §7.2 verdict without re-running the 26-53 hour live GPU sweep. This is the same evidence chain that Wave 310 + Wave 336 + Wave 350 + Wave 361 already established; the verifier is a bash-executable front-door for the existing chain.

### 3.2 Mirroring the per-cell pattern from `verify_all_headlines.sh`

The verifier's structure mirrors the canonical per-cell pattern from `reproduce/verify_all_headlines.sh` and `reproduce/07_R6_MNIST_TierAware.sh`:

| Pattern element | `verify_all_headlines.sh` (master) | `07_R6_MNIST_TierAware.sh` (R6 per-cell) | `08_verify_R6_recipe.sh` (this wave) |
|---|---|---|---|
| `set -euo pipefail` | ✓ | ✓ | ✓ |
| Per-cell script invocation | `bash "${script}"` (subprocess) | n/a (this IS a per-cell script) | n/a (this IS a per-cell-equivalent verifier) |
| Data check via `test -f` | n/a (delegated to per-cell) | `test -f "${VOUT}"` | 3 separate `test -f` checks (substrate + wave-233 + wave-235) |
| SHA-256 verification | n/a (per-cell scripts check JSON contents) | n/a | 3 separate SHA-256 checks (one per artefact group) |
| Embedded Python heredoc | n/a (delegated to per-cell) | 1 heredoc (best cell verification) | 2 heredocs (d_z reproduction + best cell verification) |
| OK/FAIL summary | ✓ | ✓ | ✓ (per step + final summary) |
| Exit code | 0 (all PASS) / 1 (any FAIL) | 0 (PASS) / 1 (FAIL) | 0 (PASS) / 1 (FAIL) |

The new verifier extends the data-check + embedded-Python sections of the per-cell pattern (R6 has 3 SHA-256-anchored artefact groups instead of 1, and 2 numerical checks instead of 1), but follows the same overall structure (data check → python verification → OK/FAIL summary → exit code). A reviewer who knows how to invoke `bash reproduce/07_R6_MNIST_TierAware.sh` will know how to invoke `bash reproduce/08_verify_R6_recipe.sh` without consulting the docs.

### 3.3 What the verifier does NOT do

- Does **NOT** re-run the live GPU 3-seed N=1000 paired sweep (camera-ready deferred per Wave 352 P1 §3.4 + Wave 357 P5 §10.5 + Wave 359 P3 cuda:0 ONLY HARD CONSTRAINT).
- Does **NOT** modify the §7.2 STRONG verdict (counterfactual methodology preserved verbatim from `R6_REPRODUCIBILITY_RECIPE.md §(d)`).
- Does **NOT** modify `paper-data/R6_lineageflow_k6/R6_SOURCE.md` (out-of-scope per Wave 362 P1 audit §3.2 — the 3 stale SHA anchors are a separate Wave 363+ cleanup item).
- Does **NOT** touch vendored upstream code (the 9 vendored repos in `data/` remain byte-identical to upstream pinned commits per Wave 260 directive).
- Does **NOT** push to remote (NO-PUSH policy, USER AUTHORIZED only).
- Does **NOT** re-implement the Wave 233 P3 tier-aware d_z from first principles; it re-applies the constant-offset counterfactual on the per-record diff via a small embedded python snippet. The full Wave 233 P3 capture script is `scripts/wave233_p3_k6_tier_aware.py` (preserved verbatim); the verifier's embedded snippet is a *re-implementation of the same math* (constant shift on easy-tier diffs, preserves variance) for CI-friendly verification.

### 3.4 Why the verifier's reproduced d_z matches the Wave 233 P3 captured d_z to 6 decimal places

The verifier's embedded python snippet (Step 4) implements the **constant-offset counterfactual** (Wave 209 P1 A3 / Wave 225 P4 methodology) on the easy tier:

```python
# Apply REDUCED_INTENSITY_FACTOR counterfactual on easy tier (Wave 225 P4)
# Per Wave 209 P1 A3 / Wave 225 P4: add a CONSTANT offset to each easy-tier diff,
# shifting the easy-tier mean toward zero by REDUCED_INTENSITY_FACTOR * |uniform_mean|.
# This preserves per-record variance (constant shift does not change sd).
easy_idx = [i for i, t in enumerate(tiers) if t == "easy"]
uniform_easy_mean = sum(diffs[i] for i in easy_idx) / len(easy_idx)
offset = -REDUCED_INTENSITY_FACTOR * uniform_easy_mean  # negative-uniform_easy_mean is +|mean|
adj = list(diffs)
for i in easy_idx:
    adj[i] = diffs[i] + offset
```

This is mathematically equivalent to the `Wave 233 P3` real-scheduler implementation (`scripts/wave233_p3_k6_tier_aware.py` `_build_counterfactual_with_real_scheduler`), which applies the per-tier `n_cap_ratio` (0.5 on easy, 1.0 on medium/hard) to the **tier mean** while preserving per-record variance:

```python
# scripts/wave233_p3_k6_tier_aware.py:255-263
for t in [0, 1, 2]:
    mask = tier_per_record == t
    if not np.any(mask):
        continue
    mean_diff_tier = float(np.mean(diff[mask]))
    ratio_tier = float(n_cap_ratio[mask][0])
    new_mean_tier = ratio_tier * mean_diff_tier
    diff_counter_tier = diff[mask] - mean_diff_tier + new_mean_tier
    counter[mask] = b_plddt[mask] + diff_counter_tier
```

Both implementations apply `new_mean_tier = 0.5 * mean_diff_tier` on the easy tier (the hard and medium tiers are unchanged because their `n_cap_ratio = 1.0`). The constant-offset recipe `diffs[i] + offset` where `offset = -0.5 * uniform_easy_mean` is algebraically equivalent to the Wave 233 P3 per-tier mean rescaling — both shift the easy-tier mean by `-0.5 * uniform_easy_mean` while leaving the per-record variance untouched. Hence the verifier's reproduced d_z (0.223463) matches the Wave 233 P3 captured d_z (0.22346278288686192) to 6 decimal places.

**Methodology correction note:** An initial multiplicative-scaling attempt (multiplying easy-tier diffs by `0.5`) yields d_z = +0.248458, which is **wrong** because scaling also halves the per-record variance (sd). The constant-offset method (which preserves variance) is the canonical Wave 209 P1 A3 methodology and reproduces the Wave 233 P3 d_z exactly. The verifier embeds the correct constant-offset recipe.

---

## 4. Cross-references to owning surfaces (not modified)

- `paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md` (Wave 362 P1 deliverable, 11567 bytes, SHA = `a5ce94a0cd3645a06c1ee9104c158eff04838b8e9408ce1cafd5d53565758645`) — the recipe doc this verifier bakes into bash.
- `reproduce/verify_all_headlines.sh` (existing, 63 lines) — the master verifier whose per-cell invocation pattern this verifier mirrors.
- `reproduce/07_R6_MNIST_TierAware.sh` (existing, 99 lines) — the existing R6 per-cell reproduction script (Wave 235 P3 grid-search verification); this verifier complements it with a SHA-256 chain + d_z reproduction.
- `reproduce/08_verify_R6_recipe.sh` (NEW, this wave, 181 lines, SHA = `ba98ec60666d527ed9ceee9f707c109b04d93aa32749bff5186ef31863884d3e`) — the one-shot recipe verifier (this wave's deliverable).
- `verification_outputs/k6_foldability_n1000_w161_q3_2026/{baseline,framework}/foldability/foldability.jsonl` (Wave 161 frozen substrate, 1000 paired records per file) — the only GPU-generated artefact in the R6 evidence chain.
- `verification_outputs/wave233-p3-tier-aware-r6.json` (Wave 233 P3 counterfactual capture, SHA = `9a0c3eacc847c29a2844fb2ce4dc36f94def244ecbd4b4978fc0c1deeaf15851`) — the §7.2 verdict artefact.
- `verification_outputs/wave235-p3-r6-uplift.json` (Wave 235 P3 grid-search capture, SHA = `9a9dff1867efa54c8f542c86dfdb7f12fb18dd2998827b82fbd52769c3cc4030`) — the §7.2 uplift analysis artefact.
- `scripts/wave233_p3_k6_tier_aware.py` (Wave 233 P3 capture script, 484 lines) — the original tier-aware counterfactual script whose math the verifier re-implements.
- `scripts/wave235_p3_r6_uplift.py` (Wave 235 P3 grid-search script) — the original 20-cell grid-search script whose best-cell configuration the verifier checks.
- `docs/audit/wave361-r6-forensic-evidence-chain.md` (Wave 361 forensic audit) — establishes the R6 evidence chain the verifier bakes into bash.
- `docs/audit/wave362-p1-r6-recipe.md` (Wave 362 P1 audit) — the companion audit for the recipe doc this verifier bakes.
- `docs/CLAIMS.md` CLM-073 (R6 k6 pLDDT large-effect uplift) — ACTIVE; preserved verbatim.
- `docs/drafts/paper-A-final.md` §7.2 R6 row (line 535) — "R6 — LineageFlow k6 foldability (STRONG via tier-aware counterfactual)" — preserved verbatim.
- `docs/drafts/paper-A-final.md` §10.5 R6 live-GPU follow-up (lines 716-724) — preserved verbatim.
- `todo/RISK-REGISTER.md` R-019 (line 297) — R6 live GPU re-verification deferred item — preserved verbatim.

---

## 5. Provenance

- **Audit doc:** `docs/audit/wave362-p2-verify-r6-recipe.md` (this file, NEW)
- **Verifier script:** `reproduce/08_verify_R6_recipe.sh` (NEW, 181 lines, SHA = `ba98ec60666d527ed9ceee9f707c109b04d93aa32749bff5186ef31863884d3e`)
- **Recipe doc (companion):** `paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md` (NEW, Wave 362 P1 deliverable)
- **P1 audit (companion):** `docs/audit/wave362-p1-r6-recipe.md` (NEW, Wave 362 P1 deliverable)
- **Verifier exit code:** 0
- **Pass count:** 5 (Step 1 + Step 2 + Step 3 + Step 4 + Step 5)
- **Fail count:** 0
- **Wall time:** <1 sec CPU
- **Reproduced d_z:** 0.223463 (matches Wave 233 P3 captured d_z to 6 decimal places)
- **Verified best cell:** cell_idx=3, easy_factor=0.0, hard_intensity=3.0, d_z=0.646718, bonf_sig=true, easy_regression_eliminated=true
- **D.4 30/30 PASS:** PASS (verified post-edit; 30 passed, 3 warnings in ~4.04s)
- **Claims consistency:** PASS (verified post-edit; 61 active + 2 deprecated; no drift)
- **Ruff 0 findings:** PASS (all checks passed in 4-dir scope)
- **Mkdocs build --strict:** PASS (verified post-edit; documentation built in ~24.49s)
- **Date:** 2026-09-27 (Wave 362 P2 — R6 recipe verifier harness authored; verifier exits 0 on all 5 checks; SHA-256 chain + d_z reproduction + Wave 235 P3 best-cell verification all PASS)

---

_Last updated: 2026-09-27 (Wave 362 P2 — R6 reproducibility recipe verifier harness authored; SHA-256 chain + python d_z reproduction + Wave 235 P3 best-cell verification; exit 0 on all 5 checks; pass count 5; fail count 0)._