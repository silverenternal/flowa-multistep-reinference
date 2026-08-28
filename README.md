# FlowA Multi-Step Re-Inference

Adaptive reflow 和多步复推理控制：round orchestration、restart memory、condition control policy、外部反馈接口和重启计划。

## Status

- Stage: prototype, active development
- Self-assessment: B+ (algorithm depth + engineering discipline; not ready
  for production use)
- Test count: 1235 passing / 7 skipped (torch-gated)
- Last audit: 2026-08-28 (see [`docs/INSIGHTS.md`](docs/INSIGHTS.md) and
  [`docs/ABLATION.md`](docs/ABLATION.md))
- Honest gaps: see [`docs/lean/GAPS.md`](docs/lean/GAPS.md)

## Architecture at a glance

The framework is **four pluggable layers wired by four feedback loops** —
not a pile of independent algorithms. Every algorithm in the table is
loaded by the loop it participates in.

```mermaid
flowchart TB
    %% Layer 4: Adapters (framework drives these)
    subgraph L4["Layer 4: Adapter Protocol (8 concrete adapters)"]
        TW[TwoDimFMAdapter<br/>2-moons / 8-gaussians]
        RF[ReferenceFlowAAdapter]
        FM[FlowMol3Adapter]
        SY[SyntheticAdapter]
        TG[ToyGaussianAdapter]
        TL[ToyLinearAdapter]
        RDK[RDKitOracle]
    end

    %% Layer 3: 4-protocol composition (the framework-internal algorithm layer)
    subgraph L3["Layer 3: 4-protocol composition (algorithm/)"]
        SC[SchedulerProtocol<br/>8 + 1 = Cosine/Linear/Exp/Poly<br/>Sigmoid/Const/ConvAdapt<br/>CodimensionSheet/Sequential]
        PD[PolicyDriverProtocol<br/>ScheduleDerived<br/>Constant<br/>Adaptive]
        MO[MergeOperatorProtocol<br/>BoundedMerge<br/>Identity<br/>EMA]
        RB[RestartBlenderProtocol<br/>Linear<br/>DistanceDecay]
    end

    %% Layer 2: Orchestration
    subgraph L2["Layer 2: Engine + Runner (orchestration)"]
        EN[Engine.run_round<br/>fail-closed, audit, capability check]
        RI[ReInferenceRunner<br/>multi-round + per-round metric]
        BT[BatchedTrajectoryRunner<br/>batched trajectories + endpoint metric]
    end

    %% Layer 1: Contracts + Metrics + Paper quantities
    subgraph L1["Layer 1: Contracts + Metrics + Paper quantities"]
        PQ[paper_quantities<br/>A_g / B_g / C_g / e_rho]
        ESG[EvidenceScaleGapMetric<br/>paper Theorem 1 witness]
        W2M[W2 / Coverage / Energy distance]
        BLD[Bounded-Lipschitz metric<br/>μ → ν distance]
    end

    %% Forward edges (top-down data flow)
    L1 --> L2
    L2 --> L3
    L3 --> L4

    %% Composition edges within Layer 3
    SC -->|n_cap| PD
    PD -->|beta| MO
    MO -->|merged_value| RB

    %% Loop 1: scheduler self-feedback (PID-lite)
    L2 -.->|W2 feedback| SC

    %% Loop 2: paper_quantities drives scheduler (theory-grounded)
    PQ -.->|A_g, B_g, C_g, e_rho| SC

    %% Loop 3: metrics feed runner (selection_ratio → next round n_cap)
    ESG -.->|selection_ratio| L2

    %% Loop 4: ledger chain integrity
    L2 -.->|hash chain| L1

    %% Emergent behaviour (cannot be done by any single layer)
    EB["Emergent:<br/>paper Theorem 1<br/>numerical witness<br/>(SNR 60.8:1)"]:::emergent
    L1 & L2 & L3 & L4 -.-> EB

    classDef emergent fill:#fff4e1,stroke:#cc6600,stroke-width:2px,color:#000
```

### The four feedback loops

