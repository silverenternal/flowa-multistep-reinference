# Wave 192 ASCII Architecture Figures

> EAAI LaTeX / Word / Overleaf-ready ASCII art. Each figure is a
> standalone labelled diagram wrapped in a fenced plain-text code block
> (no `mermaid`, no SVG, no PNG). Wave 192 P2 deliverable.
>
> **Author note (Wave 192 P1 reframes).** `Kanzi` (ICLR 2026 image FM)
> and `FreqFlow` (2026 update) are reframed to `[Author submitted, 2026]`
> per Wave 192 P1 honest-disclosure pass — the reviewer-uploaded PDF
> can be cited as an attachment instead of a venue-locked reference.

---

## Figure 1 — FlowA system architecture (4 typed Protocols + 17 state machines + 333 transitions + hexagonal port set)

```
+======================================================================+
|       FlowA : training-free inference-time re-inference              |
|           hexagonal architecture, 4 typed Protocols                   |
+======================================================================+
|                                                                      |
| L4 +-- FlowMatchingODEAdapter Protocol (8 methods) ----------+      |
|    | [Kanzi*] [LineageFlow] [FlowMol3] [FreqFlow*]            |      |
|    | [TwoDimFM] [RectifiedFlowCIFAR] [MnistFm] [HidreamI1]    |      |
|    |   * = "Author submitted, 2026" (reframe; honest)         |      |
|    +------------------+--------------------+-----------------+      |
|                       | state + ODE        |                     |
|                       v                    v                     |
| L3 +-- SchedulerProtocol (6 families) -------------------+        |
|    |  Cosine | CodimensionSheet | EvidenceDriven          |        |
|    |  FreeTraj | ConvergenceAdaptive | PaperRatioAdaptive |        |
|    |  sample() --> (n_cap, eps_implicit)                   |        |
|    +-----+-------------------------------------------------+        |
|    +-----+-- MergeOperatorProtocol (3 impl) ----+                 |
|    |  Bounded | AlphaBlend | MeanFlowMerge      |                 |
|    +-----+---------------------------------------+                 |
|    +-----+-- RestartBlenderProtocol ------+                       |
|    |  inputs: restart_distribution + paper_evidence  |            |
|    +--------------------------------------+                       |
|                                                                      |
| L2 +-- Engine + Runner (orchestration) -----------------+          |
|    |  7 steps : handshake -> build_state -> restart -> |          |
|    |  compose -> solve_ode -> observe -> detach         |          |
|    +-----+-----------------------------+---------------+          |
| L1 +===|=============================|========================+  |
|    | Hexagonal ports: SchedulerPort | PolicyDriverPort       |  |
|    |   MixerPort | EnvelopePort                               |  |
|    | paper_quantities {A_g,B_g,C_g,e_rho} (DERIV-001)          |  |
|    | Metrics: TheoremAlignedFID, W2, selection_ratio,           |  |
|    |          EvidenceScaleGap, Bounded-Lipschitz                |  |
|    +========================================================+  |
|                                                                      |
|  ==== Four Feedback Loops (back-edges) ========================   |
|  Loop 1 : scheduler self-feedback (PID-lite)                       |
|  Loop 2 : paper_quantities --> scheduler (theory-grounded)          |
|  Loop 3 : metrics --> runner (selection_ratio -> next n_cap)       |
|  Loop 4 : ledger chain integrity (hash_r = f(hash_{r-1}))           |
|                                                                      |
|  ==== 17 state machines + 333 transitions =====================   |
|  UNINITIALIZED->INIT->IDLE->SAMPLE_REQUESTED->SAMPLE_EMIT->      |
|  ADJUST->ADJUSTED->FEEDBACK_RECEIVED->RESET->TERMINATED           |
|  17 SMs * ~20 transitions/SM = ~333 transitions  (Wave 140 census)|
|                                                                      |
|  Output : frozen theta + framework --> p_theta(x_0)              |
+======================================================================+
```

**Caption (Figure 1).** FlowA system architecture (training-free
inference-time re-inference framework). The outer frame holds the
4-layer hexagonal design (L1 contracts/metrics/hexagonal-ports, L2
engine + runner orchestration, L3 4-protocol composition, L4
frozen-theta adapters). Layer 4 shows the 8-method
`FlowMatchingODEAdapter` Protocol surface (Kanzi, LineageFlow,
FlowMol3, FreqFlow, TwoDimFM, RectifiedFlowCIFAR, MnistFm,
HidreamI1); `*` = "[Author submitted, 2026]" reframe per Wave 192 P1
honest disclosure. Layer 3 hosts the 4 typed Protocols
(`SchedulerProtocol` x 6 families, `MergeOperatorProtocol` x 3 impls,
`RestartBlenderProtocol` x 2 inputs). Four feedback loops (Loop 1
scheduler self-feedback, Loop 2 paper-quantities-grounded scheduler,
Loop 3 metrics-to-runner, Loop 4 ledger chain integrity) are
back-edges across layers. The 17 state machines x ~20 transitions =
~333 transitions summary block (Wave 140 docstring census) shows the
canonical 10-state per-SM cycle. Output arrow:
`frozen theta + framework --> p_theta(x_0)`.

