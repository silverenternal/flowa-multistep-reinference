# Wave 78 — Cross-tier paper-metric synthesis + push-ready

**Date:** 2026-09-08
**Status:** PLANNED (waits for Wave 77)
**Depends on:** Wave 75 + Wave 76 + Wave 77 commits landed

> **Wave 79 framing update (2026-09-08)** — Wave 78 paper writeup
> MUST be re-framed under the **framework SOTA at inference time on
> frozen ckpt** paradigm (NOT "model SOTA" or "framework vs SOTA model"
> comparison). See §9 below. The Wave 73-74 composite-metric numbers
> ("Kanzi composite +0.1695", "LineageFlow composite +0.2083") used an
> internal composite and a broken-baseline comparison path; Wave 79
> upstream eval is the authoritative replacement and must be cited
> wherever Wave 73-74 internal-composite claims appear in §7.

## 1. Goal

Synthesize paper-metric results across all 3 Tier 3 models (Wave 75/76/77) + Tier 1 (Wave 73 already done). Update paper §1 abstract + §7.3 + §7.4 + §7.5 + §7.7.8 + §8 with paper-reproduced numbers. Final push-ready synthesis.

## 2. Inputs

- Wave 75: FlowMol3 paper-metric reproduction (`verification_outputs/flowmol3_paper_repro_q4_2026.json` + `flowmol3_paper_framework_q4_2026.json`)
- Wave 76: LineageFlow paper-metric reproduction (`verification_outputs/lineageflow_paper_repro_q4_2026.json` + `lineageflow_paper_framework_q4_2026.json`)
- Wave 77: Kanzi paper-metric reproduction (`verification_outputs/kanzi_paper_repro_q4_2026.json` + `kanzi_paper_framework_q4_2026.json`)
- Wave 73: Tier 1 paper-metric (2D Two Moons W2, CIFAR-10 RF FID) — already done
- Wave 72: §1 abstract with central framing ("同 NFE 下更好；同质量下 NFE 更少") — needs paper-metric update

## 3. Phase structure (5 phases)

### Phase 1 — Aggregate all paper-metric results
- READ-ONLY audit
- Read all Wave 75/76/77 audit docs
- Build per-model comparison table:
  - Tier 3 Kanzi: baseline vs framework on each paper metric
  - Tier 3 LineageFlow: same
  - Tier 3 FlowMol3: same
  - Tier 1 2D FM / CIFAR-10 RF: from Wave 73
- Per-metric verdict: framework_improves / framework_ties / framework_regresses
- Cross-tier structural pattern: which metrics are framework-improves-amenable, which are saturated
- Document in `docs/audit/wave78-phase1-aggregate.md`
- **No commit**

### Phase 2 — Update paper §1 abstract + §7.3/§7.4/§7.5/§7.7.8
- §1 abstract ADDITIVE: Wave 75/76/77 paper-metric numbers + per-metric verdict
- §7.3 (Kanzi) ADDITIVE Wave 77 paragraph
- §7.4 (LineageFlow) ADDITIVE Wave 76 paragraph
- §7.5 (FlowMol3) ADDITIVE Wave 75 paragraph (replaces Wave 74 internal-entropy paragraph if paper-metric is stronger)
- §7.7.8 (Tier 1 speedup) PRESERVE Wave 73 + add note that Tier 1 metrics ARE paper metrics (W2, FID)
- Honest reframing of central claim based on actual paper-metric results
- **No commit** (paper edit only, commit at end)

### Phase 3 — Update §5 Discussion + §8 SOTA baseline
- §5.1 "what is proven algorithmically" — add paper-metric framework improvement evidence
- §5.7 Limitations — add "internal composite metric is framework's, not paper's; paper-metric reproduction done in §7"
- §8.5 SOTA baseline measurement status — update with Wave 75/76/77 paper-metric reproductions
- **No commit**

### Phase 4 — Final synthesis doc + push-ready update
- Author `docs/audit/wave78-phase4-final.md`:
  - All-3-models paper-metric status table
  - Cross-tier structural pattern
  - Per-metric verdict summary
  - D.4 + G-MASTER + mkdocs status
  - Honest remaining caveats
  - Open questions for next wave
- Update `docs/push-ready-summary.md` with Wave 75/76/77/78 findings
- D.4 + G-MASTER + mkdocs verify (final gates)
- **Commit (NO push)**

### Phase 5 — Final commit + author notes
- Single commit covering paper + push-ready-summary updates
- NO push (user decides)
- Author `todo/push-ready-summary-2026-09-08.md` if needed
- Final task list cleanup (mark Wave 75-78 tasks completed)

## 4. Constraints

- **Paper edits ADDITIVE only** — don't rewrite existing Wave 73/74/75 content
- **Honest caveats everywhere** — if paper metric didn't reproduce, say so
- **D.4 + G-MASTER + mkdocs** all PASS at every commit boundary
- **NO push**

