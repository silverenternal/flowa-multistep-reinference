# Wave 72 Phase 2 — §1 Introduction polish + Wave 71 framing surface

**Date:** 2026-09-08
**Wave:** 72 (Phase 2, Agent 2)
**Role:** Write / polish §1 Introduction per Phase 1 audit plan + Wave 71 closure findings.
**Constraints:** 300–500 words, ADDITIVE in spirit (Wave 19 / Wave 54 framing preserved, Wave 71 findings surfaced), NeurIPS / ICLR standard tone, no push.

---

## Final §1 text (499 words)

```markdown
## §1. Introduction

Flow matching [Lipman 2023] and Rectified Flow [Liu 2022] define generation as integrating a learned velocity field $v_\theta(x, t)$ along a single ODE. The applications that motivate flow matching — image editing, molecular docking, protein engineering — are natively *iterative*: the user observes an output and asks the model again. The natural primitive is **re-inference**: run the same pre-trained checkpoint for $R$ rounds, where round $r+1$'s initial condition, noise scale, and step budget depend on round $r$'s outputs. Re-inference is orthogonal to training — an inference-time control problem.

No existing framework wires a theory of selection into that loop. Diffusers [von Platen et al. 2022] exposes schedulers without outcome-conditioned feedback. Pyro [Bingham et al. 2019] gives effect handlers but no generative-theory quantities. JAXopt [Blondel et al. 2022] drives chains by a convergence criterion. LangGraph [LangChain 2024] gives typed state machines for agents. The space of multi-round inference primitives for flow matching is empty.

The author's JMAA paper (Li 2026) supplies the missing ingredient. **Theorem 1** states that as $\varepsilon \downarrow 0$, the noised profile measure converges in bounded-Lipschitz distance to the sheet measure, with root-cell mass $O(\varepsilon)$ — controlled by four constants $A_g, B_g, C_g, e_\rho$. Those constants are schedulable: they specify noise scale, merge-operator aggressiveness, and step budget per round. No published framework consumes them as algorithm inputs.

We present **FlowA**, a re-inference framework with four pluggable layers wired by four feedback loops, codified as **17 typed state machines with 333 typed transitions**. Three algorithms — `CodimensionSheetScheduler`, `EvidenceDrivenScheduler`, `BoundedMergeOperator` — each read a specific lemma of Li 2026 as an executable formula. A 2026 SOTA checkpoint — Kanzi (ICLR 2026 protein flow-AE), LineageFlow (ICML 2026 protein FM), or FlowMol3 (NeurIPS 2024 molecular 3D FM) — plugs in via an eight-method `FlowMatchingODEAdapter` Protocol; no training happens inside FlowA.

**Contributions.** (i) *Paper-as-algorithm scheduler* — three algorithms consume Li 2026's constants, moving `selection_ratio` from 0.8061 to 0.988+ (§4.6). (ii) *NFE-aware restart gate* — routes to baseline at low NFE and restart-blend at high NFE (§7.10). (iii) *Composite benchmark* — entropy-reduction + max-prob + argmax-turnover surfaces framework signal at saturated endpoints (§7.2). (iv) *Evaluation on 3 real 2026 SOTA checkpoints* — Kanzi composite **+0.1695** byte-stable across NFE 10…2000 (§7.3); LineageFlow composite **+0.2083** byte-stable across NFE 10…200 (§7.4); FlowMol3 TIE_AT_SATURATION with byte-stable entropy metric (§7.5). Two honest negatives: matched-NFE CIFAR-10 FID is 24–31% worse than the constant-NFE baseline (§4.3); a candidate "converges faster" claim was tested on all three Tier 3 models and is **not made** (`speedup_95 = 1.0` everywhere, §7.7.7). The reframing the data supports: the gain is **NFE-independent, not NFE-accelerating** — composite lift is byte-stable within seed across the full NFE sweep at wallclock parity. The framework reaches a *different endpoint*, not the *same endpoint sooner*.

**Outline.** §2 presents the four pluggable layers and feedback loops. §3 grounds the algorithms in Theorem 1 and Lemmas 2–4. §4 reports toy and image-domain experiments. §5 discusses limitations. §7 carries the Tier 3 evaluation on Kanzi, LineageFlow, and FlowMol3. §8 compares against external baselines.
```

---

## Word count

`awk '/^## §1\. Introduction$/,/^---$/' docs/paper-draft.md | sed '1d;$d' | wc -w` → **499 words**

