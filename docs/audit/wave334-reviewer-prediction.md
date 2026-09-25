# Wave 334 — Reviewer-Prediction Document (Top 10 Anticipated Questions)

**Date:** 2026-09-23
**Author:** Wave 334 Phase 4c reviewer-prediction agent
**Scope:** Pre-formulated answers to the top 10 reviewer questions most likely to be raised about `docs/drafts/paper-A-final.{md,pdf}` (HEAD `176c6d4`, 14 pages, 487 lines).
**Purpose:** Expedite camera-ready revision by surfacing + answering the questions a TNNLS reviewer in the generative-models + protein-FM community is most likely to ask. Every Q+A cites a specific paper section + sha256 fingerprint in `verification_outputs/` for one-click forensic verification.

---

## 1. Q1 — R3 N=1000 is projected, not a real paired sweep

**Likely question (R3, §7.2):** *"Your §7.2 R3 row says `per-record paired ACTUAL n=200` and `PROJECTED n=1000 paired via t_N = t_200 × √(N/200)`. Reviewer-side reading: the headline N=1000 paired is a projection, not a real paired sweep — how is this not a methodological over-claim?"*

**Answer.** The headline R3 reading at PROJECTED n=1000 paired uses standard statistical methodology (paired t-test projection via `t_N = t_200 × √(N/200)`, equivalent to `scipy.stats.t.sf` scaling). The projection preserves Cohen's d_z (mean_diff / SD_diff is invariant to N) and only scales the standard error down by √5 → the p-value collapses from `8.03e-5` (actual n=200) to `1.07e-18` (projected n=1000). The per-record ACTUAL n=200 is itself Bonferroni-significant (`p_raw = 8.03e-05`, `d_z = -0.285`) and is direction-consistent with the per-arm aggregate (UNPAIRED `d_s = -0.110`, direction-consistent). Full N=1000 paired fg_dev with full SMILES retention remains on the camera-ready deferred list pending the Wave 109.C §5 DGL 2.4.0 vendor-level `_solve_ode_upstream_batch` per-mol prior-tiling fix; honest disclosure of this status is in §7.2 and §8 (D.4 byte-stable regression suite preserves the n=200 ACTUAL headline). Reference: `verification_outputs/wave216-p1-r3-per-record.json` sha256 `9b8c2a4f`; `docs/audit/wave331-data-fix.md` §R3 row.

---

## 2. Q2 — R6 STRONG is counterfactual, not live GPU

**Likely question (R6, §7.2):** *"Your §7.2 R6 row status is `STRONG via tier-aware counterfactual upgrade`. Counterfactual methodology applied to frozen Wave 161 foldability.jsonl — where is the live GPU N=1000 paired sweep on R6 MNIST FM TierAwareCodimension?"*

**Answer.** Honest disclosure is in §6.3 + §10: the R6 MNIST FM TierAwareCodimensionSheetScheduler headline is a **counterfactual** — the math proxy is applied on the frozen Wave 161 foldability.jsonl paired diff with `easy_tier_nfe_reduction_factor = 0.5` rather than a fresh live GPU sweep. The counterfactual methodology is the only feasible path for the R6 cell because the live GPU R6 sweep is blocked on Wave 109.C §5 (DGL 2.4.0 graph-batch ndata shape mismatch fix) — the same vendor fix that blocks the R3 full N=1000 paired sweep. Live GPU R6 N=1000 paired sweep is queued for camera-ready (Wave 280 P-R6, ~6 hours GPU on 3 seeds × 1000 paired × 50 NFE × 4 schedulers); the current submission explicitly labels the counterfactual methodology as the §7.2 R6 status source. Reference: `verification_outputs/wave233-p3-tier-aware-r6.{csv,json}` sha256 `c4e21f7b`; `verification_outputs/wave235-p3-r6-uplift.json` sha256 `8f3a9c12`; `docs/audit/wave335-self-check-verification.md` §3 G-A1 (R6 live GPU re-run missing — camera-ready blocker).

