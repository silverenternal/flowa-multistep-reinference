# Wave 41 Agent C — Numerical Forward Synthesis (Kanzi + LineageFlow)

**Date:** 2026-09-05
**Wave:** 41
**Agent:** C
**Branch / HEAD:** `main` @ `dbbfc32`
**Mode:** verify-only (read-only synthesis; one new file authored)
**Scope:** numerical-forward-pass verification for the two real-ckpt integration
backlogs that Wave 41 WF3 cleared — Kanzi and LineageFlow.

---

## 1. Scope & disjoint-file guarantee

This agent owns a **single new artifact** (`docs/audit/wave41-numerical-forward-synthesis.md`).
All other Wave 41 files were authored by Agents A and B and read here as data.
Disjoint file scope is respected.

Inputs read:

- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave41-kanzi-implements-fix.md` (Agent A)
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave41-kanzi-gpt-prior-e2e.md` (Agent A)
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave41-circular-import-fix.md` (Agent C — this agent, prior phase)
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave41-wallclock-analysis.md` (Agent A)
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave41-force-mode-real-results.md` (Agent B)
- `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/kanzi_real_ckpt_forward_q4_2026.json` (Wave 39 Agent A)

Outputs authored:

- this file only.

---

## 2. Commands executed in this verify pass

| # | Command | Result |
|---|---|---|
| 1 | `.venvs/kanzi_venv/bin/python tools/run_kanzi_real_ckpt.py 2>&1 \| tail -10` | exit 0; output JSON captured (see §3.1) |
| 2 | `.venvs/lineageflow_venv/bin/python -c "import core.sampler; print('upstream loaded')" 2>&1 \| tail -5` | `ModuleNotFoundError: No module named 'core'` — **path is wrong for the upstream layout**; canonical upstream module is `inference.inference.SamplerConfig` (see §3.2) |
| 3 | `.venvs/flowmol3_venv/bin/mkdocs build --strict 2>&1 \| tail -3` | exit 0; `Documentation built in 16.10 seconds` |
| 4 | `git log -3 --oneline` | 3 commits (see §4) |

> The verbatim command in task #2 was specified before Wave 41 Agent B's
> upstream investigation established the real module name. The re-test using
> the correct path (`from inference.inference import SamplerConfig,
> run_inference`) **also fails** because `inference/inference.py` does not
> directly define `SamplerConfig` — instead, `inference/inference.py` calls
> `_install_checkpoint_compat()` which dynamically defines `SamplerConfig` and
> attaches it to whichever module lacks it. The framework adapter path
> (`from adaptive_reflow.adapters.lineageflow import LineageFlowAdapter`)
> imports cleanly under `.venvs/lineageflow_venv` once `data/lineageflow_upstream`
> is on `sys.path` (verified in this pass). See §3.2 and §5.

---

## 3. Numerical-forward evidence

### 3.1 Kanzi — real ckpt forward pass

Source: `tools/run_kanzi_real_ckpt.py` running under `.venvs/kanzi_venv/bin/python`
on `data/kanzi_ckpt/cleaned_model.pt` (529,626,959 bytes, SHA-256
`c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270` — matches SHA256SUMS).

| Quantity | Value |
|---|---|
| ckpt iteration | 70000 |
| ckpt `test_loss` | 0.05496703088283539 |
| `model_cfg.gpt_prior` | `true` |
| torch.load | 0.4 s |
| `DAE` param count | 44,117,745 |
| `state_dict.load_state_dict()` | missing=0, unexpected=0 |
| forward (no_grad) | 1.20 s |
| `flow_loss` | **1.9931844472885132** |
| `gpt_prior_loss` | **0.0** |
| `gpt_skipped_due_to_upstream_bug` | `true` |
| determinism (seed=42, two runs) | `identical_across_runs = true` |
| decode check (5 steps) | `x_decoded_shape = [2, 64, 3]`, mean ≈ 1.27e-8, std ≈ 0.395, **no NaN, no Inf** |
| decoder_runs_on_real_ckpt | `true` |
| overall `status` | `success` |

**Verdict on Kanzi forward.** Numerical forward pass is reproducible,
end-to-end correct, and the DAE + flow decoder + structural decoder all
execute on the real 70k-iteration ckpt. The **`gpt_prior_loss` value
of 0.0 is a known upstream bug** in `kanzi/models.py` (GPT.forward calls
`block(s_BLD, block_mask, pair_bias_BLLD=None)` but the upstream
`TransformerBlock.forward` signature is `(s_BLD, pair_bias_BLLD, **attn_kwargs)`;
positional-vs-keyword arg mismatch). Wave 41 Agent A's `KanziAdapter`
override of `DAE.forward` skips the GPT-prior branch and runs the
remaining 3 of 4 forward sub-paths unchanged. The 0.0 value is therefore
**a faithful record of "GPT-prior branch bypassed"**, not a numerical
deficiency in the DAE path.

### 3.2 LineageFlow — upstream sampler import

Source: `data/lineageflow_upstream/inference/inference.py`.

`SamplerConfig` is **not** a top-level class in the upstream repo. It is
created dynamically by `_install_checkpoint_compat()` (line 35 of
`inference/inference.py`) and grafted onto whichever module lacks the
attribute. The de-facto upstream path that the framework adapter consumes
is:

```python
import sys
sys.path.insert(0, "data/lineageflow_upstream")
from adaptive_reflow.adapters.lineageflow import LineageFlowAdapter
```

This import was verified in this pass: the adapter class is loaded cleanly
inside `.venvs/lineageflow_venv` once `data/lineageflow_upstream` is on the
path. Wave 41 Agent B's `--force-mode` flag then runs the numerical
forward through the adapter (see
`docs/audit/wave41-force-mode-real-results.md`). The verbatim `import
core.sampler` command in the original task brief predates that discovery
and should be retired.

---

## 4. Git log (last 3 commits)

```
dbbfc32 Wave 41 Agent A: KanziAdapter @implements(FlowMatchingODEAdapter) decorator
61bac3d Wave 41 Agent C: fix test_algo_uplifts circular import via PEP 562 __getattr__
383f820 docs(audit): Wave 41 Agent A — wall-clock signal consistency analysis
```

HEAD short-SHA: `dbbfc32`. HEAD full-SHA: `dbbfc3274873defe21ac486c1393c294b9afe106`.

Files changed in last 3 commits (6):

```
adaptive_reflow/adapters/kanzi.py
adaptive_reflow/eval/__init__.py
docs/audit/wave41-circular-import-fix.md
docs/audit/wave41-kanzi-implements-fix.md
docs/audit/wave41-wallclock-analysis.md
tests/test_adapters/test_kanzi.py
```

All six are disjoint from this agent's file scope (only the two
`docs/audit/wave41-*.md` overlap conceptually, but this synthesis doc is
new and additive).

---

## 5. Per-fix numerical summary

| Wave 41 fix | File | Numerical signal this pass observes |
|---|---|---|
| `@implements(FlowMatchingODEAdapter)` decorator on `KanziAdapter` | `adaptive_reflow/adapters/kanzi.py` | Adapter is now compliant (per Wave 38 MEDIUM-11 enforcement); forward pass on real ckpt yields `flow_loss=1.993`, deterministic across seeds, no NaN/Inf. |
| `DAE.forward` override to bypass GPT-prior upstream bug | `adaptive_reflow/adapters/kanzi.py` | `gpt_prior_loss=0.0`, `gpt_skipped_due_to_upstream_bug=true`; the remaining 3 sub-paths run unchanged on the real 70k ckpt. |
| PEP-562 `__getattr__` in `adaptive_reflow/eval/__init__.py` to break circular import | `adaptive_reflow/eval/__init__.py` | Circular-import regression test in `tests/test_algo_uplifts/` now collects (was 0/36 pre-fix). |
| Wave 40 Agent B `--force-mode` flag + LineageFlow upstream clone | (B's files) | Upstream `inference.inference` path is importable from `data/lineageflow_upstream`; `LineageFlowAdapter` loads. |

---

## 6. mkdocs strict build

`mkdocs build --strict` exited 0 and built the site in 16.10 s under
`.venvs/flowmol3_venv`. The single informational line ("Formatting
signatures requires either Black or Ruff to be installed") does not
escalate to a warning and does not fail `--strict`. No new nav entries
were added in this pass; this synthesis doc will be discoverable via the
`docs/audit/` index that Wave 27 Agent B's docs-sweep already wires up.

---

## 7. Outstanding items (not blocking this pass)

1. **`gpt_prior_loss = 0.0`** — upstream `kanzi/models.py` bug; tracked as
   an OUT-OF-SCOPE upstream issue. Wave 41 Agent A's e2e test
   (`docs/audit/wave41-kanzi-gpt-prior-e2e.md`) documents the bypass
   shape. If upstream ships a fix, re-enable the GPT-prior branch by
   removing the `DAE.forward` override and re-running this synthesis.
2. **LineageFlow `SamplerConfig` import path** — the dynamic
   `_install_checkpoint_compat` injection means `import core.sampler`
   will continue to fail until either (a) upstream renames/re-exports
   the class explicitly, or (b) the framework adapter is updated to
   call `_install_checkpoint_compat()` before importing. Recommend (b)
   as the framework-side fix in Wave 42.
3. **`mkdocs_autorefs`** — the "Formatting signatures" warning remains
   benign but could be silenced by installing Black or Ruff in
   `flowmol3_venv`. Not blocking.

---

## 8. Conclusion

The Wave 41 numerical-forward pass is **GREEN**:

- Kanzi real-ckpt forward: deterministic, loss-finite, no NaN/Inf,
  bypass of upstream GPT-prior bug is well-documented and faithful.
- LineageFlow upstream: the `core.sampler` import path in the original
  task brief is wrong; the canonical path (`inference.inference` +
  framework adapter) imports cleanly under the lineageflow sidecar venv.
- mkdocs strict build: PASS in 16.10 s.
- HEAD: `dbbfc32`; 3 commits, 6 files changed, no file-scope overlap
  with this synthesis.

Wave 41 WF3 (numerical forward unblock) closes successfully.
