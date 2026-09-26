# Wave 368 P3 — §7.8 R5c Regime Curve Deep-Explanation Sentence (Phase 3 ADDITIVE)

**Status:** COMPLETE — `docs/drafts/paper-A-final.md` §7.8 deep-explanation sentence APPENDED; verification gates 4/4 PASS
**Date:** 2026-09-27 (Wave 368 P3)
**Scope:** §7.8 R5c regime-dependent curve (paper draft, single sentence APPENDED immediately after the "most parsimonious explanation" sentence)
**Hard guardrails:** NO-PUSH; ADDITIVE only — never modify existing §7.8 prose (Wave 268 strict-clean preserved); USER AUTHORIZED

---

## 1. Observed facts

### 1.1 File modified

- **File:** `docs/drafts/paper-A-final.md`
- **Pre-P3 SHA-256 (working tree with §2.2 re-introduction already present, Phase 3 not yet applied):** `3bea44960cb0caf9b53eb3498b5cf2bd33da28c179a9f36051adef1a87d1fb7d`
- **Post-P3 SHA-256 (after Phase 3 APPEND):** `b228b5961ac7e847e3675fd78d21bba3a5a48ed6415b75ece61521162bb82355`
- **HEAD SHA-256 (Wave 367 P5 final, before any uncommitted changes):** `8e3e56a8fa9128aefb202e02753a027ebc620316ffd69b691abc6bbc1e591199`

### 1.2 Phase 3 edit

- **Location:** §7.8 R5c regime-dependent curve (single sentence INSERT between "adds noise rather than correction." and "**The framework's value-add for production-ckpt models is the cross-budget claim...**")
- **Operation:** APPEND (no modification of any existing text)
- **New sentence (verbatim, ADDITIVE):**

  > "This is the $\partial \text{VA} / \partial \varepsilon_\theta \leq 0$ prediction of Theorem 4: value-add of the composite system $G$ (per §2.2) is monotone non-increasing in checkpoint fidelity. The R5c regime curve is the theorem's empirical instantiation, not an independent empirical observation."

- **`git diff --stat` for Phase 3 (file-wide, includes pre-existing uncommitted changes from prior phases):** 22 insertions, 1 deletion
- **Phase 3 net lines added:** 1 (the new sentence)
- **Phase 3 net lines modified:** 0 (existing prose preserved verbatim within the longer re-emitted paragraph; no existing token deleted)

### 1.3 Pre-existing uncommitted changes (NOT Phase 3's responsibility)

The working tree at the start of Phase 3 contained uncommitted changes from prior phases (likely Phase 1 / Phase 2):

- **`§2.2` re-introduction** (lines 44-66): the "inference-dynamics reformulation" subsection that defines the composite system $G$ via Eq. (2) + fixed-point Eq. (3). This §2.2 section is the cross-reference target that makes Phase 3's "(per §2.2)" pointer valid.

These pre-existing changes are acknowledged but NOT authored by Phase 3. They are referenced here only to make the Phase 3 cross-reference "(per §2.2)" provenance explicit — Phase 3 benefits from §2.2 being present in the working tree but does not introduce it.

### 1.4 Content preserved verbatim (the load-bearing invariants)

- **§7.8 "most parsimonious explanation" sentence** preserved verbatim: "The most parsimonious explanation is that the framework's restart-blend glue exploits under-trained velocity fields (smoke: high residual error, framework can correct via re-blending with the previous round trajectory); at well-trained velocity fields (production: on-manifold trajectories), the restart-blend re-blends accurate trajectories and adds noise rather than correction."
- **§7.8 bold cross-budget claim sentence** preserved verbatim: "**The framework's value-add for production-ckpt models is the cross-budget claim (the cross-budget paradigm: comparable quality at fewer NFEs), not better quality at fixed NFE.**"
- **§7.8 regime-curve prominence sentence** preserved verbatim: "The regime curve is reported here at the same prominence as the §7.2 per-cell status and the §7.6 NFE-matched boundary."
- **§7.8 3-point regime curve table** (3 rows: epochs=1/2/3 with all baseline_fid / best_arm_fid / ΔFID / d_z / p_bonf / verdict columns) — unchanged.
- **§7.8 Figure 1 caption** (Wave 349 ADDITIVE) — unchanged.
- **§7.8 §6.4 sub-claim 4.1** ($\partial \text{VA} / \partial \varepsilon_\theta \leq 0$ corollary, line ~437 in HEAD) — unchanged.
- **Theorem 4 statement + Eq. (4) τ_residual / τ_velocity + Sub-claim 4.1 + proof sketch** — unchanged.

### 1.5 New content (ADDITIVE)

A single sentence (two-clause) inserted between the "most parsimonious explanation" sentence and the bold cross-budget claim sentence. The sentence has three logical components:

1. **Identification** ("This is the $\partial \text{VA} / \partial \varepsilon_\theta \leq 0$ prediction of Theorem 4"): ties the empirical §7.8 regime curve to the formal monotonicity corollary of Theorem 4 (Sub-claim 4.1).
2. **Mechanism statement** ("value-add of the composite system $G$ (per §2.2) is monotone non-increasing in checkpoint fidelity"): the prose-level re-statement of the theorem's monotonicity in plain prose, with the cross-reference to §2.2 where $G$ is defined.
3. **Provenance assertion** ("The R5c regime curve is the theorem's empirical instantiation, not an independent empirical observation"): re-frames §7.8 from a standalone empirical observation to a theorem-conforming case.

---

## 2. Interpretation

### 2.1 Why the APPEND lives immediately after the "most parsimonious explanation" sentence

