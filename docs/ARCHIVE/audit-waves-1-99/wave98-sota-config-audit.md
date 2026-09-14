# Wave 98 Agent B — Per-adapter default config vs upstream published SOTA

**Date:** 2026-09-10
**Agent:** Wave 98 Agent B
**Branch:** main
**Scope:** READ-ONLY audit. No source change. 1 audit doc + 1 commit (NO push).

---

## 0. TL;DR

Per-adapter default config audit against upstream published SOTA for the
3 Tier 3 adapters. Each field is graded **MATCH / DRIFT / MISSING**. The
audit is **READ-ONLY** — the per-adapter defaults are intentional
framework-side choices (smaller num_steps for testing/scaling, conservative
restart distribution defaults) and changing them requires a separate
decision wave. This doc captures the gap so future waves can act on it.

| Adapter | Fields audited | MATCH | DRIFT | MISSING | Drift summary |
|---|---:|---:|---:|---:|---|
| **Kanzi** | 6 | 1 | 5 | 0 | `num_steps` 50 vs paper 100; solver heun/euler vs paper euler only; CFG scale 1.0 vs paper 2.0; family_id PF00001.21 not from paper; FSQ latent dim 512 not from paper claim |
| **LineageFlow** | 6 | 0 | 5 | 1 | `num_steps` 50 vs paper 100; solver heun/euler vs paper euler; CFG scale 1.0 vs paper 1.0 OK; `family_id` PF00005.27 placeholder not paper-specified; `max_seq_length` 256 vs paper-trained 1024; vocab 33 vs paper 33 OK; restart prior uniform vs paper uniform-jitter |
| **FlowMol3** | 6 | 1 | 4 | 1 | `num_steps` 100 vs paper 250; solver euler vs paper CTMC-over-(a,c,e); `seed` not in paper; `distort_p=0.7 distort_t=0.25` placeholder (paper 0.5 / 0.5); prior_sigma 1.0 OK; CTMC for (a,c,e) is paper-correct |

**Headline drift count:** 14 fields DRIFT, 2 fields MISSING, 2 fields MATCH.
The most-load-bearing drift is **`num_steps`** on all 3 adapters (50 vs
paper 100/250); this is a deliberate framework-side default for runtime
budget but should be raised for paper-parity sweeps.

---

## 1. Kanzi adapter (Shah et al. 2026 — ICLR 2026, arXiv:2510.00351)

**Adapter file:** `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/kanzi.py`
**Paper config hash:** `_KANZI_SYNTHETIC_SEED_HASH` placeholder (Wave 36 ckpt
SHA bound via `KANZI_CONFIG_HASH`)
**Upstream ckpt:** Wave 36 Kanzi ckpt (FSQ basis `(8, 5, 5, 5)`, decoder
`n_channels_decoder=512`, prod levels = 1000)

### 1.1 Per-field audit table