| Loop | Path | What it does |
|---|---|---|
| **1. Self-reflexive** | `scheduler → driver → engine → metric → scheduler.record_round_feedback` | The scheduler reads its own last-round output (W2) and updates the next round. This is what makes `ConvergenceAdaptiveScheduler` work — the framework is not executing a fixed schedule, the schedule is being *shaped* by the metric. |
| **2. Theory-grounded** | `paper_quantities.{A_g,B_g,C_g,e_rho} → CodimensionSheetScheduler._paper_evidence_balance` | The four paper invariants are computed from the user-supplied profile and feed the scheduler directly. paper math → algorithm parameters, no intermediate. |
| **3. Hash-chained integrity** | `engine.LedgerRow_r.prev_hash = LedgerRow_{r-1}.row_hash` | Round r's hash contains round r-1's hash. Tampering with any round breaks the chain. This is Temporal-style event sourcing applied to per-round inference. |
| **4. Symmetric round** | `scheduler.inject_noise (forward) ↔ blender.merge (reverse)` | Each round has a symmetric noise model: forward noise injection and reverse bounded merge. This is what lets the round be replayed byte-for-byte. |

### What this is not

- **Not a pile of independent algorithms.** Removing any layer collapses an
  emergent behaviour (see the dashed arrows). For example, deleting
  `paper_quantities` reduces CodimensionSheetScheduler to a constant
  function and loses the `selection_ratio → 1` Theorem-1 witness.
- **Not a wrapper around an existing sampler.** The framework *is* the
  algorithm layer. Plugging in a different sampler family (e.g. an
  EDM-style sampler) requires implementing the four protocols and a
  Protocol-conforming adapter — but the algorithm layer above it is
  unchanged.

Scope note: the engine is implemented for its current target domains
(2D flow matching adapters and the paper-quantity contracts). Other model
families are supported at the Protocol level only — no adapter for them
ships in this tree.

## Adapter interface

The authoritative contract for any Flow Matching model that wants to plug
into the engine is **[`docs/ADAPTER_INTERFACE_SPEC.md`](docs/ADAPTER_INTERFACE_SPEC.md)**.
It defines:

- The eight-method `FlowMatchingODEAdapter` Protocol every adapter must satisfy.
- The capability handshake (`AdapterCapabilities` dataclass) — fail-closed at registration.
- The `RestartMixer`, `EnvelopeCriterion`, and `Evaluator` Protocols.
- The per-round lifecycle (11-step orchestration).
- Hard rules (no torch, deterministic seed, opaque TensorRef, etc.).
- A worked example: `ToyLinearAdapter` (≤ 60 lines).

The molecule package (`adaptive_reflow/molecular/`) is one concrete
implementation of this spec. Any other model family — latent image FM,
discrete CTMC FM, audio FM, etc. — plugs in by implementing the same
Protocols, declaring its own channel vocabulary, and registering its
own mixer / envelope / evaluator. The universal layer (`adaptive_reflow/universal/`)
is intentionally molecule-free; an AST-level test guard enforces the
invariant.

## Package layout

The post-refactor layout is a single importable Python package,
`adaptive_reflow/`, with twelve peer subpackages, each owning one concern:

```
adaptive_reflow/
├── contracts/    <- frozen typed dataclasses + NewTypes (DTB-R0/R1/R2/R4/R5/NC1/NA1/L1/L2/S1)
├── universal/    <- model-family-agnostic kernel: FlowMatchingODEAdapter / RestartMixer /
│                  EnvelopeCriterion / Evaluator Protocols + stdlib-only carriers + validators
│                  (ZERO molecule-specific imports; enforced by AST-level test guard)
├── envelope/     <- runtime envelope + tail-budget machinery (DTB-NC1 + DTB-L3 partial)
├── molecular/    <- concrete pocket-conditioned 3D flow matching implementation of the
│                  universal Protocols: molecule channel vocabulary, molecule bundle,
│                  molecule envelope manifest, RMS-preserving restart mixer,
│                  GNINA/PoseBusters/QED/ADMET evaluator arms
├── frame/        <- universal round frame: engine + adapter protocol + bounded merge + channel rule
│                  + operation order + phase + trace v3 + orchestrator
├── policy/       <- pure decision logic (DTB-R4 + DTB-L3 + DTB-L4 calc)
├── schedule/     <- outer restart-noise schedule (DTB-NA1)
├── diagnostics/  <- observation-only ledgers (DTB-L4 observe leg)
├── writer/       <- single-writer authority + registry + audit + core-runtime handoff
├── adapters/     <- concrete FlowMatchingODEAdapter implementations (DTB-G1 + DTB-G2)
├── eval/         <- CPU-only DTB-R7 + DTB-R8 evaluation / reporting
└── legacy/       <- quarantine: pre-refactor torch-bound / pocket_modules-coupled modules
```

