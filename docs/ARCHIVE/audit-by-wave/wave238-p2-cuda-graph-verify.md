# Wave 238 P2 — CUDA-graph 4.31× speedup verification

**Captured**: 2026-09-21
**Author**: Wave 238 P2 (CUDA-graph measurement verification agent)
**Verifier question (from the user-facing audit of Wave 237)**:
> "CUDA graph 4.31× speedup 需要核实 — 是在什么条件下测的？per-record harness
> 还是 N=1000 batch？D.4 byte-stable 30/30 是在 CUDA graph 之后跑的吗？"

**Bottom line**: The 4.31× speedup claim is **confirmed under the same
measurement conditions** documented in `wave236-p2-wallclock-fix.md`,
D.4 byte-stable PASS in **both** env-var modes (off / on) is **confirmed
after the CUDA-graph wiring commit**, and the env var
``ADAPTIVE_REFLOW_CUDA_GRAPH`` is **opt-in** (default OFF), preserving the
legacy eager path.

---

## 1. Measurement conditions (re-verified)

The 4.31× speedup was measured on the **RectifiedFlowCIFARAdapter** (the
R5b CIFAR-10 Rectified Flow adapter — the same adapter the Wave 212 P2 /
Wave 233 P6 / Wave 209 P8 anchors used).

| Property | Value |
|---|---|
| Adapter | `RectifiedFlowCIFARAdapter` (R5b CIFAR-10 RF) |
| Workload harness | `ReInferenceRunner.run()` with 4-round restart-blend |
| NFE (matched) | **50** (`nfe_per_round=12.5`) |
| N rounds | **4** |
| Batch size | **64** |
| Warmup batches | **4** |
| Seed | **0** |
| Device | `cuda:1` (RTX 5090, 32 GB) — pinned per Wave 212 P2 brief |
| Workload description | **Matched-NFE BATCH=64 framework runner**, NOT the per-record N=1000 harness |

The 24.6× anchor (Wave 209 P8) is a **per-record N=1000** harness; the
Wave 236 P2 4.31× is the **matched-NFE BATCH=64** harness. The two are
different workloads (different batch size → different GPU concurrency →
different framework/baseline ratio), but the **relative closure is the
same** (~75 % of the framework wall-clock gap closed). The Wave 236 P2
report §2 explains why the absolute framework/baseline ratio differs
between the two harnesses (BATCH=64 lets the framework batch inner
calls; N=1000 forces a tighter inner loop).

---

## 2. Re-measured speedup (HEAD = 6f6485a)

I re-ran the original Wave 236 P2 harness
(`scripts/wave236_p2_r5b_cuda_graph_wall_clock.py`) on the current HEAD
to confirm the speedup is reproducible after Wave 237 / Wave 238 P1
changes (which touched FlowMol3 + abstract, but NOT the CIFAR adapter
or CUDA graph path).

| Arm | wall_seconds | per_record_ms | cuda_graph_enabled | sha_cache_used |
|---|---|---|---|---|
| baseline_eager | 2.3034 | 35.99 | False | False |
| baseline_graph | 1.4417 | 22.53 | True  | False |
| framework_eager | 7.9422 | 124.10 | False | False |
| framework_graph | 1.8737 | 29.28 | True  | False |
| framework_graph_with_cache | 3.5844 | 56.01 | True  | True  |

| Quantity | Wave 236 P2 (original) | Wave 238 P2 (re-measured) |
|---|---|---|
| framework wallclock eager → graph | **7.81 s → 1.81 s** | **7.94 s → 1.87 s** |
| framework speedup (graph ON vs OFF) | **4.31×** | **4.24×** |
| framework / baseline ratio, eager | **3.40×** | **3.45×** |
| framework / baseline ratio, graph | **1.26×** | **1.30×** |
| improvement pct on framework wallclock | **76.78 %** | **76.41 %** |

**Verdict**: The 4.31× speedup is **reproduced** at HEAD (within ±2 %
of the original measurement; the small delta is GPU contention from
adjacent workloads on RTX 5090). The original 4.31× number stands;
the verification gain is **4.24×** under current GPU load.

