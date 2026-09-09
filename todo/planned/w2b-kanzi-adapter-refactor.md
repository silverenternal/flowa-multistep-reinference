# Wave 92 — Kanzi adapter refactor + upstream N-samples patch (close W2)

**Date:** 2026-09-09 (updated 2026-09-10)
**Owner:** framework maintainer
**Status:** 🔄 **IN PROGRESS** (Wave 92a ✅ + Wave 92b ✅ + Wave 92c in flight)
**Target:** close W2 honestly — fix 3 adapter constants + add upstream N-samples patch, then re-run N=1000 framework paper-metric sweep

> **Update 2026-09-10**: Wave 92a (constants fix `73c6978`) and Wave 92b (N-samples patch `60dcbb7`) **both landed**. Wave 92c (N=1000 Kanzi framework sweep) **in flight** (Task `wlc4t3ou8`).

> **Why this wave:** Wave 91 Phase 4 re-run revealed that even with the bridge wired + flag in place, framework arm paper-metric at N=1000 is NOT measurable on CPU. Root cause = 3 adapter constants are wrong by 8-16× and upstream `--n-samples` knob not honored (Kanzi was not patched in Wave 81 like LineageFlow was). Without fixing these, the bridge path dies after the first sample.

---

## 0. Problem statement (Wave 91 honest finding)

**Wave 91 Agent D re-run (commit `wnx9d1947`) output:**
- Setup verified (5/5)
- Smoke test (limit=5) passed: 6 metrics computed, mean RMSD=2.54 Å, std=0.17 Å
- N=1000 background sweep started at 20:12 CST, **died after first sample** (`bridge x_final shape = (64, 64)` is wrong; should be `(L, 512)` for real ckpt)
- Output dir empty; log frozen at 4 lines
- Per-record time ~7s × 1000 ≈ 2h+ CPU budget not viable

**Root cause from Wave 91 Phase 1 audit §4:**

| Constant | Adapter | Real ckpt (`model_cfg`) | Effect on sweep |
|---|---|---|---|
| `KANZI_LATENT_DIM` | 64 | **512** | bridge expects `(L, 512)`, adapter emits `(L, 64)` → shape mismatch on first sample |
| `KANZI_VOCAB_SIZE` | 64 | **1000** | categorical sample range wrong |
| `KANZI_AR_SEQ_LENGTH` | 64 (fixed) | **backbone-dependent** (39..155) | per-record L mismatch |
| `KANZI_STATE_SHAPE` | `(64, 64)` | `(L, 512)` | same root cause as `KANZI_LATENT_DIM` |

**Additional gap**: `tools/run_real_ckpt_eval.py` has `--upstream-n-samples` knob but for Kanzi it goes through `tools/upstream_eval.py:347` which reads one line per call (LineageFlow Wave 81 patched this; Kanzi did not).

---

## 1. Goal

3 sequential waves (1 agent each, single commit each):

### Wave 92a: Fix Kanzi adapter constants
- Refactor `KANZI_LATENT_DIM/VOCAB_SIZE/AR_SEQ_LENGTH` to **load from ckpt `model_cfg`** at adapter init time
- Keep `KANZI_STATE_SHAPE` for backwards compat (synthetic-shape tests)
- Update 18+ test assertions to match new contract
- D.4 byte-stable preserved (use `KANZI_ABSTRACT_LATENT_DIM=64` constant for synthetic tests)

### Wave 92b: Add upstream N-samples patch (LineageFlow Wave 81 pattern)
- Patch `tools/upstream_eval.py` for Kanzi: read all records, accumulate metrics, write single output
- Mirror LineageFlow Wave 81 commit (`Wave 81 Agent C: Wave 81 Agent C — N=1000 LineageFlow upstream eval sweep`)
- Add regression test for N-samples patch

### Wave 92c: Re-run N=1000 framework paper-metric sweep
- Now that adapter emits `(L, 512)` shape AND upstream N-samples is honored
- Should produce 6 metrics with N=1000 each
- Time: ~30-60 min on CPU (after fix, ~7s/sample × 1000 = 2h budget reduced to ~30 min because bridge shape matches)

---

## 2. Wave 92a — Fix Kanzi adapter constants (1 agent, single commit)

