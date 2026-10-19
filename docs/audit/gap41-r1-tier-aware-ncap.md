# GAP-41 — R1 tier-aware n_cap: transplanting the R6 easy-tier lever onto the R1 headline

**Date:** 2026-10-16
**Author:** GAP-41 agent (USER AUTHORIZED, NO PUSH)
**Scope:** the user directive that near-miss headline metrics could be flipped by
*"改几处关键代码"*. GAP-38/39/40/40b/34 swept every *LineageFlow-side* dormant
knob (shared prior, restart-blend, classifier-aware restart, non-conserving bias,
init temperature) and all failed to move the R1 near-miss. GAP-41 is the last
candidate identified in the dormant-lever survey: the **R6 tier-aware `n_cap`
mechanism**, applied to the R1 (HMMER-hit) metric.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Result |
|---|---|
| Mechanism under test | the R6 **tier-aware `n_cap`** scheduler path (`--tier-aware-n-cap 0.5` + a baseline pLDDT `foldability.jsonl`), which trims restart NFE for records whose *baseline* pLDDT is already high |
| Screen | N=200 gate-open, seed 42: `legacy` 38 → **`tier_a` 50** hits (**+12**, +31.6 %), per-record MWU `p=0.120` — the strongest lever seen in the whole survey |
| Decisive test | N=1000, 3 seeds (42/43/44), gate-open, canonical HMMER counter, control arms reused from the archived GAP-40 `n1000_gate_open` run |
| **Seed-level result** | per-seed diffs **[−5, +14, +17]**, mean **+8.67** hits, `d_z=0.726`, **2/3 seeds positive**, `p_bonf_rlevel=1.0` → **NOT STRONG** (fails both the `d_z>0.8` bar and the 3/3 direction criterion) |
| **Per-record DL meta** | `tier vs legacy` `d_pooled=+0.0196`, `z=1.07`, `p_two=0.284` → **not significant** |
| **The +12 screen did not replicate** | the N=200 signal collapsed to a wash at N=1000, exactly as GAP-40b's N=200 `negative` screen did |
| Cross-metric note | `tier` is a wash vs **both** `legacy` (`d_z=0.73`) and the GAP-40 `centered` arm (`d_z=−0.28`) — it is not a stronger version of the classifier-aware lever, it is a different (inert) knob |
| Net | The R6 tier-aware mechanism is **real and wired** (framework FASTAs byte-distinct from every control arm) but **does not flip the R1 near-miss**. Sixth consecutive dormant lever to fail at n=3. The gap remains **power**, not code. No frozen surface moved. |

---

## 1. Motivation

The R6 sweep (`docs/audit/gap30-r6-fresh-tier.md`,
`docs/audit/gap01-r6-tier-aware-live.md`) established a **tier-aware `n_cap`**
scheduler: records whose *baseline* foldability (pLDDT) is already high are placed
in an "easy" tier and given a **reduced** restart NFE budget, concentrating
compute on the hard tier. On R6 this mechanism moves the live metric, and the R6
driver validates it end-to-end.

The dormant-lever survey (GAP-41 preamble) asked whether the **same
already-coded mechanism** could be transplanted to R1. The hypothesis: R1's
framework arm restarts from the baseline state; if the tier-aware path spends
its restart budget differently (fewer rounds for already-easy records, more
relative compute elsewhere), the HMMER-hit total could shift — a *few lines of
wiring*, no new model.

The R1 canonical driver (`tools/gen_lineageflow_n1000_fastas.py`) already
exposes `--scheduler {cosine, tier_aware_codimension}`, `--tier-aware-n-cap`, and
`--tier-aware-baseline-metrics-jsonl`, but the canonical gate-open sweep leaves
them at defaults (cosine, no cap). GAP-41 turns them on.

---

## 2. Design

Two stages, mirroring the GAP-40 / GAP-40b protocol:

**Screen (N=200, seed 42).** `run_screen.sh` generates three arms at the
canonical gate-open config (`--nfe 10 --n-rounds 3 --restart-min-nfe 5
--temperature 1.0`, `force_mode=auto` real-ckpt, GPU 0):

| arm | flags |
|---|---|
| `legacy` | (cosine default) |
| `tier_a` | `--tier-aware-n-cap 0.5 --tier-aware-baseline-metrics-jsonl <k6 foldability.jsonl>` |
| `tier_b` | `tier_a` **plus** `--scheduler tier_aware_codimension` |

**Decisive (N=1000, seeds 42/43/44).** `run_tier.sh` generates the `tier` arm at
the same config for three seeds. `baseline` / `legacy` / `centered` controls are
**reused byte-for-byte** from the archived GAP-40 `n1000_gate_open` run
(`/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap40-n1000-work`); the tier baseline FASTAs are md5-checked equal
to the GAP-40 reference at generation time.

Scoring is the canonical R1 HMMER counter (`hmmscan --noali --cpu 32 --tblout
--acc Pfam-A.hmm`; hits = non-comment `tblout` lines). Statistics: canonical
seed-level protocol (`d_z`, `t`, `p_two`, `p_bonf_rlevel = min(1, 16·p_two)`,
3/3 direction) plus per-record paired-`t` + DerSimonian–Laird random-effects meta
(`tools/gap41_tier_analysis.py`, identical pipeline to GAP-40 §4b.3).

---

## 3. Results

### 3.1 N=200 screen (seed 42)

| arm | total hits | records ≥1 | hits/record |
|---|---:|---:|---:|
| baseline | 37 | 30 | 0.1850 |
| legacy | 38 | 32 | 0.1900 |
| **tier_a** | **50** | **41** | **0.2500** |
| **tier_b** | **50** | **41** | **0.2500** |

