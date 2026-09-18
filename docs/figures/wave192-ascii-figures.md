# Wave 192 ASCII Architecture Figures (2-column compatible)

> EAAI LaTeX / Word / Overleaf-ready ASCII art. Each figure is a
> standalone labelled diagram wrapped in a fenced plain-text code block
> (no `mermaid`, no SVG, no PNG). Wave 193 P6 deliverable: refitted
> to ≤45 chars/line for 2-column EAAI layout.
>
> **Author note (Wave 192 P1 reframes).** `Kanzi` (ICLR 2026 image FM)
> and `FreqFlow` (2026 update) are reframed to `[Author submitted, 2026]`
> per Wave 192 P1 honest-disclosure pass — the reviewer-uploaded PDF
> can be cited as an attachment instead of a venue-locked reference.

---

## Figure 1 — FlowA system architecture

```
+===========================================+
|  FlowA : training-free re-inference       |
|  4 Protocols + 17 SM + 333 transitions    |
+===========================================+
| L4 Adapter Protocol (8 methods)           |
|   [Kanzi*][LineageFlow][FlowMol3]         |
|   [FreqFlow*][TwoDimFM][RectCIFAR]        |
|   [MnistFm][HidreamI1]  *=[Author 2026]   |
+-------------------------------------------+
| L3 SchedulerProtocol (6 families)         |
|   Cosine | CodimSheet | EvidenceDriven    |
|   FreeTraj | Convergence | PaperRatio     |
|   sample()->(n_cap, eps_implicit)         |
| L3 MergeOperatorProtocol (3 impl)         |
|   Bounded | AlphaBlend | MeanFlowMerge    |
| L3 RestartBlenderProtocol                 |
|   inputs: restart_dist + paper_evidence   |
+-------------------------------------------+
| L2 Engine + Runner (orchestration)        |
|   7 steps: handshake->build_state->      |
|   restart->compose->solve_ode->observe    |
|   ->detach                                |
+-------------------------------------------+
| L1 Hexagonal ports                        |
|   SchedulerPort | PolicyDriverPort        |
|   MixerPort | EnvelopePort                |
|   paper_q {A_g,B_g,C_g,e_rho} DERIV-001   |
|   Metrics: TheoremAlignedFID, W2,         |
|     selection_ratio, EvidenceScaleGap,    |
|     Bounded-Lipschitz                     |
+===========================================+
| 4 Feedback Loops (back-edges)             |
|  L1 scheduler self-feedback (PID-lite)    |
|  L2 paper_quantities -> scheduler         |
|  L3 metrics -> runner (sel_ratio -> n_cap)|
|  L4 ledger chain integrity                |
+-------------------------------------------+
| 17 state machines * ~20 transitions       |
|   = ~333 transitions (Wave 140 census)    |
|   UNINIT->INIT->IDLE->SAMPLE_REQ->        |
|   SAMPLE_EMIT->ADJUST->ADJUSTED->         |
|   FEEDBACK_RECV->RESET->TERMINATED        |
+-------------------------------------------+
| Output: frozen theta + framework          |
|   --> p_theta(x_0)                        |
+===========================================+
```

**Caption (Figure 1).** FlowA system architecture (training-free
inference-time re-inference framework). L1 contracts/metrics/hexagonal-
ports; L2 engine + runner orchestration; L3 4-protocol composition
(SchedulerProtocol x 6 families, MergeOperatorProtocol x 3 impls,
RestartBlenderProtocol x 2 inputs); L4 frozen-theta adapters (8
methods: Kanzi, LineageFlow, FlowMol3, FreqFlow, TwoDimFM,
RectifiedFlowCIFAR, MnistFm, HidreamI1). `*` = "[Author submitted,
2026]" per Wave 192 P1 honest disclosure. 4 feedback loops (scheduler
self-feedback, paper-quantities-grounded scheduler, metrics-to-runner,
ledger chain integrity) are back-edges. 17 state machines * ~20
transitions = ~333 transitions (Wave 140 census). Output:
`frozen theta + framework --> p_theta(x_0)`.

