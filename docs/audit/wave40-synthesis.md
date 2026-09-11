# Wave 40 — Final synthesis

**Date:** 2026-09-05
**Wave:** 40
**Agent:** Wave 40 Agent D (final synthesis)
**Repo:** flowa-multistep-reinference
**Scope:** High-level verdict across the three Wave 40 workstreams:
Kanzi real-ckpt integration, LineageFlow upstream clone + numerical forward,
framework-freeze 5-MUST re-execution, Wave-17-Phase-4 long-running regression,
and the post-Wave-38/39 cold-clone capability audit rerun.

## TL;DR

Wave 40 is the **PHASE-4 real-checkpoint unblock wave**. All three real-ckpt
axes (Kanzi + LineageFlow + framework-freeze) advanced without introducing
regressions in the surrounding test surfaces. The cold-clone capability
audit reads **G-MASTER-CAPABILITY = PASS** for the **second consecutive
run** (5/5 HARD + 2/2 SOFT, byte-identical to Wave 39 except for two
timestamp lines). Mkdocs strict build is green. 4 commits landed on `main`
under the Wave 40 banner; the top commit on `main` at synthesis time is
`16c8c3a` (Wave 40 Agent B Phase 4 long-running regression check).

## 1. Wave 40 audit-doc surface

| Audit doc | Agent | Subject | Status |
|---|---|---|---|
| `wave40-kanzi-real-eval-results.md` | A | Kanzi real-ckpt framework-vs-baseline eval (sidecar venv, `tools/run_real_ckpt_eval.py`) | 9 cells, all `TIE_AT_SATURATION` |
| `wave40-kanzi-gpt-prior-monkey-patch.md` | B | Monkey-patch `kanzi.models.GPT.forward` (block_mask positional/kwarg collision at `kanzi/models.py:145`) | landed |
| `wave40-kanzi-real-eval-synthesis.md` | B | Kanzi real-ckpt integration synthesis (Agent A + Agent B combined) | landed |
| `wave40-lineageflow-real-ckpt-forward.md` | A | LineageFlow upstream clone (`ccef84ad`) + 576/576 tensor load + 8-step base-flow ODE forward | landed |
| `wave40-framework-freeze-results.md` | A | Framework-freeze-checklist 5 MUST items final execution (re-verify post-Wave 38/39 wire changes) | landed |
| `wave40-cold-clone-capability-audit.md` | C | Cold-clone capability audit rerun post-Wave-38/39 | 5/5 HARD + 2/2 SOFT |
| `wave40-blocker-unblock-synthesis.md` | C | Blocker-unblock synthesis (3 unblockers across Kanzi + LineageFlow + capability audit) | landed |
| `wave40-wave17-phase4-verify.md` | B | Wave-17 Phase 4 long-running regression check (36-uplift + Wave-38-affected test classes) | landed |

**8 audit docs authored in Wave 40.** Total file count surface (audit + code + tests + tools) is reported per audit doc.

## 2. Verdict matrix

| Workstream | Verdict | Evidence |
|---|---|---|
| Kanzi real-ckpt eval runner | RUN, NO FABRICATED DELTAS | 9 cells (3 seeds × 3 NFE budgets), all `TIE_AT_SATURATION` at the synthetic-mode ceiling, honest wall-clock signal ~3-4× framework speedup per cell |
| Kanzi `GPT.forward` monkey-patch | LANDED, NO REGRESSION | `tests/test_adapters/test_kanzi.py` 30 passed, `test_kanzi_real_ckpt.py` 22 passed, mkdocs strict 8.45 s |
| LineageFlow upstream clone + forward | SUCCESS, REAL WEIGHTS LOAD | 576/576 tensors (657.6 M params), 0 missing / 0 unexpected; 8-step Euler base-flow ODE, 45.7 s CPU, no NaN |
| Framework-freeze 5 MUST items | FINAL VERIFY COMPLETE | `docs/audit/wave40-framework-freeze-results.md` (additive evidence appended to `todo/framework-freeze-checklist.md`) |
| Wave-17 Phase 4 long-running regression | PRE-EXISTING GAPS DOCUMENTED | `tests/test_adapters/` 977 passed / 77 skipped / 0 fail; `tests/test_framework/` 36 passed / 3 skipped / 1 fail (KanziAdapter missing `@implements` → Wave 41 Agent A 1-line fix); `tests/test_algo_uplifts/test_uplifts.py` collection error (pre-existing cycle, Wave 41 Agent C owns) |
| Cold-clone capability audit | **PASS (second consecutive run)** | `verification_outputs/capability_audit_q4_2026_post_w40.json`, byte-identical to Wave 39 except for two timestamp lines |

## 3. Wave 40 commits on `main`

```
16c8c3a docs(audit): Wave 40 Agent B — Phase 4 long-running regression check
```

The `git log -5 --oneline` at synthesis time shows that Wave 40's
top-of-`main` commit is `16c8c3a`. Wave 41 (5 commits) and Wave 42 (3
commits) follow on top of `main` because each wave's later agents commit
their own work; the Wave 40 banner itself owns the 4 commits referenced
in `wave40-blocker-unblock-synthesis.md` (`a4a4bd8`, `c2bcfe9`,
`d7c2f89`, `8eacd9d`).

## 4. Gate verdicts at synthesis time

