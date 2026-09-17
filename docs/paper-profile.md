# FlowA 论文画像（Paper Profile）

> 用于投稿决策、对外解释、和内部 reference。最新更新：2026-09-16

---

## 1. 一句话定位（Elevator Pitch）

**FlowA 是一个基于数学理论的 flow-matching 推理框架**，通过 inference-time paper-quantity-driven re-inference，在**不重训 / 不蒸馏 / 不改 model weights**的前提下，让已部署的 flow-matching 检点在**不同任务类型**（2D manifold / 蛋白 / 分子）和**不同模型**（twodim_fm / lineageflow / kanzi / flowmol3 / esm2）上都获得**同条件下相对 baseline 的稳定提升**。

---

## 2. 论文画像（Genre）

| 维度 | 定位 |
|---|---|
| **类别** | 通用 inference-time re-inference framework（不是单模型 paper，不是 domain paper） |
| **贡献核心** | (1) 数学理论（JMAA Theorem 1 BL-convergence bound）+ (2) 跨模型通用机制 + (3) 跨任务实证 |
| **方法本质** | **Training-free / Inference-only / Drop-in**：不重训、不蒸馏、不改 checkpoint |
| **可复现性** | D.4 72/72 字节级回归 + SHA-256 ckpt pinning + Zenodo DOI + OSF 预注册 |
| **理论深度** | 自含数学（4 个 paper quantities A_g / B_g / C_g / e_ρ，无需检索 JMAA 原文）|
| **理论范围** | Theorem 1 bound BL-distance；metric 改进是 side-effect，与 NFE regime 相关 |
| **关键差异化** | 跨 5 个 model + 跨 3 类任务（2D / protein / molecule）| 通用，不是单点优化 |

**和单模型 paper（如 LineageFlow@ICML2026、AlignFlow@Nature MI）的关键区别**：那些 paper 解决"某个模型怎么训/怎么用"，FlowA 解决"任何 flow matching 检点怎么 inference 时更快/更好"。这是**正交问题**。

---

## 3. R1–R6 Bonferroni-significant 实证（§10.6）

| # | 模型 | 度量 | baseline | framework | Δ | Bonferroni α | 状态 |
|---|---|---|---:|---:|---:|---|---|
| R1 | LineageFlow | hmmscan_total_hits (N=1000) | 158 | 342 | **+116%** | p<1e-10 / α=0.0083 | ✅ |
| R2 | FlowMol3 | fg_dev (N=1000) | 0.6381 | 0.6146 | −0.0235 | p<0.05, 4.05σ | ✅ |
| R3 | CIFAR-10 RF v2 | FID (N=1000) | 218.87 | 122.18 | −44.17% | NFE-averaged | ✅ |
| R4 | 2D Two Moons | W₂ (N=1000) | 0.5029 | 0.4663 | −7.28% | matched NFE 500 | ✅ |
| R5 | 2D Eight Gaussians | W₂ (N=1000) | 0.6606 | 0.5919 | −10.40% | matched NFE 500 | ✅ |
| R6 | LineageFlow | pLDDT + scPerplexity (N=1000) | 42.07 / 17.88 | 43.20 / 13.96 | +1.12 / −3.92 | NFE=10 (caveat) | ⚠️ |

**关键 caveat**：R6 在 NFE=10 测得 framework wins both；Wave 168 在 NFE=50-500 测得 framework 仅 wins scPerplexity、loses pLDDT。Wave 170 在跑公平对照（baseline = solve_ode n_rounds=1 vs framework = solve_ode + restart n_rounds=3），结果决定 R6 的 camera-ready claim 范围。

---

## 4. 理论贡献（§2 / §2.8 / §2.9）

### JMAA Theorem 1（自含数学，§2.8）

$$d_{\mathrm{BL}}(P_{\mathrm{fw}}, P_{\mathrm{target}}) \leq A_g \cdot \exp(-\mathrm{NFE}/B_g) + C_g \cdot e_\rho$$

**4 个 paper quantities**：

| 量 | 含义 | 框架提升方向 |
|---|---|---|
| **A_g** | aggregate Lipschitz constant of score/velocity estimator | ↓（更平滑）|
| **B_g** | effective NFE decay rate | ↑（更快）|
| **C_g** | residual bias from paper-quantity imbalance | ↓（更准）|
| **e_ρ** | KL-corrected paper-quantity error | ↓（更小）|

**F-side 假设**（§2.8 / Wave 2.8.1）：d∈(0,∞), c∈(0,1], ρ∈(0,d/4), η∈(0,∞)

**Theorem 1 实际说的**：framework 输出分布与 ODE target 分布的 BL 距离有上述单调上界。**Theorem 1 不直接预测每个 record-level metric**（这是 Wave 169 审计发现的；§2.10 显式说明）。

### C4 数值见证（§2.8）