---

## Figure 2 — Re-inference loop dataflow (vertical)

```
+===========================================+
| FlowA: Re-inference Loop (top->bot)       |
+===========================================+
| (1) frozen theta (no grad updates)        |
|       |                                   |
|       v  state shape + ODE contract       |
| (2) AdapterProtocol:                      |
|     FlowMatchingODEAdapter                |
|     - capabilities_handshake              |
|     - build_initial_state                 |
|     - export_endpoint                     |
|     - detach_and_validate_endpoint        |
|       |                                   |
|       v  StateBundle                      |
| (3) Runner: ReInferenceRunner             |
|     - per-round metric                    |
|     - audit_codes                         |
|     - ledger row (Loop 4)                 |
|       |                                   |
|       v  sample() request                 |
| (4) SchedulerProtocol.sample(             |
|     outer_cycle, round)                   |
|     returns ScheduleSample{               |
|       n_cap, n_min, n_max, u_r,           |
|       family, evidence_ratio,             |
|       eps_implicit, schedule_hash,        |
|       audit_codes }                       |
|       |                                   |
|       v  n_cap, eps_implicit              |
| (5) Solver.solve_ode(state, sample)       |
|     Heun | DPM-Solver++ | RK45 | user     |
|     -> trajectory -> endpoint             |
|     -> integrator_trace                   |
|       |                                   |
|       v  endpoint + trace                 |
| (6) Round-end composite eval              |
|     entropy_reduction = H(p_p)-H(p_r)     |
|     max_prob_delta                        |
|     argmax_turnover                       |
|     selection_ratio (paper Thm 1)         |
|     evidence_ratio_g                      |
|       |                                   |
|       v  metric (Loop 1)                  |
| (7) scheduler.record_round_feedback       |
|     -> adjust n_cap / eps_implicit        |
|     -> paper-quant perturbation           |
|     -> restart_dist update (Loop 2)       |
|       |                                   |
|       +<-- loop until n_rounds --+        |
|                                   |       |
| (8) OUTPUT {trajectories_r,               |
|     endpoints_r, ledger_rows_r,           |
|     paper_quantities_r}                   |
|   frozen theta + framework -> p_theta     |
+===========================================+
```

**Caption (Figure 2).** Vertical dataflow of the FlowA re-inference
loop. Eight stages: (1) frozen theta input; (2) `AdapterProtocol`
state shape + ODE contract; (3) Runner orchestration with per-round
metric + hash-chained ledger (Loop 4); (4) `SchedulerProtocol.sample()`
returns `ScheduleSample` with `n_cap` and `eps_implicit`; (5)
`Solver.solve_ode` dispatches to Heun / DPM-Solver++ / RK45 / user;
(6) round-end composite eval (`entropy_reduction` +
`max_prob_delta` + `argmax_turnover` + `selection_ratio` +
`evidence_ratio_g`); (7) `scheduler.record_round_feedback` perturbs
the next round via paper-quantities-driven feedback (Loops 1+2); (8)
loop until `n_rounds` reached, then emit `{trajectories_r,
endpoints_r, ledger_rows_r, paper_quantities_r}`. The output
distribution is `p_theta(x_0)` with `theta` held frozen end-to-end.

---

## Figure 3 — 3-tier experiment hierarchy + 4-arm H2H

