# Wave 174 P3 — 12-cell FASTA ladder (lineageflow + kanzi @ NFE=50/100/200)

**Date:** 2026-09-17
**Branch:** main
**Scope:** Wave 174 P3 — generate the 12-cell FASTA ladder that feeds
the Wave 172b §10.18 cross-model NFE curve empirical comparison.
Two models × three NFE levels × two arms = 12 cells, N=32 records per
FASTA (4 Pfam families × 8 records each).

---

## 1. What this commit delivers

12 FASTA files in `/tmp/w174/fastas/` plus per-cell `manifest.json`:

```
/tmp/w174/fastas/
├── lineageflow_nfe_50/   {baseline.fasta, framework.fasta, manifest.json}
├── lineageflow_nfe_100/  {baseline.fasta, framework.fasta, manifest.json}
├── lineageflow_nfe_200/  {baseline.fasta, framework.fasta, manifest.json}
├── kanzi_nfe_50/         {baseline.fasta, framework.fasta, manifest.json}
├── kanzi_nfe_100/        {baseline.fasta, framework.fasta, manifest.json}
└── kanzi_nfe_200/        {baseline.fasta, framework.fasta, manifest.json}
```

Every FASTA carries 32 records (32 `>` headers), partitioned as
8 records per family × 4 Pfam families (PF00005.27 / PF00072.24 /
PF00183.19 / PF02517.18).

---

## 2. Generator dispatch (re-affirms Wave 174 P2)

Per the Wave 174 P2 audit
(`docs/audit/wave174-dispatch-verification.md` §2), `tools/gen_lineageflow_n1000_fastas.py`
is a **lineageflow-only** generator (no `--model` flag, unconditionally
constructs the LineageFlow adapter). The canonical cross-model flow uses
two **sibling** scripts:

| Model       | Script                                            |
|-------------|---------------------------------------------------|
| lineageflow | `tools/gen_lineageflow_n1000_fastas.py`           |
| kanzi       | `tools/w172b_gen_kanzi_fastas.py` (Wave 172b P1)  |

DO NOT invoke `gen_lineageflow_n1000_fastas.py` for kanzi cells (it
will silently produce LineageFlow content under the kanzi filename).

---

## 3. SHA-256 fingerprints (verifies lineageflow ≠ kanzi)

```
lineageflow_nfe_50/baseline.fasta   1367fb9d9fbe261860de456ebdf97f8e17fc47ab41890f881546a292d4f1b75c
lineageflow_nfe_50/framework.fasta  7c6dcf70f1587170d0a85918c1ce43ba3b57645d4dcc23d8aac661a4fd68a1ae

lineageflow_nfe_100/baseline.fasta  1367fb9d9fbe261860de456ebdf97f8e17fc47ab41890f881546a292d4f1b75c
lineageflow_nfe_100/framework.fasta 063af7f2a41c4d291f37e629b002fd91d5057594385bb6c1454b41935b9e3766

lineageflow_nfe_200/baseline.fasta  1367fb9d9fbe261860de456ebdf97f8e17fc47ab41890f881546a292d4f1b75c
lineageflow_nfe_200/framework.fasta 6dc697160259528b8754c9e80ca096448cdc696b816a39ebd4c3913a8368b998

kanzi_nfe_50/baseline.fasta         f8d64600014e62e4af1d578768187080d63b2585b542102fb8dfc1d42c75e74b
kanzi_nfe_50/framework.fasta        88e9b1c1adbc7c9ed17f8a822c4658501c7f7a620f4bd12c917eba99a99d8365

kanzi_nfe_100/baseline.fasta        f8d64600014e62e4af1d578768187080d63b2585b542102fb8dfc1d42c75e74b
kanzi_nfe_100/framework.fasta       cac666c25c155a8a57c4c402b88d553525cd023ead01e27255d51b1afc4a5255

kanzi_nfe_200/baseline.fasta        f8d64600014e62e4af1d578768187080d63b2585b542102fb8dfc1d42c75e74b
kanzi_nfe_200/framework.fasta       2524106a8db4aa5b9b87dec08f555d7251fecd64dafe68f555477e3717a5aefa
```

**Dispatch verification:**

| Comparison                                  | Result          |
|---------------------------------------------|-----------------|
| lineageflow_nfe_50/baseline vs kanzi_nfe_50/baseline   | DIFFERENT (1367fb9d… vs f8d646…)   |
| lineageflow_nfe_100/baseline vs kanzi_nfe_100/baseline | DIFFERENT (1367fb9d… vs f8d646…)   |
| lineageflow_nfe_200/baseline vs kanzi_nfe_200/baseline | DIFFERENT (1367fb9d… vs f8d646…)   |

Cross-model dispatch confirmed — `gen_lineageflow_n1000_fastas.py`
(lineageflow-only) and `w172b_gen_kanzi_fastas.py` (kanzi-only)
emit byte-distinct baselines at every NFE level.

**Within-model NFE byte-stability:**

| Model       | Baseline across NFE | Framework across NFE |
|-------------|---------------------|----------------------|
| lineageflow | byte-identical (1367fb9d…) — bare RNG over Pfam bias, `--nfe` is framework-arm only | 3 distinct SHAs (NFE=50/100/200) — restart-strength + NFE wiring (Wave 168 + Wave 173 P4) |
| kanzi       | byte-identical (f8d646…) — synthetic velocity field is NFE-independent for the baseline arm | 3 distinct SHAs (NFE=50/100/200) — kanzi framework arm now respects `--nfe` (Wave 173 P4 fix) |

The lineageflow baseline byte-stability and the kanzi baseline
byte-stability are **preserved invariants** (consistent with Wave 81/86
manifest bytes). The lineageflow baseline SHAs are also identical
across NFE because `--nfe` only feeds the framework arm's restart-blend
strength (Wave 168 wiring). The kanzi baseline is NFE-independent in
synthetic mode. Both observed behaviors match the Wave 172b P1
invariants.

The framework arm's NFE differentiation reflects the Wave 173 P4
fixes (`2bc520d`, `f30f309`): lineageflow scales `restart_strength` by
`NFE_ref / NFE`; kanzi adapter now respects `--nfe`. This is the
**mechanism** by which the Wave 174 §10.19 NFE curve surfaces
framework-vs-baseline gap changes that were washed out at the
single-NFE Wave 172b §10.18 measurement.

---

## 4. NFE choice rationale (matches Wave 172b P1)

| NFE   | Reason                                                       |
|-------|--------------------------------------------------------------|
| 50    | LineageFlow default per published ICML 2026 ckpt config      |
| 100   | typical high-quality protein FM budget                       |
| 200   | near-full quality regime                                     |

Excluded: NFE=10 (below protein-native quality regime per Wave 167 P5);
NFE=500 (over-budget ceiling per Wave 171 P2 saturation diagnosis).

---

## 5. Verification gates

- D.4: **PASS** (33 passed, 30 torch-skipped unrelated; `pytest tests/ -k "d4" -q`)
- ruff: **PASS** (All checks passed on `tools/` + `docs/audit/`)
- claims consistency: **PASS** (39 active claims, 0 provisional, 2 deprecated; "No drift detected")

---

## 6. Downstream consumers

These 12 cells feed:
- Wave 174 §10.19 — empirical foldability + scPerplexity ladder at
  typical-regime NFE (next agent after P3)
- Wave 175+ — incremental paper section revisions that supersede the
  Wave 172b §10.18 single-NFE point estimates
