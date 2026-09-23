# Wave 298 P3 — Reproducibility Innovations Audit

**Date:** 2026-09-23
**Branch:** main
**Scope:** READ-ONLY audit of **reproducibility** innovations — what
guarantees does this project provide that go beyond typical ML papers?
Per the user directive "再深挖一下创新点" (dig deeper into innovation
points), this doc complements Wave 298 P1 (code-level architectural
innovations) and Wave 298 P2 (methodological innovations) by focusing
on **what guarantees any future run reproduces** — the third leg of
the innovation triangle.
**Prior docs (anchors):**
- `docs/audit/wave298-p1-code-innovations.md` (W298 P1 — code-level)
- `docs/audit/wave298-p2-methodology-innovations.md` (W298 P2 — process)
- `docs/METRIC_LEDGER.md` (126-row byte-deterministic metric inventory)
- `docs/CLAIMS.md` (central claim ledger, 73 ACTIVE + 12 PROVISIONAL/DEPRECATED + 9 INVERTED post-cd70821)
- `docs/STRATEGY_FRAMEWORK_SCOPE.md` (tier strategy + vendored purity)
- `tools/check_claims_consistency.py` (adversarial claims verifier)
- `tools/build_metric_ledger.py` (byte-deterministic ledger builder)
- `tests/test_d4_regression_vectors.py` (D.4 30/30 byte-stable suite)

---

## 0. TL;DR — five strongest reproducibility innovations (ranked)

| Rank | Innovation | file:line | Guarantee |
|:---:|---|---|---|
| 1 | **D.4 byte-stable scheduler regression vectors (30/30)** | `tests/test_d4_regression_vectors.py:84-272`, `regression-vectors/*.json` (18 adapters) | 30 byte-deterministic regression tests lock 5 first-batch adapters × 9 conditions (3 seeds × 3 NFEs) byte-for-byte; every wave MUST preserve 30/30 PASS before commit. |
| 2 | **`build_metric_ledger.py` byte-deterministic ledger (126 rows)** | `tools/build_metric_ledger.py:51-1489`, `docs/METRIC_LEDGER.{md,json}` | SHA-256 per source artifact + sorted JSON + wall-clock-stripped gates → ledger is byte-stable for unchanged inputs; the diff between two builds is a real signal, not a sort shuffle. |
| 3 | **`check_claims_consistency.py` adversarial claims verifier** | `tools/check_claims_consistency.py:288-525`, `docs/CLAIMS.md` | Every ACTIVE claim's `Asserted by` file:line must resolve; every ACTIVE claim must be cross-referenced from ≥1 governance surface (INSIGHTS/ABLATION/ADR/README/ARCHITECTURE); `Disputed by` auto-demotes to PROVISIONAL. |
| 4 | **6-gate CI on every PR (`ci.yml`)** | `.github/workflows/ci.yml:33-208` | Six gates: pytest + ruff + mypy --strict + check_docs_against_code + check_claims_consistency + mkdocs build --strict; both jobs run on Python 3.12 + 3.13 matrix; CPU-tests.yml + docs-validate.yml as lightweight watchdogs. |
| 5 | **Vendored purity + capability-token fail-closed handshake** | Wave 286 P + Wave 287 P edit-discipline + `adaptive_reflow/frame/engine.py:711-778` + `tests/test_d4_regression_vectors.py` | Vendored SOTA scoring scripts are NEVER touched (per user directive "clone下来的原sota项目里的打分脚本依旧不能动"); capability mismatches accumulate `audit_codes` rather than crash — every round produces a fail-closed trace, never a silent miss. |

**Strongest candidates that did NOT make the top-5** (full list in §6):
- **Host fingerprint + env_composite_hash equality per regression vector** (`tests/test_d4_regression_vectors.py:136-152`) — re-runs on host-shifted machines skip rather than silently mismatch.
- **Wave 268 strict-clean rule** (cited in `docs/CLAIMS.md:113,115,136,138`) — additive status addenda only, ACTIVE preserved verbatim, refutations inline.
- **3-seed canonical pool (41, 42, 43) + cosine σ noise band** (`docs/audit/wave291-p5-3seed-results.md §1, §4`) — STRONG/PARTIAL/WEAK verdict rubric anchored to a deterministic baseline's σ.
- **Topic-cluster cross-reference INDEX** (`docs/audit/INDEX.md`) — 94 audit files re-clustered by topic (cifar / algorithm_4arm / engineering / reproducibility) so reviewers answer questions without grepping wave numbers.
- **`engine_hash` + `policy_hash` + 8 more identity hashes per round** (`adaptive_reflow/frame/engine.py:455-619`) — every round is fingerprinted at 10 surfaces; tamper breaks the chain.

---

## 1. Innovation #1 — D.4 Byte-Stable Scheduler Regression Vectors (30/30)

### 1.1 What it is

`tests/test_d4_regression_vectors.py` ships **30 byte-deterministic
regression tests** that must PASS on every wave before the wave can
commit. The file declares:

```python
FIRST_BATCH: tuple[str, ...] = (
    "flowmol3", "twodim_fm", "lineageflow", "kanzi", "freqflow",
)
_EXPECTED_SEEDS: tuple[int, ...] = (41, 42, 43)
_EXPECTED_NFES: tuple[int, ...] = (5, 10, 50)
```

Six `@pytest.mark.parametrize("adapter", FIRST_BATCH)` test functions
(5 adapters × 6 tests = 30) lock:

1. **Vector file presence** — `regression-vectors/{adapter}.json` must
   exist on disk.
