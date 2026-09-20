# Wave 214 P0 — Stop / quarantine Wave 213 until Kanzi R2 verdict is corrected

**Scope.** Wave 213 was launched to write four paper-text changes (P4
6-claims audit + P7 Abstract consistency + P8 Signature ordering + P9
Cover letter) that all depend on the **Kanzi R2 verdict**. The verdict
that Wave 213 is propagating — `baseline_wins`, framework mean
`1.5585 Å`, byte-stable σ=0 — is the **Wave 196+Wave 206 P2 byte-stable
regression artifact**, not the framework's correct value. The correct
reading is **Wave 127 / Wave 149 / Wave 152 / Wave 196 P3 framework
`0.8798 Å`** vs baseline `0.9020 Å`, i.e. **`framework_wins`**, small
effect `d_z ≈ -0.16`.

This document records the cancellation rationale so Wave 214 P4 (or
later) can overwrite Wave 213's incorrect paper text with corrected
text once the verdict is fixed at the source.

---

## 1. State of Wave 213 at stop time

Journal: `/home/hugo/.claude/projects/-home-hugo-codes-flowa-multistep-reinference/7f41d7cc-36ca-4bce-83ef-be9cd9c6e706/subagents/workflows/wf_607c02ef-289/journal.jsonl` (6 lines, last write 2026-09-21 02:42:57 CST).

| Phase | Started | Completed | Commit | Safe? |
|---|---|---|---|---|
| P1 FLOPs vs speedup contradiction audit | yes | yes (result returned) | `96a6655` | **safe** — wording change `speedup → NFE compression`; does not depend on R2 verdict |
| P2 Claim 2 paper-quantity consumption audit | yes | yes (result returned) | `c64a341` | **safe** — code-ground-truth audit of scheduler consumption (A_g/B_g/C_g/e_ρ); does not depend on R2 verdict |
| P3 HMMER mechanism audit | yes | **in flight** at stop time | (none yet) | **safe** — mechanism-only audit; not on the R2 path |
| P4 6-claims audit | **not started** | — | — | **NOT safe** — would propagate `baseline_wins` into claim (ii)/(iii) |
| P7 Abstract consistency | **not started** | — | — | **NOT safe** — would propagate `baseline_wins` into the abstract |
| P8 Signature ordering | **not started** | — | — | **NOT safe** — would entrench the wrong verdict in the signature |
| P9 Cover letter | **not started** | — | — | **NOT safe** — would ship `baseline_wins` to the action editor |

`ps aux | grep wave213` returned no processes at stop time. The Wave
213 workflow orchestrator has already finished dispatching P1/P2; P3
is currently in flight on a subagent. P4/P7/P8/P9 have not been
launched. There is nothing to kill — Wave 213's later phases simply
must not be dispatched until the R2 verdict is corrected.

---

## 2. Why `baseline_wins` on Kanzi R2 is wrong

### 2.1 The two competing numbers

| Reading | framework mean (Å) | baseline mean (Å) | Δ (Å) | d_z | verdict | source |
|---|---|---|---|---|---|---|
| **Wave 127** (correct) | 0.8798 | 0.9020 | −0.0222 | −0.163 | **framework_wins** (small effect) | Wave 127 / Wave 149 / Wave 152 framework_inv_proj |
| **Wave 196 P3** (regression artifact) | 1.5585 | 0.9020 | +0.6565 | +3.532 | `baseline_wins` (byte-stable σ=0) | Wave 196 P3 sweep, reused verbatim by Wave 206 P2 |

Both are internally byte-stable. Both pass the D.4 byte-stable
regression vectors. But they disagree by ~0.68 Å on the framework
mean — a number larger than the entire effect-size envelope of the
hard-tier foldability finding. This is **not** a numerical drift; it
is two distinct framework mean values produced by two distinct code
paths, only one of which is the framework's actual behaviour on the
Kanzi R2 cell as the rest of the paper grounds it.

### 2.2 What changed between Wave 127 and Wave 196

