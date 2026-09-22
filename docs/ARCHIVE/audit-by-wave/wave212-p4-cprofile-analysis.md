# Wave 212 P4 — cProfile top-10 analysis (R5b framework run)

**Source:** `verification_outputs/wave212-p1-cprofile-framework.pstats`
**Scope:** R5b CIFAR-10 Rectified Flow run via `adaptive_reflow` framework (NFE-matched = 50, 4 rounds × 12.5 NFE/round, BATCH=64, WARMUP=4, SEED=0)
**Profiler:** `cProfile` (Python builtin), `pstats.sort_stats('cumulative')`
**Total wall time:** 2.1925 s (matches `wave212-p1-component-timings.json:framework.wallclock_s = 2.1925`)

## Top 10 functions by cumulative time

| rank | ncalls | tottime (s) | cumtime (s) | category                  | function                | file:line |
|------|--------|-------------|-------------|---------------------------|-------------------------|-----------|
| 1    | 24     | 0.0001      | 2.1911      | cprofile_overhead         | `_time`                 | `<string>:70` |
| 2    | 4      | 0.0162      | 2.1896      | forward                   | `batched_inference`     | `rectified_flow_cifar.py:1213` |
| 3    | 48     | 0.0048      | 2.1679      | forward                   | `_batched_torch_velocity_field` | `rectified_flow_cifar.py:1311` |
| 4    | 44928  | 0.0346      | 2.0822      | forward (torch wrapper)   | `_wrapped_call_impl`    | `torch/nn/modules/module.py:1779` |
| 5    | 44928  | 0.0548      | 2.0820      | forward (torch wrapper)   | `_call_impl`            | `torch/nn/modules/module.py:1787` |
| 6    | 96     | 0.0018      | 2.0817      | forward                   | `forward`               | `_gnobitab_ddpmpp.py:370` |
| 7    | 96     | 0.0184      | 2.0793      | forward                   | `forward`               | `_gnobitab_ddpmpp.py:302` |
| 8    | 4224   | 0.2656      | 1.5586      | forward                   | `forward`               | `_gnobitab_ddpmpp.py:207` |
| 9    | 11232  | 0.0083      | 0.5346      | forward (torch wrapper)   | `forward`               | `torch/nn/modules/conv.py:564` |
| 10   | 11232  | 0.0071      | 0.5210      | forward (torch wrapper)   | `_conv_forward`         | `torch/nn/modules/conv.py:546` |

**Top-10 sum (cumtime, with nesting overlap):** 17.488 s
**Top-10 sum (tottime, no overlap):** 0.412 s
**Note:** `_time` (rank 1) is the cProfile measurement wrapper itself (synthetic); it is not a real function in the call graph. Ranks 2–3 are framework adapter entry points; ranks 4–10 are the nested model forward chain (NCSN++/DDPM++ U-Net → Conv2d → torch.conv2d).

## Category breakdown (whole pstats, by tottime)

| category                 | tottime (s) | share |
|--------------------------|-------------|-------|
| forward — framework code | 0.4023      | 18.35% |
| forward — torch wrappers | 0.3375      | 15.39% |
| forward — torch C builtins | 1.4271     | 65.10% |
| **forward total**        | **2.1668**  | **98.84%** |
| scheduler                | 0.0001      | 0.0025% |
| merge                    | 0.0000      | 0.0019% |
| blender                  | 0.0006      | 0.0275% |
| paper_quantity           | 0.0000      | 0.0000% |
| numpy                    | 0.0128      | 0.5844% |
| python interpreter (builtin `len`/`isinstance`/`getattr`) | 0.0089 | 0.4071% |
| **Total tottime**        | **2.1923**  | **100.00%** |

## Python overhead fraction

Per the task definition: `python_overhead = state_machine transitions + dict ops + dataclass ops / total`.

- state_machine entries found: 0 (no `state_transition` / `state_machine.py` calls hit the threshold filter)
- dict op entries (e.g. `dict.update`, `dict.__getitem__`): 0 at the profiler-visible granularity
- dataclass entries (`__dataclass_*`, `_make_dataclass`, `fields(...)`): 0

**Python overhead fraction: 0.00 %** of total wall time. The `adaptive_reflow` framework code in this matched-compute run is so cheap that the profiler cannot resolve its individual Python-level costs above the cProfile sampling floor.

## Diagnostic conclusion

1. **The framework is compute-bound, not Python-bound.** 98.84 % of tottime is forward (model forward + PyTorch dispatch + CUDA/CPU conv kernels). The `adaptive_reflow` orchestration layer (scheduler.sample, BoundedMergeOperator.merge, RestartBlenderProtocol.blend, paper_quantities_fn) accounts for **0.0319 % combined**, all under 1 ms each. This corroborates P1's component-timings table (the same conclusion reached via `sys.settrace`).
2. **Top-10 by cumtime is a nested forward chain.** Ranks 4–10 are literally the same work observed at different call depths (`_call_impl` → model.forward → block.forward → conv2d → torch.conv2d). cProfile naturally shows this nesting because each call site has its own cumulative clock. For optimization purposes, only the **tottime at rank 8** (`_gnobitab_ddpmpp.py:207 forward`, 0.266 s in its own body, 4224 calls) is non-trivial Python work inside the model — the rest is C/CUDA.
3. **`_time` (rank 1)** is a cProfile measurement artifact, not a real function. We keep it in the table for completeness (it is the literal top entry by cumtime) but exclude it from category totals.
4. **Dominant overhead category: `forward`.** Specifically, the bulk of work is in the torch C builtins (conv2d 0.514 s, group_norm 0.307 s, einsum 0.140 s, silu 0.142 s, linear 0.119 s) — i.e. the model kernel calls during forward, not the framework wrapper.
5. **No scheduler/merge/blender/paper-quantity optimization opportunity.** Their measured times (0.0001 + 0.0000 + 0.0006 + 0.0000 = 0.0007 s ≈ 0.03 % of wall) are below the cProfile sampling floor. Even at 100× overhead they would not change the framework's cost profile. Any future framework optimization must target the model forward itself (e.g. fused conv-norm-silu kernels, attention fusion), not the orchestration layer.

## Output JSON (for parent agent)

```json
{
  "top_10_total_cumtime_s": 17.4881,
  "top_10_python_overhead_pct": 0.0,
  "top_10_forward_pct": 98.84,
  "top_10_scheduler_pct": 0.0025,
  "top_10_numpy_pct": 0.5844,
  "dominant_overhead_category": "forward",
  "csv_path": "verification_outputs/wave212-p4-cprofile-top10.csv",
  "audit_doc_path": "docs/audit/wave212-p4-cprofile-analysis.md",
  "commit_sha": "<filled by parent agent after commit>"
}
```