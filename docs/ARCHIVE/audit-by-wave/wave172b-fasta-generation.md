# Wave 172b P1 — FASTA Generation for LineageFlow + Kanzi at NFE=50/100/200

**Date:** 2026-09-16
**Branch:** main
**Scope:** Wave 172b P1 — produce 12 FASTA files (2 models × 3 NFEs × 2 arms)
ready for downstream evaluation. Each FASTA holds N=32 records (4 Pfam
families × 8 records/family).

---

## 1. NFE choice rationale

The spec named NFE=50/100/200. The rationale:

| NFE       | Why chosen                                                       | Why NOT alternatives                                         |
|-----------|------------------------------------------------------------------|--------------------------------------------------------------|
| **50**    | LineageFlow default per the published ICML 2026 ckpt config.      | NFE=10 is below protein-native quality regime (Wave 167 P5).|
| **100**   | Typical "high-quality" protein FM budget — same as Wave 166b P1.  | (—)                                                          |
| **200**   | Near-full quality regime for protein FM eval; diminishing returns| NFE=500 is the over-budget ceiling (Wave 171 P2 §2.1).       |

The three NFEs span the TYPICAL protein flow-matching regime:

- **NFE=10** was Wave 81's first cut but is below the protein-native
  quality regime (Wave 167 P5 saturation finding). Excluded.
- **NFE=500** is the over-budget ceiling at which both arms converge
  (Wave 171 P2 §2.3 saturation diagnosis). Excluded.
- **NFE=50/100/200** is the typical protein flow-matching regime
  spanning the framework-vs-baseline gap.

---

## 2. Tooling

Two FASTA generators, both in ``tools/``:

- **LineageFlow:** ``tools/gen_lineageflow_n1000_fastas.py`` (Wave 86 +
  Wave 158 + Wave 168 + Wave 170 + Wave 171 stable). CLI flags:
  ``--outdir``, ``--n``, ``--nfe``. The CLI is LineageFlow-specific
  (hardcoded ``_build_lineageflow_adapter``); it does **not** support
  kanzi.
- **Kanzi:** ``tools/w172b_gen_kanzi_fastas.py`` (this wave — written
  P1 to mirror the LineageFlow CLI surface so the downstream eval
  pipeline sees a consistent FASTA layout for both models). CLI flags:
  ``--outdir``, ``--n``, ``--nfe`` — matches the lineageflow CLI.

Both scripts run in **synthetic mode** (no GPU / no ckpt needed) so
the gen path is CI-friendly and reproducible across hosts.

### 2.1 Kanzi scope reduction (honest disclosure)

The spec described kanzi FASTAs as if kanzi natively emitted AA
sequences. It does **not** — kanzi's native output is continuous
latents / CA coordinates. The new ``w172b_gen_kanzi_fastas.py``
exercises kanzi's ``discrete_token_index`` AR-prior side channel
(``KANZI_AR_SEQ_LENGTH = 64`` tokens over ``KANZI_VOCAB_SIZE = 64``)
and emits those as a 64-residue FASTA via mod-20 AA-alphabet
mapping. This is the closest kanzi analog to LineageFlow's
per-position categorical.

The kanzi script's ``manifest.json`` carries a ``scope_note`` field
disclosing this honestly so downstream consumers can interpret the
FASTAs as kanzi's discrete-prior projections rather than direct
sequence samples.

---

## 3. Per-cell output layout

```
/tmp/w172b/fastas/
├── lineageflow_nfe_50/
│   ├── baseline.fasta   (32 records, 4 families × 8)
│   ├── framework.fasta  (32 records, 4 families × 8)
│   └── manifest.json
├── lineageflow_nfe_100/
│   ├── baseline.fasta
│   ├── framework.fasta
│   └── manifest.json
├── lineageflow_nfe_200/
│   ├── baseline.fasta
│   ├── framework.fasta
│   └── manifest.json
├── kanzi_nfe_50/
│   ├── baseline.fasta
│   ├── framework.fasta
│   └── manifest.json
├── kanzi_nfe_100/
│   ├── baseline.fasta
│   ├── framework.fasta
│   └── manifest.json
└── kanzi_nfe_200/
    ├── baseline.fasta
    ├── framework.fasta
    └── manifest.json
```