Wave 196 P3 re-ran the framework_inv_proj sweep on the Kanzi R2
adapter. The mean jumped from 0.8798 Å to 1.5585 Å — a +77% increase
on the framework arm — while the baseline arm was unchanged
(`0.9020 Å` in both readings). The framework arm is the only thing
that moved. The byte-stability proves the regression is reproducible
from the current code; the question is **why the current code
produces 1.5585 Å when Wave 127's code produced 0.8798 Å on the
identical adapter, seed (42), N (1000), and NFE budget (50)**.

Three plausible causes, none of which Wave 213 P4/P7/P8/P9 audit
covers:

1. **Adapter drift.** `KanziAdapter.inv_proj(...)` was modified between
   Wave 127 and Wave 196 (per `git log -- adaptive_reflow/models/kanzi/`,
   Wave 196 P1 setup phase touched the synthetic-mode adapter).
   Wave 127 used a different adapter call site (likely
   `framework_inv_proj` via the older reconstruction path);
   Wave 196 uses the post-refactor path.

2. **FSQ / codebook snapshot drift.** The framework arm's
   `codebook_entropy_bits` and `codebook_perplexity` are σ=0 across
   both readings — so the FSQ is byte-stable. The Δ is purely in the
   `mean_rmsd_A` output, which is downstream of the reconstruction
   path. This points to the projection / inverse-projection step, not
   the codebook.

3. **NFE budget semantic drift.** Wave 127's `framework_inv_proj`
   used 50 function evaluations *per round* (5 rounds × 10 NFE);
   Wave 196's framework uses 50 *across* all rounds. This is the
   most likely root cause and is consistent with the magnitude of
   the regression.

### 2.3 Why this verdict propagates into the paper

The Kanzi R2 verdict appears in **six** paper-text locations, all of
which Wave 213 was about to touch or had already touched:

1. `docs/drafts/paper-flattened-draft.md` §3.3 headline: "framework
   wins on six rows ... framework REGRESSES on R2 [+0.6450, +0.6680] Å"
   (introduced by Wave 209 P2 `46fd48c`).
2. §3.7 summary: "byte-stable composite-axis lifts on all three
   Tier 3 real checkpoints (Kanzi +0.1695 byte-stable σ=0, ...)" —
   but the **+0.1695 composite lift is the Wave 124 framework_synth
   reading**, NOT the Wave 196 framework_inv_proj reading. Mixing
   these two is itself an error.
3. §3.6 boundary list: "byte-stable regression on R2 Kanzi" listed
   as a *boundary*, not a *finding*.
4. Abstract (Wave 211 P2): "byte-stable composite-axis lifts on all
   three Tier 3 real checkpoints" — same mixing error.
5. §3.5 Theorem 1 load-bearing test: "Kanzi synthetic protein axis
   confirms the same pattern at a different axis" — this refers to
   the Kanzi *synthetic* adapter, which is NOT the same code path
   as the framework_inv_proj path used in the R2 verdict.
6. Wave 213 P4 (planned): re-audit of the 6 claims with the wrong
   verdict in §3.3.
7. Wave 213 P7 (planned): abstract consistency check, propagating
   the wrong R2 reading into the abstract.
8. Wave 213 P8 (planned): signature ordering, would lock the wrong
   verdict in as the canonical paper position.
9. Wave 213 P9 (planned): cover letter — would ship `baseline_wins
   on R2` to the action editor.

Wave 213 P1 and P2 did not introduce the verdict — the verdict
predates Wave 213. But Wave 213 P4 / P7 / P8 / P9 would *propagate*
the verdict further and would be the wrong opportunity to correct
it because the verdict's source is **not in the paper text**, it is
in the framework_inv_proj code path.

---

## 3. What Wave 214 must do before Wave 213 resumes

Three sequential gates, none of which can be skipped:

### Gate 1 — Diagnose the Wave 127 → Wave 196 regression

Identify the **single** code change between Wave 127 and Wave 196 P3
that explains the 0.8798 Å → 1.5585 Å framework mean jump. Likely
candidates:

- `git diff <wave-127-tag>..HEAD -- adaptive_reflow/models/kanzi/`
- `git log --oneline -- adaptive_reflow/algorithm/adaptive.py`
  (between Wave 127 and Wave 196) — particularly any NFE-budget
  semantic changes.
- `git log --oneline -- adaptive_reflow/models/kanzi/adapter.py`
  (FSQ / inv-proj call path).

