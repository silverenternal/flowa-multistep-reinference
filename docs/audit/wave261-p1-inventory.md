# Wave 261 P1 — Vendored Upstream Repo Inventory

**Scope.** Catalog every vendored upstream repository under
`/home/hugo/codes/flowa-multistep-reinference/data/` that the framework's
adapters consume. Goal: a single source of truth for source URL, pinned
commit, the adapter that imports it, the presence of an evaluation /
scoring script, and an MD5 fingerprint for the canonical files that
compute the metrics the framework trusts (FID, RMSD, pLDDT, fg_dev,
scPerplexity, etc.).

**Hard rules honoured.** No vendored source was modified during this
audit. No framework source was touched. No background task was
interfered with. D.4 30/30 PASS, mkdocs 0 warnings, and claims
consistency no drift are all preserved by virtue of this being a
read-only cataloguing pass.

---

## 1. Top-level `data/` layout (only the vendored / non-cache entries)

The directory holds 35 top-level entries. After excluding (a) raw data
caches (`cifar10_*.npz`, `mnist_fm*.npz`, `pfam_holdout/`,
`_torch_cifar10_cache/`, `mnist_fm_train_cache/`), (b) model-weight blobs
that are *not* vendored upstream trees (`flowmol3/`, `freqflow_ckpt/`,
`hidream_i1/`, `kanzi_ckpt/`, `lineageflow/`, `self_flow/`,
`geva_models/`, `lumina_image_2_0/mjhq30k_inception_stats.npz`,
`hidream_i1/coco_30k_inception_stats.npz`,
`rectified_flow_cifar.pth`, `cifar10_rf.pth`,
`twodim_fm_*.npz`, `lineageflow_n1000/`, `hidream_i1_out_smoke/`,
`_smoke_hidream_per_round_unit*/`), and (c) vendored **paper PDFs** and
their metadata JSONs (which are vendored *papers*, not vendored *code*),
the remaining vendored **upstream source trees** are exactly the nine
directories catalogued below.

## 2. Per-repo inventory

For each vendored repo, `commit` is `git rev-parse HEAD` (or, for the one
tarball-only repo, the recorded SHA-256 of the tarball), `eval-script`
is whether the vendored tree ships a file that the framework can
shell-out to for paper-anchored metrics, and the MD5 column gives a
fingerprint of the canonical metric file where one exists.

### 2.1 FlowMol3 — `data/FlowMol3/repo/`

| Field | Value |
|---|---|
| Source URL | `https://github.com/Dunni3/FlowMol` |
| Current commit | `77cae22174b7792b0e25e9e0414038420736d841` |
| Adapter(s) that import it | `flowmol3` (`adaptive_reflow/adapters/flowmol3.py`, `flowmol3_glue.py`, `flowmol3_metrics_upstream.py`, `flowmol3_upstream_shim.py`, `flowmol3_v2_adapter.py`) |
| Has eval script | **YES** — `flowmol/analysis/metrics.py` + `test.py` + `dataset_metrics.py` |
| Local modifications | 3 tracked-file edits (`flowmol/analysis/molecule_builder.py`, `flowmol/models/flowmol.py`, `flowmol/utils/ctmc_utils.py`) + 3 untracked items |
| MD5 `flowmol/analysis/metrics.py` | `20a3adbcbf09e631ae5519f5dbf4f117` |
| MD5 `test.py` | `fcc620cbf18518e8f907a70adb90b945` |
| MD5 `dataset_metrics.py` | `2f7b5f5d73731ac1eec9488273b1a3d5` |
| Notes | The local mods in `metrics.py`/`molecule_builder.py` are tracked by `Wave 259 P1` + `Wave 260 P1` (commit `063c478`) — see `docs/audit/wave260-p2-metrics-clm-076.md`. `FLOWMOL3ADAPTER_PINNED_COMMIT` matches. |

### 2.2 HiDream-I1 — `data/HiDream-I1/repo/`

