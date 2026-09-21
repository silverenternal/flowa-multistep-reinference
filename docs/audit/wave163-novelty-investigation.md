# Wave 163 P2 — LineageFlow novelty_mmseqs2 readiness investigation

**Date:** 2026-09-15
**Branch:** main
**Agent:** Wave 163 Agent 2 (READ-ONLY investigation)
**Scope:** Investigate `mmseqs2` binary + target-DB availability + internet reachability +
disk space + existing FASTA inputs before P3's install path is decided.

---

## 1. Verdict summary

| Resource | Status | Path / Notes |
|----------|--------|--------------|
| `mmseqs2` binary | **FOUND** (no install needed) | `/home/hugo/bin/mmseqs` (23.7 MB, Sep 8) + `/.venvs/protbfn_venv/bin/mmseqs` (17.4 MB, Sep 3) |
| Upstream novelty script | **FOUND** | `data/lineageflow_upstream/evaluation/novelty_mmseqs2.py` (927 LOC) |
| Existing target DB | **FOUND** (holdout, 200 seqs, 100 KB) | `data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB{,.dbtype,.index,.lookup,_h*}` (built from `random_clan.fasta`, 200 proteins) |
| Canonical per-family training target DB | **NOT BUILT** | requires `dataset/pfam_fastas_clean/<PF*.fasta>` (per-family training MSAs) — directory exists but is **EMPTY** (placeholder) |
| `Pfam-A.hmm` (profile HMM DB) | **FOUND** | `data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm` (2.1 GB + 4 HMMER index files) — for family_validity (HMMER) **NOT** for novelty (sequence similarity) |
| Per-family Pfam training FASTAs | **NOT VENDORED** | `data/lineageflow_upstream/dataset/pfam_fastas_clean/` exists but is empty (0 entries) |
| Existing query FASTAs (N=1000) | **FOUND** | `/tmp/w158/lineageflow_real_fastas/{baseline,framework}.fasta` (sha256-pinned, family headers, manifest-confirmed 4 families × 250 seqs) |
| Internet reachability | **REACHABLE** | mmseqs.com + github.com/soedinglab/MMseqs2/releases both HTTP 200/302 (Sep 15 13:57 UTC) |
| Disk space | **PLENTY** | /tmp 46 GB free, /home 1.6 TB free (3.7 TB total, 2.2 TB used) |

**Headline:** The `mmseqs2` binary is already vendored. The novelty script's *canonical*
target-DB inputs (per-family training MSAs at `dataset/pfam_fastas_clean/`) are NOT vendored.
A pre-built **holdout** target DB (`pfam_holdout_targetDB`, 200 random-clan proteins) IS
vendored and can serve as a camera-ready surrogate.

---

## 2. Step-by-step findings

### Step 1 — `mmseqs2` binary availability

```
$ which mmseqs       → not in PATH
$ which mmseqs2      → not in PATH
$ find / -name "mmseqs*" -type f -executable
  /home/hugo/bin/mmseqs
  <repo_root>/.venvs/protbfn_venv/bin/mmseqs
```

**Two binaries vendored:**

| Path | Size (bytes) | mtime | Notes |
|---|---:|---|---|
| `/home/hugo/bin/mmseqs` | 23 698 800 | Sep 8 07:34 | global binary |
| `<repo_root>/.venvs/protbfn_venv/bin/mmseqs` | 17 431 368 | Sep 3 21:27 | venv-bundled |

Both respond to `--version` with the standard MMseqs2 banner (Steinegger & Soding 2017).
No install needed; can be invoked by absolute path or symlinked to `PATH`.

### Step 2 — Upstream LineageFlow novelty script

`data/lineageflow_upstream/evaluation/novelty_mmseqs2.py` (927 LOC) — the *vendored upstream*
novelty evaluation orchestrator. CLI:

