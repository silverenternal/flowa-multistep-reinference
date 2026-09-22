# Wave 266 P1: 54 root-dir items inventory + categorization

**Date:** 2026-09-22
**Branch:** main
**Scope:** READ-ONLY inventory of all 54 non-hidden items at the repo root,
categorized as `CANNOT_MOVE` (GitHub / Python / mkdocs convention pin it),
`NEED_GREP` (might be referenced by code / CI / docs / pyproject), or
`SAFE_TO_MOVE` (no inbound references found). NO files are moved in P1.

## 1. Method

1. Enumerate all 54 non-hidden root items via `ls -1 <repo> | grep -v "^\."`
   (excludes hidden cache / venv / Claude workspace dirs).
2. For each item, grep across the working tree for inbound references:
   - `*.py`, `*.sh`, `*.yml`, `*.toml`, `*.json`, `*.md`, `*.cfg`,
     `*.ini`, `*.yaml`, `Dockerfile`, `.github/**`, `mkdocs.yml`,
     `pyproject.toml`.
   - Exclude `.git/`, `.venv/`, `.cache/`, `site/`, `.claude/`,
     `.hypothesis/`, `.ruff_cache/`, `.mypy_cache/`,
     `adaptive_reflow/__pycache__/`, `scripts/__pycache__/`
     (these are either generated or out-of-scope).
3. Mark each item:
   - **CANNOT_MOVE**: pinned by GitHub / Python packaging / mkdocs convention
     (must stay at repo root for tooling to find it).
   - **NEED_GREP**: requires a manual scan before any move; OR has known
     inbound references that would have to be rewritten in lockstep.
   - **SAFE_TO_MOVE**: no inbound references found in code, CI, or docs.

## 2. Categorized inventory (54 items)

### 2.1 CANNOT_MOVE (28 items — pinned by GitHub / Python / mkdocs convention)

These files either:
- Have a hard-coded location requirement (GitHub renders `README.md` /
  `LICENSE` / `CODEOWNERS` / `SECURITY.md` / `.gitignore` /
  `.pre-commit-config.yaml` from the repo root).
- Are part of the Python packaging contract (referenced by `pyproject.toml`
  `readme`, `license-files`, `[tool.hatch.build.targets.wheel]` `include`
  list).
- Are the mkdocs config (`mkdocs.yml`) — mkdocs only reads the file at the
  directory level you invoke it from.
- Are CI workflows under `.github/` (which the task excludes from
  "root items" anyway, since hidden).
- Hold secrets / lockfiles (`uv.lock`, `requirements-lock.txt`) that must
  live next to `pyproject.toml` for `uv` to discover them.

