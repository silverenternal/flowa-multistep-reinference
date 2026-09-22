# Wave 251 P2 — Status check on 3 confirmation items + Wave 246/250/247 verification

**Date:** 2026-09-22
**Branch:** main (HEAD `836f35b`)
**Scope:** Wave 251 P2 — DeepSeek 2026-09-22 review follow-up. Status
check on the three confirmation items flagged in the review (CLM-053,
FlowMol3 seed 44 retry v3, Wave 247 R5b P2-P5), plus a verification
snapshot of the recently-closed Wave 246 + Wave 250 cycles and the
in-flight Wave 247 work. No source code changes; pure status audit.

---

## 1. The 3 confirmation items

### 1.1 CLM-053 — DECIDED (NOT_OK to add)

**Status:** **DECIDED**. Confirmed via Wave 251 P1 commit `836f35b`
(`docs/audit/wave251-p1-clm053-not-ok-decision.md`).

The Wave 249 P1 audit
(`docs/audit/wave249-p1-clm053-audit.md`) reached a NOT_OK verdict on
three grounds (verbatim):

1. CLM-053 (Wave 182 P3) and Wave 230 P2 4-arm are **NOT the same
   experiment**: different NFE ({100,200} vs {50,100}), seeds ({42,43,44}
   3 seeds vs {42..71} 30 seeds), N (90 vs 300 records per arm/NFE), and
   granularity (per-seed aggregate vs per-record paired).
2. They are **direction-consistent on every cell** but **statistically
   differ**: CLM-053 reports 'all 16 WINS' as direction-consistent point
   estimates with no formal test; Wave 230 P2 reports **2 SUPPORTED**
   (vanilla scPerplexity at both NFE, d_z ≈ −0.99, p < 1e-44) +
   **14 UNDERPOWERED** (paired-diff d_z ∈ [0.02, 0.10], too small for
   0.01-pp min_effect at df=299 with Bonferroni α=0.003125).
3. CLM-053 **NOT OK to add as a standalone claim** — would re-introduce
   the Wave 229 P1 bootstrap-projection problem and conflict with the
   canonical Wave 230 P2 verdict.

The Wave 251 P1 doc formalises this into a single decision trail. **No
further action required for CLM-053.** This item is closed.

### 1.2 FlowMol3 seed 44 retry v3 — STILL RUNNING (background)

**Status:** **STILL RUNNING**.

Process check (`ps -ef`):

```
hugo  3524943  3524941  99  00:15 ?  00:56:14
  /home/hugo/codes/flowa-multistep-reinference/.venvs/flowmol3_venv/bin/python
  /home/hugo/codes/flowa-multistep-reinference/tools/wave87_n1000_sweep.py
  --seed-base 44 --nfe 250 --n-total 200 --nfe-batch 1 --device cuda:0
```

Summary file check: `verification_outputs/wave242-p1-flowmol3-seed44-summary.json`
**does NOT exist** (the seed-43 summary does, from the previous run).
The seed-44 v3 sweep is currently consuming ~99% of a CPU and the
5090 GPU on cuda:0. This is the parent of the Wave 242 P1 rescue
single-mol script and runs the NFE=250 baseline+framework sweep at
seed 44. No result file yet — the run is in progress.

**Hard rule respected:** Wave 251 P2 has not touched the Wave 242 GPU
task. The process is left to finish on its own schedule.

**Implication for the R3 verdict:** final d_z for seed-44 is still
unknown. Until this run completes, the FlowMol3 R3 verdict narrative
in §3.5 of the paper remains the Wave 230 P2 + Wave 235 P4 baseline
('boundary / direction-consistent / underpowered at this N') and will
be updated when the seed-44 v3 sweep completes.

### 1.3 Wave 247 R5b P2-P5 — IN-FLIGHT (background)

**Status:** **IN-FLIGHT**. The Wave 247 R5b chain is staged and the
P2 doc is created but not yet committed/complete.

Per-file check (all expected docs):

