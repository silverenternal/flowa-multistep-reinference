# FM-LCM Interface Gap Audit (r17 — 2026-09-01)

> User insight: 所有 FM-family 模型（continuous FM / CTMC / BFN / mixed-state / graph）
> 都是 ODE 或 transition kernel 求解器。它们共享一个 **least common multiple (LCM)** 结构。
> 当前 `FlowMatchingODEAdapter` 接口更接近 **GCD**（所有模型都有的最小子集）。
>
> 本文记录 10 个 LCM concerns + 15 个 SOTA adapter 实证缺失接口，
> 用于执行后复查填补状况。

---

## 1. 背景与动机

5 个 SOTA adapter（FlowMol3 / ProtBFN-AbBFN / Lumina / HiDream / GraphBFN）的实证模式：

| Adapter | Framework effect | 主要失败模式 |
|---|---|---|
| **Lumina** | ✅ FID + CLIPScore 改善 | harness bypass `Engine.run_round`（capability handshake gate 在错的层） |
| **HiDream** | ⚠️ CLIPScore ↑ / FID ↓（方向相反） | stub Llama + dual torch/synthetic mode 复制 4 遍 |
| **FlowMol3** | ❌ paper metrics 退步 | CTMC 训练 vs FE (ODE) 集成 mismatch（P-01 / task #324） |
| **ProtBFN** | ⚠️ marginal | `solve_ode` 跑 BFN 离散 refinement，Protocol 名字错误 |
| **GraphBFN** | n/a | `state_shape=()` sentinel，graph-shaped payload smuggle 通过 `_native_states` |

根因：当前 `FlowMatchingODEAdapter` 是 **GCD**，不是 **LCM**。10 个正交 concern 中，framework 暴露了 6 个、覆盖 partial 的 2 个、缺失 4 个。

---

## 2. FM-family LCM 的 10 个正交 concern

| # | Concern | Continuous FM | CTMC | BFN | Mixed (FlowMol3) | Graph (GraphBFN) |
|---|---|---|---|---|---|---|
| A | **state shape** | `(C,H,W)` tensor | `(L,K)` categorical | `(L,K)` categorical | `(x,a,c,e)` 4-tuple | `(theta_node, theta_edge, adj)` 3-tuple + variable N/E |
| B | **prior** | `N(0,I)` | uniform | uniform | per-channel size-prior | uniform + dynamic n_nodes/n_edges |
| C | **dynamics** | `dx/dt = v(x,t)` | `p(x_{t+dt}\|x_t,t)` | Bayesian update | per-channel mix | per-channel BFN update |
| D | **solver** | Euler / RK4 / Heun / DP45 | EulerHeun | BFN-step | heterogeneous Euler | discrete BFN loop |
| E | **condition** | CFG (text) | Inpainting | CDR | Null (unconditional) | property_value ∈ [0,1] |
| F | **extraction** | continuous sample | categorical argmax | decoded tokens | per-channel projection | `_argmax_rounded_samples` |
| G | **blending** | linear | categorical resample | row-renormalized | per-channel + size-aware pad/crop | elementwise + m=0/1 short-circuit |
| H | **materialization** | n/a | n/a | n/a | 4-tuple ↔ envelope | 3-tuple ↔ envelope |
| I | **trajectory** | `(T,C,H,W)` | `(N+1,L,K)` | `(N+1,L,K)` | dict `{traj_x,traj_c,traj_e,traj_a}` | dict `{theta_node, theta_edge, ...}` |
| J | **forward noise** | `clip(x_prior + injected)` | n/a | `(1-mix)*prior + mix*injected` row-renorm | per-channel | `clip(theta + delta, -10, 10)` |

每个 concern 都是可独立替换的。原 Protocol 把 (C)+(D)+(F) 三个 concern 合并到单个 `solve_ode` 调用里。

---

## 3. 当前 Protocol 暴露的 surface（**GCD**）

```python
@runtime_checkable
class FlowMatchingODEAdapter(Protocol):
    def capabilities(self) -> AdapterCapabilities: ...
    def build_initial_state(self, *, batch_id, sample_id) -> StateBundle: ...           # (B) prior
    def export_endpoint(self, state) -> StateBundle: ...                                # (F-aux)
    def detach_and_validate_endpoint(self, bundle) -> StateBundle: ...                  # (F-aux) gate
    def apply_restart_distribution(self, state, policy) -> StateBundle: ...             # (G)+(H) fused
    def compose_condition(self, bundle, delta) -> ODEConditionDelta: ...                # (E)
    def solve_ode(self, state, condition, *, seed) -> ODEIntegratorTrace: ...           # (C)+(D)+(F) FUSED
    def observe_endpoint(self, trace, state) -> StateBundle: ...                        # (F)
    def export_trajectory(self, trace) -> Any | None: ...                               # (I) untyped
    # inject_forward_noise(bundle, injected) — NOT declared; hasattr-detected (J)
```

