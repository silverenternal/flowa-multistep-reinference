# JMAA Theorem 1 真实应用盘点(基于代码 grep)

**核心定理**:`BL(mu_{g,eps}, nu_g) ≤ A_g · exp(-NFE/B_g) + C_g · e_rho`
**四个 paper quantities**:`A_g` (Lipschitz aggregate), `B_g` (NFE decay), `C_g` (residual bias), `e_rho` (exterior gap)

## 应用 1: Scheduler (CLM-005, CLM-006, CLM-011) — paper 已说
- `CosineAnnealScheduler`: consumes A_g (smoothing ramp)
- `CodimensionSheetScheduler`: consumes (A_g, B_g, C_g) → n_cap closed form
- `EvidenceDrivenScheduler`: consumes full quadruple → policy per-cell restart
- `TierAwareCodimensionSheetScheduler`: wrapper + per-zone n_cap *= 0.5
- `ConvergenceAdaptiveScheduler`: consumes W2 history → PID-lite shift
- `NFEAwareMemoryScheduler`: consumes NFE budget → memory_fraction
- `PaperRatioAdaptiveScheduler`: consumes paper quantities via base
- `FreeTrajScheduler`: trajectory-aware

## 应用 2: Solver (算法层) — paper 没明说
`solver.py:41-45`:
> "e_rho / 4 (paper Lemma 5) is consumed as the minimum step-size floor"
> "A_g sheet evidence (paper Lemma 2) can be supplied via paper_quantities argument as an initial dt hint"

→ 求解器层面用 **e_rho** 做 dt 下限(防止 step size 太小导致 posterior 偏离 fibre)
→ 求解器层面用 **A_g** 做 dt 初始 hint

**这是架构设计上的深层应用**:每个 step 的 dt 被 **e_rho** clamped 在 [e_rho/4, ∞)。如果 e_rho = 0(posterior 退化到 fibre 之外),framework 自动用 floor 兜底。

**paper 里没明确说这个 — 这是 framework design depth**。

## 应用 3: Integrator — 数值稳定
`integrator.py:22+`:
> "When paper_quantities is None (or a query that doesn't expose paper_quantities), the integrator falls back to legacy MFPQA behavior"

→ 数值积分时,如果 paper_quantities 提供,integrator **用 paper 框架的稳定路径**(没有 paper_quantities 走 legacy MFPQA path)。

## 应用 4: Dynamics (时间步 / dt 控制) — paper 没明说
`solver.py:269-303` + `dynamics.py:135+`:
> "dt is passed for paper-quantity gating (e.g. e_rho / 4 floor)"

→ 在所有 ODEStep 调用里,**dt 受 paper 定理 1 的 Lemma 5 约束**。这不是 scheduler 层的事,是 **底层数值积分** 的事。

`dynamics.py:742-745`:
```python
if paper_quantities is not None:
    e_rho = float(paper_quantities.exterior_gap_e_rho)
    if math.isfinite(e_rho) and e_rho > 0.0:
        floor = e_rho * EXTERIOR_GAP_FLOOR_FRACTION
```
**这是 framework-wide 的数值保险**:每个 ODE step 都不会让 dt 低于 paper 定理 1 推导的下限。

## 应用 5: Perturbation (per-round 噪声调度) — paper 没明说
`dynamic_noise_bias.py:22`:
> "eps(r) = max(e_rho/4, sheet_A * (1 - r/(L-1)))"

→ 每个 round r 的噪声幅度 **eps(r)** 被 **e_rho/4** floor 兜底 + sheet_A 的渐降。
**这才是 framework-level theorem 应用**:round noise 直接由 theorem 1 推导。

## 应用 6: Merge Operator (BRAI + BoundedMerge) — paper 已说
- `BoundedMergeOperator` consumes `e_rho` 做 merge-floor (BRAI)
- paper §1 已经声明这个

## 应用 7: Policy Driver (policy level) — paper 没明说
- `adaptive_reflow/algorithm/policy_driver.py` 也消费 paper_quantities

## 应用 8: Evidence Driver (Loop 2 closure) — paper 已说 (C4)
- `EvidenceDrivenScheduler` 闭合 Loop 2:paper-quantities → scheduler feedback

## 应用 9: FID Theorem-Aligned (image evaluation) — paper 没明说
`adaptive_reflow/eval/fid_theorem_aligned.py:47-50`:
```python
FID(r) <= C_paper * eps_r
where C_paper = (C_g * B_g + 1 / e_rho) / A_g
```
**这是 FID 的 paper-quantity bound**!Image-space FID 也被 theorem 1 的常数约束:
- 每个 round r 的 FID 必须满足 `FID(r) ≤ (C_g * B_g + 1/e_rho) / A_g * eps_r`
- 这是 **regression gate**:framework 跑完 r round 后,FID 不能超过这个 bound

**这是 framework 把 theorem 1 应用到 image 评估的关键 insight** —— paper 完全没提过 image FID 能用 paper 4 量 bound。

## 应用 10: Lipschitz Diagnostic (Planar BL convergence) — paper 核心
`adaptive_reflow/eval/lipschitz_diagnostic.py`:
> "planar_bl_convergence_witness" — 在 R^2 上**真实计算** BL distance
> "bounded_lipschitz_distance_2d" — exact BL between planar empirical measures
> theorem1_bl_convergence_witness + Theorem1StatementChecker

→ 这是 **theorem 1 的直接验证工具**:在 R^2 平面上,直接 BL(mu_{g,eps}, nu_g) 数值算出,跟 theorem 1 的 closed-form bound 对比。

**这是 framework 把 theorem 1 "可执行化" 的核心**。

## 应用 11: Posterior Selection Evaluator (CLM-003, CLM-004)
- `selection_ratio = sheet_evidence / (sheet_evidence + cell_evidence)` = A_g vs C_g 的比值
- paper §3.1 已经有这个

## 应用 12: Checkers (paper-quantity surface assertions)
- `adaptive_reflow/theory/checkers.py:182-184`:
> "posterior_evidence = A_g (sheet evidence floor from sheet_evidence_A)"
> "root_cell_mass = C_g * B_g * eps^2 per-round"

→ **framework 内部的一致性检查**:验证 framework 跑出来的数值跟 theorem 1 推导一致。

## 应用 13: profile_residual_fn (adapter-level)
- `adaptive_reflow/adapters/profile_residual.py:38-45`:
> "root_cell_packing_B correctly returns B_g = 0 (a degenerate case where the bound degenerates to C_g · e_ρ). The sin(s) factor restores the bound and preserves the empirical information: A_g still reflects the data, but the cell-packing coefficient B_g is now positive"

→ **adapter 的 profile_residual_fn 必须输出非零 B_g**(否则 theorem 1 退化),framework 通过 sin(s) 修补。

## 应用 14: Sheet Evidence + Cell Evidence (CLM-001, CLM-002)
- `posterior_selection_evaluator.py:279+`:sheet_evidence / cell_evidence 是从 endpoints(实测)算的,不是从 g 推的
- paper §2.5-§2.8 已经有这个

## 应用 15: Regime Selector — paper 没明说
- `adaptive_reflow/algorithm/scheduler/regime_selector.py:793-798`: 引用 `exterior_gap_e_rho`
- 这是 regime detection(framework 应该跑哪个 regime)

## 应用 16: Solver-level paper-quantities proof (`adaptive_reflow.algorithm._derivation`)
- paper `docs/theory/theorem1_rate_bound.md` 的 companion doc 在 framework 里