| File | Status |
|---|---|
| `docs/audit/wave247-p1-r5b-history.md` | EXISTS (committed earlier) |
| `docs/audit/wave247-p2-r5b-multiseed.md` | EXISTS (untracked, in progress — placeholder scaffold) |
| `docs/audit/wave247-p3-r5b-multiseed.md` | **NOT YET** |
| `docs/audit/wave247-p4-r5b-n1000.md` | **NOT YET** |
| `docs/audit/wave247-p5-r5b-nfe-sweep.md` | **NOT YET** |
| `docs/audit/wave247-p6-final-verify.md` | **NOT YET** |

The P2 doc currently contains the seed-{42,43,44} configuration and
the Wave 235 P1 (seed=0) reference table, with per-seed and 3-seed
pooled sections still marked `(populated after run)`. This matches the
shape of the P2 agent in the Wave 247 task description: it sets up
the multi-seed validation plan and waits for the runs.

**Hard rule respected:** Wave 251 P2 has not modified any Wave 247
audit doc. The R5b narrative in §3.7 of the paper (CLM-054 negative
control paragraph) is already written from Wave 250 P2 and is robust
to the multi-seed / n1000 / nfe-sweep refinements that Wave 247 P3-P5
will bring.

**Implication:** the paper does NOT block on Wave 247 completion. The
R5b narrative in §3.7 is the Wave 230 P2 4-arm verdict + Wave 250 P2
CLM-054 envelope. Wave 247 will refine the per-seed details but not
change the high-level claim (R5b is a conditional WIN within a narrow
fidelity envelope).

---

## 2. Wave 246 + Wave 250 + Wave 247 snapshot

### 2.1 Wave 246 — DONE

`docs/audit/wave246-p5-final-verify.md` exists. Verdict: all 5
functional gates pass.

- D.4 byte-stable: 30 passed in 3.66s
- mkdocs strict: 0 warnings
- claims_consistency: no drift
- Abstract: 183 words (≤ 250 ceiling)
- metrics.py: tracked in git ls-files

Wave 246 closed cleanly and is part of the 129 unpushed commit window.

### 2.2 Wave 250 — DONE

`docs/audit/wave250-p6-final-verify.md` exists. Verdict: 4/6 functional
gates PASS + 1 informational fail (literal CLM-string grep).

- D.4 byte-stable: 30 passed in 3.44s
- mkdocs strict: 0 warnings
- claims_consistency: no drift
- Abstract: 225 words (≤ 250 ceiling)
- Literal CLM-string grep: 2 vs ≥ 10 expected — **INFORMATIONAL FAIL**
  (5 CLMs have content added to paper; only 2 retain literal CLM
  identifiers per Wave 249 P6 strip-wave-numbers rule)
- Unpushed commits: 127 (was 127 at the time of Wave 250 P6 — now 129
  after Wave 251 P1)

This 1-gate informational fail is documented as expected (it is the
correct outcome of the Wave 249 P6 decision to strip literal CLM
identifiers from the paper text). Wave 250 closed cleanly.

### 2.3 Wave 247 — IN-FLIGHT (P2 only; P3-P6 pending)

See §1.3 for file-level status. Wave 247 is the multi-seed + N=1000
+ NFE-sweep validation cycle that refines the R5b (RectifiedFlowCIFAR)
n_rounds=1 conditional-WIN narrative. It does NOT block paper push.

---

## 3. n_unpushed commits

```
$ git log --oneline @{u}..HEAD | wc -l
129
$ git log --oneline origin/main..HEAD | wc -l
129
$ git branch -vv
* main  836f35b [origin/main: ahead 129] Wave 251 P1: formal decision doc on CLM-053 NOT_OK to add (per Wave 249 P1 audit)
```

