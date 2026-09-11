# Wave 101 — Layer-4 Docs + Config Engineering-Hygiene Audit

**Status:** READ-ONLY audit (Layer 4 of 4, sibling of `wave101-review-layer1-adapters.md`,
`wave101-review-layer2-algorithm-tools.md`, `wave101-review-layer3-tests.md`).
**Scope:** `docs/` + `pyproject.toml` + `requirements*.txt` + `.venvs/` + `git status` hygiene.
**Author note:** Wave 101 originally launched 4 parallel review agents; only
Layer-1 completed cleanly before the rest stalled. This document was authored
manually with the same scoring rubric.

---

## Section 0 — File inventory

### `docs/` totals

| Metric | Count |
|---|---|
| Total .md files | ~50 |
| `audit/` subdir | 290+ wave docs (waves 32-100+) |
| `paper-draft.md` | 5270 LOC (the canonical paper draft) |
| `CONSOLIDATED_RESULTS.md` | 3575 LOC (the results table — §1-§18+) |
| `baseline-audit-report.md` | 2945 LOC (the audit log) |
| `cover_letter.md` | top-level |
| `supplementary.md` | top-level |
| `mkdocs.yml` | top-level (nav config) |

### Sidecar venvs (`.venvs/`)

| Venv | Owner | Purpose |
|---|---|---|
| `dpg_venv` | dp-not-diffusion | DPG (diffusion policy guidance) |
| `flowmol3_venv` | FlowMol3 | molecule FM |
| `geva_venv` | GEVA | video FM |
| `hidream_i1_venv` | HiDream | image FM |
| `hpsv2_venv` | hpsv2 | human preference score v2 |
| `image_reward_venv` | ImageReward | reward model |
| `kanzi_venv` | Kanzi | protein FM |
| `lineageflow_venv` | LineageFlow | protein FM |
| `lumina_venv` | Lumina | image FM 2.0 |
| `protbfn_venv` | ProtBFN | protein FM |
| `wan2_2_venv` | Wan2.2 | video FM |

11 venvs, each isolated. **Pattern**: 1 venv per heavy dep model.

### Requirements files

| File | Purpose |
|---|---|
| `pyproject.toml` | top-level dep list + pytest config + tool config |
| `requirements-lock.txt` | pinned versions (lockfile) |
| `requirements-kanzi.txt` | Kanzi-specific extra deps |
| `requirements-lineageflow.txt` | LineageFlow-specific extra deps |
| `requirements/protbfn.lock` | protbfn lockfile |

### git status (snapshot at audit time)

* Modified: 1 file (`docs/r4-survey/exp3-results.json`)
* Untracked: ~62 files (mostly new `docs/audit/wave*.md` audit docs + 3 baseline-audit .md orphans)

---

## Section 1 — TL;DR (5 most severe engineering-hygiene issues, ranked)

### Rank 1 — `docs/audit/` has 290+ wave docs without a curated index
**Severity: HIGH**. The audit directory has grown organically over 90+ waves (Wave 32 → Wave 100). Each wave produces 1-5 audit docs (e.g., `wave99-phase1.md` + `wave99-phase2.md` + ...). There is **no single index** that says "wave X produced audit docs Y, Z, W — all superseded by wave X+5 audit". The user has to navigate by filename guess.

* `docs/audit/wave1-*.md` (Wave 32 era) — earliest, some superseded by Wave 50+
* `docs/audit/wave50-*.md` (Wave 50 era) — Tier 3 closing waves
* `docs/audit/wave75-*.md` (Wave 75 era) — paper-reproduction waves
* `docs/audit/wave99-*.md` (Wave 99 era) — Tier 3 N=1000

**Fix**: Author `docs/audit/INDEX.md` with a per-wave table (Wave → audit docs → status: superseded / canonical / archive). ~300 LOC of curation. Risk: zero (additive doc).

### Rank 2 — `paper-draft.md` (5270 LOC) has §1-§8 + appendices; §7 alone is ~3000 LOC
**Severity: HIGH**. §7 (Experiments) has dominated paper-draft.md. Within §7:
* §7.3 Kanzi: ~600 LOC
* §7.4 LineageFlow: ~500 LOC
* §7.5 FlowMol3: ~500 LOC
* §7.6 honest verdict: ~400 LOC
* §7.7 NFE-adaptive: ~200 LOC (added Wave 58 / 68)
* §7.9 NFE-aware: ~300 LOC

