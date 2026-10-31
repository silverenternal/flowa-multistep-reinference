# Reader-facing dead pointers: 34 addresses, 13 pages, 4 causes

**Date:** 2026-10-31
**Surface:** the pages the mkdocs navigation puts in front of a reviewer
**Gate:** `tools/check_reviewer_pointers.py` (chain entry 19), scope extended here
**No metric, claim, status label or number was changed.**

## 1. What was measured

`check_reviewer_pointers.py` resolves every backticked repository path in a
fixed set of documents. Before this pass that set was five files — `README.md`,
`README.zh.md`, `AGENTS.md`, `docs/README.md`, `docs/PAPER-EVIDENCE.md` — plus
`tnnls_submission/*.md`: 638 tokens, 0 dead.

The seven model cards and the reference pages (`ARCHITECTURE`, `environments`,
`configs`, `adapter-dependencies`, `DEPRECATION`, `PLUG_IN_YOUR_MODEL`,
`GATES`, `code-release-checklist`) sit in the same navigation and were never
checked. Running the same resolver over them reports **32 dead pointers**, and
two more are invisible to it because the token is not the first thing after a
backtick:

```
$ git stash push -- docs/ AGENTS.md    # pre-fix tree, extended gate
$ python3 tools/check_reviewer_pointers.py
checked=1027 dead=32
```

## 2. What was found — four causes

**(a) Audit records renamed by the topic-cluster flatten (8).** Commit
`3f0e7e35` ("flatten-finish — rename 24 waveNNN- files in topic clusters")
dropped the `waveNNN-` prefix; the text refs it updated did not include these
pages.

| cited | actual |
|---|---|
| `docs/audit/wave149-close.md` | `docs/audit/final_verify/close.md` |
| `docs/audit/wave201-p2-foldability-sc-workers-per-gpu.md` | `docs/audit/sweep_eval/p2-foldability-sc-workers-per-gpu.md` |
| `docs/audit/wave201-p3-run-foldability-propagate-workers-per-gpu.md` | `docs/audit/sweep_eval/p3-run-foldability-propagate-workers-per-gpu.md` |
| `docs/audit/wave111-b-config-scattering-audit.md` | `docs/audit/sweep_eval/b-config-scattering-audit.md` |
| `docs/audit/wave111-data-linkage-plan.md` | `docs/audit/data_packaging/data-linkage-plan.md` |
| `docs/audit/wave111-data-linkage-closure.md` | `docs/audit/data_packaging/data-linkage-closure.md` |
| `docs/audit/wave89-phase1-final.md` | `docs/ARCHIVE/audit-waves-1-99/wave89-phase1-final.md` |
| `docs/audit/wave131-pre-freeze-hygiene.md` | `docs/headline-evidence/byte_reproducibility_evidence/wave131-pre-freeze-hygiene.md` |

**(b) Files that were never committed in any branch (10).** Not renames — the
path has no history at all:

```
$ git log --all --oneline --diff-filter=A -- <path>
(no output)

tools/run_sota_self_flow_experiment.py          cited 5x
tools/run_sota_lineageflow_experiment.py        cited 1x
tools/check_deprecation_policy.py               cited 2x
scripts/run_kanzi_n1000_framework_inv_proj_seed42.sh   cited 1x (invisible to the gate)
docs/audit/wave48-pytest-pre-push-fixes.md      cited 1x (gone, not moved)
```

Three of them were described as existing and runnable. The self-flow card said
the harness "exits with `75` `EX_TEMPFAIL`" in four places; the release
checklist told a reviewer to `bash` the Kanzi wrapper; `DEPRECATION.md`
described its checker's output field by field and said the tool "exits
non-zero on FAIL so the per-wave verify step can wire the J.2 gate into CI".
A reviewer following any of the three gets "No such file" — the same failure
mode as the six commands in `docs/audit/repro-command-audit.md`.

**(c) An archived document (11).** `docs/paper-draft.md` was archived to
`docs/ARCHIVE/legacy-paper/paper-draft.md` on 2026-08-28. Ten citations to it
survive across the five model cards that carry a §4 record, plus one in
`PLUG_IN_YOUR_MODEL.md` to `docs/paper-plan.md` (now
`docs/ARCHIVE/top-level/paper-plan.md`). Repointed rather than dropped: the
legacy draft is where the per-model record actually is, and the live
manuscript (`docs/drafts/paper-A-final.md`) has no per-model §4 — its §4 is
the scheduler family. Pointing the cards at the live paper would have asserted
a section that does not exist.

**(d) Three path errors that never resolved.**

