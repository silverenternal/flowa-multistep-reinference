# Wave 107.A.4 — Honest stochastic N=1000 paper-presentation research (READ-ONLY)

**Date:** 2026-09-11
**Status:** READ-ONLY audit doc. No source/docs edits, no commits.
**Scope:** Find EXISTING patterns/templates/sections in the repo that can be REUSED to honestly present the stochastic N=1000 framework-vs-baseline data in paper §7 + cover letter. Avoid reinventing.

**Repo HEAD at audit time:** `c0dd9e4` (Wave 106.C.5 final synthesis: 107 findings → 30 fixes + 77 triaged; D.4 72/72 PASS, mkdocs EXIT=0).

---

## 0. TL;DR

The repo already carries a substantial honest-disclosure surface for stochastic data:

1. **`cover_letter.md` §"Honest limitations" (lines 27–31)** — three explicit limitations already disclosed, including "ties within SEM" and "post-hoc power <0.5 to detect a 1pp delta at N=1000; recommend N=5,000+". **EXTEND**, do not create.
2. **`docs/baseline-audit-report.md` §C.7 (lines 482–611)** — the canonical stochasticity disclosure template. N=200 → N=1000 → N=10000 progression with chi-squared / p / `pass_label` (`first_pass` / `second_pass` / `fourth_pass` / `non_canonical`) + `p < 0.20` marginal auto-gate. **REUSE verbatim** for any "this number is from sweep X (N=Y), the previous number was from sweep Z (N=W)" claim.
3. **`docs/audit/wave88-phase3-final.md` §1.5 (lines 72–94)** — the most direct stochasticity-of-decoder template: per-record σ table (8 records × 8 repeats) + "torch.manual_seed(1234) drives spread to 0" + "currently `sweep script needs a --seed flag threaded into dae.decode`" remediation. **REUSE structure verbatim** for the Kanzi N=1000 decoder-stochasticity disclosure.
4. **`docs/audit/wave96e-final-synthesis.md` §5 (lines 139–164)** — "Honest note on RMSD std target (0.214 vs > 0.5)" template: "criterion 3 passes on 'non-zero', fails on '> 0.5', and criteria 1 and 2 pass outright". **REUSE pattern** for any "we met the diversity bar but missed the std bar" framing.
5. **`docs/audit/wave106-a3-honesty-gaps.md` (lines 24–60)** — the existing audit-style findings table with verdict columns (`none (honest)` / `low` / `medium` / `high`). **REUSE pattern** for documenting "this number is from sweep X, the previous number was from sweep Y, the difference is …".

**Reuse opportunities found:** 11 distinct patterns. **Reuse-only path**: ~50 LOC of drop-in text (mostly table cells + paragraph extensions). **No new template code required.**

---

## 1. Findings (per the 7 CHECK FOR items)

### Check #1: Does cover_letter.md have an existing Honest limitations section to EXTEND?

**YES — and it is the natural home for stochasticity disclosures.**

- `cover_letter.md:27–31` carries **"## Honest limitations"** with three numbered limitations already disclosed:
  - **(1) Sample budget.** `cover_letter.md:29` — already discloses N=1000 vs N=5,000–50,000 paper budgets, N=999 baseline drop, and the asymmetric verdict distribution (`2/12 framework_improves`, `6/12 ties_within_sem`, `2/12 underpowered` with `post-hoc power <0.5 to detect a 1pp delta at N=1000; recommend N=5,000+`).
  - **(2) Mixed paper-metric verdict.** `cover_letter.md:29` — UFF-vs-xtb definitional gap on `pb_validity_pct` (-9.95pp), PB 0.6.5 import verified at `posebusters/modules/energy_ratio.py:6–14`.
  - **(3) Five Kanzi codebook metrics are `TIED_BY_DESIGN`.** `cover_letter.md:29` — FSQ round-trip deterministic.
- **`cover_letter.md:11` (TL;DR)** already carries explicit per-arm-N disclosure for the Kanzi case: "1/12 regresses on Kanzi at N=10 framework arm with Bonferroni p = 4.6e-7" — this is the existing convention for arm-asymmetry disclosure.

**REUSE pattern:** the existing `(1) Sample budget` paragraph at `cover_letter.md:29` is the **direct extension target** for stochasticity caveats. Drop-in addition (≤ 5 LOC): append one sentence acknowledging decoder-stochasticity per-record σ at N=1000 (cross-cite `wave88-phase3-final.md` §1.5 for the σ=0.0947 Å evidence; cross-cite `wave96e-final-synthesis.md` §5 for the std-target-missed reading). The cover letter already carries the full "honest" branding — reviewers expect this section to enumerate caveats, so adding a 4th numbered item is the lowest-friction insertion.