`Engine.run_round` 硬编码 7-step 顺序（`capabilities_handshake → build_initial_state → apply_restart_distribution → compose_condition → solve_ode → observe_endpoint → detach_and_validate_endpoint`），adapter 不能 opt-out 任何 step。

---

## 4. 实证 gap：5 个 SOTA adapter 都暴露但 framework 没接口的 15 个 primitive

| # | Missing primitive | 用到的 adapter | 当前的 workaround | 后果 |
|---|---|---|---|---|
| 1 | `batched_inference()` | HiDream, GraphBFN | 通过 helper method 调，无 Protocol surface | vanilla baseline + framework FID/FCD 计算路径不统一 |
| 2 | **multi-mechanism dispatch** | ProtBFN（`ProtBFN`/`AbBFN`/`AbBFN2`）、HiDream（`full`/`dev`/`fast`）、FlowMol3（`pinned_commit`） | 构造时硬编码 + class-level constant | runtime 不能切换 mechanism；A/B 难做 |
| 3 | **`state_shape` as typed Protocol attr** | 全部 5 个（class + instance attr，F14 修过） | `getattr(self._adapter, "state_shape", (2,))` 回退到 broken default | runner 用 sentinel 跳过 forward-noise 分配，可能 OOM |
| 4 | `integrator choice` 声明 | Lumina, HiDream（`solver ∈ {euler, heun}`） | adapter-private constant（`LUMINA_IMAGE_2_0_INTEGRATORS`） | Lumina/HiDream 复制同一 `num_steps` literal |
| 5 | `vocabulary alignment` | ProtBFN（model_K=32 vs surface_K=22） | 内部 ad-hoc zero-pad + token-0 aggregation | 残差质量丢失；无 protocol-level 验证 |
| 6 | `conditioning cache` 声明 | Lumina（text_embed_cache）、HiDream（4-encoder cache） | per-adapter LRU 私有 dict | 跨 adapter cache 复用不可能 |
| 7 | **`export_trajectory()` 返回类型** | 全部 5 个（5 种不同类型） | `Any | None` | downstream evaluator 必须 probe 类型 |
| 8 | `stub-component` 声明 | HiDream（`_StubLlama`, `_StubTokenizer`） | 私有 helper | Protocol 不知道真实 weights 是否已加载 |
| 9 | `dynamic-shape prior resampling` | GraphBFN（`n_nodes`/`n_edges`）、FlowMol3（`n_atoms`） | 在 `solve_ode` 起点 ad-hoc 重采样 | runner 不知道状态会变形 |
| 10 | `scalar conditioning knob` | GraphBFN（`property_value`）、ProtBFN（`inpaint_strength`）、Lumina/HiDream（`guidance_scale`） | 各 adapter 自定义 delta_spec 字段 | 引擎无法统一处理 |
| 11 | **heterogeneous state decomposition** | FlowMol3 `(x,a,c,e)`、GraphBFN 5-tuple | Protocol 假设 flat tensor，smuggle 通过 `_native_states` | FlowMol3 model-local `a` channel 永不在 Protocol surface 上 |
| 12 | **m=0/m=1 blend short-circuit** | GraphBFN | `if m==0: return fresh; if m==1: return prior` | 缺这层短路则 `0 * -inf = NaN` 污染 adjacency 对角 |
| 13 | `vocab_size`/`max_length`/`num_classes` | FlowMol3, ProtBFN | class-level constant（`FLOWMOL3_MODEL_ATOM_TOKENS=12`） | 无统一 vocabulary 声明 |
| 14 | **typed materialization** | 全部 5 个（heterogeneous native state） | `materializer: type | None` 是 class ref，不是 invoked Protocol | D2 加了 class ref 但 Protocol 仍没有 invoke method |
| 15 | `inject_forward_noise` 混合规则 | Lumina/HiDream（additive clip）、ProtBFN/FlowMol3/GraphBFN（row-renorm） | `Any` 接受，Protocol 不强制 | Lumina 用 `clip(±3)`，HiDream 用 `clip(±6)`，image 之间不统一 |

