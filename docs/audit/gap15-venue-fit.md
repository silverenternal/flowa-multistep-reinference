# GAP-15-VENUE — venue-fit memo (general-ML target)

**Date:** 2026-10-14
**Author:** GAP-15 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` GAP-15-VENUE — decide the **general-ML** venue target
(user directive 2026-10-14: go general ML; do **not** pigeonhole into an
image/CV or bio/medical venue) and scope the required framing + format change.
**Decision owner:** the user. This memo is decision support only.
**Frozen surfaces:** untouched.

---

## 0. TL;DR

FlowA is a **cross-domain, training-free inference-time framework** for frozen
flow-matching checkpoints, validated on **protein + molecule + toy + image**
cells. The cross-domain breadth and the genuine per-domain improvements are the
asset. Under the user's "general ML" constraint the candidate set narrows to
**IEEE TNNLS** (current target), **IEEE TPAMI**, **JMLR**, **Artificial
Intelligence**, **IEEE TCYB**, **Information Sciences**.

**Agent recommendation: stay on IEEE TNNLS.** It is already the formatted
target (IEEEtran, 11 pp), it is CAS Tier-1 TOP, and — per the recorded Wave 238
P3 analysis — it is the venue whose scope actually matches a cross-domain
solver-agnostic framework paper. **TPAMI is deprioritized**: its primary scope
is image/video/multimedia, so it would weight the two image cells heavily and
find the protein+molecule axis disjoint (Wave 238 P3 §1.3). JMLR / Artificial
Intelligence are higher-prestige but higher-risk general-ML alternatives that
require a theory-forward reframe and a format change.

---

## 1. What the paper is (fit inputs)

| Axis | FlowA |
|---|---|
| Contribution type | Training-free inference-time **framework** (typed four-port control plane, 13 schedulers) + conditional convergence theory + reproducibility infrastructure |
| Domains | protein (LineageFlow, Kanzi), molecule (FlowMol3), toy (2D), image (CIFAR-10 RF, MNIST FM) |
| Strongest cells | R6 scPerp (cluster-robust d_z = −4.019), R6 hard-tier pLDDT (+1.189 counterfactual / +1.121 live), R2 Kanzi RMSD (small), R5c smoke |
| Weakest cells | R5b (tuned-baseline 0/4), R5c (production ckpt regresses), R1 (init-attributed), R3 (n.s.) |
| Head-to-head | R6 only (vanilla + Fast-DLLM + AB-Cache + LeDiFlow) |
| Infrastructure | D.4 byte-stable 30/30, SHA-256 ledger, per-cell recipes — above venue norm |

---

## 2. Candidate matrix (general ML, CAS Tier-1)

| Venue | CAS 2025 | Scope | Fit for THIS paper | Format / cost |
|---|---|---|---|---|
| **IEEE TNNLS** (current) | 一区 TOP (IF 10.2; accept ≈17 %) | neural networks + learning systems, broad | **Best** — cross-domain framework + learning-system scheduler + BL-distance theory | IEEEtran, already done |
| **IEEE TPAMI** | 一区 TOP (CCF-A; IF ≈20.8) | image / video / multimedia primary | **Weak** — would weight the 2 image cells; protein+molecule axis disjoint (Wave 238 P3) | IEEEtran, reframe |
| **JMLR** | 一区 TOP | general ML, theory-forward | Medium — needs a stronger theory spine; the framework/engineering angle is under-weighted | LaTeX, no page cap, open access |
| **Artificial Intelligence** (Elsevier) | 一区 TOP | general AI | Medium — values conceptual novelty; the empirical axis must carry it | elsarticle |
| **IEEE TCYB** | 一区 | cybernetics / learning / optimization | Medium — broad, but less generative-sampling-centric | IEEEtran |
| **Information Sciences** | 一区 | broad ML / information | Medium — broad and volume-heavy, lower prestige than TNNLS | Elsevier |

Dropped as leads (per user directive): **Pattern Recognition** (pattern/CV-centric),
**AI4Science venues** (bio-specific) — both narrow the work to one domain.

---

## 3. Recommendation and required changes

### 3.1 Recommended: keep IEEE TNNLS
- **Required changes:** none structural. The manuscript is already IEEEtran 11 pp
  and TNNLS-formatted.
- **Framing:** lead with cross-domain generality (protein + molecule + toy +
  image) rather than any single domain. The four empirical gaps (GAP-32/34/35/37)
  raise the empirical axis regardless of venue.

### 3.2 Alternative: JMLR / Artificial Intelligence (higher ceiling, higher risk)
- **Required changes:** theory-forward reframe (elevate §6 conditional
  contraction + the restart-blend squared-error identity to the lead), a
  format change (LaTeX / elsarticle), and acceptance that the
  framework-engineering contribution (24 innovations, ledger, byte-determinism)
  is under-weighted by these venues.
- **Risk:** the empirical axis (4 STRONG of which R2 is tiny-effect, R5b
  conditional, R5c smoke, R6 partly counterfactual) is thinner than a
  theory-forward venue expects.

### 3.3 Not recommended: IEEE TPAMI
- Per the recorded Wave 238 P3 decision, TPAMI's image/video scope mismatches
  the protein+molecule-heavy content; 2 of 6 R-cells are image and 0 are video.

---

## 4. Decision requested from the user

1. **Confirm the target** (agent recommends **IEEE TNNLS**; alternatives JMLR /
   Artificial Intelligence).
2. If a change is chosen, **authorize touching the frozen manuscript** for the
   reframe + reformat (GAP-29 scope).

No frozen surface was changed by this memo. The venue-driven empirical work
(GAP-32/34/35/37) is venue-independent and proceeds regardless.

---

## 5. Files

- this memo
- `docs/audit/engineering/p3-journal-decision.md` (historical Wave 238 P3
  TPAMI→TNNLS decision)
- `docs/audit/gap19-q1-odds-alignment.md` (self-assessed acceptance probability
  removed from submission docs)
- `docs/audit/todo-history.md` §7 (2026-10-14 venue-fit addendum)