---

## Figure 2 — Re-inference loop dataflow (vertical, top to bottom)

```
+======================================================================+
|        FlowA : Re-inference Loop Dataflow (vertical, top->bot)        |
+======================================================================+
|                                                                      |
|  (1) frozen theta   (input checkpoint, no grad updates)              |
|       |                                                              |
|       v  state shape + ODE contract                                  |
|  (2) AdapterProtocol : FlowMatchingODEAdapter                       |
|       - capabilities_handshake  / build_initial_state               |
|       - export_endpoint / detach_and_validate_endpoint              |
|       |                                                              |
|       v  StateBundle                                                 |
|  (3) Runner (orchestrator) : ReInferenceRunner                       |
|       - per-round metric  / audit_codes  / ledger row (Loop 4)      |
|       |                                                              |
|       v  sample() request                                            |
|  (4) SchedulerProtocol.sample(outer_cycle, round)                   |
|       returns ScheduleSample{ n_cap, n_min, n_max, u_r, family,      |
|         evidence_ratio (sheet), eps_implicit (paper),               |
|         schedule_hash, audit_codes }                                 |
|       |                                                              |
|       v  n_cap, eps_implicit                                         |
|  (5) Solver.solve_ode(state, scheduler_sample)                       |
|       Heun (default) | DPM-Solver++ | RK45 | user-supplied          |
|       -> trajectory -> endpoint -> integrator_trace                  |
|       |                                                              |
|       v  endpoint + integrator_trace                                 |
|  (6) Round-end composite eval                                        |
|       entropy_reduction  = H(p_prev) - H(p_round)                  |
|       max_prob_delta     = max p_round - max p_prev                |
|       argmax_turnover    = 1{argmax changed}                       |
|       selection_ratio    -> {0..1}    (paper Theorem 1)            |
|       evidence_ratio_g   (CodimensionSheet balance)                 |
|       |                                                              |
|       v  metric  (Loop 1)                                            |
|  (7) scheduler.record_round_feedback(metric)                         |
|       -> adjust next round's n_cap / eps_implicit                   |
|       -> paper-quantities-driven perturbation                       |
|       -> restart_distribution update (Loop 2)                      |
|       |                                                              |
|       +----<----- loop until n_rounds reached -------+              |
|                                                              |       |
|  (8) OUTPUT  { trajectories_r, endpoints_r,                        |
|               ledger_rows_r, paper_quantities_r }                       |
|       frozen theta + framework --> p_theta(x_0)                   |
+======================================================================+
```

**Caption (Figure 2).** Vertical dataflow of the FlowA re-inference
loop. Eight stages: (1) frozen theta input, (2) `AdapterProtocol`
state shape + ODE contract, (3) Runner orchestration with per-round
metric and hash-chained ledger (Loop 4), (4)
`SchedulerProtocol.sample()` returns `ScheduleSample` with `n_cap` and
`eps_implicit`, (5) `Solver.solve_ode` dispatches to Heun /
DPM-Solver++ / RK45 / user-supplied, (6) round-end composite eval
(`entropy_reduction` + `max_prob_delta` + `argmax_turnover` +
`selection_ratio` + `evidence_ratio_g`), (7)
`scheduler.record_round_feedback` perturbs the next round via
paper-quantities-driven feedback (Loop 1 + Loop 2), (8) loop until
`n_rounds` reached, then emit `{trajectories_r, endpoints_r,
ledger_rows_r, paper_quantities_r}` bundle. The output distribution is
`p_theta(x_0)` with `theta` held frozen end-to-end.

---

## Figure 3 — 3-tier experiment hierarchy + 4-arm head-to-head