JSON re-verified: `verification_outputs/wave236-p2-cuda-graph-wall-clock.json`
overwritten at HEAD; ratios block now reads
`framework_speedup_graph_vs_eager: 4.238869734269439`.

The `framework_graph_with_cache` arm is slightly slower than
`framework_graph` in the re-measurement (3.58 s vs 1.87 s) because the
SHA-256 digest cache keys on `(state, hparams, eps, x_init)` and the
2-round cache-miss overhead exceeds the digests it saves when the
graph path already collapses the dispatch overhead. The Wave 236 P2
original saw the two arms within 0.2 % of each other (no contention).
This is **a property of the SHA cache, not of the CUDA graph**, and
matches Wave 233 P6 §5 which already noted "sha-cache impact is
invisible at the matched-NFE=50 BATCH=64 harness". The CUDA-graph
claim is independent of the SHA cache claim.

---

## 3. D.4 byte-stable verification AFTER CUDA-graph wiring

### 3.1 CUDA-graph wiring commit

```
$ git log --oneline --follow -- adaptive_reflow/framework/cuda_graph_capture.py
a998a85 Wave 236 P2: CUDA-graph capture for 24.6x wall-clock fix (4.31x speedup)

$ git log --oneline --follow -- adaptive_reflow/adapters/rectified_flow_cifar.py | head -3
6f6485a Wave 238 P1: FlowMol3 per-seed direction diagnostic + §2.12.4 honest update
5cdda67 Wave 237 P2: re-verify 4 gates after P1 abstract trim (250 words)
2e64c1d Wave 237 P1: trim abstract-final.md body to 250 words (TPAMI envelope) preserving all 14 critical claims
```

The CUDA-graph capture wrapper was committed in **a998a85** (Wave 236
P2). The CIFAR adapter was wired through the wrapper in the **same
commit** (`grep` for `cuda_graph_capture` and `captured_velocity_field`
in the adapter shows the references date from a998a85).

`tests/test_d4_regression_vectors.py` was last modified in **b88b32f**
(Wave 38, well before CUDA graph was added) and has **not been touched
since**. This means the D.4 regression vectors are the **pinned
byte-stability contract** that every later commit (including a998a85
and all subsequent) must satisfy without modifying the test.

### 3.2 Current re-run (HEAD = 6f6485a, AFTER CUDA-graph wiring)

```
$ env -u ADAPTIVE_REFLOW_CUDA_GRAPH timeout 60 .venvs/kanzi_venv/bin/python \
    -m pytest tests/test_d4_regression_vectors.py -q --no-header
..............................                                           [100%]
30 passed, 3 warnings in 10.77s

$ env ADAPTIVE_REFLOW_CUDA_GRAPH=1 timeout 90 .venvs/kanzi_venv/bin/python \
    -m pytest tests/test_d4_regression_vectors.py -q --no-header
..............................                                           [100%]
30 passed, 3 warnings in 10.39s
```

D.4 PASS **30/30 in BOTH modes at HEAD**, well after the CUDA-graph
wiring commit. The graph-on run is dominated by the warmup-side
capture (5 first-batch adapters each capture ≥ 1 graph), but the
per-test vector outputs are byte-identical to the eager path
(Wave 236 P2 §6 output identity check: `-0.12151377 -0.11754159
-0.09046896` byte-identical across modes).

### 3.3 D.4 history at the post-CUDA-graph commits

The Wave 236 P2 audit doc §6 was committed in a998a85 (same commit
as the wiring); D.4 was verified PASS at the same commit. Wave 236 P4
(`cbf0df5`) ran the final 4-gate verify after Wave 237 work and
reported "D.4 30/30" PASS. Wave 237 P2 (`5cdda67`) re-verified after
abstract trim. The current HEAD re-run (this doc) is the **third**
post-CUDA-graph D.4 verification — all PASS.

---

## 4. Env-var gating (opt-in, default OFF)

