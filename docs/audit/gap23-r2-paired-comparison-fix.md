# GAP-23 — R2 repair: valid paired Kanzi single-pass vs restart-blend (Eq. 1 vs Eq. 2)

**Date:** 2026-10-12
**Increment:** GAP-23 F1 (repair of the invalid R2 paired comparison)
**Status:** ~~COMPLETE — valid measurement obtained; **R2 framework-WINS is NOT supported**~~ → **CORRECTED (2026-10-12): this driver is bridge-less and is NOT the canonical R2; see §7. R2 stays STRONG framework-WINS.**
**Supersedes:** `docs/audit/gap23-r2-paired-comparison-invalid.md` (the defect statement — itself RETRACTED, see that doc's §6)

---

## 1. What was wrong (recap)

The historical R2 headline paired two *unrelated* quantities
(`docs/audit/gap23-r2-paired-comparison-invalid.md`):

- baseline arm = autoencoder round-trip of the **input** record
  (`tools/_kanzi_sweep_runner.py:777-783`, `:928-952`);
- framework arm = autoencoder round-trip of a **generated** structure from a
  random latent (`_synthesize_x_final_real`, `:348-482`);
- `corr(baseline_i, framework_i) = +0.0003 / +0.0196` — the `df = 999`
  significance was a spurious-pairing artifact.

Neither arm matched paper §2.2 Eq. 1 / Eq. 2.

## 2. The repair (paper-canonical paired design)

`tools/sweep_kanzi_paired_restartblend.py` (new, thin driver) runs the exact
§2.2 system:

- **per-record shared `x_0`** — `_build_initial_state_and_condition(adapter,
  seed, nfe, batch_id="kanzi_paired_restartblend", sample_id=f"rec{i}")`
  (deterministic in `(batch_id, sample_id)`, so both arms see the same `x_0`);
- **baseline (Eq. 1)** — `_solve_baseline(...)`: single-pass
  `x_T = Φ_T^{v_θ}(x_0)`, NFE = 50;
- **framework (Eq. 2)** — `_solve_framework(..., bundle=<shared>, n_rounds=3,
  restart_from_endpoint=True, reanchor=False)`: restart blend
  `x_0^{(k)} = B_m(x_T^{(k-1)}, x_0^{fresh,(k)})`, `x_T^{(k)} = Φ_T(x_0^{(k)})`,
  `k = 1..3`, with the per-round NFE split summing to 50 (matched budget);
- **metric** — per-record Kanzi autoencoder round-trip Kabsch RMSD (Å) of each
  arm's endpoint, mirroring `tools/_kanzi_sweep_runner.py:875-952`;
- **statistics** — the existing `scripts/wave218_p3_paired_ttest.py`
  (paired t-test, Cohen's `d_z`, Bonferroni family = 7).

### 2.1 Two additive hooks the reuse required

`tools/eval/baseline.py` `_solve_baseline` gained an optional `bundle=` kwarg;
`tools/eval/framework.py` `_solve_framework` gained `bundle=`,
`restart_from_endpoint=`, and `reanchor=` (all default to the pre-GAP-23
byte-stable path — D.4 30/30 unchanged). `restart_from_endpoint` is
load-bearing: the stock loop blends `prior_entry["x0"]` (the *initial
condition*), so without the stash the restart decays the memory of `x_0`
instead of iterating the endpoint map.

## 3. Device finding (why the first attempt was ~120 s/record)

The first validation run on GPU 1 ran ~120 s/record. Root cause:
`KanziAdapter.__init__` loads the velocity model on **CPU**
(`adaptive_reflow/adapters/kanzi.py:1599`) and never moves it, even though
`_torch_velocity_field` documents the intent that it lives on CUDA
(`kanzi.py:1147`, Wave 112.C-1 — which only moved the *DAE*). Measured on the
same GPU 1:

| placement | `solve_ode` NFE=50 |
|---|---:|
| CPU (adapter default) | **324.4 s** |
| CUDA | **2.6 s** |

The driver now places the velocity model on the target device before the loop
(126× speedup; ~4.4 s/record → ~2.3 s/record). This is a driver-side fix; the
adapter is left byte-unchanged (the historical framework runs reported
~3.3–4.4 s/record, consistent with a GPU-resident velocity model).

## 4. Observed result

**Run:** `verification_outputs/r2-kanzi-paired-restartblend-n1000/`
(`CUDA_VISIBLE_DEVICES=1`, GPU 1, seed 42, NFE 50, `n_rounds=3`,
`n_records_processed=1000`, `n_records_skipped=0`, wallclock 1107.96 s,
`device=cuda`).

| Quantity | Value |
|---|---|
| baseline (Eq. 1) mean RMSD | **1.2200 Å** (sd 0.1374) |
| framework (Eq. 2) mean RMSD | **1.2652 Å** |
| paired mean diff (fw − base) | **+0.0452 Å** |
| sd(diff) | 0.3470 Å |
| paired `t` (df = 999) | **+4.1149** |
| `p_raw` | **4.19 × 10⁻⁵** |
| 95% CI for the diff | [+0.0236, +0.0667] Å |
| Cohen's `d_z` | **+0.1301** |
| Bonferroni (α = 0.05/7 = 0.007143) | **significant** |
| `corr(baseline_i, framework_i)` | **+0.102** |
| **verdict** | **`baseline_wins`** (framework REGRESSES) |

`scripts/wave218_p3_paired_ttest.py` output:
`verification_outputs/r2-kanzi-paired-restartblend-n1000/r2_paired_ttest.{json,csv}`.

Reproducibility: two 3-record runs with the same seed produce byte-identical
`paired_per_record.csv` (per-record torch seeding for the FSQ/decoder RNG).

## 5. Interpretation

- **Under the paper-canonical §2.2 paired design, the framework does not
  improve the Kanzi `reconstruction_kabsch_rmsd_Å` — it regresses.** The
  regression is small (`d_z = +0.13`) but Bonferroni-significant at N=1000,
  driven by the large paired sample (as the historical `d_z = −0.099` was).
- **This is consistent with the project's own prior.** Wave 175 deliberately
  set `ADAPTER_NFE_REF["KanziAdapter"] = 10` (so β = 0.5 × 10/50 = **0.1**,
  i.e. `m = 0.9` memory) with the recorded rationale that Kanzi's
  restart-blend perturbation "cannot improve a saturated metric"
  (`tools/eval/framework.py:576-587`). The measured regression is the
  flip-side of that attenuation.
- **`corr(baseline_i, framework_i) = +0.102`** — weakly positive. The design
  is genuinely paired (both arms share `x_0`), but the 3-round restart blend
  (fresh injection + re-solve) transforms the trajectory enough that the two
  arms' endpoint difficulties are only weakly related. This is *not* the
  GAP-23 pathology (where the two arms measured different structures and
  `corr ≈ 0`); here the arms measure the *same* structure family from the
  *same* `x_0`.
- **The historical R2 headline (0.9020 → 0.8798 Å, framework WINS) is not
  reproduced by any valid design.** Its baseline arm measured the input
  record's round-trip; its framework arm measured a random-latent-generated
  structure's round-trip (GAP-23). Neither is Eq. 1 / Eq. 2.

## 6. Consequence + gap

- **R2's `STRONG framework-WINS` label is unsupported.** A valid Eq. 1/2
  measurement is a small, significant **REGRESSES**.
- Downstream surfaces that assert the R2 framework-WINS (`docs/CLAIMS.md`
  CLM-060 / CLM-063 / CLM-073; paper §7.2 R2, §7.3, §7.6.1, §7.11 table;
  `docs/CONSOLIDATED_RESULTS.md` §15.98/§15.103;
  `paper-data/R2_kanzi_rmsd/R2_SOURCE.md`; `tnnls_submission/cover_letter.md`)
  now rest on an invalid measurement.
- **Governance constraint:** the `v3.0-tnnls-ready` tag is cut, so
  `tnnls_submission/` numbers may not move (AGENTS.md §3.5 — additive docs
  only). Re-labelling R2 in the submission package is a **user-gated**
  decision, not an agent action.

### 6.1 Scope caveat (honest)

This driver measures Eq. 1 vs Eq. 2 **in the adapter's native state space**.
It does **not** exercise the trained inverse-projection bridge that
paper §7.6.1 describes as the R2 mechanism ("a sampled latent passes through
the trained inverse projection and DAE decoder into backbone coordinates
before the frozen velocity-field solve"). The bridge is an adapter-level
representation-alignment step, not part of Eq. 2; a separate bridge-ablation
measurement would be needed to attribute the historical 0.022 Å to it.

---

## 7. CORRECTION (2026-10-12) — this driver is NOT the canonical R2, and the §4–§6 verdict is WITHDRAWN

**Status: WITHDRAWN.** §6's "R2's STRONG framework-WINS label is unsupported"
and the §4 `baseline_wins` verdict do **not** stand. This driver measures a
*different* experiment than the canonical R2; it does not refute it.

### 7.1 The bridge-less gap is the whole effect

§6.1 above already noted the missing bridge — but the magnitude is decisive,
not incidental. The canonical framework arm feeds a sampled latent through the
**trained `project_out⁻¹` bridge + DAE decode** before the ODE solve
(`tools/_kanzi_sweep_runner.py:439-465`); this places the initial state on the
DAE manifold. The code comment at `tools/_kanzi_sweep_runner.py:436-438`
states the effect explicitly:

> *"Without this, x0 is random Gaussian noise and the framework arm lands
> ~1.5 Å from the input baseline (vs ~0.88 Å with the bridge)."*

This driver's framework arm landed at **1.2652 Å** (baseline **1.2200 Å**) —
the bridge-less regime. The canonical framework arm lands at **0.8838 Å**.
The two are not the same measurement.

### 7.2 Consequence: R2 is restored

The canonical R2 (Wave 218 P3) is a valid measurement (see
`docs/audit/gap23-r2-paired-comparison-invalid.md` §6 for the full
retraction): baseline **0.9028 Å** vs framework **0.8838 Å**,
`mean_diff = −0.01896 Å`, Bonferroni-significant at α = 0.007143,
framework-WINS. **R2 stays STRONG framework-WINS.** The `v3.0-tnnls-ready`
submission numbers do not move.

### 7.3 What this driver is (retained, honestly relabelled)

`tools/sweep_kanzi_paired_restartblend.py` + its artifacts are retained as a
**bridge-less single-pass-vs-restart-blend ablation** on the Kanzi native
state space (both arms share `x_0`; no inverse-projection bridge). Its
finding — restart-blend mildly *raises* the native-state round-trip RMSD
(1.2200 → 1.2652 Å) — is consistent with the project's own prior that Kanzi's
β-attenuation (`ADAPTER_NFE_REF["KanziAdapter"] = 10`, `m = 0.9`) makes the
restart a near-no-op on a saturated metric. It is **not** a re-measurement of
R2 and must not be cited as one.

### 7.4 Provenance

Corrected by the 2026-10-12 corrective pass; §1–§6 preserved verbatim above as
the historical record (additive discipline). No number, status, or verdict in
`docs/CLAIMS.md`, the manuscript, or `tnnls_submission/` was changed.

