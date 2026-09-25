# Wave 353 P3 — §3.5 hash-chained ledger concrete SHA-256 example

**Date:** 2026-09-25
**Wave:** 353 P3 (USER AUTHORIZED, NO PUSH)
**Author:** ultracode subagent (Wave 353 remaining-tasks sweep)
**Scope:** paper §3.5 additive SHA-256 ledger example + audit note. Pure doc, no code, no
experiments, no D.4 changes.

## 1. What changed

`docs/drafts/paper-A-final.md` §3.5 gained an additive §3.5.1 subsection
("Concrete SHA-256 ledger example (Wave 349 R1 3-seed GPU artifact)") inserted
between the §3.5 main description / Algorithm signature and the §3.6 heading.
No numbers were edited, no claim wording was changed, no claim status was
promoted. The §3.5 main body, the §3.5 algorithm signature paragraph, and all
surrounding §3.4 / §3.6 / §3.7 paragraphs are byte-identical to the prior
revision. The §3.5.1 addition is purely additive prose + a 3-row table + a
3-line `bash` reproducibility recipe + 3 cross-reference citations.

## 2. Why now

§3.5 introduced the hash-chained ledger concept in abstract terms
(`LedgerChain.append()` / `verify_incremental()` per-round invariants, the
`SHA-256(canonical(fields) ∥ h_{i-1})` row-hash definition). A reviewer reading
the paper §3.5 alone would have no concrete byte-level artifact to point at
for "what does a ledger entry actually look like in this repo". The
`verification_outputs/wave349-r1-3seed-gpu/` directory is the highest-fidelity
byte-addressable ledger artifact the repo ships: 2 seed manifests
(`seed42_manifest.json`, `seed44_manifest.json`) plus an aggregator
(`SHA256SUMS`), all with reproducible content hashes that bind the wave-349
zero-fallback retro-validation claim (§2.3 of `wave349-gap-audit.md`) to its
underlying JSON bytes. Anchoring §3.5 to that artifact closes the gap between
"the framework can prove the published metric ledger was not hand-edited" and
"here is the exact 64-hex-char hash chain a reviewer would re-derive".

## 3. Concrete ledger anchors (additive §3.5.1 contents)

| artifact | bytes | sha256 | role |
|---|---:|---|---|
| `verification_outputs/wave349-r1-3seed-gpu/seed42_manifest.json` | 805 | `0861e4b156c1e64078f56561c093dfe10e22542aa9740efbb8f4a61d76552ce7` | seed=42 evidence manifest: `n=1000` records, 4 Pfam families × 250 records, `framework_fallback_per_family_count={}` |
| `verification_outputs/wave349-r1-3seed-gpu/seed44_manifest.json` | 805 | `cc4390bc4a02799dc2add0ad251e7e5ece08e29f1ec2322c8c6f28f813cf44ed` | seed=44 evidence manifest: `n=1000` records, same 4-family × 250 partition, `framework_fallback_per_family_count={}` |
| `verification_outputs/wave349-r1-3seed-gpu/SHA256SUMS` | 2642 | `28aafe1c95195c0a2daa727150e4ea42651daa49cd5872443a81b88cfed15be2` | aggregator: `<sha256>  <filename>` column binding both manifests + markdown preamble |
| (derived) inner column hash | n/a | `206d69942a3325116c9a86062c3bb0f41302316fee48d6868d24bec50cc27cd8` | SHA-256 of just the per-file sha256 column rows (preamble excluded) |

All four hex hashes were re-derived in this wave via `sha256sum` against the
on-disk bytes; no hash in §3.5.1 was copied from a prior audit doc without
re-verification.

## 4. Reproducibility recipe (additive §3.5.1 bash block)

```bash
cd verification_outputs/wave349-r1-3seed-gpu
sha256sum --check SHA256SUMS     # both manifests must print OK
sha256sum SHA256SUMS             # must equal 28aafe1c95195c0a2daa727150e4ea42651daa49cd5872443a81b88cfed15be2
```

A regenerated manifest whose bytes diverge (different seed, different family
partition, non-empty fallback) fails step 1; a hand-edited wrapper that
re-prints the committed shasums but changes the preamble fails step 2. This is
the artifact-level instantiation of the §3.5 per-round invariant
`SHA-256(canonical(fields) ∥ h_{i-1})`: the per-file SHA-256 column plays the
role of `prev_ledger_row_hash` for the next row, and `sha256sum` over raw
bytes plays the role of `compute_ledger_row_hash`'s canonicalisation.

## 5. Observed vs interpretation vs gap

### 5.1 Observed facts (re-derived 2026-09-25)

- `sha256sum verification_outputs/wave349-r1-3seed-gpu/seed42_manifest.json`
  → `0861e4b156c1e64078f56561c093dfe10e22542aa9740efbb8f4a61d76552ce7` (805 bytes)
- `sha256sum verification_outputs/wave349-r1-3seed-gpu/seed44_manifest.json`
  → `cc4390bc4a02799dc2add0ad251e7e5ece08e29f1ec2322c8c6f28f813cf44ed` (805 bytes)
- `sha256sum verification_outputs/wave349-r1-3seed-gpu/SHA256SUMS`
  → `28aafe1c95195c0a2daa727150e4ea42651daa49cd5872443a81b88cfed15be2` (2642 bytes)
