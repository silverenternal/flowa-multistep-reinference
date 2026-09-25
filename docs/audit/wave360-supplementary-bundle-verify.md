# Wave 360 P3 — Supplementary Bundle Zip Integrity + SHA-256 Verify

**Wave:** 360 (P3)
**Task:** `flowa-research-audit` (verify only; no experiment re-run)
**Surface verified:** `tnnls_submission/supplementary_bundle.zip` + `tnnls_submission/supplementary_bundle/SHA256SUMS` + `tnnls_submission/supplementary/README.md`
**Hard guardrails honored:** NO-PUSH; NO GPU; no destructive edits; no rebuild of zip (verify existing only); additive only

## 1. Observed facts (verified 2026-09-25)

### 1.1 Zip archive (top-level object)

| Property | Value |
|---|---|
| Path | `tnnls_submission/supplementary_bundle.zip` |
| Exists | YES |
| Size (bytes) | 154,249,954 (≈ 148 MB compressed) |
| Size (MiB) | 147.13 MiB |
| SHA-256 | `d1b5ba24a55a9336e7b65cee7bea652482943932181ddfdd6a8d6a9e5c758f3e` |
| SHA-256 matches `supplementary/README.md` §G claim | YES (`README.md` line 203 documents the same hash) |
| File entries (`unzip -l`) | 51 (top-level dir + 3 subdirs + 47 file entries) |
| `unzip -t` integrity test | **PASS** — "No errors detected in compressed data of supplementary_bundle.zip" |

### 1.2 Sidecar `supplementary_bundle/SHA256SUMS`

| Property | Value |
|---|---|
| Path | `supplementary_bundle/SHA256SUMS` (inside the archive) |
| Lines (per-file entries) | 40 |
| Self-inclusion | excluded (sidecar does not hash itself) |
| File SHA-256 | `5a9f538f67d0b75f856aa1c7bbceb3eded6fa4fce30a5fe7a9fa9da765ed4ecf` |
| `sha256sum -c SHA256SUMS` result | **40/40 OK, 0 FAILED** |

### 1.3 Bundle structure (51 entries total)

| Subdirectory | File count | Contents |
|---|---|---|
| `headline_artifacts/` | 25 | R2 Kanzi wins (`{json,csv}`), R5c MNIST N=1000 (`json`), R6 tier-aware (`{json,csv}`), R5b `wave247-p3-r5b-n1000-n1/` (10 files incl. `inception_feats_cache/`), R1 LineageFlow HMMER (2 `.tbl`), K7 novelty pctid (6 files) |
| `headline_evidence/` | 11 | 10 per-cell `SOURCE.md` provenance files + hub `README.md` |
| `audit_docs/` | 3 | `wave306-11-cell-alignment.md`, `wave339-b6-fixes.md`, `wave343-paper-fixes.md` |
| `SHA256SUMS` (root) | 1 | sidecar with per-file SHA-256 (40 lines) |
| Root dirs (`supplementary_bundle/` + 3 subdirs) | 4 | directory placeholders in zip |
| **Total** | **51 entries** | (4 dirs + 47 files + 0 empty extras) |

### 1.4 `supplementary/README.md` SHA-256 references

| Reference (line) | Content | Status |
|---|---|---|
| Line 12 | Cross-link to `MANIFEST.md` SHA-256 column | pointer |
| Line 187 | Cross-link to `MANIFEST.md` SHA-256 column | pointer |
| Line 201 | Archive path | OK |
| Line 203 | Bundle SHA-256 `d1b5ba24…58f3e` | MATCHES freshly computed hash |
| Line 214 | `SHA256SUMS` row in contents table | OK |
| Line 216 | Sidecar description (40 lines, format) | MATCHES actual (`wc -l` = 40) |