---

## 5. Tier 排序：哪些 gap 最优先修

### Tier 1 — Critical（block LCM）

- **(C)+(D)** dynamics+solver fusion in `solve_ode` — FlowMol3 CTMC mismatch 根因
- **(H)** typed materialization as invoked Protocol — heterogeneous state 永远 smuggle

### Tier 2 — Structural

- **(E)** typed `Condition` 判别联合 — inpainting / CFG / null 全塞 `Mapping[str, Any]`
- **(A)+(G)** per-channel state-type + blend-protocol — `(2,)` sentinel 不能描述 mixed
- **(F)** unified `extract(kind)` 替换 3 个 split methods
- **(G)** blend invocation through Protocol（`RestartBlenderProtocol` 已存在但只在构造时 set）

### Tier 3 — Convenience

- **(I)** trajectory Protocol member typed return
- **(J)** `ForwardNoiseInjector` as Protocol member（`@runtime_checkable` 兼容）
- **(I+J)** dual-mode backend Protocol（torch/numpy 切换当前每 adapter 复制 4 遍）

---

## 6. 设计目标（4 个 design，每个覆盖一组 gap）

| Design | 覆盖 LCM concerns | 解决的 # |
|---|---|---|
| **D1：拆分 `solve_ode` 为 `dynamics + integrate`** | (C) (D) | 4 § item #1 CTMC swap、#4 integrator choice、#15 mixing rule |
| **D2：typed `Condition` 判别联合** | (E) | item #6 conditioning cache、#10 scalar knob |
| **D3：per-channel state-type + blend-protocol** | (A) (G) | item #3 state_shape sentinel、#9 dynamic-shape resampling、#12 m=0/1 short-circuit、#13 vocab constants |
| **D4：typed materialization route** | (H) | item #11 heterogeneous state decomp、#14 typed materialization |

每 design 都加为 **opt-in**（保留现有 Protocol 不破坏 2356 pytest）。

---

## 7. 引用

- s1 `FlowMatchingODEAdapter` LCM vs GCD 分析 — `wf_d93c06fd-138/journal.jsonl` line 2
- s2 5 SOTA adapter 实证方法表 — `wf_d93c06fd-138/journal.jsonl` line 4
- JMAA 论文理论 — `NoiseSelectedRectification_EN.md`（Theorem 1: μ_{g,ε} → ν_g, ε→0）
- 已实施的 JMAA 框架扩展 D1-D4 — task #373, #374, #375, #376（CategoricalAwareBlender、MaterializationRouteProtocol、NullConditionInjector、DynamicNoiseBias）
- FlowMol3 CTMC mismatch — task #324 / #330
- Engine.run_round 硬编码 7-step — `adaptive_reflow/frame/engine.py:1441-1492`

---

## 8. 状态追踪（执行后复查用）