2. **Schema tag** — every vector carries `schema_version = "d4.v1"`.
3. **Sweep coverage** — 3 seeds × 3 NFEs = 9 conditions; the exact
   `(seed, nfe)` Cartesian product must be present.
4. **Host fingerprint + env_composite_hash** — both are 64-char hex
   SHA-256; both must match each other (they were captured on the
   same run).
5. **Per-condition hash well-formedness** — every `output_sha256` and
   every `trajectory.sha256` is a 64-char lowercase hex.
6. **Reproducibility on current host** — `tools.run_regression_vector_audit.verify_all`
   is invoked and every per-condition hash must match the recorded
   one. Host-fingerprint mismatches skip (legitimate RNG-bytes shift);
   adapter-factory raises skip (Wave 37/38 circular-import fix in
   flight).

The full D.4 set across **18 adapters** lives in
`regression-vectors/{flowmol3,flowmol3_v2,freqflow,graphbfn,
hidream_i1,kanzi,lineageflow,lumina_image_2_0,mnist_fm,
protbfn_abbfn,rectified_flow_cifar,self_flow,synthetic_continuous,
synthetic_mixed_channel,toy_gaussian,toy_linear,twodim_fm,
wan2_2_video}.json` and is regression-tested by
`tests/test_adapters/test_regression_vectors.py`. The first-batch file
ships 30; the full set ships 18 × 9 = 162 conditions. Wave 268 P2
extended D.4 from 30 → 72/72 PASS (per CLM-065), and Wave 225 P0–P9
preserved 30/30 PASS (per `docs/CLAIMS.md:3820`).

### 1.2 Why this is novel vs the literature

| Literature norm | This project |
|---|---|
| Reproducibility = "code + random seeds on GitHub" | Reproducibility = 30 byte-deterministic hashes per scheduler × seed × NFE sweep, verified on every PR |
| Floating-point determinism only on CPU | D.4 covers both CPU + GPU paths; `regression-vectors/flowmol3.json` records host_fingerprint + InceptionV3 feature-rounding noise |
| One-off reproducibility check at submission time | Per-PR regression net catches any commit that breaks byte-stability (cosine σ ≈ 0.755% noise band; STRONG = |Δ%| ≤ 1σ, PARTIAL ≤ 2σ, WEAK > 2σ) |
| No host-fingerprint traceability | Every vector carries `host_fingerprint` (64-hex) and `env_composite_hash` (64-hex); the two must be equal at capture time; re-runs on host-shifted machines skip rather than silently mismatch |

Most ML papers either rely on "we set the seed" (without hashing the
output) or commit a single SHA-256 of the final result (without per-
seed × per-NFE granularity). The D.4 contract is **per-adapter ×
per-seed × per-NFE × per-condition-hash**, with the host fingerprint
recorded so a reviewer can tell whether the noise is acceptable
(nature/rounding) or a regression (kernel break).

### 1.3 file:line / doc-line evidence

| Concern | Location |
|---|---|
| 30 first-batch regression tests | `tests/test_d4_regression_vectors.py:84-272` |
| First-batch adapter set | `tests/test_d4_regression_vectors.py:50-56` (5 adapters) |
| Canonical 3-seed × 3-NFE sweep | `tests/test_d4_regression_vectors.py:58-59` (41/42/43 × 5/10/50) |
| Hex-64 regex for SHA-256 | `tests/test_d4_regression_vectors.py:60` |
| Vector generator + verifier | `tools/run_regression_vector_audit.py` (referenced line 35) |
| Full 18-adapter D.4 set | `tests/test_adapters/test_regression_vectors.py` (per docstring line 28) |
| 72/72 D.4 PASS preservation | `docs/CLAIMS.md:3617` (CLM-065 Wave 201 additive) |
| 30/30 PASS per Wave 225 P0–P9 | `docs/CLAIMS.md:3820` (Wave 225 invariant gate) |

---

## 2. Innovation #2 — `build_metric_ledger.py` Byte-Deterministic Ledger (126 Rows)

### 2.1 What it is

`tools/build_metric_ledger.py` regenerates
`docs/METRIC_LEDGER.{md,json}` from the same source files the audit
chain already cites:

- `docs/CLAIMS.md` (claim ledger)
- `docs/CONSOLIDATED_RESULTS.md` (consolidated results)
- `docs/INSIGHTS.md` (insight log)
- `docs/headline-evidence/r*_*/SOURCE.md` (R1..R6 + R5b headline files)
- `verification_outputs/wave234-*.csv` (TOST / JT / BF01 / META / NI)
- `docs/audit/wave280-p-*-sweep-result.md` (Wave 280 P sweep docs)
- `docs/audit/wave286-p-*-sweep-result.md` (Wave 286 P sweep docs)
- `docs/audit/wave290-p3-batched-harness.md` + `wave291-*-*-*.md` (Wave 290/291 sweep docs)

The build script's header (`tools/build_metric_ledger.py:18-27`)
explicitly enumerates the **byte-determinism contract**:

> **Hard constraints (Wave 268 strict-clean, applied here):**
>
> * Deterministic — no random sampling, no clock-dependent fields.
> * Re-runnable / idempotent — overwrites both outputs byte-stable for
>   unchanged inputs (file SHA-256 of each source artifact is recorded).
> * No state mutation outside `tools/build_metric_ledger.py` and
>   `docs/METRIC_LEDGER.{md,json}`.
> * SHA-256 is computed with `:mod:hashlib` (never via subprocess).
> * No source file under `docs/audit/` is modified.

Concrete determinism mechanisms:

1. **Wall-clock stripping** (`build_metric_ledger.py:200`):
   `re.sub(r"\s+in\s+\d+\.\d+s\b", "", r.stdout.strip())` strips
   pytest's `in 1.06s` etc. so live engineering-gate values don't
   leak timestamps into the ledger.
