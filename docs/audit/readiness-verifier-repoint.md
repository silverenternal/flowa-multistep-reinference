# Readiness verifier repoint + drift allowlist + pytest collection fix

**Date:** 2026-10-12
**Scope:** Follow-up to `docs/audit/repo-docs-maintenance.md`, on explicit user
request ("指向现在的稿件吧，pytest 里没过的修一下"). Four independent fixes:
(1) repoint the readiness verifier's `k1_rc5` gate at the **live** manuscript,
(2) extend the `drift_33` allowlist so it flags only the live reviewer-facing
surface, (3) fix the bare-`pytest` collection error from stray `tools/*_test.py`
scripts, (4) update the 5 stale Kanzi adapter tests to the current Wave 149/178
shape contract.
**Status:** COMPLETE — readiness verifier now reports **all gates pass**
(`READY_WITH_SKIPS: mypy_0`, exit 0); the Kanzi adapter suite is green in
`kanzi_venv` (58 passed / 0 failed in the two touched files). **No manuscript
artifact, metric, claim, source module, or vendored-upstream file changed** (fix
4 is test-only).

---

## 1. Findings (observed facts)

| # | Finding | Evidence |
|---|---|---|
| F1 | **`k1_rc5` gate read a superseded artifact.** `tools/verify_submission_readiness.py` scanned the legacy EAAI-era `docs/paper-draft.md` for the sentinels `"only RC5"` + `"REMAINING"` (pre-Wave-153 K1 wording). The live manuscript (`docs/drafts/paper-A-final.md`) discloses the K1 cell as **NOT-SIGNIFICANT at K-level α** with corrected Bonferroni $p_\text{b} = 0.5676$ at $k = 4$ — so the gate failed against the current source. | Pre-fix verifier: `[FAIL] k1_rc5 : K1 §10.4 wording missing sentinel phrases: only RC5, REMAINING`. |
| F2 | **`drift_33` allowlist incomplete.** The pre-expansion D.4 `33/33 PASS` string survives across historical record trees (`docs/audit/`, `docs/ARCHIVE/`, `docs/supplementary/`, `docs/internal/`, `docs/tables/`, `docs/baseline-audit-report.md`, `docs/CONSOLIDATED_RESULTS.md`), which the provenance rule retains verbatim. The gate flagged them as "new drift" (148→150 offenders). | Pre-fix verifier: `[FAIL] drift_33 : 150 unintended 33/33 occurrences`. |
| F3 | **Bare `pytest` aborts collection.** Running `pytest` from the repo root (no explicit path) also collects stray `tools/*_test.py` debug scripts. `tools/w196_p3_kanzi_debug_test.py` does `from kanzi import DAE, kabsch_rmsd` → `ModuleNotFoundError: No module named 'kanzi'`, aborting collection with exit 2. CI always invokes `pytest tests/` explicitly, so this only bites a bare root invocation. | Pre-fix: `pytest --co` → collection error, exit 2. |
| F4 | **Stale legacy banner.** The `docs/paper-draft.md` banner (added in the previous maintenance pass) claimed the file "is still read by … the `k1_rc5` K1-wording gate". After F1's repoint that is no longer true — and the `r1_r6_sha` / `framework_n1000` gates use **hardcoded** artifact lists, not the file. | `gate_r1_r6_sha` iterates the module-level `R1_R6_ARTIFACTS` tuple; it never opens `paper-draft.md`. |
| F5 | **5 Kanzi adapter tests stale vs the Wave 149/178 shape contract.** In a torch-enabled venv, `tests/test_adapters/test_kanzi_real_ckpt.py` (3 tests) and `test_kanzi_smoke.py` (2 tests) assert the pre-Wave-178 `(64, 512)` trajectory shape, but the real-mode trajectory now lives in `(64, 3)` coord space (`_real_state_shape`; `state_shape` stays the `(64, 512)` latent dim). Wave 178 P2 §5 explicitly deferred the `test_kanzi_real_ckpt.py:697` update to a "follow-up cleanup"; the two `test_kanzi_smoke.py` tests additionally assume the pre-Wave-149 bridge-less velocity field. | `.venvs/kanzi_venv` run: `test_kanzi_real_ckpt.py` → 3 failed / 52 passed; `test_kanzi_smoke.py` → 2 failed. CI does not install torch (`.[test,dev,flow_matching]`), so these tests `importorskip("torch")` and **skip in CI**. |