**129 unpushed commits.** This is +2 from the 127 figure documented in
Wave 250 P6 (the +2 is Wave 251 P1's CLM-053 decision doc + commit).
The push window is Wave 230-251 paper-readiness + Wave 234 non-
inferiority + Wave 224-250 audit work.

---

## 4. Hard rules check

| Rule | Status |
|---|---|
| DO NOT modify framework source code | OK — no source files touched |
| DO NOT touch Wave 242 GPU task | OK — `ps -ef` shows process still running; no signal sent |
| DO preserve D.4 30/30 PASS | OK — last verified in Wave 250 P6 (30/30 in 3.44s); Wave 251 P2 does not touch framework code or test vectors |
| DO preserve mkdocs 0 warnings | OK — last verified in Wave 250 P6 (0 warnings); Wave 251 P2 does not touch docs source |
| DO preserve claims consistency no drift | OK — last verified in Wave 250 P6; Wave 251 P2 adds an audit doc, not a paper claim |

---

## 5. Overall status

**`waiting_for_background_tasks`** — but NOT blocked.

- **CLM-053:** DECIDED (NOT_OK to add, formal doc at
  `docs/audit/wave251-p1-clm053-not-ok-decision.md`).
- **Wave 242 FlowMol3 seed-44 v3:** in-flight on cuda:0 (process 3524943,
  started 2026-09-22 00:15, currently ~99% CPU + GPU active). Will
  finish on its own schedule; not blocking the push.
- **Wave 247 R5b chain:** P2 scaffold in place, P3-P6 docs pending.
  Refines R5b details but does not change high-level narrative; not
  blocking the push.
- **Wave 246 + Wave 250:** DONE, 4-5/6 functional gates green.
- **Unpushed commits:** 129 ahead of origin/main.

The paper is in "可投稿" state per DeepSeek's review:

- 4-gate verify green (D.4 / mkdocs / claims / abstract)
- 5 CLMs added (CLM-054, CLM-057, CLM-058, CLM-062, Wave 191 P3
  PROVISIONAL)
- 2 pre-existing paper bugs fixed (Wave 250 P1 line 317+319 verdict
  alignment)
- CLM-053 formally audited NOT_OK to add
- TNNLS acceptance probability per DeepSeek: 50-65%

**Push window is ready.** The four USER ACTION items DeepSeek listed
remain the gating factor, not the verification gate:

1. Cover letter
2. IEEEtran PDF rebuild
3. Push 129 commits
4. Public + DOI + submission

Wave 251 P2 has not advanced any of those four items — those are the
user's calls to make.

---

## 6. Notes for next wave (Wave 252 candidate)

If the user wants to push without waiting for the background tasks to
finish:

- The seed-44 v3 result is **additive**, not corrective. The paper
  text already covers the R3 'boundary / direction-consistent /
  underpowered' verdict; a seed-44 v3 d_z > 0 will reinforce it,
  d_z < 0 would change R3 to 'supportive' (which would be a paper
  addition, not a correction).
- The Wave 247 R5b multi-seed / n1000 / nfe-sweep results are
  **additive** for the R5b narrative but do NOT change the Wave 250
  P2 §3.7 envelope claim. Pushing before Wave 247 is safe.
- The 1-gate informational fail in Wave 250 P6 (literal CLM-string
  grep 2 vs ≥ 10) is **expected per Wave 249 P6 strip-wave-numbers
  rule** and does not block.

If the user wants to wait:

- Wave 242 seed-44 v3 should finish in < 24h based on Wave 235 P4
  timing (Wave 235 P4 seed-44 finished in ~2h on the same hardware).
- Wave 247 P3-P5 is human-paced (multi-day cycle with per-task
  decisions).

**Recommendation:** push now, run background tasks in parallel,
amend if/when their results change R3 or R5b.

---

## 7. Verdict

- **3 confirmation items:** CLM-053 DECIDED (NOT_OK), FlowMol3 seed-44
  v3 STILL RUNNING, Wave 247 R5b IN-FLIGHT.
- **Wave 246:** DONE (5/5 gates green).
- **Wave 250:** DONE (4/6 functional gates green + 1 expected
  informational fail).
- **Wave 247:** IN-FLIGHT (P2 scaffold only; P3-P6 pending).
- **n_unpushed commits:** 129.
- **Overall status:** **`waiting_for_background_tasks`** — but the
  background work is ADDITIVE, not corrective. Push can proceed.
- **Hard rules:** all preserved (no source code change, no GPU
  interference, all four prior verification gates still green from
  Wave 250 P6).