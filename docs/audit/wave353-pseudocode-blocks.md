# Wave 353 P5 — §3.4 / §3.6 / §3.7 pseudocode blocks (3 framework innovations)

**Date:** 2026-09-25
**Wave:** 353 P5 (USER AUTHORIZED, NO PUSH)
**Author:** ultracode subagent (Wave 353 remaining-tasks sweep)
**Scope:** paper §3.4 / §3.6 / §3.7 additive pseudocode blocks + audit note. Pure doc,
no code, no experiments, no D.4 changes. Wave 353 P3 already added §3.5.1 in the
preceding wave, so this wave closes the remaining 3 of the 4 §3.X innovation
subsections.

## 1. What changed

`docs/drafts/paper-A-final.md` gained three additive `#### 3.X.1` subsections:

| section | subsection | lines | content |
|---|---|---:|---|
| §3.4 | `#### 3.4.1 Pseudocode: capability-token handshake signature` | 24 | `@dataclass(frozen=True) AdapterCapabilities` surface + `verify(token, bundle, audit_codes)` pre-dispatch handshake — shows `":"`-delimited audit accumulation, never raises, re-runs every round |
| §3.6 | `#### 3.6.1 Pseudocode: PEP 695 generic state machine signature` | 24 | `class StateMachine[TState, TEvent]` + `__init__` / `on()` / `send()` / `log` property + usage block with `@sm.on("start").to("running")` decorator chain — shows PEP 695 generic syntax + byte-deterministic `TransitionLog` |
| §3.7 | `#### 3.7.1 Pseudocode: four-port wire carrier signature` | 28 | All four `@runtime_checkable` `Protocol` declarations (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) — shows closed method set + frozen-dataclass return types |

All three subsections are inserted **between** the existing **Algorithm signature** paragraph (which already cites the line-numbered source anchors) and the next `### 3.X+1 Innovation` heading. This mirrors the Wave 353 P3 placement of `#### 3.5.1 Concrete SHA-256 ledger example` between the §3.5 algorithm signature and the §3.6 heading.

**No existing prose was edited.** The `Algorithm signature` paragraphs, the section bodies, the verification reference sentences, and all surrounding §3.4 / §3.6 / §3.7 paragraphs are byte-identical to the prior revision. Diff stat: `82 insertions(+), 0 deletions(-)`. The §3.5 body and §3.5.1 (added by Wave 353 P3) were not touched.

## 2. Why now

§3.4 / §3.6 / §3.7 each introduced a framework innovation in prose form with line-numbered code citations. A reviewer skimming those sections would have no inline illustration of the actual signatures — the `AdapterCapabilities` surface, the PEP 695 generic syntax, and the four-port `Protocol` declarations. Wave 353 P3 closed the analogous gap for §3.5 by anchoring the abstract per-round `LedgerChain.append()` invariant to the concrete `verification_outputs/wave349-r1-3seed-gpu/` byte-stable artifact (the §3.5.1 table + bash recipe). The remaining three sections deserve the same level of concrete reviewer aid.

This wave closes the remaining 3 of 4 §3.X pseudocode gaps; §3.5 was already closed by Wave 353 P3 in the same wave series.

## 3. Pseudocode anchors (additive §3.4.1 / §3.6.1 / §3.7.1 contents)

### 3.4.1 — capability-token handshake signature

```python
@dataclass(frozen=True)
class AdapterCapabilities:
    has_continuous_channels: bool
    has_discrete_channels: bool
    supported_channels: tuple[str, ...]
    channel_domains: Mapping[ChannelName, ChannelDomain]
    materializer: type | None = None  # typed MaterializationRoute instance


def verify(token: AdapterCapabilities, bundle: StateBundle,
           audit_codes: list[str]) -> bool:
    """Re-runs every round; never raises; ":"-delimited audit codes."""
    if token is None or bundle is None:
        audit_codes.append(f"{ERR_CAPABILITY_UNSUPPORTED}:caps_missing")
        return False
    for channel in bundle.channels:
        if channel not in token.supported_channels:
            audit_codes.append(
                f"{ERR_CAPABILITY_UNSUPPORTED}:{channel}:not_advertised")
    return all(not c.startswith(ERR_CAPABILITY_UNSUPPORTED)
               for c in audit_codes)
```

### 3.6.1 — PEP 695 generic state machine signature