`tier_a` and `tier_b` are **byte-identical** (framework md5
`3ecc30481d505c3a1e883172e5e35a2e`) → `--scheduler tier_aware_codimension` is a
**no-op**; the entire effect is driven by `--tier-aware-n-cap 0.5` + the baseline
`foldability.jsonl`. `tier_a vs legacy` per-record MWU `p=0.120` — directional
but not significant at the single-seed screen. The baseline arm is byte-stable.
Screen decision: advance to the decisive N=1000 sweep.

### 3.2 Decisive N=1000 3-seed sweep

| seed | baseline | legacy | centered | **tier** |
|---:|---:|---:|---:|---:|
| 42 | 158 | 257 | 271 | **252** |
| 43 | 159 | 265 | 269 | **279** |
| 44 | 174 | 245 | 265 | **262** |

**Seed-level pooled (n=3, df=2, canonical R1 protocol):**

| comparison | per-seed diffs | mean | `d_z` | `p_two` | `p_bonf_rlevel` | 3/3 dir | STRONG? |
|---|---|---:|---:|---:|---:|:--:|:--:|
| **tier vs legacy** | [−5, 14, 17] | +8.67 | **0.726** | 0.335 | **1.0** | ✗ (2/3) | **no** |
| tier vs centered | [−19, 10, −3] | −4.00 | −0.275 | 0.680 | 1.0 | ✗ (1/3) | no |
| tier vs baseline | [94, 120, 88] | +100.67 | 5.918 | 0.0094 | 0.150 | ✓ | no |
| legacy vs baseline | [99, 106, 71] | +92.00 | 4.968 | 0.0132 | 0.212 | ✓ | no |
| centered vs legacy | [14, 4, 20] | +12.67 | 1.567 | 0.113 | 1.0 | ✓ | no |

The `legacy`/`centered` control rows reproduce the GAP-40 §4b.2 numbers exactly
(`centered vs legacy` mean +12.67, `d_z=1.567`) — the pipeline is the same one.

**Per-record paired t (df=999) + DerSimonian–Laird meta:**

| comparison | per-seed `d_z` | DL `d_pooled` | DL `z` | DL `p_two` | `p_bonf,k=7` |
|---|---|---:|---:|---:|---:|
| **tier vs legacy** | −0.010 / +0.032 / +0.037 | **+0.0196** | 1.07 | **0.284** | 1.0 |
| tier vs centered | −0.029 / +0.016 / −0.005 | −0.0059 | −0.32 | 0.748 | 1.0 |
| tier vs baseline | +0.143 / +0.172 / +0.132 | +0.1491 | 8.12 | 4.6e-16 | 3.2e-15 |
| centered vs legacy | +0.025 / +0.008 / +0.040 | +0.0243 | 1.33 | 0.184 | 1.0 |

The `centered vs legacy` DL row (`d_pooled=+0.0243`, `z=1.33`, `p=0.184`)
reproduces GAP-40 §4b.3 **exactly** — confirming the statistics pipeline.

### 3.3 The screen did not replicate

The N=200 `tier_a` +12 (+31.6 %) signal **collapsed to a wash** at N=1000:
mean **+8.67** hits, **only 2 of 3 seeds positive**, `d_z=0.726` (below the
pre-registered `>0.8`), `p_bonf_rlevel=1.0`, per-record DL `p=0.284`. This is the
same pattern as GAP-40b (`negative` 47 vs 44 at N=200 → `d_z=0.234`, 2/3 at
N=1000): a single-seed screen at N=200 has ~±8 hits of noise, and the tier lever
sits inside it.

---

## 4. Verdict

* **The R6 tier-aware mechanism is real and wired, but inert on R1.** The tier
  framework FASTAs are byte-distinct from `legacy`, `centered`, and `baseline`
  (three distinct md5s per seed) and the manifests record
  `tier_aware_n_cap=0.5` — the mechanism genuinely engaged. It simply does not
  move the HMMER-hit total beyond noise.
* **`tier` is not a stronger `centered`.** `tier vs centered` is `d_z=−0.28`
  (a wash / slight negative); the two knobs act on different parts of the
  restart budget and neither clears the R1 bar.
* **The R1 near-miss is not code-limited.** This is the sixth consecutive
  dormant lever (GAP-38 shared prior, GAP-39 restart-blend, GAP-40
  classifier-aware restart, GAP-40b non-conserving bias, GAP-34 init temperature,
  GAP-41 tier-aware n_cap) that is *wired and active* yet fails the n=3 STRONG
  criterion. The pre-registered bar requires `p_two < 1.95e-4` (i.e. `d_z > 17.7`)
  at n=3 — unreachable for a realistic effect size regardless of wiring.
* **The gap is power, not code** — consistent with
  `project_dormant_levers` and the GAP-37 power audit.

---

## 5. Honest scope / what is NOT claimed

* The N=200 `tier_a` +12 is reported as observed; it is **explicitly not
  promoted** — it did not replicate at N=1000.
* No claim that the tier-aware path is useless in general; only that it does not
  flip the **R1** near-miss at the canonical config.
* No R1/K4/K5/K7 verdict promotion. The R1 headline is untouched.
* No promotion of any frozen surface. Observations-only.

---

## 6. Reproduce

```bash
# screen (N=200, seed 42)
bash /home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-n200/run_screen.sh
# decisive (N=1000, seeds 42/43/44)
bash /home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-n1000/run_tier.sh
# statistics (CPU-only)
python tools/gap41_tier_analysis.py     # writes /home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-n1000/analysis.json
```

Evidence: `verification_outputs/gap41-r1-tier-aware-ncap/`
(`n200_screen/` + `n1000_gate_open/` — `*_tblout`, `*_manifest.json`,
`hits.txt`, `FASTA_MD5.txt`, `summary.json`, `analysis.json`,
`gap41_tier_analysis.py`).