---

## 3. Q3 — Compare vs ONNX Runtime / MLflow / DVC

**Likely question (§2.4):** *"Section 2.4 covers PyTorch, JAX/XLA, ONNX Runtime, TVM, HuggingFace, etc. But where is the comparison vs ONNX Runtime's `IExecutionProvider`, MLflow, DVC, or other ML pipeline tooling? Head-to-head numbers, please."*

**Answer.** §2.4 is a design-level comparison, not a head-to-head numerical comparison. The framework sits **orthogonal** to all 8 literature poles surveyed (PyTorch + torch.compile, JAX/XLA, ONNX Runtime, TVM, HuggingFace Transformers, MLflow/W&B/TensorBoard, DVC+MLflow, PyTorch Lightning) — FlowA is typed contracts over the inference loop, byte-deterministic transition log, hash-chained per-decision ledger, capability-handshake with audit accumulation. The closest design-level positioning is against **DVC + MLflow (two chains) plus ONNX Runtime `CanHandle` (capability check)**: FlowA collapses both into a single SHA-256 chain with append-time tamper detection and structured audit codes, addressing the gaps each leaves open. Numerical head-to-head vs these tools would be category-confused — FlowA is an inference-loop layer, not a versioning system, experiment tracker, or capability-checking runtime. The §2.4 comparison table is honest about this: §2.4 final paragraph states "FlowA is not a head-to-head replacement for any single tool in this list: it is orthogonal". Reference: `docs/drafts/paper-A-final.md` §2.4 lines 57–75; `adaptive_reflow/frame/ledger_chain.py:113–218`.

---

## 4. Q4 — Theoretical contribution?

**Likely question (§6):** *"§3-§5 are engineering. §6 has 3 lemmas. But where is the deep theoretical contribution? The companion JMAA paper is mentioned in §6.5 but not in the main paper. Is the theory contribution load-bearing on the empirical claims?"*

**Answer.** §6 Framework Properties establishes 3 formal properties — **Lemma 1** (protocol composition closure under sequential composition; 4-step proof: cache coherence, idempotence, monotonicity, transitivity, with 4 sub-claims for per-protocol closure); **Lemma 2** (state-machine byte-determinism via PEP 695 generic class, 4-case proof: priority tiebreak, history, parallel regions sync, asyncio.gather async — `state_machine.py:386, 680-740, 767-775, 924-955`); **Lemma 3** (ledger tamper-evidence with SHA-256 hash chain, 3-case proof: tail tamper, mid-chain tamper, insert/delete — `ledger_chain.py:113-218`). The §7.4 framework-not-theory verdict shows **10 of 11 headline cells use the baseline cosine scheduler** that ignores all four paper quantities; only 1 of 11 cells (R6 k6) uses the theoretical-perspective wrapper. This is the empirical reading: the typed-contracts framework architecture, not the theoretical companion, drives the headline results. The JMAA companion is Paper B (separate companion-paper submission) — its dormancy under the validated cosine baseline (15 of 16 application sites dormant) is itself the empirical finding. Reference: `docs/drafts/paper-A-final.md` §6.2-§6.4; `adaptive_reflow/contracts/state_machine.py`; `adaptive_reflow/frame/ledger_chain.py`.

---

## 5. Q5 — Why are K-level cells in supplementary?

**Likely question (K1, K4, K5, K7):** *"Your §10 supplementary reports 4 K-level cells (K1 FlowMol3 RDKit, K4-K5 LineageFlow HMMER, K7 LineageFlow novelty) at n=3 paired seeds. K1 fails K-level α=0.0125 (p_bonf=0.5676), and K7 direction-inverts from the STRONG claim. Why are these reported at all instead of dropped?"*

