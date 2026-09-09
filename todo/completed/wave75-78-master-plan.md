# Wave 75-78 master plan — Tier 3 paper-metric reproduction

**Date:** 2026-09-08
**Owner:** framework maintainer
**Status:** Wave 75 in flight; 76/77/78 planned

> **Sample count strategy (revised 2026-09-08):** All 3 Tier 3 paper
> reproductions use **N = 1000 samples per arm** (baseline + framework)
> — Strategy B. This bounds total wall-clock at ~5-10 hours for all 3
> models combined (vs 30-50 hours for full-spec 5K-50K). See §5b below
> for rationale + per-model wall-clock breakdown.

## 0. Problem statement

Wave 71-74 claimed Tier 3 models (Kanzi / LineageFlow / FlowMol3) are SOTA based on our framework's **internal composite metric** (entropy_reduction + max_prob_delta + argmax_turnover). This is **not** the FlowMol3/LineageFlow/Kanzi papers' published metrics:

| Model | Paper-reported metrics (what reviewers care about) | What we measured |
|---|---|---|
| FlowMol3 (NeurIPS 2024) | validity_pct (RDKit sanitization), pb_validity_pct (PoseBusters full), fg_dev (vs GEOM_DRUGS), ood_ring_rate | composite (internal) |
| LineageFlow (ICML 2026) | family_validity (HMMER), foldability (OmegaFold pLDDT), self_consistency (ESM-IF1), novelty (MMseqs2) | composite (internal) |
| Kanzi (ICLR 2026) | FBD, perplexity, motif coverage, structural validity (need paper verify) | composite (internal) |

**Without paper-metric reproduction, the §7 Tier-3 SOTA claims are not defensible.** Wave 75-78 closes this gap one model at a time to bound server load.

## 1. Constraints (locked in by user 2026-09-08)

- **One model at a time** — no parallel Wave 76/77/78 (avoid server overload; 2 GPUs available)
- **Align 1:1 with upstream repo** — no new metric invention; call upstream functions / use vendored reference data
- **Honest caveats everywhere** — if paper metric diverges from target > 5%, do not fabricate narrative; just document the gap
- **D.4 byte-stable preservation** — every code change preserves D.4 vectors 72/72
- **NO push** — all commits local; user decides push
- **Interface-first** — every new flag is opt-in; legacy default unchanged

## 2. Wave sequence