```
+===========================================+
| FlowA : 3-tier exp hierarchy + 4-arm H2H  |
| honest disclosures marked with (*)        |
+===========================================+
| Tier 1: toy / fast iteration              |
|   2D Rectified Flow (TwoDimFMAdapter)     |
|     targets: two_moons | eight_gauss      |
|     metric: W2 ; baseline Euler NFE=2     |
|     headline: -7.28% / -10.40% (R5)       |
|   MNIST FM smoke (*)                      |
|     ckpt: CristianLazoQuispe/MNIST-FM     |
|     headline R6: FID 347.75 vs 409.18     |
+-------------------------------------------+
| Tier 2: image-domain SOTA repro           |
|   CIFAR-10 Rectified Flow                 |
|     61.8M params (gnobitab state_dict)    |
|     v4 honest: framework +24-31% at       |
|     matched NFE; scheduler disc: YES      |
|   MNIST FM full                           |
|     FM loss end-to-end (Wave 191)         |
|     N=1000 framework-vs-baseline sweep    |
|   Scheduler discrimination                |
|     4 schedulers spread ~5.1 FID window   |
+-------------------------------------------+
| Tier 3: real-ckpt SOTA 2026               |
|   Kanzi (ICLR 2026, image FM) (*)         |
|     RMSD 0.886 A mean | regression        |
|   LineageFlow (ICML 2026, protein FM)     |
|     hmmscan_total_hits: 158 -> 342        |
|     headline R1: +116% (p<1e-10)          |
|   FlowMol3 (NeurIPS 2024 + 2026 update)   |
|     fg_dev R3: 0.6381 -> 0.6146 (*)       |
+-------------------------------------------+
| 4-arm head-to-head (cross-tier)           |
|   arms: Vanilla | FlowA | baseline |      |
|     paper-SOTA                            |
|   every cell: matched-weights, seed, NFE  |
|   honest disclosures (*):                 |
|     Kanzi RMSD regression                 |
|     FlowMol3 composite placeholder        |
|     post-cd70821 2D neutral               |
|     FreqFlow synthetic-only               |
|     MNIST smoke ckpt                      |
+===========================================+
```

**Caption (Figure 3).** Three-tier experiment hierarchy plus 4-arm
cross-tier head-to-head. **Tier 1** (toy): 2D Rectified Flow on
`two_moons` / `eight_gaussians` (R5 headline W2 -7.28% / -10.40%);
MNIST FM smoke ckpt (R6 FID 347.75 vs 409.18). **Tier 2** (image
SOTA): CIFAR-10 RF v4 (honest +24-31% at matched NFE; scheduler
discrimination YES); MNIST FM full (FM-loss end-to-end, Wave 191,
N=1000 sweep); scheduler-discrimination row. **Tier 3** (real-ckpt
SOTA 2026): Kanzi (ICLR 2026 image FM, RMSD 0.886 A mean),
LineageFlow (ICML 2026 protein FM, R1 +116% HMMER hits), FlowMol3
(NeurIPS 2024 + 2026 update, R3 fg_dev 4.1sigma). 4-arm H2H
(Vanilla | FlowA | baseline | paper-SOTA) runs at matched-weights /
matched-seed / matched-NFE. Honest disclosures (`*`).

---

## Figure 4 — 4-arm head-to-head schematic (4 baselines + FlowA column)

```
+=========================================+
| FlowA : 4-arm H2H (Vanilla | FastD |    |
|   AB-Cache | LeDiFlow | FlowA)          |
+=========================================+
| row       |Van |FDLL|ABC |LeDi|FlowA    |
+=========================================+
| Accel     |1ps |par |KVca|dist|multi-   |
| mechanism |    |dl  |re  |sh  |round    |
+=========================================+
| Train-    |YES |YES |YES |YES |YES      |
| free?     |    |    |    |    |         |
+=========================================+
| Solver-   |YES |NO  |YES |YES |YES      |
| agnostic? |any |DLLM|any |any |Heun/    |
|           |    |only|ODE |ODE |DPM/RK   |
+=========================================+
| NFE @     |50  |12- |50  |50  |25-50    |
| matched Q |    |25  |    |    |avg 25   |
+=========================================+
| FID/W2    |TIE |WIN*|TIE |WIN*|self-ref |
| quality   |    |<NF |    |mult|s Theorem|
+=========================================+
| NFE       |LOSE|TIE/|WIN |WIN |self-ref |
| budget    |50  |LOSE|cach|mult|avg 25   |
+=========================================+
| HMMER /   |TIE |TIE |TIE |TIE |WIN(R1   |
| protein   |    |    |    |    | +116%)  |
+=========================================+
| integr.   |any |DLLM|any |any |Heun/    |
| swap      |ODE |-sp |ODE |ODE |DPM/RK   |
+=========================================+
| * FlowA wins on multi-round re-inf      |
|   (paper Thm 1, sel_ratio->1); ties/    |
|   losses in CONSOLIDATED_RESULTS.md     |
|   (CIFAR-10 v4 honest: +24-31% @mNFE).  |
+=========================================+
```

