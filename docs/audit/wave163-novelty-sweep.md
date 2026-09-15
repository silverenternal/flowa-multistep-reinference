# Wave 163 P4 — LineageFlow novelty_mmseqs2 N=1000 sweep

**Date:** 2026-09-15
**Branch:** main
**Agent:** Wave 163 Agent 4 (novelty_mmseqs2 sweep)
**Scope:** Run novelty_mmseqs2 evaluation on baseline + framework FASTAs (N=1000 each),
compute novelty count + delta_pct + avg min e-value, sha256 the outputs, verify gates.

---

## 1. Verdict summary

| Field | Value |
|-------|-------|
| Sanity N=5 | **PASS** (both arms: pipeline runs end-to-end; valid JSON output) |
| N=1000 baseline hits (raw m8 lines) | 82 (with `-e 10` permissive threshold) |
| N=1000 framework hits (raw m8 lines) | 25 |
| Baseline novel count (e>1e-3 OR no-hit) | 1000 / 1000 |
| Framework novel count (e>1e-3 OR no-hit) | 1000 / 1000 |
| Delta novel count | **0** (0.00%) |
| Baseline avg min e-value (hits-only, n=77 queries) | 2.711 |
| Framework avg min e-value (hits-only, n=25 queries) | 4.959 |
| novelty_mmseqs2 status | **PARTIAL** — pipeline works end-to-end; strict 1e-3 novelty count saturated at 100% for both arms due to small/diverse holdout target DB |
| Gates | d4 (33 passed, 31 skipped-torch-missing), ruff (0 errors), claims (no drift) |

**Headline:** Both arms completed the novelty_mmseqs2 sweep against the
holdout target DB (200 sequences from `random_clan.fasta`). All 1000
sequences in each arm register as "novel" at the strict e<1e-3 threshold
because the holdout DB is too divergent from the generated sequences
(matching families PF00005/72/183/02517 vs. unrelated holdout clan).
The **avg min e-value among queries that DO have hits** shows a
**+83% increase** for framework (2.711 → 4.959, i.e. framework queries
are **farther** from any target DB homolog). This is a one-sided novelty
**signal** (lower = closer match = less novel → framework less close =
more novel), but it is not statistically significant under Bonferroni
(only 77 vs 25 of 1000 queries have hits). Status: **PARTIAL** — pipeline
works; metric uninformative at strict threshold; secondary metric (avg
min e-value) shows directional novelty improvement.

---

## 2. Method

### 2.1 — Inputs

- **Baseline FASTA:** `/tmp/w158/lineageflow_real_fastas/baseline.fasta`
  (1000 records, real LineageFlowAdapter-solved, 126 939 bytes)
- **Framework FASTA:** `/tmp/w158/lineageflow_real_fastas/framework.fasta`
  (1000 records, real LineageFlowAdapter-solved, 128 313 bytes)
- **Target DB (holdout surrogate):** `data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB`
  (200 protein sequences from `random_clan.fasta`, mtime Sep 8 07:36)
- **mmseqs binary:** `/home/hugo/bin/mmseqs`
  (version `c77b5afa910bec52c784566e378cb6ebd3d0d453`, sha256
  `9760ae8683802a8bf987cc48e6a168e363dc62fb969777b6d8cb740cc3d77c84`)

### 2.2 — Scripts

- **Upstream novelty metric:** `data/lineageflow_upstream/evaluation/novelty_mmseqs2.py`
  (per-seq fident, coverage-filtered hits, novelty rate at multiple
  identity thresholds). Used for the summary.json + per_seq.jsonl
  outputs that downstream paper §15.59 + §R.50 reference.
- **Plain mmseqs easy-search:** for the m8 (raw e-value) outputs used to
  compute the "novelty = e>1e-3 OR no-hit" count and avg min e-value.

### 2.3 — Novelty definition

A sequence is "novel" if either:
1. It has **no hit** in the target DB at all (no alignment produced), OR
2. Its **best hit has e-value > 1e-3** (the sequence has no close homolog)

Both criteria are captured by the rule: `(no hit in m8) OR (min e-value
across hits > 1e-3)`.

---

## 3. Sanity check N=5

### 3.1 — Setup

