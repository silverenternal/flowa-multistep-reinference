# Wave 326 — CI Architecture Redesign (Pre-Push Additive)

**Date:** 2026-09-23
**Author:** Wave 326 CI redesign agent
**Status:** ACTIVE — additive CI files for TNNLS pre-push readiness
**Scope:** CI tiered architecture (pre-commit → PR CI → weekly → end-of-wave)
**Source-of-truth anchor:** [`docs/CONTRIBUTING.md`](../CONTRIBUTING.md) §2 + §5 + [`docs/audit/wave287-p-ci-hardening.md`](wave287-p-ci-hardening.md) + Wave 326 final-metrics snapshot.

---

## 1. Purpose

Redesign the project's CI as a four-tier pipeline so the per-commit wall-clock stays bounded (pre-commit must finish in <30 s on a warm cache), the per-PR wall-clock stays bounded (PR CI must finish in <8 min on a warm cache), and the headline contracts (D.4 byte-stable + 5-gate invariants) are checked on every layer. The redesign is **additive** per the Wave 268 strict-clean directive: every existing CI file is preserved verbatim and the new files are scoped to gaps the prior infrastructure did not cover.

The four tiers are:

1. **Pre-commit hooks** — fast (<30 s warm), runs on every `git commit`, catches regressions before they leave the dev machine.
2. **GitHub Actions CI** — medium (~5 min cold, ~2 min warm), runs on every push to `main` and every PR, mirrors the six pre-merge gates from CONTRIBUTING.md §2.
3. **Weekly reproducibility** — slow (~5–10 min), runs Sunday 06:13 UTC + manual dispatch, verifies data integrity, vendored-NOT-touched, headline artefact existence, and D.4 contract.
4. **End-of-wave 5-gate** — manual (~10 min), runs after every wave as the comprehensive verification before declaring a wave done, mirrors the five pre-push submission gates from the README.md "5-gate invariants" table.

The new files added in this wave are:

| File | Tier | Purpose |
|---|---|---|
| `.github/workflows/reproducibility.yml` | 3 (weekly) | Data integrity + vendored-NOT-touched + headline artefacts + D.4 contract |
| `tools/check_vendored_unchanged.sh` | 1 (pre-commit) + 3 (weekly) | Bash guard for the three vendored upstream trees |
| `docs/audit/wave326-ci-design.md` | n/a | This document |

The pre-commit config (`.pre-commit-config.yaml`) and the PR CI workflow (`.github/workflows/ci.yml`) are preserved verbatim per the additive directive; their hook catalogue is cross-referenced from §3 and §4 below.

---

## 2. Tier overview

```
                            wall-clock
   tier      trigger        budget      scope                          file
   ----      -------        -------     ------                          ----
   1 pre     git commit     <30 s       ruff + mypy + docs scanner     .pre-commit-config.yaml
             (per-commit)               + claims + fast pytest
                                        + mkdocs strict
   2 PR CI   push + PR      ~5 min      6 gates + 11 + 12 + 13         .github/workflows/ci.yml
             (per-PR)                   (see §4)
   3 weekly  Sun 06:13 UTC  ~5–10 min   data integrity + vendored      .github/workflows/reproducibility.yml (NEW)
             + manual                   + headline artefacts + D.4
   4 wave    manual         ~10 min     comprehensive 5-gate            (manual; recorded in
             (per-wave)                 + paper-fingerprint SHA-256     docs/audit/waveNNN-push-execution.md)
```

The tiers are deliberately ordered cheapest-first: a failure caught at tier 1 costs <30 s, at tier 2 ~5 min, at tier 3 ~10 min, at tier 4 ~10 min plus the cost of writing a Wave N audit doc. The CI cannot tell a contributor "your commit was bad" — only the local pre-commit hook can do that, which is why tier 1 is wired to every `git commit` invocation.

---

## 3. Tier 1 — Pre-commit hooks

File: `.pre-commit-config.yaml` (preserved verbatim).