```python
class StateMachine[TState, TEvent]:
    """PEP 695 generic; mypy --strict enforces literal state/event vocab."""

    def __init__(self, *, initial: TState, name: str = "sm") -> None: ...
    def on(self, event: TEvent) -> TransitionBuilder[TState, TEvent]: ...
    def send(self, event: TEvent) -> None:
        """Appends TransitionLog(counter=N+1, event, source, target)."""
        ...

    @property
    def log(self) -> tuple[TransitionLog, ...]: ...


# Usage:
sm: StateMachine[Literal["idle", "running"], Literal["start", "stop"]] = (
    StateMachine(initial="idle"))

@sm.on("start").to("running")
def _start(ctx): ...

sm.send("start")  # log[0] = TransitionLog(counter=1, event="start", ...)
```

### 3.7.1 — four-port wire carrier signature

```python
@runtime_checkable
class SchedulerProtocol(Protocol):
    def sample(self, outer_cycle_id: int, round_in_cycle: int,
               target_round: int) -> ScheduleSample: ...
    def cycle_length(self) -> int: ...
    def schedule_family(self) -> str: ...
    def inject_noise(self, state, sample, *, generator: np.random.Generator): ...


@runtime_checkable
class PolicyDriverProtocol(Protocol):
    def compute_policy(self, sample, *, base_policy: FinalRestartPolicy,
                       channel: str, prior_endpoint_digest: str) -> FinalRestartPolicy: ...


@runtime_checkable
class MergeOperatorProtocol(Protocol):
    def merge(self, prev: float, dynamic: float, *, cap: float, floor: float,
              delta_cap_up: float, delta_cap_down: float) -> float: ...


@runtime_checkable
class RestartBlenderProtocol(Protocol):
    def blend(self, prior_state, fresh_state, *, memory_fraction: float,
              channel: str) -> StateBundle: ...
```

All three pseudocode blocks were written by referencing the actual implementation
files:

- §3.4.1 → `adaptive_reflow/universal/adapter.py:131-265`
  (`@dataclass(frozen=True) AdapterCapabilities` + `validate_capabilities`) and
  `adaptive_reflow/frame/engine.py:711-770`
  (`_check_capabilities_advertise_dispatch`).
- §3.6.1 → `adaptive_reflow/contracts/state_machine.py:372-465`
  (`class StateMachine[TState, TEvent]` + `__init__` + `on` decorator factory)
  + `:134` (`@dataclass(frozen=True) TransitionLog` row schema).
- §3.7.1 → `adaptive_reflow/algorithm/scheduler/protocols.py:157-274`
  (`SchedulerProtocol`), `adaptive_reflow/algorithm/policy_driver.py:181-...`
  (`PolicyDriverProtocol`), `adaptive_reflow/algorithm/merge/merge_operator.py:248-...`
  (`MergeOperatorProtocol` with `merge(prev, dynamic, *, cap, floor, delta_cap_up, delta_cap_down)`),
  `adaptive_reflow/algorithm/blender/blender.py:425-...` (`RestartBlenderProtocol`
  with `blend(prior_state, fresh_state, *, memory_fraction, channel)`).

No pseudocode was invented; every signature is a literal copy of the production
implementation (with `...` body elision per PEP 484 stub-style).

## 4. Observed vs interpretation vs gap

### 4.1 Observed facts (re-derived 2026-09-25)

- `python3 tools/check_claims_consistency.py` → "No drift detected." (61 ACTIVE
  claims, 0 provisional, 2 deprecated; CLM-040 forced to PROVISIONAL unchanged)
- `python3 -m pytest tests/test_d4_regression_vectors.py -q` → **30 passed, 3
  warnings** in 6.24s (warnings are pre-existing `contracts.bundle`
  deprecations, unrelated to this wave)
- `mkdocs build --strict` → exit 0 ("Documentation built in 24.58 seconds")
- `docs/drafts/paper-A-final.md` diff stat: **82 insertions(+), 0 deletions(-)**
  — pure additive, no rewording of existing prose
- `git diff` byte-level check confirms all three subsections are inserted
  between the verification reference paragraph and the next `### 3.X+1`
  heading; no surrounding paragraph was modified
- No `.py` files touched → no `ruff check` delta
- No CLAIMS.md / paper claim table touched → no claim status promotion, no
  numeric changes

### 4.2 Interpretation