### File: `adaptive_reflow/adapters/kanzi.py`

**Strategy** (audit doc §6 plan b, then refactor):
1. Keep `KANZI_ABSTRACT_LATENT_DIM = 64` for framework-algorithm testing (don't break 18+ tests)
2. Add new method `KanziAdapter._load_ckpt_dims()` that reads `model_cfg` from real ckpt
3. Set `self._real_latent_dim`, `self._real_vocab_size`, `self._real_seq_length` from ckpt
4. Override `KANZI_STATE_SHAPE` lazily based on ckpt-loaded dims (or keep abstract + add `_state_shape_real`)
5. Update `solve_ode()` to use real dims when ckpt is loaded
6. Update `observe_token_indices()` to return indices in real range [0, 1000)

### Tests: `tests/test_adapters/test_kanzi.py` + `test_kanzi_real_ckpt.py`

- Update abstract-shape assertions to use `KANZI_ABSTRACT_LATENT_DIM`
- Add tests for real-ckpt shape assertions: `(L, 512)` not `(64, 64)`
- Add tests for `_load_ckpt_dims()` round-trip
- D.4 byte-stable regression

### Commit (single, NO push)
**Title**: "Wave 92a: Kanzi adapter refactor — fix 3 constants via ckpt model_cfg load"
**Body**: per-constant diff + D.4 verify

---

## 3. Wave 92b — Upstream N-samples patch (1 agent, single commit)

### File: `tools/upstream_eval.py`

**Strategy**: Mirror LineageFlow Wave 81 commit pattern
1. Find the Kanzi eval branch (around line 325-374)
2. Refactor to **loop over all records, accumulate metrics, write single output JSON**
3. Add `--upstream-n-samples` knob that controls how many records to read from input file
4. Write per-metric stats (mean, std, N)

### Tests: `tests/test_tools/test_upstream_eval.py`

- Test 1: Kanzi N=1000 path produces 6 metrics × N records
- Test 2: N-samples knob honored
- Test 3: mean + std computed correctly across N records

### Commit (single, NO push)
**Title**: "Wave 92b: Kanzi upstream N-samples patch (LineageFlow Wave 81 pattern)"
**Body**: per-file diff + test results + D.4 verify

---

## 4. Wave 92c — N=1000 framework paper-metric sweep (1 agent, single commit)

### Run:
```bash
.venvs/kanzi_venv/bin/python tools/run_real_ckpt_eval.py \
    --model kanzi --force-mode real \
    --kanzi-framework-paper-metrics \
    --upstream-n-samples 1000 \
    --output-dir verification_outputs/kanzi_n1000_framework_paper_metrics_real/
```

### Output:
- 6 metrics × N=1000 each (mean, std, CI)
- Per-metric verdict (SUPPORTED / TIE / REGRESSES / UNDERPOWERED)
- Audit doc with honest verdict

### Commit (single, NO push)
**Title**: "Wave 92c: Kanzi N=1000 framework paper-metric — finally measurable after Wave 92a/b refactor"
**Body**: per-metric N=1000 numbers + verdict

---

## 5. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Breaking D.4 byte-stable by changing constants | P1 | Keep `KANZI_ABSTRACT_LATENT_DIM=64` for synthetic tests; real path uses ckpt dims |
| 18+ test assertions break | P1 | Use abstract constant name for synthetic shape; update tests to use abstract name |
| Adapter load time increases (read ckpt on init) | P2 | Lazy load via `_load_ckpt_dims()` only when real-ckpt mode triggered |
| Framework arm shape still mismatches even after constants fix | P1 | Phase 1 audit §7.6 already identified (L, 512) match — should resolve |
| CPU N=1000 still too slow (2h+) | P2 | Use `--seeds 0..99` × 10 cells = N=1000 (vectorized) |

---

## 6. Cross-references

- Wave 91 Phase 1 audit: `docs/audit/wave91-phase1-audit.md` §4 + §6
- Wave 91 Phase 4 eval (n=5 smoke): `docs/audit/wave91-phase4-eval-real.md`
- LineageFlow Wave 81 commit pattern: `1392bea` (5-LOC _StubLineageFlow.forward signature fix)
- Master plan: `todo/planned/tier3-final-close-master-plan.md`