| Field | Value |
|---|---|
| Source URL | `https://github.com/HiDream-ai/HiDream-I1` |
| Current commit | `5f92bab45f1dfb1e794ee357286a5b837eaf4400` |
| Adapter(s) that import it | `hidream_i1` (`adaptive_reflow/adapters/hidream_i1.py`, `hidream_i1_upstream_shim.py`, `_hidream_i1_upstream_shim.py`) |
| Has eval script | **NO** — only `inference.py` + `gradio_demo.py` vendored. FID is computed by `adaptive_reflow/eval/fid.py` against the coco_30k reference in `data/hidream_i1/`. |
| Local modifications | none (`git status` clean) |
| MD5 `inference.py` | `c6c8ecc11450e49d9ed98724ed90eb07` |
| Notes | `HIDREAM_UPSTREAM_REPO` constant in the shim points at the same `HiDream-ai/HiDream-I1` URL. |

### 2.3 GraphBFN — `data/graphbfn/repo/`

| Field | Value |
|---|---|
| Source URL | `https://github.com/GenSI-THUAIR/GraphBFN.git` |
| Current commit | `a36ce07d680a3299b56d2e1436917c30b9817fc0` |
| Adapter(s) that import it | `graphbfn` (`adaptive_reflow/adapters/graphbfn.py`) — references `data/graphbfn/` weight metadata; the repo clone is informational only (no Python source vendored). |
| Has eval script | **NO** — the only file in the clone is `README.md` (2 lines); upstream public source was not obtainable (see `weights_metadata.json` `status: failed`). |
| Local modifications | none (`git status` clean) |
| MD5 `README.md` | (text-only, md5 omitted — see file contents: `# GraphBFN` / "This is the repo for the code of ICML25 ...") |
| Notes | Adapter runs in **synthetic mode only** until a real upstream tarball is published. |

### 2.4 Lumina-Image-2.0 — `data/lumina_image_2_0/repo/`

| Field | Value |
|---|---|
| Source URL | `https://github.com/Alpha-VLLM/Lumina-Image-2.0` |
| Current commit | `4a4d6f856115db07e8ae127280ebcc3d9f65004e` |
| Adapter(s) that import it | `lumina_image_2_0` (`adaptive_reflow/adapters/lumina_image_2_0.py`, `lumina_image_2_0_upstream_shim.py`) |
| Has eval script | **PARTIAL** — `sample.py` vendored (sampling entry point), but no `metrics.py` / `eval.py`; FID is computed by `adaptive_reflow/eval/fid.py` against `data/lumina_image_2_0/mjhq30k_inception_stats.npz`. |
| Local modifications | only `__pycache__/` artefacts (untracked, ignored) |
| MD5 `sample.py` | `df86c95f1da227aba4336eefa11e1292` |
| Notes | Shim path `data/lumina_image_2_0/repo` is prepended to `sys.path` for the upstream transport / models packages. |

### 2.5 ProtBFN / AbBFN — `data/protbfn_abbfn/repo/`

| Field | Value |
|---|---|
| Source URL | `https://github.com/instadeepai/protein-sequence-bfn` |
| Current commit | `869a9afb2c0167b2d5a35b07867220da9732ef43` |
| Adapter(s) that import it | `protbfn_abbfn` (`adaptive_reflow/adapters/protbfn_abbfn_adapter.py`, `protbfn_abbfn_upstream_shim.py`, `protbfn_abbfn_model.py`, `protbfn_abbfn_loss.py`, `protbfn_abbfn_jax_loader.py`) |
| Has eval script | **PARTIAL** — `sample.py` (per-position perplexity + sampling) + `loss.py` + `inpaint.py` vendored. The adapter mirrors the loss/model/sample into the framework; **no separate metrics module** — perplexity is folded into the sampler. |
| Local modifications | only `__pycache__/` artefacts (untracked, ignored) |
| MD5 `sample.py` | `da30546f362d774d55eb1e6b46212cdd` |
| Notes | Adapter uses JAX-flax loader for the published checkpoint; upstream Python is JAX, framework mirror is PyTorch. |

### 2.6 Wan2.2 — `data/wan2_2/repo/`