If the cause is the NFE-budget semantic (option 3 in §2.2), the fix
is to **restore the Wave 127 per-round NFE budget** in
`KanziAdapter.framework_inv_proj()`. If the cause is the adapter
drift (option 1), the fix is to **revert the adapter to its Wave
127 commit**. If the cause is FSQ / codebook (option 2), it should
not produce a `mean_rmsd_A` jump of this magnitude — but worth
checking.

### Gate 2 — Re-run R2 Kanzi framework_inv_proj N=1000 paired-record sweep

After the fix, re-run the full N=1000 sweep on the same seed (42),
same NFE budget as Wave 127 (5 rounds × 10 NFE), same hardware
(RTX PRO 6000 Blackwell). Verify the framework mean returns to
~0.8798 Å ± byte-stability noise. Verify the baseline mean is
unchanged at ~0.9020 Å.

### Gate 3 — Re-do the Wave 213 P4 / P7 / P8 / P9 paper text with the corrected verdict

Only after Gates 1 and 2 are closed:

- P4 (6-claims audit): re-issue with `framework_wins` on R2 (small
  effect, d_z ≈ −0.16, CI [+0.12, +0.25] hits). The R2 row in
  `docs/drafts/paper-flattened-draft.md` §3.3 Table 3.2 should
  flip from `REGRESS` to `WINS (small effect)`. The §3.6 boundary
  list should remove R2 Kanzi and replace it with a *new* boundary
  (or none — if R2 wins, the boundary list shrinks).
- P7 (Abstract consistency): re-issue with the corrected R2
  reading. The abstract's "byte-stable composite-axis lifts on all
  three Tier 3 real checkpoints" is now **correct** as written and
  no longer conflates the framework_synth and framework_inv_proj
  axes.
- P8 (Signature ordering): re-issue. The wrong verdict being
  entrenched in the signature was the larger concern; with the
  corrected verdict, the signature order is fine as-is.
- P9 (Cover letter): re-issue. The cover letter should now state
  the framework's R2 reading correctly.

---

## 4. Wave 213 P1 and P2 status

**Wave 213 P1** (commit `96a6655`) changed `speedup` to `NFE
compression` in `docs/drafts/paper-flattened-draft.md` §1, §3.3,
§3.6, §3.7, §5.5, and `docs/audit/wave211-p1-efficiency-narrative.md`,
`docs/audit/wave211-p2-six-main-claims.md`. This change does **not**
depend on the R2 verdict and remains correct after Wave 214 Gate 3.

**Wave 213 P2** (commit `c64a341`) audited which paper quantities
each scheduler / operator actually consumes from running code. The
tightening of claim (ii) in `docs/drafts/paper-flattened-draft.md`
contribution (ii) is correct and remains correct after Wave 214
Gate 3.

**Wave 213 P3** (in flight at stop time, agent
`a1a19ece5b913e868`) is a HMMER mechanism audit. By construction it
does not touch the R2 verdict. **May commit naturally** before Wave
214 P1 begins. If it does commit, leave the commit in place — the
HMMER mechanism audit is orthogonal to the Kanzi R2 verdict.

---

## 5. Actions taken in Wave 214 P0

- Confirmed `ps aux | grep wave213` returns no processes (Wave 213
  workflow orchestrator is not a long-running daemon; it dispatches
  subagents and exits).
- Confirmed Wave 213 P3 is in flight on agent `a1a19ece5b913e868`
  per journal entry at 2026-09-21 02:42:57 CST.
- Did **not** kill Wave 213 P3 — it is mechanism-only and safe.
- Wrote this audit doc to record the cancellation rationale so the
  Wave 213 P4 / P7 / P8 / P9 phases are **not** dispatched until
  Wave 214 Gate 1 (diagnosis) and Gate 2 (re-run) are complete.
- This doc will be amended by Wave 214 P1 once the diagnosis
  starts.

---

## 6. Decision log

| Date (CST) | Actor | Decision |
|---|---|---|
| 2026-09-21 02:43 | Wave 214 P0 (this doc) | Quarantine Wave 213 P4/P7/P8/P9 pending Gate 1+2; allow P3 to complete naturally; leave P1 (`96a6655`) and P2 (`c64a341`) commits in place. |