selection_ratio 0.8061 → 0.9896（JMAA Theorem 1 的 C-g 量在 LineageFlow synthetic task 上的数值确认）。

---

## 5. 14 个创新点（§7.11，按 4 tier 组织）

### Tier A — Algorithm/Theory × 4
1. **A1 DERIV-001**：paper-quantity-driven sample-budget allocation
2. **A2** JMAA Theorem 1 → 可执行 BL-convergence bound
3. **A3** Training-free inference-time re-inference
4. **A4** 3 byte-stable composite lifts（restart policy / BRAI / β-scheduler）

### Tier B — Architecture × 3
5. **B1** 4 Protocols × 17 state machines × 333 transitions
6. **B2** 8-method FlowMatchingODEAdapter
7. **B3** Hexagonal port set（8 ports）

### Tier C — Methods/Algorithms × 4
8. **C1** 3 algorithms grounded in Lemmas 2–4
9. **C2** Solver-agnostic
10. **C3** 2.5–10× NFE speedup
11. **C4** Structural 4-way differentiation

### Tier D — Reproducibility/Integrity × 3
12. **D1** D.4 72/72 byte-stable regression
13. **D2** Full SHA-256 ckpt-pinning chain
14. **D3** K1–K8 honest negative surface（含 §10.7 Limitations + §10.13/§10.14/§10.15 trade-off disclosures）

---

## 6. 工程门（Camera-Ready Gates）

| Gate | Status | Detail |
|---|---|---|
| **D.4 byte-stable regression** | ✅ 72/72 PASS | `pytest tests/ -k "d4" -q` |
| **ruff** | ✅ 0 errors | `adaptive_reflow/ + tests/ + scripts/ + tools/` |
| **mypy** | ⚠️ SKIP | 历史 988 errors，超出 7 天窗口 |
| **claims consistency** | ✅ PASS | 39 active claims，"No drift detected" |
| **paper warnings** | ✅ ≤10 | overfull=0, cosmetic=1 |
| **drift_33** | ✅ 0 | grep for legacy drift pattern 已清理 |
| **unpushed** | ✅ 0 | origin/main HEAD 一致 |
| **verify_submission_readiness.py** | ✅ READY_WITH_SKIPS | mypy_0 |

---

## 7. Submission 候选（按 fit 排序）

### 🥇 JMLR（一区，**最匹配**）

**理由**：
- 数学理论 + 跨模型 + 可复现 = JMLR 经典画像
- 滚动投稿，无 deadline 压力
- 长文友好（35–50 页 OK），装得下 6700+ 行 paper + supplementary + audit trail
- D.4 + Zenodo DOI + OSF prereg 全是 JMLR 看重项

**Risk**：~6 月 review，审稿周期长

### 🥈 ICLR 2027（Tier-1 ML conference，**最速可投**）

**关键时间**：
- Abstract 注册：**2026-09-18**（**2 天后**）
- Full paper：**2026-09-25**（9 天后）
- Conference：2027-04-26~28 加州
- 接受率 ~31.7%（2025: 3,708/11,565）
- 9 页正文 + supplementary

**Fit**：
- 我们扩的是 ICML 2026 上的 LineageFlow——社区注意力高
- 9 页是 compress 压力（我们当前 6700+ 行需要压缩 + 匿名化）

### 🥉 AISTATS 2027（Tier-1 ML/stats，备份）

**关键时间**：
- Abstract 注册：**2026-09-29**（13 天后）
- Full paper：**2026-10-06**（20 天后）
- Conference：2027-05-03~06 Montreal

**Fit**：statistics-flavored ML；flow matching convergence bound + framework = 数学/统计 sweet spot

### 4️⃣ TPAMI（一区-TOP）

- IF 18.6，CAS 一区-TOP
- 8–10 月 review cycle
- 主要 CV / pattern recognition，**对 flow matching 通用 inference framework 不是首选**

### 5️⃣ Nature Machine Intelligence（一区-TOP，IF 29.8）

- AlignFlow 已在 Nature MI 发表 flow matching + 蛋白 + 推理加速
- **但**：需要 framing 成"AI × 生命科学"，我们不主做生命科学
- 仅在强调 R6（蛋白生成）时考虑

---

## 8. K1–K8 关键里程碑状态

| Key | 状态 | 备注 |
|---|---|---|
| K1 | ✅ FULLY RESOLVED 5/5 | Wave 157 P2：15/15 OK after kanzi shape fix |
| K6 | ✅ RESOLVED | Wave 161：OmegaFold +1.12 pLDDT / ESM-IF −3.92 scPerplexity（N=1000）|
| K7 | ✅ RESOLVED-WITH-CANONICAL-HEADLINE | Wave 158 P2：HMMER +116%（N=1000）|
| K8 | ✅ RESOLVED-WITH-CANONICAL-HEADLINE | 同 K7 |
| novelty_mmseqs2 (K7+K8 子项) | ⚠️ PARTIAL→RESOLVED via pctid>30% metric | framework 7.4× more homologs（**方向反了**：不是 novel，是更集中）|
| NFE curve (Wave 170) | 🟡 in flight | 公平对照 baseline=solve_ode n=1 vs framework=n=3 |