**Existing cross-references to stochasticity docs already in place:**
- `cover_letter.md:31` → `docs/audit/wave99-n1000-final.md` (verdict)
- `cover_letter.md:31` → `docs/audit/wave106.A.2` (JSON path for the N=10 framework arm)
- `cover_letter.md:31` (Wave 99 update) — explicit "the framework arm has reached **N=10** at the largest available sweep, not N=1000" disclosure.

**LOC delta vs new template:** ~5 LOC of drop-in text. **No new section required.**

---

### Check #2: Does supplementary.md have existing footnote / caveat markers to REUSE syntax/style of?

**YES — at least 4 distinct styles already in use.**

| Style | Location | Example |
|---|---|---|
| **Per-paper-axis verdict table with verdict enum** | `supplementary.md:242–252` (§S5.4) | `framework_improves` / `framework_worse` / `TIE_AT_SATURATION` / `TIED_BY_DESIGN` / `NOT_MEASURABLE_N1000` / `REPORTED` / `DEFERRED` |
| **Per-Wave X F-N caveat** | `supplementary.md:252` (§S5.4) | "**Per-Wave 106.A.2 F-02 caveat:** 1 molecule dropped from baseline due to CTMC valence artifact (per Wave 87 §"Honest caveats" #7). Framework arm produces 1000 molecules cleanly." |
| **Carry-forward to venue** | `supplementary.md:161` (§S3.5 title), `supplementary.md:204` (§S4.4 title) | "Honest caveats (carry-forward to venue)" + "Honest disclosure:" |
| **Noise floor / FSQ quantisation noise band** | `supplementary.md:163` (§S3.5) | "**FSQ quantisation noise floor.** Wave 36 Kanzi ckpt FSQ basis `(8, 5, 5, 5)` → codebook size 1000 → per-row projection error ~0.5 Å in coord space. Decoder stochasticity from `torch.randn_like` is unseeded (Wave 88 F-4: 8 records × 8 unseeded repeats, σ=0.095 Å run-to-run)." |
| **Cross-wave delta progression table** | `supplementary.md:2227` (§S5.4, Wave 79 → Wave 83 row table) | explicit "Wave 79 n=2 → Wave 80 N=32 smoke → Wave 83 N=200 sweep" delta table with "supersedes" / "retracted" framing |
| **<!-- TODO(Wave XX) --> marker** | `supplementary.md:39, 49, 88, 118, 318–340` | explicit placeholder with Wave number for downstream fill |

**REUSE pattern:** the `Per-Wave X F-N caveat` style at `supplementary.md:252` is the **direct template** for stochasticity disclosures in supplementary §S5 (FlowMol3) and §S3 (Kanzi). The phrase "**Per-Wave XXX F-NN caveat:**" is a stable naming convention used 4+ times across supplementary.md and is indexed by the `docs/audit/wave106-a-2-audit.md` and downstream `wave106-c2-fix-summary.md`.

**LOC delta vs new template:** ~3 LOC per cell (one "Per-Wave XXX F-NN caveat:" line + one citation + one numerical value).

---

### Check #3: Does the repo have a Stochasticity caveat template somewhere (CONDITIONS.md / operating-regime.md)?

**NO dedicated template file** — but the substance is well-distributed.

- `docs/baseline-audit-report.md:482–611` (§C.7 "Simulation-Based Calibration for stochastic re-inference") is **the de facto stochasticity disclosure template** in this codebase. It carries:
  - Per-algorithm chi² / p tables at N=200, N=1000, N=10000 (lines 489–500, 529–544)
  - The `p < 0.20` marginal auto-gate (lines 502–525)
  - `pass_label` enum: `first_pass` / `second_pass` / `fourth_pass` / `non_canonical` (lines 573–578)
  - Backward-compat note: "primary sweep passes `seed_offset=0`, so the committed `sbc_audit_n200.json` and `sbc_audit_n1000.json` reports reproduce byte-identically" (line 554–555)
  - **Backward compatibility prose at line 554** is the exact pattern for "this number is from sweep X (N=Y), the previous number was from sweep Z (N=W), the difference is …" — REUSE the seed-offset rationale.
- `docs/baseline-audit-report.md:1180` (§B.7) carries the `@settings(derandomize=True)` property-test pattern: "all property tests in this directory either pin an explicit `numpy.random.Generator(seed=...)` or restrict their scope to deterministic algorithms" — direct prose template for "we pin seeds at N=1000 to surface the same shrunk counter-example across runs".
- `docs/baseline-audit-report.md:1127–1180` (§F.5 env_hash + §B.7 property-based test coverage) — the closest existing pattern for environment-fingerprint reproducibility, including the seed offset convention.
- `docs/CONDITIONS.md:104–111` — the failure-mode characterisation table cites `docs/reproducibility_record.md` for stochasticity reproduction evidence per model family.