## 5. Honest caveats (Tier 3 paper metric reproduction may diverge)

- Sample count limitation: paper uses 5K-50K; we may use 1K-5K (GPU budget)
- Reference distribution: paper uses GEOM_DRUGS / Pfam-A / chembl — must vendor or download
- Some paper metrics may not be reproducible on our ckpt (different training data subset)
- If framework REGRESSES on some paper metrics: honest negative in paper

## 6. Time estimate

- Phase 1: ~10 min (aggregate)
- Phase 2: ~15 min (paper §7 + §1 update)
- Phase 3: ~10 min (§5 + §8 update)
- Phase 4: ~10 min (synthesis + push-ready)
- Phase 5: ~5 min (commit)
- **Total: ~50 min wall-clock** (paper-writeup only; no new eval runs)

## 7. Success criteria

- [ ] All 3 Tier 3 models have paper-metric reproduction documented
- [ ] §1 abstract + §7.3 + §7.4 + §7.5 + §7.7.8 + §5 + §8 all updated
- [ ] Per-metric verdict (framework_improves / framework_ties / framework_regresses) documented per model
- [ ] Central framing in §1 ("同 NFE 下更好；同质量下 NFE 更少") backed by paper metrics, not just internal composite
- [ ] D.4 72/72 byte-stable
- [ ] G-MASTER 7/7 PASS
- [ ] mkdocs build --strict EXIT=0
- [ ] NO push
- [ ] Push-ready summary updated with all 4 waves (75/76/77/78) + ready for user push decision

## 8. Push-readiness checklist (post-Wave 78)

- [ ] All §7 Tier 3 sections cite paper metrics (not internal composite) where paper metrics exist
- [ ] All honesty caveats preserved (Wave 71 NFE-independent reframing, Wave 73 multi-tier story, Wave 74 honest ground, Wave 75-77 paper-metric reproductions)
- [ ] No overclaims left in paper (re-check §1 abstract carefully)
- [ ] D.4 + G-MASTER + mkdocs all green
- [ ] ~290+ unpushed commits accumulated (Wave 9-78), all locally verified
- [ ] User reviews push-ready summary + commits → decides to push or pause

## 9. Wave 79 caveat (MANDATORY for paper §7)

### 9.1 What Wave 73-74 claimed, and why we now caveat

Wave 73-74 measured framework vs baseline on an **internal composite metric**
(entropy_reduction + max_prob_delta + argmax_turnover) and reported per-model
numbers such as:

| Model | Wave 73-74 claim | What it actually was |
|---|---|---|
| Kanzi | "composite +0.1695, framework_improves" | Internal composite on a frozen ckpt |
| LineageFlow | "composite +0.2083, framework_improves" | Internal composite on a frozen ckpt |
| FlowMol3 | "composite TIE (0.0)" | Internal composite, baseline entropy observer broken at n_molecules > 1 |

**Two measurement-config issues that Wave 79 corrected:**

1. **Internal composite is framework's diagnostic, not the paper's metric**
   The chemistry papers (FlowMol3 / LineageFlow / Kanzi) report validity /
   pb_validity / fg_deviation / family_validity / foldability / FBD / etc.
   These are what reviewers care about. The internal composite was useful
   for engineering iteration but does NOT support a "framework SOTA on
   chemistry" claim by itself.

2. **Baseline entropy observer returns 0 at n_molecules > 1 (Wave 68 root cause)**
   For batched sample sizes, the Wave 68 entropy observer reading was
   wrong, so Wave 73-74 baseline entropy was 0.0 — making any positive
   framework composite a comparison against a broken-baseline, not a
   real improvement.

Wave 79 fixes both: baseline and framework now run on the **same upstream
eval pipeline** (vendored per-model) with symmetric measurement config,
so the framework-vs-baseline delta is meaningful.

### 9.2 Where in the paper this caveat must appear

| Section | Required edit |
|---|---|
| §1 abstract | Replace any "framework SOTA on chemistry" language with "framework improves quality / reduces NFE across 4 generation domains, with paper-metric reproduction on Tier 3 in §7.3-§7.5 and Wave 79 caveat for Wave 73-74 internal-composite numbers" |
| §7.3 (Kanzi) | Cite Wave 79 Kanzi upstream-eval numbers (FBD / motif coverage / etc.) instead of Wave 73-74 composite +0.1695. If Wave 79 not yet landed, write "Wave 73-74 numbers are internal composite; Wave 79 upstream-eval reproduction in progress" |
| §7.4 (LineageFlow) | Same — Wave 79 upstream-eval numbers (HMMER / OmegaFold / ESM-IF1 / MMseqs2) instead of Wave 73-74 composite +0.2083 |
| §7.5 (FlowMol3) | Same — Wave 79 upstream-eval numbers (RDKit validity / PoseBusters / fg_dev / OOD ring) instead of Wave 74 internal composite TIE |
| §7.6 honest verdict | Add paragraph: "Wave 73-74 internal-composite claims superseded by Wave 79 upstream-eval reproduction. Wave 79 uses symmetric measurement config (baseline + framework both call upstream eval as subprocess), so the framework-vs-baseline delta is on paper metrics, not internal diagnostic." |
| §5.7 Limitations | Add: "Internal composite metric (Wave 47-74) is a framework diagnostic, not a paper metric. Paper-metric reproduction is in §7.3-§7.5." |