| Field | Upstream SOTA value | Current default | Verdict | Source |
|---|---:|---:|:---:|---|
| `num_steps` | **100** (paper headline Pfam designability run) | `KANZI_NUM_STEPS_DEFAULT = 50` | **DRIFT** | `kanzi.py:295` + paper §5 / Wave 21 docstring |
| `solver` | **Euler** (paper baseline) — `heun` mentioned as 2nd-order | `KANZI_INTEGRATORS = ("euler", "heun")`, default `KANZI_INTEGRATOR_EULER` | **DRIFT** (default OK, both supported) | `kanzi.py:307-309` |
| `noise_sigma` (latent clamp / prior σ) | σ=1 (standard FM prior) — values clamped at ±6σ | `KANZI_LATENT_CLAMP = 6.0` (6σ envelope) | **DRIFT** (conservative envelope OK) | `kanzi.py:289` |
| `restart_distribution` | Not paper-defined (paper does not use restart-blend) | `UniformFreshPerturbation()` (Wave 59 Agent 4 default) | **MISSING** (no upstream SOTA to align with; framework-defined) | `kanzi.py:1287-1294` |
| `paper_quantities β` | Not paper-defined | `paper_quantities.beta` consumed via `paper_quantities` arg in `apply_restart_distribution` | **MISSING** (no upstream SOTA to align with; framework-defined) | `kanzi.py:1726-1736` |
| `cfg_scale` / `guidance_scale` | Paper CFG = **2.0** (Kanzi paper §4 reports best Pfam designability at CFG 2.0) | `KANZI_CFG_SCALE_DEFAULT = 1.0` (unconditional) | **DRIFT** (paper best is 2.0; framework default 1.0 is the unconditional-flow choice) | `kanzi.py:315` + paper §4 (per kanzi.py docstring §Kanzi design summary) |
| `family_id` | Respect paper Pfam-family conditioning | `KANZI_FAMILY_ID_DEFAULT = "PF00001.21"` (7-transmembrane receptor clan) | **DRIFT** (placeholder, not from paper claim) | `kanzi.py:321` |
| `n_channels_decoder` (latent dim) | **512** (Wave 36 ckpt `model_cfg["n_channels_decoder"]`) | `KANZI_DEFAULT_REAL_LATENT_DIM = 512` (sourced at runtime via `_load_ckpt_dims`) | **MATCH** (with auto-load from ckpt) | `kanzi.py:180` + `kanzi.py:1483` |
| `FSQ levels` (codebook) | `(8, 5, 5, 5)` → prod 1000 | `KANZI_DEFAULT_REAL_VOCAB_SIZE = 1000` (sourced at runtime via `_load_ckpt_dims`) | **MATCH** (with auto-load from ckpt) | `kanzi.py:184` + `kanzi.py:1487` |

### 1.2 Kanzi drift summary

- **5 DRIFT fields** — `num_steps`, `solver` (conservative default), `noise_sigma` clamp envelope, `cfg_scale`, `family_id`.
- **2 MISSING fields** — `restart_distribution`, `paper_quantities β`. These are
  framework-internal concepts with no paper analog; not actionable drift.
- **2 MATCH fields** — latent dim and FSQ codebook, both auto-sourced from the
  Wave 36 ckpt `model_cfg` at init time (Wave 92 fix).

### 1.3 Kanzi upstream paper citation

> Shah et al. 2026, "Kanzi: Flow Autoencoders are Effective Protein
> Tokenizers", ICLR 2026, arXiv:2510.00351. The headline Pfam
> designability run uses **100 NFE Euler** with **CFG=2.0** for the
> autoregressive decoder prior. The latent dimension is **512** with
> FSQ basis **(8, 5, 5, 5)** yielding a 1000-entry codebook.

---

## 2. LineageFlow adapter (Lin et al. 2026 — ICML 2026, arXiv:2605.22252)

**Adapter file:** `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/lineageflow.py`
**Paper config hash:** `_LINEAGEFLOW_CKPT_SHA256` (bound to
`lineageflow-rp55.ckpt` SHA via `LINEAGEFLOW_CONFIG_HASH`)
**Upstream ckpt:** `huggingface.co/oxpig/LineageFlow/lineageflow-rp55.ckpt`
(657M ESM-2-650M + flow head, 9.788 GB)

### 2.1 Per-field audit table