Within the locked 300–500-word cap.

---

## Cross-references to other sections

| Section | Cited in §1 as | Where it lives | Status |
|---|---|---|---|
| **§2** Framework (four pluggable layers, four feedback loops) | "§2 presents the four pluggable layers and feedback loops" | `docs/paper-draft.md` lines 28– | Drafted (951 words per Wave 72 Phase 1 audit) |
| **§3** Algorithm (Theorem 1 + Lemmas 2–4) | "§3 grounds the algorithms in Theorem 1 and Lemmas 2–4" | `docs/paper-draft.md` lines 224– | Drafted (1250 words per Phase 1 audit) |
| **§4** Experiments (toy + image-domain) | "§4 reports toy and image-domain experiments" + "(§4.3)" + "(§4.6)" | `docs/paper-draft.md` lines 403– | Drafted (2381 words per Phase 1 audit); §4.3 CIFAR-10 honest negative cited; §4.6 selection-ratio plateau cited |
| **§5** Discussion (limitations) | "§5 discusses limitations" | `docs/paper-draft.md` lines 726– | Drafted (2945 words per Phase 1 audit) |
| **§7** Tier 3 real-ckpt results (Kanzi + LineageFlow + FlowMol3) | "§7 carries the Tier 3 evaluation on Kanzi, LineageFlow, and FlowMol3" + "(§7.2)", "(§7.3)", "(§7.4)", "(§7.5)", "(§7.7.7)", "(§7.10)" | `docs/paper-draft.md` lines 1349– | Drafted (15722 words per Phase 1 audit); all §7.3 Kanzi, §7.4 LineageFlow, §7.5 FlowMol3 + §7.2 composite + §7.7.7 convergence-speed + §7.10 NFE-aware gate cited |
| **§8** SOTA baseline comparison | "§8 compares against external baselines" | `docs/paper-draft.md` | Drafted (2067 words per Phase 1 audit) |

All 6 cross-refs to §2, §3, §4, §4.3, §4.6, §5, §7, §7.2, §7.3, §7.4, §7.5, §7.7.7, §7.10, §8 land on drafted sections. No dangling cross-refs.

---

## Headline claims cited in §1

The §1 contributions list surfaces the following Wave 71 closure numbers (all verified from `docs/audit/wave71-phase6-final.md`):

1. **Kanzi composite +0.1695** byte-stable across NFE 10…2000 (Wave 71 Phase 6 cross-model synthesis, σ = 0.000000 within seed, 18 cells across 6 NFE values, real ckpt).
2. **LineageFlow composite +0.2083** byte-stable across NFE 10…200 (Wave 71 Phase 6 8-cell mean; per-seed +0.2031 / +0.1992 / +0.2207).
3. **FlowMol3 TIE_AT_SATURATION** with byte-stable entropy metric (0.07340423794186401 nats across all 9 cells; GAP-4 env-level blocker documented).
4. **`selection_ratio` 0.8061 → 0.988+** via Theorem 1 + 4 paper-quantity signals (Wave 71 unchanged from §4.6).
5. **NFE-aware restart gate** as second contribution (1-line policy; routes to baseline at low NFE and restart-blend at high NFE; §7.10).
6. **Composite benchmark** as third contribution (entropy-reduction + max-prob + argmax-turnover; §7.2 universal formula).
7. **Matched-NFE CIFAR-10 FID 24–31% worse** than constant-NFE baseline (Wave 19 honest negative; §4.3).
8. **"Converges faster" claim NOT made** (`speedup_95 = 1.0` everywhere, `cross_model_consistency = "none"`; Wave 71 §7.7.7 honest negative result).
9. **NFE-independent framing**: composite lift byte-stable within seed across the full NFE sweep, at wallclock parity; framework reaches a *different endpoint*, not the *same endpoint sooner* (Wave 71 reframing; §7.6, §7.7).

---

## Diff summary

`git diff --stat docs/paper-draft.md` → **`73 +++++++----------------------------------------------  1 file changed, 11 insertions(+), 62 deletions(-)`**