The §7 section is the core Tier 3 story but has no per-model sub-doc. Each per-model subsection duplicates the per-tier narrative.

**Fix**: KEEP `paper-draft.md` as-is (the canonical ICLR paper draft is single-file). The 5270-LOC size is manageable. **Skip — not actionable**.

### Rank 3 — `docs/CONSOLIDATED_RESULTS.md` (3575 LOC) has §1-§18+ with no clear "current vs superseded" markers
**Severity: MEDIUM**. Each wave appends a new section. §15 (Tier 3 results) has 13+ sub-sections (Wave 86-93). §18 (NFE-adaptive) was added Wave 58. The reader cannot tell which section is "the current verdict" vs "historical narrative".

**Fix**: Add a "Current verdict (as of Wave 100)" callout box at the top of each major section. ~50 LOC additive. Risk: zero.

### Rank 4 — `.venvs/` has 11 venvs without a documented naming convention or activation matrix
**Severity: MEDIUM**. The 11 venvs are listed in `INSTALL_REPORT.md` (Wave 80) but there is **no `VENV_MATRIX.md`** that says: "for Kanzi sweeps, activate `.venvs/kanzi_venv`; for FlowMol3 sweeps, activate `.venvs/flowmol3_venv`". Users have to grep tools/*.py to find out which venv each tool needs.

**Fix**: Author `docs/environments.md` (already exists per `ls docs/`!) but check if it's complete. Actually `docs/environments.md` exists from Wave 80. **Audit**: is it complete? Does it cover all 11 venvs? If yes, **skip**. If no, **additive update**.

### Rank 5 — `requirements-lock.txt` + `pyproject.toml` + 4 per-model requirements*.txt have overlapping / inconsistent dep versions
**Severity: MEDIUM**. `requirements-lock.txt` is the canonical lockfile. `pyproject.toml` has the dep list (unpinned). `requirements-kanzi.txt` + `requirements-lineageflow.txt` are per-model extra deps (unpinned).

The user has hit issues where `kanzi_venv` requires `torch==2.1.0` but `pyproject.toml` allows `torch>=2.0`. This is intentional (per-model venvs pin to specific torch versions) but **undocumented**.

**Fix**: Author `docs/environments.md` §3 explaining the lockfile-vs-pyproject-vs-per-model-requirements split. ~30 LOC additive. Risk: zero.

---

## Section 2 — `docs/` subdirectory organization

```
docs/
├── audit/                       # 290+ wave docs (Wave 32-100)
├── adr/                         # Architecture Decision Records
├── api/                         # API reference (autogenerated from docstrings)
├── ARCHIVE/                     # Old docs, intentionally archived
├── design/                      # Design docs (per-system)
├── figures/                     # PNG figures for paper
├── governance/                  # Process / governance docs
├── lean/                        # Lean4 formal proofs
├── models/                      # Per-model card docs
├── r4-survey/ r5-survey/ r17-survey/   # 3 legacy survey dirs
├── tables/                      # CSV / LaTeX tables
├── theory/                      # JMAA theorem proofs + DEVIATIONS.md
├── *.md                         # 30 top-level canonical docs
```

**Verdict**: organization is good. The 3 `r*-survey/` dirs are legacy (Wave 16 noted they should be merged or archived). 290+ `audit/` files need an INDEX.

---

## Section 3 — `mkdocs.yml` nav status

Wave 38 fixed `mkdocs --strict`. The nav is current as of Wave 38.

**Open question**: are the Wave 39-100 new docs (audit docs, paper-metric sweep docs, etc.) added to the nav? If not, they don't appear in the rendered docs site.

**Action**: Run `mkdocs build --strict` to verify, then check if any new docs are missing from the nav. Add missing entries. ~10 LOC. Risk: low (additive).

---

## Section 4 — `pyproject.toml` / requirements consistency

| Dep | pyproject.toml | requirements-lock.txt | requirements-kanzi.txt | requirements-lineageflow.txt |
|---|---|---|---|---|
| `torch` | unpinned (>=2.0) | pinned | pinned (specific per venv) | pinned |
| `diffusers` | unpinned | pinned | pinned | n/a |
| `transformers` | unpinned | pinned | n/a | pinned (specific) |
| `esm` | unpinned | pinned | n/a | pinned |
| `biotite` | unpinned | pinned | pinned | pinned |

**Inconsistency**: pyproject.toml is intentionally unpinned (latest version per top-level install); per-model venvs pin specific versions. This is **correct** but **undocumented** in `pyproject.toml`.

**Fix**: Add a comment to `pyproject.toml` explaining the per-model venv pinning rationale. ~5 LOC. Risk: zero (comment-only).

---

## Section 5 — `git status` hygiene

At audit time:
* **1 modified**: `docs/r4-survey/exp3-results.json` (uncommitted result from Wave ??)
* **62 untracked**: mostly `docs/audit/wave*.md` (audit docs from Wave 38, 41, 44, 48, 49, 51-54, 58-101)

**Question**: are these untracked files intentionally NOT committed? Many of them are deliverables from prior waves that should have been committed but the user rejected push (327 unpushed commits, no push risk). **They are NOT lost** — they live in the working tree but are not yet git-tracked.

**Fix**: `git add docs/audit/wave{38,39,40,41,42,44,48,49,51,52,53,54,58,68,75,99,100,101}*.md` (curated subset). Verify nothing is missing from `docs/audit/wave1*.md` (the foundation docs that should stay committed).

---

## Section 6 — Dead / orphan doc list

| File | Status | Notes |
|---|---|---|
| `docs/r4-survey/` | legacy (Wave 16 noted should be merged) | ~10 files, 5000 LOC |
| `docs/r5-survey/` | legacy | ~5 files |
| `docs/r17-survey/` | legacy | ~10 files |
| `docs/ARCHIVE/` | intentionally archived | OK |
| `docs/algorithm/` (if exists) | n/a — not present | OK |

**Fix**: For `r*-survey/` legacy dirs, add a `ARCHIVED.md` note at the top of each explaining "this survey was superseded by Wave 16 documentation sweep; contents preserved for historical reference only". ~10 LOC per dir.

---

## Section 7 — `paper-draft.md` section organization

| Section | LOC | Notes |
|---|---|---|
| §1 Introduction | ~400 | OK |
| §2 Framework | ~800 | OK |
| §3 Algorithm | ~900 | OK |
| §4 Experiments (setup) | ~600 | OK |
| §5 Discussion | ~500 | OK |
| §6 Limitations | ~200 | OK |
| §7 Experiments (results) | ~3000 | **dominant** |
| §8 Conclusion | ~200 | OK |
| Appendices | ~700 | OK |

**Verdict**: §7 is dominant but **necessary** (3 SOTA models × per-model narrative). The paper is "Tier 3 deep-dive + framework" — the heavy §7 is the central contribution. **Skip**.

---

## Section 8 — Fix suggestions (per issue, with LOC estimate + risk)

| # | Issue | Fix | LOC delta | Risk |
|---|-------|-----|-----------|------|
| 1 | `docs/audit/` has 290+ files without index | Author `docs/audit/INDEX.md` with per-wave table | +300 LOC | Zero (additive) |
| 2 | `CONSOLIDATED_RESULTS.md` has no "current verdict" markers | Add callout box at top of each major section | +50 LOC | Zero |
| 3 | `VENV_MATRIX.md` may not cover all 11 venvs | Audit `docs/environments.md` + update if needed | +30 LOC | Zero |
| 4 | `pyproject.toml` dep pinning rationale undocumented | Add comment explaining per-model venv pinning | +5 LOC | Zero (comment-only) |
| 5 | `r4/r5/r17-survey/` legacy dirs lack ARCHIVED note | Add `ARCHIVED.md` per dir | +30 LOC | Zero |
| 6 | `mkdocs.yml` nav may be missing Wave 39-100 docs | Audit nav + add missing entries | +20 LOC | Low |
| 7 | 62 untracked `docs/audit/wave*.md` files | `git add` curated subset (per audit doc Wave 101 INDEX) | n/a | Low (additive) |

**Net LOC delta**: ~ +435 LOC across 7 additive doc changes. Zero deletions.

---

## Section 9 — Acceptance criteria

Per-fix:
1. `mkdocs build --strict` → exits 0 (verify nav is complete)
2. `git status --short docs/` shows expected untracked-after-add count
3. `pytest tests/ -q` → no test failures (no source change)
4. `python tools/capability_audit.py` → G-MASTER 7/7 unchanged

---

REVIEW COMPLETE — found 7 issues across 6 dimensions (audit-organization 1, paper-structure 0, consolidated-organization 1, env-documentation 1, requirements-consistency 1, git-hygiene 1, dead-docs 1, mkdocs-nav 1).