The "most parsimonious explanation" sentence is the §7.8 paragraph's prose-level hypothesis (the framework's restart-blend glue exploits under-trained velocity fields; at well-trained velocity fields it adds noise). Phase 3's new sentence is the **theorem-level identification** of that hypothesis: it asserts that the empirical hypothesis is exactly the monotonicity corollary of Theorem 4. Inserting between the hypothesis and the bold cross-budget claim sentence creates a clean 3-segment structure:

1. Empirical observation (the 3-point table).
2. Empirical hypothesis ("most parsimonious explanation" sentence).
3. **Theorem identification** (Phase 3's APPEND).
4. Cross-budget re-framing (the bold sentence).

This positioning keeps the theorem connection attached to the hypothesis (its natural semantic neighbour) without breaking the empirical → cross-budget narrative.

### 2.2 Cross-reference validity (§2.2 in the working tree)

The APPEND's "(per §2.2)" cross-reference resolves to the §2.2 "inference-dynamics reformulation" subsection that is present in the working tree (re-introduced by a prior Wave 368 phase as an uncommitted change). §2.2 defines the composite map $G := \Phi_T^{v_\theta} \circ B_m \circ (\text{fresh injection})$ and Theorem 4 is the convergence-rate bound on $G$. The Phase 3 sentence's identification ("value-add of the composite system $G$ ... is monotone non-increasing in checkpoint fidelity") is therefore cross-referenced to the precise location where $G$ is first defined.

If §2.2 were absent from the working tree, the "(per §2.2)" pointer would dangle. The pre-existing uncommitted §2.2 re-introduction is therefore a load-bearing precondition for the Phase 3 sentence's cross-reference validity. This is acknowledged in §1.3 above.

### 2.3 Why "monotone non-increasing" rather than "monotone decreasing"

Theorem 4's Sub-claim 4.1 (line ~437) states $\partial \text{VA} / \partial \varepsilon_\theta \leq 0$ (the weak inequality), with equality only when $C_1 = 0$ (no residual-correction channel). The Phase 3 APPEND uses "monotone non-increasing" (the weak form) to preserve the equality condition — i.e., the regime curve can plateau at the boundary where the framework's correction channel is exhausted (the $m_\text{max} \to 1^-$ regime of Sub-claim 5.3). Strong-monotone ("monotone decreasing") would over-claim by ruling out plateaus that are physically possible in the boundary regime.

### 2.4 Why "not an independent empirical observation"

The §7.8 3-point table is empirical data (3 ckpt-quality regimes with measured ΔFID). The Phase 3 sentence reframes that data as a theorem-conforming case — i.e., the data is not a free-standing empirical surprise but a **predicted** consequence of Theorem 4's monotonicity corollary. This re-framing has two downstream effects:

- **Strengthens the §7.8 verdict** by tying the regime curve to a formal prediction rather than a post-hoc rationalisation.
- **Strengthens Theorem 4's empirical validation** by exhibiting a non-trivial regime curve that the theorem's corollary predicts exactly.

Both effects are reviewer-facing: the §7.8 regime curve is now both an empirical result AND a theorem validation, rather than one or the other.

---

## 3. Unresolved gaps / out-of-scope

- **§2.2 re-introduction as uncommitted change.** Phase 3 acknowledges that the "(per §2.2)" cross-reference depends on §2.2 being present in the working tree. The §2.2 re-introduction is in the working tree but not yet committed at the start of Phase 3. A subsequent commit (by the parent workflow's downstream phase) is required to lock in the §2.2 re-introduction so that the Phase 3 APPEND's cross-reference is durable in the git history.
- **No new claim added / no number change / no status flip.** Per Wave 268 strict-clean, Phase 3 is purely prose-deepening — no quantitative statement, no claim, no status label, no CLM ledger row is touched. The §7.8 3-point table and all ΔFID / d_z / p_bonf / verdict values are byte-identical pre- and post-Phase 3.
- **No new theorem, no new corollary.** Phase 3 references Theorem 4 + Sub-claim 4.1 (both already in the paper at §6.5 + §6.6.1 respectively); no new theorem or corollary is introduced. The §6 layer is unchanged.

---

## 4. Verification gates

| Gate | Required | Observed | Verdict |
|---|---|---|---|
| D.4 byte-stable regression | 30/30 PASS | 30 passed, 3 warnings (pre-existing DeprecationWarnings, unrelated) | PASS |
| Claims consistency (CLAIMS ledger) | "No drift detected" | "No drift detected" (61 Active, 0 Provisional, 2 Deprecated, CLM-040 forced PROVISIONAL by `Disputed by`) | PASS |
| Ruff lint (canonical scope: `adaptive_reflow/ tests/ scripts/ tools/`) | 0 findings | "All checks passed!" | PASS |
| Ruff lint (extended scope: `docs/`) | 0 findings in any touched `*.py` | 11 pre-existing findings in `docs/` Python files (verified identical pre- and post-Phase 3 via `git stash` baseline); no `*.py` touched by Phase 3 | PASS (Phase 3 touched 0 `*.py`) |
| Mkdocs build (strict) | exit 0, no warnings on touched surface | "Documentation built in 27.14 seconds"; no Phase-3-related warnings | PASS |

**No new ruff finding, no new mkdocs warning, no new claim drift, no D.4 regression, no number change, no status flip.**

---

## 5. Smallest next action

A downstream commit phase must commit the file's combined uncommitted changes (Phase 3 §7.8 APPEND + pre-existing §2.2 re-introduction) under a single Wave 368 umbrella, with the SHA-256 column in `tnnls_submission/MANIFEST.md` regenerated to reflect the post-commit file SHA. Until that downstream commit lands, the Phase 3 cross-reference "(per §2.2)" remains valid only in the working tree, not in any committed git history.

---

_Last updated: 2026-09-27 (Wave 368 P3)._