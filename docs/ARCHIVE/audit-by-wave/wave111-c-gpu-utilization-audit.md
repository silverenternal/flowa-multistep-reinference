# Wave 111.0 Reviewer C: GPU Utilization Root-Cause Audit

**Author:** Wave 111.0 Reviewer C (READ-ONLY)
**Date:** 2026-09-11
**Scope:** Why GPU utilization stays at 0% during Kanzi sweep, even when CUDA is available.

---

## §0 — TL;DR

There are **4 root causes** in a stack:

| # | Root cause | Severity | Where | LOC for fix |
|---|------------|----------|-------|-------------|
| **RC-1** | `_kanzi_sweep_runner.py:340` constructs `DAE.from_pretrained(...).eval()` but **never moves it to CUDA**. The DAE stays on CPU. | **CRITICAL** | tools/_kanzi_sweep_runner.py:340 | 2 LOC |
| **RC-2** | `_KanziDAEShim.forward()` (Wave 110.B "Bug 2 fix") returns `torch.zeros_like(x)` without invoking DAE.encode/DAE.net. Even on CUDA, the framework arm would still ship zeros. | **CRITICAL** (framework arm only) | adaptive_reflow/adapters/kanzi.py:1124-1138 | 10-15 LOC (real fix), 1 LOC (keep zero & add `assert self._mode == "synthetic"` fail-fast) |
| **RC-3** | `kanzi_latent_to_coord.py:148-154` derives `device = next(decoder.parameters()).device`. Since the decoder is loaded on CPU in RC-1, every bridge call coerces the latent to CPU — so `DAE.decode()` runs the 100-step diffusion on CPU `nn.Linear`. | **CRITICAL** (downstream of RC-1) | tools/kanzi_latent_to_coord.py:148-154 | 0 LOC (auto-fix once RC-1 lands) |
| **RC-4** | `_torch_velocity_field()` constructs `torch.as_tensor(x, dtype=dtype)` without specifying `device=` — and the shim returns zeros regardless, so any CUDA move is moot for framework arm. For baseline arm via the bridge (`kanzi_latent_to_coord`), the decoder decode path *would* use CUDA if RC-1 is fixed. | **LOW** | adaptive_reflow/adapters/kanzi.py:1046-1057 | 3 LOC |

**CUDA is available.** Verified:
```
.venvs/kanzi_venv/bin/python -c "import torch; print(torch.cuda.is_available())"
→ cuda_available: True
→ cuda_version: 13.0
→ torch_version: 2.14.0+cu130
```

The 3248 MiB GPU memory in the nvidia-smi readout is the CUDA context allocated by **`import torch`** + the shim instantiation (which creates a `nn.Module` on the default device, i.e. CUDA when torch is built with CUDA). But **no kernels run**: see RC-2 for the shim-forward case and RC-1+RC-3 for the decoder-bridge case.

The same project already has a working fix in `tools/sweep_kanzi_n1000_diverse.py:136` (`dae = dae.to("cuda")`) with the explicit comment "DAE was on CPU. Bridge auto-coerces latent to the decoder's parameter device, so the entire 100-step diffusion ran on CPU nn.Linear (~95% of runtime per py-spy profile, >500h wall for N=1000)." — but the canonical `_kanzi_sweep_runner.py` was never updated.

---

## §1 — Call chain trace

### 1.1 Baseline arm (the active GPU work path)

```
[tools/_kanzi_sweep_runner.py:340]
  dae = DAE.from_pretrained(str(ckpt)).eval()
        # ↑ NO .to("cuda") call. Model stays on CPU.
        # data/kanzi_upstream/src/kanzi/models.py:335-341 confirms from_pretrained has no device= param.

[tools/_kanzi_sweep_runner.py:227+] (per-sequence decode)
  → kanzi_latent_to_coord(latent, decoder=dae, fsq_quantizer=dae.quantize, ...)
    [tools/kanzi_latent_to_coord.py:148-154]
      device = next(decoder.parameters()).device   # → torch.device("cpu")  ← BUG INHERITED FROM RC-1
      x_t = torch.as_tensor(latent, dtype=torch.float32, device=device)   # → CPU
      ...
      x_pred = decoder.decode(idx_BL, n_steps=..., ...)   # → 100× self.net(x_BLD, ...) on CPU
        [data/kanzi_upstream/src/kanzi/models.py:373-428]
          c_BLD = self.quantize.indices_to_codes(idx_BL)
          device = c_BLD.device                # CPU (inherits from idx_BL which was on CPU)
          x_BLD = torch.randn(..., device=device)   # CPU
          for step in range(n_steps):           # 100 iters of self.net() + vf_to_score() on CPU
              v = self.net(x_BLD, ..., z_BLD=c_BLD)   # ← CPU nn.Linear
              ...
```

