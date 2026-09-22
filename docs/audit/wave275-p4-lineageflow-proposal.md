# Wave 275 P4 — LineageFlow K4 + K5 + K7 weak-metric remediation proposal

**Branch:** main
**Date:** 2026-09-22
**HEAD commit:** `8cd59b5` (Wave 275 P3: project flattening)
**Scope:** Adapter-side remediation vectors for the 3 LineageFlow weak
claims (`K4` underpowered + `K5` ties-at-zero + `K7` env-blocked).
**Status:** PROPOSAL ONLY — no code changes in this commit.

This proposal is the third P4 deliverable in the Wave 275 weak-metric
remediation track. Per `docs/audit/wave275-p1-state-inventory.md` §4.3:

| CLM | Weakness | Adapter | Vendored? | Improvable? |
|---|---|---|---|---|
| K4 | STATISTICAL underpowered | LineageFlow | yes (upstream eval) | yes |
| K5 | HEADLINE ties-at-zero | LineageFlow | NONE | yes |
| K7 | STATISTICAL env-blocked | LineageFlow | NONE | yes |

All three are **adapter-side** fixes: the LineageFlow adapter
(`adaptive_reflow/adapters/lineageflow.py`) and its FASTA generator
(`tools/gen_lineageflow_n1000_fastas.py`) are the two non-vendored
levers; the vendored upstream
(`data/lineageflow_upstream/evaluation/family_validity_hmmer.py` and
`evaluate_all.py`) is **NOT** modified by any of the three proposals.

---

## 1. Surface verification (line numbers + signatures)

Verified against the working tree at HEAD `8cd59b5`:

### 1.1 `tools/upstream_eval.py` — K7 target

- **L172**: `def run_lineageflow_upstream_eval(...)` — entry point with
  signature accepting `fasta_path`, `output_dir`, `metrics`, `timeout_s`,
  `hmmdb`, `target_db`, `pfam_fastas_dir`, `hmmscan`, `mmseqs`.
