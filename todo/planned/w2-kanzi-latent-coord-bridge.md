# Wave 91 (W2) — Kanzi latent→coord bridge + framework paper-metric measurement

**Date:** 2026-09-09
**Status:** PLANNED (1 agent, ~3-5h wall-clock, single commit)
**Closes:** reviewer weakness W2 (Kanzi framework arm NOT_MEASURABLE)
**Depends on:** Wave 90 commit `fe95293` (PB-xtb) — DONE
**Blocks:** Wave 92 (N=5000 sweep, optional), Wave 93 (statistical power)

> **Why this matters:** Kanzi framework arm was previously NOT_MEASURABLE because there's no way to go from framework's restart-blended latent distribution back to Kanzi's 3D-coordinate space (Kanzi encodes latents → FSQ codebook → decoder to coords). Wave 91 builds the missing bridge so framework paper-metric becomes measurable.

---

## 1. Goal

Build a `tools/kanzi_latent_to_coord.py` thin wrapper that:
1. Takes a framework-generated latent (after restart-blend round)
2. Passes it through Kanzi's encoder inverse + FSQ quantize + decoder
3. Returns 3D coordinates suitable for PoseBusters / sanitization metrics

Then wire this into `tools/run_real_ckpt_eval.py` as opt-in `--kanzi-framework-paper-metrics` flag.

Run N=1000 framework paper-metric eval on Kanzi to close W2.

---

## 2. Pre-requisites (READ first)

- **Wave 88 commit `6add1b9`**: Kanzi N=1000 baseline paper-metric eval exists; framework plumbing (`solve_ode` + `apply_restart_distribution`) verified working
- **Wave 90 commit `fe95293`**: PB-xtb pipeline pattern (`tools/flowmol3_xtb_bridge.py`) is a **template** to follow for Kanzi's bridge
- **Kanzi upstream code**: must read `data/kanzi_upstream/` (cloned in Wave 79 Phase 1) — find `kanzi/encoder.py`, `kanzi/quantizer.py`, `kanzi/decoder.py`, `kanzi/inference.py`

---

## 3. Constraints

- **CALL upstream decoder** — do not reimplement; use `KanziDecoder.forward(z_q)` directly
- **Same eval protocol** — `tools/paper_metrics_kanzi.py` (Wave 83) computes 6 Kanzi paper metrics
- **D.4 byte-stable**: 33/33 unchanged
- **Interface-first**: new `--kanzi-framework-paper-metrics` flag opt-in; legacy default unchanged
- **NO push** — user decides

---

## 4. Phase 1 — READ-ONLY audit (~30 min)

### Inputs
- `data/kanzi_upstream/` (Kanzi upstream cloned)
- `tools/flowmol3_xtb_bridge.py` (Wave 90 pattern)
- `tools/paper_metrics_kanzi.py` (Wave 83)
- `adaptive_reflow/adapters/kanzi.py` (current Kanzi adapter)
- `verification_outputs/kanzi_n1000_paper_metrics/` (Wave 88 baseline numbers)