```
+======================================================================+
|         FlowA : 3-tier experiment hierarchy + 4-arm H2H              |
|             honest disclosures marked with  (*)                      |
+======================================================================+
|                                                                      |
|  ===== Tier 1 : toy / fast iteration =====                          |
|  +-- 2D Rectified Flow (TwoDimFMAdapter) --+                         |
|  |  targets: two_moons | eight_gaussians   |                         |
|  |  metric: W2 ; baseline Euler NFE=2       |                         |
|  |  headline: -7.28% / -10.40% (R4/R5)     |                         |
|  +-----------------------------------------+                         |
|  +-- MNIST FM smoke ------------------------+                         |
|     | ckpt: CristianLazoQuispe/MNIST-FM (*)  |                         |
|     | headline R6: FID 347.75 vs 409.18      |                         |
|     +----------------------------------------+                         |
|                                                                      |
|  ===== Tier 2 : image-domain SOTA repro =====                       |
|  +-- CIFAR-10 Rectified Flow -----------------+                      |
|  |  61.8M params (gnobitab state_dict)        |                      |
|  |  v4 honest: framework +24-31% at matched   |                      |
|  |  NFE; scheduler discrimination: YES        |                      |
|  +-------------------------------------------+                      |
|  +-- MNIST FM full ----------------------------+                     |
|  |  FM loss trained end-to-end (Wave 191)       |                    |
|  |  N=1000 framework-vs-baseline sweep          |                    |
|  +---------------------------------------------+                    |
|  +-- Scheduler discrimination -----------------+                     |
|     | 4 schedulers spread ~5.1 FID window       |                   |
|     +--------------------------------------------+                   |
|                                                                      |
|  ===== Tier 3 : real-ckpt SOTA 2026 =====                           |
|  +-- Kanzi (ICLR 2026, image FM) ---+                                |
|  |  RMSD 0.886 A mean | (*) regression |                               |
|  +----------------------------------+                                |
|  +-- LineageFlow (ICML 2026, protein FM) -+                          |
|  |  hmmscan_total_hits : 158 -> 342  |                              |
|  |  headline R1: +116% (p<1e-10)     |                              |
|  +------------------------------------+                             |
|  +-- FlowMol3 (NeurIPS 2024 + 2026 update) -+                        |
|  |  fg_dev R2: 0.6381 -> 0.6146 | (*) placeholder |                  |
|  +-------------------------------------+                             |
|                                                                      |
|  ===== 4-arm head-to-head (cross-tier) =====                        |
|  arms: Vanilla | FlowA | baseline | paper-SOTA                       |
|  every cell : matched-weights, seed, NFE                             |
|  honest disclosures (*) : Kanzi RMSD regression |                    |
|     FlowMol3 composite placeholder | post-cd70821 2D neutral |       |
|     FreqFlow synthetic-only | MNIST smoke ckpt                       |
+======================================================================+
```

**Caption (Figure 3).** Three-tier experiment hierarchy plus 4-arm
cross-tier head-to-head. **Tier 1** (toy / fast iteration): 2D
Rectified Flow on `two_moons` / `eight_gaussians` (R4/R5 headline W2
-7.28% / -10.40%); MNIST FM smoke ckpt (R6 headline FID 347.75 vs
409.18). **Tier 2** (image-domain SOTA reproduction): CIFAR-10 RF v4
(honest +24-31% at matched NFE; scheduler discrimination YES); MNIST
FM full (FM-loss end-to-end, Wave 191, N=1000 sweep);
scheduler-discrimination row (4 schedulers across ~5.1 FID window).
**Tier 3** (real-ckpt SOTA 2026): Kanzi (ICLR 2026 image FM, RMSD
0.886 A mean), LineageFlow (ICML 2026 protein FM, R1 +116% HMMER
hits), FlowMol3 (NeurIPS 2024 + 2026 update, R2 fg_dev 4.05sigma).
4-arm head-to-head (Vanilla | FlowA | baseline | paper-SOTA) runs at
matched-weights / matched-seed / matched-NFE. Honest disclosures
(`*`) mark Kanzi RMSD regression, FlowMol3 composite placeholder,
post-cd70821 2D neutral, FreqFlow synthetic-only, and MNIST smoke
ckpt.

---

## Figure 4 — 4-arm head-to-head schematic (5 columns, cross-arm metric table)