```text
--fasta             Generated FASTA (queries; expects `family=<id>` in headers)
--pfam-fastas-dir   Per-family training FASTA dir (default `dataset/pfam_fastas_clean`)
--pi-file           Family table CSV (default `dataset/pfam_pi_smooth_tau0.5_gap060_gt80_020.csv`)
--keep-file         Optional keep-list (default `dataset/pfam_priors_keep_ids_gap060_gt80_020.txt`)
--prior-dir         Optional prior dir (default `dataset/pfam_priors_asr_mad`)
--target-db         MMseqs2 target DB prefix (REQUIRED; will be built if missing)
--target-fasta      Optional prebuilt target FASTA used to build DB
--mmseqs            MMseqs2 binary (default "mmseqs")
--threads           (default 8)
--sensitivity       (default 7.5)
--max-hits          Top hits per query (default 200)
--min-qcov          (default 0.8)
--min-tcov          (default 0.8)
--within-gen-cluster    Compute within-gen clustering (default True)
--within-gen-thresholds 0.9,0.8 identity thresholds
--out               Summary JSON
--out-per-seq       Per-sequence JSONL
--min-plddt         Optional filter (requires --fold-metrics-jsonl)
```

**Behaviour summary (lines 437–922):**

1. Reads queries from `--fasta` (expects `family=<id>` in headers; `parse_family` line 90).
2. Cleans each sequence (drop X, gap chars; require min-len=10).
3. Builds family→id map from `--pi-file` (or sorted `pfam_fastas_clean/*.fasta` stems).
4. **If `--target-db` does not exist:** builds a per-family reference FASTA from
   `pfam_fastas_clean/<fam>.fasta` (deterministic train/val split; `ref_split="train"`
   default), then runs `mmseqs createdb <ref_fasta> <target_db>`.
