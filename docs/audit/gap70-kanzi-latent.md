# GAP-70 — Kanzi token-selective latent blend: two premise errors found before the code

**Date:** 2026-10-23
**Author:** GAP-70 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` `GAP-70-ADAPTER-KANZI-LATENT` (P1).
**Status:** code landed behind a default-off flag; **the acceptance test cannot
be run as written** — see §0.2. No GPU spent.
**Frozen surfaces:** untouched.

---

## 0. Pre-registration and premise audit (written before the code)

### 0.1 What the gap claims

`todo.json` GAP-70 says K7 is "the least explained number in the paper: 12.6×
less novel (3.7 % vs 46.6 %, McNemar p=1e−102)" and attributes it to Kanzi's
64×64 continuous latent, where "the blend treats all 4096 coordinates alike".
The proposed lever is a decoder-aware blend that leaves the identity-carrying
tokens fresh.

### 0.2 Two premise errors

**P1 — K7 is a LineageFlow cell, not a Kanzi cell.** Every canonical record
names LineageFlow:

* `docs/audit/gap50-evidence-grade-table.md:40` — `| K7 | LineageFlow | novelty |`
* `docs/audit/wave306-11-cell-alignment.md:25` — `K7 | LineageFlow novelty`
* `paper-data/K7_lineageflow_novelty/REPRODUCIBILITY_RECIPE.md:1`

The 46.6 % / 3.7 % numbers come from
`verification_outputs/novelty_pctid_w166_q3_2026/{baseline,framework}/n1000_full_loose.m8`,
which are mmseqs searches of **LineageFlow FASTA files**
(`data/lineageflow_n1000/`), scored by
`tools/lineageflow/novelty_metric_pctid.py`. Kanzi contributes no sample to
that number. Kanzi's cells are **R2** (Kabsch RMSD) and **K4** (decision-metric
saturation).

Consequence: **a change to `KanziAdapter.apply_restart_distribution` cannot move
K7.** Whatever the token-selective blend does, the K7 regression will read
exactly as it does today.

**P2 — no Kanzi driver measures validity or novelty.** The acceptance criterion
is "validity and novelty measured on the SAME samples, same seeds, N=1000". No
Kanzi tool computes either:

| driver | metrics |
|---|---|
| `tools/sweep_kanzi_n1000_paper_metrics.py` | `reconstruction_kabsch_rmsd_A`, 5 codebook metrics |
| `..._framework_paper_metrics.py` | same |
| `..._framework_paper_metrics_inv_proj.py` | same |
| `tools/sweep_kanzi_n1000_diverse.py` | same |
| `tools/sweep_kanzi_paired_restartblend.py` | paired RMSD t-test |

Grep of `verification_outputs/kanzi_n1000_paper_metrics/kanzi_n1000_paper_metrics.json`
confirms: no `validity`, no `novelty` key. So the acceptance test requires a
Kanzi → FASTA → (hmmscan, mmseqs) pipeline that does not exist. Building it is a
larger job than the blend, and it is **not** what `agent_action` step 3 asks for.

**P3 — the saliency signal is not computable in-repo.** The design says "blend
only the latent tokens whose decoded contribution is below a threshold
(estimated by masking)". Masking means a decoder forward pass per latent
position: 64 positions × N records. Nothing in the repo does this, and
`tools/kanzi_latent_to_coord.py` decodes a whole `(L, 512)` latent in one pass,
not per position. So the threshold in the design has **no input**.

### 0.3 What this commit therefore does, and does not, do

Does: implements the **mechanism** the gap asks for — a per-token blend behind a
default-off flag, with the signal supplied by the caller through a documented
per-record key. This is step 3 of `agent_action`, and it is the only step that
does not depend on P1/P2/P3.

Does not: run anything, or claim any effect on K7. Steps 4–5 of `agent_action`
are blocked by P1 (wrong adapter) and P2 (no metric).

### 0.4 The mechanism, fixed before the code

`blended[i] = m_vec[i] · prior[i] + (1 − m_vec[i]) · fresh[i]` with

```
m_vec = m_base · w,        w ∈ [0, 1]^{L_z},  m_base = 1 − beta
```

`w` is read per record from `prior_entry["token_keep_weights"]`. The schedule
still owns the global level `m_base`; `w` only **redistributes** it across
positions, so `w ≡ 1` reproduces the existing scalar blend exactly and the
endpoints (`m_base = 0`, `m_base = 1`) are unchanged for every `w`. There is no
new hyperparameter and no hidden heuristic: the experiment supplies `w`.

**Fail closed.** `token_selective_blend=True` with the key absent raises
`CapabilityMissingError` rather than falling back to the scalar path. The
GAP-69 incident is the precedent: a silent fallback produced a run that looked
valid and was not (`docs/audit/gap69-lineageflow-profile.md` §1.4).

### 0.5 What would falsify the design hypothesis — on the correct adapter

Since the hypothesis cannot be tested on Kanzi (§0.2 P1), this section states
what a **re-scoped** test would have to show, so a future run cannot be
retrofitted:

* On LineageFlow samples (where K7 lives), a position-selective blend must hold
  validity (Pfam hit rate, 53.8 % → 96.3 % baseline → framework on record) while
  cutting the novelty drop from 12.6× to ≤ 2×.
* If validity falls, the trade-off is real and the blend is not free.
* If the novelty drop is unchanged, the decoder prior / blend locality is not
  the lever and K7 stays an unexplained boundary.

### 0.6 Limitation

`L1` — a per-token blend on a `(L_z, d)` latent assumes position `i` of the
latent is the token that decodes to position `i` of the sequence. The
inverse-projection bridge (`tools/kanzi_latent_to_coord.py:88-103`) quantises
the whole latent to FSQ codes and decodes them in one rollout, so this
correspondence is an assumption, not a verified property.

---

## 1. Code landed

`adaptive_reflow/adapters/kanzi.py`:

* `KanziAdapter(..., token_selective_blend: bool = False)` — default off.
* When on, `apply_restart_distribution` reads `prior_entry["token_keep_weights"]`
  (`(L_z,)`, finite, in `[0, 1]`), forms `m_vec = m_base · w`, broadcasts over
  `d`, and blends per position.
* The digest records `token_keep_weights` only when the path is active, so the
  default path stays byte-identical.
* Provenance gains `kanzi_token_selective_blend` only on the opt-in path.
* Missing / malformed weights raise `CapabilityMissingError` — never a silent
  scalar fallback.

## 2. Status

| item | state |
|---|---|
| §0 premise audit | done — K7 is LineageFlow (P1), no Kanzi validity/novelty driver (P2), no saliency signal (P3) |
| step 3: token-selective blend behind a flag | **landed**, default off |
| step 4: run validity + novelty on the same samples | **blocked** by P1 + P2 |
| step 5: 6 gates + commit | gates run; commit is this file |
| verdict | none — there is nothing to verdict |

**Recommendation (user decision).** GAP-70 as written cannot reach its
deliverable ("K7 stated as an unexplained boundary with the latent hypothesis
excluded") because excluding the latent hypothesis requires a Kanzi novelty
measurement that does not exist. Two re-scopes are available:

1. **Re-scope to LineageFlow**, where K7 actually lives: implement the
   position-selective blend on `LineageFlowAdapter` and measure validity +
   novelty on the same samples. The GAP-69 infrastructure (Pfam profile,
   mmseqs recipe) already exists.
2. **Keep Kanzi** and first build the Kanzi validity/novelty pipeline (FASTA
   export → hmmscan + mmseqs), then test the blend against it. Larger, and it
   still cannot move K7.

This agent does not choose between them.