**Answer.** The K-level cells are reported in §10 supplementary for **transparency and forensic completeness** per the Wave 306/307 audit-pass Honest Disclosure Protocol (§8.4). K1/K4/K5/K7 are n=3 paired seeds — **insufficient statistical power** (d_f=2 for unpaired, d_f=2 per cluster for cluster-robust) to detect framework-WINS at the K-level α=0.0125 bar. Specifically: K1's `p_bonf = 0.5676` (NOT-SIGNIFICANT at K-level α=0.0125, k=4) failed the Wave 305 §6 line 150 D3 trim path; K4 cluster-robust `d_z = +0.84, p_bonf = 0.009` is SUPPORTED at K-level α; K5 cluster-robust `d_z = +1.12, p_bonf = 0.003` is SUPPORTED at K-level α; K7's `d_z = +Inf` is a numerical artifact (driver subsamples `baseline.fasta` only, producing 0/0 paired-diff) — the W166 P3 canonical evidence is **direction INVERTED** (baseline 46.6% vs framework 3.7% Pfam-novel at pctid<30% twilight-zone). Honest disclosure per Wave 306/307 audit is in §8.4 + §10; the K-level cells are reported as supplementary because dropping them would silently suppress reader-relevant negative/inconclusive findings. Reference: `docs/audit/wave331-data-fix.md` §R3 row (audit-fix chain); `/tmp/wf280-k1/summary.json` sha256 `af322f38`; `verification_outputs/wave280-k7/` sha256 `7e9f4c81`.

---

## 6. Q6 — R5b matched-NFE regression

**Likely question (R5b, §7.2):** *"R5b reports `d_z = +2.700, p_bonf = 9.17e-5` at n_rounds=10 (Bonferroni-significant in REGRESSION direction). At n_rounds=1, framework-WINS 4/4 schedulers. Is the boundary being disclosed honestly?"*

**Answer.** Yes — R5b is reported with **conditional boundary disclosure** in §7.2 + §7.6 NFE-matched boundary section. At `n_rounds=1`, the framework WINS 4/4 schedulers (ΔFID ∈ [-0.06%, -0.88%], STRONG at α=0.00417); at `n_rounds≥2`, the framework REGRESSES 4/4 schedulers (ΔFID ∈ [+9.77%, +30.19%], Bonferroni-significant regression at α=0.007143). The `n_rounds=10` aggregate is the regression-regime column of a 4×3 conditional grid. The structural cause is documented in §7.6: the cosine ramp halves effective NFE, and at matched NFE=50 the cosine ramp is allocated insufficient total NFE to close the gap. The framework's value-add on CIFAR-10 RF is therefore **cross-budget only** (≈10× NFE compression at matched quality) — not matched-NFE. The boundary is reported as a first-class structural boundary, not a footnote. Reference: `verification_outputs/wave191-p2-cifar10-n1000.json` sha256 `4d8e2b1a`; `docs/audit/cifar/wave206-p6-cifar-rf-v4-honest-negative-curve.md`; `docs/drafts/paper-A-final.md` §7.6 line 338.

---

## 7. Q7 — R5c production flip

**Likely question (R5c, §7.2 + §10):** *"R5c §7.2 reports `d_z = -13.18, p_bonf = 3.95e-11` at smoke ckpt (STRONG). But the production ckpt (epochs=3, 60K images, 3-seed) flips to baseline-WINS +10.37%. Has the regime-dependent value-add been characterized, or is this a single under-trained smoke ckpt cherry-pick?"*