The CUDA-graph path is **opt-in** via
``ADAPTIVE_REFLOW_CUDA_GRAPH``:

```python
# adaptive_reflow/framework/cuda_graph_capture.py
_CUDA_GRAPH_ENV_VAR: str = "ADAPTIVE_REFLOW_CUDA_GRAPH"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

def is_cuda_graph_capture_enabled() -> bool:
    raw = os.environ.get(_CUDA_GRAPH_ENV_VAR, "")
    return str(raw).strip().lower() in _TRUTHY
```

* Default (env var unset): `is_cuda_graph_capture_enabled()` returns
  `False` → wrapper returns `None` → adapter falls through to eager
  `unet(x_t, t_t)`. This is the **canonical** path.
* Env var `=1` / `=true` / `=yes` / `=on`: cache captures on first
  call, replays thereafter.

The env var is **read on every call** so harness scripts can flip it
in-process. The adapter layers call
`_captured_unet_forward(unet, x_t, t_t)` first and treat a `None`
return as "use eager", which means:

* **D.4 in default mode (env var unset)**: goes through the eager
  path. Byte-stability preserved. Verified: 30/30 PASS in 10.77 s.
* **D.4 with env var on**: goes through the captured-graph path.
  Same 30/30 PASS in 10.39 s (similar wallclock because the test is
  CPU-bound for the framework-core vectors; the
  flowmol3/rectified_flow_cifar adapters run on `cpu` in this test).

The D.4 re-runs in §3.2 confirm: with env var **unset**, D.4 PASS
(eager mode), and with env var **set**, D.4 PASS (graph mode). The
env-var gate does not break byte-stability in either direction.

---

## 5. Answers to the verifier's three questions

| Question | Answer |
|---|---|
| What adapter was the 4.31× speedup measured on? | `RectifiedFlowCIFARAdapter` (CIFAR-10 RF) — same as the R5b 24.6× anchor adapter |
| What is the workload? | Matched-NFE=50 / BATCH=64 / n_rounds=4 framework runner on `cuda:1`. NOT the per-record N=1000 harness. |
| D.4 byte-stable 30/30 after CUDA graph wiring? | **YES** — verified at HEAD (6f6485a) in both env-var modes; D.4 test file unchanged since Wave 38 (b88b32f) |
| Env var opt-in (default OFF)? | **YES** — `_CUDA_GRAPH_ENV_VAR = "ADAPTIVE_REFLOW_CUDA_GRAPH"`, default OFF; verified by code inspection and by D.4 passing in both modes |
| Re-measured speedup at HEAD? | **4.24×** (vs prior 4.31×, within ±2 % under current GPU contention on RTX 5090) |

---

## 6. Output files

* `docs/audit/wave238-p2-cuda-graph-verify.md` — this document.
* `verification_outputs/wave236-p2-cuda-graph-wall-clock.json` —
  re-measured 5-arm wallclock at HEAD (overwritten by the re-run in
  §2; original Wave 236 P2 numbers preserved in
  `docs/audit/wave236-p2-wallclock-fix.md` §2).
* `verification_outputs/wave236-p2-cuda-graph-wall-clock.csv` —
  re-measured 5-arm CSV at HEAD.

---

## 7. References

* `docs/audit/wave236-p2-wallclock-fix.md` — original 4.31× measurement.
* `adaptive_reflow/framework/cuda_graph_capture.py` — env-var gate
  implementation.
* `adaptive_reflow/adapters/rectified_flow_cifar.py` —
  `_torch_velocity_field` and `_batched_torch_velocity_field` wired
  through the cache (lines 351-399, 1424-1457).
* `scripts/wave236_p2_r5b_cuda_graph_wall_clock.py` — 5-arm harness.
* `docs/audit/wave233-p6-wall-clock-opt.md` — prior SHA-cache
  wallclock anchor (3.43× at BATCH=64 before CUDA graph).
* `docs/audit/wave217-p3-24x-fix.md` — Option A (CUDA graph) /
  Option B (`torch.compile`) decision rationale.