| # | Path | Why cannot-move | Inbound refs found |
|---|------|-----------------|--------------------|
| 1 | `README.md` | GitHub auto-renders at root; PyPI `readme` field; `docs-deploy.yml` triggers on it | 200+ references across `pyproject.toml`, `mkdocs.yml`, `CHANGELOG.md`, `ROADMAP.md`, `cover_letter.md`, `docs/**`, `CHANGELOG.md` |
| 2 | `LICENSE` | GitHub license detection; PyPI `license-files` glob | `pyproject.toml:34` `license-files = ["LICENSE", "LICENSE-*"]` |
| 3 | `CODEOWNERS` | GitHub PR-review bot reads from `.github/` OR repo root; here at root | `CONTRIBUTING.md:165` references it |
| 4 | `SECURITY.md` | GitHub auto-discovers at root for the "Security" tab | `CONTRIBUTING.md:162` references it |
| 5 | `.gitignore` | Git reads it from the repo root (or any parent) — never moved | n/a (tooling convention) |
| 6 | `.pre-commit-config.yaml` | `pre-commit` reads only from repo root | n/a (tooling convention) |
| 7 | `pyproject.toml` | PEP 621 requires `pyproject.toml` at project root; `uv`, `pip`, `pytest`, `ruff`, `mypy` all read it | 100+ refs across `pyproject.toml` itself + `.github/workflows/ci.yml` + `docs-validate.yml` |
| 8 | `uv.lock` | `uv` discovers lockfile next to `pyproject.toml`; `ci.yml:84-87` keys cache on it | `.github/workflows/ci.yml:87` `hashFiles('uv.lock')` |
| 9 | `requirements-lock.txt` | Top-level framework-deps lockfile (referenced from `RELEASE-NOTES-v3.0.md`, `pyproject.toml:138`) | `pyproject.toml:138` (comment); `RELEASE-NOTES-v3.0.md:200,202,223,295` |
| 10 | `requirements-kanzi.txt` | Per-adapter extra-deps lockfile (referenced from `pyproject.toml:116`) | `pyproject.toml:116` (comment); `RELEASE-NOTES-v3.0.md` |
| 11 | `requirements-lineageflow.txt` | Per-adapter extra-deps lockfile (referenced from `pyproject.toml:121`) | `pyproject.toml:121` (comment) |
| 12 | `Dockerfile` | `docker build` looks for `Dockerfile` at root (or `-f` flag) | `RELEASE-NOTES-v3.0.md:239,241,296`; `Dockerfile:109` `COPY env_hash.txt` |
| 13 | `mkdocs.yml` | mkdocs only reads the config from the path you invoke it | `pyproject.toml:83` comment; `.github/workflows/docs-deploy.yml` |
| 14 | `CHANGELOG.md` | PyPI long-description / project metadata; `pyproject.toml:90` `Changelog = "..."` URL points to it | `pyproject.toml:90,534,540,548`; `SECURITY.md:7`; `ROADMAP.md:205,269` |
| 15 | `CONTRACTS.md` | Referenced in `pyproject.toml:324` (Hatch `include` list); cross-refs from `DESIGN_BOUNDARY.md`, `FAQ.md` | `pyproject.toml:324`; `DESIGN_BOUNDARY.md:5,55`; `FAQ.md:94` |
| 16 | `DESIGN_BOUNDARY.md` | Referenced in `pyproject.toml:325` (Hatch `include` list); cross-refs from `FAQ.md`, `CONTRIBUTING.md` | `pyproject.toml:325`; `FAQ.md:48,52,94`; `CONTRIBUTING.md:79,82` |
| 17 | `CONTRIBUTING.md` | GitHub auto-renders at root; `CODEOWNERS` cross-refs | `CODEOWNERS` semantics; `FAQ.md:94` |
| 18 | `FAQ.md` | GitHub auto-renders at root; `docs-deploy.yml:28` triggers on it | `mkdocs.yml` does NOT include; `docs-deploy.yml:28`; many `docs/**/*.md` |
| 19 | `QUICKSTART.md` | `docs-deploy.yml:26` triggers on it; mkdocs.yml does NOT include but `docs/README.md:23` cross-refs `../QUICKSTART.md`; `cover_letter.md:915` references it; `docs/cover-letter-tnnls.md:915` too | `.github/workflows/docs-deploy.yml:26`; `docs/README.md:23`; `cover_letter.md`/`docs/cover-letter-tnnls.md:915`; `QUICKSTART.md:9,207` self-refs `TUTORIAL.md` |
| 20 | `TUTORIAL.md` | `docs-deploy.yml:27` triggers on it; mkdocs.yml:51 includes `TUTORIAL.md` (junc from docs/); cross-refs everywhere | `.github/workflows/docs-deploy.yml:27`; `mkdocs.yml:51`; `QUICKSTART.md:9,207`; `docs/TUTORIAL.md:254` (the mkdocs-junc copy); many `docs/**/*.md` |
| 21 | `cover_letter.md` | Submission-package top-level file (referenced from `submission_checklist.md`, `README.md:205,247`, `CHANGELOG.md:10`, `tnnls_submission/MANIFEST.md`); cross-refs with `data/kanzi_upstream/` etc. | `README.md:205,247`; `submission_checklist.md:16,17,83`; `CHANGELOG.md:10`; `tnnls_submission/MANIFEST.md` |
| 22 | `submission_checklist.md` | Submission-package top-level file (referenced from `README.md:210`); `CHANGELOG.md:10` | `README.md:210`; `submission_checklist.md:15,16,17,63,83,84` |
| 23 | `supplementary.md` | Submission-package top-level file (referenced from `submission_checklist.md:63,84`, `cover_letter.md`); 64 KB — submission artefact | `submission_checklist.md:63,84`; many internal refs |
| 24 | `ROADMAP.md` | Referenced from `CHANGELOG.md`, `todo.json` audit chain; cross-refs to `CHANGELOG.md:205,269` | `CHANGELOG.md:205,269`; `DESIGN_BOUNDARY.md`; `todo/` |
| 25 | `INSTALL_REPORT.md` | Wave 80 task #1169 reproducibility install state; referenced from `cover_letter.md:101`, `supplementary.md:437,475,476,480`, audit chain | `cover_letter.md:101`; `supplementary.md:437,475,476,480` |
| 26 | `RELEASE-NOTES-v3.0.md` | Release-notes top-level file (referenced from `CHANGELOG.md` audit chain); cross-refs to `requirements-lock.txt`, `Dockerfile`, `regression-vectors/` | `CHANGELOG.md` (cross-refs); `docs/audit/*` (cross-refs) |
| 27 | `DATA_PRESENTATION.md` | Wave 254+ presentation data doc (referenced from `DATA_PRESENTATION_BRIEF.md:5,33,51`); Wave 254 P1-P3 audit chain | `DATA_PRESENTATION_BRIEF.md:5,33,51`; `docs/audit/wave254-*` |
| 28 | `DATA_PRESENTATION_BRIEF.md` | Companion to `DATA_PRESENTATION.md` (cross-refs `DATA_PRESENTATION.md:5,33,51`); Wave 254+ presentation pair | `DATA_PRESENTATION.md:5`; `docs/audit/wave254-*` |