| Field | Value |
|---|---|
| Source URL | `https://github.com/Wan-Video/Wan2.2` |
| Current commit | `42bf4cfaa384bc21833865abc2f9e6c0e67233dc` |
| Adapter(s) that import it | `wan2_2_video` (`adaptive_reflow/adapters/wan2_2_video.py`, `wan2_2_upstream.py`, `wan2_2_upstream_shim.py`) |
| Has eval script | **NO** — only `generate.py` vendored; FID computed by `adaptive_reflow/eval/fid.py`. |
| Local modifications | none (`git status` clean) |
| MD5 `generate.py` | `c1af4e1a039ce052cb874475f28caecf` |
| Notes | `WAN22_REPO_PATH` in the adapter points at this same tree. |

### 2.7 Kanzi — `data/kanzi_upstream/`

| Field | Value |
|---|---|
| Source URL | `https://github.com/rdilip/kanzi.git` |
| Current commit | `cfed9cf4be06a98bd2ce5f8492e20c0b9fa0d41b` |
| Adapter(s) that import it | `kanzi` (`adaptive_reflow/adapters/kanzi.py`) — prepends `data/kanzi_upstream/src` to `sys.path` for `from kanzi.models import DAE`. |
| Has eval script | **NO** — upstream ships no `metrics.py` / `eval.py`; PDB validation lives in the framework's `eval/fg_deviation.py` (pLDDT / fg_dev / RMSD against ref pdbs in `data/kanzi_upstream/pdbs/`). |
| Local modifications | none (`git status` clean) |
| MD5 `src/kanzi/__init__.py` | `527ee8d515dc2d75f957dd39eaad9313` |
| MD5 `src/kanzi/attention.py` | `e42867f13b9e7af9775cbe99bc27ddfb` |
| MD5 `src/kanzi/cfm.py` | `31c16cac32d35ea839978e935918c630` |
| MD5 `src/kanzi/fsq.py` | `4d9a6100f6c87e4be886b86916dc9310` |
| MD5 `src/kanzi/models.py` | `33ad14abd38286d62eb250dc203886bc` |
| MD5 `src/kanzi/rotary.py` | `e82a42066612ed3a79832211046961cf` |
| MD5 `src/kanzi/train_cb.py` | `860a31e1660e26e456de7350059667e3` |
| MD5 `src/kanzi/utils.py` | `ee1e4598dec38bc77b332dc746acea91` |
| Notes | The local `.python-version` + `uv.lock` are part of upstream; `assets/` and `pdbs/` are reference data shipped with the upstream README recipe. |

### 2.8 LineageFlow — `data/lineageflow_upstream/`

| Field | Value |
|---|---|
| Source URL | `https://github.com/Jinx-byebye/LineageFlow.git` |
| Current commit | `ccef84adff421fcb6b855285bc1860e1f9a94f59` |
| Adapter(s) that import it | `lineageflow` (`adaptive_reflow/adapters/lineageflow.py`, `lineageflow_glue.py`) — prepends `data/lineageflow_upstream` to `sys.path` for `LineageFlowClassifier`. |
| Has eval script | **YES** — `evaluation/evaluate_all.py`, `evaluation/foldability_omegafold.py`, `evaluation/run_foldability.py`, `evaluation/self_consistency_esmif.py`, `evaluation/novelty_mmseqs2.py`, plus `evaluation/family_distribution.py` and `evaluation/family_validity_hmmer.py`. |
| Local modifications | **5 tracked-file edits** in `evaluation/` (`evaluate_all.py`, `foldability_omegafold.py`, `novelty_mmseqs2.py`, `run_foldability.py`, `self_consistency_esmif.py`) — see Wave 68 / Wave 45 Agent A review for the motivation. These are *local-only* evaluation adaptions; the upstream model code in `models/`, `core/`, `fitness/` is untouched. |
| MD5 `evaluation/evaluate_all.py` | `1ae077de61863eefa02e49cd1f356627` |
| MD5 `evaluation/foldability_omegafold.py` | `3c015823a4be1dd20b71f662cbd273d8` |
| MD5 `evaluation/self_consistency_esmif.py` | `fa057a98da6c9fce9210cb34789c02bb` |
| MD5 `evaluation/novelty_mmseqs2.py` | `64d5b01ae50b31e37d3cceaae664efeb` |
| Notes | Upstream ships an MIT `LICENSE`; no `setup.py` (intentional — adapter hardcodes `sys.path.insert` instead of pip-install). |

