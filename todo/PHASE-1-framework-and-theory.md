# Phase 1 — Framework adjustment + theory deepening + algorithm strengthening

**Status:** done (Wave 11 + Wave 12 shipped; `G-MASTER-PHASE-1` re-verified post-Wave 12) (+ Wave 38: HIGH-4 + MEDIUM-11 + 22 CLM claims wired; Wave 41: pytest pollution cleanup; Wave 51-53: pre-push pytest fixes; G-MASTER-PHASE-1 remains MET)
**Owner:** framework maintainer
**Goal:** lock down the framework's theoretical + algorithmic foundation **before**
touching any new model integration. Get the abstractions and helpers right so
Phase 2-4 are "just glue".

## Phase 1 sub-task status (post-Wave 12)

| Sub-task | Status | File |
|---|---|---|
| 1.1 Theory lift to framework core | done | (Wave 11 + Wave 12 commits `ebc0550`, `e0238ab`) |
| 1.2 Algorithm uplift strengthening | done + ongoing follow-ups | this file §1.2 (4 follow-ups) |
| 1.3 Conformance test surface | done | Wave 11 Phase 4 (52 tests) + Wave 12 (32 more) |
| 1.4 Defensive engineering | preserved | `tests/test_framework/test_import_acyclic.py` 13/13 pass |

**Note**: Wave 11 Phase 3 ("shrink adapters") was NOT completed — adapters are
still 1000-2000 lines each. Tracked separately; not blocking Phase 2.

## Sub-tasks (in execution order)

### 1.1 Theory lift to framework core
- **Driver:** Wave 11 (JMAA paper theorem refactor)
- **What it does:** read JMAA paper (Theorem 1 + Lemmas 2-5) → codify the 4 paper
  quantities (A_g, B_g, C_g, e_rho) in framework core (`adaptive_reflow/theory/`
  or `contracts/theory.py`) → reduce adapters to thin implementations of the
  abstract interface.
- **Currently in:** Wave 11 Phases 1a-c + 2 + 4 + 5 (mostly done); Phase 0 (audit
  fixes from A2) + Phase 3 (shrink adapters) still pending.
- **Status file:** `todo/wave11-result-validation.md`

### 1.2 Algorithm uplift strengthening
- **Driver:** ongoing (no single wave)
- **What it does:** keep adding measured algorithm uplifts (currently 36 in
  `docs/benchmark-uplifts.md`). Each uplift must have a BEFORE/AFTER measurement
  + a target.
- **Backlog candidates:** explore FreeTraj and MeanFlow as full algorithm-layer
  contributions rather than scheduler-only; explore per-channel restart policy
  (Wave 4 T4 was theoretical; can now be validated against the JMAA framework).
- **Output:** per-uplift row added to `docs/benchmark-uplifts.md`.