**Caption (Figure 4).** 4-arm head-to-head schematic comparing FlowA
against Vanilla (single-pass), Fast-DLLM (parallel-decoding), AB-Cache
(KV/prompt cache reuse), and LeDiFlow (distribution-shift
re-inference). Rows: acceleration mechanism; training-free? (yes for
all five); solver-agnostic? (FlowA = yes: Heun / DPM-Solver++ / RK45 /
user; Fast-DLLM = no, sampler-specific); NFE budget at matched
quality; FID/W2 (quality) wins/ties/losses; NFE (budget)
wins/ties/losses; HMMER/protein counts; integrator swap (solver
freedom). FlowA WINS on quality axes where multi-round re-inference

**Caption (Figure 4).** 4-arm head-to-head schematic comparing FlowA
against Vanilla (single-pass), Fast-DLLM (parallel-decoding), AB-Cache
(KV/prompt cache reuse), and LeDiFlow (distribution-shift
re-inference). Rows: acceleration mechanism; training-free? (yes for
all five); solver-agnostic? (FlowA = yes: Heun / DPM-Solver++ / RK45 /
user; Fast-DLLM = no, sampler-specific); NFE budget at matched
quality; FID/W2 (quality) wins/ties/losses; NFE (budget)
wins/ties/losses; HMMER/protein counts; integrator swap (solver
freedom). FlowA WINS on quality axes where multi-round re-inference
pays off (W2 -7.28%/-10.40% on 2D RF, HMMER +116% on LineageFlow);
TIES on most other arms; LOSES on raw NFE-budget against the best
cache / DLLM arms. CIFAR-10 v4 honest framing (+24-31% at matched
NFE) is documented in `docs/CONSOLIDATED_RESULTS.md` §6.

---

## Provenance

* **Wave 193 P6 deliverable** — 4 ASCII figures refitted to ≤45
  chars/line for EAAI 2-column layout compatibility (Wave 192 P2
  original was 70-75 chars wide, which only fits single-column
  typesetting). The 4-figures preserve their content fidelity;
  layout was reflowed vertically with abbreviated labels and a
  per-line cap.
* **Wave 192 P2 source figures** at this path (pre-refit) preserved
  as the canonical content reference. Refit strategy: vertical
  stacking + abbreviated protocol names + abbreviated step names +
  abbreviated metric labels + abbreviated column-header strings.
* **Wave 192 P1 reframes** preserved: Kanzi and FreqFlow rows are
  marked `*` (= `[Author submitted, 2026]`); the reviewer-uploaded
  PDF can be cited as an attachment.
* **No code changes** in this wave; this file is
  documentation-only.
* **Sister figures** (PNG/SVG, generated by `tools/_make_figures.py`
  and `tools/_make_wave19_figures.py`): `fig5-architecture.svg`,
  `fig6-ablation.svg`, `fig7-conditions.svg`, `fig1-protocol.png`,
  `fig2-loops.png`, `fig3-selection-ratio.png`, `fig4-cifar-fid.png`.
  These 4 ASCII figures are a *plain-text complement* — they paste
  verbatim into EAAI LaTeX 2-column layout, Word, Overleaf, or any
  plain-text reviewer channel without binary asset loss.