---

## 4. Per-cell sha256

```
1367fb9d9fbe261860de456ebdf97f8e17fc47ab41890f881546a292d4f1b75c  /tmp/w172b/fastas/lineageflow_nfe_50/baseline.fasta
7c6dcf70f1587170d0a85918c1ce43ba3b57645d4dcc23d8aac661a4fd68a1ae  /tmp/w172b/fastas/lineageflow_nfe_50/framework.fasta
1367fb9d9fbe261860de456ebdf97f8e17fc47ab41890f881546a292d4f1b75c  /tmp/w172b/fastas/lineageflow_nfe_100/baseline.fasta
063af7f2a41c4d291f37e629b002fd91d5057594385bb6c1454b41935b9e3766  /tmp/w172b/fastas/lineageflow_nfe_100/framework.fasta
1367fb9d9fbe261860de456ebdf97f8e17fc47ab41890f881546a292d4f1b75c  /tmp/w172b/fastas/lineageflow_nfe_200/baseline.fasta
6dc697160259528b8754c9e80ca096448cdc696b816a39ebd4c3913a8368b998  /tmp/w172b/fastas/lineageflow_nfe_200/framework.fasta
f8d64600014e62e4af1d578768187080d63b2585b542102fb8dfc1d42c75e74b  /tmp/w172b/fastas/kanzi_nfe_50/baseline.fasta
aa190a396725533a0ff142b35330bfd1a5f29e1ad013b87ea7734ccfc7222d94  /tmp/w172b/fastas/kanzi_nfe_50/framework.fasta
f8d64600014e62e4af1d578768187080d63b2585b542102fb8dfc1d42c75e74b  /tmp/w172b/fastas/kanzi_nfe_100/baseline.fasta
aa190a396725533a0ff142b35330bfd1a5f29e1ad013b87ea7734ccfc7222d94  /tmp/w172b/fastas/kanzi_nfe_100/framework.fasta
f8d64600014e62e4af1d578768187080d63b2585b542102fb8dfc1d42c75e74b  /tmp/w172b/fastas/kanzi_nfe_200/baseline.fasta
aa190a396725533a0ff142b35330bfd1a5f29e1ad013b87ea7734ccfc7222d94  /tmp/w172b/fastas/kanzi_nfe_200/framework.fasta
```

**Note on byte-identity:**

- **LineageFlow baseline** FASTAs are byte-identical across all three
  NFE values (sha256 prefix ``1367fb9d`` repeated 3 times). This is
  expected: the baseline arm is bare RNG draws over Pfam-family AA
  bias and does **not** consume the ``--nfe`` flag (NFE is a
  framework-arm parameter). The flag is preserved on the per-cell
  ``manifest.json`` for documentation but does not affect baseline
  bytes.
- **Kanzi baseline + framework** FASTAs are byte-identical across
  all three NFE values in synthetic mode. This is also expected:
  the synthetic kanzi velocity field is deterministic and does not
  vary NFE. Real-mode kanzi (which would consume ``--nfe``) is out
  of scope for this P1 (the spec's synthetic-mode invariant is
  preserved).
- **LineageFlow framework** FASTAs differ across NFE values because
  the framework's multi-round restart-blend chain consumes the
  per-round NFE budget.

---

## 5. Verification gates

- **D.4 (claims/dod):** PASS — 33 tests passed, 31 skipped (the 31
  are torch-dependent, unrelated to this P1). Audit doc adds a
  ``scope_note`` field to the kanzi manifest so the synthetic-mode
  nature of the kanzi FASTAs is disclosed, not silently dropped.