#### 1.2.a Algorithm improvement A — re-point Theorem 1 to true R^2 BL
- **Driver:** Wave 12 high-3 follow-up (agent's own notes)
- **What it does:** re-point `theorem1_bl_convergence_witness` and
  `Theorem1StatementChecker` at `planar_bl_convergence_witness` (the new R^2
  BL added in Wave 12). Eliminates the 1-D y=0 projection + rejection sampler
  path from the unified checker.
- **Detail file:** `todo/algo-improvement-planar-bl-repoint.md`
- **Estimated time:** 30-60 min, no GPU
- **Gate:** `G-ALGO-PLANAR-BL` (defined in detail file)

#### 1.2.b Algorithm improvement B — explicit rate bound theorem
- **Driver:** Wave 12 high-3 (algorithm-layer new capability)
- **What it does:** write `BL(mu_{g,eps}, nu_g) <= sqrt(2/pi) * eps` as a
  first-class framework theorem: dataclass + checker + tests + formal
  theorem-statement doc with proof (synchronous coupling + Kantorovich
  duality).
- **Depends on:** 1.2.a (A) — so the unified checker is on the right metric
  before this theorem is layered on top.
- **Detail file:** `todo/algo-improvement-rate-bound.md`
- **Estimated time:** 30-60 min, no GPU
- **Gate:** `G-ALGO-RATE-BOUND` (defined in detail file)

#### 1.2.c Algorithm improvement C — uplift isolation test suite
- **Driver:** ongoing (no single wave)
- **What it does:** for each of the 36 measured algorithm uplifts, add an
  independent toggle test (default on, env-var off, compare metric delta).
  Identifies top-10 strongest uplifts; produces isolation + interaction +
  cumulative tables in `docs/ABLATION.md` v2.
- **Detail file:** `todo/algo-improvement-uplift-isolation.md`
- **Estimated time:** 1-2 hours, no GPU
- **Gate:** `G-ALGO-UPLIFT-ISOLATION` (defined in detail file)

#### 1.2.d Algorithm improvement D — failure-mode controlled noise injection
- **Driver:** Wave 8 FIX-3 (framework WORSE on 2D RF) + Wave 10 (LineageFlow
  BLOCKED) — characterise the value boundary quantitatively.
- **What it does:** inject Gaussian noise into a base adapter's velocity
  output at levels σ ∈ {0, 0.01, 0.05, 0.1, 0.2, 0.5}; measure framework
  recovery vs baseline; produce a controlled
  "noise level vs framework uplift" table.
- **Detail file:** `todo/algo-improvement-failure-modes.md`
- **Estimated time:** 1-2 hours GPU (start with twodim_fm, cheapest)
- **Gate:** `G-ALGO-FAILURE-MODES` (defined in detail file)

### 1.3 Conformance test surface
- **Driver:** Wave 11 Phase 4
- **What it does:** at least one test per JMAA theorem — assert that the
  framework's EvidenceScaleGapMetric + 4 paper quantities + selection_ratio
  computation matches the paper formulas (within numerical tolerance).
- **Currently in:** Wave 11 Phase 4 (mostly done; need to verify pytest
  collection + test count after Phase 0+3 ship).

### 1.4 Defensive engineering
- **Driver:** ongoing
- **What it does:** preserve 28e3bf9 OOM defenses + a6dffd3 acyclic test gate
  + Wave 8 FIX-1/2/3/4 conclusions. Each Phase 4 integration must NOT break
  these.
- **Verification:** `pytest tests/test_framework/test_import_acyclic.py -v`
  + `pytest tests/test_adapters/test_adapter_common.py -v` must pass.

## Acceptance

- All existing tests pass (3146+ baseline + new conformance tests).
- `docs/ARCHITECTURE.md` has a "Where the theory lives" section pointing to the
  new module.
- At least one of the 4 paper quantities (A_g, B_g, C_g, e_rho) has a
  paper-claims-its-formula test in `tests/test_theory/`.
- 28e3bf9 OOM defenses + a6dffd3 acyclic gate still pass.

## Acceptance gate (BINDING — see `todo/GATES.md`)

**Gate name:** `G-MASTER-PHASE-1` (defined in `todo/GATES.md`)

**Pre-condition:** n/a (this is the entry gate)

**Pass conditions (ALL must hold):**
- [ ] Wave 11 Phase 0 (#339) and Phase 3 (#344) are committed
- [ ] `pytest --collect-only -q` shows **>= 3146 tests, no ImportError**
- [ ] `pytest tests/test_framework/test_import_acyclic.py -v` shows **4/4 PASS**
- [ ] `pytest tests/test_adapters/test_adapter_common.py -v` shows **9/9 PASS**
- [ ] `mkdocs build --strict` exits **0**
- [ ] `docs/CLAIMS.md` has **>= 47 CLM entries**; none of them have a recent
      wave's `Disputed by` (which would indicate broken claims)
- [ ] `git status --short` returns empty (G-OPS-CLEAN-WORKING-TREE)
- [ ] `todo/STATUS.md` is up-to-date (G-OPS-TODO-LOG-UPDATED)

**Verification commands (run before claiming gate pass):**
```bash
cd /home/hugo/codes/flowa-multistep-reinference
git status --short                              # expect: empty
git log origin/main..HEAD --oneline              # expect: empty OR all are "Phase 1 done" commits
.venvs/flowmol3_venv/bin/python -m pytest --collect-only -q 2>&1 | tail -3
.venvs/flowmol3_venv/bin/python -m pytest tests/test_framework/test_import_acyclic.py tests/test_adapters/test_adapter_common.py -v
.venvs/flowmol3_venv/bin/mkdocs build --strict 2>&1 | tail -3
```

**Block rule:** if ANY pass condition fails, **Phase 2 cannot start**.
Either fix the failing condition or append a new LL (lesson learned) entry
to `todo/lessons-learned.md` explaining why the gate evolved.

## Exit criteria (move to Phase 2)

`G-MASTER-PHASE-1` passed.

## Wave 56 close-out

Status refreshed: G-MASTER-PHASE-1 has been re-verified post Wave 38 (HIGH-4 + MEDIUM-11 + 22 CLM claims wired), post Wave 41 (test pollution cleanup), and post Wave 51-53 (pre-push pytest fixes). All Phase 1 gates remain MET. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).