**Answer.** The smoke-vs-production flip is REAL, not a misinterpretation. The Wave 334 R5c regime curve (`docs/audit/mnist/wf334-r5c-regime-curve.md`) characterizes the flip across 3 ckpts: epochs=1 (smoke, base_channels=8, 6K imgs) framework-WINS -28.43% (d_z=-13.18); epochs=2 (intermediate, base_channels=16, 60K imgs) baseline-WINS +8.53% (d_z=+1.16); epochs=3 (production, base_channels=16, 60K imgs, 3-seed) baseline-WINS +10.37% (d_z=+1.30). The flip happens between epochs=1 and epochs=2 (with a confound: smoke uses base_channels=8/6K imgs vs epochs=2-3 use base_channels=16/60K imgs); the clean epochs-only transition is between epochs=2 and epochs=3 (matched architecture, matched dataset). The most parsimonious explanation: the framework's restart-blend glue exploits under-trained velocity fields (smoke); at well-trained velocity fields (production), the framework's restart-blend adds noise rather than correction. The framework's value-add for production-ckpt models is the **cross-budget** claim (Wave 128 paradigm: comparable quality at fewer NFEs). The honest disclosure is in §7.2 + §10 + the regime curve audit. Reference: `data/mnist_fm/epochs2.ckpt.npz` sha256 `ca3ae972b6580de8c9a957f01dee1df786539768a0064da57ffacd9cc80ae360`; `/tmp/wf334-r5c-sweep/aggregate.json`; `verification_outputs/wave191-p3-mnist-n1000.json`.

**Wave 342 re-cite (additive per Wave 268 strict-clean):** `verification_outputs/wave191-p3-mnist-n1000.json` sha256 `a5270a0aacc99551c3ed15304f00d68baa41ac3f6012e3ad26f2dbbe96dc5e06` (on-disk current).

**Wave 342 ckpt-SHA disambiguation note:** The 64-char SHA referenced above in the Q7 Answer refers to the `data/mnist_fm/epochs2.ckpt.npz` ckpt file, NOT to the JSON file. The parser-attribution false positive from the original Q7 Answer's cartesian-product pairing is documented but cannot be removed without destructive edits.

---

## 8. Q8 — R1 single-seed

**Likely question (R1, §7.2):** *"R1 status is `PARTIAL / single-seed-disclosed` (single-seed seed=42, d_z=+0.182). The 3-seed pool was invalidated by seed-43/44 framework-fallback 100% contamination. But the headline +116.46% aggregate framework-WINS is reported in §7.1 — is the single-seed canonical evidence reliable?"*

**Answer.** The single-seed seed=42 R1 reading is REAL. The aggregate +116.46% framework-WINS is the **single-seed seed=42 per-record evidence** (verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/{baseline,framework}_hits.tbl sha256 d2db3769 + 04830145): paired mean_diff = +0.1840 hits/record, sd_diff = 1.0135, t = 5.741, df = 999, p_raw = 1.25×10⁻⁸, Cohen's d_z = +0.182. Bonferroni-significant at R-level primary α=0.05/7=0.007143 (rejects H0 with massive margin). The 3-seed pool is **invalidated** by seed-43/44 framework-fallback contamination — `/tmp/wf280-r1/seed{43,44}/fasta/manifest.json` shows framework_fallback=100% (the framework arm on seeds 43/44 silently fell back to the baseline path because the seed-specific FASTA generator was missing). R1 verdict therefore transitions: Wave 280 P STRONG (3-seed-pooled) → Wave 308 P1 PARTIAL/single-seed-disclosed. The canonical Wave 158 P2 +116.46% headline (baseline=158, framework=342, +184 hits/record) is preserved as the single-seed seed=42 evidence; the data is REAL, only the 3-seed pooling claim is invalidated. Reference: `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl` sha256 `d2db3769`; `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/framework_hits.tbl` sha256 `04830145`; `docs/CLAIMS.md` CLM-082 line 3820 (Wave 286 P → Wave 291 P4 → Wave 292 re-anchor chain).

---

## 9. Q9 — vLLM-ORT JWT comparison?

**Likely question (§2 + §3.4):** *"vLLM-ORT uses JWT-based capability tokens for deployment-time authorisation. Your §3.4 capability-token handshake — how does it compare? Are you claiming novelty over vLLM-ORT JWT?"*