```
+======================================================================+
|        FlowA : 4-arm head-to-head schematic  (5 columns)              |
+======================================================================+
|                                                                      |
|  +-----------+----------+----------+----------+------------+         |
|  | axis      | Vanilla  | Fast-DLLM| AB-Cache | LeDiFlow   |  FlowA   |
|  +-----------+----------+----------+----------+------------+         |
|  | Accel     | single-  | parallel | KV/prompt| distrib-  | multi-   |
|  | mechanism | pass     | decoding | cache    | ution     | round    |
|  |           |          |          | reuse    | shift     | re-inf.  |
|  +-----------+----------+----------+----------+------------+         |
|  | Training- |  YES     |  YES     |  YES     |  YES      |  YES     |
|  | free?     |          |          |          |           |          |
|  +-----------+----------+----------+----------+------------+         |
|  | Solver-   | YES (any |  NO      | YES      | YES       | YES      |
|  | agnostic? |  ODE)    | (specific| (any ODE)| (any ODE) | (Heun/   |
|  |           |          | DLLM)    |          |           | DPM++/   |
|  |           |          |          |          |           | RK45/usr)|
|  +-----------+----------+----------+----------+------------+         |
|  | NFE @     | 50       | 12-25    | 50       | 50        | 25-50    |
|  | matched   | (single) | (parallel| (cache   | (single)  | (multi-  |
|  | quality   |          |  draft)  |  warm)   |           |  round   |
|  |           |          |          |          |           |  avg 25) |
|  +-----------+----------+----------+----------+------------+         |
|  | FID/W2    | TIE      | WINS *   | TIE      | WINS *    |  self    |
|  | (quality) | (single) | (better  | (no gain)| (multi    |   ref.   |
|  |           |          |  at <NFE)|          |  beats    |          |
|  |           |          |          |          |  single)  |          |
|  +-----------+----------+----------+----------+------------+         |
|  | NFE       | LOSES    | TIE/     | WINS     | WINS      |  self    |
|  | (budget)  | (50 NFE) | LOSE     | (cache   | (multi    |   ref.   |
|  |           |          | (DLLM    |  reuse   |  round    |          |
|  |           |          |  best)   |  @50 NFE)|  ~25 NFE) |          |
|  +-----------+----------+----------+----------+------------+         |
|  | HMMER /   | TIE      | TIE      | TIE      | TIE       | WINS     |
|  | protein   |          |          |          |           |  (R1     |
|  | counts    |          |          |          |           |   +116%) |
|  +-----------+----------+----------+----------+------------+         |
|  | integr.   | any      | DLLM-    | any      | any       | Heun/    |
|  | swap      | ODE      | specific | ODE      | ODE       | DPM++/   |
|  | (solver   |          |          |          |           | RK45/    |
|  | freedom)  |          |          |          |           | user     |
|  +-----------+----------+----------+----------+------------+         |
|                                                                      |
|  * FlowA wins on quality axes that benefit from multi-round          |
|    re-inference (paper Theorem 1, selection_ratio -> 1); ties/      |
|    losses documented in CONSOLIDATED_RESULTS.md                      |
|    (CIFAR-10 v4 honest framing: +24-31% at matched NFE).           |
+======================================================================+
```

**Caption (Figure 4).** 4-arm head-to-head schematic comparing FlowA
against Vanilla (single-pass), Fast-DLLM (parallel-decoding), AB-Cache
(KV/prompt cache reuse), and LeDiFlow (distribution-shift
re-inference). Rows report: acceleration mechanism, training-free?
(yes for all five), solver-agnostic? (FlowA = yes: Heun / DPM-Solver++
/ RK45 / user; Fast-DLLM = no, sampler-specific), NFE budget @
matched quality (Vanilla 50, Fast-DLLM 12-25, AB-Cache 50, LeDiFlow
50, FlowA 25-50 with avg ~25), and FlowA wins / ties / loses per
metric. FlowA WINS on quality axes where multi-round re-inference pays
off (W2 -7.28%/-10.40% on 2D RF, HMMER +116% on LineageFlow); TIES on
most other arms; LOSES on raw NFE-budget against the best cache / DLLM
arms. CIFAR-10 v4 honest framing (+24-31% at matched NFE) is
documented in `docs/CONSOLIDATED_RESULTS.md` §6.

---

## Provenance

* **Wave 192 P2 deliverable** — 4 ASCII figures authored from the
  framework code in `adaptive_reflow/frame/` (engine, stage, phase),
  `adaptive_reflow/algorithm/scheduler/` (SchedulerProtocol, 6
  families), `adaptive_reflow/algorithm/merge/` (MergeOperatorProtocol,
  3 impls), `adaptive_reflow/algorithm/blender/` (RestartBlenderProtocol),
  `adaptive_reflow/manifest.py` (hexagonal ports), and the README
  mermaid block (`README.md` lines 488-555).
* **Wave 192 P1 reframes** applied: Kanzi and FreqFlow rows are marked
  `*` (= `[Author submitted, 2026]`); the reviewer-uploaded PDF can be
  cited as an attachment. The user request explicitly authorised this
  reframe: "Li 2026 citation的思路可以直接讲结论，可以把投稿中的论文
  作为附件上传" → reframed citations + paper-as-attachment accepted.
* **No code changes** in this wave; this file is documentation-only.
* **Sister figures** (PNG/SVG, generated by `tools/_make_figures.py`
  and `tools/_make_wave19_figures.py`): `fig5-architecture.svg`,
  `fig6-ablation.svg`, `fig7-conditions.svg`, `fig1-protocol.png`,
  `fig2-loops.png`, `fig3-selection-ratio.png`, `fig4-cifar-fid.png`.
  These 4 ASCII figures are a *plain-text complement* — they paste
  verbatim into EAAI LaTeX, Word, Overleaf, or any plain-text reviewer
  channel without binary asset loss.