### 9.3 The single claim we CAN defend after Wave 79

- **Mechanism claim (Tier 1 toy, Wave 73):** "At matched NFE, framework
  improves quality; at matched quality, framework uses fewer NFE."
  Evidence: 2D Two Moons W2 -7.28%, CIFAR-10 RF FID -44.17%,
  2D FM 10× NFE speedup, CIFAR-10 RF 2.5× NFE speedup. **These are
  paper-aligned metrics on standard benchmarks; this claim stands.**

- **Mechanism claim (Tier 3 chemistry, Wave 79):** "Given a frozen
  flow-matching ckpt, applying our framework does not regress
  paper-metric performance." Evidence: Wave 79 upstream-eval runs
  (1000-2000 samples per arm, per paper metric, baseline + framework
  symmetric). **If framework ties on paper metrics, that itself is
  a valid application evidence.**

- **Cross-domain generalization (Tier 1 + Tier 3, Wave 73 + Wave 79):**
  "Framework improves quality (Tier 1) and doesn't regress paper
  metrics (Tier 3) across 4 generation domains (2D toy, 2D image,
  3D molecule, 1D protein, 3D motif) and 7+ model architectures."
  **This is a claim reviewers can evaluate, even if Wave 79 shows
  framework ties rather than improves.**

### 9.4 What we MUST NOT claim (post-Wave 79)

- ❌ "Framework beats SOTA chemistry model on its own paper metric."
  Even if Wave 79 shows framework_improves on some chemistry metric,
  the comparison is **frozen-ckpt + framework vs frozen-ckpt + vanilla
  sampler**, not framework vs SOTA model. We are not re-training.

- ❌ "Internal composite +X.YYYY on chemistry means framework is SOTA."
  Wave 79 supersedes this. Internal composite is engineering diagnostic.

- ❌ "Wave 73-74 numbers are valid without Wave 79 caveat."
  They are valid only as Wave 47-74 engineering telemetry, NOT as
  paper-metric evidence.

### 9.5 Wave 78 writeup ordering (revised)

1. **Wave 78 Phase 1**: Aggregate Wave 75/76/77 paper-metric results
   (NOT Wave 73-74 internal composite)
2. **Wave 78 Phase 2**: Update §7.3/§7.4/§7.5 with Wave 75-77 paper
   metrics + Wave 79 caveat for Wave 73-74 internal-composite
   citations that still appear in §7
3. **Wave 78 Phase 3**: Update §1 abstract with single-paper framing
   ("framework SOTA at inference time on frozen ckpt", "cross-domain
   evidence on toy + chemistry with paper metrics")
4. **Wave 78 Phase 4**: Final synthesis + push-ready summary

If Wave 79 has not committed by the time Wave 78 starts, write
"Wave 79 in progress, expected end-of-Wave-78" in §7.6 — don't
fabricate Wave 79 numbers.

## 9.6 Sample count strategy B (N=1000 per arm, applied to Wave 75-77)

All three Tier 3 paper reproductions use **N = 1000 samples per arm**
(baseline + framework) instead of paper's full 5K-50K. This is a
deliberate cost/benefit choice:

| Concern | Strategy B (1K) | Full-spec (5K-50K) |
|---|---|---|
| Wall-clock | ~5-10h for 3 models | 30-50h |
| Validity CI | ±1% | ±0.4% |
| Distribution metric variance | 2.2× higher | baseline |
| Reviewer acceptance | honest + reproducible | harder to verify |

**Paper framing in §7.3/§7.4/§7.5**: "We ran the paper-metric
reproduction protocol on N=1000 samples per arm, due to GPU budget.
Sample count is 5-10× smaller than paper. Per-metric verdict is
reported with confidence intervals where applicable; full-spec rerun
would tighten CI but is not within this paper's compute budget."

**If reviewer asks for full-spec**: Point to §7 "Limitations" where
this is explicitly documented. **Do NOT rerun full-spec in revision**
unless reviewer specifically requires it — the cost/benefit doesn't
favor it for a framework paper (mechanism is proven by JMAA Theorem 1
+ toy evidence; chemistry is application sanity, not core claim).