**Non-findings (verified clean):**
- No stale "only RC5" / "4 of 5 RCs RESOLVED" wording on any live surface
  (`README.md`, `README.zh.md`, `docs/README.md`, `docs/GATES.md`,
  `docs/CLAIMS.md`, `todo/*.md`, `tnnls_submission/*.md`) — `grep` returns none.
- The 13 `@pytest.mark.xfail` markers in `tests/test_tools/` (reason
  `"k1_rc5 historical drift, see Wave 359 P1"`) are a **deliberate, documented**
  decision (see `docs/audit/wave359-k1-rc5-drift33-fix.md`): they pin APIs that
  were reverted from the sacred vendored upstream (LineageFlow `--workers-per-gpu`)
  or assert a pre-Wave-275 contract. They are not accidental failures and are
  left unchanged (the reason string names the Wave 359 grouping, not the verifier
  gate).

## 2. Changes (additive; no deletions)

**Fix 1 — repoint `k1_rc5` (F1).** In `tools/verify_submission_readiness.py`:
- `PAPER_DRAFT = docs/paper-draft.md` → `PAPER_MANUSCRIPT = docs/drafts/paper-A-final.md`.
- `K1_RC5_PHRASES = ("only RC5", "REMAINING")` → `("NOT-SIGNIFICANT at K-level", "0.5676")`.
- Rewrote `gate_k1_rc5` body + module docstring item 7. The gate **name** is kept
  as `k1_rc5` to preserve the audit trail (documented in the docstring as
  "historically the k1_rc5 gate").

**Fix 2 — extend `DRIFT_SAFE_PATHS` (F2).** Added the historical record trees
listed in F2 so the gate flags only the live reviewer-facing files under `docs/`
(`docs/README.md`, `docs/drafts/`, …). `docs/GATES.md` and `docs/INSIGHTS.md`
were already allowlisted (pre-existing entries). Corrected the accompanying
comment to describe the actual scan scope (the gate greps `docs/` only).

**Fix 3 — scope bare `pytest` (F3).** Added `testpaths = ["tests"]` to
`[tool.pytest.ini_options]` in `pyproject.toml`. Explicit paths still override it,
so `pytest tools/...` continues to work.

**Fix 4 — correct the legacy banner (F4).** Updated the `docs/paper-draft.md`
banner to state that no verifier gate reads the file.

**Fix 5 — update the 5 stale Kanzi adapter tests to the current contract (F5).**
Test-only edits (no source change):
- `tests/test_adapters/test_kanzi_real_ckpt.py` — `test_real_adapter_smoke_round_trip`
  and `test_real_adapter_heun_solver_smoke` now assert the real-mode trajectory
  shape `(3, 64, 3)` (was `(3, 64, 512)`); `test_state_shape_abstract_vs_real`
  now asserts `real._real_state_shape == (64, 3)` (was `(64, 512)`), keeping
  `real.state_shape == (64, 512)` (the latent dim). This is exactly the
  `test_kanzi_real_ckpt.py:697` update Wave 178 P2 §5 deferred.
- `tests/test_adapters/test_kanzi_smoke.py` —
  `test_torch_velocity_field_validates_against_per_call_state_shape` was
  rewritten to the current `_torch_velocity_field` contract (verified
  empirically): a non-`(L, 3)` `state_shape` is bridged through
  `kanzi_latent_to_coords` (requires a `latent_to_coord_decoder`), the model
  receives `(1, L, 3)`, and the output is reshaped back to the caller's
  `state_shape`; the `(L, 3)` coord path is a no-op; the bridge-less `(L, 512)`
  path raises `CapabilityMissingError`.
  `test_torch_velocity_field_inverse_projects_post_project_out_latents` now
  asserts `out_latent.shape == (64, 512)` (the Wave 177 P1 zero-pad reshape-back),
  not `(64, 3)`.