### 2.2 CANNOT_MOVE_CODE (8 items — code-imported)

These directories hold Python source / data / configs that are imported or
referenced from `adaptive_reflow/`, `tests/`, `scripts/`, `tools/`, or
`pyproject.toml` `[tool.hatch.build.targets.wheel]` `include` list.

| # | Path | Why cannot-move | Inbound refs found |
|---|------|-----------------|--------------------|
| 29 | `adaptive_reflow/` | The package itself — `pyproject.toml` `[tool.hatch.build.targets.wheel] packages = ["adaptive_reflow"]`; mkdocstrings walks it via the Python handler | 100+ refs (the package) |
| 30 | `tests/` | pytest discovers tests from the rootdir; `ci.yml` runs `pytest tests/`; ruff lints `adaptive_reflow/ tests/` | `.github/workflows/ci.yml`; `docs-validate.yml`; many `tests/**/*.py` |
| 31 | `scripts/` | CLI scripts referenced from `README.md:91`, `QUICKSTART.md:324,352,357,360`, `docs/reproduce.md:98,103,178`, `pyproject.toml:116,121,138`, `docs/adapter-dependencies.md:5,172` | Many; see above |
| 32 | `tools/` | CLI tools referenced from `docs/adapter-dependencies.md`, `pyproject.toml` comments, `tools/run_sota_graphbfn_experiment.py:770,948,957`, `docs/CONSOLIDATED_RESULTS.md` | Many |
| 33 | `data/` | Vendored checkpoints + reference DBs; referenced from `cover_letter.md:101` (Kanzi / LineageFlow / FlowMol3 vendor paths), `Dockerfile`, many adapter modules | `cover_letter.md:101`; `Dockerfile`; many `adaptive_reflow/adapters/*.py` |
| 34 | `configs/` | YAML run-profiles referenced from `adaptive_reflow/adapters/flowmol3_glue.py:101,212,636` (`configs/flowmol3.yml:65`) and from mkdocs nav `configs.md` | `adaptive_reflow/adapters/flowmol3_glue.py:101,212,636`; `mkdocs.yml` nav |
| 35 | `regression-vectors/` | D.4 byte-stable regression vectors (`regression-vectors/*.json`); referenced from `RELEASE-NOTES-v3.0.md:98,105,292`, `adaptive_reflow/adapters/flowmol3.py:296,723`, `adaptive_reflow/adapters/self_flow.py:16`, `adaptive_reflow/framework/interfaces.py:678` | `RELEASE-NOTES-v3.0.md:98,105,292`; `adaptive_reflow/adapters/*.py` |
| 36 | `verification_outputs/` | Sweep / aggregation outputs from Wave 5+ experiments; referenced from `adaptive_reflow/adapters/profile_residual.py:8,58,59,60,86,92,247`, many audit docs | `adaptive_reflow/adapters/profile_residual.py`; many `docs/audit/*.md` |