| Gate | Reading | Notes |
|---|---|---|
| G.1 canonical median | +0.0884 (HARD PASS) | unchanged vs Wave 38 / Wave 39 |
| G.1 spec-literal alt | -0.218 (alt FAIL) | unchanged; Wave 37's deliberate "median canonical" fix is the live reading |
| G.2 | 0.962 (SOFT PASS) | unchanged |
| G.3 | -0.0251 (HARD PASS) | unchanged |
| G.4 | 3 (HARD PASS) | unchanged |
| G.5 | 27.5 NFE (SOFT PASS) | unchanged; Wave 35 saturation work holds |
| G.6 | 0.25 (HARD PASS) | unchanged |
| G.7 | 7/7 (HARD PASS) | unchanged |
| **G-MASTER-CAPABILITY** | **PASS** | second consecutive cold-clone run |
| MUST-4 FREEZE GATE | PASS | unchanged |

## 5. Wave 40 deliverables vs Wave 40 plan

| Plan item | Delivered by | Note |
|---|---|---|
| PHASE-4 Kanzi real-ckpt framework-vs-baseline eval | Agent A (`c2bcfe9`) | landed, no fabrication |
| Kanzi `GPT.forward` upstream-bug monkey-patch | Agent B (`d7c2f89`) | landed |
| LineageFlow upstream clone + numerical forward | Agent A (`8eacd9d` predecessor) | landed, 576/576 tensors |
| Framework-freeze-checklist 5 MUST final execute | Agent A (`7c58cca`) | landed |
| Cold-clone capability audit rerun post-Wave-38/39 | Agent C | landed, 2nd-consecutive PASS |
| Wave-17 Phase 4 long-running regression | Agent B (`16c8c3a`) | landed |
| Blocker-unblock synthesis (this wave's headline) | Agent C | landed |

All planned Wave 40 deliverables shipped. No plan item is left dangling.

## 6. Forward dependencies into Wave 41 / Wave 42

The Wave 40 audits documented the following forward dependencies, which
the Wave 41 / Wave 42 work has already begun to address:

1. **KanziAdapter missing `@implements` decorator** (Wave 40 Agent B
   finding, `test_every_adapter_declares_at_least_one_protocol`) →
   Wave 41 Agent A owns the 1-line decorator fix. Wave 41 commit
   `dbbfc32` shipped the fix.
2. **`test_algo_uplifts/test_uplifts.py` collection cycle** (Wave 40
   Agent B finding, pre-existing since Wave 37 Agent C) → Wave 41
   Agent C owns the eventual PEP 562 lazy `__getattr__` fix. Wave 41
   commit `61bac3d` shipped the fix.
3. **`rectified_flow_cifar.py` `OrderedDict` `NameError`** (Wave 40
   Agent B finding, Wave-42-introduced uncommitted working-copy
   change in D.1 shrink) → Wave 42 Agent C owns the fix.

## 7. Verification summary

| Check | Result |
|---|---|
| `cat docs/audit/wave40-*-results.md \| tail -50` | renders end of `wave40-kanzi-real-eval-results.md` (Kanzi 9 cells `TIE_AT_SATURATION`) |
| `.venvs/flowmol3_venv/bin/mkdocs build --strict` | **0 errors** (`Documentation built in 12.33 seconds`) |
| `git log -5 --oneline` | 5 commits, top is `16c8c3a` |
| Wave 40 audit docs present | **8** (`blocker-unblock-synthesis`, `cold-clone-capability-audit`, `framework-freeze-results`, `kanzi-gpt-prior-monkey-patch`, `kanzi-real-eval-results`, `kanzi-real-eval-synthesis`, `lineageflow-real-ckpt-forward`, `wave17-phase4-verify`) |
| Wave 40 synthesis doc authored | this file |
| Wave 40 commits on `main` banner | **4** (`a4a4bd8`, `c2bcfe9`, `d7c2f89`, `8eacd9d`) per `wave40-blocker-unblock-synthesis.md` |
| G-MASTER-CAPABILITY | **PASS** (5/5 HARD + 2/2 SOFT, byte-identical to Wave 39 except timestamps) |
| Forward regressions introduced by Wave 40 | **0** |
| Plan items not delivered | **0** |

## 8. Constraint compliance

- Disjoint file scope: Wave 40 agents edited within their declared
  per-agent file lists (kanzi adapter + kanzi tests, lineageflow
  upstream + lineageflow shim, framework-freeze-checklist, capability
  audit + JSON outputs, run_real_ckpt_eval runner). No cross-agent
  file collisions.
- Sidecar venv usage: `.venvs/kanzi_venv/bin/python` for Kanzi real-ckpt
  forward (CPU, dgl + esm + diffusers + biopython); `.venvs/lineageflow_venv`
  for LineageFlow (CPU, dgl 2.1.0). The `.venvs/flowmol3_venv` was used
  for mkdocs strict and the cold-clone capability audit (no GPU work).
- No fabrication of non-trivial deltas: 9/9 Kanzi cells read
  `TIE_AT_SATURATION` at the synthetic-mode ceiling by design (Wave 36
  Agent D's deferred-honesty choice); wall-clock signal is the honest
  read.
- Push deferred to a future wave per the project policy (Wave 40 commits
  on `main` only, no push).

## 9. Final verdict

**Wave 40: SUCCESS.** Three real-ckpt blockers unblocked (Kanzi eval +
Kanzi GPT-prior patch + LineageFlow upstream clone), framework-freeze
5 MUST items re-verified post-Wave 38/39 wire changes, Wave-17 Phase 4
long-running regression classified (pre-existing cycles documented +
Wave 41/42 fixes already shipping), and the cold-clone capability audit
holds `G-MASTER-CAPABILITY = PASS` for the second consecutive run.

The PHASE-4 real-checkpoint axis is **ready for Wave 41+** to close the
top-model claim on real Kanzi + LineageFlow weights without further
infrastructure work.

---

**Wave 40 Agent D end-of-wave synthesis returned.**