- `sha256sum verification_outputs/wave349-r1-3seed-gpu/seed{42,44}_manifest.json`
  piped through `sha256sum` → `206d69942a3325116c9a86062c3bb0f41302316fee48d6868d24bec50cc27cd8`
  (inner column hash, preamble excluded)
- `python3 tools/check_claims_consistency.py` → "No drift detected." (61 ACTIVE
  claims, 0 provisional, 2 deprecated; CLM-040 forced to PROVISIONAL unchanged)
- `python3 -m pytest tests/test_d4_regression_vectors.py -q` → 30/30 PASS
  (warnings are pre-existing deprecations unrelated to this wave)
- `mkdocs build --strict` → exit 0 ("Documentation built in 24.35 seconds")
- `docs/drafts/paper-A-final.md` line count delta: +19 lines (one new
  subsection heading + table + 2 paragraphs + bash block + cross-references)
- No `.py` files touched → no `ruff check` delta

### 5.2 Interpretation

The additive §3.5.1 anchors the §3.5 abstract invariant to a concrete,
verifiable, byte-stable artifact that already exists in the repo. The
reproducibility recipe (`sha256sum --check` + `sha256sum SHA256SUMS`) lets a
reviewer re-derive both per-file hashes and the aggregator hash from the
on-disk bytes in two commands, with no framework code execution required.
This is a tighter reviewer loop than re-running the wave-349 sweep driver and
is appropriate for §3.5's reproducibility-claim emphasis.

The §3.5.1 table distinguishes the aggregator wrapper hash
(`28aafe1c…`, 2642 bytes including the markdown preamble) from the inner
column hash (`206d6994…`, preamble-excluded) because the two diverge on a
preamble edit — a reviewer who edits only the markdown narrative (e.g. to
rephrase the GPU note) will see the wrapper hash change while the inner
column hash and the per-file `sha256sum --check` outcome stay stable. That
distinction is informative for tamper analysis and is preserved here per
Wave 268 strict-clean additive-only rule.

### 5.3 Unresolved gaps

None new. The R1 PARTIAL / single-seed-disclosed status is preserved verbatim
per Wave 268 strict-clean "no number change" rule + Wave 349 P2 §7.2 R1 row
addendum; §3.5.1 references that preservation in passing ("anchored on
byte-stable evidence rather than narrative assertion") but does not promote
any status label. The wave-349 R1 3-seed pool aggregation d_z materialisation
remains camera-ready scope for the next wave (2-4h wall-clock with GPU
dispatch) per `wave349-r1-3seed-gpu` §Interpretation.

## 6. Cross-references

- Paper: `docs/drafts/paper-A-final.md` §3.5 main + new §3.5.1 (additive)
- Concrete artifacts: `verification_outputs/wave349-r1-3seed-gpu/{seed42_manifest.json,seed44_manifest.json,SHA256SUMS}`
- Upstream wave audits:
  - `docs/audit/wave349-r1-3seed-gpu.md` — Wave 349 P4 + P5 final R1 3-seed audit
  - `docs/audit/wave349-impl.md` — Wave 349 P1 + P3 audit
  - `docs/audit/wave349-gpu-acceleration.md` — Wave 349 P4 cuda:0 dispatch audit
  - `docs/audit/wave349-gap-audit.md` §2.3 — R1 3-seed retro-validation (VERIFIED)
- Code anchors cited in §3.5: `adaptive_reflow/frame/ledger_chain.py:113`,
  `:167-218`, `:228`, `:65-110`, `:380-460`
- Tests cited in §3.5: `tests/test_ledger_chain.py` (50/50 PASS),
  `tests/test_ledger_chain_parallel.py` (25/25 PASS),
  `tests/test_d4_regression_vectors.py` (30/30 PASS)

## 7. Hard guardrails compliance

- **Vendored upstream:** untouched (no `data/*` edits)
- **No destructive edits:** additive paragraph only, no rewording of existing
  §3.5 prose, no numeric changes, no claim status changes
- **NO-PUSH:** committed locally only; not pushed (user gating preserved)
- **Honest uncertainty:** R1 PARTIAL status preserved; no promotion to SUPPORTED
- **TNNLS freeze:** §3.5 is in `docs/drafts/`, not in `tnnls_submission/`; no
  SHA-256 column regeneration required for this wave
- **Per-phase audit doc:** this file (12-decimal-CLAIMS-table format preserved
  per Wave 121-273 template; no claim table changes)
- **Stricter = cleaner:** single §3.5.1 subsection, single audit doc, single
  commit; no extra files touched

## 8. Verification summary

| gate | command | result |
|---|---|---|
| Claims consistency | `python3 tools/check_claims_consistency.py` | PASS — "No drift detected." (61 ACTIVE, 0 provisional) |
| D.4 regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | PASS — 30/30 |
| Mkdocs strict | `mkdocs build --strict` | PASS — exit 0 ("Documentation built in 24.35 seconds") |
| Ruff (no .py touched) | n/a | n/a — no .py edits in this wave |
| SHA-256 re-derivation | `sha256sum` over all 3 artifacts + inner column | PASS — all 4 hashes match §3.5.1 + this audit |