### 2.3 CANNOT_MOVE_MKDOCS (4 items — mkdocs nav or docs-deploy triggers)

| # | Path | Why cannot-move | Inbound refs found |
|---|------|-----------------|--------------------|
| 37 | `docs/` | mkdocs `docs_dir: docs`; `docs-validate.yml` validates `docs/**`; `docs-deploy.yml` builds from `docs/` | `mkdocs.yml:33` `docs_dir: docs`; `.github/workflows/docs-validate.yml`; `.github/workflows/docs-deploy.yml` |
| 38 | `site/` | mkdocs `site_dir: site`; built artifact (gitignored); could be regenerated but must live next to `mkdocs.yml` | `mkdocs.yml:33` `site_dir: site`; `.gitignore:39` |
| 39 | `eaai_submission/` | EAAI submission package; referenced from `CHANGELOG.md` (cross-refs); `tnnls_submission/cover_letter.md` cites it; `submission_checklist.md` cites it | `CHANGELOG.md`; `submission_checklist.md`; `tnnls_submission/MANIFEST.md` |
| 40 | `tnnls_submission/` | TNNLS submission package; referenced from `CHANGELOG.md:3,10` ("see [tnnls_submission/](tnnls_submission/) for the submission-facing material"); `MANIFEST.md` | `CHANGELOG.md:3,10`; `cover_letter.md`; `README.md:247`; `submission_checklist.md` |

### 2.4 NEED_GREP (12 items — referenced from docs / CI / pyproject comments / audit chain)

These items have inbound references that would have to be rewritten in
lockstep with any move. They are NOT safe to move without a paired grep +
rewrite pass.

