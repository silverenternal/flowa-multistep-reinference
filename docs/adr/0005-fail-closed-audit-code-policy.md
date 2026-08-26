---
status: accepted
date: 2026-08-27
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 5. Fail-closed audit-code policy

## Context and Problem Statement

The engine and the bounded merge emit **audit codes** as the
fail-closed report for every round and every channel decision. The
audit codes live as string literals today:

* `adaptive_reflow/contracts/types.py` — the literal-set constants
  `COMPLEMENT_BLOCKER_CODES`, `RESTART_TRIGGER_CODES`, and
  `FEEDBACK_MODES`.
* `adaptive_reflow/frame/channel_rule.py` — the `BLOCKER_*`
  constants (`BLOCKER_PROXY_ONLY`, etc.).
* `adaptive_reflow/envelope/classifier.py` — the `OBS_*` and
  `_BLOCKER_GEOMETRY` constants.
* `adaptive_reflow/frame/engine.py` — the `ERR_*` constants that
  populate `EngineRoundResult.audit_codes`.

The audit codes are part of the **public surface**: the round trace
ships them downstream, the writer consumes them for fail-closed
rejection, and the docs scanner enumerates them in the audit-code
catalogue. Today the literals are scattered: some are `SCREAMING_SNAKE_CASE`
constants in the canonical surface; some are inline strings inside
the literal-set tuples in `contracts/types.py`; some are short
kebab-case strings that appear once in the docstrings.

The risk is that an audit code drifts: an inline string is renamed,
a constant is added but never exported, and the downstream consumer
silently fails to recognise the new code.

## Decision Drivers

* Audit codes are *fail-closed*: a consumer that does not recognise
  a code must reject the round, not guess.
* The codes appear in `tests/test_adversarial/` (every hostile-case
  test asserts a specific audit code).
* The docs scanner (`tools/check_docs_against_code.py`) must be able
  to enumerate every audit code so a rename surfaces as drift.

## Considered Options

1. **Every `AUDIT_*` constant is re-exported in the public
   `__init__.py` and indexed by the docs scanner catalogue.**
2. **Inline-string only.** Rejected because the docs scanner cannot
   enumerate inline literals without a static-analysis pass.
3. **A central `audit_codes.py` module.** Rejected because it would
   break the per-subpackage concern ownership and would force the
   audit codes to live outside the subpackage that emits them.

## Decision Outcome

Chosen option: **Every `AUDIT_*`, `ERR_*`, `BLOCKER_*`, and `OBS_*`
constant in `adaptive_reflow.contracts.types`,
`adaptive_reflow.frame.channel_rule`, `adaptive_reflow.frame.engine`,
and `adaptive_reflow.envelope.classifier` is re-exported from the
relevant `__init__.py` (the per-subpackage curated public surface) and
appears in the docs scanner catalogue at
`tools/check_docs_against_code.py`.**

The re-export pattern is:

* `adaptive_reflow/contracts/__init__.py` re-exports
  `COMPLEMENT_BLOCKER_CODES`, `RESTART_TRIGGER_CODES`, and
  `FEEDBACK_MODES` from `contracts.types`.
* `adaptive_reflow/frame/__init__.py` re-exports the
  `BLOCKER_*` constants from `frame.channel_rule` and the `ERR_*`
  constants from `frame.engine`.
* `adaptive_reflow/envelope/__init__.py` re-exports the `OBS_*` and
  `_BLOCKER_GEOMETRY` constants from `envelope.classifier`.

The docs scanner walk in `tools/check_docs_against_code.py` indexes
every CamelCase / SCREAMING_SNAKE_CASE identifier it finds inside
python-fenced code blocks in the governance docs and verifies each
against the AST-built symbol table.

### Consequences

Positive:

* Renaming an audit code surfaces as a doc-scanner drift failure
  before merge.
* Adding a new audit code without re-exporting it surfaces as the
  same drift failure.
* `tests/test_adversarial/test_hostile_cases.py` (and its siblings)
  can assert that the expected audit code is reachable from the
  public surface.

Negative:

* The re-export layer is one more thing to update when an audit
  code is added. The cost is small (one line per `__init__.py` per
  audit code) and is part of the merge bar.
* The literal-set tuples in `contracts/types.py` carry the canonical
  list of audit codes; the re-export layer must stay in sync with
  the tuples, not duplicate them.

### Confirmation

The decision is enforced by:

* The doc scanner (`tools/check_docs_against_code.py`) — every
  audit code referenced in `docs/` must resolve.
* The adversarial tests under `tests/test_adversarial/` — every
  hostile-case fixture asserts a specific audit code.
* The `CODEOWNERS` rule that pins the public `__init__.py` files
  to the maintainer.

## More Information

* [docs/TESTING_STRATEGY.md §2.3](../TESTING_STRATEGY.md) — the
  adversarial-test catalogue that consumes the audit codes.
* [DESIGN_BOUNDARY.md §3](../../DESIGN_BOUNDARY.md) — the six
  hostile cases, each with its expected audit code.
* [ARCHITECTURE.md §4.1](../../ARCHITECTURE.md) — the curated
  public surface of `contracts/`.
* [ROADMAP.md](../../ROADMAP.md) — the Now-bucket entry that closes
  DTB-R0 §3 case 2 and case 5 by 2026-09-15.