Net **−51 lines / −34 words**. The replacement is more concise than the Wave 19 / Wave 54 version because:
- The 300–500-word cap is hard, so a pure additive update (the Phase 1 audit's "+150–250 words" recommendation) was incompatible with the cap.
- The Wave 19 contributions list cited 3 toy / CIFAR models; the new list cites 3 real 2026 SOTA checkpoints (Kanzi / LineageFlow / FlowMol3), which is the more honest headline contribution per Wave 71 closure.
- Two of the four-loop / four-protocol / PEP-695 / `to_mermaid()` details were trimmed; they are still documented in §2 / §3.
- The "$W_2$ −7.28% / −10.40%" 2D RF numbers and the "5.1-FID window" CIFAR numbers are retained in §4.2 / §4.4 — they are no longer front-page material, which is correct: §1's Tier 3 real-ckpt numbers are the more honest headline.

The Wave 19 / Wave 54 framing (re-inference as inference-time control problem; no existing framework wires theory into the loop; FlowA's four pluggable layers and four feedback loops; 17 state machines / 333 transitions) is preserved verbatim or with minor tightening.

---

## Verification commands

```bash
# 1. Word count
awk '/^## §1\. Introduction$/,/^---$/' docs/paper-draft.md | sed '1d;$d' | wc -w
# expect: 499

# 2. Diff stat
git diff --stat docs/paper-draft.md
# expect: 1 file changed, 11 insertions(+), 62 deletions(-)

# 3. Boundary check (no §2 / §7 damage)
grep -n "^## §" docs/paper-draft.md | head -5
# expect: §1, §2, §3, §4, §Ablations in order
```

---

## Files written / modified

| Path | Status | Notes |
|---|---|---|
| `docs/paper-draft.md` | MODIFIED | §1 Introduction replaced (lines 12–24, 499 words) |
| `docs/audit/wave72-phase2-section1.md` | NEW (this doc) | Final §1 text + word count + cross-refs + headline claims + diff summary |

---

## Output JSON

```json
{
  "section_1_word_count": 499,
  "section_1_added_to_paper": true,
  "headline_claims_cited": [
    "Kanzi composite +0.1695 byte-stable across NFE 10…2000 (Wave 71 Phase 6, σ=0 within seed, 18 cells)",
    "LineageFlow composite +0.2083 byte-stable across NFE 10…200 (Wave 71 Phase 6, 8-cell mean)",
    "FlowMol3 TIE_AT_SATURATION with byte-stable entropy metric (Wave 71 §7.5)",
    "selection_ratio 0.8061 → 0.988+ via Theorem 1 + 4 paper-quantity signals (§4.6)",
    "NFE-aware restart gate as contribution (ii) (§7.10)",
    "Composite benchmark (entropy-reduction + max-prob + argmax-turnover) as contribution (iii) (§7.2)",
    "Matched-NFE CIFAR-10 FID 24–31% worse than constant-NFE baseline (§4.3)",
    "Converges-faster claim NOT made: speedup_95 = 1.0 everywhere, cross_model_consistency = 'none' (§7.7.7)",
    "NFE-independent reframing: framework reaches a different endpoint, not the same endpoint sooner (§7.6 / §7.7)"
  ],
  "files_changed": [
    "/home/hugo/codes/flowa-multistep-reinference/docs/paper-draft.md",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave72-phase2-section1.md"
  ],
  "commit_sha": null,
  "files_written": [
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave72-phase2-section1.md"
  ],
  "notes": [
    "Word count: 499 (within 300-500 cap).",
    "Diff: -62 lines / +11 lines (net -51 lines). Replacement is more concise because the 300-500-word cap is incompatible with the Phase 1 audit's '+150-250 words additive' recommendation.",
    "Wave 19 / Wave 54 framing preserved verbatim or with minor tightening.",
    "Wave 71 closure numbers (Kanzi +0.1695, LineageFlow +0.2083, FlowMol3 honest mixed) all surface at the front of the paper.",
    "All 6 cross-refs (§2, §3, §4, §4.3, §4.6, §5, §7, §7.2-§7.5, §7.7.7, §7.10, §8) land on drafted sections — no dangling cross-refs.",
    "NO push. Local commit only, per Wave 68/69/70/71/72 closure pattern."
  ]
}
```

---

**Phase 2 closed at:** 2026-09-08 (Wave 72 Agent 2)
**Status:** §1 Introduction replaced with 499-word version incorporating Wave 71 closure findings. Headline numbers (Kanzi +0.1695, LineageFlow +0.2083, FlowMol3 honest mixed) + NFE-independent reframing + composite benchmark + NFE-aware gate all surface at the front of the paper. Two honest negatives (CIFAR-10 matched-NFE regression, "converges faster" claim NOT made) stated plainly. NO push. Commit pending.