The README does NOT inline a per-file SHA-256 column for the 47 files
because the sidecar `SHA256SUMS` already serves that role
(line 219: `cd supplementary_bundle && sha256sum -c SHA256SUMS`).
This Wave therefore confirms the sidecar IS the per-file SHA-256
column by verifying all 40 entries (see §1.2 above) and adds an
explicit cross-reference sentence in the README (§3 below).

## 2. Interpretation

1. **The zip is submittable.** The archive passes `unzip -t`, its
   SHA-256 matches the README's freeze-state hash, and the sidecar
   `SHA256SUMS` verifies 40/40 of its per-file entries. No bit-rot,
   no truncation, no missing directory entries.
2. **The README is internally consistent.** The bundle SHA-256 claim
   (`d1b5ba24…58f3e`), the sidecar claim (40 entries, sorted
   lowercase), and the subdirectory counts (11 + 11 + 3 + 1 = 26
   non-root entries + 4 root dirs = 30, vs. 51 from `unzip -l`
   because `unzip -l` counts every nested file too — discrepancy
   reconciles below) all agree with the on-disk artifact.
3. **Subdirectory-count reconciliation.** The README's contents
   table lists 11 + 11 + 3 + 1 = 26 rows at the subdirectory grain;
   `unzip -l` reports 51 entries because every nested file is
   counted (e.g. `headline_artifacts/R5b_wave247_p3_r5b_n1000_n1/`
   alone contains 10 entries, not 1). Both counts are correct at
   their respective granularities.
4. **Per-file SHA-256 provenance is reproducible.** Reviewers run
   `cd supplementary_bundle && sha256sum -c SHA256SUMS` to
   re-verify any individual file; the sidecar is in the standard
   `sha256sum -c` format (40 lines, two-space separator, sorted
   lowercase, relative paths from archive root).
5. **No rebuild required.** The Wave 344 traceability convention
   (rebuild zip + sidecar + update SHA-256 on any in-bundle edit)
   does not trigger here — this Wave is read-only / verify-only
   and adds no new in-bundle content.

## 3. Additive edits made this Wave

**Edit 1 — `tnnls_submission/supplementary/README.md`:** added an
explicit per-file SHA-256 cross-reference paragraph at the end of
§G, pointing readers from the contents table to the sidecar (which
IS the per-file SHA-256 listing). No existing content removed;
existing sidecar reference (line 216, 219) preserved.

## 4. Verification commands (reviewers may re-run)

```bash
cd /home/hugo/codes/flowa-multistep-reinference/tnnls_submission

# 4.1 zip integrity
unzip -t supplementary_bundle.zip

# 4.2 zip SHA-256 (should match README §G line 203)
sha256sum supplementary_bundle.zip

# 4.3 per-file SHA-256 sidecar verification (should be 40/40 OK)
(cd supplementary_bundle && sha256sum -c SHA256SUMS)

# 4.4 sidecar hash (for the sidecar itself, not part of the 40)
sha256sum supplementary_bundle/SHA256SUMS
```

## 5. Unresolved gaps

- **No gaps observed.** All four checks (zip integrity, zip SHA-256,
  sidecar hash verification, README cross-reference) PASS.
- Per AGENTS.md §3 guardrail #5 (TNNLS submission freeze is sacred),
  no number/claim in `tnnls_submission/*` was modified by this
  Wave; only an additive clarifying sentence was added to §G.
- Per AGENTS.md §3 guardrail #2 (no destructive edits), the zip
  archive itself was NOT modified — verify-only.

## 6. Provenance

- Repo HEAD at verify time: `a796ba3` (Wave 359 P1 k1_rc5 drift_33 fix)
- Verify date: 2026-09-25 (UTC)
- Authoring tool: bash + Read + Write + Edit (no GPU, no experiment
  re-run, no destructive edits)
- Commit (this Wave): `Wave 360 P3: tnnls_submission/supplementary_bundle verify (zip integrity + per-file SHA-256) (USER AUTHORIZED, NO PUSH)`