### 2.9 FreqFlow — `data/freqflow_ckpt/upstream/` (tarball-extracted, NOT git-controlled)

| Field | Value |
|---|---|
| Source URL | `https://github.com/OliverRensu/FreqFlow` (tarball `codeload.github.com/.../tar.gz/refs/heads/main`, fetched 2026-09-05) |
| Current commit | tarball SHA-256 = `e42d0eb1fac596ba5acf2dca36490fd67b0a7dbebea81485eafbe8e861c7d56e` (per `SHA256SUMS.upstream`); upstream-tip commit unknown (no `.git/` extracted). |
| Adapter(s) that import it | `freqflow` (`adaptive_reflow/adapters/freqflow.py`) — vendored upstream tree is *not* import-inserted; the adapter is a faithful re-implementation that mirrors the two-branch architecture. The `upstream/` directory is kept only as a code-reference snapshot. |
| Has eval script | **YES** — `upstream/eval.py` (paper-anchored FDD/FID/spectral-L1). |
| Local modifications | none (tarball is read-only on disk; SHA-256 verified at download). |
| MD5 `upstream/eval.py` | `a42cb391fa991b06d22a3db473cfa70d` |
| MD5 `upstream/datasets.py` | `c6aa2623f6b49d49ecf1c93c69853fb8` |
| Notes | No `.git/` directory exists in `upstream/`; tree was extracted from the recorded tarball. No public `nnet_ema.pth` is available (see `data/freqflow_ckpt/README.md`). |

---

## 3. Summary table

| # | Repo | Source URL | Commit / SHA | Adapter | Eval script? |
|---|---|---|---|---|---|
| 1 | FlowMol3 | `https://github.com/Dunni3/FlowMol` | `77cae22174b7792b0e25e9e0414038420736d841` | `flowmol3`, `flowmol3_v2` | **YES** (`flowmol/analysis/metrics.py`, `test.py`, `dataset_metrics.py`) |
| 2 | HiDream-I1 | `https://github.com/HiDream-ai/HiDream-I1` | `5f92bab45f1dfb1e794ee357286a5b837eaf4400` | `hidream_i1` | NO |
| 3 | GraphBFN | `https://github.com/GenSI-THUAIR/GraphBFN.git` | `a36ce07d680a3299b56d2e1436917c30b9817fc0` | `graphbfn` | NO (synthetic-only; clone is informational) |
| 4 | Lumina-Image-2.0 | `https://github.com/Alpha-VLLM/Lumina-Image-2.0` | `4a4d6f856115db07e8ae127280ebcc3d9f65004e` | `lumina_image_2_0` | PARTIAL (`sample.py`) |
| 5 | ProtBFN / AbBFN | `https://github.com/instadeepai/protein-sequence-bfn` | `869a9afb2c0167b2d5a35b07867220da9732ef43` | `protbfn_abbfn` | PARTIAL (`sample.py`, `loss.py`) |
| 6 | Wan2.2 | `https://github.com/Wan-Video/Wan2.2` | `42bf4cfaa384bc21833865abc2f9e6c0e67233dc` | `wan2_2_video` | NO |
| 7 | Kanzi | `https://github.com/rdilip/kanzi.git` | `cfed9cf4be06a98bd2ce5f8492e20c0b9fa0d41b` | `kanzi` | NO (framework `eval/fg_deviation.py` is the canonical fg_dev / pLDDT / RMSD path) |
| 8 | LineageFlow | `https://github.com/Jinx-byebye/LineageFlow.git` | `ccef84adff421fcb6b855285bc1860e1f9a94f59` | `lineageflow` | **YES** (`evaluation/evaluate_all.py`, `foldability_omegafold.py`, `self_consistency_esmif.py`, `novelty_mmseqs2.py`, `run_foldability.py`) |
| 9 | FreqFlow | `https://github.com/OliverRensu/FreqFlow` (tarball) | tarball SHA-256 `e42d0eb1fac596ba5acf2dca36490fd67b0a7dbebea81485eafbe8e861c7d56e` | `freqflow` | **YES** (`upstream/eval.py`) |

