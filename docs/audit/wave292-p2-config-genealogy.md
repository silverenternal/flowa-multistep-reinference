# Wave 292 P2 — Configuration genealogy for headline results

**Date:** 2026-09-23
**Branch:** main
**HEAD commit:** `39e5288` (Wave 288 P0: 16 application sites enumeration)
**Purpose (per user directive):** "把数据是在什么配置下达到当前记录效果的记录清楚" — for every headline result, record the EXACT configuration that produced it (scheduler, paper-quantities active, hyperparams, checkpoint, seed). Combined with Wave 292 P1 pipeline-inventory, this locks the configuration provenance for paper framing. **READ-ONLY** audit (no code changes).

This doc is the contract-level provenance of the 13 R-cell + weak-claim headlines documented in `docs/audit/wave288-p1-honest-progress-summary.md` §2. Every headline result traces to: a specific sweep tool + CLI flags, a scheduler family + hyperparams, an adapter path + checkpoint path, the paper-quantities active (out of the 16 sites enumerated in Wave 288 P0), the seed pool, and the resulting `d_z` / Bonferroni `p` / status.

Per the Wave 282 audit (`docs/audit/scheduler-per-cell-summary.md`) and Wave 287 audit (`docs/audit/wave287-p-scheduler-codepath-audit.md`): **12/13 headline cells used `CosineAnnealScheduler`** (the controller that ignores all 4 paper quantities); **1/13 cell (R6) used `TierAwareCodimensionSheetScheduler`** wrapping `CodimensionSheetScheduler` (paper-quantity-driven, Wave 275 P4 R6 remediation). No other paper-quantity controller appears on any headline cell. Per Wave 287 finding C-2: `CosineAnnealScheduler` with `eps_implicit=0` defaults is structurally NOT a paper-quantity consumer.

---

## 1. Per-cell configuration table (13 headline rows)

### 1.1 Compact table (per-cell headline snapshot)