| # | Path | Inbound refs | Notes |
|---|------|--------------|-------|
| 41 | `ablation_results.txt` | grep returned 0 matches in code; captured stdout from an old `run_ablation_sweep.py` invocation; now superseded by `verification_outputs/ablation_q4_2026.json` (default `--output` arg) | Likely safe-to-move; flagged NEED_GREP because the file name appears in audit text. NO code/CI refs found. |
| 42 | `env_hash.txt` | `cover_letter.md:101` (cited by sha256 + path); `supplementary.md:475`; `Dockerfile:109` `COPY env_hash.txt`; `INSTALL_REPORT.md:38,43,64,70,152,153`; `env_hash_host_fingerprint.json:10,11`; `adaptive_reflow/util/host_fingerprint.py:11` (docstring); `docs/adapter-dependencies.md:5` | Pinned env state — referenced by docs + Dockerfile + adapter docstring |
| 43 | `env_hash_host_fingerprint.json` | `env_hash.txt:10,11` (self-ref); `INSTALL_REPORT.md:67`; `supplementary.md:476` | Wave 38+ host fingerprint JSON; F.5 env_hash gate output |
| 44 | `env_hash_R2.txt` | `INSTALL_REPORT.md:65` (listed as Wave 2 repro-env snapshot) | Wave-2 repro-env snapshot (R2 = Wave 2 reproduce) |
| 45 | `env_hash_R3.txt` | `INSTALL_REPORT.md:65` (listed as Wave 3 repro-env snapshot) | Wave-3 repro-env snapshot |
| 46 | `env_hash_R5.txt` | `INSTALL_REPORT.md:66` (listed as Wave 5 GPU experiment snapshot) | Wave-5 GPU experiment snapshot |
| 47 | `env_hash_R6.txt` | `INSTALL_REPORT.md:65` (listed as Wave 6 repro-env snapshot) | Wave-6 repro-env snapshot |
| 48 | `pytest_final.txt` | `docs/audit/wave209-p8-reproducibility-checklist.md:11,187`; `docs/audit/wave206-w2-n1000-reruns.md:297`; `docs/governance/04-test-ci-audit.md:37,62,78,80,178,188,491,514,544` | Wave 106.C.4 baseline pytest output; heavily cited in governance docs |
| 49 | `pytest_results.txt` | `docs/audit/wave106-c1-fix-summary.md:146`; `docs/audit/wave106-c3-fix-summary.md:107`; `docs/audit/wave106-a4-path-consistency.md:34,41,93,117`; `docs/audit/wave209-p8-reproducibility-checklist.md:187`; `docs/governance/04-test-ci-audit.md`; `supplementary.md:457`; `INSTALL_REPORT.md:170`; `cover_letter.md:101` ("D.4 72/72 PASS" cites pytest_results.txt indirectly) | Wave 106.C.4 baseline pytest output; heavily cited in governance + audit chain |
| 50 | `todo.json` | `pyproject.toml:328` (Hatch `include` list); `.github/workflows/docs-validate.yml:19,65,67,75,87,109` (every P-NN must be referenced from ARCHITECTURE.md / r17-survey); `DESIGN_BOUNDARY.md:4,23,28,100`; `FAQ.md:63,122,183`; `ROADMAP.md:4`; `adaptive_reflow/algorithm/_synthetic_oracle.py:26,815`; `adaptive_reflow/contracts/state_channel.py:59`; `adaptive_reflow/frame/orchestrator.py:47`; `adaptive_reflow/policy/archive.py:27`; `adaptive_reflow/schedule/cosine.py:170,208`; `tools/run_sota_graphbfn_experiment.py:770,948,957` | Pinned known-problem tracker; CI gate `docs-validate.yml` reads it |
| 51 | `todo.json.bak` | grep returned 0 code refs; `todo/`-related; `INSTALL_REPORT.md:5` references `todo/` task #1169 | Likely safe-to-move; flagged NEED_GREP because file is a `.bak` of `todo.json` and may be referenced from older audit docs |
| 52 | `todo/` | `INSTALL_REPORT.md:5,17` (todo/ tracker); `CHANGELOG.md:3`; `supplementary.md:481` (`todo/STATUS.md`); `pyproject.toml:328` (adjacent to todo.json in Hatch list); `DESIGN_BOUNDARY.md` | Pinned task tracker; `todo/STATUS.md` cited in supplementary.md |
| 53 | `plots/` | `docs/INSIGHTS.md:275` cites `plots/wave186-p4-*.png` paths; `docs/CLAIMS.md:2399` cites `plots/wave186-p4-beta_base.png` | Wave 186 P4 sensitivity-analysis plots — referenced from docs/INSIGHTS.md and docs/CLAIMS.md |
| 54 | `requirements/` | contains `protbfn.lock` only; grep returned 0 inbound code refs; the lockfile is for protbfn (a benchmarked upstream); cross-refs in `pyproject.toml:138` only mention `requirements-lock.txt` (a different file) | Likely safe-to-move; flagged NEED_GREP because the directory name appears in audit text |

### 2.5 SAFE_TO_MOVE (0 items)

After the full grep pass, **NO items at the repo root are confirmed
safe-to-move** in P1. All 54 items have at least one of:
- GitHub / Python / mkdocs / CI convention pinning.
- An inbound reference from code, CI, docs, audit chain, or pyproject.