| page | said | is |
|---|---|---|
| `docs/environments.md:26` | `adaptive_reflow/algorithm/scheduler.py` | `adaptive_reflow/algorithm/scheduler/` (a package) |
| `docs/environments.md:369` | `data/FlowMol3/repo/flowmol/train.py` | `data/FlowMol3/repo/train.py` |
| `docs/adapter-dependencies.md:167` | shim injects `tools/flowmol/`; deps in `tools/flowmol/requirements.txt` | shim injects `data/FlowMol3/repo` (`FLOWMOL3_UPSTREAM_REPO`); the tree carries `environment.yml` |
| `docs/ARCHITECTURE.md:1643` | `scripts/wave242_p1_flowmol3_rescue_single_mol.py` wrapper | no wrapper; the sweep was driven with the flags inline |

The fourth is counted under (b) because the script was never committed.

## 3. What was changed

Twelve files, 32 addresses. Three sentences were rewritten rather than
repointed because the file they named is gone and no equivalent exists:

* `docs/GATES.md` said "The Wave 48 record of the original three remains at
  `docs/audit/wave48-pytest-pre-push-fixes.md` as history." It does not; the
  record is in no branch. The sentence now says the record was not carried
  into the flattened tree and restates the one fact it held (the three were
  an import-order defect in the test's mock).
* `docs/DEPRECATION.md` now says the J.2 ratio is read off the table by hand,
  that no checker ships, and what the ratio actually is — **0/9**, all nine
  rows `sunset_date: TBD`, against a target of >= 0.8. This is a disclosure
  that a governance target is unmet, not a change to it; J.2 appears in no
  paper surface (`grep -rn "J\.2" docs/drafts tnnls_submission docs/CLAIMS.md`
  returns nothing), so nothing in the submission moves.
* The self-flow card's four "harness stub" claims became "no SOTA harness
  ships; the stub named in earlier revisions was never committed", which is
  the same statement about capability with a true address attached.

`AGENTS.md:298` was a thirty-fourth instance the resolver could not see: the
research-audit playbook says `$EDITOR docs/paper-draft.md`, unbackticked, and
`TOKEN_RE` requires backticks. Fixed by hand. Widening the regex to
unbackticked tokens was rejected — it cannot distinguish a path from prose and
would have produced hundreds of false positives; the backtick is the signal
that the author meant an address.

## 4. The gate

`check_reviewer_pointers.py` gains three things.

**`READER_GLOBS`** — the nine page patterns above, globbed and de-duplicated
against the existing surfaces. Scope 638 -> **1016** tokens.

**`PROSE_ABSENT`** — nine `(document, token)` pairs whose *sentence* says the
target is gone ("was not carried over", "retired 2026-10-13", "never
committed", "not yet authored"). A resolver cannot judge these: "the record
this used to cite was retired" is a true statement whose subject is a missing
file, and rewriting the path would assert the record is filed somewhere it
never was.

The exemption is **conditional on the prose**, the same way `DECLARED_ABSENT`
is conditional on the file being absent. Each entry stores the phrases that
justify it, and at least one must appear within two lines of the token. Edit
the sentence to claim the file exists and the exemption lapses and the pointer
is reported. Keying on `(document, token)` rather than `token` means an
exemption cannot leak to another page that cites the same path for a real
reason.

**`DECLARED_ABSENT`** gains three entries for checkpoints the repository does
not distribute (`data/kanzi/kanzi_encoder.pt`, `data/kanzi_encoder.pt`,
`data/freqflow_ckpt/nnet_ema.pth`). Same conditional semantics as the two
already there: exempt while absent, checked once present.

Four tests pin the behaviour: a dead pointer in a model card is reported; a
`PROSE_ABSENT` pair is exempt only in its own document; the exemption lapses
when the phrase is removed; an undelivered checkpoint stops being exempt once
the file exists.

## 5. Observed facts vs interpretation

**Observed.** The 32 addresses do not resolve; five of the targets have no git
history; the 22-gate chain, `mypy --strict` and `ruff` pass before and after;
the manuscript's `.md`, `.tex` and `.pdf` are untouched.

**Interpretation.** These are not evidence defects — no number moved. They are
promises to a reader that the repository does not keep, and the class that
matters most is (b): four pages described a runnable artefact that was never
written. That is the same shape as the mypy gate reporting `SKIPPED` for
months (`docs/audit/mypy-gate-restoration.md`) and as the six §6 commands that
never executed (`docs/audit/repro-command-audit.md`): the surface reads as
verified because nothing was checking it.

**Unresolved.** 641 dead tokens remain in `docs/baseline-audit-report.md` and
`docs/CONSOLIDATED_RESULTS.md`. They are deliberately out of scope and now
named as such in the gate's docstring: those rows cite the
`verification_outputs/waveNNN-*` artefact of the run that produced the
measurement, which is the address of a result rather than a promise that the
file is on disk today. Repointing them would rewrite the provenance of a
measurement to a path that may hold a different run.

## 6. Verification

```
check_reviewer_pointers   checked=1016 dead=0        (pre-fix: 1027 / 32)
22/22 gate chain          OK
tests/test_tools/test_reviewer_pointers.py   13 passed
ruff check tools/ tests/  clean
mkdocs build --strict     exit 0
```