**REUSE pattern:** adopt the C.7 3-column sweep table structure (`N=X chi² / p | N=Y chi² / p | runtime`) at `docs/baseline-audit-report.md:491` and the `pass_label` enum at line 573 for any "this number is from sweep X (N=Y), the previous number was from sweep Z (N=W)" claim. The seed-offset rationale at line 521 ("`_FOURTH_PASS_SEED_OFFSET = 700001` rather than extending the primary sweep's draws. A nested prior would make the two verdicts statistically dependent and defeat the point of re-verification; the offset keeps the deeper sweep independent while leaving it reproducible.") is the **direct template phrase** for "deep N=1000 sweep reproduces independently of N=200 smoke".

**LOC delta vs new template:** ~10 LOC (mostly the per-N chi²/p table + `pass_label` enum cell). The C.7 template is already 130 LOC of substance — REUSE.

---

### Check #4: Is there an existing convention for reporting multiple-metric, same-axis claims (framework_improves + framework_ties insight)?

**YES — at least 4 patterns.**

1. **`docs/CONSOLIDATED_RESULTS.md:2902`** carries the explicit "noise floor" tier in the verdict distribution: "|TIE| |Δ| < 1pp noise floor OR true saturation OR encoder_summary by construction OR N=5 degenerate | 8/12 (67%) |" — direct precedent for `|Δ| < 1pp noise floor` as a `framework_ties_within_sem` verdict tier.
2. **`cover_letter.md:29`** ("Honest limitations" item 1) carries the explicit verdict distribution: "2/12 framework_improves, 6/12 ties_within_sem, 2/12 underpowered" — direct precedent for the 3-tier verdict distribution convention.
3. **`docs/CONSOLIDATED_RESULTS.md:668–692`** (§12.1 / §12.2) carries the per-cell value table with `signed_delta_pct` and a separate `direction` column (`framework better` / `parity (within G.3)` / `saturation tie`), with a separate per-metric verdict table that names HARD/SOFT and target thresholds.
4. **`docs/paper-draft.md:1942` (§7.3 Kanzi)** carries the per-cell value table with `composite_verdict` enum (`framework_improves` / `no_signal` / `TIE_AT_SATURATION`) + a separate aggregate `verdict_overall` field + a separate decomposition table.
5. **`docs/paper-draft.md:2321` (§7.4 LineageFlow aggregate)** carries the per-cell composite + a separate composite-axis verdict + a separate decision-metric-axis verdict — direct precedent for **two verdicts on the same metric** ("framework improves composite axis" but "TIE_AT_SATURATION decision-metric axis").

**REUSE pattern:** the 3-tier verdict distribution at `cover_letter.md:29` (the `(1) Sample budget` paragraph) is the **direct extension target** for stochasticity caveats. Drop-in addition (≤ 3 LOC): extend item (1) to say "the 6/12 ties_within_sem cells include N cells where the per-record σ from `DAE.decode` (0.0947 Å) is on the order of |Δ|; cross-cite `wave88-phase3-final.md` §1.5".

**LOC delta vs new template:** ~3 LOC of drop-in text.

---

### Check #5: Does the existing cover_letter section G1 (SHA-256) pattern have a template for documenting stochastic run-to-run variance?

**NO direct G1-style template for run-to-run variance — but the G1 disclosure pattern is generalisable.**

- `cover_letter.md:19` (G1 SHA-256 ckpt verification) carries the per-model SHA-256 + manifest-pointer pattern: "Kanzi `c2f2ab8d...d270` (`verification_outputs/kanzi_real_ckpt_forward_q4_2026.json`); LineageFlow `f0b4b25e...54a2b` (`verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json`); FlowMol3 `data/flowmol3/weights_real/checkpoints/last.ckpt` (epoch 17, global_step 1,547,236). A reviewer re-verifies with each JSON's `sha256` field."
- `cover_letter.md:21` (G2 Upstream default sampling config) carries the per-model NFE / σ / seed pattern: "FlowMol3 uses upstream `flowmol.FlowMol.sample(...)` at the paper's default NFE 250 and σ=0.05; LineageFlow uses upstream `evaluation/evaluate_all.py` with `--nfe 250`; Kanzi uses upstream `kanzi.DAE.encode+decode+kabsch_rmsd`."

**REUSE pattern:** G1's "SHA-256 → JSON manifest pointer" pattern is generalisable to a **G1-stoch "decoder seed → JSON manifest pointer"** entry. Drop-in: append to G1 (or extend G2) a one-line per-model seed-handling disclosure: "FlowMol3 framework arm seeds via upstream `flowmol.FlowMol.sample(seed=42)` (verified Wave 74 F2); LineageFlow framework arm uses `np.random.seed(seed_base)` (per `data/lineageflow_upstream/...`); Kanzi `DAE.decode` is currently UNSEEDED (`torch.randn_like` writes the global torch RNG state) — see `wave88-phase3-final.md` §1.5 for σ=0.0947 Å evidence + remediation proposal (`--seed` flag threaded into `dae.decode`)".

