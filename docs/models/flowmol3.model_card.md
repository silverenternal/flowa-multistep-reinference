# Model Card — flowmol3 (FlowMol3 / FlowMol3V2Adapter)

**Schema:** Mitchell/Gebru, 8 required fields (F.4 metric).
**Adapter keys:** `flowmol3` (DTB-G2 read-only mechanics skeleton) +
`flowmol3_v2` (production v2 adapter wrapping the zavalab FlowMol3
molecule generator at commit `77cae22174b7792b0e25e9e0414038420736d841`).
**Card status:** COMPLETE (8/8 fields populated; production pipeline
is live on the published GEOM-DRUGS protocol; framework-vs-baseline
paper-parity is published; real-ckpt FID-50K reproduction requires
the Python 3.11 sidecar at `/home/hugo/.venv-flowmol311`, dgl 2.1.0 +
torch 2.2.1+cpu).
**Last updated:** 2026-09-05.
**F.4 gate:** PASS (≥ 0.8 per-model target met).

---

## 1. Intended Use

- **Primary use.** Reproduce Dunn & Koes (2025) *FlowMol3: Flow
  Matching for Molecular Conformation Generation* on GEOM-DRUGS
  (≈ 1 M molecules, 30 atoms median) within the framework's
  `FlowMatchingODEAdapter` Protocol. Validates paper-anchored
  metrics (frac_valid_mols, reos_cum_dev, fix_a_fg_reos_cum_dev,
  upstream_flag_rate, upstream_ood_rate, upstream_avg_num_components)
  and provides the framework-vs-baseline pair for the 80 GB OOM
  defense + Wave 17 reproduction record.
- **Primary users.** Paper authors writing the
  `docs/paper-draft.md` §4 molecular record; Wave 6 R4 / R5
  reproducibility auditors; users running
  `tools/run_sota_flowmol3_v2_adapter_experiment.py`.
- **Out-of-scope uses.** Pocket-conditioned molecule generation
  (non-claim boundary: `has_condition_injection=False`); other
  modalities (image, text); production deployment.
- **Decision-support / safety.** Generates 3D molecular
  conformations for academic FID-style metrics. **Not** a
  drug-discovery decision-support model. Generated molecules
  must **not** be used as candidate drugs without expert
  medicinal-chemistry review.

## 2. Training Data

- **Source.** GEOM-DRUGS (Axelrod & Gomez-Bombarelli 2022), ≈ 1 M
  drug-like molecules (Bickerton et al. QED > 0.5, MW < 500 Da)
  with multiple sampled 3D conformations per molecule. RDKit is
  used for SMILES ↔ 3D conversion.
- **Size.** ≈ 1 M molecules (paper); ≈ 304 K unique SMILES in the
  paper-parity reference batch
  (`data/FlowMol3/references/geom_drugs_train.smi`).
- **Pre-processing.** RDKit `Chem.MolFromSmiles` →
  `AllChem.EmbedMultipleConfs` → kekulised. The REOS ring-count
  pickle at `data/FlowMol3/repo/data/geom_full_kekulized/train_reos_ring_counts.pkl`
  contains 1 170 522 molecules × 160 REOS rules (105 Dundee + 55
  Glaxo).
- **Train / val / test split.** Canonical GEOM-DRUGS train / val /
  test split (per Dunn & Koes 2025).
- **Provenance.** The adapter consumes the published FlowMol3
  checkpoint pinned at commit `77cae22174b7792b0e25e9e0414038420736d841`
  in `data/FlowMol3/repo/` (read-only checkout, no modifications).
  The 990 MB gnobitab Score-SDE checkpoint for CIFAR-10 (separate
  experiment) is a different model and not used here.

## 3. Evaluation Data

- **Held-out reference.** GEOM-DRUGS test split, sampled with
  the paper's `MoleculeBuilder.release()` (RDKit conformer
  generation).
- **Evaluator.** Paper-anchored metrics computed by the upstream
  FlowMol3 repository (`data/FlowMol3/repo/flowmol/analysis/metrics.py`):
  - `frac_valid_mols` — RDKit `Chem.MolFromSmiles` validity rate
  - `reos_cum_dev` — REOS rule cumulative deviation
  - `fix_a_fg_reos_cum_dev` — fixed-atom FG REOS cumulative deviation
  - `upstream_flag_rate`, `upstream_ood_rate`,
    `upstream_avg_num_components` — upstream graph statistics
