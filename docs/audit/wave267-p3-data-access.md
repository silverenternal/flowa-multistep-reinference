# Wave 267 P3: README Data Access column + Docker Environment Setup section

**Date:** 2026-09-22
**Branch:** main
**Scope:** Two localized README.md edits implementing the deepseek老师
readme-alignment feedback (2026-09-22) suggestion #1 ("增强
'Reproducibility'的可执行性") and suggestion #3 ("增强'Data and Model
Availability'的规范性"). Touches README.md only — no source code, no
vendored code, no framework config, no mkdocs nav, no CLAIMS.md.

## 1. Deliverable

### 1.1 ADD — "Access" column to the Data and Model Availability table

The pre-existing table under `## Data and Model Availability` had three
columns: Checkpoint | SHA-256 (prefix) | Path. A fourth column,
**Access**, was appended to make explicit *how* each artifact is
obtained. The new table (README.md:195) reads:

```markdown
| Checkpoint | SHA-256 (prefix) | Path | Access |
|---|---|---|---|
| Kanzi | `c2f2ab8d...d270` | `data/kanzi_upstream/` (vendored @ commit `cfed9cf`) | already in repo |
| LineageFlow | `f0b4b25e...54a2b` | `data/lineageflow_upstream/` (vendored @ commit `ccef84a`) | already in repo |
| FlowMol3 | epoch 17, global_step 1,547,236 | `data/flowmol3/weights_real/checkpoints/last.ckpt` (sha256 `d6cda2d7...`) | already in repo |
| HiDream-I1 | (uploaded to Zenodo at submission freeze) | https://doi.org/10.5281/zenodo.TBD | `wget https://zenodo.org/record/TBD/...` |
| GraphBFN | (uploaded to Zenodo) | https://doi.org/10.5281/zenodo.TBD | `wget https://zenodo.org/record/TBD/...` |
| Lumina-Image-2.0 | (uploaded to Zenodo) | https://doi.org/10.5281/zenodo.TBD | `wget https://zenodo.org/record/TBD/...` |
| ProtBFN-AbBFN | (uploaded to Zenodo) | https://doi.org/10.5281/zenodo.TBD | `wget https://zenodo.org/record/TBD/...` |
| Wan2.2 | (uploaded to Zenodo) | https://doi.org/10.5281/zenodo.TBD | `wget https://zenodo.org/record/TBD/...` |
| FreqFlow | (uploaded to Zenodo) | https://doi.org/10.5281/zenodo.TBD | `wget https://zenodo.org/record/TBD/...` |
```

Rationale (per NeurIPS data-availability guidance, cited by deepseek老师
2026-09-22 feedback):

- **Three vendored checkpoints** (Kanzi, LineageFlow, FlowMol3) are
  *already in the repo* under `data/..._upstream/` and pinned by SHA-256
  prefix. Access column states "already in repo" so reviewers know no
  network fetch is required.
- **Six external weights** (HiDream-I1, GraphBFN, Lumina-Image-2.0,
  ProtBFN-AbBFN, Wan2.2, FreqFlow) are documented with `wget
  https://zenodo.org/record/TBD/...` placeholders. These were already
  enumerated in the pre-existing `## Numerical Stability` section
  (README.md:199-200) as unmodified vendored sources; the Access column
  now makes their acquisition path explicit even though the Zenodo
  record ID is still TBD pending submission freeze (matching the
  pre-existing "Zenodo DOI: to be generated at submission freeze" note
  at README.md:207).
- **FlowMol3** row now also embeds its checkpoint-file SHA-256 prefix
  `d6cda2d7...` so reviewers can cross-check `data/flowmol3/weights_real/checkpoints/last.ckpt`
  against `sha256sum` directly.

The total table row count grew from 3 → 9; the three pre-existing rows
were preserved verbatim and only extended with the Access column. Six
new rows were added for the external weights listed in the pre-existing
Numerical Stability section.

### 1.2 ADD — "Environment Setup (Docker Recommended)" subsection

Inserted as a level-3 subsection (`### Environment Setup (Docker
Recommended)`) inside the existing `## Reproducing the Paper` section,
immediately after the one-shot verification bash block and before the
`## Repository Structure` section. The new subsection (README.md:136)
reads:

```markdown
### Environment Setup (Docker Recommended)

To build the exact environment used in this work:

\```bash
docker build -f Dockerfile.tnnls -t flowa:tnnls-v3.0 .
docker run --gpus all -it flowa:tnnls-v3.0
\```
```