```
mkdir -p /tmp/w163/novelty_sanity/{baseline,framework}/
PY=/home/hugo/.conda/envs/omegafold_py310/bin/python
$PY -c "
from Bio import SeqIO
records = list(SeqIO.parse('/tmp/w158/lineageflow_real_fastas/baseline.fasta', 'fasta'))[:5]
SeqIO.write(records, '/tmp/w163/novelty_sanity/baseline_n5.fasta', 'fasta')
records = list(SeqIO.parse('/tmp/w158/lineageflow_real_fastas/framework.fasta', 'fasta'))[:5]
SeqIO.write(records, '/tmp/w163/novelty_sanity/framework_n5.fasta', 'fasta')
"
```

Sanity FASTAs contain 5 sequences each (sizes 41–150 aa).

### 3.2 — Run (upstream novelty_mmseqs2.py)

```
$PY data/lineageflow_upstream/evaluation/novelty_mmseqs2.py \
  --mmseqs $MMSEQS \
  --fasta /tmp/w163/novelty_sanity/baseline_n5.fasta \
  --pfam-fastas-dir data/lineageflow_upstream/dataset/pfam_fastas_clean \
  --target-db data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB \
  --target-fasta data/pfam_holdout/random_clan.fasta \
  --threads 4 --max-hits 10 \
  --min-qcov 0.5 --min-tcov 0.3 \
  --no-within-gen-cluster \
  --tmpdir /tmp/w163/novelty_sanity/baseline_tmp \
  --out /tmp/w163/novelty_sanity/baseline.json \
  --out-per-seq /tmp/w163/novelty_sanity/baseline_per_seq.jsonl \
  --no-verbose
```

### 3.3 — Sanity outputs

```
baseline:  n_total=5 hits_kept=0 nohit_all=5 novelty_all={'0.95':1.0,'0.8':1.0,'0.5':1.0}
framework: n_total=5 hits_kept=0 nohit_all=5 novelty_all={'0.95':1.0,'0.8':1.0,'0.5':1.0}
```

**Sanity PASS.** Both arms produced valid JSON summaries with the upstream
script's standard schema (n_total / hits_kept / nohit_all / novelty_all).
The strict novelty count is saturated at 1.0 (5/5 novel) at N=5, which
matches the N=1000 trend — the holdout target DB is too divergent from
queries to produce hits at min_qcov=0.5 / min_tcov=0.3. The pipeline
itself runs cleanly (no errors, valid output schema, files written).

### 3.4 — Sanity sha256

```
ab90c7b0922078f6ac9bcdd11efd6a69a20aaa367154d715d0601c692f53048a  baseline.json
1db90b3681d76d2219abed0ae40a1ffdb428f1f148c510442f62d50f37bcfaca  framework.json
```

---

## 4. Full N=1000 sweep

### 4.1 — Launch (background, parallel arms)

```
mkdir -p /tmp/w163/novelty_n1000/{baseline,framework}/

nohup $PY data/lineageflow_upstream/evaluation/novelty_mmseqs2.py \
  --mmseqs $MMSEQS \
  --fasta /tmp/w158/lineageflow_real_fastas/baseline.fasta \
  --pfam-fastas-dir data/lineageflow_upstream/dataset/pfam_fastas_clean \
  --target-db data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB \
  --target-fasta data/pfam_holdout/random_clan.fasta \
  --threads 8 --max-hits 10 \
  --min-qcov 0.5 --min-tcov 0.3 \
  --no-within-gen-cluster \
  --tmpdir /tmp/w163/novelty_n1000/baseline/tmp \
  --out /tmp/w163/novelty_n1000/baseline/summary.json \
  --out-per-seq /tmp/w163/novelty_n1000/baseline/per_seq.jsonl \
  --keep-tmp --no-verbose \
  > /tmp/w163/novelty_n1000/baseline/sweep.log 2>&1 &
echo "BASELINE_PID: $!"

nohup $PY data/lineageflow_upstream/evaluation/novelty_mmseqs2.py \
  --mmseqs $MMSEQS \
  --fasta /tmp/w158/lineageflow_real_fastas/framework.fasta \
  --pfam-fastas-dir data/lineageflow_upstream/dataset/pfam_fastas_clean \
  --target-db data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB \
  --target-fasta data/pfam_holdout/random_clan.fasta \
  --threads 8 --max-hits 10 \
  --min-qcov 0.5 --min-tcov 0.3 \
  --no-within-gen-cluster \
  --tmpdir /tmp/w163/novelty_n1000/framework/tmp \
  --out /tmp/w163/novelty_n1000/framework/summary.json \
  --out-per-seq /tmp/w163/novelty_n1000/framework/per_seq.jsonl \
  --keep-tmp --no-verbose \
  > /tmp/w163/novelty_n1000/framework/sweep.log 2>&1 &
echo "FRAMEWORK_PID: $!"
```