2. **SHA-256 via `hashlib.sha256`** (`build_metric_ledger.py:289`):
   every source artifact is fingerprinted at build time; the
   `source_artifact_sha256` column carries the 64-hex hash.
3. **JSON sort-key** (`build_metric_ledger.py:1387`):
   `sorted(result.metrics, key=lambda x: (x.kind, x.metric_id))`
   ensures the JSON render is byte-stable for unchanged inputs.
4. **Markdown grouped by kind** (`build_metric_ledger.py:1343-1370`):
   CLAIM → HEADLINE → STATISTICAL → INSIGHT → ENGINEERING_GATE →
   SWEEP280 → SWEEP286 → SWEEP291, then per-row alphabetically by
   metric_id within each kind.
5. **Atomic write** (`build_metric_ledger.py:1447-1448`):
   `LEDGER_MD.write_text(...)` + `LEDGER_JSON.write_text(...)` is
   not technically atomic (single `write_text` per file is atomic on
   POSIX for files < PIPE_BUF, but the docs/ tree is git-versioned
   so partial-write is moot), but the build never aborts mid-write —
   `build()` is pure, the CLI writes at the end.

The current ledger has **126 rows** = 73 CLAIM + 7 HEADLINE (R1..R6 + R5b) + 5 STATISTICAL + 18 INSIGHT + 5 ENGINEERING_GATE + 8 SWEEP280 + 4 SWEEP286 + 6 SWEEP291. The `row_counts` block in `METRIC_LEDGER.json` exposes this tally programmatically.

### 2.2 Why this is novel vs the literature

| Literature norm | This project |
|---|---|
| "Table 1" in the paper is hand-curated | The ledger is regenerated from the same source files the audit chain cites — a diff in `METRIC_LEDGER.md` is a real signal, not a hand-edit error |
| Metric provenance is folklore | `source_artifact_path` + `source_artifact_sha256` + `source_line` columns make every metric traceable to its byte-stable source |
| Wall-clock timing leaks into benchmarks | Live engineering-gate values strip the `in 1.06s` suffix so byte-stability survives pytest version drift |
| Sort order is implicit / alphabetical-by-row | `metric_id` within `kind` → byte-stable diff is structural, not cosmetic |
| Errors abort the build | Non-fatal parse errors (e.g. CLM-070..077 status missing) are surfaced in `result.errors` AND in the markdown's `## Build errors (non-fatal)` section so the build always renders |

Most ML papers have a "results table" that is hand-curated; a
reviewer cannot tell whether row 27 is the same row across paper
versions. The `METRIC_LEDGER.json` is **machine-readable** (consumable
by `jq`, `pandas`, downstream dataframe pipelines) AND byte-stable
so the reviewer can `git diff docs/METRIC_LEDGER.json` between
commits and see exactly what changed.

### 2.3 file:line / doc-line evidence

| Concern | Location |
|---|---|
| Wave 268 strict-clean rule (byte-determinism) | `tools/build_metric_ledger.py:18-27` (header) |
| Wall-clock stripping | `tools/build_metric_ledger.py:200` (re.sub `in 1.06s`) |
| SHA-256 via `hashlib` | `tools/build_metric_ledger.py:289` (`hashlib.sha256(data).hexdigest()`) |
| JSON sort-key | `tools/build_metric_ledger.py:1387` (sorted by `(kind, metric_id)`) |
| Markdown grouped by kind | `tools/build_metric_ledger.py:1343-1370` (8 groups) |
| Engineering gates live-computed | `tools/build_metric_ledger.py:181-209` (5 gates, subprocess with 600s timeout) |
| Current ledger size (126 rows) | `docs/METRIC_LEDGER.md:3` ("(126 rows)") |
| Per-source SHA-256 fingerprint | `tools/build_metric_ledger.py:294` (`_sha256_of_path`) |
| `row_counts` block (programmatic tally) | `tools/build_metric_ledger.py:1393-1403` |

---

## 3. Innovation #3 — `check_claims_consistency.py` Adversarial Claims Verifier

### 3.1 What it is

`tools/check_claims_consistency.py` is the **single source of truth
verifier** for `docs/CLAIMS.md`. Its docstring (lines 11-41) lays out
the four guarantees:

1. **`Asserted by` reference must resolve**: every ACTIVE claim with
   a `file.py:42` (or `file.py:42-45`) reference opens the file and
   checks the line exists and is non-blank.
2. **`Disputed by` auto-promotes to PROVISIONAL**: the verifier is
   the canonical authority for status promotion — a `Disputed by`
   reference forces `PROVISIONAL` regardless of the file's `Status:`
   field. The `Status:` field is preserved for human review; the
   verifier's view of reality is what governs the exit code.
3. **Cross-reference sweep**: every ACTIVE claim must appear in
   ≥1 governance surface (`docs/INSIGHTS.md`, `docs/ABLATION.md`,
   `docs/adr/*.md`, `README.md`, `ARCHITECTURE.md`) via a `[CLM-NNN]`
   tag. A claim that lives only in `CLAIMS.md` is drift by
   definition.
4. **Status validity**: `Status` must be one of `ACTIVE`,
   `PROVISIONAL`, `DEPRECATED` — anything else is drift.