This is the path the user observed: GPU 0 at 0% util, 3248 MiB used (CUDA context from `import torch` in the kanzi_venv shell), but every kernel runs on CPU `nn.Linear`.

### 1.2 Framework arm (currently a no-op regardless of CUDA)

```
[adaptive_reflow/adapters/kanzi.py:1414-1419]
  self._mode: Mode = _resolve_mode(force_mode, self._weights_path, ..., torch_available=torch_is_available())
        # torch_is_available() = lambda: _adapter_common_torch_is_available() → just `import torch`
        # Does NOT probe torch.cuda.is_available().

[adaptive_reflow/adapters/kanzi.py:1452]
  self._model = _load_torch_model(self._weights_path)
        # _load_torch_model → DAE.from_pretrained(...) wrapped in _KanziDAEShim.
        # Shim is a nn.Module but still on CPU (no .to("cuda") anywhere).

[adaptive_reflow/adapters/kanzi.py:2059-2087 — _velocity_field]
  if self._mode == "torch":
      assert self._model is not None
      return _torch_velocity_field(self._model, x, t, dtype=self._torch_dtype, ...)
  assert self._synthetic_weights is not None
  return _synthetic_velocity_field(x, t, weights=self._synthetic_weights)

[adaptive_reflow/adapters/kanzi.py:1009-1059 — _torch_velocity_field]
  with torch.no_grad():
      x_t = torch.as_tensor(x, dtype=dtype).unsqueeze(0)   # NO device= → CPU
      t_t = torch.tensor([float(t)], dtype=dtype)           # NO device= → CPU
      family_t = torch.as_tensor(cache.get(...), dtype=dtype).unsqueeze(0)   # NO device= → CPU
      v = model(x_t, t_t, family=family_t)     # ← calls _KanziDAEShim.forward(x_t, t_t, family_t)
      out = np.asarray(v.squeeze(0).detach().cpu().numpy(), dtype=np.float64)   # → numpy
  return out.reshape(state_shape)

[adaptive_reflow/adapters/kanzi.py:1124-1138 — _KanziDAEShim.forward (Wave 110.B "Bug 2 fix")]
  def forward(self, x, t, family=None):
      # Docstring: "Until the adapter's state is migrated to backbone-coord space,
      # return a zero-velocity field of the input shape"
      with torch.no_grad():
          return torch.zeros_like(x)        # ← no DAE.encode/net call, no kernels
```

Even if RC-1 is fixed and the shim is moved to CUDA, the framework arm **still** returns zeros for every forward call. RC-2 is a separate, framework-arm-only bug.

### 1.3 The known-good reference (already fixed in one driver)

```
[tools/sweep_kanzi_n1000_diverse.py:131-138]
  dae = DAE.from_pretrained(str(args.ckpt)).eval()
  # Wave 99.A → 99.E root-cause fix: DAE was on CPU. Bridge auto-coerces
  # latent to the decoder's parameter device, so the entire 100-step
  # diffusion ran on CPU nn.Linear (~95% of runtime per py-spy profile,
  # >500h wall for N=1000). Move DAE to CUDA so .decode() lands on GPU.
  dae = dae.to("cuda")
```

This driver has been working since Wave 99.E. But `_kanzi_sweep_runner.py` (the canonical, refactored runner used by `sweep_kanzi_n1000_paper_metrics.py` + the framework sweeps) was **never** updated. This is a regression caused by Wave 105 P1-A's runner extraction: the fix that lived inline in the old driver didn't migrate into the new shared runner.

---

## §2 — Root causes identified

### RC-1 (CRITICAL): `_kanzi_sweep_runner.py:340` does not move DAE to CUDA