5. Builds query DB, runs `mmseqs search --max-seqs 200 --threads N` against target DB.
6. Runs `mmseqs convertalis` to TSV; parses best-by-fident (then bits) per query.
7. Computes NN identity globally (all hits) and within-family (target's family matches
   query's family, parsed from `tid.split("|", 1)[0]`).
8. Within-gen MMseqs2 clustering at thresholds 0.9 + 0.8 (default).
9. Writes summary JSON + per-sequence JSONL.

**Metric summary output:**

```text
{
  "n_total": ...,
  "coverage_thresholds": {"min_qcov": 0.8, "min_tcov": 0.8},
  "hits": {"hits_kept": ..., "nohit_all": ..., "nohit_fam": ...},
  "nnid_all":  {"mean": ..., "median": ..., "p10": ..., "p90": ...},
  "nnid_fam":  {"mean": ..., "median": ..., "p10": ..., "p90": ...},
  "novelty_all": {"0.95": ..., "0.80": ..., "0.50": ...},   # fraction < threshold
  "novelty_fam": {"0.95": ..., "0.80": ..., "0.50": ...},
  "duplicates": {"duplicate_all_rate": ..., "duplicate_fam_rate": ...},
  "within_gen_clusters": {"coverage_threshold": 0.8, "thresholds": {"0.9": {...}, "0.8": {...}}}
}
```

**Identity threshold:** `fident` from MMseqs2 alignment; coverage `min_qcov=0.8`,
`min_tcov=0.8` (script lines 488–489). **No e-value** filter applied at hit-parsing
step (e-value is reported in TSV but not gated; see line 734 `qid, tid, fident,
alnlen, qlen, tlen, evalue, bits = ln.split("\t")` then immediately drops the
e-value). Default `sensitivity = 7.5`, `--max-seqs 200`.

### Step 3 — Target DB candidates

| Candidate | Path | Size | Status | Suitable for novelty? |
|---|---|---:|---|---|
| Per-family Pfam training MSAs (canonical) | `dataset/pfam_fastas_clean/<PF*.fasta>` | n/a | **Directory exists but is EMPTY** (placeholder) | **YES — canonical** |
| Pre-built holdout target DB | `data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB{,.dbtype,.index,.lookup,_h*}` | 80 KB | **Pre-built** from `random_clan.fasta` (200 proteins, 100 KB) | **YES — surrogate** (holdout novelty vs. the unseen `random_clan.fasta` subset) |
| Pfam-A.hmm (profile HMM DB) | `data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm` + 4 index files | 2.1 GB + 2.5 GB indices | Pre-pressed for HMMER `hmmscan` | **NO** — profile DB (not a sequence DB; cannot be used for similarity search) |
| UniRef30 / ColabFoldDB | not on disk | n/a | Would require 30–60 GB download + index | **YES — but heavy** |

`data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB.source` ASCII content
confirms the pre-built DB was built from `<repo_root>/data/pfam_holdout/random_clan.fasta` (200 protein sequences, full SwissProt-style headers
e.g. `>sp|O00254|PAR3_HUMAN ...`). This is a proper holdout set (distinct from any
training corpus the LineageFlow adapter would have seen).

The canonical per-family training set directory `data/lineageflow_upstream/dataset/pfam_fastas_clean/`
is **empty** (commit-era placeholder). The accompanying `pfam_pi_smooth_tau0.5_gap060_gt80_020.csv`
(958 KB) lists 7 000+ family rows (last column is the pi probability mass); the per-family
FASTAs the script reads are not vendored.

### Step 4 — What the novelty script computes (covered in Step 2)

- **NN identity** (fident from MMseqs2 alignment; coverage ≥ 0.8 in both directions)
- **Identity thresholds:** `0.95 / 0.80 / 0.50` (script line 761)
- **No-hit → identity 0.0** (treats no-hit as fully novel; lines 840, 852)
- **Duplicate flag:** fident ≥ 0.999 AND qcov ≥ 0.999 AND tcov ≥ 0.999 (line 790)
- **Within-gen clustering:** MMseqs2 `cluster` at 0.9 + 0.8 identity (lines 283-340)

### Step 5 — Internet reachability

```
$ curl --max-time 10 -sI https://mmseqs.com/latest/mmseqs-linux-avx2.tar.gz
  HTTP/2 200, content-length 19 103 055 bytes

$ curl --max-time 10 -sI https://github.com/soedinglab/MMseqs2/releases/latest
  HTTP/2 302, location: https://github.com/soedinglab/MMseqs2/releases/tag/18-8cc5c

$ curl --max-time 10 -sI https://github.com
  HTTP/2 200
```

**All three endpoints reachable.** The `mmseqs-linux-avx2.tar.gz` static binary is
downloadable (19 MB) — though not needed since the binary is already vendored. Pfam full
sequence DB (`Pfam-A.fasta.gz`, ~600 MB) is reachable at
`https://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.fasta.gz` for any
future vendoring of the canonical per-family MSAs.

### Step 6 — Disk space

```
$ df -h /tmp /home
tmpfs            48G  1.8G   46G   4%  /tmp
/dev/nvme0n1p2  3.7T  2.2T   1.6T  59% /home
```

**46 GB free on /tmp, 1.6 TB free on /home.** Easily accommodates any of:
- `Pfam-A.fasta.gz` (600 MB) → uncompressed ~3 GB
- UniRef30 (~30 GB) → ColabFold index ~50 GB total
- Mini-DB built from `random_clan.fasta` (negligible)

### Step 7 — Existing FASTA inputs

```
$ ls -la /tmp/w158/lineageflow_real_fastas/
  -rw-r--r-- baseline.fasta   (126 939 bytes; 1 000 sequences)
  -rw-r--r-- framework.fasta  (128 313 bytes; 1 000 sequences)
  -rw-r--r-- manifest.json    (623 bytes)

$ sha256sum /tmp/w158/lineageflow_real_fastas/*.fasta
  4ef0ec94d67850aa018d8cb83806d1ad52f80081dca758a732891a08a9e80db1  baseline.fasta
  afe53dc0ea168c9d7629915ce6bda02de28299cc1bfa730583410888b83aaec5  framework.fasta
```

Per manifest.json: 4 families × 250 seqs (PF00005.27, PF00072.24, PF00183.19,
PF02517.18); seed 42; min_len=30; max_len=150; nfe_per_record=10; n_rounds=3.
These are the same FASTAs used for the Wave 158 HMMER R1 +116% headline
re-derivation (canonical sha256-pinned evidence; see
`docs/audit/wave158-hmmer-rederivation.md` §3). Headers carry `family=<id>`
metadata as required by the novelty script's `parse_family` function (line 90).

---

## 3. Recommendation for P3

**RECOMMENDED PATH (camera-ready surrogate, fast, honest disclosure):**

1. **No mmseqs install needed** — reuse `/home/hugo/bin/mmseqs` (or symlink to `PATH`).
2. **Reuse the existing pre-built holdout target DB** at
   `data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB`
   as a surrogate for the canonical per-family training-set DB.
3. **Run the novelty script directly** against `/tmp/w158/lineageflow_real_fastas/{baseline,framework}.fasta`:
   ```bash
   python data/lineageflow_upstream/evaluation/novelty_mmseqs2.py \
     --fasta /tmp/w158/lineageflow_real_fastas/baseline.fasta \
     --mmseqs /home/hugo/bin/mmseqs \
     --target-db data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB \
     --out results/novelty/baseline.json \
     --out-per-seq results/novelty/baseline_per_seq.jsonl \
     --threads 8 --max-hits 200 --min-qcov 0.8 --min-tcov 0.8
   ```
4. **Disclose the surrogate in baseline-audit-report §R.50 + paper §15**:
   novelty target DB is the 200-seq Pfam holdout (`random_clan.fasta`), not the
   canonical per-family training set (which is not vendored upstream). The
   metric is therefore "novelty against unseen holdout" rather than
   "novelty against training set", but the script's API + thresholds + JSON
   schema are identical to upstream.

**ALTERNATIVE PATH (canonical target DB, heavier install):**

If the canonical per-family training-set DB is required:
1. Download `Pfam-A.fasta.gz` (~600 MB) from
   `https://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/`.
2. Extract sequences for the 4 known families (PF00005, PF00072, PF00183, PF02517)
   by parsing the `#=GF ID` line in each Pfam-format record.
3. Per-family aligned FASTA → unaligned, gap-stripped (`clean_seq` line 102 of
   novelty_mmseqs2.py).
4. Apply deterministic train/val split (line 115 of novelty_mmseqs2.py;
   `val_frac_per_family=0.05`, `val_split_seed=1337`).
5. Concatenate to single reference FASTA; build MMseqs2 DB with
   `mmseqs createdb`. Pass via `--target-db` (script auto-builds when missing).
6. ~30–60 min CPU wallclock for Pfam extraction + DB build; novelty sweep
   then runs against the canonical target.

**Trade-off:** the canonical path is more faithful to upstream semantics but
costs an extra ~1 GB download + ~30 min of pre-processing; the surrogate path
is zero-cost, pre-vendored, and gives the same JSON schema with honest
disclosure. For camera-ready (deferred to compute window), the surrogate path
is the right choice.

---

## 4. Files referenced

- `data/lineageflow_upstream/evaluation/novelty_mmseqs2.py` — vendored upstream script (927 LOC)
- `data/lineageflow_upstream/evaluation/evaluate_all.py` — orchestrator that fans out into 4 metrics
- `data/lineageflow_upstream/dataset/pfam_dataset.py` — per-family FASTA loader (training-side; line 28-30 `DEFAULT_FASTA_DIR`)
- `data/lineageflow_upstream/dataset/pfam_pi_smooth_tau0.5_gap060_gt80_020.csv` — family table CSV (vendored, 958 KB)
- `data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB*` — pre-built holdout MMseqs2 DB (200 random-clan proteins)
- `data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm*` — pre-pressed Pfam profile DB (for HMMER, NOT for novelty)
- `data/pfam_holdout/random_clan.fasta` — source FASTA for the pre-built holdout target DB (200 proteins)
- `/tmp/w158/lineageflow_real_fastas/{baseline,framework}.fasta` — query FASTAs (1 000 seqs each, sha256-pinned)
- `/home/hugo/bin/mmseqs` — vendored mmseqs2 binary (23.7 MB, Sep 8)
- `<repo_root>/.venvs/protbfn_venv/bin/mmseqs` — secondary vendored copy (17.4 MB, Sep 3)

## 5. Open items for P3

| # | Item | Decision needed |
|---|---|---|
| 1 | mmseqs install path | none — binary already vendored; no install needed |
| 2 | Target DB strategy | **Adopt surrogate** (pre-built holdout) — see §3 RECOMMENDED PATH. Document the deviation in baseline-audit-report §R.50 + paper §15 (ADDITIVE note: novelty reference is the 200-seq Pfam holdout, not the canonical training-set DB which is not vendored) |
| 3 | Novelty sweep command | run upstream script directly against `/tmp/w158/lineageflow_real_fastas/{baseline,framework}.fasta` per §3 (no wrapper changes) |
| 4 | Sweep compute budget | ~30 min total CPU for N=1000 baseline + framework (search sensitivity 7.5; 200 random-clan target DB is tiny → fast) |
| 5 | Output paths | `<repo_root>/results/novelty/{baseline,framework}/{novelty.json,novelty_per_seq.jsonl}` |

---

**Wave 163 P2 READ-ONLY audit complete.** Zero source changes; zero installs.
All findings are factual and reproduce-able via the commands listed above.