### Universal core vs molecular concrete implementation

`adaptive_reflow/` is organised as a **two-layer split**:

* **`universal/`** is the model-family-agnostic kernel. It declares the
  `FlowMatchingODEAdapter`, `RestartMixer`, `EnvelopeCriterion`, and
  `Evaluator` Protocols together with stdlib-only carriers and validators.
  **It has zero molecule-specific imports** — verified by
  `tests/test_universal/test_no_molecular_import.py`.
* **`molecular/`** is the pocket-conditioned 3D flow matching *concrete*
  implementation of those universal abstractions. Every molecule-specific
  dataclass, channel vocabulary entry, and Protocol impl lives here.

**Invariant (load-bearing):** `universal/` has zero molecule-specific
imports; `molecular/` implements universal abstractions.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full governance doc —
layered structure, dependency direction rules, public API surface per
subpackage, the Adapter Protocol recipe for adding a new model, and the
file inventory.

## How to import

Every subpackage exposes a narrow, curated public surface via its
`__init__.py`. Import directly from the subpackage you need:

```python
# Contracts (frozen dataclasses + NewTypes + validators; stdlib-only)
from adaptive_reflow.contracts import (
    RoundResultBundle,
    ChannelTransferEvidence,
    PhaseState,
    CosineScheduleConfig,
    ArchiveQuota,
    RestartPolicyAuthorityContract,
    FinalRestartPolicy,
)

# Universal (model-family-agnostic kernel; stdlib-only; zero molecule imports)
from adaptive_reflow.universal import (
    FlowMatchingODEAdapter,    # Protocol — the canonical engine surface
    RestartMixer,              # Protocol — coordinate blender
    EnvelopeCriterion,         # Protocol — envelope ladder
    Evaluator,                 # Protocol — per-channel scorer (R7)
    StateBundle,               # carrier
    AdapterCapabilities,       # capability handshake
    EnvelopeClassification,    # carrier
    validate_capabilities,
    validate_state_bundle,
)

# Molecular (concrete pocket-3D flow matching impl of the universal Protocols)
from adaptive_reflow.molecular import (
    MOLECULE_CHANNELS,
    MoleculeChannel,
    MoleculeRoundResultBundle,
    MoleculeEnvelopeManifest,
    MoleculeEnvelopeClassification,
    MoleculeStratum,
    MoleculeStratumAssignment,
    RMSPreservingCoordinateMixer,        # concrete RestartMixer Protocol impl
    GNINAEvaluator,                      # concrete Evaluator Protocol impl
    PoseBustersEvaluator,                # concrete Evaluator Protocol impl
    QEDEvaluator,                        # concrete Evaluator Protocol impl
    ADMETEvaluator,                      # concrete Evaluator Protocol impl
)

# Frame (the universal round driver)
from adaptive_reflow.frame import (
    Engine,
    FlowMatchingODEAdapter,    # Protocol (re-exported from universal/ for back-compat)
    StateBundle,
    bounded_merge,
    compute_channel_decision,
    RoundTraceV3,
    AdaptiveReflowPolicyOrchestrator,
)

# Policy (pure decision logic)
from adaptive_reflow.policy import (
    SameSampleArchive,
    PruneGate,
    Stratum,
    physical_noise_proxy,
)

# Schedule (DTB-NA1)
from adaptive_reflow.schedule import (
    CosineScheduleSampler,
    n_cap_for_round,
    validate_cosine_schedule_config,
)

# Diagnostics (observation-only; never influences beta/claim/prune)
from adaptive_reflow.diagnostics import (
    FreshNoiseCumulativeMassRecord,
    empty_diagnostics,
)

# Writer (single-writer authority + registry + audit + handoff)
from adaptive_reflow.writer import (
    WriterArbitrator,
    build_final_restart_policy,
    CoreRuntimeHandoff,
    CandidateRegistry,
    AuditTemplate,
)

# Adapters (concrete FlowMatchingODEAdapter implementations)
from adaptive_reflow.adapters import (
    FlowMol3Adapter,
    ReferenceFlowAAdapter,
    SyntheticContinuousAdapter,    # also used by parity harnesses
)

# Eval (DTB-R7 calibration + paired evaluation; DTB-R8 claim gate + promotion + rollback)
from adaptive_reflow.eval import (
    wilson_lower_bound,
    beta_lower_bound,
    ClaimGateConfig,
    evaluate_claim_gate,
    build_deferred_promotion_report,
    apply_rollback,
    LayeredMetricPanel,
)
```