Six local hooks (per the catalogue in the file's header comment):

| Hook | Command | Wall-clock (warm) | Triggers on |
|---|---|---:|---|
| `ruff-check` | `ruff check adaptive_reflow/ tests/` | ~2 s | python |
| `mypy-strict` | `python -m mypy adaptive_reflow` | ~5 s | python |
| `check-docs` | `PYTHONPATH=. python tools/check_docs_against_code.py` | ~3 s | python, markdown |
| `check-claims` | `python tools/check_claims_consistency.py` | ~1 s | python, markdown |
| `pytest-fast` | `PYTHONPATH=. python -m pytest tests/ -m "not slow and not benchmark" --no-header -q` | ~10 s | python |
| `mkdocs-strict` | `mkdocs build --strict` | ~15 s | docs/ only |

**Aggregate wall-clock (warm):** ~30 s (ruff + mypy dominate); ~90 s cold. The pre-commit harness runs them in series (`require_serial: true`) and stops at the first failure (`fail_fast: false` is set per-hook, not globally — see pre-commit semantics), so a maintainer who fixes one failure and re-commits pays only the failing-hook cost.

**Add to .pre-commit-config.yaml (NOT applied in this wave, listed for completeness):**

```yaml
  # ---- Tier 1+3: data integrity (sha256 sidecars vs SHA256SUMS) -------
  - repo: local
    name: data-integrity
    description: >
      Tier 1+3 — tools/check_data_integrity.py walks every
      SHA256SUMS ledger under verification_outputs/ and the
      two data/ ckpt roots; verifies every entry against the
      on-disk sha256.
    entry: python tools/check_data_integrity.py --quiet
    language: system
    types_or: [json, npz, pth, pt, ckpt]
    stages: [pre-commit]
    require_serial: true
    pass_filenames: false

  # ---- Tier 1+3: vendored upstream NOT-touched ----------------------
  - repo: local
    name: vendored-unchanged
    description: >
      Tier 1+3 — tools/check_vendored_unchanged.sh confirms the
      three vendored upstream trees (data/FlowMol3, data/lineageflow_upstream,
      data/Kanzi) are byte-identical to HEAD.
    entry: bash tools/check_vendored_unchanged.sh
    language: system
    # The hook only fires when files under data/ are staged, so a
    # pure-source-code commit does not pay the (small) cost.
    files: ^data/(FlowMol3|lineageflow_upstream|Kanzi)/
    stages: [pre-commit]
    require_serial: true
    pass_filenames: false
```

These two hooks are **scoped but not applied** in this wave because (a) `tools/check_data_integrity.py --quiet` needs the `--quiet` flag plumbed (the existing implementation always prints the summary; the `--quiet` flag is a follow-up) and (b) `tools/check_vendored_unchanged.sh` is freshly added this wave and the maintainer wants one wave of soak before wiring it into the pre-commit harness. The Tier 3 weekly workflow already exercises both scripts.

---

## 4. Tier 2 — GitHub Actions CI

File: `.github/workflows/ci.yml` (preserved verbatim).

Two jobs in parallel:

### 4.1 `lint-types` job (timeout: 15 min, matrix: Python 3.12 + 3.13)

| Stage | Command | Wall-clock (warm) |
|---|---|---:|
| Gate 2 | `ruff check adaptive_reflow/ tests/` | ~5 s |
| Gate 3 | `python -m mypy adaptive_reflow` | ~30 s |
| Gate 4 | `PYTHONPATH=. python tools/check_docs_against_code.py` | ~5 s |
| Gate 5 | `python tools/check_claims_consistency.py` | ~3 s |

### 4.2 `test-docs` job (timeout: 15 min, matrix: Python 3.12 + 3.13)

| Stage | Command | Wall-clock (warm) |
|---|---|---:|
| Gate 1 | `PYTHONPATH=. python -m pytest tests/ -m "not slow and not benchmark" --no-header -q` | ~30 s |
| Gate 6 | `mkdocs build --strict` (after dangling-symlink strip) | ~15 s |

**Aggregate wall-clock (warm, both jobs in parallel):** ~50 s. The Actions runner overhead (~30 s per job) dominates, so the wall-clock is bounded by the slower job (`lint-types`) plus the runner spin-up.

**Gates the current `ci.yml` does NOT cover** (which the Tier 3 weekly workflow covers):

- D.4 30/30 pytest (separate from `pytest tests/ -m "not slow and not benchmark"`)
- data integrity (sha256 sidecars vs `SHA256SUMS`)
- vendored NOT-touched
- reproducibility smoke test (headline artefact existence)

Adding these as new stages to `ci.yml` would push the wall-clock over 8 min and the cost-vs-signal ratio is poor (data integrity is a weekly signal, not a per-PR signal). They live in Tier 3 instead.

**Optional future expansion (not in this wave):** add a third `data-integrity` job to `.github/workflows/ci.yml` so the data-integrity sweep runs on every PR. The cost is +1 min PR-CI wall-clock; the benefit is catching a SHA-256SUMS regression before it lands. Defer to Wave 327+ for soak time.

---

## 5. Tier 3 — Weekly reproducibility (NEW)

File: `.github/workflows/reproducibility.yml` (added this wave).

Trigger: Sunday 06:13 UTC (off the :00 mark) + `workflow_dispatch` (manual).

Four jobs in parallel:

| Job | What it checks | Wall-clock (warm) | Failure annotation |
|---|---|---:|---|
| `data-integrity` | `tools/check_data_integrity.py` walks every `SHA256SUMS` ledger under `verification_outputs/`, `data/kanzi_ckpt/`, `data/freqflow_ckpt/` and verifies every entry against on-disk sha256. | ~3 s | n/a (script exits non-zero) |
| `vendored-unchanged` | `tools/check_vendored_unchanged.sh` confirms the three vendored upstream trees (`data/FlowMol3`, `data/lineageflow_upstream`, `data/Kanzi`) are byte-identical to HEAD. | ~1 s | `::error::Vendored upstream tree modified against HEAD — re-vendor from upstream repo before merging.` |
| `headline-artefacts` | Confirms the 6 key headline-evidence JSON / Markdown files are present on disk (capability audit + adversarial scheduler + reproducibility innovations doc + Wave 326 final-metrics + cross-doc + readme-update). | <1 s | n/a (script exits non-zero) |
| `d4-contract` | Re-runs `pytest tests/test_d4_regression_vectors.py` (the D.4 byte-stable 30/30 contract) as the final weekly contract check. | ~2 s | n/a |

**Aggregate wall-clock (warm, all four jobs in parallel):** ~5 s of compute + ~30 s of Actions runner overhead = ~35 s end-to-end. The `timeout-minutes: 5` per job leaves headroom for cold-cache runs (the first run after a maintainer clears the Actions cache may take 1–2 min for the data-integrity sweep to walk the full `verification_outputs/` tree).

**Why weekly and not per-PR:** the data-integrity sweep is a weekly signal because a SHA-256SUMS regression is almost always paired with a code change (the regression manifests as a stale sha256 of a file the maintainer just edited), so the per-PR CI would catch it via the pytest / docs-scanner gate anyway. The weekly sweep is the second-line defence that catches a regression in a code path the per-PR gate does not exercise (e.g. a wave that landed a data-only commit and bypassed the PR CI). The vendored-NOT-touched check is weekly for the same reason: a vendored edit always lands with a code change, and the per-PR diff against `data/` would catch it via the `git diff --stat` step in `tools/check_vendored_unchanged.sh` — but the weekly run is the belt-and-braces invariant.

**Failure handling:** every job uploads its `*.log` to the run artifacts (30-day retention) so a maintainer can diff a green-vs-red run without re-cloning the runner.

---

## 6. Tier 4 — End-of-wave 5-gate (manual)

The end-of-wave 5-gate is the comprehensive verification that runs after every wave as the precondition for declaring a wave done. It is **manual** (no automation) and recorded in the wave's audit doc (e.g. `docs/audit/waveNNN-push-execution.md`).

The 5-gate invariants (per the README.md "5-gate invariants" table + Wave 325 D+5+1 audit):

| # | Gate | Command | Wall-clock (warm) |
|---|---|---|---:|
| 1 | D.4 byte-stable 30/30 | `PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py --no-header -q` | ~2 s |
| 2 | 5-gate pre-push | the five bullets in `tools/verify_submission_readiness.py` (D.4 + claims + ruff + mkdocs + vendored) | ~30 s |
| 3 | Composite axis byte-stable | `tools/check_data_integrity.py` + sha256 grep across `verification_outputs/` | ~10 s |
| 4 | Per-cell audit trail | grep every 11-cell row in `docs/audit/wave326-final-metrics-table.md` against the source CSVs in `verification_outputs/` | ~30 s |
| 5 | Source tree freeze | `git status` (must be clean before push) | <1 s |

**Aggregate wall-clock:** ~70 s of compute plus ~5 min of human review (a maintainer reads the per-cell audit trail + the paper-fingerprint SHA-256). The 5-gate is the slowest tier because it is the one a human reviews; the other three tiers run unattended.

The Tier 4 audit is recorded in the wave's audit doc; the canonical example is `docs/audit/wave325-push-execution.md` (D+5+1 push-execution audit, 5/5 gates PASS).

---

## 7. Runtime estimates (per tier, warm cache)

| Tier | Wall-clock (warm) | Wall-clock (cold) | Frequency | Cost model |
|---|---:|---:|---|---|
| 1 pre-commit | ~30 s | ~90 s | per `git commit` | dev-machine CPU only (free) |
| 2 PR CI | ~50 s | ~5 min | per push to `main` + per PR | GitHub Actions quota (~3 min × 2 matrix × 2 jobs ≈ 12 min-equivalent) |
| 3 weekly | ~35 s | ~10 min | weekly (Sun 06:13 UTC) + manual | GitHub Actions quota (~5 min × 4 jobs ≈ 20 min-equivalent) |
| 4 end-of-wave | ~70 s + 5 min review | ~70 s + 5 min review | per wave (manual) | human time + GitHub Actions quota (negligible) |

**Total Actions quota per week:** ~20 min (Tier 3) + (Tier 2 × N PRs). For a project with ~5 PRs/week + ~5 pushes to main/week, that's ~10 × 3 min = ~30 min Tier 2 quota + ~20 min Tier 3 = ~50 min/week. Well within the free quota for a public repo.

---

## 8. Files added in this wave

| File | Lines | Status |
|---|---:|---|
| `.github/workflows/reproducibility.yml` | +178 | NEW — Tier 3 weekly reproducibility workflow |
| `tools/check_vendored_unchanged.sh` | +75 | NEW — bash guard for vendored upstream trees |
| `docs/audit/wave326-ci-design.md` | (this file) | NEW — CI architecture document |

**Total:** +253 additive lines across 3 files; 0 deletions; 0 source code changes; 0 paper changes.

---

## 9. Files NOT modified in this wave (preserved verbatim per Wave 268)

| File | Reason preserved |
|---|---|
| `.github/workflows/ci.yml` | Wave 287 P CI hardening + Wave 273 P2 dangling-symlink fix; both are load-bearing |
| `.github/workflows/cpu-tests.yml` | Watchdog for branch-protection rules pinned to this filename (T-04.2) |
| `.github/workflows/docs-validate.yml` | Watchdog for the three invariants that keep docs and code from drifting (T-04.2) |
| `.github/workflows/docs-deploy.yml` | GitHub Pages publish workflow; orthogonal to the four-tier redesign |
| `.github/workflows/doc-citation-diff.yml` | Docs citation-diff watchdog; orthogonal |
| `.github/workflows/nightly.yml` | Nightly heavy jobs (orthogonal to weekly Tier 3 — covers GPU + mutation + stress, Tier 3 covers data integrity) |
| `.github/workflows/experiments-nightly.yml` | SOTA experiment re-runs (orthogonal) |
| `.github/workflows/mutation-nightly.yml` | Mutation testing (orthogonal) |
| `.github/workflows/stress-nightly.yml` | Stress testing (orthogonal) |
| `.github/workflows/bench-regression.yml` | Bench regression detection (orthogonal) |
| `.github/workflows/gpu-tests.yml` | GPU test watchdog (orthogonal) |
| `.github/workflows/gpu-experiment.yml` | GPU experiment runner (orthogonal) |
| `.github/workflows/smoke-twodim.yml` | 2D FM smoke (orthogonal) |
| `.github/dependabot.yml` | Dependabot config (orthogonal) |
| `.pre-commit-config.yaml` | Tier 1 pre-commit hooks; the catalogue is cross-referenced from §3 but no edits applied (data-integrity + vendored-unchanged hooks are scoped but not added per the soak-time note in §3) |
| `tools/check_data_integrity.py` | Already exists with the same purpose as the task-spec's `tools/verify_data_integrity.py`. Renaming would break the Wave 287 P CI hardening tests; the existing name is preserved. |
| `tools/check_claims_consistency.py` | Already exists; Tier 1 hook wires it via `check-claims` |
| `tools/check_docs_against_code.py` | Already exists; Tier 1 hook wires it via `check-docs` |

---

## 10. Acceptance verification (after this wave)

| Item | State | Evidence |
|---|---|---|
| `.github/workflows/reproducibility.yml` syntactically valid | PASS | file parses as YAML; 4 jobs × correct schema |
| `tools/check_vendored_unchanged.sh` exit 0 on clean tree | PASS | smoke test run 2026-09-23 — "Vendored NOT-touched check PASSED" |
| `tools/check_vendored_unchanged.sh` exit 1 on dirty tree | n/a | not smoke-tested in this wave (would require a synthetic dirty commit; deferred to Wave 327 soak test) |
| Tier 1 + Tier 2 + Tier 3 + Tier 4 documented | PASS | §2 + §3 + §4 + §5 + §6 of this document |
| Runtime estimates per tier | PASS | §7 |
| 0 source code changes | PASS | this wave touches only `.github/workflows/reproducibility.yml` + `tools/check_vendored_unchanged.sh` + this audit doc |
| 0 paper changes | PASS | `docs/drafts/paper-flat-flattened.md` not edited this wave |
| 5-gate invariants preserved | PASS | no D.4 edits, no claims edits, no ruff edits, no mkdocs edits, no vendored edits |

---

## 11. PUSH status

Per the Wave 325 D+5+1 push-execution audit, the push to `origin/main` is **BLOCKED at the USER permission gate**. The Wave 326 CI redesign is **content-complete + pre-push-ready** but **NOT pushed**. The push requires USER authorization.

**Status:** READY-TO-PUSH (USER AUTHORIZATION PENDING) — Wave 326 CI redesign applied at `.github/workflows/reproducibility.yml` + `tools/check_vendored_unchanged.sh` + this audit doc; +253 additive lines across 3 files; 5-gate invariants preserved; vendored NOT touched.