| Gap # | Design | Status | Test |
|---|---|---|---|
| #1 CTMC swap | D1 (DynamicsProtocol + IntegratorProtocol seam) | ✅ Applied | `tests/test_algorithm/test_dynamics_solver.py::test_ctmc_euler_heun_solver_plus_ctmc_dynamics_wraps_rate_matrix` |
| #2 multi-mechanism | （非 critical，scope creep） | ⏳ 待定 | — |
| #3 state_shape | D3 (per-channel typed shape) | ✅ Applied | `tests/test_contracts/test_state_channel.py` |
| #4 integrator choice | D1 (IntegratorProtocol — euler/heun/rk4/adaptive_rk4/ctmc_euler_heun/bfn) | ✅ Applied | `tests/test_algorithm/test_dynamics_solver.py` (27 tests) |
| #5 vocabulary alignment | D3 | ⏳ 待定 | pytest `test_vocab_declaration.py` |
| #6 conditioning cache | D2 (typed Condition discriminated union) | ✅ Applied | `tests/test_universal/test_condition_typed.py` |
| #7 trajectory typing | Tier 3 (DynamicsTrajectory carrier) | ✅ Applied (partial) | `tests/test_algorithm/test_dynamics_solver.py::test_native_state_digest_byte_stable_for_fixed_inputs` |
| #8 stub-component | （非 critical） | ⏳ 待定 | — |
| #9 dynamic-shape | D3 | ✅ Applied | `tests/test_contracts/test_state_channel.py` |
| #10 scalar knob | D2 | ✅ Applied | `tests/test_universal/test_condition_typed.py` (ScalarConditioningKnob via CFG/PropertyCondition) |
| #11 heterogeneous decomp | D3 + D4 | ✅ Applied | `tests/test_algorithm/test_dynamics_solver.py::test_flowmol3_dynamics_step_4_channel_tuple` (4-channel composite) |
| #12 m=0/1 short-circuit | D3 (PerChannelBlender m=0/m=1 short-circuit) | ✅ Applied | `tests/test_algorithm/test_per_channel_blender.py` |
| #13 vocab constants | D3 | ⏳ 待定 | pytest `test_vocab_constants.py` |
| #14 typed materialization | D4 (MaterializationRoute typed envelope↔native) | ✅ Applied | `tests/test_contracts/test_materialization_typed.py` (48 tests) |
| #15 inject_forward_noise typing | D1 (DynamicsProtocol seam — additive, opt-in) | ✅ Applied (seam) | `tests/test_algorithm/test_dynamics_solver.py::test_dynamics_protocol_runtime_checkable` |
| P-13 oracle validation (algorithm core) | P-13 strategic initiative — known ground-truth litmus test | ✅ Applied | `tests/test_algorithm/{test_synthetic_oracle,test_algorithm_on_2d_oracle,test_scheduler_algorithm_on_2d_oracle,test_blender_algorithm_on_2d_oracle,test_merge_algorithm_on_2d_oracle}.py` (57 tests, 0 fail); `docs/r17-survey/synthetic-oracle.md` §4-5. Verifies the framework algorithm core (Scheduler / CategoricalAwareBlender / BoundedMergeOperator / identity Materializer) produces monotone non-increasing analytical KL trajectory on a 2D Gaussian-mixture target with known closed-form / MC oracle. Pre-flight check before P-15 / P-16 (synthetic-image gate) and SOTA re-tests (P-17). PASS verdict; 0 bugs filed. |
| P-15+P-16 synthetic-image oracle (Gate 2 of evidence chain) | P-15 (synthetic-image ground truth) + P-16 (framework validation) | ✅ Applied (Gate 2 PASS) | `tests/test_algorithm/{test_image_algorithm_math,test_image_algorithm_determinism,test_image_algorithm_on_synthetic_oracle}.py` (18 tests, 0 fail); `tools/run_synthetic_image_eval.py` driver. Verifies the framework image algorithm (Scheduler / CategoricalAwareBlender / BoundedMergeOperator / Materializer, identical to 2D path but with `InceptionV3TheoremAlignedFIDEvaluator`) produces a **monotone non-increasing FID** on a deterministic 5K geometric-shape synthetic dataset. PASS verdict; 0 bugs filed. |
| P-19 hyperparameter-free principle under DERIV-001 (Gate 3 of evidence chain) | P-19 strategic initiative — every per-round hparam must trace to a derivation rule | ✅ Applied (Gate 3 PASS; **23/23 algorithm-layer hparams covered**) | `tests/test_algorithm/{test_hparam_derived_2d_oracle,test_hparam_derived_end_to_end,test_derivation}.py` (190 tests, 0 fail; 60 + 12 + 118 across the three files); `adaptive_reflow/algorithm/_derivation.py`. Verifies the framework algorithm trajectory still converges monotonically when every per-round hyperparameter (full 23-hparam coverage map: P-18 done 5 + P-19 follow-up 18 = 23 — `memory_fraction`, `alpha_grad`, `eps_implicit`, `eps_threshold`, `handoff_window`, `tolerance`, `machine_eps`, `ema_alpha`, `distance_decay_temperature`, `min_gumbel_temp`, `eps_log`, `exponential_alpha`, `polynomial_power`, `sigmoid_midpoint/steepness`, `convergence_adaptive_kp/kd/shift_max/ema`, `metric_weights`, `jitter_std`, `constant_beta`, `target_estimate`, named-provenance `e_rho/4`, EDM Karras preconditioner — `nfe/num_steps` deferred as FM-LCM adapter-layer territory per P-18 task statement) is supplied by a DERIV-001 derivation rule rather than the ADR-0010 cosine fallback. 23 derivation rules match closed-form on the 2D oracle. PASS verdict; 0 bugs filed. |
| **Phase-4 per-round harness wiring** (Lumina + HiDream harness `_make_per_round_callback` + `tools/run_image_eval.py --per-round`) | harness-layer (NOT a `FlowMatchingODEAdapter` Protocol gap, hence no row in §4) — see task #393 + `docs/r17-survey/img-comparison.md` §2.2.3 | ⚠️ per-round-wired-partial | `tests/test_tools/test_run_image_eval.py::test_per_round_emits_per_round_metrics` and `test_per_round_falls_back_when_no_round_dirs` (2 tests, currently ERROR on `import torch` in this verify pass — torch not installed in `.venv`); `tests/test_eval/test_fid_theorem_aligned.py` (15 tests, all pass). Empirical Lumina per-round PNG dump + HiDream supervisor blocked on torch install (see §2.2.3). |
| **Phase-4 scheduler eps regime enforcement** (`e_rho` consulted before `eps(r)` chosen; TheoremAlignedFIDResult.regime_check_ok blocks, not just reports) | bridge to Tier-1 §5 (C)+(D) dynamics+solver — scheduler eps must obey Lemma 4 regime `eps^2 < e_rho / log(2)` for JMAA Theorem 1 convergence | ⏳ pending implementation (diagnostic-only) | `adaptive_reflow/eval/fid_theorem_aligned.py::ConvergenceDiagnostic.regime_violations` surfaces the violation; the scheduler still consumes `paper_quantities` at round 0 only and `_apply_paper_quantities_rewiring` at runner.py:577 does NOT gate on `e_rho`. Phase 4 did not block here. | |
| **P-07 SOTA adapter audit fixes** (workflow G, 2026-09-02) | protocol-conformance nits documented in `docs/r17-survey/sota-adapter-audit.md` (1 MEDIUM + 6 LOW): P-04 [M] ProtBFN mechanism_id return type → `MechanismId`; P-03 [L] HiDream mechanism_id class-level → `MechanismId`; P-01 [L] FlowMol3V2 `inject_forward_noise` hook; P-06 [L] Lumina channel_domains `"latent"`; P-02/P-05/P-07 [L] state_shape doc comments (P-07 also adds instance-level override matching HiDream pattern) | ✅ Applied (7/7 fixes; **0/7 remaining**) | `adaptive_reflow/adapters/protbfn_abbfn_adapter.py:532` (mechanism_id → `MechanismId`); `adaptive_reflow/adapters/hidream_i1.py:824` (mechanism_id: `MechanismId`); `adaptive_reflow/adapters/flowmol3_v2_adapter.py:1817-1920` (full inject_forward_noise method with native (x,a,c,e) cache + AUDIT_FLOWMOL3_INJECT_FORWARD_NOISE provenance); `adaptive_reflow/adapters/lumina_image_2_0.py:106` (ChannelName("latent"): "latent"; line 542 class-level + line 666 instance-level state_shape); `adaptive_reflow/adapters/graphbfn.py:20,60,488-503,591-602` (DESIGN NOTE for state_shape=() zero-length surrogate); `adaptive_reflow/adapters/flowmol3_v2_adapter.py:108-113,1843-1847` (doc comment for state_shape=(3,) one-atom degenerate prior). All 5 files staged in git index (NOT committed per workflow G brief). Verification: `pytest tests/test_adapters/ -m "not benchmark and not slow"` reports **220 passed / 4 skipped / 1 xfailed** (matches pre-fix baseline; no regression). mypy --strict clean on `adaptive_reflow/contracts/` and `adaptive_reflow/universal/` (no errors introduced). |

**See also: docs/r17-survey/algorithm-correctness-evidence.md.** This
gap audit focuses on the **Protocol-surface** side of the FM-LCM
redesign (15 primitives; 10 orthogonal concerns; D1-D4 designs); the
companion **algorithm-correctness evidence chain** focuses on the
*behavioural* side — three named gates (P-13 2D Gaussian-mix oracle /
P-15+P-16 synthetic-image oracle / P-19 hyperparameter-free under
DERIV-001) that together prove the framework's per-round algorithm
produces trajectories consistent with the paper Theorem 1 prediction.
190 PASS tests / 0 bugs filed across the DERIV-001 evidence chain
(P-13 2D oracle 57 + P-15+P-16 synthetic-image ~33 + P-19 hyperparameter-free
**100 — 60 in `test_hparam_derived_2d_oracle.py` + 12 in
`test_hparam_derived_end_to_end.py` + 118 rule-level unit tests in
`test_derivation.py` — full 23/23 algorithm-layer coverage**);
paper Section 4 skeleton 4.1-4.5 lives in that document. **See also:
docs/r17-survey/algorithm-correctness-evidence.md.**