`adaptive_reflow.legacy/` is intentionally **not** re-exported. Importing it
emits a `DeprecationWarning`; nothing new should depend on the legacy
torch-bound modules.

## Adding a new model adapter

The protocol is `FlowMatchingODEAdapter` in `adaptive_reflow.frame.adapter`.
See [`ARCHITECTURE.md` §5](ARCHITECTURE.md#5-adapter-protocol--how-to-add-a-new-model)
for the four-step recipe.

In short:

1. Subclass `FlowMatchingODEAdapter` and implement its `Protocol` surface
   (8 methods + a `mechanism_id` property + a `capabilities()` handshake).
2. Re-export the new class from `adaptive_reflow/adapters/__init__.py`.
3. Register a `CandidateEntry` in `adaptive_reflow.writer.registry`.
4. Add tests under `tests/test_adapters/`.

Hard rules: no `import torch` in `adaptive_reflow/adapters/*`, capability
handshake is mandatory, `source_round` is non-negative int, deterministic
seed.

## 挂载与边界

- 主线挂载路径：`src/pocket_modules/mechanisms/inference/adaptive_reflow`。
- 每一 round 重新求解同一共享模型状态；本仓库不拥有独立专家模型或独立生成器。
- 外部指标反馈只能经显式、带来源的接口进入，不能伪装为无条件 de novo 结果。

## 晋级要求

修改 round 条件、memory、freeze、restart 或反馈语义时，必须在主线验证 condition trace、状态隔离、checkpoint 兼容和逐 round 对照。多步输出必须与原始单轮输出分别报告。

## Component boundary

This repo (`flowa-multistep-reinference`) is the **sole executable writer** for the
restart distribution and ODE condition updates per the
`RestartPolicyAuthorityContract`. The companion restart-noise / metric-delta bias
library has been split off into its own repo:

- [`silverenternal/flowa-noise-bias`](https://github.com/silverenternal/flowa-noise-bias)

That companion is **stateless calculation / diagnostic only** (`diagnostic_only` mode);
it may coexist with `adaptive_reflow` in the same run but never writes executable
sampler controls. `legacy_standalone` mode is mutually exclusive with
`adaptive_reflow` being active.

See `DESIGN_BOUNDARY.md`, `CONTRACTS.md`, and `ARCHITECTURE.md` for the full
contracts, governance rules, and post-refactor package layout.

## Documentation

The full doc set is the single source of truth for the package. Start
here, then drill down based on what you need.

The auto-generated API reference (rendered by mkdocs + mkdocstrings from
every module-level docstring and typed signature under `adaptive_reflow/`)
is published to GitHub Pages:

- **<https://silverenternal.github.io/flowa-multistep-reinference/>**

| Doc | Read it for… |
| --- | --- |
| [`QUICKSTART.md`](QUICKSTART.md) | Five-minute on-ramp: install, run the suite, walk one round against `ToyGaussianAdapter`, capture a golden, run the docs scanner. |
| [`TUTORIAL.md`](TUTORIAL.md) | Hands-on walk-through of one round end-to-end. |
| [`FAQ.md`](FAQ.md) | Twenty short answers to the questions that come up most often. |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Package layout, dependency DAG, governance invariants, the Adapter Protocol recipe for adding a new model, the file inventory. |
| [`docs/adr/`](docs/adr/) | Load-bearing boundary decisions (universal/molecular split, typed-contracts core boundary, engine operation order, fail-closed audit-code policy). |
| [`docs/ADAPTER_INTERFACE_SPEC.md`](docs/ADAPTER_INTERFACE_SPEC.md) | The authoritative spec for adapter authors (DTB-G1). |
| [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) | What the six test layers cover and what bars a change has to clear before merge. |
| [docs/PERFORMANCE_BUDGETS.md](docs/PERFORMANCE_BUDGETS.md) | Kernel p95 budgets, the bench runner, the regression gate. |

Every claim in these docs is verified against the source tree by
[`tools/check_docs_against_code.py`](tools/check_docs_against_code.py)
on every CI run.

## Tests

```bash
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/ --no-header -q
```

Current state on this tree: 1235 tests pass, 7 skipped (torch-gated
molecular mixer tests). The suite includes the AST-level guard that
asserts `universal/` has zero molecule-specific imports.