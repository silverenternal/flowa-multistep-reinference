# Wave 279 — User Decisions Awaiting

**Date:** 2026-09-22
**Branch:** main (12 commits ahead of `origin/main`)
**Companion doc:** `docs/audit/wave279-plan-complete.md`
**Scope:** Items the user must decide before the next workflow run.

This doc captures **only the items that need user input**. All other
deliverables from the Wave 275-278 chain are landed and verified.

---

## 1. Push to `origin/main`

**Status:** READY (no decision, just go).

```
git status                                  # clean
git log origin/main..HEAD --oneline | wc -l   # 12
ruff check adaptive_reflow/ tests/ scripts/ tools/   # 0 findings
pytest tests/test_d4_regression_vectors.py -q       # 30/30 PASS
mkdocs build --strict                                # 0 warnings
python3 tools/check_claims_consistency.py            # No drift
python3 tools/build_metric_ledger.py                 # EXIT=0, byte-deterministic
```

**Action:** `git push origin main`.

The user explicitly delegated the push to "ultracode-driven workflow"
at the close of Wave 278 — this is the trigger to execute it.

---

## 2. GPU sweeps for the 9 weak-metric implementations

**Status:** CODE LANDED, VERIFY RE-RUNS DEFERRED.

The Wave 276 / 277 weak-metric adapter improvements landed as code
(see `docs/audit/wave279-plan-complete.md` §2.2 for the 9-of-9 list),
but the GPU validation runs that would turn "code-IMPLEMENTED" into
"empirically re-verified" are out-of-scope for the Wave 275-278 chain
(CPU-only mandate). These runs are ready to fire the next time a GPU
session is available:

| # | Weak claim | Adapter | GPU verify run | Approx. budget |
|---|---|---|---|---|
| 1 | R5c | MNIST | Re-materialize the MNIST FM production ckpt (`tools/materialize_mnist_fm.py`) and re-run the STATISTICAL N=60000 sweep | ~30 min on a single GPU |
| 2 | K3 + R5b | CIFAR-10 RF | Re-run `tools/run_sota_cifar_experiment.py --cosine-ramp-strength 0.5` on CIFAR-10 v5 with the new `--cosine-ramp-strength` CLI flag (N=500 matched-NFE) | ~3-4 hr on PRO 6000 |
| 3 | K1 + R3 | FlowMol3 | Re-run FlowMol3 N=1000 with the new `validity_mode=pb_energy=False` + `_rdkit_bridge_validity` helper + `repeat_interleave` tile in `_solve_ode_upstream_batch`; 3-seed sweep | ~6 hr on 5090 |
| 4 | K7 | LineageFlow | Re-run LineageFlow N=1000 with `restrict_novelty_to_target_db` flag set + tempdir placeholder active | ~2 hr on 5090 |
| 5 | K4 + K5 | LineageFlow | Re-run the LineageFlow sweep with the length-bias re-weight + uniform AA prior composition | ~2 hr on 5090 |
| 6 | R6 | k6 foldability | Re-run the k6 foldability sweep with `--tier-aware-n-cap` | ~10 min (CPU) |

**Decision needed:** schedule a `gpu-experiment-wave5` (or successor)
skill run to validate. **NOT blocking the push** — the code is correct
and ruff-clean; the GPU runs are pure confirmation.

---

## 3. TNNLS submission

**Status:** OUT OF SCOPE per user explicit instruction ("投稿相关的先不用管").

User said: "投稿相关的先不用管，先把项目内部指标严格追溯，治理好...".
The TNNLS submission package (`tnnls_submission/`) is NOT touched by
Waves 275-278.

Pre-existing pending TNNLS items (from Wave 274 P3 + P4):

- **Cover letter `FILL_GUIDE.md`** — placeholders enumerated; user must
  fill them in before submission.
- **`paper-tnnls.pdf` IEEEtran rebuild** — BLOCKED on Wave 274 P4 due
  to network restriction blocking `latexmk` package download. Either
  (a) ship the existing PDF (compiled from an older IEEEtran), or (b)
  pre-fetch the IEEEtran class on a network-enabled machine and
  rebuild.
- **v3.0-tnnls-ready tag** — to be cut at submission time.

**Decision needed:** when the user is ready to resume the submission,
schedule a separate workflow (the natural successor to the Wave 275-278
chain) that handles cover letter fill-in + IEEEtran rebuild + tag cut.

---

## 4. ruff 0 (no decision)

**Status:** ACHIEVED (no user action needed).

Wave 276 branch A landed 12 mechanical ruff fixes. All 5 release gates
green. Listed for completeness only.

---

## 5. Zenodo DOI + v3.0-tnnls-ready tag

**Status:** POST-SUBMISSION scope.

Per Wave 269 P2: Zenodo `TBD` removal was applied to the README. The
DOI assignment + tag cut happen at submission time.

**Decision needed:** none now; this becomes an item in the post-TNNLS
workflow.

---

## 6. Items NOT requiring a decision (FYI)

These are the items that were discussed and resolved within the
Wave 275-278 chain itself:

- **Flatten "看不到 wave 信息" success criterion** — achieved at
  navigation surface (`mkdocs nav` = 0 Wave-N entries; INDEX.md
  topic-cluster only); the ~47 `waveNNN-` references remaining in
  CLAIMS.md / CONSOLIDATED_RESULTS.md are PROVENANCE pointers per
  Wave 268 strict-clean + Wave 275 P3 §3, deliberately preserved.
- **Vendored-code invariant** — 0 vendored files modified across
  Waves 275-278, per CLM-077 / Wave 262 P1.
- **D.4 byte-stable regression vectors** — 30/30 PASS preserved.
- **Weak-claim env-block (K6)** — documented but not code-fixable
  until `sm_120` torch is available. Out of Wave 275-278 scope.
- **Weak-claim out-of-scope (R1)** — vendored metric redefinition
  required, explicitly out of scope per Wave 275 P1 §4.3.

---

## 7. Recommended next-step workflow

If the user wants to continue the chain, the natural next-step is
`gpu-experiment-wave5` (or successor) for the GPU verify runs in §2.
If the user wants to push and move on, `git push origin main` is the
single trigger. If the user wants to resume submission, a new
`submission-prep-wave-N` workflow that picks up from Wave 274 P3+P4
state.

**No single right answer — these are user-direction items.**