Both sweeps completed in <1 minute (1000 queries × 8 threads against
the 200-sequence holdout DB; total work is small).

### 4.2 — Secondary m8 capture (permissive threshold for signal)

The upstream script's convertalis step applies `--min-qcov 0.5 --min-tcov 0.3`
filter and produces a `hits.tsv` that is empty here (all 5-sequence sanity
and 1000-sequence full sweeps return 0 hits passing the coverage filter).
To capture the raw e-value signal (even for low-coverage matches), we ran
a parallel `mmseqs easy-search` with permissive `-e 10 --max-seqs 50`:

```
$MMSEQS easy-search /tmp/w158/lineageflow_real_fastas/baseline.fasta \
  $TARGET_DB /tmp/w163/novelty_n1000/baseline/easy_search.m8 \
  /tmp/w163/novelty_n1000/baseline/easy_tmp/ \
  --threads 8 -e 10 --max-seqs 50 \
  --format-output "query,target,fident,alnlen,qlen,tlen,evalue,bits"
```

(equivalent command for `framework.fasta`).

---

## 5. Results

### 5.1 — Summary (upstream novelty_mmseqs2.py)

| Arm | n_total | hits_kept | nohit_all | novelty_all (0.95/0.8/0.5) | duplicate_all_rate |
|-----|---------|-----------|-----------|----------------------------|---------------------|
| baseline | 1000 | 0 | 1000 | 1.0 / 1.0 / 1.0 | 0.0 |
| framework | 1000 | 0 | 1000 | 1.0 / 1.0 / 1.0 | 0.0 |

Both arms report **100% novel** at all three identity thresholds
(0.95 / 0.80 / 0.50). This is a **saturated metric**: every query in both
arms lacks any close homolog in the holdout DB at min_qcov=0.5/min_tcov=0.3.

### 5.2 — Permissive raw hits (m8, `-e 10`)

| Arm | raw m8 lines | queries with ≥1 hit | avg min e (hits-only) |
|-----|--------------|---------------------|------------------------|
| baseline | 82 | 77 | 2.711 |
| framework | 25 | 25 | 4.959 |

When the e-value threshold is loosened to 10 (capturing even remote
similarities), the holdout DB produces some signal: baseline has **3.3× more**
permissive hits than framework (82 vs 25), and the avg min e-value among
queries that DO have hits is **~1.83× higher** (further from homolog) for
framework. This is a directional novelty signal: framework queries are
further from any holdout DB homolog than baseline queries.

### 5.3 — Novelty count (e>1e-3 OR no-hit, strict)

| Arm | n_total | n_novel | fraction |
|-----|---------|---------|----------|
| baseline | 1000 | 1000 | 1.000 |
| framework | 1000 | 1000 | 1.000 |
| **delta** | | **0** | **+0.00%** |

Delta novel count = **0** (saturated at 1.000 for both arms). The strict
novelty count does not distinguish baseline from framework at this target
DB.

### 5.4 — Why saturated (target DB analysis)

The holdout target DB has 200 sequences from `random_clan.fasta`
(one Pfam clan, mean length 400 aa, min 291, max 951). The generated
queries belong to families PF00005 (ABC transporter), PF00072 (response
regulator), PF00183 (Hsp70), PF02517 (CP12) — different Pfam clans.
The holdout clan is too evolutionarily distant for sensitive matches to
be expected at the upstream script's coverage thresholds.