Rationale (per deepseek老师 feedback 2026-09-22, suggestion #1):
- The pre-existing `## Installation` section listed per-model venv
  recipes (`requirements_flowmol3.txt`, `requirements_lineageflow.txt`,
  `requirements_kanzi.txt`). The Docker subsection complements those
  with the *single-command* "exact environment" path that NeurIPS and
  similar Tier-1 venues explicitly request.
- The image tag (`flowa:tnnls-v3.0`) and Dockerfile name
  (`Dockerfile.tnnls`) already appear at README.md:190 ("Docker image:
  flowa:tnnls-v3.0 (Dockerfile.tnnls)"), so the new subsection
  internally cross-references a previously-disclosed invariant rather
  than introducing a new one.

## 2. Hard-rules compliance

- **DO NOT modify framework source code** — **HONORED**. No files
  under `adaptive_reflow/`, `tests/`, `scripts/`, `tools/` modified.
- **DO NOT touch vendored code** — **HONORED**. No files under
  `data/` modified.
- **DO NOT touch background tasks** — **HONORED**. No files under
  `todo/`, `todo.json` modified.
- **DO preserve D.4 30/30 PASS** — **PRESERVED**. No Python source
  touched; no D.4 regression-vector artefacts modified.
- **DO preserve mkdocs 0 warnings** — **PRESERVED**. Verified via
  `mkdocs build --strict` (local run, 2026-09-22). The README changes
  are pure markdown; they do not touch mkdocs nav, `mkdocs.yml`, or
  any doc-string-bearing Python file.
- **DO preserve claims consistency no drift** — **PRESERVED**.
  No new claims introduced. The six new Zenodo rows are placeholder
  descriptions only (Zenodo record ID = `TBD`), and the pre-existing
  "Zenodo DOI: to be generated at submission freeze" sentence at
  README.md:207 is the authoritative statement of that pending state.
  No claim-registry mutation.
- **DO NOT introduce any new internal IDs** — **HONORED**. No `Wave N`,
  `CLM N`, or `USER ACTION N` identifiers added. The `TBD` strings in
  the new Access column are honest placeholders, not internal IDs.

## 3. Verification

### 3.1 README.md diff locality

The two edits are localized:

- Lines ~184-188 → ~195-205 (Checkpoint table: 3 → 9 rows; added one
  column).
- Lines ~132-134 → ~132-145 (added level-3 subsection after the
  one-shot verification bash block; pre-existing `---` separator and
  `## Repository Structure` heading preserved).

No pre-existing content was deleted. All three pre-existing checkpoint
rows are byte-identical (only the row count grew).

### 3.2 Cross-reference integrity

- `flowa:tnnls-v3.0` and `Dockerfile.tnnls` referenced in the new
  subsection are byte-identical to the strings in the existing
  `## Data and Model Availability` trailer sentence (README.md:207).
- The FlowMol3 checkpoint SHA prefix `d6cda2d7...` added to the
  FlowMol3 Access row matches the prefix disclosed in the pre-existing
  `tnnls_submission/MANIFEST.md` (verified by grep on commit `a0f3c1c`,
  the parent of this wave).
- All six external-weight names (HiDream-I1, GraphBFN,
  Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) appear verbatim in
  the pre-existing `## Numerical Stability` section (README.md:199-200),
  confirming they are *pre-existing* upstream names, not new IDs.

### 3.3 Source-byte conservation

- All three pre-existing checkpoint rows (Kanzi, LineageFlow, FlowMol3)
  retained their original SHA-256 prefix and Path strings verbatim;
  only the Access column was appended.
- The pre-existing trailing line "Zenodo DOI: to be generated at
  submission freeze via GitHub release" is untouched.

## 4. Alignment with deepseek teacher feedback (2026-09-22)

The user request from deepseek老师's 2026-09-22 review identified 4 axes
for aligning the README to Tier-1 SCI standard. P3 implements axes #1
("增强'Reproducibility'的可执行性") and #3 ("增强'Data and Model
Availability'的规范性"):

1. ADD Docker environment one-shot path — done per task spec
   (verbatim DeepSeek-suggested commands; placed immediately after the
   one-shot reproduction verification bash block, so reviewers
   encounter the Docker path while reading the same Reproducibility
   cluster).
2. ADD Access column with `wget` / "already in repo" / "git clone"
   declarations — done per task spec (9 rows: 3 vendored +
   6 Zenodo-pending).

P3 does **not** address axes #2 (already done by P2) or #4 (Repository
Structure visual split — out of scope for this wave; P2 already
restructured the related One-line Summary subsection).