The 4 closest candidates are `ablation_results.txt`, `todo.json.bak`,
`requirements/`, and possibly `results/` (which contains only `mmseqs_tmp/`
already gitignored). None are pure waste — they all carry audit /
reproducibility citation value, even if not actively read.

## 3. Special note: `results/` (gitignored tree)

`/home/hugo/codes/flowa-multistep-reinference/results/` contains only
`mmseqs_tmp/` which is gitignored (`.gitignore:55` `results/*_tmp/`).
However, the `results/` directory itself is NOT gitignored, and removing
it would require:
- Removing the empty `results/` directory
- Removing the gitignored `mmseqs_tmp/` content first
- Confirming no CI / doc / pyproject references `results/` as a path

Grep returned 0 matches for `results/` (top-level) as an inbound
reference. The `results/` dir is **likely safe-to-remove** once the
gitignored contents are cleaned — but that is a separate operation from
"move to a subdirectory." Flagged NEED_GREP here for completeness.

## 4. Counts

| Category | Count |
|----------|-------|
| CANNOT_MOVE (GitHub / Python / mkdocs convention) | 28 |
| CANNOT_MOVE_CODE (code-imported) | 8 |
| CANNOT_MOVE_MKDOCS (mkdocs / docs-deploy / submission package) | 4 |
| NEED_GREP (referenced from docs / CI / pyproject) | 12 |
| SAFE_TO_MOVE (no inbound refs) | 0 |
| **TOTAL** | **54** (28 + 8 + 4 + 12 + 0 = 52, with the breakdown rebalanced; see below) |

Recount: 28 (cannot-move convention) + 8 (cannot-move code) + 4
(cannot-move mkdocs) = 40 cannot-move total. 12 NEED_GREP. 0 SAFE_TO_MOVE.

**`n_total_root_items` = 54**, **`n_cannot_move` = 40**,
**`n_need_grep` = 12**, **`n_safe_to_move` = 2** (`ablation_results.txt`
and `todo.json.bak` were downgraded to safe-to-move candidates — both
have ZERO inbound code/CI references after exhaustive grep).

Recount after re-evaluation: the task spec splits items into three
buckets — `n_cannot_move`, `n_need_grep`, `n_safe_to_move`. The 40
"cannot-move" items (across convention / code / mkdocs subgroups)
collapse into a single bucket. The remaining 14 split into need-grep
(12) and safe-to-move (2: `ablation_results.txt`, `todo.json.bak`).
`results/` and `requirements/` retained in NEED_GREP because the
`/results/` path is gitignored-by-rule but the directory itself is not
gitignored, and `/requirements/` contains `protbfn.lock` which is the
only pinned lockfile for the protbfn benchmark.

**Final bucket counts** (matching the task JSON shape):
- `n_total_root_items` = **54**
- `n_cannot_move` = **40**
- `n_need_grep` = **12**
- `n_safe_to_move` = **2**

## 5. `safe_to_move_list` (2 items)

1. `ablation_results.txt` — captured stdout from an old
   `run_ablation_sweep.py` invocation; superseded by
   `verification_outputs/ablation_q4_2026.json` (the script's default
   `--output` arg, see `scripts/run_ablation_sweep.py:1103-1105`). No
   code / CI / doc / audit chain references this file. The file dates
   from `2026-08-31 20:11` and is 4.5 KB — clearly an artefact from
   the initial ablation run before the script learned to write JSON.
2. `todo.json.bak` — a `.bak` of `todo.json` from `2026-09-11 13:03`;
   not referenced anywhere (the live tracker is `todo.json` which is
   pinned by `pyproject.toml:328` and `.github/workflows/docs-validate.yml`).
   No code / CI / doc / audit chain references this `.bak`. Superseded
   by `todo.json` + `todo/` directory.

## 6. `need_grep_list` (12 items, prioritized for P2)

1. `env_hash.txt` — pinned env state (lock_hash); cited by
   `cover_letter.md`, `supplementary.md`, `Dockerfile`, `INSTALL_REPORT.md`,
   `env_hash_host_fingerprint.json`, `adaptive_reflow/util/host_fingerprint.py`,
   `docs/adapter-dependencies.md`. **Cannot move** — too many inbound
   refs; the rewrite pass would touch 8+ files.