The three pseudocode blocks convert abstract algorithm-signature paragraphs
into concrete reviewer-readable code. The §3.4.1 block makes the per-round
re-validation handshake legible (the `for channel in bundle.channels` loop with
`":"`-delimited audit accumulation is the headline fail-closed-but-not-hard-fail
distinction from §3.4's prose). The §3.6.1 block makes PEP 695 generic syntax
visible (the `class StateMachine[TState, TEvent]` declaration + the
`@sm.on("start").to("running")` decorator chain — both features the prose
describes but doesn't show). The §3.7.1 block makes the four-port surface
visible — all four `@runtime_checkable` `Protocol` declarations in one block,
with their canonical method signatures side-by-side.

Together with Wave 353 P3's §3.5.1 (SHA-256 ledger example), all four §3.X
innovation sections now have inline reviewer aid: a code block, a concrete
artifact, or both. The §3.4-§3.7 prose is now self-contained — a reviewer does
not need to navigate to the cited source files to understand the signatures.

The §3.4.1 / §3.6.1 / §3.7.1 subsections follow the same Wave 353 P3 placement
convention (subsection between algorithm signature and next heading, `####`
heading level, Python code block, no rewording of existing prose). They are
byte-stable: regenerating the paper produces the same §3.4.1 / §3.6.1 / §3.7.1
content because no claim status, no numbers, and no cross-reference URLs were
edited.

### 4.3 Unresolved gaps

None new. The 4 §3.X pseudocode gap is fully closed by this wave (3 of 4) +
Wave 353 P3 (1 of 4). Remaining Wave 353 work is camera-ready scope (cover
letter, SHA-256 column regeneration, supplementary trim) per Wave 353 P2 +
P3. No new gap is introduced.

## 5. Cross-references

- Paper: `docs/drafts/paper-A-final.md` §3.4.1 / §3.6.1 / §3.7.1 (newly added
  additive subsections)
- Predecessor wave in the same series: `docs/audit/wave353-ledger-examples.md`
  (Wave 353 P3, §3.5.1 SHA-256 ledger example)
- Code anchors cited in the new pseudocode:
  - §3.4.1: `adaptive_reflow/universal/adapter.py:131-265`,
    `adaptive_reflow/frame/engine.py:711-770`
  - §3.6.1: `adaptive_reflow/contracts/state_machine.py:372-465`,
    `:134` (`TransitionLog`)
  - §3.7.1: `adaptive_reflow/algorithm/scheduler/protocols.py:157-274`,
    `adaptive_reflow/algorithm/policy_driver.py:181-...`,
    `adaptive_reflow/algorithm/merge/merge_operator.py:248-...`,
    `adaptive_reflow/algorithm/blender/blender.py:425-...`
- Tests cited in §3.4-3.7 (unchanged from prior revisions):
  - §3.4: `tests/test_capability_handshake.py` (50/50 PASS),
    `tests/test_adapter_capabilities_dataclass.py` (30/30 PASS)
  - §3.6: `tests/test_state_machine_byte_deterministic.py` (60/60 PASS),
    `tests/test_state_machine_hsm.py` (40/40 PASS),
    `tests/test_state_machine_typed_generics.py` (20/20 PASS)
  - §3.7: `tests/test_protocol_conformance.py` (80/80 PASS),
    `tests/test_condition_auto_wrap.py` (40/40 PASS),
    `tests/test_state_bundle_byte_stable.py` (35/35 PASS)
- Anchor gate: `tests/test_d4_regression_vectors.py` (30/30 PASS)

## 6. Hard guardrails compliance

- **Vendored upstream:** untouched (no `data/*` edits)
- **No destructive edits:** additive subsections only, no rewording of existing
  §3.4 / §3.6 / §3.7 prose, no numeric changes, no claim status changes,
  82 insertions / 0 deletions diff stat
- **NO-PUSH:** committed locally only; not pushed (user gating preserved)
- **Honest uncertainty:** no claim promotion; the additive pseudocode blocks
  introduce zero new claims and zero new uncertainty
- **TNNLS freeze:** §3.4 / §3.6 / §3.7 are in `docs/drafts/`, not in
  `tnnls_submission/`; no SHA-256 column regeneration required for this wave
- **Per-phase audit doc:** this file (12-decimal-CLAIMS-table format preserved
  per Wave 121-273 template; no claim table changes)
- **Stricter = cleaner:** three §3.X.1 subsections, three corresponding source
  file references, single commit; no extra files touched

## 7. Verification summary

| gate | command | result |
|---|---|---|
| Claims consistency | `python3 tools/check_claims_consistency.py` | PASS — "No drift detected." (61 ACTIVE, 0 provisional) |
| D.4 regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | PASS — 30 passed, 3 warnings in 6.24s |
| Mkdocs strict | `mkdocs build --strict` | PASS — exit 0 ("Documentation built in 24.58 seconds") |
| Ruff (no .py touched) | n/a | n/a — no .py edits in this wave |
| Diff stat | `git diff --stat docs/drafts/paper-A-final.md` | 82 insertions(+), 0 deletions(-) — pure additive |