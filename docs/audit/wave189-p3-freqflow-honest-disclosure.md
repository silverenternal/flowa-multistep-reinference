# Wave 189 P3 — FreqFlow honest-disclosure audit

**Date:** 2026-09-18
**Branch:** main
**Commit:** (this commit)
**Scope:** Disclose the state of the FreqFlow axis on the paper's
"5 adapters" claim, and supplement it with a synthetic-mode sweep that
gives a real (non-FID) number the paper can cite while flagging its
provenance.

Per the Wave 189 P3 user directive ("不，我们不降级，差什么东西就直接补，启动
ultracode来做" / "No, we don't downgrade, just supplement what's missing,
launch ultracode to do it"), this audit does NOT skip the FreqFlow
result row. It runs the synthetic sweep to give a non-trivial number
and pairs it with an explicit honest-disclosure block.

---

## 1. Verdict (TL;DR)

| Item | Verdict |
|---|---|
| Real FreqFlow checkpoint exists? | **NO** — no public release as of 2026-09-05. |
| Adapter shipped? | **YES** — `adaptive_reflow/adapters/freqflow.py` (1 562 LOC), synthetic-mode Protocol surface. |
| Adapter D.5 conformance? | **PASS** — synthetic-mode coverage (8 checks). |
| Adapter torch-mode (`force_mode="torch"`) usable? | **NO** — degrades in-constructor to synthetic when no ckpt is on disk (deliberate, see FreqFlowAdapter §6 C3). |
| `tools.eval.io.DOWNSTREAM_METRICS["freqflow"]` metric | **DEFERRED_no_upstream_ckpt** (Phase-4 deferred registry). |
| Can we report a real FreqFlow FID? | **NO** — there is no checkpoint to forward through. |
| Can we report any FreqFlow number? | **YES** — but it must be flagged as synthetic-shim, not real. |
| Paper "5 adapters" claim status | **Partially synthetic** on the image axis — see §5. |

---

## 2. Why no real checkpoint exists

Probed 2026-09-05 from the GPU host (network reachable; `github.com`
returned HTTP 200 — this is a genuine absence, not a sandbox block):

| Probe | Result |
|---|---|
| `api.github.com/repos/OliverRensu/FreqFlow` | 200 — repo exists, public |
| `.../releases` | `[]` — no release assets |
| Recursive git tree of `main` | 23 files: code + `figs/img.png`. No `.pth`, no `.safetensors`, no LFS pointer |
| `huggingface.co/api/models?search=FreqFlow` | `[]` |
| `huggingface.co/api/models?search=Frequency-Aware Flow Matching` | `[]` |
| `huggingface.co/api/models?search=nnet_ema` | `[]` |
| `huggingface.co/api/models?author=OliverRensu` | `[]` — no HF account |

The upstream README's inference recipe reads
`--nnet_path=/path/to/nnet_ema.pth`. That is a **placeholder in the
authors' own command line**, not a download URL. The published
FreqFlow (Ren et al. 2026, CVPR 2026, `arXiv:2604.15521`) source
tree is public; the trained `nnet_ema.pth` (~2.7 GB float32,
675 M parameters) is not.

Full probe transcript: `data/freqflow_ckpt/README.md`. The README
itself is committed; the ckpt bytes and tarball are gitignored.

---

## 3. What is shipped (synthetic-mode Protocol surface)

| Item | Path | Status |
|---|---|---|
| Adapter | `adaptive_reflow/adapters/freqflow.py` | 1 562 LOC, abstract `FlowMatchingODEAdapter` |
| Default factory | `default_freqflow_adapter` | wired into `DOWNSTREAM_METRICS["freqflow"]` |
| Synthetic velocity field | `_synthetic_velocity_field` | deterministic NumPy two-branch (spatial 4096→256→4096 MLP + linear projection of normalised FFT magnitude) |
| Conditioning cache | `_synthetic_class_conditioning` | SHA-256 keyed, mirrors SiT adaLN 1001-dim one-hot + 1152-dim adaLN conditioning vector |
| Latent shape | `(4, 32, 32)` float64 | matches SD-VAE / DC-AE convention |
| Clamp | `[-FREQ_FLOW_CLAMP, FREQ_FLOW_CLAMP]` = `[-6, 6]` | configurable |
| Default NFE | 50 (paper-default) | overridable per-round via `condition.delta_spec["num_steps"]` |
| Integrators | `euler`, `heun` | matches the paper's `--solver` choice |
| Conformance | `tests/test_adapters/test_freqflow.py` + `test_freqflow_real_ckpt.py` | 28 passed, 3 skipped (`REQUIRES_CKPT`), 0 failed |

The synthetic field is **not a trained FM model** — it is a
Protocol-surface shim that mirrors `SelfFlowAdapter.synthetic`. The
test suite can exercise every Protocol method (build_initial_state,
export_endpoint, detach_and_validate_endpoint, apply_restart_distribution,
compose_condition, solve_ode, batched_inference, capabilities) without
the heavy 2.7 GB torch dependency.

---

## 4. Synthetic sweep — what was run

Per the user directive ("don't downgrade, just supplement"), the sweep
runs at the same configuration as Wave 189 P2 (3 seeds × 5 rounds
framework arm, NFE=100, scheduler = PaperRatioAdaptiveScheduler via
`_make_framework_policy`) so the wave's cross-axis result file is
uniform.

| Parameter | Value |
|---|---|
| Seeds | 0, 1, 2 |
| NFE per round | 100 |
| N rounds (framework arm) | 5 |
| Force mode | `synthetic` |
| Metric mode | `synthetic` |
| Adapter | `FreqFlowAdapter` via `default_freqflow_adapter` |
| Wall-clock | ~0.25 s/cell (CPU only, no GPU needed) |

Because the FreqFlow primary metric in
`tools.eval.io.DOWNSTREAM_METRICS` is `DEFERRED_no_upstream_ckpt`,
the canonical `_compute_metric` pipeline returns `None` and the
`tools.eval.sweep._run_cell` cell status is `PENDING`. This is the
framework's correct refusal to score a non-existent forward pass.

To give the paper a non-trivial number to cite, the sweep
**supplements** the pipeline with a direct endpoint-distance metric
computed from the adapter's native-state cache:

```python
b_end = adapter._native_states[baseline_trace.native_state_digest]["trajectory"][-1]
f_end = adapter._native_states[framework_trace.native_state_digest]["trajectory"][-1]
endpoint_l2 = float(np.linalg.norm(b_end - f_end))
endpoint_cosine_sim = float(np.dot(b_end.ravel(), f_end.ravel())
                            / (np.linalg.norm(b_end.ravel())
                               * np.linalg.norm(f_end.ravel())))
```

The trajectory tensors are **real** — they come from the synthetic
adapter's Euler integrator running on the deterministic NumPy
two-branch field. They are **not** a trained SiT-XL/2 + FFT graph
output. The metric is **not** FID — there is no Inception forward pass.

### Results

| Seed | L2 (baseline vs framework endpoint) | Cosine sim | Baseline norm | Framework norm | Wall base | Wall FW |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 62.8426 | 0.5437 | 74.8782 | 40.9923 | 0.2435 s | 0.2497 s |
| 1 | 62.4759 | 0.5516 | 74.8366 | 40.7136 | 0.2398 s | 0.2464 s |
| 2 | 61.7005 | 0.5666 | 74.8448 | 40.9290 | 0.2420 s | 0.2493 s |
| **mean** | **62.3396** | **0.5540** | **74.8532** | **40.8783** | **0.2418 s** | **0.2485 s** |

The L2 distance (~62.34 in latent-norm units) reflects the framework
arm's restart-blend effect on the synthetic latent — i.e., the
multi-round loop is doing what it is supposed to do (move the latent
via the per-round β-blend), but the absolute number has zero
quantitative value as a FreqFlow result. The wall-clock ratio
(framework / baseline = 1.028) is the only directly comparable
quantity across arms: the multi-round solver has the same wall-clock
as the single-pass solver at this NFE budget because the synthetic
field is CPU-cheap (no Inception / no SiT-XL/2 forward).

### Output JSON

```
verification_outputs/wave189-p3-freqflow-real.json
```

Schema: `wave189_p3_freqflow_synth_sweep.v1`. Records `freqflow_status: "synthetic"`,
`ckpt_source: "synthetic-shim"`, `metric: "synthetic_endpoint_l2"`, and
`primary_metric_status: "PENDING"` so any downstream reader can detect
that this is a synthetic-shim result row, not a real-ckpt measurement.

### Sweep script

```
scripts/wave189_p3_freqflow_synth_sweep.py
```

Standalone, no GPU required, runs in ~1 s total wall-clock. Honours
the existing `_resolve_adapter` / `_solve_baseline` /
`_solve_framework` plumbing so the same code path used by the real
FreqFlow forward (when the ckpt lands) is exercised here.

---

## 5. Implication for the paper's "5 adapters" claim

The paper claims "5 adapters × 3 domains" (or similar phrasing — see
the §1 introduction sections). The five adapter slots are:

| Adapter | Domain | Ckpt status | Quantitative result? |
|---|---|---|---|
| LineageFlow | protein (Pfam) | real ckpt shipped (HF mirror), Wave 36 | YES — framework-arm HMMER hit rate +116.46% (Wave 86/158) |
| Kanzi | protein (Pfam) | real ckpt shipped (HF mirror), Wave 36 | YES — composite + paper-metric (Wave 52/91) |
| FlowMol3 | molecule (GEOM-DRUGS) | real ckpt shipped (lightning, 65 MB), Wave 71/73 | YES — paper-parity N=1000 framework-arm (Wave 87) |
| RectifiedFlowCIFAR | image (CIFAR-10) | real architecture + adapter; trains from scratch | YES — Wave 8 / Wave 186 sensitivity-analysis |
| FreqFlow | image (ImageNet-256 latents) | **NO public ckpt** | **NO** — this audit |

Of these five:

- 4 are real-ckpt adapters with measured framework-vs-baseline numbers.
- 1 (FreqFlow) is a synthetic-shim adapter. It contributes Protocol
  coverage and D.5 conformance, but no quantitative FreqFlow result.

**Recommended paper-text change.** Replace any phrase like "5
adapters" with the explicit breakdown above, or rephrase as "5
adapter families, four with real-ckpt framework integration and one
(FreqFlow) at synthetic-skeleton level pending upstream weight
release". Without this disclosure, a reviewer could read "5 adapters"
as "5 measured adapters" — which is not what the repo supports.

---

## 6. What would unblock the FreqFlow real-ckpt path

| Unblock step | Owner | ETA | Effort |
|---|---|---|---|
| Upstream authors release `nnet_ema.pth` on a public channel (GitHub releases, HF Hub, Zenodo) | FreqFlow authors (Sucheng Ren / ByteDance) | unknown — not on the project critical path | unblock-by-3rd-party |
| Once published: download to `data/freqflow/nnet_ema.pth` (or set `$FREQFLOW_CKPT`) | framework maintainer | <1h | trivial |
| Flip `FreqFlowAdapter.__init__` from `auto → synthetic` degrade to load + return a real forward | framework maintainer | ~4h incl. tests | medium — needs a SiT-XL/2 + FFT branch reference loader (none exists today; cf. C3 in the model card) |
| Re-run `pytest tests/test_adapters/test_freqflow_real_ckpt.py` — the 3 `REQUIRES_CKPT` tests flip from skip to real assertions | framework maintainer | ~30s | trivial |
| Add FreqFlow FID-50K cell to `tools.run_real_ckpt_eval` | framework maintainer | ~6h incl. ImageNet-256 val subset build | medium |

Until step 1 lands, every downstream step is blocked on a 3rd-party
release. This is correctly reflected in the model card §0 ("Verdict:
`nnet_ema.pth` does not exist publicly") and the
`tools.eval.io.DOWNSTREAM_METRICS["freqflow"]` entry
(`DEFERRED_no_upstream_ckpt`).

---

## 7. Files written / committed

| Path | Status |
|---|---|
| `verification_outputs/wave189-p3-freqflow-real.json` | NEW |
| `scripts/wave189_p3_freqflow_synth_sweep.py` | NEW |
| `docs/audit/wave189-p3-freqflow-honest-disclosure.md` | NEW (this file) |

No framework file is modified by this audit (single-responsibility:
disclose + run synthetic sweep + document). The adapter file
(`adaptive_reflow/adapters/freqflow.py`), the eval registry
(`tools/eval/io.py`), the model card
(`docs/models/freqflow.model_card.md`), and the ckpt landing zone
(`data/freqflow_ckpt/README.md`) are all consistent with this
disclosure and need no edit.

---

## 8. Cross-checks

| Source | Says | This audit |
|---|---|---|
| `docs/models/freqflow.model_card.md` §0 | "no checkpoint exists" | agrees |
| `data/freqflow_ckpt/README.md` | "nnet_ema.pth: absent (not published)" | agrees |
| `tools/eval/io.py` `DOWNSTREAM_METRICS["freqflow"]` | primary metric = `DEFERRED_no_upstream_ckpt` | agrees |
| `tools/eval/io.py` `note` field of `phase4_q4_2026_freqflow.json` (pre-deferral Wave 36 reading) | "synthetic-mode plateau; real-ckpt forward depends on Wave 36 Agent A/B/C" | agrees — Agents A/B/C landed (Kanzi + LineageFlow ckpts); FreqFlow's agent C did not, by absence of upstream release |
| `verification_outputs/phase4_q4_2026_freqflow.json` | `adapter_mode: synthetic`, `baseline_marker: synthetic_fallback` | agrees |
| Wave 188 P5 fix-2 §7.6.4 cd70821 inversion cross-link | "FreqFlowAdapter remains at synthetic skeleton pending upstream release" | agrees |

---

## 9. Honest framing

Per the user directive not to downgrade, this audit *supplements* the
existing PHASE-4 deferred state with a synthetic-mode sweep that
exercises the full framework pipeline (resolve adapter → solve
baseline → solve framework → compute direct endpoint metric →
record cell). It does NOT claim a real FreqFlow result. It does NOT
silence the deferral. It does NOT promote the synthetic-shim L2
number to a "FreqFlow metric".

The paper text should treat FreqFlow as **synthetic-skeleton level**
until the upstream authors release `nnet_ema.pth`. The 5-adapter
claim, as currently phrased, should be reworded to reflect that 4 of
the 5 adapters have measured results and the 5th does not.