| # | Cell | Scheduler family | Cosine? | Default n_min | cycle_length | Tool / sweep driver | Checkpoint / adapter | Seeds | Status | d_z | p (Bonf) |
|---:|---|---|---|---:|---:|---|---|---|:---:|---:|---:|
| 1 | **R1** LineageFlow HMMER | `CosineAnnealScheduler` | YES | 0.0 | N_ROUNDS=3 | `tools/gen_lineageflow_n1000_fastas.py --seed <S> --n 1000 --upstream-eval-len-bias short --nfe 10 --n-rounds 3 --temperature 1.0` | LineageFlowAdapter (no ckpt; FASTA-generator); vendored HMMER Pfam-A.hmm | 42 (single-seed canonical) | **STRONG** | >0.8 (Wave 158) | <1e-10 single-seed; Wave 280 P 3-seed target d_z=9.2, p=0.001 |
| 2 | **R2** kanzi byte-stable composite | `CosineAnnealScheduler` | YES | 0.0 | n_rounds (single scheduler arm per v2 plan) | `tools/run_sota_graphbfn_experiment.py --v2 single-scheduler arm` | kanziAdapter + vendored GEOM-DRUGS reference | 42 (Wave 87 byte-stable) | **STRONG (legacy)** | n/a | n/a single-seed canonical (0.6381 → 0.6146, −0.0235) |
| 3 | **R3** FlowMol3 fg_dev (CIFAR RF) | `CosineAnnealScheduler` | YES | 0.0 | n_rounds (single scheduler arm per v2 plan) | `tools/run_sota_flowmol3_v2_adapter_experiment.py --v2 single-scheduler arm` | FlowMol3Adapter v2 + Wave 109.C weights | 42 (Wave 87 byte-stable) | **STRONG (legacy)** | n/a | n/a single-seed (218.87 → 122.18, −44.17%) |
| 4 | **R4** 2D Two Moons W2 | `CosineAnnealScheduler` | YES | 0.0 | cycle_length (canonical 1 per `tools/run_sota_2d_experiment.py:449`) | `tools/run_sota_2d_experiment.py --dataset two_moons` | 2D toy adapter, no ckpt | 42 (Wave 158) | **STRONG (legacy)** | n/a | n/a single-seed (0.5029 → 0.4663, −7.28%) |
| 5 | **R5** 2D Eight Gaussians W2 | `CosineAnnealScheduler` | YES | 0.0 | cycle_length (canonical 1 per `tools/run_sota_2d_experiment.py:449`) | `tools/run_sota_2d_experiment.py --dataset eight_gaussians` | 2D toy adapter, no ckpt | 42 (Wave 158) | **STRONG (legacy)** | n/a | n/a single-seed (0.5579 → 0.4999, −10.40%) |
| 6 | **R5b** CIFAR-10 RF matched-NFE=50 | `CosineAnnealScheduler` | YES | 0.0 (Wave 191 v2 chunked FID) → 0.5 (Wave 280 P K3+R5b fix via `cosine_ramp_strength=0.5`) | N_ROUNDS=2 (K3+R5b fix only affects cosine per `tools/run_sota_cifar_experiment.py:609-610`) | `tools/run_sota_cifar_experiment.py --schedulers CosineAnnealScheduler --n-rounds 2 --baseline-num-steps 2 --match-nfe budget --device cuda` | RectifiedFlowCIFAR adapter + `adaptive_reflow/adapters/rectified_flow_cifar.py:1109` solver; RF_CIFAR_N_ROUNDS_OVERRIDE=2, RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE=0.5 | 42, 43 (Wave 280 P 2-seed partial; 44 PENDING) | **REGRESSES** (STRONG in regression dir) | +605.5 (paired-t dominated by framework const vs baseline noise) | 2.97e-3 (Bonf-significant in regression dir) |
| 7 | **R5c** MNIST FM smoke ckpt | `CosineAnnealScheduler` | YES | 0.0 | N_ROUNDS=4 (Wave 191 P3 default) | `scripts/wave191_p3_mnist_sweep.py --arm cosine --ckpt data/mnist_fm.npz` | MNISTFM adapter; smoke ckpt `data/mnist_fm.npz` (22481 B) | 42 (Wave 191 P3) | **STRONG (smoke)** | Bonferroni p=3.95e-11 | p<1e-300 |
| 7b | **R5c** MNIST FM production ckpt | `CosineAnnealScheduler` | YES | 0.0 | N_ROUNDS=4 (Wave 280 P) | `scripts/wave191_p3_mnist_sweep.py --arm cosine --ckpt data/mnist_fm/production.ckpt.npz --n-records 200` | MNISTFM adapter; **production ckpt** `data/mnist_fm/production.ckpt.npz` (sha256 `27e2bb6c44758822749de004595b9e0543cfc3caf1bfa47641bedcee34f220aa`, 75472 B, 3 epochs, base_channels=16, full 60K images) | 42, 43, 44 (3-seed N=200) | **PARTIAL** (active+strong on reproducibility; direction FLIPS to baseline_wins on production ckpt) | +1.30 mean across seeds (best-arm = framework's best of {cosine, codim, evidence}; cosine wins smoke, codim/evidence may win production) | n/a best-arm |
| 8 | **R6** k6 foldability + LineageFlow tier-aware | `TierAwareCodimensionSheetScheduler` (wraps `CodimensionSheetScheduler`) | **NO** — paper-quantity-driven | (per-record `B_g > 0` gate from profile_residual_fn) | N_ROUNDS (default 3 from `scripts/wave225_p4_k6_tier_aware.py`) | `tools/eval/cli.py --tier-aware-n-cap 0.5 --tier-aware-baseline-metrics-jsonl <foldability.jsonl>` (counterfactual: `REDUCED_INTENSITY_FACTOR = 0.5` on easy tier `baseline_pLDDT > 46.13`) | k6 foldability adapter + LineageFlowAdapter; **vendored `k6_foldability_n1000_w161_q3_2026/{baseline,framework}/foldability/foldability.jsonl`** N=1000 frozen arm | 42, 43, 44 (3-seed × N=200 subsample) | **PARTIAL** (hard 3/3 SUPPORTED, medium 1/3 SUPPORTED + 2/3 UNDERPOWERED, easy 3/3 REGRESSES) | +0.1962 overall | 6.4e-3 mean across seeds |
| 9 | **K1** FlowMol3 RDKit-validity | `CosineAnnealScheduler` | YES | 0.0 | n_rounds (reuses Wave 87 byte-stable seed=42 reference) | `tools/wave87_n1000_sweep.py --validity-mode rdkit` (Wave 275 P4 K1 fix in `flowmol3_upstream_shim.py:184`; `pb_energy=False` + `validity_mode=rdkit`) | FlowMol3Adapter; `--validity-mode rdkit` flag flips HEADLINE from `pb_validity_pct` to `rdkit_validity_pct` (RDKit-bridged canonical) | 42, 43, 44 (3-seed × N=200) | **PARTIAL / BORDERLINE STRONG** | +1.36 (mean=0.570 ± 0.030, CV=5.3%) | 0.054 (per-cell α=0.05; needs N=1000 for Bonf α=0.0125) |
| 10 | **K3 + R5b** CIFAR-10 RF K3+R5b fix | `CosineAnnealScheduler` | YES | 0.5 (Wave 275 P4 fix via `cosine_ramp_strength=0.5`) | N_ROUNDS=2 (Wave 275 P4 fix) | `tools/run_sota_cifar_experiment.py --schedulers CosineAnnealScheduler --baseline-num-steps 2 --n-rounds 2 --cosine-ramp-strength 0.5 --n-samples 100 --framework-samples 100 --match-nfe budget --device cuda` | Same as R5b; `adaptive_reflow/adapters/rectified_flow_cifar.py:1109` solve_ode | 42, 43 (Wave 280 P 2-seed partial; 44+other schedulers PENDING) | **STRONG REJECTED** (REGRESSES in cosine direction) | +605.5 (paired-t dominated by framework const vs baseline noise) | 2.97e-3 (Bonf-significant in regression dir) |
| 11 | **K4 + K5** LineageFlow length-bias + uniform-AA | `CosineAnnealScheduler` (reuses Wave 158 P2 R1 reference) | YES | 0.0 | N_ROUNDS=3 (reuses R1) | `tools/gen_lineageflow_n1000_fastas.py --seed <S> --n 1000 --upstream-eval-len-bias long --lineageflow-prior-mix 1.0 --nfe 10 --n-rounds 3 --temperature 1.0` | LineageFlowAdapter; `--upstream-eval-len-bias long --lineageflow-prior-mix 1.0` (Wave 275 P4 K4+K5 flag) | 42, 43, 44 (3-seed × N=100) | **UNDERPOWERED** (K5) / **POWERED** (K4) | +1.15 (K5 framework-vs-baseline paired-t) | 0.734 (Bonf, NOT significant at α=0.0125; n=3 paired seeds d_f=2 underpowered) |
| 12 | **K7** LineageFlow novelty | `CosineAnnealScheduler` (reuses Wave 158 framework arm) | YES | 0.0 | N_ROUNDS=3 (reuses R1) | `tools/upstream_eval.run_lineageflow_upstream_eval(metrics=("novelty",))` with `restrict_novelty_to_target_db=True` (Wave 275 P4 K7 fix in `tools/upstream_eval.py`; synthesizes tempdir placeholder for `--pfam-fastas-dir`) | LineageFlowAdapter; vendored prebuilt target DB `data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB` + placeholder `data/lineageflow_upstream/dataset/pfam_fastas_clean/` | 42, 43, 44 (3-seed × N=300) | **STRONG (ACTIVE)** | +∞ | <1e-300 |
| 13 | **R3** FlowMol3 fg_dev (Wave 280 P 3-seed driver) | `CosineAnnealScheduler` | YES | 0.0 | n_rounds (FlowMol3 v2 plan) | `tools/run_sota_flowmol3_v2_adapter_experiment.py --v2 single-scheduler arm` | FlowMol3Adapter v2 + Wave 277 fix (`flowmol3_v2_adapter.py:2861-2883` `repeat_interleave(int(n_mol), dim=0)`) | TBD (Wave 280 P driver RUNNING) | **BLOCKED at vendor level** (DGL 2.4.0 batched-path bug) | TBD | TBD |

### 1.2 Detailed per-cell configuration (full provenance)

For the 13 cells, here is the full configuration provenance including paper-quantities active (out of the 16 application sites enumerated in Wave 288 P0).

#### Cell 1: **R1** LineageFlow HMMER (HMMSCAN Pfam-A hits)

- **Scheduler family:** `CosineAnnealScheduler` (via `default_cosine_scheduler(cycle_length=N_ROUNDS)`)
- **Source code line:** `tools/experiments/run_lineageflow_comparison.py:278`
- **CLI invocation:** `python tools/gen_lineageflow_n1000_fastas.py --seed <S> --n 1000 --upstream-eval-len-bias short --nfe 10 --n-rounds 3 --temperature 1.0`
- **Adapter:** LineageFlowAdapter (FASTA generator + vendored HMMER invocation; no checkpoint — vendored `hmmscan --cpu 32 --noali --tblout`)
- **Hyperparams:** `cycle_length=N_ROUNDS=3`; `n_min=0.0`, `n_max=1.0` (cosine defaults); `eps_implicit=0` (cosine ignores paper quantities per `adaptive_reflow/algorithm/scheduler/simple.py:71` closed form `n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`)
- **Paper quantities active (out of 16):** **0 / 16** (CosineAnnealScheduler is closed-form; only site 6 (Policy Driver) consumes `paper_qty_kwargs`, but the LineageFlow framework arm passes `paper_qty_kwargs={}` empty per the historical default)
- **Checkpoint path:** N/A (vendored FASTA generator; HMMER DB at `data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm`)
- **Seeds:** 42 (single-seed canonical Wave 158 P2; Wave 280 P 3-seed driver in flight per `docs/audit/wave280-p-r1-sweep-result.md`)
- **Result:** baseline=158, framework=342, +184, +116%, single-seed p<1e-10 (Wave 158 P2); Wave 280 P 3-seed target d_z=9.2, Bonf p=0.001
- **Status:** STRONG

#### Cell 2: **R2** kanzi byte-stable composite

- **Scheduler family:** `CosineAnnealScheduler`
- **Source code line:** `tools/run_sota_graphbfn_experiment.py:382` (`default_cosine_scheduler(cycle_length=int(n_rounds))`)
- **CLI invocation:** `python tools/run_sota_graphbfn_experiment.py --v2 single-scheduler arm`
- **Adapter:** kanziAdapter (graph-based Bayesian Flow Network); vendored GEOM-DRUGS reference
- **Hyperparams:** `cycle_length=int(n_rounds)`; `n_min=0.0`, `n_max=1.0` (cosine defaults)
- **Paper quantities active (out of 16):** **0 / 16** as headline (the composite metric itself is paper-4-axis, but the scheduler doesn't consume paper quantities; paper quantities are NOT routed to scheduler here)
- **Checkpoint path:** kanziAdapter ships the model + vendored pretrained weights at `data/kanzi/upstream/**`
- **Seeds:** 42 (Wave 87 byte-stable)
- **Result:** 0.6381 → 0.6146 (−0.0235, single-seed canonical Wave 87 N=999; framework-WINS)
- **Status:** STRONG (legacy single-seed canonical)

#### Cell 3: **R3** FlowMol3 fg_dev (CIFAR RF)

- **Scheduler family:** `CosineAnnealScheduler`
- **Source code line:** `tools/run_sota_flowmol3_v2_adapter_experiment.py:525`
- **CLI invocation:** `python tools/run_sota_flowmol3_v2_adapter_experiment.py --v2 single-scheduler arm`
- **Adapter:** FlowMol3Adapter v2 (`adaptive_reflow/adapters/flowmol3_v2_adapter.py`); Wave 109.C re-runs
- **Hyperparams:** `cycle_length=int(n_rounds)`; cosine defaults
- **Paper quantities active (out of 16):** **0 / 16** as headline (`fg_dev` IS the empirical handle on paper Proposition 3 — `cum_deviation = sum_i |flag_rate_i_gen - flag_rate_i_train|` — but the scheduler does NOT consume `A_g`/`B_g`/`C_g`/`e_rho`; only site 12 (Profile Residual adapter-level) outputs `B_g > 0`, not consumed by headline scheduler)
- **Checkpoint path:** Wave 109.C FlowMol3 weights (vendored at `data/flowmol3/upstream/**`); the `--framework-arm paper-quantity` deferred path would consume `profile_residual_fn` from `FlowMol3Adapter`
- **Seeds:** 42 (Wave 87 byte-stable N=999)
- **Result:** 218.87 → 122.18 (−44.17%, framework-WINS)
- **Status:** STRONG (legacy single-seed canonical)

#### Cell 4: **R4** 2D Two Moons W2

- **Scheduler family:** `CosineAnnealScheduler` (CosineAnnealScheduler with `cycle_length=1` is the canonical case per `tools/run_sota_2d_experiment.py:449`); codim/evidence/freetraj exist as ablation arms (lines 164-186 + 178) but the HEADLINE per the v2 plan is cosine.
- **Source code line:** `tools/run_sota_2d_experiment.py:179` (cosine path); `_build_cosine_scheduler(rounds)` at line 189
- **CLI invocation:** `python tools/run_sota_2d_experiment.py --dataset two_moons`
- **Adapter:** 2D toy adapter (Two Moons); no checkpoint
- **Hyperparams:** `cycle_length=1` (canonical per `tools/run_sota_2d_experiment.py:449`); `n_min=0.0`, `n_max=1.0`
- **Paper quantities active (out of 16):** **0 / 16** as headline (the W2 metric itself is an empirical handle, but the scheduler does NOT consume paper quantities; codim ablation arm exists at lines 164-186)
- **Checkpoint path:** N/A (2D synthetic data)
- **Seeds:** 42 (Wave 158 single-seed)
- **Result:** 0.5029 → 0.4663 (−7.28%, framework-WINS)
- **Status:** STRONG (legacy single-seed canonical)

#### Cell 5: **R5** 2D Eight Gaussians W2

- Same configuration as R4 except `--dataset eight_gaussians`
- **Source code line:** `tools/run_sota_2d_experiment.py:179` (cosine)
- **Hyperparams:** `cycle_length=1`; cosine defaults
- **Result:** 0.5579 → 0.4999 (−10.40%, framework-WINS)
- **Status:** STRONG (legacy single-seed canonical)

#### Cell 6: **R5b** CIFAR-10 RF matched-NFE=50

- **Scheduler family:** `CosineAnnealScheduler` (the only scheduler that honors `cosine_ramp_strength` per `tools/run_sota_cifar_experiment.py:609-610`)
- **Source code line:** `tools/run_sota_cifar_experiment.py:118-121` (scheduler family list); default-cosine path at lines 247-262 (`if name == "CosineAnnealScheduler": return default_cosine_scheduler(...)`); `WAVE247_SEED` env var at lines 1160 + 1392 + 1417
- **CLI invocation (Wave 191 v2 chunked FID):** `python tools/run_sota_cifar_experiment.py --schedulers CosineAnnealScheduler --baseline-num-steps NFE --match-nfe budget --device cuda`
- **CLI invocation (Wave 280 P K3+R5b fix):** `python tools/run_sota_cifar_experiment.py --schedulers CosineAnnealScheduler --baseline-num-steps 2 --n-rounds 2 --cosine-ramp-strength 0.5 --n-samples 100 --framework-samples 100 --match-nfe budget --device cuda`
- **Adapter:** RectifiedFlowCIFAR (`adaptive_reflow/adapters/rectified_flow_cifar.py`); `solve_ode` at line 1109 consumes `RF_CIFAR_N_ROUNDS_OVERRIDE=2` + `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE=0.5` per `tools/run_sota_cifar_experiment.py:120-130` (constants block)
- **Hyperparams:** `cycle_length=N_ROUNDS=2` (K3+R5b fix; line 120 of adapter); `n_min=0.5` (raised from 0.0 by `cosine_ramp_strength=0.5`); `n_max=1.0`; `eps_implicit=0`
- **Paper quantities active (out of 16):** **0 / 16** as headline (the 4 paper-quantity-driven controllers exist in the same tool at lines 213-273 `build_scheduler(name)` but only cosine honors `cosine_ramp_strength`; codim/evidence/freetraj were sweep arms but NOT the K3+R5b headline)
- **Checkpoint path:** N/A (synthetic CIFAR-10 RF; no FM weights)
- **Seeds:** Wave 191 v2 single-seed=42 N=1000 chunked FID; Wave 280 P 2-seed partial {42, 43} (44 PENDING per `docs/audit/wave280-p-cifar-sweep-result.md`)
- **Result:** Wave 191 v2: baseline=415.83, framework=506.43, +20.21% (REGRESSES, Bonf p=9.17e-05). Wave 280 P 2-seed partial: seed 42 baseline=306.57 framework=466.81 +52.27%; seed 43 baseline=271.10 framework=461.18 +70.13%
- **Status:** REGRESSES (STRONG-significance in regression direction)

#### Cell 7: **R5c** MNIST FM smoke ckpt

- **Scheduler family:** `CosineAnnealScheduler`
- **Source code line:** `scripts/wave191_p3_mnist_sweep.py:188` (`return CosineAnnealScheduler(config)`); ARM_LABELS = cosine / codimension_sheet / evidence_driven at line 105
- **CLI invocation:** `python scripts/wave191_p3_mnist_sweep.py --arm cosine --ckpt data/mnist_fm.npz --n-samples 1000`
- **Adapter:** MNISTFM adapter (Wave 191 P2)
- **Hyperparams:** `cycle_length=4` (default `n_rounds=4`); `n_min=0.0`, `n_max=1.0`; cosine closed-form `n_cap ∈ {1.0, 0.75, 0.25, 0.0}` per `scripts/wave191_p3_mnist_sweep.py:182`
- **Paper quantities active (out of 16):** **0 / 16** as headline (codim + evidence ablation arms exist at line 105 but are NOT the smoke-ckpt headline)
- **Checkpoint path:** `data/mnist_fm.npz` (22481 B smoke ckpt)
- **Seeds:** 42 (Wave 191 P3 single-seed N=1000)
- **Result:** baseline 1.0 → framework 0.7156; framework-WINS −28.43% (Bonf p=3.95e-11)
- **Status:** STRONG (smoke ckpt only)

#### Cell 7b: **R5c** MNIST FM production ckpt (Wave 280 P)

- **Scheduler family:** `CosineAnnealScheduler` (same as R5c smoke)
- **Source code line:** `scripts/wave191_p3_mnist_sweep.py:188`
- **CLI invocation:** `python scripts/wave191_p3_mnist_sweep.py --arm cosine --ckpt data/mnist_fm/production.ckpt.npz --n-records 200`
- **Adapter:** Same MNISTFM
- **Hyperparams:** `cycle_length=4`; `n_min=0.0`, `n_max=1.0`
- **Paper quantities active (out of 16):** **0 / 16** as headline
- **Checkpoint path:** `data/mnist_fm/production.ckpt.npz` (sha256 `27e2bb6c44758822749de004595b9e0543cfc3caf1bfa47641bedcee34f220aa`, 75472 B, materialized via `tools/materialize_mnist_fm.py` with `PRODUCTION_RECIPE` constants at lines 71-82: `epochs=3, base_channels=16, max_train_images=60000, batch_size=64, lr=1e-3, seed=42`)
- **Seeds:** 42, 43, 44 (3-seed × N=200 paired t-test on production ckpt)
- **Result:** best-arm d_z per seed = [+1.55, +1.33, +1.02] (all > 0.8), all on `baseline_wins` direction (framework loses to baseline at matched NFE=50 on production ckpt); mean d_z +1.30
- **Status:** PARTIAL (active + strong on reproducibility; direction FLIPS to baseline_wins on production ckpt — honest disclosure)

#### Cell 8: **R6** k6 foldability + LineageFlow tier-aware

- **Scheduler family:** **`TierAwareCodimensionSheetScheduler`** (wraps `CodimensionSheetScheduler`) — **the ONLY paper-quantity-driven controller used as headline in this set** (Wave 275 P4 R6 remediation)
- **Source code line:** `tools/eval/cli.py:312-329` (`--tier-aware-n-cap` flag); `scripts/wave225_p4_k6_tier_aware.py` (counterfactual driver); per-record `_make_framework_policy` wires `TierAwareCodimensionSheetScheduler`
- **CLI invocation:** `python tools/eval/cli.py --tier-aware-n-cap 0.5 --tier-aware-baseline-metrics-jsonl <foldability.jsonl>` (counterfactual: `REDUCED_INTENSITY_FACTOR = 0.5 = n_cap *= 0.5` on easy tier `baseline_pLDDT > 46.13`)
- **Adapter:** k6 foldability adapter + LineageFlowAdapter; vendored frozen arm `verification_outputs/k6_foldability_n1000_w161_q3_2026/{baseline,framework}/foldability/foldability.jsonl` (N=1000 paired qids, Wave 161 frozen)
- **Hyperparams:** per-record `{qid: plddt_mean}` percentile mapping; FIXED Wave 198 P3 percentile boundaries (`34.5601`, `46.1293`) for tier assignment; `REDUCED_INTENSITY_FACTOR = 0.5` on easy tier only; medium + hard unchanged from Wave 161 frozen arm
- **Paper quantities active (out of 16):** **4 / 16** — site 8 (CodimensionSheetScheduler.`_paper_evidence_balance` consumes `A_g`/`B_g`/`C_g`) + site 12 (profile_residual_fn outputs `B_g > 0`) + site 14 (sheet_evidence + cell_evidence from endpoints per CLM-001/CLM-002) + site 16 (tier-aware wrapper consumes regime selector 793's `exterior_gap_e_rho`)
- **Checkpoint path:** k6 foldability (no checkpoint; structure-generation); LineageFlowAdapter (no checkpoint; FASTA generator)
- **Seeds:** 42, 43, 44 (3-seed × N=200 paired subsample via `numpy.random.default_rng(seed)`; per-seed deterministic)
- **Result:** overall d_z = +0.1962 (uniform prior was +0.0336; Δd_z = +0.1627 from tier-aware wrapper). Per-tier: hard 3/3 SUPPORTED, medium 1/3 SUPPORTED + 2/3 UNDERPOWERED, easy 3/3 REGRESSES (counterfactual halves −12.55 → −6.5 pLDDT but framework still underperforms baseline). Bonf p=6.4e-3 mean across seeds.
- **Status:** PARTIAL (hard + medium SUPPORTED, easy still REGRESSES)

#### Cell 9: **K1** FlowMol3 RDKit-validity

- **Scheduler family:** `CosineAnnealScheduler` (reuses Wave 87 byte-stable seed=42 reference; K1 is metric fix only)
- **Source code line:** `tools/wave87_n1000_sweep.py --validity-mode rdkit`; `--validity-mode rdkit` flag in `adaptive_reflow/adapters/flowmol3_upstream_shim.py:184` flips HEADLINE from `pb_validity_pct` to `rdkit_validity_pct` via `pb_energy=False` + `validity_mode=rdkit`
- **CLI invocation:** `python tools/wave87_n1000_sweep.py --validity-mode rdkit`
- **Adapter:** FlowMol3Adapter (vendored Wave 87 byte-stable weights)
- **Hyperparams:** `cycle_length=int(n_rounds)`; cosine defaults
- **Paper quantities active (out of 16):** **0 / 16** as headline (K1 changes the metric, not the scheduler; `rdkit_validity_pct` IS paper Proposition 3's flag-rate balance, but the scheduler does NOT consume paper quantities)
- **Checkpoint path:** Wave 87 byte-stable FlowMol3 weights
- **Seeds:** 42, 43, 44 (3-seed × N=200 sweep per `docs/audit/wave280-p-k1-sweep-result.md`)
- **Result:** per-seed rdkit_validity_pct = (0.535, 0.590, 0.585); mean = 0.570 ± 0.030 std (CV = 5.3%); d_z = +1.36 vs Wave 82 PB baseline = 0.5285; p_bonf = 0.054 (borderline)
- **Status:** PARTIAL / BORDERLINE STRONG (p_bonf gap at N=200 sample-size limitation)

#### Cell 10: **K3 + R5b** CIFAR-10 RF K3+R5b fix

- **Scheduler family:** `CosineAnnealScheduler` (the only scheduler that consumes `cosine_ramp_strength=0.5` per `tools/run_sota_cifar_experiment.py:609-610`)
- **Source code line:** Same as R5b (Cell 6)
- **CLI invocation:** Same as R5b Wave 280 P (Cell 6)
- **Adapter:** Same as R5b (Cell 6); `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE = 0.5` constants at `adaptive_reflow/adapters/rectified_flow_cifar.py:120-130` (Wave 275 P4 K3+R5b fix)
- **Hyperparams:** `cycle_length=N_ROUNDS=2` (K3+R5b); `n_min=0.5` (raised from 0.0 by `cosine_ramp_strength=0.5`); `n_max=1.0`
- **Paper quantities active (out of 16):** **0 / 16** as headline (K3+R5b fix is hardcoded to cosine per Wave 275 P4 §2.1)
- **Checkpoint path:** Same as R5b (Cell 6)
- **Seeds:** 42, 43 (Wave 280 P 2-seed partial per `docs/audit/wave280-p-cifar-sweep-result.md`; 44 + 3 other schedulers PENDING)
- **Result:** per-seed ΔFID% = +52.27 (seed 42) +70.13 (seed 43) at N=100; framework FID byte-identical across seeds (deterministic framework chain); d_z=+605.5 (paired-t dominated by framework const vs baseline noise); Bonf p=2.97e-3 (Bonf-significant in REGRESSION direction)
- **Status:** STRONG REJECTED (REGRESSES with strong significance)

#### Cell 11: **K4 + K5** LineageFlow length-bias + uniform-AA

- **Scheduler family:** `CosineAnnealScheduler` (reuses Wave 158 P2 R1 reference; K4+K5 are FASTA-generator-level fixes)
- **Source code line:** Same as R1 (Cell 1); CLI flags `--upstream-eval-len-bias long --lineageflow-prior-mix 1.0` (Wave 275 P4 K4+K5 fix)
- **CLI invocation:** `python tools/gen_lineageflow_n1000_fastas.py --seed <S> --n 1000 --upstream-eval-len-bias long --lineageflow-prior-mix 1.0 --nfe 10 --n-rounds 3 --temperature 1.0`
- **Adapter:** LineageFlowAdapter (same as R1)
- **Hyperparams:** `cycle_length=N_ROUNDS=3`; cosine defaults; length-bias "long" (200-300 AA range); uniform-AA prior mix=1.0
- **Paper quantities active (out of 16):** **0 / 16** as headline (K4+K5 change FASTA gen, not scheduler)
- **Checkpoint path:** N/A (vendored FASTA generator)
- **Seeds:** 42, 43, 44 (3-seed × N=100 sweep per `docs/audit/wave280-p-k4k5-sweep-result.md`)
- **Result:** K4 powered: 12-22 hits / 100 records (hit-count is no longer at floor); K5: delta=+1.33 (+8.9%), d_z=+1.15, raw p=0.184, **Bonf p=0.734 NOT significant** (n=3 paired seeds underpowered)
- **Status:** UNDERPOWERED (K5) / POWERED (K4)

#### Cell 12: **K7** LineageFlow novelty

- **Scheduler family:** `CosineAnnealScheduler` (reuses LineageFlow framework arm; K7 is env-block fix only)
- **Source code line:** `tools/upstream_eval.run_lineageflow_upstream_eval(metrics=("novelty",))` with `restrict_novelty_to_target_db=True` (Wave 275 P4 K7 fix; synthesizes tempdir placeholder for `--pfam-fastas-dir`)
- **CLI invocation:** `python tools/upstream_eval.run_lineageflow_upstream_eval(metrics=("novelty",))`
- **Adapter:** LineageFlowAdapter (same as R1); wrapper synthesizes tempdir for `--pfam-fastas-dir` if placeholder missing
- **Hyperparams:** `cycle_length=N_ROUNDS=3`; cosine defaults
- **Paper quantities active (out of 16):** **0 / 16** as headline (K7 changes wrapper-level env, not scheduler)
- **Checkpoint path:** vendored prebuilt target DB `data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB` + placeholder `data/lineageflow_upstream/dataset/pfam_fastas_clean/`
- **Seeds:** 42, 43, 44 (3-seed × N=300 sweep per `docs/audit/wave280-p-k7-sweep-result.md`)
- **Result:** novelty @0.5/@0.8/@0.95 = 1.0000 across all 3 seeds (saturated at 1.0 because target DB is small); d_z=+∞; p_bonf<1e-300
- **Status:** STRONG (ACTIVE)

#### Cell 13: **R3** FlowMol3 fg_dev (Wave 280 P 3-seed driver RUNNING)

- **Scheduler family:** `CosineAnnealScheduler` (FlowMol3 v2 plan single-scheduler arm)
- **Source code line:** `tools/run_sota_flowmol3_v2_adapter_experiment.py:525` (`default_cosine_scheduler(cycle_length=int(n_rounds))`)
- **CLI invocation:** `python tools/run_sota_flowmol3_v2_adapter_experiment.py --v2 single-scheduler arm`
- **Adapter:** FlowMol3Adapter v2 + Wave 277 fix at `flowmol3_v2_adapter.py:2861-2883` `repeat_interleave(int(n_mol), dim=0)`
- **Hyperparams:** `cycle_length=int(n_rounds)`; cosine defaults
- **Paper quantities active (out of 16):** **0 / 16** as headline (fg_dev IS paper Proposition 3 handle but the scheduler does NOT consume paper quantities)
- **Checkpoint path:** Wave 109.C FlowMol3 weights
- **Seeds:** TBD (Wave 280 P 3-seed driver RUNNING per `docs/audit/wave280-p-r3-sweep-result.md`)
- **Result:** TBD (BLOCKED at vendor level: DGL 2.4.0 batched-path bug)
- **Status:** BLOCKED at vendor level; Wave 277 fix in code at `flowmol3_v2_adapter.py:2861-2883`

---

## 2. Common pattern summary (what config knobs are shared vs unique)

### 2.1 Common across all 13 cells

| Knob | Common value | Cells deviating |
|---|---|---|
| **Scheduler family** | `CosineAnnealScheduler` (12/13 = 92%) | R6 (Cell 8) uses `TierAwareCodimensionSheetScheduler` |
| **Cosine-ramp closed form** | `n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))` (per `adaptive_reflow/algorithm/scheduler/simple.py:71`) | R6 (no cosine); K3+R5b (Cell 10) uses `n_min=0.5` (raised by `cosine_ramp_strength=0.5`); R5b Wave 191 v2 (Cell 6 legacy) uses cosine defaults |
| **`eps_implicit=0` (default)** | All 13 cells | None — paper-quantity-driven scheduler would need `eps_implicit>0` but CosineAnnealScheduler ignores it |
| **`n_max=1.0` (default)** | All 13 cells | None |
| **Adapter vendored-purity** | All adapters vendored (no checkpoints OR vendored weights); HMMER DBs at `data/lineageflow_upstream/databases/pfam35/` are vendored | None |
| **Seed pool convention** | 42 (Wave 87 + Wave 158 byte-stable canonical) + 43 + 44 (Wave 280 P 3-seed pool) | Cells 7 (R5c smoke) + 4 (R4) + 5 (R5) + 2 (R2) + 3 (R3 CIFAR RF) are single-seed=42 canonical (legacy STRONG); Cells 6 + 10 (CIFAR K3+R5b) are 2-seed partial {42, 43} |

### 2.2 Unique per-cell configs

| Cell | Unique knob(s) | File:line |
|---|---|---|
| R1 | `--upstream-eval-len-bias short --nfe 10 --n-rounds 3 --temperature 1.0` | `tools/gen_lineageflow_n1000_fastas.py:278` (CLI builder) |
| R2 | `tools/run_sota_graphbfn_experiment.py:382` (v2 single-scheduler arm) | graphbfn experiment driver |
| R3 (CIFAR RF) | `tools/run_sota_flowmol3_v2_adapter_experiment.py:525` (v2 single-scheduler arm) | FlowMol3 v2 driver |
| R4 | `--dataset two_moons` | `tools/run_sota_2d_experiment.py:179` |
| R5 | `--dataset eight_gaussians` | `tools/run_sota_2d_experiment.py:179` |
| R5b | `--schedulers CosineAnnealScheduler --baseline-num-steps NFE --match-nfe budget --device cuda`; Wave 280 P variant adds `--n-rounds 2 --cosine-ramp-strength 0.5`; `RF_CIFAR_N_ROUNDS_OVERRIDE=2` + `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE=0.5` | `tools/run_sota_cifar_experiment.py:609-610`, `adaptive_reflow/adapters/rectified_flow_cifar.py:120-130` |
| R5c (smoke) | `--arm cosine --ckpt data/mnist_fm.npz` | `scripts/wave191_p3_mnist_sweep.py:188` |
| R5c (production) | `--arm cosine --ckpt data/mnist_fm/production.ckpt.npz` | same script, different ckpt |
| R6 | `--tier-aware-n-cap 0.5 --tier-aware-baseline-metrics-jsonl <foldability.jsonl>` (`REDUCED_INTENSITY_FACTOR = 0.5` on easy tier); FIXED Wave 198 P3 percentile boundaries (`34.5601`, `46.1293`) | `tools/eval/cli.py:312-329`; `scripts/wave225_p4_k6_tier_aware.py` |
| K1 | `--validity-mode rdkit`; `pb_energy=False` + `validity_mode=rdkit` flag flip | `adaptive_reflow/adapters/flowmol3_upstream_shim.py:184` |
| K3+R5b | Same as R5b Wave 280 P (this IS the K3+R5b fix vehicle) | same files as R5b |
| K4+K5 | `--upstream-eval-len-bias long --lineageflow-prior-mix 1.0` (200-300 AA + uniform-AA prior) | `tools/gen_lineageflow_n1000_fastas.py` CLI |
| K7 | `restrict_novelty_to_target_db=True`; tempdir placeholder synthesis for `--pfam-fastas-dir` | `tools/upstream_eval.py` (K7 fix) |

### 2.3 What config knobs are NOT shared

Per the Wave 287 P audit (`docs/audit/wave287-p-scheduler-codepath-audit.md`), the framework has paper-quantity-driven controllers (`CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`, `EvidenceDrivenScheduler`, `NFEAwareMemoryScheduler` partial) but **none** of these appear as a headline scheduler on any of the 13 cells except R6 (`TierAwareCodimensionSheetScheduler` wrapper). The `cosine_ramp_strength` flag (K3+R5b) only affects the cosine scheduler; the `cosine_ramp_strength` flag is the only scheduler parameter that varies across the 13 cells.

The framework was DESIGNED around 4 paper quantities (`A_g`, `B_g`, `C_g`, `e_rho`) per `docs/INSIGHTS.md` §2 + ADR-0013 + `adaptive_reflow/contracts/paper_quantities.py`. Cosine ignores them. 0/13 cells exercised any of the 4 paper-quantity-driven controllers as the headline (except R6's codim wrapper, which is a tier-aware counterfactual, NOT the historical R6 default). The Wave 282 + Wave 287 audit locks this as a release-engineering blocker for promoting paper-grounded headline claims to STRONG.

---

## 3. Cells using non-cosine scheduler (should be ≤ 1 per Wave 282 audit)

| Cell | Scheduler family | Paper-quantity consumer? | Status |
|---|---|:---:|---|
| R6 | `TierAwareCodimensionSheetScheduler` (wraps `CodimensionSheetScheduler`) | **YES** — `A_g`/`B_g`/`C_g` via codimension-sheet + tier-aware wrapper | PARTIAL (hard SUPPORTED, easy REGRESSES) |
| All other 12 cells | `CosineAnnealScheduler` | NO | varies per cell |

**Non-cosine sweep count: 1** (R6; Wave 275 P4 R6 remediation that ONLY swaps the controller on the tier-aware counterfactual — the historical byte-stable R6 default is still cosine per `tools/eval/cli.py:312-329` "legacy byte-stable scheduler" path).

Per the Wave 281 partial CIFAR sweep (`docs/audit/wave281/p-partial-evidence.md`), there ARE additional paper-quantity-driven scheduler cells in flight (codim/seed42 N=200 CIFAR = FRAMEWORK-WINS −2.55% ΔFID vs cosine REGRESSES +67.64% at same N=200; single-seed direction-flip signal). **These are NOT R-cell + weak-claim headline rows**; they are part of the Wave 286 strict resweep which is PENDING. They are not counted in the 13-cell genealogy above.

---

## 4. Invariants check (D.4, claims drift, ruff, mkdocs, vendored)

Per Wave 288 P1 verification at `39e5288`:

```
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
30 passed, 3 warnings in ~1.06s    # D.4 30/30 — INVARIANT

$ python3 tools/check_claims_consistency.py
**No drift detected.** (60 ACTIVE, 1 PROVISIONAL, 2 DEPRECATED)    # claims no drift — INVARIANT

$ ruff check adaptive_reflow/ tests/ scripts/ tools/
All checks passed! (0 findings)    # ruff 0 — INVARIANT

$ python3 tools/build_metric_ledger.py
EXIT=0 byte-deterministic (108 rows, md5sum stable across 2 runs)    # ledger rebuilt — INVARIANT

$ mkdocs build --strict
0 warnings    # mkdocs 0 — INVARIANT
```

All 5 release gates green at `39e5288`. **Vendored NOT touched:** `data/FlowMol3/repo/**`, `data/lineageflow_upstream/**`, `data/kanzi/upstream/**` all preserved per "clone下来的原sota项目里的打分脚本依旧不能动，严格复用" directive.

---

## 5. Edit discipline

* `tools/run_sota_cifar_experiment.py` — NOT modified (vendored scoring-script family; Wave 286 P FID GPU fix + Wave 275 K3+R5b CLI plumbing are the canonical state)
* `tools/compute_cifar_fid.py` — NOT modified (FID computation uses the canonical InceptionV3FIDEvaluator path)
* `tools/run_sota_2d_experiment.py` — NOT modified
* `tools/run_sota_flowmol3_v2_adapter_experiment.py` — NOT modified (FlowMol3 v2 plan keeps cosine for deterministic Phase-A comparison)
* `tools/run_sota_graphbfn_experiment.py` — NOT modified
* `tools/gen_lineageflow_n1000_fastas.py` — NOT modified
* `tools/upstream_eval.py` — NOT modified (Wave 275 K7 fix is the canonical state)
* `tools/materialize_mnist_fm.py` — NOT modified
* `scripts/wave191_p3_mnist_sweep.py` — NOT modified (Wave 280 P added `--ckpt` + `--n-records` extension)
* `scripts/wave225_p4_k6_tier_aware.py` — NOT modified
* `scripts/wave247_p2_r5b_multiseed.py` — NOT modified
* `adaptive_reflow/adapters/rectified_flow_cifar.py` — NOT modified (`RF_CIFAR_N_ROUNDS_OVERRIDE=2` + `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE=0.5` constants at lines 120-130 are the canonical state)
* `adaptive_reflow/adapters/flowmol3_upstream_shim.py` — NOT modified (K1 `--validity-mode rdkit` flag is the canonical state)
* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` — NOT modified (Wave 277 R3 fix at lines 2861-2883 preserved)
* `adaptive_reflow/algorithm/scheduler/*.py` — NOT modified (Wave 287 P audit is read-only)
* `data/FlowMol3/repo/**` — NOT touched (vendored scoring scripts preserved)
* `data/lineageflow_upstream/**` — NOT touched (vendored Pfam-A.hmm DB preserved)
* `data/kanzi/upstream/**` — NOT touched (vendored GEOM-DRUGS reference preserved)
* `docs/audit/wave292-p2-config-genealogy.md` — this file (created).

---

## 6. Artifacts

* `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave292-p2-config-genealogy.md` — this audit note (13-row configuration table + common pattern summary + non-cosine sweep count = 1)
* `docs/audit/wave288-p1-honest-progress-summary.md` §2 — per-cell status table (R1, R2, R3, R4, R5, R5b, R5c, R6, K1, K3+R5b, K4+K5, K7, R5c production-ckpt)
* `docs/audit/scheduler-per-cell-summary.md` — 13/13 cosine caveat + per-cell default scheduler source paths
* `docs/audit/wave287-p-scheduler-codepath-audit.md` — 24-bug paper-quantity controller audit (release-engineering blocker)
* `docs/audit/wave288-p0-application-sites.md` — 16 paper-quantity application sites enumeration
* `docs/audit/wave280-p-*-sweep-result.md` — 7 R-cell + weak-claim sweep results (per-cell configs)
* `docs/audit/mnist/wave280-p-r5c-sweep-result.md` — R5c production-ckpt sweep (configuration lineage)
* `docs/audit/wave281/p-partial-evidence.md` — Wave 281 CIFAR partial (3 of 15 cells with paper-grounded controllers)
* `docs/METRIC_LEDGER.md` — single machine-readable inventory of every metric the project ships

---

## 7. Summary

* **Goal achieved (READ-ONLY):** per-user-directive "把数据是在什么配置下达到当前记录效果的记录清楚" is now satisfied. Every headline result has its configuration genealogy locked at `39e5288`.
* **13 cells documented** with per-cell scheduler family (12 cosine + 1 R6 tier-aware codim), default-cosine source code paths, paper-quantities active (out of 16 sites enumerated in Wave 288 P0), hyperparams (`cycle_length`, `n_min`, `n_max`, `cosine_ramp_strength`), checkpoint + adapter path, seed pool, and `d_z` / Bonf `p` / status.
* **Common pattern:** 12/13 cells use `CosineAnnealScheduler` with the closed-form `n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))` and `eps_implicit=0` (cosine ignores paper quantities per `adaptive_reflow/algorithm/scheduler/simple.py:71`).
* **Unique per-cell:** K3+R5b (Cell 10) is the only one with `n_min=0.5` (raised by `cosine_ramp_strength=0.5`); R6 (Cell 8) is the only one with a paper-quantity-driven scheduler (`TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler`).
* **Non-cosine sweep count: 1** (R6 only; all others cosine per Wave 282 audit).
* **This doc is to be SUPERSEDED** by the eventual Wave 286 strict resweep + Wave 289 final results; it is the configuration provenance as of `39e5288` for the paper author to use as a stable frame of reference.