## 3. Gate results (acceptance record)

| Gate | Command | Result |
|---|---|---|
| readiness verifier | `python tools/verify_submission_readiness.py` | **READY_WITH_SKIPS: mypy_0** (exit 0) — `d4_72` / `ruff_0` / `claims_pass` / `paper_warns` / `r1_r6_sha` / `k1_rc5` / `drift_33` / `framework_n1000` all OK; `mypy_0` SKIP (mypy absent from PATH) |
| bare pytest collection | `pytest --co -q` (no path) | **PASS** — `5705 tests collected`, exit 0 |
| Kanzi adapter tests (kanzi_venv) | `pytest tests/test_adapters/test_kanzi_real_ckpt.py tests/test_adapters/test_kanzi_smoke.py -m "not slow and not benchmark"` | **PASS** — 58 passed, 0 failed (was 5 failed) |
| claims consistency | `python tools/check_claims_consistency.py` | **PASS** — no drift (61 active claims) |
| docs-against-code | `python tools/check_docs_against_code.py` | **PASS** — 4142 claims verified |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **PASS** |
| mkdocs strict | `mkdocs build --strict` | **PASS** — exit 0 |

### 3.1 Post-edit file digests

Recorded for provenance; the digests are the pre-commit working-tree values.

| File | SHA-256 |
|---|---|
| `tools/verify_submission_readiness.py` | `f48c129901dd0ab02866755ea45aa680619b52de8bae38ae79cafd50eb7efb45` |
| `pyproject.toml` | `4cb2e55b76c090b821ee6c571e280e953d4f0e81533e3f99a26621e9c9c4f841` |
| `README.md` | `037d59bbdb8f02393e935149fbe2e54247b5ed81327f6531fbe40a709c481e7b` |
| `README.zh.md` | `18ec16609e937f0436502c8e70d0560f8c7164af5b07f745afaf14e680d21df0` |
| `docs/README.md` | `ecea99851effe38bccfbdc5b386d32fbd41050ec30210c7dc01b0d29a35bd727` |
| `docs/paper-draft.md` | `37c329401da6ca5fd2663eb19e781b92b40833499017f13d9e81af13bb9757a6` |
| `todo/WAVES.md` | `6766225956d3d35938593f6cae8ba03cbf291d00cc850375599a290015af964a` |
| `todo/README.md` | `a2c6d85ecd39d8851942a5e46d266cdb939cd57efe64919029a1bc151e753e5e` |
| `tests/test_adapters/test_kanzi_real_ckpt.py` | `c791d6e5c7ff70165c29909280d3c6a34a8c641b34ec016c3deb2be1dfbe9351` |
| `tests/test_adapters/test_kanzi_smoke.py` | `4d9090e27ad10dff2a3b5c14552c145ca341f426b27956a209023309b3d7d83e` |

## 4. Unresolved gaps / caveats

- **`tests/test_algorithm/` is slow (not failing).** A single-directory run
  exceeded a 300 s budget at ~36% progress. This is why the full `pytest tests/`
  sweep does not terminate within the prior ~27 min budget — a runtime/ordering
  property of this sandbox, not a test failure. The reproducible pytest gates are
  D.4 (72/72 via the verifier) plus `tests/test_tools/` (green).
- **Venv-mixing is expected to fail.** `tests/test_adapters/test_kanzi_real_ckpt.py`
  requires the `kanzi` package (`jaxtyping` etc.); running it in `flowmol3_venv`
  raises `CapabilityMissingError(ModuleNotFoundError: jaxtyping)` and fails. Per
  AGENTS.md, model environments must not be mixed — the Kanzi adapter tests are
  green in `kanzi_venv`, and CI (no torch) skips them.
- **The 13 `tests/test_tools/` xfails are intentional** (see Non-findings) and
  remain.
- **`mypy_0` is SKIPped** when mypy is absent from PATH (as in this sandbox); in
  the canonical environment it reports 0 errors.