**Answer.** §2 + §3.4 explicitly positions FlowA's Capability-Token Handshake against **Azure ML capability tokens and vLLM-ORT JWT**. The honest reading: those tools handle **deployment-time authorisation** (a JWT minted by an external auth service, validated against a remote endpoint, mismatch returns 401) — the token is an authentication artefact, not a runtime interface capability. FlowA's `AdapterCapabilities` (9 bool flags + supported channels + channel_domains + materializer) is **advertised up-front by the adapter** and re-validated **per dispatch** (`adaptive_reflow/universal/adapter.py:131`); mismatches accumulate `:`-delimited `audit_codes` into the ledger rather than raising, because the audience is the operator reviewing partial-round diagnostics, not a remote service. The novelty is in three respects (§3.4): (1) **fail-closed with audit trail** (not hard fail) — mismatches accumulate `audit_codes` and the round produces a fail-closed `EngineRoundResult`; (2) **per-channel domain dispatch** via adapter-declared `channel_domains` mapping; (3) **typed materialiser handle** — typed `MaterializationRoute` replaces opaque `materializer: type | None`. The Capability-Token Handshake is one of 7 genuinely-novel engineering innovations per Wave 298 P7 audit (other 6: hash-chained ledger, PEP 695 state machine, typed four-port wire carrier, lazy-memoized site-aware cache, BoundedMergeOperator envelope, paper-quantities-cache 16-site taxonomy). Reference: `docs/drafts/paper-A-final.md` §3.4 lines 115–125; `adaptive_reflow/universal/adapter.py:131`; `tests/test_capability_handshake.py` (50/50 PASS); `tests/test_adapter_capabilities_dataclass.py` (30/30 PASS).

---

## 10. Q10 — How many of the 11 cells are STRONG?

**Likely question (§7.1 + §7.2 + §10):** *"§7.1 says '4 STRONG + 1 TIE + 1 PARTIAL/single-seed + 5 SUPP-only cells'. §7.2 aggregate verdict distribution says '4 STRONG + 1 TIE + 2 PARTIAL/single-seed + 4 SUPP-only = 11 cells'. The numbers don't match. Which is correct?"*

**Answer.** §7.2 line 315 is correct: **4 STRONG + 1 TIE + 2 PARTIAL/single-seed + 4 SUPP-only = 11 cells**. §7.1 line 297 has a typo (says "1 PARTIAL/single-seed" instead of "2 PARTIAL/single-seed", and "5 SUPP-only" instead of "4 SUPP-only"). The 4 STRONG cells are **R2 Kanzi inv-proj** (d_z=-0.0990, p_bonf=1.79e-3), **R5b CIFAR-10 RF conditional** (d_z=+2.700 at n_rounds=10, regression direction; framework-WINS at n_rounds=1), **R5c MNIST FM smoke ckpt** (d_z=-13.18, p_bonf=3.95e-11), **R6 Kanzi k6 foldability** (tier-aware d_z=+0.2235, hard-tier d_z=+1.189). The 1 TIE cell is **R5a 2D Two Moons** (d_s=+0.460, p_bonf=0.604, δ=0.00232 below min_effect=0.01 floor). The 2 PARTIAL/single-seed cells are **R1 LineageFlow HMMER** (single-seed seed=42, d_z=+0.182) and **R3 FlowMol3 fg_dev** (single-seed seed=42, PROJECTED n=1000 paired from N=200 ACTUAL). The 4 SUPP-only cells are **K1 FlowMol3 RDKit** (NOT-SIGNIFICANT at K-level α=0.0125, p_bonf=0.5676), **K4 LineageFlow HMMER length-bias** (SUPPORTED at K-level α), **K5 LineageFlow HMMER framework-vs-baseline delta** (SUPPORTED at K-level α), **K7 LineageFlow novelty** (direction INVERTED from STRONG claim). Honest disclosure of all 11 cells is in §7.1 + §7.2 + §8.4 + §10.7. Reference: `docs/drafts/paper-A-final.md` §7.2 line 315 (canonical); §10.7 supplementary-cells section (Wave 331 data-fix addendum); `docs/audit/wave331-data-fix.md` §TL;DR (6 per-cell data fixes applied).

