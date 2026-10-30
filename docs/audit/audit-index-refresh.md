# The audit index was a map with 129 streets missing

**Date:** 2026-10-30
**Scope:** `docs/audit/INDEX.md`, its generator, and the gate that keeps them in
sync.
**Status:** index regenerated (613 records, was 484 listed); generator committed as
`tools/regen_audit_index.py`; `--check` added to the gate chain and CI. No
metric, claim, status label, or verdict moved; no GPU was used.

---

## 1. The defect

`docs/audit/INDEX.md` is the topic-cluster map a reviewer reads to answer *"what
does the project claim about X?"*. It is generated — its own header says so —
but the generator lived at `/tmp/regen_index.py` and was never committed.

`/tmp` does not survive. So the map could not be refreshed, and by 2026-10-30 it
had drifted in three independent ways:

| | Index said | Tree held |
|---|---:|---:|
| Records listed | 484 | 613 |
| TOTAL row | 509 | — |
| Sum of its own columns | — | 484 |

The TOTAL row had been wrong since it was written: 509 is not the sum of the
column values above it, and never was. 129 records — 21% of the audit surface,
including every `GAP-01 … GAP-96` investigation note — appeared nowhere in the
map.

`INDEX_MAINTENANCE.md` documented this honestly: *"this index lists 484 of the
558 audit records on disk … the listing cannot be regenerated reproducibly.
Treat the index as a reading guide, not as a completeness proof."* That note was
itself stale (558, not 613) and it ended with the fix: *"A future wave could
commit it under `tools/` for reproducibility."* This is that wave.

## 2. What was done

`tools/regen_audit_index.py` reimplements the algorithm `INDEX_MAINTENANCE.md`
§2–§3 describes, because the original source was gone. Three properties were
required of it and each one shaped the design:

**Deterministic.** The old rows carried `(size, mtime)`. mtime is checkout time
on a clone, so a `--check` mode built on it would fail on every fresh checkout.
Size is no better: it changes whenever a record's prose is edited, which would
make the gate fire on prose edits and train everyone to regenerate without
reading the diff. Rows now carry the filename only, so the gate fires on
exactly the events that matter — a record added, removed, renamed, or moved
between clusters.

**Stable.** A record already listed in `INDEX.md` keeps its cluster. The keyword
passes place only records that are new since the last refresh. Running them over
the whole tree instead reshuffled 226 records into `engineering` on the first
attempt — because "link", "hash" and "todo" appear in half the corpus — and a
reading guide that moves under the reader is worse than one that lags.

**Complete.** Every `.md` under `docs/audit/` except `INDEX.md` is listed, and
the TOTAL row is computed rather than typed.

Two rules that the original document left implicit are now stated in it:

* **Three matching modes, not two.** `fname` (the 14 per-model clusters) and
  `name` (the six workflow clusters: engineering, reproducibility, push_state,
  paper_claims, final_verify, governance) match the filename only; `any` (the
  five topic clusters) also reads the first 40 lines. Content is a signal about
  *subject matter*, not *workflow stage* — a body mention of "submission" must
  not move an R-level study into `push_state`, and it did, in the first draft.
* **The `GAP-NN` series goes to `governance` unless its filename names a
  model.** Sixty-odd records, one investigation each, spanning several model
  families and no single topic. The `governance` scope line already names "gap"
  and "cross-cutting". `gap70-kanzi-latent` still lands in `kanzi`, because the
  per-model pass runs first.

## 3. Result

```
613 records (was 484 listed; 614 .md files under docs/audit/ minus INDEX.md)
347 active / 266 historical
25 clusters, order unchanged
```

612 of those are the records that existed before this note was written; the
613th is this note itself, which is why the number moved between the first and
second run.

The cluster count is 25, not the 24 `INDEX_MAINTENANCE.md` claimed: the table it
was describing has always had 25 rows, and its "16 per-model + 8 activity" split
sums to 24 only because two clusters were counted twice. Corrected there.

`governance` grows from 40 to 107 records because the gap series now lives
there; every other cluster is within a few records of where it was.

## 4. The gate

`python3 tools/regen_audit_index.py --check` exits 1 when the committed file
differs from a fresh build. `tests/test_tools/test_audit_index.py` (7 tests)
pins the invariants that failed:

* a fresh build is byte-identical to the committed file;
* the multiset of listed filenames equals the multiset on disk — so a record
  cannot vanish and a phantom cannot appear;
* the TOTAL row equals the sum of the columns;
* each table row agrees with the detail block beneath it, and a zero-file
  cluster has no detail block;
* cluster order matches `CLUSTERS` and the count is 25;
* two builds in the same tree are identical;
* a record inside `docs/audit/kanzi/` classifies as `kanzi` regardless of what
  its body says.

It is entry 15 of `todo.json`'s `gate_chain` and part of CI's Gate 7.

## 5. What this does not fix

Cluster assignment for a cross-cutting note is still a judgement call, and the
keyword lists in `tools/regen_audit_index.py` are a reconstruction — the
original lists are gone. They were tuned until the 128 records new since Wave
384 landed sensibly; they are not authoritative for records that already have a
placement, because those keep it.

The map also remains a *reading guide*: `ls docs/audit/` is still the
authoritative inventory. The difference is that the two now agree.