**Evidence:**

- `tools/_kanzi_sweep_runner.py:340`: `dae = DAE.from_pretrained(str(ckpt)).eval()`
- `data/kanzi_upstream/src/kanzi/models.py:335-341`: `DAE.from_pretrained(cls, ckpt_pth)` does only `torch.load(ckpt_pth)` + `model.load_state_dict(ckpt["model"])`. No `device=` parameter. No `.to(...)` call.
- `data/kanzi_upstream/src/kanzi/models.py:204` (`GPT.from_pretrained`): same pattern.
- Grep across `adaptive_reflow/`, `tools/`, `data/kanzi_upstream/src/kanzi/`: **zero** `.to("cuda")` / `.cuda()` calls on the upstream DAE. The only Kanzi `.to("cuda")` is `tools/sweep_kanzi_n1000_diverse.py:136`.

**Effect:** All DAE parameters stay on CPU. The bridge inherits CPU via `next(decoder.parameters()).device`. The 100-step `DAE.decode()` diffusion runs entirely on CPU `nn.Linear` (and CPU `MultiheadAttention`/`TransformerBlock`).

**Note on KANZI ADAPTER (framework arm):** `_load_torch_model` (adaptive_reflow/adapters/kanzi.py:1062) returns a `_KanziDAEShim` wrapping `DAE.from_pretrained(...)`. The shim is a `nn.Module` whose only attribute is `self._dae = dae`. **The shim's `.to("cuda")` was never called either.** So even the framework arm — which by construction returns zeros in RC-2 — would have zero GPU activity beyond the initial import.

### RC-2 (CRITICAL, framework-arm only): `_KanziDAEShim.forward()` returns zeros

**Evidence:**

- `adaptive_reflow/adapters/kanzi.py:1124-1138`: `def forward(self, x, t, family=None): ... return torch.zeros_like(x)`
- Docstring explicitly says: "Until the adapter's state is migrated to backbone-coord space, return a zero-velocity field of the input shape so the trajectory endpoint (≈ initial state) satisfies the bridge's `(B, L, n_channels_decoder)` contract without raising."

**Effect:** The framework arm's velocity field is the zero tensor — independent of input, time, conditioning, AND device. This is the Wave 110.B "Bug 2 fix" placeholder for the latent↔backbone-coord migration. The user-facing effect: framework arm produces a constant trajectory (= initial state + zero velocity integrated), no kernels run, GPU stays at 0%.

**Status:** Acknowledged in the docstring as a TEMPORARY workaround pending backbone-coord migration. Not a "bug" in the traditional sense — it's a documented placeholder. The audit call is to **either** (a) implement the real backbone-coord path so the shim calls `self._dae.encode(...)` + `self._dae.net(...)`, **or** (b) make the fail-fast more visible (`assert self._mode == "synthetic"` for the framework arm) so users don't think the framework arm is doing meaningful work.

### RC-3 (CRITICAL, downstream of RC-1): bridge auto-coerces latent to decoder's CPU device

**Evidence:**

- `tools/kanzi_latent_to_coord.py:148-154`: `device = next(decoder.parameters()).device; x_t = torch.as_tensor(latent, dtype=torch.float32, device=device)`
- Same pattern at line 305-306: `weight = state["weight"].float().to(device=x_t.device)`

**Effect:** When the decoder is on CPU (RC-1), the latent is materialized on CPU, the FSQ implicit-codebook is read on CPU (`torch.arange(...device=device)`), the cdist argmin is CPU, and `decoder.decode(...)` runs on CPU. This is the path that consumes ~95% of sweep wall-time per the inline comment in `tools/sweep_kanzi_n1000_diverse.py:132-135`.

**Fix LOC: 0.** This auto-fixes the moment RC-1 is fixed.

### RC-4 (LOW): `_torch_velocity_field()` does not specify device

**Evidence:**

- `adaptive_reflow/adapters/kanzi.py:1046-1057`: `x_t = torch.as_tensor(x, dtype=dtype).unsqueeze(0)` — no `device=` argument.

**Effect:** Negligible today because RC-2 makes the framework arm return zeros regardless. But for the day RC-2 is resolved (real DAE.encode/net path), the input tensors must be moved to CUDA explicitly. Otherwise the shim would receive CPU tensors and either crash or fall back to CPU compute.