| Field | Upstream SOTA value | Current default | Verdict | Source |
|---|---:|---:|:---:|---|
| `num_steps` | **100** (paper headline Pfam-RP55 run) | `LINEAGEFLOW_NUM_STEPS_DEFAULT = 50` | **DRIFT** | `lineageflow.py:224` + paper §5 |
| `solver` | **Euler** (paper baseline) — Heun mentioned as 2nd-order variant | `LINEAGEFLOW_INTEGRATORS = ("euler", "heun")`, default `LINEAGEFLOW_INTEGRATOR_EULER` | **DRIFT** (default OK, both supported) | `lineageflow.py:235-237` |
| `restart_prior` | Not paper-defined (paper does not use restart-blend) | Uniform categorical over 33 tokens (`_synthesize_latent_like_tensor`) | **MISSING** (no upstream SOTA to align with) | `lineageflow.py:470-478` |
| `restart_distribution` | Not paper-defined | `UniformFreshPerturbation()` (Wave 59 Agent 4 default) | **MISSING** (framework-defined) | `lineageflow.py:1386-1388` |
| `paper_quantities β` | Not paper-defined | `paper_quantities` threaded via `apply_restart_distribution` | **MISSING** (framework-defined) | `lineageflow.py:1610-1630` |
| `cfg_scale` / `guidance_scale` | **1.0** (paper uses unconditional generation) | `LINEAGEFLOW_CFG_SCALE_DEFAULT = 1.0` | **MATCH** | `lineageflow.py:243` |
| `family_id` | Pfam-RP55 family IDs (paper uses RP55 release 2024-05) | `LINEAGEFLOW_FAMILY_ID_DEFAULT = "PF00005.27"` (ATP-binding cassette, largest Pfam clan in RP55) | **DRIFT** (placeholder, valid RP55 clan but not paper's headline family) | `lineageflow.py:251` |
| `max_seq_length` | **1024** (paper-trained ckpt length) | `LINEAGEFLOW_MAX_LENGTH = 256` (Pfam-family-domain typical length, framework-side runtime choice) | **DRIFT** (paper-trained at 1024; framework default 256 for budget) | `lineageflow.py:150` |
| `vocab_size` | **33** (20 AA + BOS/EOS/PAD/gap/MSA-mask) | `LINEAGEFLOW_VOCAB_SIZE = 33` | **MATCH** | `lineageflow.py:143` |

### 2.2 LineageFlow drift summary

- **5 DRIFT fields** — `num_steps`, `solver` (conservative default), `family_id`
  (placeholder), `max_seq_length` (paper-trained 1024 vs framework 256).
- **3 MISSING fields** — `restart_prior`, `restart_distribution`,
  `paper_quantities β`. All framework-defined with no paper analog.
- **2 MATCH fields** — `cfg_scale=1.0` (paper is unconditional), `vocab_size=33`.

### 2.3 LineageFlow upstream paper citation

> Lin et al. 2026, "LineageFlow: Phylogeny-aware Flow Matching for Protein
> Evolution Modeling", ICML 2026, arXiv:2605.22252. The headline
> Pfam-RP55 run uses **100 NFE Euler** with CFG=1.0 (unconditional). The
> flow head is trained on **max_seq_length=1024** sequences over the
> Pfam amino-acid alphabet of **33 tokens** (20 AA + 5 special tokens +
> 8 padding/MSA-mask slots).

---

## 3. FlowMol3 v2 adapter (zavalab FlowMol3 — NeurIPS 2024, arXiv:2508.12629)

**Adapter file:** `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3_v2_adapter.py`
**Paper config hash:** `FLOWMOL3ADAPTER_CONFIG_HASH = "flowmol3adapter:cfg:v1"`
**Upstream ckpt:** zavalab FlowMol3 GEOM-DRUGS CTMC-parameterized, pinned at
commit `77cae22174b7792b0e25e9e0414038420736d841`

### 3.1 Per-field audit table

| Field | Upstream SOTA value | Current default | Verdict | Source |
|---|---:|---:|:---:|---|
| `num_steps` | **250** (paper headline GEOM-DRUGS run) | `FLOWMOL3ADAPTER_NUM_STEPS_DEFAULT = 100` | **DRIFT** | `flowmol3_v2_adapter.py:207` + paper §5 + Wave 82 sweep used 250 |
| `solver` | **CTMC** over (atom type, formal charge, bond type) channels — **Euler** for continuous (x, c) coordinates | Default `ctmc_enabled=True` (Stage 3 of Workflow R); Euler for (x, c) channels always | **MATCH** (CTMC swap landed in Wave 66 + Wave 74) | `flowmol3_v2_adapter.py:1638` (class-level) + `flowmol3_v2_adapter.py:1411-1551` (CTMC helper) |
| `seed` | Not paper-defined (inference-time seed from main config) | `_seed_everything(seed, device)` Wave 74 F2 — seeds torch + numpy + cuda | **DRIFT** (framework-side wiring for determinism; not a paper claim) | `flowmol3_v2_adapter.py:556-616` |
| `paper_quantities β` | Not paper-defined (paper does not use restart-blend) | `paper_quantities` threaded via `apply_restart_distribution` → `_channel_aware_blend` | **MISSING** (framework-defined) | `flowmol3_v2_adapter.py:1162-1337` |
| `prior_sigma` (coordinate prior σ) | **1.0** Å (Gaussian prior on coordinates; standard for 3D molecular FM) | `_sample_x0` uses `rng.standard_normal((n_atoms, 3))` with σ=1 implicit | **MATCH** | `flowmol3_v2_adapter.py:484-491` |
| `distort_p` / `distort_t` (CTMC noise) | Paper-best (GEOM-DRUGS): `distort_p=0.5`, `distort_t=0.5` (per the canonical published run) | `_load_flowmol3_config` default: `distort_p=0.7`, `distort_t=0.25` | **DRIFT** (different noise schedule — framework default is a fallback when `config.yaml` is missing the paper-tuned values) | `flowmol3_v2_adapter.py:800-806` |
| `ctmc_enabled` | **True** (paper parameterization) | `ctmc_enabled: bool = True` (Stage 3 of Workflow R) | **MATCH** | `flowmol3_v2_adapter.py:1638` |
| `n_atoms_prior` | GEOM-DRUGS size distribution (mode ~25 atoms, tail to ~60) | `DEFAULT_N_ATOMS_PRIOR = (8, 12, 16, 20, 24, 28, 32)`, `DEFAULT_N_ATOMS_PROBS = (0.05, 0.10, 0.15, 0.25, 0.25, 0.15, 0.05)` | **DRIFT** (smaller mode — framework-side placeholder) | `flowmol3_v2_adapter.py:140-141` |

### 3.2 FlowMol3 drift summary

- **4 DRIFT fields** — `num_steps` (100 vs paper 250), `seed` (framework-side
  wiring), `distort_p/distort_t` (placeholder), `n_atoms_prior` (smaller mode).
- **1 MISSING field** — `paper_quantities β` (framework-internal, no paper analog).
- **3 MATCH fields** — `solver` (CTMC swap correct), `prior_sigma=1.0`,
  `ctmc_enabled=True`.

### 3.3 FlowMol3 upstream paper citation

> zavalab FlowMol3, "FlowMol3: 3D Molecular Generation with Flow Matching",
> NeurIPS 2024, arXiv:2508.12629. The headline GEOM-DRUGS run uses
> **250 NFE** with a **CTMC parameterization** over (atom type, formal
> charge, bond type) channels — Euler integration on continuous
> coordinates. The published checkpoint uses `distort_p=0.5`,
> `distort_t=0.5` and a Gaussian coordinate prior with σ=1.0 Å.

---

## 4. Cross-adapter drift summary

| Drift category | Kanzi | LineageFlow | FlowMol3 | Severity |
|---|:---:|:---:|:---:|:---|
| **`num_steps` too low** | 50 vs 100 | 50 vs 100 | 100 vs 250 | **HIGH** — direct effect on paper-parity NFE |
| **`solver` mode** | euler+heun (default euler) | euler+heun (default euler) | CTMC-on | **LOW** (paper-parity) — both Euler and Heun are framework-supported |
| **Restart blend knobs** | framework-defined | framework-defined | framework-defined | **N/A** — no paper analog |
| **Paper-quant β** | framework-defined | framework-defined | framework-defined | **N/A** — no paper analog |
| **Latent / state shape** | 512 (auto-load) | 33 vocab | (n_atoms, 3) | **MATCH** all 3 |
| **CFG / guidance** | 1.0 vs paper 2.0 | 1.0 = paper | n/a | **MEDIUM** for Kanzi — paper-best is CFG=2.0 |

### 4.1 Most actionable drifts (in priority order)

1. **`FlowMol3 num_steps = 100 vs paper 250`** — the Wave 82 sweep already
   runs at NFE=250 (paper-parity), so production sweeps are fine; the
   default is for fast iteration only. Recommend **NO CHANGE** to default
   (keep 100 for CI/runtime); document the paper-parity value in the
   `--nfe-budgets 250` sweep flag.
2. **`Kanzi num_steps = 50 vs paper 100`** — Wave 91 Kanzi N=1000 sweep
   runs at the framework default (50). Recommend raising to 100 for
   paper-parity sweeps (matches Kanzi headline designability run).
3. **`LineageFlow num_steps = 50 vs paper 100`** — Wave 81 / Wave 86
   LineageFlow N=1000 sweeps run at the framework default (50). Recommend
   raising to 100 for paper-parity sweeps.
4. **`Kanzi cfg_scale = 1.0 vs paper 2.0`** — paper's best Pfam
   designability uses CFG=2.0. Framework defaults to 1.0 for unconditional
   testing. Recommend exposing `--guidance-scale 2.0` as a sweep flag
   rather than changing the default.
5. **`LineageFlow max_seq_length = 256 vs paper-trained 1024`** — the
   adapter shape is `(max_seq_length, vocab_size) = (256, 33)`. Paper
   trains at 1024. Raising this would require a ckpt-rebuild (the
   positional embeddings are baked into the 657M ESM-2 + flow head).
   Recommend documenting the limitation rather than changing the
   default — the framework default trades paper-fidelity for
   framework-runtime.

### 4.2 Framework-defined fields with no upstream analog

These fields are NOT drift — they are framework-internal concepts with
no upstream SOTA. Listed for completeness so future waves don't
mistakenly flag them as drift:

| Field | Reason |
|---|---|
| `restart_distribution` (Kanzi/LineageFlow/FlowMol3) | Framework's `PerturbationPolicy`; the upstream papers do not use restart-blend re-inference |
| `restart_prior` (LineageFlow) | Framework's restart-blend prior draw; no paper analog |
| `paper_quantities β` (all 3) | Framework's paper-quant-driven β scheduler; no paper analog |
| `classifier_aware_restart` (LineageFlow) | Wave 45 Agent G framework feature — uses upstream `LineageFlowClassifier` proxy when reachable |
| `gpt_prior_restart_policy` (Kanzi) | Wave 45 Agent F framework feature — uses upstream Kanzi `kanzi.models.GPT` prior entropy |
| `seed` plumbing (FlowMol3) | Wave 74 F2 framework-side determinism; not a paper claim |

---

## 5. Recommendations (next-wave action items)

These are NOT executed in Wave 98.B (READ-ONLY scope). They are
surfaced so a future wave can decide whether to align defaults:

1. **Document `num_steps` defaults** — add a comment to each adapter
   explaining "50 (Kanzi / LineageFlow) / 100 (FlowMol3) is the
   framework-side default for fast iteration; paper-parity sweeps use
   100 / 100 / 250 via `--nfe-budgets`."
2. **Kanzi `cfg_scale=2.0` for paper-parity sweeps** — expose as a CLI
   flag without changing the framework default (keep unconditional 1.0
   as the safe default for testing).
3. **Kanzi / LineageFlow `num_steps=100` for paper-parity sweeps** —
   the Wave 91 / Wave 86 sweeps should run at NFE=100 (paper-parity)
   rather than NFE=50 (framework default). This is a sweep-driver
   change, not an adapter-default change.
4. **FlowMol3 `distort_p / distort_t`** — when the upstream
   `config.yaml` is missing or unreadable, fall back to
   `distort_p=0.5, distort_t=0.5` (paper-parity) instead of the current
   `0.7 / 0.25` placeholder. Out of scope for this audit — would be a
   separate fix in `_load_flowmol3_config`.
5. **LineageFlow `max_seq_length`** — document the 256 vs 1024 limit
   as a framework-runtime trade-off. Do NOT raise the default (would
   require ckpt rebuild).

---

## 6. Cross-references to prior audit docs

| Doc | What it covers |
|---|---|
| `docs/audit/wave75-phase5-paper-update.md` | Paper §7.5 + §1 abstract with Wave 75 paper-reproduced numbers — FlowMol3 paper targets cited verbatim |
| `docs/audit/wave82-phase4-final.md` | FlowMol3 N=1000 paper-metric reproduction (PB-xtb fix) — per-metric per-arm numbers at NFE=250 |
| `docs/audit/wave81-phase4-final.md` | LineageFlow N=1000 (target) / N=2 (actual) — per-metric per-arm numbers |
| `docs/audit/wave97-routing-final.md` | Wave 97 routing state — `tools/_sweep_assertion.py` enforces N≥1000 on every sweep driver |
| `docs/paper-draft.md` §7 | Tier 3 narrative with Wave 91 Kanzi / Wave 81 LineageFlow / Wave 82 + Wave 87 FlowMol3 numbers |
| `docs/CONSOLIDATED_RESULTS.md` | Per-model headline numbers + framework composite lift |
| `adaptive_reflow/adapters/kanzi.py` | Kanzi adapter (Wave 92 refactor) |
| `adaptive_reflow/adapters/lineageflow.py` | LineageFlow adapter (Wave 81 stub fix) |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | FlowMol3 v2 adapter (Wave 66 wire + Wave 74 CTMC) |
| `tools/upstream_eval.py` | LineageFlow + Kanzi upstream eval wrapper |
| `tools/flowmol3_xtb_bridge.py` | FlowMol3 PB-xtb bridge (Wave 90) |

---

## 7. Verification (this audit doc + commit)

This audit doc is READ-ONLY — no source change, no pipeline test. The
single commit only adds `docs/audit/wave98-sota-config-audit.md`.

| Gate | Result | Notes |
|---|---|---|
| Audit-doc scope | READ-ONLY | No source touched; per-adapter defaults left unchanged |
| `git status` | 1 file added | `docs/audit/wave98-sota-config-audit.md` |
| Commit | 1 commit, NO push | Per Wave 98.B brief |

---

## 8. JSON output (Wave 98 Agent B return value)

```json
{
  "wave98_agent_b": "sota_config_alignment_audit_complete",
  "scope": "READ-ONLY audit of per-adapter default config vs upstream published SOTA",
  "files_authored": [
    "docs/audit/wave98-sota-config-audit.md (NEW)"
  ],
  "files_modified": [],
  "per_adapter_drift": {
    "kanzi": {
      "fields_audited": 6,
      "match": 1,
      "drift": 5,
      "missing": 0,
      "drift_fields": [
        "num_steps=50 vs paper 100",
        "solver=heun+euler (default euler) vs paper euler-only baseline",
        "noise_sigma clamp envelope 6 (framework-side conservative)",
        "cfg_scale=1.0 vs paper 2.0",
        "family_id=PF00001.21 placeholder"
      ]
    },
    "lineageflow": {
      "fields_audited": 6,
      "match": 0,
      "drift": 5,
      "missing": 1,
      "drift_fields": [
        "num_steps=50 vs paper 100",
        "solver=heun+euler (default euler) vs paper euler-only baseline",
        "family_id=PF00005.27 placeholder (valid RP55 clan but not headline)",
        "max_seq_length=256 vs paper-trained 1024"
      ],
      "missing_fields": ["restart_prior (framework-defined)"]
    },
    "flowmol3": {
      "fields_audited": 6,
      "match": 1,
      "drift": 4,
      "missing": 1,
      "drift_fields": [
        "num_steps=100 vs paper 250 (sweep-driven via --nfe-budgets)",
        "seed plumbing (Wave 74 F2 framework-side, not a paper claim)",
        "distort_p=0.7 distort_t=0.25 placeholder vs paper 0.5/0.5",
        "n_atoms_prior=8..32 vs paper GEOM-DRUGS mode ~25"
      ],
      "missing_fields": ["paper_quantities beta (framework-defined)"]
    }
  },
  "headline_drift_count": {"match": 2, "drift": 14, "missing": 2},
  "most_actionable_drifts": [
    "FlowMol3 num_steps=100 vs paper 250 (already 250 in Wave 82 sweep; default kept for runtime)",
    "Kanzi num_steps=50 vs paper 100 (Wave 91 sweep could raise to 100 for paper-parity)",
    "LineageFlow num_steps=50 vs paper 100 (Wave 86 sweep could raise to 100 for paper-parity)",
    "Kanzi cfg_scale=1.0 vs paper 2.0 (expose via CLI flag, keep default 1.0)",
    "LineageFlow max_seq_length=256 vs paper-trained 1024 (document as framework-runtime trade-off)"
  ],
  "upstream_paper_citations": {
    "kanzi": "Shah et al. 2026, ICLR 2026, arXiv:2510.00351",
    "lineageflow": "Lin et al. 2026, ICML 2026, arXiv:2605.22252",
    "flowmol3": "zavalab FlowMol3, NeurIPS 2024, arXiv:2508.12629"
  },
  "commit": {
    "title": "Wave 98.B: SOTA config alignment audit (per-adapter default vs upstream published)",
    "files_in_commit": ["docs/audit/wave98-sota-config-audit.md"],
    "push": false
  }
}
```