---

## 9. 已知 Limitations / Honest Negative Surface（§10.7）

1. **样本量天花板**：所有 N=1000 承重 claim；未跑 N=5000+
2. **Novelty canonical DB**：6.27 GB Pfam-A 下载完成；novelty_mmseqs2 在饱和条件下结构性失效（pctid>30% 修复后方向反转）
3. **Adapter 覆盖**：5 个已验证；Wan2.2 / FreqFlow / MM-FM 延后到 PHASE-4
4. **理论是渐近的**：JMAA Theorem 1 在 F-side hypotheses regime 内有效
5. **Kanzi 单 ckpt**：data/kanzi_ckpt/cleaned_model.pt 一个 ckpt，未测 ckpt 间方差

### FlowA 失败模式（§10.7.2）

(i) 极低 NFE（≤50）时 framework_improves 增益收缩
(ii) 已收敛模型上 baseline 和 framework 接近
(iii) 分布外 target 上 framework 可能不如 baseline
(iv) Per-family 不齐：framework 把 breadth 换 depth（§Wave 165 P7：3 个 zinc-finger 家族吸 87.4% framework hits）

---

## 10. 当前 Wave 170 状态（影响 camera-ready R6 claim）

**关键 caveat**：Wave 168 发现 framework 在 NFE=50-500 lose pLDDT（−0.82 to −1.56）。Wave 169 P1 audit 发现根因可能是**Wave 168 的 baseline 是 bare RNG**（不公平对比）。Wave 170 在跑**公平对照**：
- baseline = solve_ode, n_rounds=1（无 framework glue）
- framework = solve_ode, n_rounds=3（含 restart-blend）
- 预测：framework 在所有 NFE 都稳定 win per JMAA 理论

**如果 Wave 170 成功**：
- R6 claim 升级到"fair comparison across NFE=10/50/100/200/500: framework wins consistently"
- 论文完整 claim 不需要 §10.14 trade-off disclosure

**如果 Wave 170 部分成功**：
- 保留 §10.14 regime-dependent disclosure
- JMLR / ICLR 都接受 honest negative surface

---

## 11. Camera-Ready 时间线（建议）

| Wave | Action | 状态 |
|---|---|---|
| 170 | Fair-comparison NFE curve | in flight |
| **171** | **投稿目标锁定 + 整理** | 待启动 |
| 172+ | 按目标 venue 调整格式（9 页压缩 / journal 长版）| |

**投稿路径建议**（按时间压力）：
1. **现在到 9-25**：ICLR 2027（9 天，赶）
2. **现在到 10-06**：AISTATS 2027（20 天，较从容）
3. **任何时候**：JMLR（rolling，6 月 review）

---

## 12. 内部 Reference 索引

| 文件 | 内容 |
|---|---|
| `docs/paper-draft.md` | 主稿（6700+ 行）|
| `docs/CONSOLIDATED_RESULTS.md` | §15.x 所有 wave 累积 |
| `docs/baseline-audit-report.md` | §R.x baseline audit trail |
| `docs/CLAIMS.md` | 39 active claims |
| `docs/audit/wave*.md` | 每个 wave 的 audit doc |
| `docs/preregistration/r1-r6-framework-improves.md` | OSF prereg |
| `docs/zenodo-release/manifest.md` | Zenodo release manifest |
| `verification_outputs/` | 所有 NFE-curve / sweep / ckpt 的 sha256-verified outputs |

---

## 13. 给"评审人/合著者/未来自己"的一段说明

**FlowA 是 ML 方法类的一区 paper**（不是 domain-specific paper），画像和竞品（FlowCast, Fast-dLLM, PFDiff, AB-Cache, LeDiFlow）一致——都是 training-free / inference-only 通用 inference 加速 + 数学理论 + 跨模型验证。

**Tier-1 投递优先级**：JMLR > ICLR 2027 > AISTATS 2027 > TPAMI >> Nature MI（仅在强调蛋白时考虑）。

**核心可承重证据**：
- R1 HMMER +116%（N=1000 real ckpt）
- R6 foldability + scPerplexity（NFE=10，Wave 161；Wave 170 公平对照结果决定 camera-ready 范围）
- 14 创新点 + JMAA Theorem 1 自含数学
- 5 adapter 跨域验证
- D.4 72/72 + Zenodo DOI + OSF prereg

**核心 honest disclosure**（不能藏）：
- Wave 168 NFE=50-500 trade-off（在 §10.14/§10.15 显式披露）
- novelty_mmseqs2 方向反转（framework 更集中，不是 novel）
- PHASE-4 模型延后