- **ruff:** PASS — ``All checks passed!`` on ``adaptive_reflow/``,
  ``tests/``, ``scripts/``, ``tools/``. The new
  ``w172b_gen_kanzi_fastas.py`` is ruff-clean.
- **claims consistency:** PASS — ``No drift detected``.

---

## 6. Files produced

- ``/tmp/w172b/fastas/{lineageflow,kanzi}_nfe_{50,100,200}/{baseline,framework}.fasta`` —
  12 FASTA files, 32 records each (N=32 = 4 families × 8 records).
- ``/tmp/w172b/fastas/{lineageflow,kanzi}_nfe_{50,100,200}/manifest.json`` —
  6 manifest files documenting per-family record counts + scope notes.
- ``tools/w172b_gen_kanzi_fastas.py`` — new kanzi FASTA generator.
- ``docs/audit/wave172b-fasta-generation.md`` — this audit doc.

Total LOC added (tools/w172b_gen_kanzi_fastas.py): 280 lines.

---

## 7. Reproducibility record

```bash
# LineageFlow cells (3 cells, ~12 sec total on a CPU host)
python tools/gen_lineageflow_n1000_fastas.py \
  --outdir /tmp/w172b/fastas/lineageflow_nfe_50/ \
  --n 32 --nfe 50
python tools/gen_lineageflow_n1000_fastas.py \
  --outdir /tmp/w172b/fastas/lineageflow_nfe_100/ \
  --n 32 --nfe 100
python tools/gen_lineageflow_n1000_fastas.py \
  --outdir /tmp/w172b/fastas/lineageflow_nfe_200/ \
  --n 32 --nfe 200

# Kanzi cells (3 cells, ~12 sec total on a CPU host)
python tools/w172b_gen_kanzi_fastas.py \
  --outdir /tmp/w172b/fastas/kanzi_nfe_50/ --n 32 --nfe 50
python tools/w172b_gen_kanzi_fastas.py \
  --outdir /tmp/w172b/fastas/kanzi_nfe_100/ --n 32 --nfe 100
python tools/w172b_gen_kanzi_fastas.py \
  --outdir /tmp/w172b/fastas/kanzi_nfe_200/ --n 32 --nfe 200

# sha256 verify
for model in lineageflow kanzi; do
  for nfe in 50 100 200; do
    for arm in baseline framework; do
      sha256sum /tmp/w172b/fastas/${model}_nfe_${nfe}/${arm}.fasta
    done
  done
done
```

---

## 8. Follow-up tasks (Wave 172b P2 candidates)

1. **Downstream HMMER eval on the 6 lineageflow cells** — invoke
   ``tools.upstream_eval.run_lineageflow_upstream_eval`` on each
   LineageFlow baseline + framework FASTA (6 invocations). The
   orchestrator writes a ``summary.json`` per cell. This is the
   real-world fair-comparison ladder: framework vs baseline
   ``family_validity`` + ``novelty`` at NFE=50/100/200.
2. **Downstream kanzi eval on the 6 kanzi cells** — kanzi FASTAs
   emitted via the AR-prior discrete-token-index channel;
   downstream eval would compute per-position entropy reduction
   + categorical-distance from Pfam-held-out reference. The kanzi
   eval path is the Wave 171 P2 ``per_position_entropy_reduction``
   metric, which the existing
   ``tools.paper_metrics_kanzi.compute_all_paper_metrics`` exposes.
3. **Real-ckpt kanzi FASTA path** — the synthetic kanzi FASTAs
   are byte-identical across NFEs (the synthetic velocity field
   is NFE-independent). A real-ckpt path (requires GPU + the
   ``data/kanzi_ckpt/cleaned_model.pt`` 529 MB ckpt) would produce
   NFE-varying FASTAs. Out of scope per the synthetic-mode
   invariant preserved in this P1.