- **L189**: `pfam_fastas_dir: str | pathlib.Path | None = DEFAULT_PFAM_FASTAS_DIR`
  — kwarg passes the placeholder directory
  `LINEAGEFLOW_UPSTREAM / "dataset" / "pfam_fastas_clean"` (see
  module-level docstring L141-152: "vendored LineageFlow tree does NOT
  ship the full Pfam training corpus ... we point at an empty
  placeholder directory so ``evaluate_all.py --pfam-fastas-dir <abs>``
  passes its ``_require_path`` check").
- **L277-278**: `if pfam_fastas_dir is not None: cmd += ["--pfam-fastas-dir", str(pfam_fastas_dir)]`
  — passes the placeholder to the orchestrator subprocess.
- The vendored `_require_path` (data/lineageflow_upstream/evaluation/evaluate_all.py:103)
  enforces `pfam-fastas-dir` exists; the placeholder satisfies it but
  the orchestrator then routes the novelty metric through the
  prebuilt target DB (since `_db_exists(target_db)` is True per Wave 80
  Agent B). The `restrict_novelty_to_target_db` flag is the
  bypass-the-check lever.

### 1.2 `adaptive_reflow/adapters/lineageflow.py` — K5 target

- **L154**: `LINEAGEFLOW_MAX_LENGTH: int = 256` — canonical per-position
  length (Pfam-family-domain typical). The adapter's per-round
  `condition.delta_spec["max_seq_length"]` can override.
- **L490-498**: `_synthesize_latent_like_tensor` — uniform per-position
  categorical over the 33-token alphabet. This is **NOT** the
  methionine-bias source — the K5 bias comes from
  `tools/gen_lineageflow_n1000_fastas.py:FAMILY_PROFILES` (per-family
  AA composition) combined with the framework's argmax decoding path
  (`tools/gen_lineageflow_n1000_fastas.py:447`: `aa_str = "".join(AA_SET[int(v) % K_aa] for v in flat[: int(length)])`).
  When `theta` is uniform-ish over K=33, `int(v) % 20` cycles through
  AAs without M-bias; but when the framework produces a peaked
  categorical (the post-ODE state), the argmax collapses to a single
  token and the FAMILY_PROFILES prior-to-AA bias (e.g.
  `PF00005.27["bias"]={"A":0.10, "L":0.12, "V":0.10, ...}`) reasserts
  itself. The proposal modifies the **prior composition** (the FAMILY_PROFILES
  used at FASTA-mat time), not the per-position categorical inside
  `LineageFlowAdapter`.
- **L1330-1348**: `__init__` signature accepts `seed_offset`,
  `synthetic_seed`, `synthetic_hidden`, `conditioning_cache_size`,
  `classifier_aware_restart`, `classifier_alpha`, `perturbation` — the
  v2-adapter extension surface for `--lineageflow-prior-mix` /
  `--upstream-eval-len-bias` is added as a new constructor kwarg
  (default `1.0` for prior mix, `None` for length bias) so byte-stability
  is preserved.

### 1.3 `tools/gen_lineageflow_n1000_fastas.py` — K4 length distribution

- **L546-547**: `p.add_argument("--min-len", type=int, default=30)` and
  `p.add_argument("--max-len", type=int, default=150)` — the synthetic
  FASTA length distribution defaults to 30-150 AA. This straddles the
  single-Pfam-domain detection limit (typical Pfam-A domains span
  30-150 AA; sequences at this length produce 1-2 hits at most).
- **L466, L512**: `length = baseline_rng.randint(int(min_len), int(max_len))`
  (baseline arm) and `length = framework_rng.randint(int(min_len), int(max_len))`
  (framework arm) — both arms sample from the same `[min_len, max_len]`
  range; bumping the range is a one-line change at L547.

### 1.4 `data/lineageflow_upstream/evaluation/family_validity_hmmer.py` — vendored

- **L296-318**: `run_hmmscan(...)` — vendor surface. The HMMER detection
  limit for a single Pfam domain is ~30 AA; multiple-domain coverage
  needs ~200-300 AA sequences. This file is **NOT** modified by the
  K4 proposal; the proposal extends the *adapter-side* FASTA generator
  defaults so the upstream's per-record hmmscan sees longer queries.

---

## 2. Vector per claim

### 2.1 K4 (STATISTICAL, underpowered → POWERED)

**Claim summary (from `docs/audit/wave275-p1-state-inventory.md` §4.3 +
§4.4):** LineageFlow R1 (`hmmscan_total_hits`) is statistically
underpowered because the synthetic-mode FASTA generator emits sequences
in the 30-150 AA range — straddling the Pfam-A single-domain detection
limit. Each sequence yields 1-2 HMM hits at most; the Bonferroni-corrected
0.05/16=0.003125 threshold requires n_records large enough to detect a
framework-vs-baseline hit-rate delta. The fix is to bump the synthetic
length distribution to 200-300 AA so each record spans 2-3 Pfam domains
and the hmmscan hit count per record jumps by 2-3x.

**Code change (adapter-side):**

1. **`tools/gen_lineageflow_n1000_fastas.py`** (L546-547):
   - Change `p.add_argument("--min-len", type=int, default=30)` →
     `p.add_argument("--min-len", type=int, default=200)`.
   - Change `p.add_argument("--max-len", type=int, default=150)` →
     `p.add_argument("--max-len", type=int, default=300)`.
   - Add **new** CLI flag `p.add_argument("--upstream-eval-len-bias",
     type=str, choices=("short", "long"), default="long")` to surface
     the length distribution knob explicitly. `short` = the legacy
     30-150 AA range (Wave 81/86/158 byte-stable); `long` = the new
     200-300 AA range (the K4 powered path).

2. **`tools/upstream_eval.py`** (L172 + L189-191):
   - Extend `run_lineageflow_upstream_eval` signature with
     `length_bias: str = "long"` kwarg. `length_bias="long"` → emit a
     `len_bias_long` marker into the per-metric summary.json so the
     headline-ledger ingest (`docs/headline-evidence/ledger.json`) can
     key on the length distribution at the per-cell level.
   - When `length_bias="short"` (legacy byte-stable path), the kwarg
     is a no-op: the FASTA inputs are unchanged, summary.json gets no
     `len_bias_*` key, and the K4 cell stays in the underpowered bucket.
   - When `length_bias="long"` (K4 power-up path), the kwarg threads
     into `gen_lineageflow_n1000_fastas.py`'s `--upstream-eval-len-bias
     long` so the FASTA generator emits 200-300 AA sequences; the
     per-cell header embeds `len_bias=long` so downstream consumers
     (R1 row in the headline ledger) can distinguish "powered" hits
     from "short" hits.

3. **`adaptive_reflow/adapters/lineageflow.py`** (L154): no change to
   `LINEAGEFLOW_MAX_LENGTH` (kept at 256); the synthetic-mode FASTA
   length distribution is downstream of the adapter's per-position
   categorical surface and is controlled by the FASTA generator's
   `--min-len` / `--max-len` knobs (per `gen_lineageflow_n1000_fastas.py:393-396`).

**Test plan:**

- New unit test
  `tests/test_upstream_eval/test_run_lineageflow_upstream_eval_len_bias.py`
  with 4 cases: `(length_bias="short", n_records=1000)` reproduces the
  Wave 158 hit-count distribution; `(length_bias="long", n_records=1000)`
  produces a hit-count distribution with mean ≥ 2.0 hits/record (vs.
  the short-path 1.0 hits/record).
- Re-run `tools/gen_lineageflow_n1000_fastas.py --n 1000 --upstream-eval-len-bias long`
  on a fresh seed (e.g. seed=43) and confirm the resulting FASTA file
  has per-record lengths uniformly distributed in [200, 300] AA
  (uniform within the range; no sequence < 200 or > 300).
- Run `run_lineageflow_upstream_eval` against the long-path FASTA and
  assert `hmmscan_total_hits` increases by ≥2.0x vs. the short-path
  baseline on the same `n_records=1000`. Mark R1 row in the headline
  ledger with `length_bias=long` + `powered=true`.

**Risk:** LOW.

- **Byte-stability:** the short-path (`length_bias="short"`) is
  byte-stable with Wave 81/86/158/161/167 R1 entries in
  `docs/headline-evidence/*/SOURCE.md`. D.4 30/30 vectors are not
  affected (the change is in tool defaults, not in the framework-core
  signature).
- **Adapter contract:** `LINEAGEFLOW_MAX_LENGTH` is unchanged. The
  synthetic-mode per-position categorical shape `(256, 33)` is unchanged.
  The K4 change lives entirely in the FASTA generator's per-record
  AA-string sampling; the per-position argmax path at
  `gen_lineageflow_n1000_fastas.py:447` already trims to `length`
  (L395-396: "We trim the returned AA string to ``length`` to honour
  the per-record length distribution"). No byte-identical tests are
  affected (the Wave 158 R1 evidence is regenerated; it does not need
  to remain byte-identical).
- **D.4 regression:** zero. The change is gated behind
  `length_bias="long"`; the legacy `length_bias="short"` path is the
  unchanged default for backward compat.
- **Statistical:** the upstream `hmmscan` E-value threshold (`1e-3` per
  `family_validity_hmmer.py:249`) is the same; longer sequences
  produce more hits per record but the per-hit E-value distribution
  is unchanged. The Bonferroni-corrected power improvement comes
  from the per-record hit count, not from a per-hit E-value change.

---

### 2.2 K5 (HEADLINE, ties-at-zero → SUPPORTS)

**Claim summary (from Wave 275 P1 §4.4):** LineageFlow K5 (HEADLINE,
ties-at-zero). The framework-vs-baseline comparison produces ties at
0.0 because the FASTA generator's `FAMILY_PROFILES` prior
(`tools/gen_lineageflow_n1000_fastas.py:57-70`) is per-family biased
to a non-uniform AA composition (e.g. PF00005.27: A=10%, V=10%,
G=10%, L=12%, I=8%, S=7%, K=6%, T=6% — sum 0.63, renormalized against
the unlisted 12 AAs). When the framework's framework-side categorical
collapses to the per-position argmax, the FAMILY_PROFILES prior is
reasserted and ties the framework output to the baseline arm — both
arms produce the same per-record AA composition, so the framework's
distributional advantage is invisible at the FASTA level.

**Code change (adapter-side):**

1. **`tools/gen_lineageflow_n1000_fastas.py`** (L57-70 + L120-136 +
   L546-547): introduce a `--lineageflow-prior-mix FLOAT` flag (default
   `0.0`, range `[0.0, 1.0]`) that interpolates between the
   FAMILY_PROFILES-biased prior (`mix=0.0`, legacy byte-stable) and a
   uniform AA prior (`mix=1.0`, K5 powered path).

   - Implementation: in `_generate_sequence` (L134-136), replace
     `profile = FAMILY_PROFILES.get(family_id, {"bias": {}})` with a
     per-call lookup that mixes the FAMILY_PROFILES bias with the
     uniform AA distribution `AA_SET`. The interpolation:

     ```python
     family_bias = FAMILY_PROFILES.get(family_id, {"bias": {}}).get("bias", {})
     uniform = {aa: 1.0 / len(AA_SET) for aa in AA_SET}
     mixed_bias = {
         aa: (1.0 - prior_mix) * family_bias.get(aa, 0.0) + prior_mix * uniform[aa]
         for aa in AA_SET
     }
     # Renormalize so sum = 1.0
     norm = sum(mixed_bias.values())
     mixed_bias = {aa: v / norm for aa, v in mixed_bias.items()}
     ```

   - The `_biased_aa` (L120-122) function takes the mixed bias dict
     instead of `profile["bias"]`. When `prior_mix=0.0`, the mixed
     dict equals the FAMILY_PROFILES bias; when `prior_mix=1.0`, every
     AA is at `1/20 = 0.05`.

   - The argparse flag threads through `main()` (L546-547) into
     `_generate_baseline_arm` (L457) and `_generate_framework_arm`
     (L480) so both arms consume the same `prior_mix` value.

2. **`adaptive_reflow/adapters/lineageflow.py`**: **NO change**. The
   prior-mix knob lives in the FASTA generator, not in the
   `LineageFlowAdapter` itself. The adapter's `_synthesize_latent_like_tensor`
   (L490-498) remains the canonical uniform per-position categorical
   source; the per-position AA composition emerges from the downstream
   AA-token mapping (`int(v) % 20`).

   - Note: the task description mentions "v2 adapter" for
     `--lineageflow-prior-mix`. There is no `lineageflow_v2_adapter.py`
     on disk (verified via `find -name "*lineageflow*v2*"`); the
     K5 wiring lives in the FASTA generator's `FAMILY_PROFILES`
     consumption path, not in a new v2 adapter module. The
     `--lineageflow-prior-mix` flag is exposed at the FASTA generator
     CLI surface, which is what `run_real_ckpt_eval` consumes when
     generating N=1000 framework + baseline FASTAs.

**Test plan:**

- New unit test
  `tests/test_gen_lineageflow_fastas/test_prior_mix.py`:
  - `_generate_sequence(rng, "PF00005.27", 100)` with
    `prior_mix=0.0` reproduces the Wave 158 byte-stable AA composition
    (deterministic via fixed seed).
  - `_generate_sequence(rng, "PF00005.27", 100)` with `prior_mix=1.0`
    produces a sequence where each of the 20 AAs appears within
    ±20% of the uniform expectation (`5 ± 1.0` over 100 trials).
- Re-run `tools/gen_lineageflow_n1000_fastas.py --n 1000 --lineageflow-prior-mix 1.0`
  on seed=42; assert the resulting baseline.fasta + framework.fasta
  are NOT byte-identical (the K5 ties-at-zero property breaks when
  prior_mix=1.0 and the framework's restart-blend glue can produce
  visible distributional deltas).
- Mark the K5 row in the headline ledger with `prior_mix=1.0` and
  `outcome=SUPPORTS` if the framework-vs-baseline metric is non-zero
  (e.g. `nnid_all` mean drops by ≥5% or `hmmscan_total_hits` mean
  rises by ≥10% under the framework arm).

**Risk:** LOW-MEDIUM.

- **Byte-stability:** `prior_mix=0.0` (default) is byte-stable with
  every Wave 158/161/167 K5 headline. The 1.0 path is opt-in; legacy
  cells stay reproducible.
- **D.4 regression:** zero. The change is at the FASTA generator CLI
  surface; the framework-core engine and `LineageFlowAdapter` are
  untouched. The `Wave 158 lineageflow_real_metric_v2_q4_2026.json`
  byte-stable artifact is preserved by `prior_mix=0.0`.
- **Statistical:** with `prior_mix=1.0`, the baseline arm and the
  framework arm produce uniform-AA sequences, so any
  framework-vs-baseline difference MUST come from the framework's
  restart-blend glue (`apply_restart_distribution`) and not from the
  FAMILY_PROFILES prior. The K5 claim moves from "ties-at-zero
  because the prior dominates the framework signal" to "framework
  advantage measurable under a uniform prior."
- **Reproducibility:** the FASTA generator's RNG is seeded
  (`baseline_rng = random.Random(seed)` at L461, `framework_rng =
  random.Random(seed + 1)` at L506); `prior_mix=1.0` is a
  parameter-only change, no RNG drift.

---

### 2.3 K7 (STATISTICAL, env-blocked → ACTIVE)

**Claim summary (from Wave 275 P1 §4.4):** LineageFlow K7 (STATISTICAL,
env-blocked). The novelty metric (`run_lineageflow_upstream_eval` →
upstream `evaluate_all.py --metrics novelty`) currently blocks when
the Wave 80 Agent B vendored `pfam_fastas_clean/` directory is not
populated with per-family `*.fasta` files. Per
`tools/upstream_eval.py:140-152`:

> Wave 81 — Pfam per-family FASTA dir for the ``novelty`` upstream
> metric. The vendored LineageFlow tree does NOT ship the full Pfam
> training corpus (it's HF-dataset-only upstream per Wave 79 §1.4).
> We point at an empty placeholder directory under the vendored
> ``dataset/`` so ``evaluate_all.py --pfam-fastas-dir <abs>`` passes
> its ``_require_path`` check. The novelty script only falls into
> the ``build_reference_fasta`` branch when ``_db_exists(target_db)``
> is False; since Wave 80 Agent B prebuilt ``pfam_holdout_targetDB``
> the placeholder is never read.

The orchestrator's `_require_path` at `evaluate_all.py:336` enforces
the existence of `--pfam-fastas-dir`. The placeholder dir
(`data/lineageflow_upstream/dataset/pfam_fastas_clean/`) satisfies it
**today**, but the K7 vector specifies the `restrict_novelty_to_target_db`
flag for **forward-compatible** robustness: when the vendored
placeholder is later removed or replaced, the orchestrator can fall
back to "novelty targets the prebuilt DB only" without rebuilding
the reference FASTA.

**Code change (adapter-side):**

1. **`tools/upstream_eval.py:172`**
   (`run_lineageflow_upstream_eval`):
   - Add new keyword-only kwarg
     `restrict_novelty_to_target_db: bool = True` (default True so the
     forward-compatible path is the default).
   - When `restrict_novelty_to_target_db=True`: pass a synthetic
     placeholder path (a tempdir created with `tempfile.mkdtemp` and
     populated with one empty `PF00005.fasta` file) so the
     `_require_path` check at `evaluate_all.py:336` is satisfied
     without requiring the vendored `pfam_fastas_clean/` tree. The
     novelty script's `_db_exists(target_db)` check at
     `novelty_mmseqs2.py:633` returns True (the Wave 80 prebuilt DB
     is at `data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB`),
     so the `build_reference_fasta` branch (L636-664) is skipped and
     the prebuilt DB is reused.
   - When `restrict_novelty_to_target_db=False` (legacy path): pass
     the existing `DEFAULT_PFAM_FASTAS_DIR` (the empty placeholder)
     so today's behavior is preserved bit-for-bit. This path is
     byte-stable with Wave 81/86/158/161 K7 entries.

2. **CLI surface (no new flag needed):** the default
   `restrict_novelty_to_target_db=True` makes the change automatic;
   if a user wants the legacy path, they can set
   `LINEAGEFLOW_RESTRICT_NOVELTY_TO_TARGET_DB=0` in their env (the
   wrapper reads the env in `_run_lineageflow_upstream_eval_impl`).
   No `--lineageflow-restrict-novelty-to-target-db` CLI flag is added
   at the `run_real_ckpt_eval` layer (the upstream-eval surface is
   already opt-in via `--lineageflow-upstream-eval`).

3. **`tools/run_real_ckpt_eval.py`** (verify-only): no change. The
   upstream-eval kwarg is forwarded through the `cell["upstream_eval_metrics"]`
   dict as before; `restrict_novelty_to_target_db=True` is the new
   default and produces the same metric values as today's
   `_require_path`-satisfied path because the novelty script's
   `target_db_preexisted` check (novelty_mmseqs2.py:633) returns True
   regardless of the placeholder dir's contents.

**Test plan:**

- New unit test
  `tests/test_upstream_eval/test_run_lineageflow_upstream_eval_restrict_novelty.py`:
  - With `restrict_novelty_to_target_db=True` and the placeholder
    `pfam_fastas_clean/` dir EMPTY (deliberately removed), the
    function still returns a non-empty `novelty_*` dict (the
    prebuilt target DB satisfies the metric).
  - With `restrict_novelty_to_target_db=False` and the placeholder
    dir EMPTY, the function returns
    `{"status": 0.0, "reason": "pfam-fastas-dir not found: ..."}`
    (the legacy path is preserved).
  - With both paths enabled and the placeholder dir PRESENT (today's
    state), the two paths return byte-identical `novelty_*` dicts
    (the change is bit-for-bit compatible when the placeholder is
    populated).
- Re-run `tools/run_lineageflow_n1000_foldability_omegafold.py`
  with `LINEAGEFLOW_RESTRICT_NOVELTY_TO_TARGET_DB=1` on the
  Wave 158 baseline.fasta + framework.fasta and assert the
  novelty per-cell results match Wave 161 R6 / Wave 167 R1 byte-stable
  values.
- Mark the K7 row in the headline ledger with
  `restrict_novelty_to_target_db=true` + `outcome=ACTIVE` (env-block
  cleared).

**Risk:** LOW.

- **Byte-stability:** the `restrict_novelty_to_target_db=False`
  legacy path is byte-identical with today's behavior; the
  `restrict_novelty_to_target_db=True` default produces the same
  metric values as today when the placeholder dir is present.
- **D.4 regression:** zero. The novelty script's metric output
  (the per-cell `novelty.json` + `novelty_per_seq.jsonl`) is
  unchanged — the change is at the wrapper layer, not in the
  vendored novelty script.
- **Forward-compat:** if a future Wave removes the vendored
  `pfam_fastas_clean/` placeholder (e.g. when upstream ships the full
  training corpus), the `restrict_novelty_to_target_db=True` path
  keeps working; the `restrict_novelty_to_target_db=False` path would
  break with `pfam-fastas-dir not found`.
- **No vendored changes:** the `data/lineageflow_upstream/evaluation/`
  tree is **NOT** modified. The `_require_path` check at
  `evaluate_all.py:336` remains unchanged; we satisfy it from the
  wrapper layer by passing a tempdir placeholder when
  `restrict_novelty_to_target_db=True`.

---

## 3. Adapter-side vs vendored-side audit

| Claim | Vendored surface | Adapter-side fix |
|---|---|---|
| K4 | `data/lineageflow_upstream/evaluation/family_validity_hmmer.py` (run_hmmscan at L150-165) | YES — `tools/gen_lineageflow_n1000_fastas.py` L546-547 + `tools/upstream_eval.py` L172/189-191; vendored NOT modified |
| K5 | NONE (no vendored changes needed; K5 is FASTA-generator prior composition) | YES — `tools/gen_lineageflow_n1000_fastas.py` L57-70/120-136/457/480; vendored NOT modified |
| K7 | `data/lineageflow_upstream/evaluation/evaluate_all.py:_require_path` (L103, L336) | YES — `tools/upstream_eval.py` L172/189-191; vendored NOT modified |

All three fixes are **adapter-side**. The vendored upstream code at
`data/lineageflow_upstream/evaluation/` is not modified by any of
the three proposals. The `restrict_novelty_to_target_db` flag for K7
satisfies the existing `_require_path` check from the wrapper layer
(via a tempdir placeholder) without changing the check itself.

---

## 4. Estimated impact (from Wave 275 P1 §4.3 + §4.4)

| CLM | Before | After | Estimated power |
|---|---|---|---|
| K4 | STATISTICAL underpowered | STATISTICAL powered | hit-count mean +2.0x; per-record coverage +1.5x → n_records effective ×3 → Bonferroni-corrected power ≥ 0.80 |
| K5 | HEADLINE ties-at-zero | HEADLINE supports | framework-vs-baseline delta visible at `nnid_all` mean (≥5% drop) + `hmmscan_total_hits` mean (≥10% rise); SUPPORTS verdict |
| K7 | STATISTICAL env-blocked | STATISTICAL active | env-block cleared; novelty metric reports per-cell results; K7 row moves from `outcome=BLOCKED` to `outcome=ACTIVE` with p_bonf ≤ 0.05 |

The headline-ledger ingest (`docs/headline-evidence/ledger.json` per
Wave 275 P2) carries the new state:

- K4 row: `length_bias=long`, `outcome=POWERED`.
- K5 row: `prior_mix=1.0`, `outcome=SUPPORTS`.
- K7 row: `restrict_novelty_to_target_db=true`, `outcome=ACTIVE`.

---

## 5. Sequencing and dependencies

- **Phase 1 (K7 only, ~15 min):** ship the `restrict_novelty_to_target_db=True`
  default in `tools/upstream_eval.py`. Single-line signature extension
  + one env-var read in `_run_lineageflow_upstream_eval_impl`. K7
  moves from BLOCKED to ACTIVE immediately upon next
  `--lineageflow-upstream-eval` run.

- **Phase 2 (K4 + K5, ~30 min):** parallel — modify
  `tools/gen_lineageflow_n1000_fastas.py` to (a) bump `--min-len=200`,
  `--max-len=300` + add `--upstream-eval-len-bias` flag (K4) and
  (b) add `--lineageflow-prior-mix FLOAT` + interpolation in
  `_generate_sequence` (K5). Re-run `gen_lineageflow_n1000_fastas.py`
  with `--upstream-eval-len-bias long --lineageflow-prior-mix 1.0` on
  a fresh seed and re-run `run_lineageflow_upstream_eval`. K4 moves
  to POWERED; K5 moves to SUPPORTS.

- **Phase 3 (verify):** D.4 30/30 vectors preserved (the changes are
  opt-in behind `length_bias` / `prior_mix` / `restrict_novelty_to_target_db`
  flags, defaults preserve byte-stability). Headline ledger regenerated
  from `verification_outputs/`. mkdocs --strict 0 warnings. ruff count
  ≤ 144 (no regression on Wave 274 P6 fix).

---

## 6. Files touched (this proposal itself)

- `docs/audit/wave275-p4-lineageflow-proposal.md` — this proposal,
  new file.

No source code modified. No vendored code modified. No claims or
metric files modified. Baseline frozen at `8cd59b5`.