### Outputs
- `docs/audit/wave91-phase1-audit.md` with:
  - Upstream decoder call signature (`z_q → coords`, file:line)
  - Current framework → Kanzi latent → coord gap (what's missing)
  - Exact Python code snippet to do the bridge (~30-50 LOC)

### No commit
Pure documentation; just code:line citations + proposed function signature.

---

## 5. Phase 2 — Author the bridge (~60-90 min)

### File: `tools/kanzi_latent_to_coord.py` (NEW)

**Function signature:**

```python
def kanzi_latent_to_coords(
    latent: torch.Tensor,         # shape [B, latent_dim], framework output
    decoder: KanziDecoder,         # vendored from upstream, NOT reimplemented
    fsq_quantizer: FSQuantizer,    # vendored from upstream
) -> torch.Tensor:                 # shape [B, n_atoms, 3]
    """Bridge framework-generated latent to Kanzi's 3D coordinate space.
    
    Pipeline: latent → decoder.input_proj → FSQ.quantize → decoder.forward
    Mirrors upstream kanzi/inference.py:decode_latent_step (cite file:line)
    """
```

### Implementation
- ~30-50 LOC
- Calls upstream decoder (NOT a wrapper — direct call)
- Returns coords with same dtype/device as input
- Unit testable with synthetic latent

### Tests: `tests/test_tools/test_kanzi_latent_to_coord.py` (NEW)

- Test 1: synthetic latent → coords shape `[B, n_atoms, 3]` PASS
- Test 2: `coord.requires_grad` matches upstream pattern
- Test 3: deterministic across runs (seed=42)
- Test 4: dtype/device round-trip

### Verify
- `pytest tests/test_tools/test_kanzi_latent_to_coord.py -v`
- D.4 byte-stable: `pytest tests/ -k d4 → 33/33 PASS`

### Commit (single, NO push)
**Title:** "Wave 91 Phase 2: Kanzi latent→coord bridge (W2 Kanzi framework paper-metric measurement)"
**Body:** per-line audit + 4 unit tests + D.4 verify

---

## 6. Phase 3 — Wire into eval pipeline (~60 min)

### Modify: `tools/run_real_ckpt_eval.py`

- Add `--kanzi-framework-paper-metrics` CLI flag (default OFF)
- Add `_compute_kanzi_framework_metric` helper that:
  1. Generates N framework samples via `_solve_framework` (Wave 86 fixed)
  2. For each, calls `kanzi_latent_to_coords` to get coords
  3. Runs `tools/paper_metrics_kanzi.py` 6-metric suite on coords
  4. Returns per-metric dict

### Regression test
- Add 1 test in `tests/test_tools/test_run_real_ckpt_eval.py`: flag exists + smoke (off path)
- D.4 verify

### Commit (single, NO push)
**Title:** "Wave 91 Phase 3: wire Kanzi framework paper-metric into run_real_ckpt_eval"

---

## 7. Phase 4 — Run N=1000 framework paper-metric eval (~60-90 min)

### Command
```bash
.venvs/kanzi_venv/bin/python tools/run_real_ckpt_eval.py \
    --model kanzi \
    --force-mode real \
    --kanzi-framework-paper-metrics \
    --n-samples 1000 \
    --output-dir verification_outputs/kanzi_n1000_framework_paper_metrics/
```

### Outputs
- `verification_outputs/kanzi_n1000_framework_paper_metrics/per_metric.json`:
  ```json
  {
    "reconstruction_kabsch_rmsd_A": {"baseline": 0.95, "framework": 0.91, "delta": -0.04, "p_value": <1e-3},
    "codebook_utilization": {"baseline": 0.71, "framework": 0.74, "delta": +0.03, "p_value": 0.02},
    "codebook_entropy": {...},
    "motif_coverage": {...},
    "structural_validity": {...},
    "fbd": {...}
  }
  ```

### Verify
- All 6 metrics computed (no NaN, no inf)
- Statistical test: Welch's t-test or Mann-Whitney (pick per-metric based on distribution)
- Honest verdict: per-metric SUPPORTED / PARTIAL / TIE / REGRESSES (same scheme as Wave 89)

### NO commit
Just data + audit doc

---

## 8. Phase 5 — Paper §7.3 update + final synthesis (~30-45 min)

### Update: `docs/paper-draft.md` §7.3 Kanzi (ADDITIVE)
- Add Wave 91 paragraph with 6 metrics + verdict
- Cross-reference Wave 88 baseline + Wave 91 framework
- Per-paper-claim status: SUPPORTED if framework wins, TIE if neutral, etc.

### Author: `docs/audit/wave91-phase5-final.md`
- Per-metric baseline vs framework with delta + p-value
- Statistical power at N=1000
- D.4 byte-stable 33/33 PASS
- G-MASTER 7/7 PASS
- mkdocs build --strict EXIT=0
- Honest caveats (FSQ noise floor, decoder-side error, etc.)

### Update: `docs/push-ready-summary.md` (additive)

### Verify
- D.4 + G-MASTER + mkdocs

### Commit (single, NO push)
**Title:** "Wave 91: Kanzi latent→coord bridge + framework paper-metric measurement — W2 closed"

---

## 9. Time budget

- Phase 1 (audit): 30 min
- Phase 2 (bridge code + tests): 60-90 min
- Phase 3 (wire into pipeline): 60 min
- Phase 4 (N=1000 framework eval): 60-90 min
- Phase 5 (paper update + commit): 30-45 min
- **Total: 3.5-5.5 hours wall-clock**

---

## 10. Open questions

1. **Kanzi upstream decoder signature** — needs Phase 1 audit to confirm; if differs from what I sketched, plan adapts
2. **FSQ quantizer on framework latent** — does framework latent need to be projected to FSQ's expected input dim before quantization? Phase 1 audit answers
3. **Per-metric statistical test** — Welch's t-test (parametric) vs Mann-Whitney (non-parametric)? Pick after Phase 4 distribution check
4. **N=1000 vs N=5000 for Kanzi** — defer to Wave 92 decision

---

## 11. Per-paper-claim status after Wave 91

| Metric | Baseline | Framework | Delta | p-value | Verdict |
|---|---|---|---|---|---|
| reconstruction_kabsch_rmsd_A | 0.95 | TBD | TBD | TBD | TBD |
| codebook_utilization | 0.71 | TBD | TBD | TBD | TBD |
| codebook_entropy | TBD | TBD | TBD | TBD | TBD |
| motif_coverage | TBD | TBD | TBD | TBD | TBD |
| structural_validity | TBD | TBD | TBD | TBD | TBD |
| fbd | TBD | TBD | TBD | TBD | TBD |

**Wave 91 success criteria:** at least 3/6 metrics become measurable (others may stay NOT_MEASURABLE due to FSQ noise floor or decoder-side error — honest caveat).

---

## 12. Cross-references

- Wave 90 commit `fe95293`: PB-xtb pipeline pattern to mirror
- Wave 88 commit `6add1b9`: Kanzi baseline numbers (comparison reference)
- Wave 83 commit `50107eb`: Kanzi 5 codebook metrics wrapper (call sites)
- Wave 79 commit `f46e167`: Kanzi upstream clone (where to read decoder)