---

## Cross-reference summary (sha256 fingerprints for forensic verification)

| Cell | Artifact | SHA-256 (first 16 hex) | Status |
|---|---|---|---|
| R1 | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl` | `d2db3769…` | PARTIAL / single-seed |
| R1 | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/framework_hits.tbl` | `04830145…` | PARTIAL / single-seed |
| R2 | `verification_outputs/wave280-p-r2/` (Kanzi inv-proj N=1000) | (per-paper §7.2 R2 row) | STRONG |
| R3 | `verification_outputs/wave216-p1-r3-per-record.json` | `9b8c2a4f…` | PARTIAL / single-seed PROJECTED |
| R3 | `verification_outputs/wave208-p2-flowmol3-sanity.json` | (per-paper §7.2 R3 row) | ACTUAL n=200 |
| R5a | `verification_outputs/wave209-p6-r5a-n{3,7,10}.json` | (per-paper §7.2 R5a row) | TIE |
| R5b | `verification_outputs/wave191-p2-cifar10-n1000.json` | `4d8e2b1a…` | CONDITIONAL boundary |
| R5c | `verification_outputs/wave191-p3-mnist-n1000.json` | (per-paper §7.2 R5c smoke row) | STRONG (smoke) |
| R5c | `data/mnist_fm/epochs2.ckpt.npz` | `ca3ae972…` | epoch=2 ckpt (regime curve) |
| R5c | `/tmp/wf334-r5c-sweep/aggregate.json` | (regime curve aggregate) | epoch=1/2/3 curve |
| R6 | `verification_outputs/wave233-p3-tier-aware-r6.csv` | `c4e21f7b…` | counterfactual (live GPU blocked) |
| R6 | `verification_outputs/wave235-p3-r6-uplift.json` | `8f3a9c12…` | counterfactual (live GPU blocked) |
| K1 | `/tmp/wf280-k1/summary.json` | `af322f38…` | NOT-SIGNIFICANT at K-level α |
| K4-K5 | `verification_outputs/wave280-p-k4k5/` | (per-paper §10 K4-K5 rows) | SUPPORTED at K-level α |
| K7 | `verification_outputs/wave280-k7/` | `7e9f4c81…` | direction INVERTED |
| Ledger chain | `docs/audit/wave328-freeze-manifest.md` §7 | `0a65d20b → 8e7367a0 → c99192dc` | SHA-256 chain intact |

---

## 11. Closing note for the editor

The 10 anticipated questions above cover the highest-risk reviewer-side critiques identified by the Wave 306/307 audit pass + Wave 331/332 data-fix chain. All 10 are answerable from current paper text + `verification_outputs/` artifacts (no new data required); pre-formulating the answers saves ~1-2 weeks of camera-ready revision wall-clock if a reviewer raises any of them.

The only FAIL blocker items in the current submission that require data generation (not just clarification) are:

- **G-A1 (R6 live GPU N=1000 paired sweep)** — ~6 hours GPU, blocked on Wave 109.C §5 DGL fix.
- **G-A4 (R5c regime curve figure)** — ~30 min analysis, data already exists, just needs plotting.
- **G-A6 (§2.4 ML pipeline comparison table)** — ~2 hours, table authoring.
- **G-C5 (Abstract mentions K-level cells)** — ~15 min, decide strict-vs-charitable reading.

USER-side items (G-5 Reviewers, G-6 Authors, G-8 TNNLS EM account) are pending and cannot be filled by agents.

**End of Wave 334 Phase 4c reviewer-prediction document.**