**Recommendation for stronger signal (not in scope of this Wave):**
adopt the full per-family training DB (which is **not vendored upstream**
per Wave 163 P2 §3) or a Pfam-A subset (~20 000+ families) — both
would yield non-saturated novelty counts that distinguish baseline from
framework. The current PARTIAL outcome is **expected and informative**
given the holdout-surrogate target DB.

---

## 6. Outputs + sha256

### 6.1 — Easy-search m8 (raw e-value, permissive)

```
584915814a563bb33b84d8c23ff7c03d9ee62023ffd4b746f413043aacf6288e  /tmp/w163/novelty_n1000/baseline/easy_search.m8  (5850 bytes)
79b29fd5f70a69fe9234493b7a02c6b501a92f7e04a960213f0943e60bc5b4eb  /tmp/w163/novelty_n1000/framework/easy_search.m8  (1773 bytes)
```

### 6.2 — Upstream summary.json + per_seq.jsonl

```
5636078c9857f1aa830ad9fc18441bf83e92a0cb41b5a36a136f370e8a798709  baseline/summary.json   (1039 bytes)
9b26432a85a566fd93aa94ede4d93d40523dff136153779afbb543f2776d5ec8  framework/summary.json  (1040 bytes)
e72c7b463972c62bebec8a5db1fa13a40d53198da9e541d884a4c28c6eb0592b  baseline/per_seq.jsonl  (138 204 bytes)
f05faae1a7762a8401c1762d85c035dbea55b05023879779b05453324da54491  framework/per_seq.jsonl (139 210 bytes)
```

### 6.3 — Sweep logs + metrics

```
39f50a820e9d54a10f42e35978f140483b33e4eeb95169adb6be381750098774  baseline/sweep.log
155d3c0568fcbf4d3b4dfc0aff053900b013f786fbcd3aedd1a1f7d6484d31d4  framework/sweep.log
bb7edf299a33938c29b349bccc979670a4bb341ed5830db464a15b2ad3fdc694  metrics.json  (consolidated metric summary)
```

### 6.4 — verification_outputs/ copied artifacts

```
verification_outputs/lineageflow_novelty_mmseqs2_w163_q3_2026/
  metrics.json
  baseline/easy_search.m8, summary.json, per_seq.jsonl, sweep.log
  framework/easy_search.m8, summary.json, per_seq.jsonl, sweep.log
```

---

## 7. Gate verification

### 7.1 — d4 pytest

```
$ pytest tests/ -k "d4" -q --tb=line | tail -3
33 passed, 31 skipped, 5020 deselected, 9 warnings in 2.55s
```

**PASS.** 33 d4 tests pass; 31 skipped due to missing `torch` (pre-existing
skip, unrelated to this wave). 5020 deselected (non-d4 tests).

### 7.2 — ruff

```
$ ruff check adaptive_reflow/ tests/ scripts/ tools/
All checks passed!
```

**PASS.** 0 errors, 0 warnings. No new ruff violations introduced.

### 7.3 — claims consistency

```
$ python tools/check_claims_consistency.py | tail -3
**No drift detected.**
```

**PASS.** Claims registry reports 47 active claims with no drift.
No new framework_improves claims added by this wave (novelty count
saturated at 1.0 — no claim can be added without non-saturated signal).

---

## 8. Status

**novelty_mmseqs2 status: PARTIAL**

- Pipeline runs end-to-end (sanity N=5 PASS, full N=1000 runs, valid JSON + m8 outputs)
- Strict novelty count (e>1e-3 OR no-hit) saturated at 100% for both arms
  → delta = 0; **no framework_improves claim supportable from this metric alone**
- Secondary signal (avg min e-value among hits-only queries): framework
  4.959 vs baseline 2.711 → +83% farther from any homolog → directional
  novelty improvement but small-N (77 vs 25 of 1000)
- Gates preserved (d4 PASS, ruff 0, claims no-drift)
- All outputs sha256-pinned and copied to verification_outputs/

**Decision:** Do not add a "framework improves novelty" claim to the
paper. The strict novelty count is uninformative due to the holdout DB
size/diversity. The avg min e-value is a directional signal but lacks
the N to support a Bonferroni-significant claim. PARTIAL outcome is
documented in this audit for §15.59 + §R.50 disclosures.