**Cross-cite precedent for "decoder is stochastic + currently unseeded":**
- `supplementary.md:163` already discloses "Decoder stochasticity from `torch.randn_like` is unseeded (Wave 88 F-4: 8 records × 8 unseeded repeats, σ=0.095 Å run-to-run)" — same fact, lower-stakes placement.
- `paper-draft.md:2169` (Wave 88 §7.3 item 3) carries the longer form: "`DAE.decode` is stochastic and nothing seeds it. Per-record `reconstruction_kabsch_rmsd_A` has a run-to-run σ of 0.0947 Å over 8 real records × 8 unseeded repeats — about half the total across-record variance (`std = 0.132 Å` on the Wave 83 N=200 sweep). Neither `tools/sweep_kanzi_n1000_paper_metrics.py` nor the upstream `_KANZI_DRIVER` in `tools/upstream_eval.py` calls `torch.manual_seed` before `dae.decode`. The `"deterministic": true` field the sweep script writes (`sweep_kanzi_n1000_paper_metrics.py:239`) is **incorrect**, as is Wave 83's "result is deterministic + byte-stable" risk-mitigation claim (`wave83-phase4-final.md:306`). Pinning `torch.manual_seed(1234)` before each call drives the run-to-run spread to 0 (verified at Wave 88 F-4)."

**LOC delta vs new template:** ~5 LOC of drop-in text in G1 or G2.

---

### Check #6: Are there existing examples of "this number is from sweep X (N=Y), the previous number was from sweep Z (N=W), the difference is…"?

**YES — many, but inconsistently cited.**

