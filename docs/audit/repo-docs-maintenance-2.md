# Repository documentation maintenance — pass 2 (state pins + legacy labels)

**Date:** 2026-10-12
**Scope:** Continuation of `docs/audit/repo-docs-maintenance.md` on user request
("继续管理一下仓库文档并维护一下项目"). Two workstreams: (1) refresh the stale
repository-state pins in the primary surfaces, (2) label the remaining unlabelled
legacy artifacts (root-level ICLR-2027-era submission files + two venue drafts).
**Status:** COMPLETE. All gates green. **No manuscript artifact, metric, claim,
source module, or vendored-upstream file changed.**

---

## 1. Findings (observed facts)

| # | Finding | Evidence |
|---|---|---|
| F1 | **Stale state pins in the primary surfaces.** `todo/WAVES.md` and `todo/README.md` reported HEAD `8756f19` with **5** commits ahead of `origin/main`; `README.md` / `README.zh.md` said "Last updated 2026-10-11 … HEAD `061682c`". Actual: HEAD `a957906`, **7** ahead. | `git rev-list --count origin/main..HEAD` → `7`. |
| F2 | **Root-level legacy submission files unlabelled.** `cover_letter.md` (ICLR-2027 / NeurIPS-workshop era, last touched Wave 132), `submission_checklist.md` (ICLR-2027 era, Wave 97, 2026-09-10), and `supplementary.md` (NeurIPS/ICML-era template, Wave 97) sat at the repo root with no banner, and their names collide with the canonical `tnnls_submission/` files (which are different: e.g. root `cover_letter.md` 106 lines vs `tnnls_submission/cover_letter.md` 1234 lines). No current tooling reads them (`tools/render_cover_letter.py` targets `tnnls_submission/cover_letter.md`). | `grep -rn cover_letter.md tools/` → only `tnnls_submission/cover_letter.md`. |
| F3 | **Two venue drafts unlabelled.** `docs/paper-draft-anonymous.md` (workshop draft, 2026-09-05) and `docs/paper-final-neurips.md` (NeurIPS 2026 anonymous) carried no legacy banner. | File heads. |
| F4 | **`docs/README.md` verifier note stale.** It listed `k1_rc5` / `drift_33` without stating they now pass. | line 4. |

**Non-findings (verified clean / intentional):**
- No stale "remain red" / `NOT_READY` wording remains on any live surface.
- `pytest_final.txt` / `pytest_results.txt` (root, 2026-08-30) are **intentionally
  committed** historical pytest records — referenced by
  `docs/governance/04-test-ci-audit.md` as "the canonical recorded run". Left untouched.
- `docs/paper-draft.md` already carried a legacy banner (previous pass).

## 2. Changes (additive; no deletions)

**Workstream 1 — state-pin refresh (F1, F4).**
- `todo/WAVES.md` §1.1: HEAD → `a957906` (prior readings preserved); ahead → **7**.
- `todo/README.md`: HEAD/ahead refreshed; "latest audit" pointer → this pass; user-gated push count → 7.
- `README.md` / `README.zh.md`: "Last updated" line → 2026-10-12 / HEAD `a957906`.
- `docs/README.md` §4: the readiness-verifier note now states it passes **all** gates.

**Workstream 2 — legacy labels + inventory (F2, F3).**
- `cover_letter.md`, `submission_checklist.md`, `supplementary.md` (repo root): added
  a top **LEGACY** banner naming the canonical `tnnls_submission/` counterpart and
  stating no current tooling reads the file. Body unchanged.
- `docs/paper-draft-anonymous.md`, `docs/paper-final-neurips.md`: added a top **LEGACY
  DRAFT** banner pointing at `drafts/paper-A-final.md`. Body unchanged.
- `docs/README.md` §6: added a "Superseded top-level submission artifacts" bullet
  covering the three root files + the `eaai_submission/` archive.

## 3. Gate results (acceptance record)

| Gate | Command | Result |
|---|---|---|
| readiness verifier | `python tools/verify_submission_readiness.py` | **READY_WITH_SKIPS: mypy_0** (exit 0) |
| claims consistency | `python tools/check_claims_consistency.py` | **PASS** — no drift |
| docs-against-code | `python tools/check_docs_against_code.py` | **PASS** |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **PASS** |
| mkdocs strict | `mkdocs build --strict` | **PASS** — exit 0 |

### 3.1 Post-edit file digests

Recorded for provenance; the digests are the pre-commit working-tree values.

| File | SHA-256 |
|---|---|
| `todo/WAVES.md` | `aec131cf44946a4b51a0b7acdb4bfd65d5d5d0aaf58a2272b62bd6268080ddb9` |
| `todo/README.md` | `980f575086e3369407886148a5cb657810473e6e56a9e3d19e29888d852a4e77` |
| `README.md` | `ed07cf068f74b8525a28517a2918f9081fa3febaf2b7b92f2e79532444798ec2` |
| `README.zh.md` | `2df96f60041cf22a18aa1ef488c83dc08867530579e2792ec1161e8f433774a3` |
| `docs/README.md` | `d7672d3e3d11f0ba72389f6dff1a249824784df5ace6cf4db69594e5ff002930` |
| `cover_letter.md` | `71d9b83a024a0c90e28b0152a123304e7709c2ba6bc1056fd2ccb8fb53ec3782` |
| `submission_checklist.md` | `64d51aaa18dbdd7ee5fbb21c45d3472b740fc473ed04e425e5dbf6067fe40c3b` |
| `supplementary.md` | `d3cb7783269c566eba1df8c285401931ee973ead2f84a539847b66bca7a8d174` |
| `docs/paper-draft-anonymous.md` | `87e0e730612e13830bffa665f7f868434715d61c0c95e8a3c7edfd38fe2ee014` |
| `docs/paper-final-neurips.md` | `bf6ea519b85afb7ac11358db9777c227923fcd972db12559f960bab512b4951e` |

## 4. Unresolved gaps / caveats

- **Legacy artifacts are labelled, not deleted** (provenance rule). The root-level
  `cover_letter.md` / `submission_checklist.md` / `supplementary.md` and the
  `eaai_submission/` tree remain on disk.
- **Old per-wave bookkeeping** (`todo/STATUS.md`, `INDEX.md`, `GATES.md`, `LOOP.md`,
  `PUSH-READY.md`, `TIMELINE.md`, `RISK-REGISTER.md`, `decisions.md`,
  `lessons-learned.md`, `TPAMI-6-WEEK-PLAN.md`) is **retained verbatim** and still
  pins the older HEAD `fea137d` / "0 ahead" readings — intentionally historical; the
  primary surface is `todo/WAVES.md`.