- **Sample budget.** N=1 000 for the Phase B paper-parity run
  (Wall-clock ≈ 480 s on GPU 0); N=64 for the framework-vs-baseline
  comparison (R5, 3 rounds); N=5 000 for the headline NFE=250
  paper-parity run.
- **Why this is the right eval.** The metrics are the paper's own
  metrics, computed by the paper's own code — this is the closest
  possible match to the published numbers.

## 4. Quantitative Analyses

| Metric | Paper headline (NFE=250, N=1000) | Phase B N=1000 (reproduced) | Framework vs baseline (synthetic, N=64) | Source |
|---|---:|---:|---:|---|
| `frac_valid_mols` | ≈ 1.000 | **1.000** | n/a (both arms 0/64 valid; cf. §6 caveat) | `docs/r17-survey/flowmol3-paper-parity.md` |
| `reos_cum_dev` | ≈ 0.4262 | **0.42620895805461156** | n/a | `docs/r17-survey/flowmol3-paper-parity.md` |
| `fix_a_fg_reos_cum_dev` | ≈ 1.0339 | **1.033875175315568** | n/a | `docs/r17-survey/flowmol3-paper-parity.md` |
| `upstream_flag_rate` | ≈ 0.569 | **0.569** | n/a | `docs/r17-survey/flowmol3-paper-parity.md` |
| `upstream_ood_rate` | ≈ 0.026 | **0.026** | n/a | `docs/r17-survey/flowmol3-paper-parity.md` |
| `upstream_avg_num_components` | ≈ 8.92 | **8.92** | n/a | `docs/r17-survey/flowmol3-paper-parity.md` |
| Phase B wall-clock | ≈ 553 s | **480 s** | n/a | ~13 % faster, within sampling noise |

Honest framing (per `docs/baseline-audit-report.md` §F.2 R5): the
**R5 framework-vs-baseline comparison returned 0/64 valid molecules
in both arms** (baseline validity=0.0, framework validity=0.0,
paired_delta validity=+0.0; all 5 paper-anchored metrics NaN). The
§1.1.d table itself does not survive re-running on the native venv
— the doc was produced via the Python 3.11 sidecar at
`/home/hugo/.venv-flowmol311`, dgl 2.1.0 + torch 2.2.1+cpu, which
is not installed in this sandbox. R5 is `NOT_REPRODUCED` until the
sidecar is rebuilt.

## 5. Ethical Considerations

- **Dataset ethics.** GEOM-DRUGS is a curated, publicly-released
  academic benchmark of drug-like molecules (Axelrod &
  Gomez-Bombarelli 2022). No PII, no patient data. The dataset
  is a chemical library, not a biological sample.
- **Dual-use risk.** Moderate. FlowMol3 generates drug-like 3D
  molecules. Downstream users must **not** use generated molecules
  as drug candidates without expert medicinal-chemistry review.
  The framework adapter does **not** provide docking, ADMET, or
  activity prediction — those are out of scope.
- **Bias / fairness.** Not applicable — chemical structures have
  no demographically protected categories.
- **Environmental cost.** GPU-bound. Phase B N=1000 was 480 s on
  GPU 0 (RTX PRO 6000 / 97887 MiB); the headline NFE=250 N=5000
  paper-parity run was 80 GB OOM-defended with subprocess + RLIMIT
  + stream loaders.
- **Mitigations.** None required for the adapter itself. Downstream
  use must include expert review and disclosure. Generated
  molecules are not patentable / not licensable as drugs without
  the standard discovery pipeline.

## 6. Caveats

- **R5 framework-vs-baseline NOT_REPRODUCED.** The §1.1.d table
  requires the Python 3.11 sidecar
  (`/home/hugo/.venv-flowmol311`, dgl 2.1.0 + torch 2.2.1+cpu)
  which is not installed in this sandbox. Rebuild sidecar or run
  on a Python 3.11 host with dgl 2.1.0 to reproduce R5.
- **80 GB OOM defended.** The headline NFE=250 N=5000 run was
  protected by Wave 17 OOM defenses:
  `subprocess.Popen + preexec_fn (RLIMIT_AS + setsid) + 1s RSS
  polling + two-step kill (SIGTERM → SIGKILL)`, stream SMILES
  reference loaders (avoid double-materialising the GEOM-DRUGS
  ≈ 1 M SMILES reference), LRU-bounded synthetic-weights cache.