**Fix LOC: 3** (read `next(model.parameters()).device` and pass to `torch.as_tensor(..., device=device)`).

---

## §3 — Per-cause fix plan

| Cause | File:line | LOC | Risk | ETA |
|-------|-----------|-----|------|-----|
| **RC-1** | tools/_kanzi_sweep_runner.py:340 | +2 | **LOW** — identical to the already-working `sweep_kanzi_n1000_diverse.py:136` fix. Add 1 conditional `if torch.cuda.is_available(): dae = dae.to("cuda")` after `.eval()`. | 5 min |
| **RC-2** (option A — real fix) | adaptive_reflow/adapters/kanzi.py:1124-1138 | +10-15 | **HIGH** — requires migrating adapter state to backbone-coord `(B, L, 3)` space. Out of scope for Wave 111.0; this is the architectural fix tracked by the Wave 110.D follow-up. |
| **RC-2** (option B — fail-fast) | adaptive_reflow/adapters/kanzi.py:1124-1138 | +1 | **LOW** — replace `return torch.zeros_like(x)` with `raise NotImplementedError("Wave 110.B placeholder: backbone-coord migration pending; framework arm is currently a no-op")`. Keeps the bridge contract intact, makes the placeholder visible. | 5 min |
| **RC-3** | (auto-fix) | 0 | **ZERO** | 0 min |
| **RC-4** | adaptive_reflow/adapters/kanzi.py:1046-1057 | +3 | **LOW** — pass `device=` matching `next(model.parameters()).device` to all 3 `torch.as_tensor` calls. | 10 min |

**Total LOC estimate for safe fixes (RC-1 + RC-2B + RC-4): 6 LOC.**
**Total LOC estimate for the real RC-2 fix: ~15-20 LOC** (requires Wave 110.D follow-up work — backbone-coord migration is a separate architectural change).

---

## §4 — GPU verification protocol

After applying the RC-1 fix (`dae = dae.to("cuda")` in `_kanzi_sweep_runner.py`), verify in three ways:

### 4.1 Sanity-check device of loaded model (single-shot)

```bash
.venvs/kanzi_venv/bin/python -c "
import sys; sys.path.insert(0, 'data/kanzi_upstream/src')
import torch
from kanzi.models import DAE
dae = DAE.from_pretrained('data/kanzi_ckpt/cleaned_model.pt').eval()
print('before:', next(dae.parameters()).device)
if torch.cuda.is_available():
    dae = dae.to('cuda')
print('after :', next(dae.parameters()).device)
"
# Expected: "before: cpu", "after: cuda:0"
```

### 4.2 Verify kernel activity during bridge call

```bash
# Terminal A: monitor GPU
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv -l 1

# Terminal B: run a single decode call
.venvs/kanzi_venv/bin/python -c "
import sys; sys.path.insert(0, 'data/kanzi_upstream/src')
import torch, numpy as np
from kanzi.models import DAE
dae = DAE.from_pretrained('data/kanzi_ckpt/cleaned_model.pt').eval()
dae = dae.to('cuda')
# Build a fake (B=1, L=64) index batch
idx = torch.randint(0, dae.quantize.codebook_size, (1, 64), device='cuda')
out = dae.decode(idx, n_steps=50, noise_weight=0.45)
print('out.shape:', out.shape, 'device:', out.device)
"
# Expected: nvidia-smi shows util jumping to 30-90%, out.device = cuda:0
```

### 4.3 Verify the sweep driver uses CUDA

```bash
# Run a small Kanzi sweep (N=10) and time it.
time .venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py \
    --mode baseline --n-samples 10 --output-dir /tmp/wave111-verify
# Expected: total wall < 2 min on 5090; nvidia-smi util averages > 40%.
# Current (pre-fix): total wall ~15-20 min; nvidia-smi util 0%.
```

### 4.4 D.4 byte-stable regression check

```bash
pytest tests/ -k "d4" -v
# Expected: 72/72 PASS
```

The fix is non-functional from the byte-stable perspective — `_kanzi_sweep_runner.py:340` adds a device move after `.eval()`, which doesn't change any tensor values. All deterministic regression vectors must remain PASS.