### Wave 75 (IN FLIGHT) — FlowMol3 paper reproduction
- **Status**: Workflow `w9sveok4w` running
- **Upstream**: `data/FlowMol3/repo/` vendored (clone of https://github.com/Dunni3/FlowMol, commit 77cae22)
- **4 paper metrics to reproduce**: validity_pct / pb_validity_pct / fg_dev / ood_ring_rate
- **Paper target**: validity 0.999, pb_validity 0.919, fg_dev 0.27, ood_ring_rate 0.10
- **6 phases**: audit → implement metrics → reproduce → framework compare → paper update → final synthesis
- **Expected**: ~100-170 min wall-clock

### Wave 76 (NEXT) — LineageFlow paper reproduction
- **Trigger**: Wave 75 commits landed
- **Upstream**: `data/lineageflow_upstream/` vendored (clone of https://github.com/Jinx-byebye/LineageFlow, ICML 2026)
- **Key upstream file**: `data/lineageflow_upstream/evaluation/evaluate_all.py`
- **4 paper metrics to reproduce**: family_validity (HMMER), foldability (OmegaFold pLDDT), self_consistency (ESM-IF1), novelty (MMseqs2 NN identity)
- **5-6 phases**: audit → wire upstream eval → reproduce → framework compare → paper §7.4 update → final synthesis
- **Expected**: ~60-90 min wall-clock (upstream eval pipeline is already vendored, no clone step)

### Wave 77 (THEN) — Kanzi paper reproduction
- **Trigger**: Wave 76 commits landed
- **PRE-REQUISITE**: clone Kanzi upstream repo from github (NOT yet vendored)
  - Need: source code for evaluation + reference distribution for any distribution-based metric
  - Action: `git clone <kanzi-upstream-url>` into `data/kanzi_upstream/` (TBD: confirm URL from Kanzi paper/ICLR 2026)
- **Paper metrics to identify**: read Kanzi paper / upstream README for actual reported metrics (FBD / perplexity / motif coverage / structural validity — to be confirmed in Phase 1 audit)
- **5-6 phases**: clone upstream → audit → wire eval → reproduce → framework compare → paper §7.3 update → final synthesis
- **Expected**: ~120-180 min wall-clock (clone + paper metrics + framework eval)

### Wave 78 (FINAL) — Cross-tier paper-metric synthesis + push-ready
- **Trigger**: Wave 77 commits landed
- **Goal**: synthesize 3 Tier 3 paper-reproduction outcomes (Kanzi + LineageFlow + FlowMol3) + Tier 1 (already done in Wave 73) + update paper §1 abstract + §7.3/§7.4/§7.5 + final push-ready summary
- **5 phases**: aggregate all Wave 75-77 paper-metric results → update §1 / §7 / §8 → verify D.4 + G-MASTER + mkdocs → final synthesis → update push-ready-summary.md
- **Expected**: ~60 min wall-clock (paper-writeup only; no new eval runs)

## 3. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Kanzi upstream not publicly accessible | P1 | If no public github, fall back to paper PDF + reverse-engineer metrics from tables |
| Paper-metric divergence > 5% on Kanzi | P1 | Document as honest negative; do not fabricate narrative |
| Sample count > 10K becomes GPU-bound (> 2 hours) | P2 | Use 5K samples (statistical power for validity + ood_ring_rate; less for fg_dev which is distribution-level) |
| LineageFlow upstream eval needs HMMER + OmegaFold + MMseqs2 + ESM-IF1 (heavy deps) | P1 | Check which deps are in lineageflow_venv already; document missing deps as honest caveat |
| FlowMol3 paper reproduction FCD is HUGE (needs 50K+ samples, hours on RTX PRO 6000) | P2 | We report validity / pb_validity / ood_ring_rate (5K samples enough); FCD is reported but flagged as partial-sample caveat |
| Wave 76/77 verdict is REGRESSION (framework worse than baseline on paper metrics) | P1 | Reframe §7.4 / §7.3 — paper-metric negative + composite-benchmark positive is honest mixed story |
| User wants to push before all 4 waves complete | P2 | Each wave commits independently; can push after each; user decides |

## 4. Cascade gates

- Wave 75 → Wave 76 only after Wave 75 commits (or escalates)
- Wave 76 → Wave 77 only after Wave 76 commits (or escalates)
- Wave 77 → Wave 78 only after Wave 77 commits (or escalates)
- Wave 78 → push-prep done; user decides push

## 5. Open questions

1. **Kanzi upstream URL** — needs verification before Wave 77 Phase 1
2. ~~Sample count vs wall-clock budget~~ — **RESOLVED 2026-09-08**: Strategy B
   (N=1000 per arm) chosen; see §5b
3. **Honest mixed-result framing** if framework regresses on some paper metrics
4. **Push cadence** — push after each wave, or batch all 4 then push?

## 5b. Sample count strategy B (N=1000 per arm)

**Decision (2026-09-08):** All Wave 75/76/77 paper reproductions use
**N = 1000 samples per arm** (baseline + framework), NOT paper's full
5K-50K.

**Per-model wall-clock under strategy B:**

| Wave | Model | N per arm | Paper metrics | Wall-clock (estimated) |
|---|---|---|---|---|
| 75 | FlowMol3 | 1000 | validity + pb_validity + fg_dev + ood_ring_rate | ~100-140 min (down from 100-170) |
| 76 | LineageFlow | 1000 | family_validity + foldability + self_consistency + novelty | ~125-160 min |
| 77 | Kanzi | 1000 (TBD by paper) | TBD (FBD / perplexity / motif coverage) | ~130-180 min |
| **Total** | | | | **~6-8 hours wall-clock** (vs 30-50h for full-spec) |

**Why strategy B:**

1. **Total wall-clock budget**: Full-spec (5K-50K samples) for 3 models
   is 30-50 hours single-GPU. Strategy B is 6-8 hours.
2. **Statistical power at N=1000** is sufficient for binomial metrics
   (validity, family_validity, novelty — ±1% CI) and reasonable for
   continuous metrics (foldability pLDDT ±0.5, ESM-IF1 perplexity ±0.05).
3. **Reviewer acceptance**: Honest N=1000 + paper protocol unchanged +
   explicit §7 caveat is a defensible position for a framework paper.
   Mechanism claim is proven by JMAA Theorem 1 + toy evidence
   (Tier 1, Wave 73 — already done). Chemistry is application sanity
   check, not core claim.

## 5c. The 4 reviewer-proof guarantees (locked in across Wave 75-77)

The core defense against reviewer attacks is **external reproducibility**
— every claim in §7 is verifiable by running upstream code + upstream
weights + our framework. All Wave 75-77 plans must capture these 4
guarantees:

| # | Guarantee | What's verified | Where it lives |
|---|---|---|---|
| **G1** | **Model weights are upstream release** | SHA-256 hash of `data/{flowmol3,lineageflow,kanzi}_ckpt/*.pt` matches upstream release | `verification_outputs/ckpt_sha256.json` (new in Wave 75/77) |
| **G2** | **Sampling config is upstream default** | Both baseline and framework call `upstream_repo.FlowMol.sample(nfe=N, ...)` with paper's default args | Wave 75/76/77 audit doc, §"Phase 1 audit" |
| **G3** | **Eval pipeline is upstream code** | Both arms call `upstream_repo.evaluation.evaluate_all.py` (or upstream `SampleAnalyzer.analyze`) — we wrote ZERO new metric code | Wave 75/76/77 plan §"Phase 2 wire eval" |
| **G4** | **vendored upstream snapshot is frozen** | `data/{X}_upstream/` has fixed commit hash (FlowMol3: 77cae22; LineageFlow: vendored commit; Kanzi: TBD after clone) | `data/{X}_upstream/.git/HEAD` or `data/{X}_upstream/COMMIT.txt` |

**Why these 4 guarantees kill reviewer attacks:**

- "Your metric is self-invented" → G3: we call upstream's metric
- "Your baseline config is wrong" → G2: we use upstream's default
- "Your ckpt is fake / different" → G1: SHA-256 verifies against release
- "Your upstream code drifted from paper" → G4: vendored snapshot is frozen

**Paper §7 framing convention (locked)**:

> "We apply the framework to {model} **without retraining** the released
> checkpoint (data/{X}_ckpt/, SHA-256 verified against upstream release).
> Both baseline (frozen ckpt + upstream {model}.sample) and framework
> (frozen ckpt + our 3-round re-inference loop) are evaluated using the
> upstream {eval entrypoint} (vendored at data/{X}_upstream/, commit {hash}),
> with the paper's evaluation protocol unchanged. We run N=1000 samples
> per arm due to GPU budget."

Every sentence in §7.3/§7.4/§7.5 should follow this template. Reviewers
who try to challenge the comparison have to attack upstream itself,
not us.

**Honest framing in §7.3/§7.4/§7.5**: "We ran the paper-metric
reproduction protocol on N=1000 samples per arm, due to GPU budget.
Sample count is 5-10× smaller than paper. Per-metric verdict is
reported with confidence intervals where applicable; full-spec rerun
would tighten CI but is not within this paper's compute budget."

## 6. Decision log

- 2026-09-08: User chose "one at a time to avoid server load" → sequential Wave 76/77/78 after Wave 75
- 2026-09-08: User confirmed "and upstream repos we cloned before" — LineageFlow upstream IS vendored, FlowMol3 upstream IS vendored, Kanzi upstream NOT vendored → Wave 77 needs clone step
- 2026-09-08: User confirmed scope is Kanzi / LineageFlow / FlowMol3 — Tier 1 (already Wave 73 done) + Tier 3 (Wave 75-77) cover all models in scope
- 2026-09-08: User chose sample count strategy B (N=1000 per arm) over full-spec (5K-50K) — bounds total wall-clock at ~6-8h for 3 models vs 30-50h; sufficient statistical power for binomial metrics + reasonable for continuous; honest + defensible framing in §7
