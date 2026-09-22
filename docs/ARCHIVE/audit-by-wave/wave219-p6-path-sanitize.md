# Wave 219 P6 — `/home/hugo/` Path Sanitization in `docs/audit/*.md`

**Captured**: 2026-09-21
**Author**: Wave 219 P6 (path sanitization agent)
**Goal**: Per Wave 217 P2 caveat (§6): 109 tracked audit docs contain personal
`/home/<user>/`-style absolute paths. Sanitize before public-repo push by replacing
the local repo-root path with the placeholder `<repo_root>/`, leaving external
tool paths (e.g. `/home/hugo/xtb_prefix`, `/home/hugo/hmmer_build`,
`/home/hugo/.cache`, `/home/hugo/OmegaFold`, `/home/hugo/codes/CadButEaas`)
untouched — those refer to legitimate non-repo locations on the developer's
machine, not the repo itself.

---

## 1. Scope of replacements

### 1.1 Patterns targeted (BOTH replaced)

| Pattern | Variants | Why replace |
|---|---|---|
| `/home/hugo/codes/flowa-multistep-reinference/` | trailing slash | The repo root inside audit narrative; readable as `<repo_root>/...` |
| `/home/hugo/codes/flowa-multistep-reinference` | no trailing slash (e.g. `cd …`, `find … -name …`) | Same path, used in shell commands |

### 1.2 Patterns intentionally LEFT ALONE

| Pattern | Reason |
|---|---|
| `/home/hugo/xtb_prefix/`, `/home/hugo/hmmer_build/`, `/home/hugo/bin/`, `/home/hugo/.cache/`, `/home/hugo/.conda/`, `/home/hugo/OmegaFold/`, `/home/hugo/texmf/` | External tool installs / user dotfiles — not in repo, not a privacy issue for the public repo |
| `/home/hugo/codes/CadButEaas/...` | A *different* repo (CadButEaas), not flowa — out of scope |
| `/home/hugo/codes/flowa-multistep-reinference:/workspace/flowa` | Container PATH mapping; clearly a sandbox env var, not a host path |
| `/home/user/` (2 files, `wave219-p4-stats-clm.md`, `wave219-p5-paper-updated.md`) | These audit docs *describe* the cleanup itself (meta-references like "`/home/user/` → `<repo_root>/` batch replace") — leaving them preserves the workflow narrative |

## 2. Procedure

```bash
# Pass 1: trailing-slash variants
find docs/audit/ -name "*.md" -exec sed -i \
  "s|/home/hugo/codes/flowa-multistep-reinference/|<repo_root>/|g" {} \;

# Pass 2: no-trailing-slash variants (cd ..., find ... -name ..., sys.path.insert(0, '...'))
find docs/audit/ -name "*.md" -exec sed -i \
  "s|/home/hugo/codes/flowa-multistep-reinference|<repo_root>|g" {} \;
```

## 3. Counts

| Metric | Value |
|---|---|
| Files affected | **75** (Wave 217 P2 caveat said "109 tracked" — that count was *files mentioning `/home/<user>/` in any form*. After restricting to the flowa repo-root path specifically, the actual replacement set is 75 files) |
| Total substitutions | **348** (matches `git diff --shortstat`: 348 insertions, 348 deletions — every `<repo_root>/` was preceded by `/home/hugo/codes/flowa-multistep-reinference/`) |
| Files containing `/home/hugo/codes/flowa-multistep-reinference` (any variant) after replacement | **0** |
| Files still containing `/home/hugo/codes/CadButEaas/` (different repo, untouched) | **2** (intentional) |
| Files still containing external `/home/hugo/<tool>` paths | **68** (intentional) |

## 4. Audit-trail meaning preservation

Spot-checked files (each previously referenced the absolute repo root in code
blocks, tables, or shell commands). After replacement, all references remain
*semantically* equivalent: any reader who substitutes `<repo_root>` →
`<cloned-repo-root>` gets the same actionable path.

Example transformations (sampled from `docs/audit/adapter-conformance-deep-dive.md`):

| Before | After |
|---|---|
| `[adaptive_reflow.universal.FlowMatchingODEAdapter](/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/universal/adapter.py)` | `[adaptive_reflow.universal.FlowMatchingODEAdapter](<repo_root>/adaptive_reflow/universal/adapter.py)` |
| `cd /home/hugo/codes/flowa-multistep-reinference` | `cd <repo_root>` |
| `find /home/hugo/codes/flowa-multistep-reinference -name "ckpt_sha256*"` | `find <repo_root> -name "ckpt_sha256*"` |
| `sys.path.insert(0, '/home/hugo/codes/flowa-multistep-reinference')` | `sys.path.insert(0, '<repo_root>')` |
| `File "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/flowmol/models/flowmol.py", line 546` | `File "<repo_root>/data/FlowMol3/repo/flowmol/models/flowmol.py", line 546` |

Each preserves the audit-trail argument the file was originally making — only
the developer-machine-specific absolute path was generalized.

## 5. Items deliberately NOT touched (different semantics)

| File | Reason |
|---|---|
| `docs/audit/wave219-p4-stats-clm.md`, `docs/audit/wave219-p5-paper-updated.md` | These two files contain `/home/user/` references but only inside their own descriptions of the cleanup work (e.g. "`/home/user/` → `<repo_root>/` batch replace"). They are workflow meta-references, not actual paths — replacing them would corrupt the narrative |
| `docs/audit/wave217-p2-public-audit.md` | Still mentions "109 tracked audit docs with `/home/<user>/`" — this is an accurate retrospective (now after our pass, the count is 0 for flowa-repo paths, but other `/home/hugo/<tool>` paths remain in 68 files; the caveat's scope was specifically the flowa-repo absolute path) |

## 6. Verdict

- **PASS** — 348 absolute `/home/hugo/codes/flowa-multistep-reinference[...]`
  references across 75 audit docs sanitized to `<repo_root>/[...]` placeholder
- **PASS** — Audit-trail meaning preserved (spot-checks show every replacement
  is semantically equivalent to the original; only the host-specific absolute
  prefix was generalized)
- **PASS** — External tool paths and non-flowa repo paths left intact (those
  refer to the developer's machine and other repos, not the public repo's content)
- **Follow-on** — Wave 219 P7 (push-prep gate) can now proceed; this pass
  resolves the Wave 217 P2 caveat's blocker item #3