### 4.5 Adversarial check: the framework arm is still zeros (RC-2 not yet fixed)

```bash
.venvs/kanzi_venv/bin/python -c "
import torch, numpy as np
from adaptive_reflow.adapters.kanzi import _load_torch_model, _KanziDAEShim
shim = _load_torch_model('data/kanzi_ckpt/cleaned_model.pt')
x = torch.randn(1, 64, 64)
t = torch.tensor([0.5])
v = shim(x, t)
print('v.abs().max():', v.abs().max().item())
# Expected: 0.0 (confirms RC-2 placeholder is still active)
"
```

If this prints `0.0`, RC-2 is still in effect and the framework arm is honest about being a placeholder. The user-facing message in §5 below should make this clear.

---

## §5 — User-facing message (drafted for the user's review)

> Kanzi sweep GPU is at 0% because **the DAE model is loaded on CPU**, not CUDA. CUDA *is* installed and the import succeeds (3248 MiB reserved) — but every `DAE.decode()` kernel (100 steps × `nn.Linear`) runs on CPU. This costs >500 h wall-time at N=1000 (per `tools/sweep_kanzi_n1000_diverse.py:132-135`).
>
> **The one-line fix (`dae = dae.to("cuda")`) was applied in `tools/sweep_kanzi_n1000_diverse.py` at Wave 99.E but never migrated into the refactored `tools/_kanzi_sweep_runner.py:340` at Wave 105 P1-A.** Re-applying it restores expected runtime.
>
> **For the framework arm only**, `_KanziDAEShim.forward()` (adaptive_reflow/adapters/kanzi.py:1124-1138) currently returns `torch.zeros_like(x)` — a documented placeholder until the latent→backbone-coord migration lands. **The framework arm is currently a no-op regardless of CUDA state.** This is the Wave 110.B "Bug 2 fix" placeholder, separately tracked under the Wave 110.D follow-up.
>
> Net effect after Wave 111.x lands: **baseline arm runs on GPU at 30-90% util (the GPU workhorse); framework arm is a known-placeholder returning zeros (no GPU work because there's no real velocity field to evaluate).** The user's feedback "GPU should NOT stay at 0% during Kanzi sweep" is fixed for the baseline arm; the framework-arm placeholder requires a separate architectural migration.

---

## §6 — Appendix: cross-references

- **Wave 99.E** (`tools/sweep_kanzi_n1000_diverse.py:131-138`): first `dae.to("cuda")` fix, with the inline py-spy justification. **Working.**
- **Wave 105 P1-A** (`tools/_kanzi_sweep_runner.py`): extracted runner, **DID NOT migrate the `.to("cuda")` fix**. This is the regression.
- **Wave 110.B** (`adaptive_reflow/adapters/kanzi.py:1124-1138`): `_KanziDAEShim.forward()` returns zeros. Documented as "until backbone-coord migration".
- **Wave 95 Phase 3.B** (`kanzi_latent_to_coord.py:189-227`): bridge logic — uses `device = next(decoder.parameters()).device` (auto-inherits CPU when DAE is on CPU).
- **Wave 99** (`_load_torch_model` in `adaptive_reflow/adapters/kanzi.py:1062-1163`): real `DAE.from_pretrained` shim wired in. The fix replaced the diffusers stub with the real upstream DAE, but again, **no `.to("cuda")` was added**.

---

## §7 — SHAs cited

- `fe95293` Wave 90 Step 8-13: FlowMol3 PB-xtb pipeline real wire (not directly relevant but most recent)
- `4f7e3c7` Wave 110.B: Fix framework_inv_proj by forcing KanziAdapter real mode (n_channels_decoder=512) — the shim-return-zeros change
- `36fd031` Wave 109.A: Re-run Kanzi N=1000 with --seed (PARTIAL)
- `f9df1f6` Wave 110.C: Re-run Kanzi N=1000 sweep with Bug 1+2 fixes verified (PARTIAL — wallclock budget exhausted)
- `7050128` Wave 110.D: Author wave110-final-synthesis.md + close Wave 109.A follow-up

(Pre-Wave-100 SHAs cited inline in §6 above for the older `.to("cuda")` precedent and runner extraction.)

---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