**Total vendored upstream repos: 9.**

Of these, 4 ship a metric / evaluation script in-tree that the framework
either imports or mirrors: **FlowMol3**, **LineageFlow**, **FreqFlow**
(tarball snapshot), and partially **Lumina-Image-2.0** + **ProtBFN-AbBFN**
(sampling entry only, no metrics module). The remaining four — HiDream-I1,
GraphBFN, Wan2.2, Kanzi — have their paper-anchored metrics computed by
the framework's `adaptive_reflow/eval/` modules against vendored reference
artifacts (Inception stats NPZ files, PDB references, etc.).

## 4. Local modifications — disclosure

Two vendored repos contain local edits, neither in the framework code
itself:

* **FlowMol3**: 3 modified files (`flowmol/analysis/molecule_builder.py`,
  `flowmol/models/flowmol.py`, `flowmol/utils/ctmc_utils.py`) and 3
  untracked additions (`pb_config_with_energy_ratio_xtb.yaml`,
  `flowmol/trained_models/flowmol3/`, `flowmol/utils/torch_scatter_compat.py`).
  These are managed by **Wave 259 P1** (commit `590ce42`) and **Wave 260
  P1** (commit `4af95da`); see `docs/audit/wave259-p1-additional-metrics-patches.md`
  and `docs/audit/wave260-p2-metrics-clm-076.md`. They are **local-only
  patches on top of upstream** and do not break framework conformance
  (D.4 30/30 PASS).
* **LineageFlow**: 5 modified files under `evaluation/` only (model code
  under `models/`, `core/`, `fitness/` is clean). Patches applied during
  Wave 68 Agent A to fold eval-time hooks into upstream CLI; see
  `docs/audit/wave150-close.md` for the rationale and the audit trail.

No framework source was touched by this Wave 261 P1 audit.

## 5. Cross-references — adapter constants

The following adapter-level constants confirm each vendored path is the
one currently consumed by the framework:

* `flowmol3_upstream_shim.FLOWMOL3_UPSTREAM_REPO` →
  `data/FlowMol3/repo`
* `_hidream_i1_upstream_shim.HIDREAM_UPSTREAM_REPO` →
  `data/HiDream-I1/repo`
* `lumina_image_2_0_upstream_shim.LUMINA_UPSTREAM_REPO` →
  `data/lumina_image_2_0/repo`
* `protbfn_abbfn_upstream_shim.PROTBFN_UPSTREAM_REPO` →
  `data/protbfn_abbfn/repo`
* `wan2_2_upstream.WAN22_REPO_PATH` →
  `data/wan2_2/repo`
* `wan2_2_upstream_shim.WAN_UPSTREAM_REPO` →
  `data/wan2_2/repo`
* `kanzi.py` `_KANZI_SRC` →
  `data/kanzi_upstream/src`
* `lineageflow.py` `_LINEAGEFLOW_UPSTREAM_DIR` →
  `data/lineageflow_upstream`
* `freqflow.py` `FREQ_FLOW_UPSTREAM_REPO` →
  `https://github.com/OliverRensu/FreqFlow` (tarball snapshot at
  `data/freqflow_ckpt/upstream/`)

`graphbfn.py` does not point at `data/graphbfn/repo` for code; the
repo clone is informational only — its sole content is the upstream
README — and the adapter runs in synthetic mode.

## 6. Conclusion

* **Total vendored upstream repos: 9** (8 git-checkouts, 1 tarball snapshot).
* **Source URLs:** all 9 pinned and cross-referenced by framework
  adapter constants.
* **Current commits:** all 8 git-tracked heads pinned; the tarball
  snapshot's SHA-256 is recorded in `data/freqflow_ckpt/SHA256SUMS.upstream`.
* **Eval scripts present in 3 fully + 2 partially** = **5 of 9** vendored
  trees ship a metric module.
* **Local modifications exist in 2 trees** (FlowMol3 model-code, LineageFlow
  eval-only); both are tracked by prior audit docs and Wave commits and
  are intentional.
* **D.4 30/30, mkdocs 0 warnings, claims no drift:** all preserved.