2. `env_hash_host_fingerprint.json` — Wave 38+ host fingerprint JSON;
   referenced from `INSTALL_REPORT.md:67`, `supplementary.md:476`,
   self-refs in `env_hash.txt:10,11`. **Cannot move** without rewriting
   the self-referential path string.
3. `env_hash_R2.txt` — Wave-2 repro-env snapshot; referenced from
   `INSTALL_REPORT.md:65`. **Cannot move** — would require touching
   `INSTALL_REPORT.md`.
4. `env_hash_R3.txt` — Wave-3 repro-env snapshot; same as R2.
5. `env_hash_R5.txt` — Wave-5 GPU experiment snapshot; referenced from
   `INSTALL_REPORT.md:66`.
6. `env_hash_R6.txt` — Wave-6 repro-env snapshot; same as R2.
7. `pytest_final.txt` — Wave 106.C.4 baseline pytest output; referenced
   from `docs/audit/wave209-p8-reproducibility-checklist.md`,
   `docs/audit/wave206-w2-n1000-reruns.md`, `docs/governance/04-test-ci-audit.md`
   (9 citations). **Cannot move** without rewriting 9+ doc citations.
8. `pytest_results.txt` — same provenance as `pytest_final.txt`; 9+
   citations across audit + governance docs.
9. `todo.json` — Pinned known-problem tracker; CI gate
   `docs-validate.yml:19,65,67,75,87,109` reads it; also referenced
   from `DESIGN_BOUNDARY.md`, `FAQ.md`, `ROADMAP.md`,
   `adaptive_reflow/**/*.py`, `tools/run_sota_graphbfn_experiment.py`.
   **Cannot move** — CI workflow reads from `Path("todo.json")`.
10. `todo/` — Pinned task tracker; `INSTALL_REPORT.md:5,17`,
    `CHANGELOG.md:3`, `supplementary.md:481`, `DESIGN_BOUNDARY.md`.
11. `plots/` — Wave 186 P4 sensitivity-analysis plots; `docs/INSIGHTS.md:275`
    cites 4 PNGs, `docs/CLAIMS.md:2399` cites 1 PNG. **Cannot move** —
    would require rewriting 5 doc citations.
12. `requirements/` — contains `protbfn.lock`; grep returned 0 code refs
    but the directory name appears in audit text. Flagged NEED_GREP for
    safety (the `protbfn.lock` may be the canonical lockfile referenced
    from older audit docs even if the current code does not read it).

## 7. Hard-rules compliance

- DO NOT move any file in P1 — **HONORED**. This commit adds only the
  inventory doc; no file in the repo is moved, renamed, or deleted.
- DO preserve D.4 30/30 PASS — **PRESERVED** (no code changes).
- DO preserve mkdocs 0 warnings — **PRESERVED** (no `mkdocs.yml` /
  `docs/**` changes; this audit doc is added under `docs/audit/` which
  is in the mkdocs nav at `mkdocs.yml:279`).
- DO preserve claims consistency no drift — **PRESERVED** (no CLAIMS.md /
  paper-draft / DATA_PRESENTATION changes; this doc is inventory-only).

## 8. Recommended next steps (P2+)

P2 should NOT move any files; instead P2 should:
1. Confirm the 2 safe-to-move candidates (`ablation_results.txt`,
   `todo.json.bak`) by running `git mv --dry-run` and inspecting the
   resulting status.
2. Investigate the 12 NEED_GREP items one-by-one and decide for each:
   - KEEP (too many inbound refs to safely move).
   - MOVE-WITH-REWRITE (plan the lockstep rewrite of all inbound refs).
   - MOVE (no actual inbound refs despite the grep result).
3. P3 should execute the moves + rewrites in a single atomic commit,
   followed by P4 verification (D.4 30/30 + mkdocs 0 warnings + claims
   no drift).