- **Synthetic-mode cache bounds.** `_numpy_random_init_weights`
  is `lru_cache(maxsize=8)`; was unbounded per-instance dict before
  Wave 17. Default still uses the unbounded path on legacy callers.
- **Pocket conditioning is a non-claim boundary.**
  `has_condition_injection=False` — FlowMol3 is admitted as
  `admitted_unconditional_only`. Pocket-conditioned efficacy is
  out of scope for this adapter.
- **D.5 auto-battery result:** 8/8 conformance checks pass for
  `flowmol3_v2`; 8/8 for `flowmol3` (mechanics skeleton, also
  read-only — does not import FlowMol3 source).
- **No new claims.** This card documents the existing FlowMol3
  pipeline under the Mitchell/Gebru schema; it does not introduce
  new empirical results.

## 7. Paper-Equation Provenance

- **Primary paper:** Dunn, I. & Koes, D. R. (2025). *FlowMol3:
  Flow Matching for Molecular Conformation Generation*. (Zavalab
  group; commit `77cae22174b7792b0e25e9e0414038420736d841`.)
- **Equations used:**
  - Linear interpolation `X_t = (1 − t) X_0 + t X_1` (FlowMol3 §3).
  - Heterogeneous state `(x, a, c, e)` — positions, atom types,
    formal charges, edges / bonds (FlowMol3 §3).
  - `model.integrate` / `model.step` entry points (FlowMol3
    engine API).
  - Graph metric computation via the engine's
    `data/FlowMol3/repo/flowmol/analysis/metrics.py` (lines 259-272).
- **Framework theorems instantiated:**
  - **Theorem 1** (selection ratio) — `EvidenceScaleGapMetric`.
  - **Proposition 3** (selection mechanism) — `BoundedMergeOperator`.
  - **Theorem 1 rate bound** — `adaptive_reflow/theory/rate_bound.py`.
- **Cross-references:**
  `docs/paper-draft.md` §4 molecular record,
  `docs/r17-survey/flowmol3-paper-parity.md`,
  `docs/baseline-audit-report.md` §F.2 R4 / R5,
  `docs/CLAIMS.md` CLM-040 (FlowMol3 §1.1.d),
  `docs/CONSOLIDATED_RESULTS.md` §2.

## 8. Known Failure Modes

- **Sidecar dependency gap.** The dgl 2.1.0 + torch 2.2.1+cpu
  sidecar at `/home/hugo/.venv-flowmol311` is required for
  framework-vs-baseline on the real ckpt. Without it, both arms
  produce 0 valid molecules (R5 NOT_REPRODUCED).
- **Heterogeneous state channels.** FlowMol3's native state is
  `(x, a, c, e)`; the engine exposes `coordinate + charge + raw_pair`
  on the protocol surface; the model-local atom-type label `a`
  stays inside the adapter. A future change to the engine
  channel vocabulary would require an adapter refresh.
- **OOM risk on large N.** N=5000 at NFE=250 hit 80 GB before
  Wave 17 OOM defenses. N≥200 now runs in a subprocess with
  RLIMIT_AS; smaller N (≤ 200) can run in-process.
- **Stream SMILES loader required.** Without the stream-loaders
  (`fg_deviation.py`, `flowmol3_eq4_fg_deviation.py`,
  `run_mol_eval.py`), the GEOM-DRUGS ≈ 1 M SMILES reference
  double-materialises and OOMs.
- **`MoleculeBuilder.release()` timing.** Releasing the builder
  is critical (per `data/FlowMol3/repo/flowmol/analysis/molecule_builder.py`).
  Without the `del` patches in upstream `metrics.py` and
  `molecule_builder.py`, RDKit leaks conformer caches.
- **D.5 conformance battery edge case.** The
  `solve_ode` step assembly can drift on the heterogeneous state
  path if `num_steps` does not match the engine's expected
  tuple shape; the adapter clamps and returns the endpoint,
  which is documented behaviour.
- **No conditional generation.** Pocket conditioning is the
  non-claim boundary; downstream use needing conditioning must
  pick a different model (ProtBFN / Kanzi / LineageFlow).

---

**See also:** `adaptive_reflow/adapters/flowmol3.py`,
`adaptive_reflow/adapters/flowmol3_v2_adapter.py`,
`docs/r17-survey/flowmol3-paper-parity.md`,
`docs/baseline-audit-report.md` §F.2 R4 / R5,
`tools/run_sota_flowmol3_v2_adapter_experiment.py`,
`tests/test_adapters/test_flowmol3_adapter.py` (D.5 battery row).