| Existing example | Location | Pattern |
|---|---|---|
| Wave 79 n=2 → Wave 80 N=32 → Wave 83 N=200 → Wave 88 N=1000 progression | `paper-draft.md:2115` (§7.3 Wave 80 verdict transition) | "**Wave 80 verdict transition — Wave 79 placeholder verbiage → Wave 80 N=1000 infra-ready.** The Wave 79 §7.3 placeholder table cell ... is **superseded by the Wave 80 N=32 smoke baseline 0.887 Å** (different N, different coord-generator → not directly comparable; the N=32 smoke uses deterministic Gaussian variants ... while the Wave 79 N=2 used 2 demo records parsed directly). The Wave 79 reading is preserved additively; the Wave 80 reading supersedes the N=2 number ... **The Wave 73-74 `framework_improves` verdict on the internal composite axis is NOT deleted** by this Wave 80 update — the Wave 80 paragraph above adds new infra evidence; it does not retract the Wave 73-74 framing." |
| Same example, shorter form | `docs/audit/wave96e-final-synthesis.md:2232–2240` (§"Wave 92c vs Wave 95 P3.C vs Wave 96.D — the collapse-fix progression") | explicit per-Wave table: "Wave | Bridge | x_final source | n_unique_idx | RMSD (Å) | Verdict" with "1/10 → 1/10 → 10/10" cell |
| Wave 81 n=2 → Wave 84 n=5 → Wave 86 n=1000 progression | `cover_letter.md:11` (TL;DR) | "the on-disk `verification_outputs/lineageflow_n1000_*_q4_2026.json` files contain Wave 81 N=2 per arm data with `hmmscan_total_hits=0` both arms" + "sourced from Wave 86 N=1000 per arm sweep at `docs/audit/wave86-phase3-sweep.md` §2" |
| Wave 81 N=200 → Wave 86 N=1000 attribution | `supplementary.md:175–177` (§S4.1) | explicit cross-cite: "The `+116% framework_improves` claim ... is sourced from **Wave 86 N=1000 per arm sweep** ... NOT from Wave 81. Cover letter citation is correct in attributing the +116% to Wave 86 N=1000 per arm." |
| Per-Wave +116% misattribution fix | `docs/audit/wave106-a3-honesty-gaps.md:27` (finding #5) | "**+116% claim attribution to Wave 81 N=200 is FACTUALLY WRONG** — see findings 5/7/8/24." — explicit "Wave X attribution wrong, Wave Y attribution correct" prose. |
| Per-Wave addendum with commit SHA | `docs/CONSOLIDATED_RESULTS.md:2089–2174` (§15.14) | "Wave 91 — Kanzi latent→coord bridge (`dfe0f4e` + `8c5eaaf` + `2a4c46e`)" + "Wave 92a — Kanzi adapter constants fix (`73c6978`)" + "Wave 92b — Kanzi upstream N-samples patch (`60dcbb7`)" — explicit "(Wave-XX commit-SHA)" convention. |

**REUSE pattern:** the "**Wave XX verdict transition — Wave YY placeholder verbiage → Wave ZZ N=??? infra-ready**" prose at `paper-draft.md:2115` is the **most directly reusable template** for any new "this number is from sweep X (N=Y), the previous number was from sweep Z (N=W), the difference is…" disclosure. The pattern includes:
1. **Header sentence** naming both waves ("Wave 79 placeholder verbiage → Wave 80 N=32 smoke")
2. **Parenthesised explanation** of why the two readings are not directly comparable (different N, different coord-generator)
3. **Explicit verdict on the old reading** ("Wave 79 reading is preserved additively; the Wave 80 reading supersedes the N=2 number")
4. **Explicit verdict on the new reading** ("The Wave 73-74 `framework_improves` verdict ... is NOT deleted — the Wave 80 paragraph above adds new infra evidence; it does not retract the Wave 73-74 framing.")

**LOC delta vs new template:** ~6 LOC of drop-in text following the 4-part structure.

---

### Check #7: Do docs/Wave* audit docs have a Stochasticity disclosure section we can cite?

**YES — at least 5 distinct stochasticity disclosure sections exist.**

| Section | Location | Scope |
|---|---|---|
| **§1.5 Stochasticity of `DAE.decode` (Wave 88 F-4)** | `docs/audit/wave88-phase3-final.md:72–94` | THE primary decoder-stochasticity disclosure. Per-record σ table (8 records × 8 repeats), `torch.manual_seed(1234)` drops spread to 0, proposed `--seed` flag fix. |
| Wave 88 §1 F-4 finding | `docs/audit/wave88-phase3-final.md:18` (TL;DR item 3) | TL;DR-level summary: "**`DAE.decode` is stochastic and unseeded** — run-to-run σ of `reconstruction_kabsch_rmsd_A` is 0.0947 Å (8 records × 8 unseeded repeats), about half the total across-record variance on the Wave 83 N=200 sweep. The sweep script's `"deterministic": true` field and Wave 83's "byte-stable" claim are both incorrect." |
| Wave 88 §3.1 §F-4 cmd-line repro | `docs/audit/wave88-phase3-final.md:189–192` | re-executable probe: `.venvs/kanzi_venv/bin/python /tmp/wave88/probe_stochasticity.py` + `/tmp/wave88/probe_determinism.py` |
| Wave 91 Phase 5 §5 decoder stochasticity | `docs/audit/wave91-phase5-final.md:92` | "**Decoder stochasticity:** `DAE.decode` uses `torch.randn_like` for diffusion noise; unseeded, this contributes ~0.095 Å per-record run-to-run σ (Wave 88 F-4: 8 records × 8 unseeded repeats). Seeding drops the spread to 0." |
| Wave 96.E §5 honest std-target note | `docs/audit/wave96e-final-synthesis.md:139–164` | "Honest note on RMSD std target (0.214 vs > 0.5)" — the **template for any "we met the diversity bar but missed the std bar" framing** |
| Wave 99.B statistical-power analysis | `docs/audit/wave99b-n1000-verdict.md` (entire doc) | per-metric + Bonferroni + Wave 93 verdict precedence — the template for "underpowered at the 1pp detection floor" |
| Wave 106.A.3 honesty-gap audit | `docs/audit/wave106-a3-honesty-gaps.md:24–60` | 30 findings table with per-finding verdict (`none (honest)` / `low` / `medium` / `high`) — the audit-style findings table |
| Wave 93 Phase 2 statistical power | `docs/audit/wave93-phase2-final.md` (entire doc) | 12-row per-cell Bonferroni + post-hoc power + verdict precedence table |

**REUSE pattern:** `docs/audit/wave88-phase3-final.md:72–94` is the **canonical stochasticity disclosure citation**. The §1.5 section title "Stochasticity of `DAE.decode` (Wave 88 F-4, Kanzi only)" establishes a clean naming convention that the rest of the codebase follows. Any new stochasticity disclosure should follow the same:
1. **§N.M Stochasticity of `XYZ.fn` (Wave XX F-N, <scope>)** header
2. **Per-record σ table** with `mean / sd / min / max` columns
3. **Seed-pinning remediation evidence** ("torch.manual_seed(1234) drops spread to 0")
4. **95% CI computation** ("±0.186 Å at 95% — ≈72% of Wave 83 N=200 across-record std")
5. **Proposed fix** ("sweep script needs `--seed` flag threaded into `dae.decode` for next sweep")

**LOC delta vs new template:** ~30 LOC for a full Wave-88-§1.5-style disclosure section. The C.7 SBC template at `docs/baseline-audit-report.md:482–611` is the broader-context companion.

---

## 2. Synthesis — the single canonical stochasticity-disclosure template

Combining items 1–7 above, the single most reusable template for any new "stochastic run-to-run disclosure" is:

```
## §N.M Stochasticity of `XYZ.fn` (Wave XX F-N, <scope>)

| Probe | Result |
|---|---|
| `<op>` with fixed seed, M repeats | identical (deterministic) |
| `<op>` unseeded, M repeats | differs (stochastic) |
| `torch.manual_seed(S) before each call, M repeats | spread = 0 (pinnable) |

Per-record σ of `<metric>`, K real records × M repeats each:

| Record | mean | sd | min | max |
|---|---:|---:|---:|---:|
| 0 | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |
| **mean** | — | **σ̄** | — | — |

So a single-draw per-record `<metric>` carries ±X at 95%. This is ≈Y% of the
prior N=??? across-record std. Pinning `torch.manual_seed(S)` before each
call drives the per-record spread to 0. The sweep script needs a `--seed`
flag threaded into `<target_fn>` for the next sweep.

**Cross-references:**
- `cover_letter.md` (Honest limitations item N) — discloses this to reviewers.
- `paper-draft.md` §N.M — discloses this in the paper.
- `verification_outputs/<artifact>.json` — carries the per-record σ in the JSON.
```

This template is the Wave 88 §1.5 structure verbatim; reuse as-is.

---

## 3. Reuse-only path (no new code, no new sections)

For a paper-presentation update that needs to honestly present stochastic N=1000 data, the drop-in work is:

| File | Action | LOC delta |
|---|---|---|
| `cover_letter.md` | EXTEND "(1) Sample budget" paragraph at line 29 with one sentence cross-citing `wave88-phase3-final.md` §1.5 for the σ=0.0947 Å evidence + add a "(4) Decoder stochasticity" 4th limitation enumerating the per-model seed-handling state (FlowMol3 seeded via `flowmol.FlowMol.sample(seed=42)` per Wave 74 F2; LineageFlow seeded via `np.random.seed(seed_base)`; Kanzi `DAE.decode` UNSEEDED, σ=0.0947 Å). | ~5 LOC |
| `paper-draft.md` §7.3 Kanzi | EXTEND the Wave 88 F-4 paragraph at line 2169 with a sentence on "this stochasticity means single-draw N=10 framework arm carries ±0.186 Å 95% CI — the +0.864 Å verdict is robust (4.81σ pooled, Bonferroni p=4.6e-7 ≪ 0.0083) but the per-record variance is decoder-bound, not framework-bound". | ~3 LOC |
| `paper-draft.md` §7.5 FlowMol3 | EXTEND the §S5.4 honest caveat at line 252 with a sentence on "n_sampled=999 (1 molecule dropped, CTMC valence artifact) is consistent with Wave 87 §"Honest caveats" #7; framework arm n_sampled=1000 is unaffected". | ~2 LOC |
| `paper-draft.md` §7.6 honest verdict | EXTEND with a sentence cross-citing `wave96e-final-synthesis.md` §5 for the "met diversity bar but missed std bar" framing where applicable. | ~2 LOC |
| `paper-draft.md` §7.7 NFE-aware | ADD a sentence: "The 6-point NFE scan (§7.7.3) is deterministic per seed — σ within seed = 0.000000 — because the framework's `solve_ode` reads `trajectory[-1]` as a deterministic function of `(seed, model_weights)`; decoder stochasticity (§F-4) does not enter this axis." | ~2 LOC |
| `supplementary.md` §S3.5 Honest caveats | EXTEND line 163 with a sentence cross-citing the per-Wave 88 F-4 σ=0.0947 Å table; ADD a 4th item: "**Decoder seed-handling per model family.** FlowMol3 framework arm seeds via `flowmol.FlowMol.sample(seed=42)` (Wave 74 F2 byte-stable across 3 runs); LineageFlow framework arm seeds via `np.random.seed(seed_base)` per upstream `evaluation/evaluate_all.py`; Kanzi `DAE.decode` is currently UNSEEDED (Wave 88 F-4 σ=0.0947 Å run-to-run) — proposed fix: `--seed` flag threaded into `dae.decode`." | ~6 LOC |
| `supplementary.md` §S5.5 Honest caveats | EXTEND line 258 with a sentence: "The FlowMol3 framework arm's `fg_dev` is **byte-stable across 3 runs** at `0.6146` (Wave 74 F2 + Wave 82 + Wave 87 N=1000 byte-stable reproduction) — the framework's restart-blend noise is reproducible per seed even though the upstream `flowmol.FlowMol.sample` does not pin torch RNG; this is the framework-side determinism that makes the 4.05σ verdict reproducible." | ~3 LOC |
| `docs/CONSOLIDATED_RESULTS.md` §15.16 | (NO edit required — already cross-cites `wave88-phase3-final.md` §1.5 and `wave96e-final-synthesis.md` §5 verbatim.) | 0 LOC |
| NEW: `docs/audit/wave107-a4-paper-presentation.md` | THIS FILE (research output, no edits to paper). | N/A |

**Total LOC delta across paper-package files:** ~23 LOC of drop-in prose + table cells. **No new template code required.**

---

## 4. Cross-doc cross-reference graph (what to cite where)

```
cover_letter.md:29 (Honest limitations item 1, "Sample budget")
  └── [EXTEND] cross-cite wave88-phase3-final.md:72 (decoder stochasticity)
                cross-cite wave96e-final-synthesis.md:139 (std target missed)
                cross-cite wave93-phase2-final.md (per-cell Bonferroni)

cover_letter.md:31 (Wave 99 Kanzi update, "REGRESSES_BY_+0.864_Å")
  └── [NO EDIT — already cross-cites wave92c §5 architectural + wave99b-n1000-verdict.md]
  └── [OPTIONAL EXTEND] cross-cite wave88-phase3-final.md:72 (decoder stochasticity
                bounds the +0.864 Å magnitude to a real effect, not a sweep artifact)

paper-draft.md §7.3 Kanzi (line 2169, Wave 88 F-4 paragraph)
  └── [EXTEND] cross-cite wave93-phase2-final.md (per-cell Bonferroni table)
                note: framework arm at N=10 is well-powered for the 0.864 Å direction
                but the magnitude bound depends on decoder σ

paper-draft.md §7.5 FlowMol3 (line 252, §S5.4 F-02 caveat)
  └── [NO EDIT — already cross-cites wave87 §"Honest caveats" #7]
  └── [OPTIONAL EXTEND] cross-cite wave74 F2 (byte-stable 3-run reproduction of fg_dev)

paper-draft.md §7.7 NFE-aware (line 4125, §F-4 honest caveat)
  └── [EXTEND] add per-seed σ = 0.000000 for the composite axis (deterministic by construction)

supplementary.md §S3.5 (line 163, FSQ quantisation noise floor)
  └── [EXTEND] cross-cite wave88-phase3-final.md:72 (decoder σ = 0.0947 Å evidence)
  └── [ADD item 4] per-model decoder seed-handling (FlowMol3 / LineageFlow / Kanzi)

supplementary.md §S5.5 (line 258, PB-xtb version dependency)
  └── [EXTEND] cross-cite wave74 F2 (byte-stable 3-run fg_dev reproduction)

docs/CONSOLIDATED_RESULTS.md §15.16 (line 2261, Wave 96.E final synthesis)
  └── [NO EDIT — already cross-cites wave88-phase3-final.md:72 + wave96e-final-synthesis.md:5]

docs/baseline-audit-report.md §C.7 (line 482, SBC stochasticity template)
  └── [REUSE VERBATIM] the N=200/N=1000/N=10000 chi²/p table + pass_label enum
  └── [REUSE VERBATIM] the seed_offset rationale at line 521 for "deep N=1000 sweep
                reproduces independently of N=200 smoke"

docs/audit/wave88-phase3-final.md §1.5 (line 72, decoder stochasticity)
  └── [CITED from cover_letter.md + paper-draft.md §7.3 + supplementary.md §S3.5]
  └── [NO EDIT — this is the canonical stochasticity-disclosure document]

docs/audit/wave96e-final-synthesis.md §5 (line 139, honest std-target note)
  └── [CITED from paper-draft.md §7.6 + supplementary.md §S3.5]
  └── [NO EDIT — this is the canonical "met bar but missed bar" document]
```

---

## 5. Honesty-gap self-check

Per `docs/audit/wave106-a3-honesty-gaps.md` and `Wave 106.A.4 path-consistency`, the existing honesty surface already discloses:

- Kanzi framework arm at N=10, not N=1000 — **disclosed** at `cover_letter.md:31` (Wave 99 update) and `submission_checklist.md:43` (Kanzi / `reconstruction_kabsch_rmsd_A` row).
- Wave 79 n=2 framework-arm proxy `Δ=+0.27 Å` retracted — **disclosed** at `paper-draft.md:2167` (Wave 88 §7.3 item 2: "The Wave 79 n=2 framework-arm proxy (`baseline 1.40 Å vs framework 1.67 Å, Δ=+0.27 Å`) is an artifact and should be retracted") and `wave88-phase3-final.md:18` (TL;DR item 2).
- `DAE.decode` stochasticity + unseeded — **disclosed** at `paper-draft.md:2169` (Wave 88 §7.3 item 3) and `supplementary.md:163` (§S3.5 FSQ quantisation noise floor).
- 1 molecule dropped from FlowMol3 baseline arm (n_sampled=999) — **disclosed** at `submission_checklist.md:35` (FlowMol3 / `fg_dev` row) and `supplementary.md:252` (§S5.4 F-02 caveat).
- LineageFlow N=1000 framework-vs-baseline +116% claimed is from Wave 86, NOT Wave 81 — **disclosed** at `cover_letter.md:11` (TL;DR) and `supplementary.md:175–177` (§S4.1) and `wave106-a3-honesty-gaps.md:27` (finding #5).
- LineageFlow N=1000 foldability + self_consistency DEFERRED — **disclosed** at `submission_checklist.md:40–42` (LineageFlow / `foldability` / `self_consistency` rows).
- 5 Kanzi codebook metrics `TIED_BY_DESIGN` — **disclosed** at `cover_letter.md:29` (Honest limitations item 3) and `submission_checklist.md:44–46` (Kanzi / codebook rows).
- Framework wall-clock cost on Kanzi is 1.28× baseline (real ckpt, paired N=100) — **disclosed** at `paper-draft.md:2180` (Wave 88 F-1 framework liveness evidence).

**Stochasticity disclosures NOT yet made that this research identifies as needed:**

1. **Per-model decoder seed-handling** (FlowMol3 seeded; LineageFlow seeded via np.random; Kanzi UNSEEDED) — partial coverage at `supplementary.md:163`, no cover-letter mention. **FIX**: extend `cover_letter.md` item (1) with one sentence.
2. **`n_sampled=999` ↔ `n_sampled=1000` arm-asymmetry** — partial coverage at `submission_checklist.md:35` and `supplementary.md:252`, no cover-letter TL;DR mention. **FIX**: extend `cover_letter.md` item (1) with one sentence.
3. **Kanzi +0.864 Å magnitude bound depends on decoder σ** — partial coverage at `paper-draft.md:2169` (Wave 88 F-4), no `Wave 96.D`/`Wave 99.B` cross-cite. **FIX**: extend `paper-draft.md` §7.3 with one sentence.
4. **Framework-side determinism that makes `fg_dev` byte-stable across 3 runs at 0.6146** — partial coverage at `paper-draft.md:2609` (Wave 87 §"Honest caveats" #7), no explicit "framework side is seeded; upstream is not; framework-side determinism is reproducible" framing. **FIX**: extend `supplementary.md` §S5.5 with one sentence.
5. **NFE-scan composite axis is deterministic per seed (σ=0)** — partial coverage at `paper-draft.md:1993` (§7.7.3 per-seed stability table), no explicit "decoder stochasticity does not enter this axis because trajectory[-1] is deterministic in (seed, model_weights)". **FIX**: extend `paper-draft.md` §7.7 with one sentence.

All 5 fixes are ≤ 3 LOC of drop-in text per fix. **Total honesty-gap remediation: ~15 LOC.**

---

## 6. JSON return

```json
{
  "commit_sha": "c0dd9e49251a6de845e034e68bd086e85aeec485",
  "files_audited": [
    "/home/hugo/codes/flowa-multistep-reinference/cover_letter.md",
    "/home/hugo/codes/flowa-multistep-reinference/submission_checklist.md",
    "/home/hugo/codes/flowa-multistep-reinference/supplementary.md",
    "/home/hugo/codes/flowa-multistep-reinference/docs/paper-draft.md (lines 1815–2414, §7.1–§7.4)",
    "/home/hugo/codes/flowa-multistep-reinference/docs/CONSOLIDATED_RESULTS.md (lines 1–2900, §1–§15.16)",
    "/home/hugo/codes/flowa-multistep-reinference/docs/baseline-audit-report.md (lines 1–2945, esp. §C.7 lines 482–611)",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave88-phase3-final.md (esp. §1.5 lines 72–94)",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave91-phase5-final.md (line 92)",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave96e-final-synthesis.md (esp. §5 lines 139–164)",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave99b-n1000-verdict.md (cited)",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave93-phase2-final.md (cited)",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave106-a3-honesty-gaps.md (lines 24–60)",
    "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/flowmol/model_utils/load.py (seed_ckpt param at line 13)",
    "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/flowmol/models/flowmol.py (sample signature at line 490)"
  ],
  "external_libs_audited": [
    "torchdiffeq (already in pyproject.toml — for ODE solvers; no stochasticity disclosure)",
    "biotite 1.7.1 (already in pyproject.toml — deterministic per input)",
    "transformers (vendored at data/lineageflow_upstream/ — EsmModel dtype fix at Wave 47 Agent B F-4)",
    "posebusters 0.6.5 (PB-xtb UFF-vs-xtb definitional gap disclosed at cover_letter.md:29)",
    "fair-esm (vendored at data/lineageflow_upstream/ — deterministic per seed)",
    "rdkit (vendored at FlowMol3 upstream — CTMC valence artifact at Wave 87 §'Honest caveats' #7)",
    "torch.randn_like (Kanzi DAE.decode — UNSEEDED, σ=0.0947 Å run-to-run per Wave 88 F-4)"
  ],
  "reuse_opportunities_count": 11,
  "output_file": "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave107-a4-paper-presentation.md"
}
```

**11 reuse opportunities, all drop-in. NO new template code required. ~23 LOC of paper-package drop-in text + ~15 LOC of honesty-gap remediation = ~38 LOC total.**


---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