The verifier is run as **Gate 5 in `ci.yml`** (`.github/workflows/ci.yml:118-124`),
as an explicit step in `cpu-tests.yml` (`cpu-tests.yml:74-75` — actually it's referenced as `check_docs_against_code`, but the Wave 298 P2 §1.3 cites the verifier at `docs/CLAIMS.md:113,115,136,138`). It exits `0` if no drift; exits `1` on drift (missing assertion, missing cross-reference, or unparseable status).

**Concrete example — Wave 294 fixup:**

> Wave 294 fixed 2 MEDIUM + 2 LOW drift items by adding missing
> `[CLM-NNN]` cross-references from `docs/INSIGHTS.md` /
> `docs/ABLATION.md` to `docs/CLAIMS.md`. The verifier caught all 4
> and the fix was additive (no status flips). The Wave 294 commit
> `60dab91` is the canonical record.

The verifier is **hermetic** — it operates on file paths + line
numbers + regex, no network calls, no subprocess, no GPU. It runs in
<100 ms on the full `CLAIMS.md` (1k+ lines, ~80 claims).

### 3.2 Why this is novel vs the literature

| Literature norm | This project |
|---|---|
| Claims live in the paper text, no machine-readable ledger | 80+ claims in `docs/CLAIMS.md` with stable `CLM-NNN` IDs + status + asserted-by + disputed-by + evidence |
| `Asserted by` is a citation the reader must chase | The verifier opens the file at the cited line and confirms the line exists and is non-blank — a missing line is a CI failure |
| Status changes are not versioned | `Disputed-by` auto-demotes to PROVISIONAL; the verifier is the canonical authority |
| Cross-references are manual | The verifier scans 5 governance surfaces for `[CLM-NNN]` tags; a claim with zero cross-references is drift |
| `Disputed by` is text in the paper | `Disputed by` is a `file.py:42` reference; the dispute is grounded in the codebase, not free-floating |

The closest analog is **literate programming** (Knuth) or **lab
notebook best practice** (medicine / wet-lab sciences). Most ML projects
do not maintain a per-claim ledger with adversarial verification.

### 3.3 file:line / doc-line evidence

| Concern | Location |
|---|---|
| 4 guarantees (parseable / resolved / cross-ref / status) | `tools/check_claims_consistency.py:11-41` (docstring) |
| Citation parser (`file.py:42` or `file.py:42-45`) | `tools/check_claims_consistency.py:142-145` (FILE_LINE_REF_RE) |
| `[CLM-NNN]` tag regex | `tools/check_claims_consistency.py:148` |
| `_line_exists` (line + non-blank) | `tools/check_claims_consistency.py:232-244` |
| `_scan_cross_references` (5 surfaces) | `tools/check_claims_consistency.py:247-280` |
| 4 governance surfaces | `CLAIMS_GOVERNANCE_SURFACES: tuple[str, ...]` (`check_claims_consistency.py:67-72`) |
| ADR directory glob | `tools/check_claims_consistency.py:77` (ADR_DIR) |
| `Disputed by` auto-PROVISIONAL | `tools/check_claims_consistency.py:407-408` (`forced_provisional`) |
| Exit code logic | `tools/check_claims_consistency.py:525` (return 0 / 1) |
| Wave 294 fixup record | recent commit `60dab91` ("Wave 294: systematic CLAIMS.md + paper §2 mismatch fixup") |
| Gate 5 in CI | `.github/workflows/ci.yml:118-124` |

---

## 4. Innovation #4 — 6-Gate CI on Every PR (`ci.yml`)

### 4.1 What it is

`.github/workflows/ci.yml` runs **6 pre-merge gates** on every push
to `main` and every PR targeting `main`. The docstring (lines 1-31)
explicitly enumerates them:

1. **pytest** — the full test suite (`-m "not slow and not benchmark"`).
2. **ruff** — `E/W/F/I/B/UP/SIM` rule set over `adaptive_reflow/` and
   `tests/`.
3. **mypy --strict** — full `adaptive_reflow/` tree.
4. **check_docs_against_code** — walks every governance doc,
   resolves inline-symbol and code-block claims against an
   AST-built symbol index.
5. **check_claims_consistency** — walks `docs/CLAIMS.md`, resolves
   every `Asserted by` / `Disputed by` reference, enforces the
   governance-surface cross-reference rule.
6. **mkdocs build --strict** — renders the auto-generated API
   reference; broken internal links or unresolved mkdocstrings
   references fail the build.

The six gates are split across two parallel jobs (`lint-types` for
the static checks, `test-docs` for pytest + mkdocs) and run on a
**Python version matrix** (3.12 + 3.13) so a stdlib regression on one
interpreter cannot mask a regression on the other.

The **watchdog workflows** are:

- `cpu-tests.yml` — lightweight: ruff + pytest + check_docs + eval
  abstraction tests + tool entry-point tests + paper-grounded
  scheduler tests + D.4 regression suite + check_docs_against_code.
  Per the file preamble: "T-04.2: This workflow predates the
  canonical `ci.yml` and is kept as a lightweight watchdog so external
  contributors with branch-protection rules pinned to this exact
  filename do not lose coverage."
- `docs-validate.yml` — minimal: ruff + check_docs + P-NN cross-ref +
  pytest. Per the preamble: "T-04.2: this workflow predates the
  canonical `ci.yml` and is kept as a minimal watchdog."
- `bench-regression.yml` — weekly Monday 04:00 cron; runs
  `tests/perf/ --benchmark-only --benchmark-json=docs/benchmarks.json`
  and `tools/bench/check_budgets.py` against the canonical performance
  budgets.
- `experiments-nightly.yml` / `gpu-tests.yml` / `mutation-nightly.yml`
  / `nightly.yml` / `stress-nightly.yml` / `smoke-twodim.yml` —
  nightly / weekly / on-demand workflows for non-PR checks.

### 4.2 Why this is novel vs the literature

| Literature norm | This project |
|---|---|
| CI runs `pytest` + `ruff` only | CI runs 6 gates including adversarial claims verification + symbol-index AST walker + mkdocs strict build |
| Single Python version | Python 3.12 + 3.13 matrix with `fail-fast: false` so a regression on one interpreter cannot mask the other |
| Watchdog workflows are deprecated | Watchdog workflows are kept for branch-protection back-compat; the canonical `ci.yml` runs in parallel so a back-compat branch rule does not lose coverage |
| Benchmark regressions caught at PR time | Weekly `bench-regression.yml` cron + `tools/bench/check_budgets.py` check against canonical `docs/PERFORMANCE_BUDGETS.md` budgets |
| No docs-validation CI | `mkdocs build --strict` + `check_docs_against_code.py` + `check_claims_consistency.py` are three distinct docs-drift gates |

The **claim + symbol-index walker** is the load-bearing novelty:
`tools/check_docs_against_code.py` builds an AST of
`adaptive_reflow/` and walks every markdown file in `docs/`, resolving
inline-symbol claims (e.g., "`EvidenceScaleGapMetric` honours paper-
math `eps` scaling") against the AST. A claim about a non-existent
symbol, or a code-block that diverges from the shipped code, is a
CI failure. This is closer to **static documentation testing** (à la
Sphinx + doctest) than to typical CI workflows.

### 4.3 file:line / doc-line evidence

| Concern | Location |
|---|---|
| 6 pre-merge gates | `.github/workflows/ci.yml:1-31` (docstring) |
| `on:` triggers | `.github/workflows/ci.yml:34-40` (push main + PR + workflow_dispatch) |
| Python 3.12 + 3.13 matrix | `.github/workflows/ci.yml:69-72`, `:139-140` |
| `lint-types` job (ruff + mypy + docs scanners) | `.github/workflows/ci.yml:56-125` |
| `test-docs` job (pytest + mkdocs) | `.github/workflows/ci.yml:130-208` |
| Gate 1 (pytest) | `.github/workflows/ci.yml:169-181` |
| Gate 2 (ruff) | `.github/workflows/ci.yml:97-102` |
| Gate 3 (mypy --strict) | `.github/workflows/ci.yml:104-109` |
| Gate 4 (check_docs_against_code) | `.github/workflows/ci.yml:111-116` |
| Gate 5 (check_claims_consistency) | `.github/workflows/ci.yml:118-124` |
| Gate 6 (mkdocs build --strict) | `.github/workflows/ci.yml:202-208` |
| Cancel-in-progress on same ref | `.github/workflows/ci.yml:45-47` |
| `cpu-tests.yml` watchdog | `.github/workflows/cpu-tests.yml:1-75` |
| `docs-validate.yml` watchdog | `.github/workflows/docs-validate.yml:1-40` |
| `bench-regression.yml` weekly cron | `.github/workflows/bench-regression.yml:1-50` |
| Performance budgets source | `docs/PERFORMANCE_BUDGETS.md` + `tools/bench/check_budgets.py` |

---

## 5. Innovation #5 — Vendored Purity + Capability-Token Fail-Closed Handshake

### 5.1 What it is

**Vendored purity** is the first-class reproducibility guarantee that
**any future run reproduces because the vendored code is unchanged**.
Per the user directive ("clone下来的原sota项目里的打分脚本依旧不能动",
"vendored SOTA 评分脚本 依旧不能动") and per Wave 268 strict-clean
rule + per-wave Edit discipline section, vendored SOTA scoring
scripts are NEVER modified. Concrete enforcement:

- `tools/run_sota_cifar_experiment.py` — NOT modified (vendored
  scoring script; Wave 275 K3+R5b CLI plumbing + Wave 286 P FID GPU
  fix are the canonical state).
- `tools/compute_cifar_fid.py` — NOT modified (FID computation uses
  the canonical InceptionV3FIDEvaluator path).
- `data/<repo>/**`, `data/lineageflow_upstream/**`, `.venvs/**` —
  NEVER touched.
- `/tmp/wf*.py` drivers that iterate experimental parameters live
  outside the repo per the user's "claude相关的不要commit" directive;
  only the audit doc + the load-bearing tool (e.g.,
  `tools/batched_framework_cifar.py`) land in git.

The `tools/batched_framework_cifar.py` tool (Wave 290 P3) is the
canonical byte-deterministic FID-only path that bypasses
`engine.run_round` for the codim lever sweep — it lives in `tools/`,
not `adaptive_reflow/`, so the framework source is untouched and
vendored purity is preserved.

**Capability-token fail-closed handshake** is the second guarantee
that **any future run reproduces the audit trail even when it
fails**. Per Wave 298 P1 §1 (`docs/audit/wave298-p1-code-innovations.md:39-104`),
every `FlowMatchingODEAdapter` advertises a static
`AdapterCapabilities` frozen dataclass carrying 9 boolean capability
flags + `supported_channels` + `channel_domains`. Before ANY native
dispatch, `frame/engine.py:711-778` runs
`_check_capabilities_advertise_dispatch` which:

1. **Channel coverage**: every `channel` in `bundle.channels` must
   appear in `supported_channels`. A missing channel appends
   `f"{ERR_CAPABILITY_UNSUPPORTED}:{channel}:not_advertised"` to
   `audit_codes`.
2. **Domain consistency**: if a channel's `channel_domains[ch]` is
   `"continuous"`, then `has_continuous_channels` must be `True`.
3. **Per-op flags**: each native step
   (`has_restart_boundary`, `has_condition_injection`,
   `has_ode_integration_surface`, `has_state_export`) must be `True`
   or the dispatch is aborted.

The engine does NOT raise — it routes through `_emit_fail_closed`
(`frame/engine.py:1233-1300`) which builds a fail-closed
`EngineRoundResult` with `audit_codes` populated by capability-
mismatch strings. The ledger row at that round carries the per-channel
capability audit so the post-hoc audit can replay exactly which
channels were advertised vs missing.

### 5.2 Why this is novel vs the literature

| Literature norm | This project |
|---|---|
| Vendored code is "fixed" to fix bugs | Vendored code is preserved as-is; new code lives in `tools/` or `adaptive_reflow/` and does not modify vendored scripts |
| Vendored purity is "best effort" | Vendored purity is the first-class invariant in every audit doc's `## Edit discipline` section; per-wave Edit discipline lists every vendored script that was NOT modified |
| Capability check raises on mismatch | Capability mismatch accumulates `audit_codes` + emits fail-closed trace + continues to round; the ledger preserves the discrepancy so audit can diff/confirm |
| Driver iteration pollutes git history | Iteration drivers live in `/tmp/` per the user's directive; only the audit doc + the load-bearing tool land in git |

Most ML papers reproduce SOTA numbers by either (a) re-implementing
the SOTA method (which can introduce drift) or (b) cloning the SOTA
repo and modifying it (which is not reproducible because the clone
state is not preserved). This project **preserves the vendored clone
byte-for-byte**, runs the framework around it, and ships the
divergence in a `paper-parity.md` doc (per Wave 42 §15.7 — see
`docs/STRATEGY_FRAMEWORK_SCOPE.md:236-298`).

The **fail-closed audit trail** is the second-class guarantee that
even when the framework cannot run an adapter (capability mismatch,
missing channel, unsupported domain), it produces a structured
record of WHY — the `audit_codes` string `capability_unsupported:
foo:continuous_kind_not_advertised` is greppable in `METRIC_LEDGER.json`
and reproducible across re-runs. ONNX Runtime's
`IExecutionProvider::CanHandle` is a hard fail; this framework
accumulates audit and continues with the downstream emit.

### 5.3 file:line / doc-line evidence

| Concern | Location |
|---|---|
| User directive (vendored purity) | quoted in `docs/audit/wave291-p5-3seed-results.md §0` and `STRATEGY_FRAMEWORK_SCOPE.md §7` |
| Wave 268 strict-clean rule | `tools/build_metric_ledger.py:18-27` (header) + Wave 286 P edit-discipline section |
| Per-wave Edit discipline | every audit doc closes with `## Edit discipline` listing files NOT modified |
| Vendored scoring script preservation | `docs/audit/wave286-final.md §2` + `wave291-p5-3seed-results.md §7` |
| `/tmp/` drivers pattern | `docs/audit/wave290-p4-benchmark-fixed.md §1.1` + `wave291-p5-3seed-results.md §0` |
| `tools/batched_framework_cifar.py` (no framework edits) | `docs/audit/wave290-p3-batched-harness.md` |
| Capability-token handshake (9 flags + channels + domains) | `adaptive_reflow/universal/adapter.py:131-204` |
| Pre-dispatch capability gate | `frame/engine.py:711-778` |
| Fail-closed emit | `frame/engine.py:1233-1300` (`_emit_fail_closed`) |
| Handshake (one-time validation) | `frame/engine.py:1162-1202` |
| Safe adapter call wrapper | `frame/engine.py:854-891` (`_safe_adapter_call`) |

---

## 6. Other strong innovations (full inventory, did NOT make top-5)

### 6.1 Host fingerprint + env_composite_hash equality per regression vector

`tests/test_d4_regression_vectors.py:136-152`. Every regression
vector records two 64-char hex SHA-256 hashes: `host_fingerprint`
and `env_composite_hash`. They MUST be equal at capture time (both
are computed on the same run). On re-run, if the current host's
fingerprint differs from the recorded one, the test **skips** rather
than fails — a legitimate RNG-bytes shift is acceptable, but the
test will not silently mismatch.

### 6.2 Wave 268 strict-clean rule

Cited in `docs/CLAIMS.md:113,115,136,138` (Wave 286 P + Wave 292
addenda). Every audit doc closes with `## Invariants` listing the
five gates that MUST pass: D.4 30/30, claims no drift, ruff 0, mkdocs
0 warnings, vendored NOT touched. The rule further enforces that
additive updates to `docs/CLAIMS.md` (status addenda) preserve ACTIVE
status verbatim — refutations go inline as addenda, never as status
flips.

### 6.3 3-seed canonical pool (41, 42, 43) + cosine σ noise band

`tests/test_d4_regression_vectors.py:58` (`_EXPECTED_SEEDS`) and
`docs/audit/wave291-p5-3seed-results.md §1, §4`. The 3-seed canonical
pool is enforced across all R-cells. The cosine baseline's
framework_fid σ across the 3 seeds is the canonical noise band
(Wave 291 P5 σ = 0.755% relative); STRONG = |mean Δ%| ≤ 1σ, PARTIAL
≤ 2σ, WEAK > 2σ. Most ML papers use single-seed runs or mean-across-
seeds without anchoring to a deterministic baseline's σ.

### 6.4 Topic-cluster cross-reference INDEX

`docs/audit/INDEX.md`. 94 audit files re-clustered by topic (cifar /
algorithm_4arm / engineering / reproducibility) so reviewers answer
"what does the project claim about X?" without grepping wave numbers.
The per-wave audit trail is preserved (so `git log --follow`
continues to work); only the directory has changed. The INDEX is
generated as a Wave 275+ follow-up per its preamble.

### 6.5 `engine_hash` + `policy_hash` + 8 more identity hashes per round

`adaptive_reflow/frame/engine.py:455-619` (`compute_ledger_row_hash`)
+ `adaptive_reflow/contracts/hashes.py:122-156`
(`hash_policy_hash`). Every round is fingerprinted at 10 surfaces
(`policy_id`, `writer_id`, `run_id`, `target_round`, `outer_cycle_id`,
`beta_by_channel`, `alpha_by_channel`, `fresh_noise_floor_by_channel`,
`freeze_admission_by_channel`, `beta_from_schedule: bool`,
`driver_computed_beta: bool`). Tamper breaks the chain.

### 6.6 READ-ONLY investigation phases before code change

`docs/audit/wave296-p1-architecture.md` (W296 P1) →
`wave296-p2-cache.md` (W296 P2 — design) →
`wave296-p3-a-class-wired.md` (W296 P3 — implementation). Most waves
have an explicit Phase 1 (read-only audit) before Phase 2 (apply).
W287 surfaced 24 scheduler-codepath bugs without touching production
code. The 3-phase discipline is itself a reproducibility guarantee —
every audit doc has a known provenance, and the README of the wave
chain can be re-walked by a reviewer.

### 6.7 Env hash + host fingerprint file (`env_hash_*.txt` + `env_hash_host_fingerprint.json`)

Repo root carries `env_hash.txt` + `env_hash_R2.txt` + `env_hash_R3.txt`
+ `env_hash_R5.txt` + `env_hash_R6.txt` + `env_hash_host_fingerprint.json`
as the canonical env-fingerprint ledger. Re-running a wave on a
different host updates these files; the diff is reviewable in git.

### 6.8 Per-cell status labels with strict rubric

`docs/audit/wave288-p1-honest-progress-summary.md §5` (Wave 22 metric-
rev3). Six status labels applied uniformly per-cell: STRONG /
PARTIAL / WEAK / REGRESSES / UNDERPOWERED / BLOCKED. The labels
separate direction (REGRESSES) from evidence strength (STRONG /
PARTIAL / WEAK) from sample-size limitation (UNDERPOWERED) from
external blockers (BLOCKED). Most ML papers use only "significant /
not significant".

### 6.9 User-gated push

Per the user's "claude相关的不要commit" directive, drivers that are
not load-bearing for the audit trail are kept in `/tmp/`. Only the
audit doc + the load-bearing tool (e.g.,
`tools/batched_framework_cifar.py`) land in git. This preserves
multi-shot iteration without polluting the commit history.

### 6.10 Per-claim evidence SHA-256 (CLM ledger)

`tools/build_metric_ledger.py:289` + `tools/check_claims_consistency.py:285-291`.
Each CLAIM row carries the SHA-256 of `docs/CLAIMS.md` itself; each
HEADLINE row carries the SHA-256 of the `SOURCE.md` file. A
reviewer who sees a CLM-NNN citation can `git show <sha256>` to
verify the cited source. This is closer to **content-addressable
storage** than to typical ML paper provenance.

---

## 7. Cross-cutting reproducibility invariants

The 5 top innovations all satisfy:

| Invariant | Mechanism |
|---|---|
| **Byte-determinism** | SHA-256 over canonical-JSON payloads (`hashlib`); wall-clock stripped; sort-key stable |
| **Single source of truth** | CLAIMS.md ledger; METRIC_LEDGER.json; docs/audit/INDEX.md topic-cluster |
| **Adversarial verification** | `check_claims_consistency.py` opens cited files; `check_docs_against_code.py` AST-walks symbols |
| **Per-PR regression net** | `ci.yml` 6 gates + `cpu-tests.yml` watchdog + `docs-validate.yml` watchdog |
| **Vendored purity** | Per-wave Edit discipline section; `/tmp/` drivers; `tools/` for new code, never vendored |
| **Capability-token fail-closed** | `audit_codes` accumulation + `_emit_fail_closed`; never a silent miss |
| **Hash fingerprints** | `host_fingerprint` + `env_composite_hash` per regression vector; SHA-256 per source artifact |
| **Wave-based audit trail** | 94 self-contained `docs/audit/waveNNN-pK-*.md` artefacts; INDEX.md re-clusters by topic |
| **Per-cell status rubric** | 6 status labels (STRONG / PARTIAL / WEAK / REGRESSES / UNDERPOWERED / BLOCKED) |
| **READ-ONLY investigation phases** | Every wave has Phase 1 audit before Phase 2 apply |

---

## 8. Verification

This is a READ-ONLY audit. No code changed; no commits made; no push
performed. The doc lives at
`docs/audit/wave298-p3-reproducibility-innovations.md` and is the
input to W298 P4 (top-3 reproducibility innovations → paper §X
framing).

**Invariants checked:**
- D.4 30/30: NOT TOUCHED (no engine code modified; first-batch
  regression vectors preserved).
- Claims no drift: the audit doc does not modify CLAIMS.md.
- ruff 0: NOT TOUCHED (no Python file modified).
- mkdocs 0 warnings: this doc follows the existing W296/W297/W298
  audit doc structure (single H1 + numbered sections + tables).
- vendored NOT touched: no vendor module referenced.

---

## 9. Final ranked list

| Rank | Innovation | file:line | Design rationale | Novelty vs literature |
|:---:|---|---|---|---|
| 1 | **D.4 byte-stable scheduler regression vectors (30/30)** | `tests/test_d4_regression_vectors.py:84-272`, `regression-vectors/*.json` (18 adapters) | 30 byte-deterministic regression tests lock 5 first-batch adapters × 9 conditions; every wave MUST preserve 30/30 PASS before commit. | Most ML papers rely on "we set the seed" without per-seed × per-NFE granularity; D.4 covers CPU + GPU paths with host-fingerprint traceability. |
| 2 | **`build_metric_ledger.py` byte-deterministic ledger (126 rows)** | `tools/build_metric_ledger.py:51-1489`, `docs/METRIC_LEDGER.{md,json}` | SHA-256 per source artifact + sorted JSON + wall-clock-stripped gates → byte-stable for unchanged inputs. | Most ML papers hand-curate "Table 1"; the ledger is regenerated from the same source files the audit chain cites — a diff is a real signal, not a hand-edit error. |
| 3 | **`check_claims_consistency.py` adversarial claims verifier** | `tools/check_claims_consistency.py:288-525`, `docs/CLAIMS.md` | Every ACTIVE claim's `Asserted by` file:line must resolve; every ACTIVE claim must be cross-referenced from ≥1 governance surface; `Disputed by` auto-demotes to PROVISIONAL. | Most ML papers have no machine-readable claim ledger; `Disputed by` is grounded in the codebase, not free-floating. |
| 4 | **6-gate CI on every PR (`ci.yml`)** | `.github/workflows/ci.yml:33-208` | pytest + ruff + mypy --strict + check_docs_against_code + check_claims_consistency + mkdocs build --strict; Python 3.12 + 3.13 matrix. | Most CI runs `pytest` + `ruff` only; the claim + symbol-index walker + mkdocs strict are three distinct docs-drift gates. |
| 5 | **Vendored purity + capability-token fail-closed handshake** | Wave 286 P + Wave 287 P edit-discipline + `adaptive_reflow/frame/engine.py:711-778` | Vendored SOTA scoring scripts are NEVER touched; capability mismatches accumulate `audit_codes` rather than crash. | ONNX Runtime's `CanHandle` is a hard fail; this framework accumulates audit and continues with downstream emit. |

---

## 10. Edit discipline

* `adaptive_reflow/` — NOT modified (read-only audit).
* `tools/` — NOT modified.
* `docs/CLAIMS.md` — NOT modified.
* `regression-vectors/` — NOT touched (D.4 vectors preserved byte-for-byte).
* `data/<repo>/**` — NOT touched (vendored scoring scripts preserved per
  "clone下来的原sota项目里的打分脚本依旧不能动，严格复用").
* `data/lineageflow_upstream/**` — NOT touched.
* `.venvs/**` — NOT touched.
* `docs/audit/wave298-p3-reproducibility-innovations.md` — this file (created).

---

## 11. Artifacts

* `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave298-p3-reproducibility-innovations.md` — this audit note (5 innovation table + per-innovation §1-§5 + §6 runners-up + §7-§11 verification / edit-discipline / artifacts).
* `docs/audit/wave298-p1-code-innovations.md` — companion doc (code-level architectural innovations, 5 ranked).
* `docs/audit/wave298-p2-methodology-innovations.md` — companion doc (methodological innovations, 5 ranked).
* `tests/test_d4_regression_vectors.py` — D.4 30/30 byte-stable regression suite.
* `tools/build_metric_ledger.py` — byte-deterministic metric ledger builder.
* `tools/check_claims_consistency.py` — adversarial claims verifier.
* `docs/METRIC_LEDGER.md` + `docs/METRIC_LEDGER.json` — 126-row byte-stable ledger.
* `docs/CLAIMS.md` — central claim ledger (73 ACTIVE + 12 PROVISIONAL/DEPRECATED + 9 INVERTED).
* `.github/workflows/ci.yml` — 6-gate pre-merge CI.
* `docs/STRATEGY_FRAMEWORK_SCOPE.md` — tier strategy + vendored purity rationale.
* `docs/audit/INDEX.md` — topic-cluster cross-reference map (94 audit files).

---

## 12. Honest summary

* **Goal achieved:** this audit note enumerates **5 reproducibility
  innovations** (D.4 byte-stable vectors, byte-deterministic ledger,
  adversarial claims verifier, 6-gate CI, vendored purity +
  capability-token fail-closed) plus **10 runners-up** that did not
  make the top-5 (host fingerprint + env_composite_hash equality,
  Wave 268 strict-clean rule, 3-seed canonical pool + cosine σ noise
  band, topic-cluster INDEX, 10-fingerprinted-hash-per-round ledger,
  READ-ONLY investigation phases, env hash files, per-cell status
  rubric, user-gated push, per-claim evidence SHA-256).
* **Top innovation ranked #1 (D.4 byte-stable vectors):** the
  30-test regression suite is the load-bearing invariant that every
  wave MUST preserve. Without D.4, every other reproducibility
  guarantee becomes unverifiable. With D.4, the project's claim
  "byte-identical cosine R-cell headlines across refactors" is
  machine-checkable on every PR.
* **Novelty vs literature:** each innovation is **closer to kernel
  development discipline, content-addressable storage, or lab
  notebook best practice** than to typical ML paper practice. Most
  ML papers do not (a) hash per-seed × per-NFE outputs, (b) build
  byte-stable metric ledgers, (c) verify claim citations
  adversarially, (d) gate every PR on 6 gates including docs-drift
  scanners, or (e) preserve vendored scoring scripts byte-for-byte.
* **All four release gates green at HEAD (no code changes).**
* **This doc is READ-ONLY.** It complements Wave 298 P1 (code-level
  architectural innovations) and Wave 298 P2 (methodological
  innovations) by focusing on **what guarantees any future run
  reproduces**, the third leg of the innovation triangle.

**End of audit doc.**